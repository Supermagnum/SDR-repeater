#!/usr/bin/env python3
"""P2.5 step 3: charge-pump Monte Carlo, fractional spurs from the measured nonlinearity, PLL current
(spec/pll-topology.md §6, step 3).

Run inside the container from this folder:

    mkdir -p out
    python3 -u run_step3.py mc | tee out/summary_mc.txt         # Monte Carlo, about 4 h (n=10)
    python3 -u run_step3.py mc n=3 tt | tee out/summary_mc3.txt # quick trial
    python3 -u run_step3.py spur | tee out/summary_spur.txt     # minutes, uses out/mc_*.json
    python3 -u run_step3.py current | tee out/summary_cur.txt   # uses out/mc_*.json

mc      The step-2a PFD and charge pump (transistor level, with the offset-current pair) with PDK mismatch on
        every transistor (sigma(V_T) 3.9 / 2.2 mV um / sqrt(WL), sigma(beta) 0.5 / 0.33 % um, sigma(W) 4 nm,
        sigma(L) 2 nm; as P2.4 step 3). Per sample: Q(dt) at dt = 1-5 ns of UP lead, its slope, lock point and
        INL; plus a nominal run per case. Cases: tt at V_tune 0.25 / 0.6 / 0.95 V, ss at 0.6 V.
spur    For every curve, the fractional spur at the boundary offset (600 kHz VHF, 2 MHz UHF) from the
        cycle-by-cycle PLL model pll_behav.py (real Sigma-Delta sequence, measured nonlinearity, P2.2 loop).
        Limit at RF -95 dBc (25 W duplex).
current Supply current of PFD, pump and amplifiers from the runs, plus estimates for the other PLL blocks,
        against the <= 1.8 mA left in the LO budget (D7).
Results are [SCH] (mc), [MODEL] (spur), [SCH] + [HAND] (current).
"""
import importlib.util
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
_spec = importlib.util.spec_from_file_location("pll_step2", os.path.join(REPO, "analog", "pll", "step2", "run_step2.py"))
S2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S2)
S2.OUT = OUT

CASES = [("tt", 0.25), ("tt", 0.6), ("tt", 0.95), ("ss", 0.6)]
DTS = [1.0e-9, 2.0e-9, 3.0e-9, 4.0e-9, 5.0e-9]
MM = {"n": (3.9e-3, 0.005), "p": (2.2e-3, 0.0033)}      # A_VT (V um), A_beta (um), PDK mismatch values
DW, DL = 4e-9, 2e-9


def mismatch(rng):
    """Netlist transform: random V_T (series gate source), beta and W, L on every sg13_lv MOS line."""
    pat = re.compile(r"^(\S+) \((\S+) (\S+) (\S+) (\S+)\) sg13_lv_(n|p)mos w=([\d.]+)u l=([\d.]+)u(.*)$")

    def apply(text):
        out, k = [], 0
        for ln in text.splitlines():
            m = pat.match(ln)
            if not m:
                out.append(ln)
                continue
            name, d, g, s, b, typ, w, l, rest = m.groups()
            w, l = float(w), float(l)
            avt, ab = MM[typ]
            dvt = rng.normal(0, avt / math.sqrt(w * l))
            beta = rng.normal(1, ab / math.sqrt(w * l))
            w2 = (w + rng.normal(0, DW * 1e6)) * beta
            l2 = l + rng.normal(0, DL * 1e6)
            k += 1
            out.append(f"vmm{k} (x_mmg{k} {g}) vsource dc={dvt:.5e}")
            out.append(f"{name} ({d} x_mmg{k} {s} {b}) sg13_lv_{typ}mos w={w2:.4f}u l={l2:.4f}u{rest}")
        return "\n".join(out) + "\n"
    return apply


def curve(corner, vt, tag, post):
    qs, ivdd, ioff = [], [], []
    for dt in DTS:
        q, _, _, _, st = S2.run(f"mc_{corner[0]}_{vt:.2f}_{tag}_{dt*1e9:.0f}", corner, vt, dt, S2.ICP, ioff=True, post=post)
        qs.append(q / S2.ICP)
        ivdd.append(st["ivdd"])
        ioff.append(st["ioff"])
    da, qa = np.array(DTS), np.array(qs)
    k, c = np.polyfit(da, qa, 1)
    inl = float(np.max(np.abs(qa - (k * da + c))))
    return dict(tag=tag, dts=DTS, qs=qs, slope=float(k), lock=float(-c / k), inl=inl,
                ivdd=float(np.mean(ivdd)), ioff=float(np.mean(ioff)))


