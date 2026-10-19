#!/usr/bin/env python3
"""Check the 130-175 MHz harmonic low-pass (7th-order elliptic-type ladder, 3 traps).

Prints insertion loss (lossless and with finite Q), stopband rejection, a +-2 % Monte Carlo
and the RMS voltage/current in every part at a given power, matched and at SWR 3.

    python3 tools/vhf_lpf_check.py            # 100 W
    python3 tools/vhf_lpf_check.py --power 5  # LinHT level
Topology (50 ohm in/out):
    C1 shunt - (L2 || C2) series - C3 shunt - (L4 || C4) series - C5 shunt - (L6 || C6) series - C7 shunt
"""
import argparse
import numpy as np

Z0 = 50.0
# Rounded design values: capacitors E24 (pF), inductors to 0.5 nH
DESIGN = [("C", 33.0), ("T", 36.0, 2.7), ("C", 75.0), ("T", 22.0, 12.0),
          ("C", 68.0), ("T", 24.5, 15.0), ("C", 27.0)]


def mats(el, f, QL=None, QC=None):
    w = 2 * np.pi * f
    out = []
    for e in el:
        if e[0] == "C":
            Zc = 1 / (1j * w * e[1] * 1e-12)
            if QC:
                Zc += abs(Zc) / QC
            out.append(np.array([[1, 0], [1 / Zc, 1]]))
        else:
            ZL = 1j * w * e[1] * 1e-9
            Zc = 1 / (1j * w * e[2] * 1e-12)
            if QL:
                ZL += abs(ZL) / QL
            if QC:
                Zc += abs(Zc) / QC
            out.append(np.array([[1, ZL * Zc / (ZL + Zc)], [0, 1]]))
    return out


def s21_db(el, f, **q):
    M = np.eye(2, dtype=complex)
    for m in mats(el, f, **q):
        M = M @ m
    A, B, C, D = M.ravel()
    return -20 * np.log10(abs(2 / (A + B / Z0 + C * Z0 + D)))


def stress(el, f, P, gamma):
    """RMS voltage across / current through each part; source 50 ohm, available power P."""
    ZL = Z0 * (1 + gamma) / (1 - gamma)
    Vs = np.sqrt(8 * P * Z0)
    w = 2 * np.pi * f
    V, I = ZL, 1.0
    st = []
    for m, e in zip(reversed(mats(el, f)), reversed(el)):
        Vo = V
        V, I = m @ np.array([V, I])
        st.append((e, V, Vo))
    k = (Vs / (Z0 + V / I)) / I
    res = []
    for e, Vi, Vo in reversed(st):
        if e[0] == "C":
            Vc = Vi * k
            res.append((f"C {e[1]:g} pF", abs(Vc) / 2 ** .5, abs(Vc * 1j * w * e[1] * 1e-12) / 2 ** .5))
        else:
            Vd = (Vi - Vo) * k
            res.append((f"L {e[1]:g} nH", abs(Vd) / 2 ** .5, abs(Vd / (1j * w * e[1] * 1e-9)) / 2 ** .5))
            res.append((f"C {e[2]:g} pF (trap)", abs(Vd) / 2 ** .5, abs(Vd * 1j * w * e[2] * 1e-12) / 2 ** .5))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--power", type=float, default=100.0, help="available power in W")
    ap.add_argument("--ql", type=float, default=100.0)
    ap.add_argument("--qc", type=float, default=500.0)
    a = ap.parse_args()
    el = DESIGN
    print("Insertion loss, dB (lossless / with QL=%g, QC=%g):" % (a.ql, a.qc))
    for f in [130e6, 145e6, 160e6, 175e6]:
        print(f"  {f/1e6:4.0f} MHz  {s21_db(el, f):5.2f} / {s21_db(el, f, QL=a.ql, QC=a.qc):5.2f}")
    fs = np.linspace(256e6, 1200e6, 2000)
    att = np.array([s21_db(el, f) for f in fs])
    print(f"Minimum rejection 256-1200 MHz: {att.min():.1f} dB at {fs[att.argmin()]/1e6:.0f} MHz (lossless, no parasitics)")
    rng = np.random.default_rng(0)
    fp = np.linspace(130e6, 175e6, 46)
    fsm = np.linspace(256e6, 1200e6, 400)
    pb, sb = [], []
    for _ in range(300):
        p = [("C", e[1] * (1 + rng.uniform(-.02, .02)) + rng.uniform(-.1, .1)) if e[0] == "C" else
             ("T", e[1] * (1 + rng.uniform(-.02, .02)), e[2] * (1 + rng.uniform(-.02, .02)) + rng.uniform(-.1, .1))
             for e in el]
        pb.append(max(s21_db(p, f) for f in fp))
        sb.append(min(s21_db(p, f) for f in fsm))
    print(f"Monte Carlo, 300 runs, +-2 % (+-0.1 pF): passband loss 99th pct {np.percentile(pb, 99):.2f} dB, "
          f"rejection 1st pct {np.percentile(sb, 1):.1f} dB")
    for name, gl in [("matched", [0]),
                     ("SWR 3, all phases", [0.5 * np.exp(1j * t) for t in np.linspace(0, 2 * np.pi, 72, endpoint=False)])]:
        worst = {}
        for f in np.linspace(130e6, 175e6, 10):
            for g in gl:
                for i, (lab, V, I) in enumerate(stress(el, f, a.power, g)):
                    o = worst.get(i, (lab, 0, 0))
                    worst[i] = (lab, max(o[1], V), max(o[2], I))
        print(f"Worst-case part stress, {a.power:g} W, 130-175 MHz, {name} (V rms / A rms):")
        for lab, V, I in worst.values():
            print(f"  {lab:18s} {V:6.1f} V  {I:5.2f} A")


if __name__ == "__main__":
    main()