def check_mc(cases, n):
    print(f"## Charge-pump Monte Carlo, {n} samples per case [SCH]\n")
    print("Q(dt) at dt = 1-5 ns with the offset current; INL = largest deviation from the straight line (ps). "
          "Transistor mismatch on every device of PFD, pump and amplifiers.\n")
    print("| Corner | V_tune | Nominal INL (ps) | INL mean / max (ps) | Lock point mean / min / max (ns) | "
          "Slope mean / sigma | Offset current mean / sigma (µA) | Supply current (mA) |")
    print("|---|---|---|---|---|---|---|---|")
    for cname, vt in cases:
        corner = next(c for c in S2.CORNERS if c[0] == cname)
        res = [curve(corner, vt, "nom", None)]
        for k in range(n):
            try:
                res.append(curve(corner, vt, f"s{k}", mismatch(np.random.default_rng(3000 + k))))
            except RuntimeError as e:
                print(f"  sample {k} failed: {str(e)[-200:]}", file=sys.stderr)
        with open(os.path.join(OUT, f"mc_{cname}_{vt:.2f}.json"), "w") as fh:
            json.dump(dict(corner=cname, vt=vt, results=res), fh, indent=1)
        s = res[1:]
        if not s:
            print(f"| {cname} | {vt} | {res[0]['inl']*1e12:.1f} | no samples |")
            continue
        inl = np.array([r["inl"] for r in s]) * 1e12
        lk = np.array([r["lock"] for r in s]) * 1e9
        sl = np.array([r["slope"] for r in s])
        io = np.array([r["ioff"] for r in s]) * 1e6
        print(f"| {cname} | {vt} | {res[0]['inl']*1e12:.1f} | {inl.mean():.1f} / {inl.max():.1f} | "
              f"{lk.mean():.2f} / {lk.min():.2f} / {lk.max():.2f} | {sl.mean():.3f} / {sl.std(ddof=1) if len(sl) > 1 else 0:.3f} | "
              f"{io.mean():.1f} / {io.std(ddof=1) if len(io) > 1 else 0:.1f} | {res[0]['ivdd']*1e3:.2f} |")
    print()


def load():
    data = []
    for cname, vt in CASES:
        p = os.path.join(OUT, f"mc_{cname}_{vt:.2f}.json")
        if os.path.exists(p):
            data.append(json.load(open(p)))
    if not data:
        sys.exit("no out/mc_*.json - run 'mc' first")
    return data


def check_spur():
    import pll_behav as B
    print("## Fractional spur at the boundary offset from the measured pump nonlinearity [MODEL]\n")
    print("Cycle-by-cycle PLL (pll_behav.py): MASH 1-1-1 sequence, P2.2 loop (150 kHz), I_cp 50 µA, K_VCO "
          "40 MHz/V, offset current 10 %; the pump's measured Q(dt) deviation from a straight line applied to every "
          "cycle. Spur at RF (dBc); limit −95 dBc. 'Floor' is the Σ-Δ noise in one bin (≈ 550 Hz) — a spur below "
          "it is not resolved.\n")
    lin = {band: B.spur(band) for band in B.BANDS}
    print(f"Linear pump (reference): VHF {lin['VHF']['spur_rf']:.1f} dBc (floor {lin['VHF']['floor_rf']:.1f}), "
          f"UHF {lin['UHF']['spur_rf']:.1f} dBc (floor {lin['UHF']['floor_rf']:.1f}).\n")
    print("| Corner | V_tune | Curve | INL (ps) | VHF spur (dBc) | UHF spur (dBc) |")
    print("|---|---|---|---|---|---|")
    worst = {"VHF": -999.0, "UHF": -999.0}
    for d in load():
        rows = d["results"]
        nom, samples = rows[0], rows[1:]
        pick = [("nominal", nom)]
        if samples:
            pick.append(("worst INL sample", max(samples, key=lambda r: r["inl"])))
        for lab, r in pick:
            f = B.inl_from_curve(r["dts"], np.array(r["qs"]))
            sp = {band: B.spur(band, f)["spur_rf"] for band in B.BANDS}
            for band in sp:
                worst[band] = max(worst[band], sp[band])
            print(f"| {d['corner']} | {d['vt']} | {lab} | {r['inl']*1e12:.1f} | {sp['VHF']:.1f} | {sp['UHF']:.1f} |")
    print(f"\nWorst: VHF {worst['VHF']:.1f} dBc, UHF {worst['UHF']:.1f} dBc against −95 dBc "
          f"(margin {-95 - worst['VHF']:.0f} / {-95 - worst['UHF']:.0f} dB).\n")


def check_current():
    print("## PLL current [SCH] + [HAND]\n")
    meas = [(d["corner"], d["vt"], d["results"][0]["ivdd"]) for d in load()]
    print("PFD, charge pump and both amplifiers, measured (mean supply current over the run, I_cp 100 µA, offset "
          "pair on): " + "; ".join(f"{c} {vt} V: {i*1e3:.2f} mA" for c, vt, i in meas) + ".\n")
    pump = max(i for _, _, i in meas)
    est = [("Reference buffer (36 MHz)", 0.15e-3, "[HAND]"),
           ("PFD, charge pump, replica amplifier, dummy buffer, offset pair", pump, "[SCH] (worst of the runs)"),
           ("Amplifier bias generator", 0.03e-3, "[HAND]"),
           ("MMD prescaler, two TSPC cells at ≤ 2.2 GHz", 0.25e-3, "[HAND] (P2.4 TSPC: ≈ 0.1 mA per flip-flop pair)"),
           ("MMD counters at ≤ 550 MHz", 0.05e-3, "[HAND]"),
           ("Σ-Δ, lock detector, calibration (36 MHz)", 0.1e-3, "[HAND] (≈ 1500 gates, activity 0.3)")]
    print("| Block | Current (mA) | Source |")
    print("|---|---|---|")
    tot = 0.0
    for lab, i, src in est:
        tot += i
        print(f"| {lab} | {i*1e3:.2f} | {src} |")
    print(f"| **PLL total** | **{tot*1e3:.2f}** | budget ≤ 1.8 mA (D7 margin) |\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    n = next((int(a[2:]) for a in args if a.startswith("n=")), 10)
    print("# P2.5 step 3 — charge-pump Monte Carlo, spurs, current\n")
    if "mc" in args:
        cases = [c for c in CASES if c[0] in args] or CASES
        check_mc(cases, n)
    if "spur" in args:
        check_spur()
    if "current" in args:
        check_current()


if __name__ == "__main__":
    main()
