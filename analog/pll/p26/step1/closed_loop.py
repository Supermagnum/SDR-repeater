#!/usr/bin/env python3
"""P2.6 step 1: behavioural closed loop with the circuit data — band calibration, acquisition, lock
(spec/pll-topology.md §13).

Runs anywhere (numpy, scipy; no simulator):

    python3 closed_loop.py | tee out/summary.txt      # landing sweep + closed-loop runs, a few minutes
    python3 closed_loop.py land                       # calibration landing sweep only (seconds)

Blocks, each from its circuit result:
  VCO        f(code, V) = f_bank(code) + K(code) (V - 0.6 V); bank 2.90-4.41 GHz over 128 codes (C linear in
             code, as models.f_vco), K 13.1 MHz/V at the bottom to 38.6 MHz/V at the top, interpolated in f^3
             (P2.3 §9). Linear in V (the varactor's own curvature is not modelled).
  I_cp       per band so that I_cp K is about 50 uA x 40 MHz/V, in 25 uA steps 25-200 uA (PLL_CTRL[5:3]);
             offset current 10 % of I_cp (D18). Compliance: up current falls to zero over 0.2 V above the top
             of the window (0.95 V; 0.85 V at the slow corner, step 2a), down current below 0.15 V.
  PFD        tri-state, reset 0.25 ns after both are set (step 2a).
  Loop filter  C1 39 pF || (R1 9.5 kOhm + C2 355 pF), R3 34 kOhm, C3 3.9 pF (P2.2), solved exactly.
  Divider    ref 36 MHz; P = 3 (VHF) / 2 (UHF) from the LO chain; MMD ratio every cycle from the bit-exact
             MASH 1-1-1 model (rtl/afe/sdm.sv); random initial divider phase after the hold is released.
  Calibration  rtl/afe/bandcal.sv: V_tune held at the step-4 hold voltage (0.568 V tt, 0.498 V ss, 0.641 V ff);
             SAR over 7 bits, prescaler output f/(4P) counted for 128 reference cycles with a random count
             phase; result = highest code whose count is >= the target. Variant 'nearest' (proposal): one more
             trial on the next code (code + 1, the first one below the target) and keep whichever count is
             closer to the target, +4.2 us.
  Lock detector  rtl/afe/lockdet.sv (two-sided, window 7.4 ns, 64 good cycles, two-flop synchronisers).
Outputs per run: V_tune after lock (inside 0.25-0.95 V? ss: 0.25-0.85 V), time for the lock detector, time
until the frequency error (averaged over 128 reference cycles) stays within 10 Hz at RF, cycle slips.
Wake budget: calibration + lock <= 150 us (spec/phase2-plan.md §2.2). Results are [MODEL].
"""
import math
import os
import sys

import numpy as np
from scipy.linalg import expm

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "rtl", "afe", "cocotb"))
import models  # noqa: E402

F_REF = 36e6
T = 1 / F_REF
sys.path.insert(0, os.path.join(REPO, "analog", "pll-model"))
import pll_model  # noqa: E402
# Loop filter. As built in P2.5 (P2.2 values): C1 39 pF, C2 355 pF, R1 9.5 kOhm, R3 34 kOhm, C3 3.9 pF - sized with a
# 2 pi error in pll_model.design_loop, so the loop is about 42 kHz with 35 deg phase margin, not 150 kHz / 55 deg.
LF_BUILT = dict(C1=39e-12, C2=355e-12, R1=9.5e3, R3=34e3, C3=3.9e-12)
BW = next((float(a[3:]) for a in sys.argv[1:] if a.startswith("bw=")), 60e3)
LF_NEW = {k: float(v) for k, v in pll_model.design_loop(BW, 62.0, 40e6, 50e-6, 3.65e9 / 32e6).items()}
LF = LF_BUILT if "built" in sys.argv[1:] else LF_NEW
K_LOG2, SETTLE, SETTLE0 = 7, 16, 64
T_RST = 0.25e-9
T_W = 7.4e-9
CORNERS = {"tt": dict(vhold=0.568, vup=0.95), "ss": dict(vhold=0.498, vup=0.85), "ff": dict(vhold=0.641, vup=0.95)}
WINDOW = {"tt": (0.25, 0.95), "ss": (0.25, 0.85), "ff": (0.25, 0.95)}
F_LO, F_HI = 2.90e9, 4.41e9


CFG = dict(nb=7, cdiv=4)        # bank bits; counted clock = f_VCO / (cdiv x P) (RTL: 4, the MMD prescaler output)


def ncodes():
    return 1 << CFG["nb"]


def f_bank(code):
    # same range (2.90-4.41 GHz) for any number of bank bits, C linear in code
    return models.f_vco(code * 127 / (ncodes() - 1))


def kvco(code):
    f = f_bank(code)
    return 13.1e6 + (38.6e6 - 13.1e6) * (f ** 3 - F_LO ** 3) / (F_HI ** 3 - F_LO ** 3)


def f_of(code, v):
    return f_bank(code) + kvco(code) * (v - 0.6)


def icp_for(code):
    return min(200e-6, max(25e-6, round(50e-6 * 40e6 / kvco(code) / 25e-6) * 25e-6))


def channel(f_vco, band):
    p = 3 if band == "VHF" else 2
    n = f_vco / F_REF
    n_int, n_frac = int(n), int(round((n - int(n)) * 2 ** 24))
    if n_frac == 2 ** 24:
        n_int, n_frac = n_int + 1, 0
    m = models.m_full(n_int, n_frac, p == 3)
    return p, m, p * m / 2 ** 24 * F_REF          # P, M (7.24), exact VCO target


# ------------------------------------------------------------------------------------------ calibration
def count(f, p, rng):
    return int(math.floor(f / (CFG["cdiv"] * p) * (1 << K_LOG2) * T + rng.random()))


def calibrate(m, p, vhold, rng, rule="highest"):
    """bandcal.sv: SAR from code 64, keep a bit while count >= target. Returns code, time (s)."""
    target = (m << K_LOG2) // (CFG["cdiv"] << 24)       # K M / cdiv (RTL: m_full >> 19)
    nb = CFG["nb"]
    code, band = 0, 1 << (nb - 1)
    cycles = 0
    for bitn in range(nb - 1, -1, -1):
        cycles += (SETTLE0 if bitn == nb - 1 else SETTLE) + (1 << K_LOG2) + 6
        ok = count(f_of(band, vhold), p, rng) >= target
        if ok:
            code = band
        if bitn:
            band = (band if ok else code) | (1 << (bitn - 1))
        else:
            band = band if ok else code
    if rule == "nearest" and band < ncodes() - 1:
        cycles += SETTLE + (1 << K_LOG2) + 6
        c0 = count(f_of(band, vhold), p, rng)          # (the RTL would keep this count from the last trial)
        c1 = count(f_of(band + 1, vhold), p, rng)
        if abs(c1 - target) < abs(c0 - target):
            band += 1
    return band, cycles * T


OPTIONS = [("as designed (7 bits, count f / 4P)", 7, 4), ("7 bits, count f / P", 7, 1),
           ("8 bits, count f / 4P", 8, 4), ("8 bits, count f / P", 8, 1)]


def landing(cn, rule, rng):
    c = CORNERS[cn]
    vs, cases, tc = [], [], 0.0
    for band, lo, hi in (("VHF", 3.12e9, 4.20e9), ("UHF", 3.20e9, 3.84e9)):
        for fv in np.arange(lo, hi + 1, 0.5e6):
            p, m, ft = channel(fv, band)
            code, tc = calibrate(m, p, c["vhold"], rng, rule)
            v = c["vhold"] + (ft - f_of(code, c["vhold"])) / kvco(code)
            vs.append(v)
            cases.append((v, band, fv))
    return np.array(vs), cases, tc


def land_sweep():
    print("## Where V_tune lands after the band calibration [MODEL]\n")
    print("Every VCO target from 3.12 to 4.20 GHz in 0.5 MHz steps (VHF, P = 3) and 3.20–3.84 GHz (UHF, P = 2), "
          "2858 channels; V_tune after lock = V_hold + (f_target − f(code, V_hold)) / K. Window 0.25–0.95 V "
          "(slow corner 0.25–0.85 V). 'highest' = the RTL rule; 'nearest' = one more trial on the next code and keep "
          "the closer count. One band step is 0.45–0.59 V of V_tune with 7 bits, half that with 8. Counting f / P "
          "instead of f / 4P gives 4 × the counts (3700–6400 instead of 920–1600 per 128 reference cycles).\n")
    print("| Bank, counter | Rule | Calibration (µs) | tt: V_tune min–max, outside | ss | ff |")
    print("|---|---|---|---|---|---|")
    worst = {}
    for lab, nb, cdiv in OPTIONS:
        CFG.update(nb=nb, cdiv=cdiv)
        for rule in ("highest", "nearest"):
            cells, tc = [], 0.0
            for cn in CORNERS:
                vs, cases, tc = landing(cn, rule, np.random.default_rng(1))
                lo_w, hi_w = WINDOW[cn]
                out = np.mean((vs < lo_w) | (vs > hi_w)) * 100
                cells.append(f"{vs.min():.2f}–{vs.max():.2f} V, {out:.1f} %")
                worst[(lab, rule, cn)] = (min(cases), max(cases))
            print(f"| {lab} | {rule} | {tc*1e6:.1f} | " + " | ".join(cells) + " |")
    CFG.update(nb=7, cdiv=4)
    print()
    return worst


# ---------------------------------------------------------------------------------------- closed loop
def run(fv, band, corner, rule, seed=0, t_end=220e-6, align=False, fast=0.0):
    rng = np.random.default_rng(seed)
    c = CORNERS[corner]
    p, m, ft = channel(fv, band)
    n_lo = 24 if band == "VHF" else 8
    code, t_cal = calibrate(m, p, c["vhold"], rng, rule)
    k, icp = kvco(code), icp_for(code)
    f0 = f_of(code, 0.6)
    ioff = 0.1 * icp
    c1, c2, r1, r3, c3 = LF["C1"], LF["C2"], LF["R1"], LF["R3"], LF["C3"]
    ncyc = int(t_end / T) + 2
    nseq = models.sdm(m, ncyc + 10)

    def mat(i, r1=r1):
        # z = [v1, v2, v3, phi (VCO cycles), 1]
        M = np.zeros((5, 5))
        M[0, :3] = [-1 / (r1 * c1) - 1 / (r3 * c1), 1 / (r1 * c1), 1 / (r3 * c1)]
        M[0, 4] = i / c1
        M[1, :2] = [1 / (r1 * c2), -1 / (r1 * c2)]
        M[2, 0], M[2, 2] = 1 / (r3 * c3), -1 / (r3 * c3)
        M[3, 2], M[3, 4] = k, f0 - 0.6 * k
        return M

    def current(up, dn, v1):
        gu = min(1.0, max(0.0, (c["vup"] + 0.2 - v1) / 0.2))
        gd = min(1.0, max(0.0, v1 / 0.15))
        return icp * (up * gu - dn * gd) - ioff * gd

    z = np.array([c["vhold"]] * 3 + [0.0, 1.0])
    if align:
        # divider started on a reference edge: first divider edge one divider period later (D18 lock point)
        target = f_of(code, c["vhold"]) * (T + 2.8e-9)
    else:
        # random divider phase at release: first divider edge somewhere in the first divider period
        target = rng.random() * p * nseq[0]
    t, kref, kdiv = 0.0, 0, 0
    next_ref = T
    up = dn = 0
    reset_at = None
    samples = []                      # (time, kind, cycle) - lock-detector sampling
    lock_t = None
    good = 0
    pipe_u, pipe_d = [1, 1], [1, 1]
    dq = 1
    v3_log, t_log = [], []
    phase_err = []
    while t < t_end:
        cand = [next_ref]
        if reset_at is not None:
            cand.append(reset_at)
        if samples:
            cand.append(samples[0][0])
        tn = min(cand)
        boost = t < fast                          # fast lock: 4 x I_cp, R1 / 2 (twice the bandwidth)
        if fast and t < fast < tn:
            tn = fast
        M = mat(current(up, dn, z[0]) * (4 if boost else 1) + (3 * ioff if boost else 0), r1 / 2 if boost else r1)
        zn = expm(M * (tn - t)) @ z
        if zn[3] >= target:                       # divider edge first
            tc = t + (target - z[3]) / max(f_of(code, z[2]), 1e8)
            for _ in range(4):
                zc = expm(M * (tc - t)) @ z
                tc -= (zc[3] - target) / max(k * zc[2] + f0 - 0.6 * k, 1e8)
                tc = min(max(tc, t), tn)
            z = expm(M * (tc - t)) @ z
            t = tc
            dn = 1
            if up and reset_at is None:
                reset_at = t + T_RST
            samples.append((t + T_W, "dn", kdiv))
            samples.sort()
            phase_err.append(t - kdiv * T - T)    # divider edge against the k-th reference edge
            kdiv += 1
            target += p * nseq[kdiv]
            continue
        z, t = zn, tn
        if tn == fast and tn != next_ref and tn != reset_at and not (samples and samples[0][0] == tn):
            continue                               # end of the fast-lock interval only
        if tn == next_ref:
            up = 1
            if dn and reset_at is None:
                reset_at = t + T_RST
            samples.append((t + T_W, "up", kref))
            samples.sort()
            kref += 1
            next_ref = (kref + 1) * T
            v3_log.append(z[2])
            t_log.append(t)
        elif reset_at is not None and tn == reset_at:
            up = dn = 0
            reset_at = None
        else:
            _, kind, _ = samples.pop(0)
            if kind == "dn":
                dq = dn
            else:                                  # clk_su domain: synchronisers and counters
                pipe_u = [up, pipe_u[0]]
                pipe_d = [dq, pipe_d[0]]
                if not (pipe_u[1] or pipe_d[1]):
                    good += 1
                    if good == 64 and lock_t is None:
                        lock_t = t
                else:
                    good = 0
    v3 = np.array(v3_log)
    tl = np.array(t_log)
    # settling: the control voltage averaged over 128 reference cycles (sampled at the reference edges, the
    # same ripple phase every time) against its average over the last 20 us, as a frequency error at RF.
    # (The VCO frequency itself, averaged over 128 cycles, keeps 50-100 Hz at RF of Sigma-Delta wander - the
    # divider-phase noise over a 3.6 us window - so it cannot show 10 Hz.)
    w = 128
    va = np.convolve(v3, np.ones(w) / w, mode="valid")
    vf = np.mean(v3[-int(20e-6 / T):])
    err = np.abs(va - vf) * k / n_lo
    def settle(lim):
        bad = np.where(err > lim)[0]
        if not len(bad):
            return tl[w]
        return tl[bad[-1] + w] if bad[-1] + w < len(tl) - int(20e-6 / T) else float("inf")
    t_settle, t_settle100 = settle(10.0), settle(100.0)
    pe = np.array(phase_err)
    slips = int(np.sum(np.abs(np.diff(np.round(pe / T))) > 0))
    return dict(code=code, t_cal=t_cal, df0=f_of(code, c["vhold"]) - ft, icp=icp, k=k,
                v_final=float(np.mean(v3[-200:])), t_lock=lock_t, t_settle=t_settle, t_settle100=t_settle100, slips=slips,
                vmin=float(v3.min()), vmax=float(v3.max()), n_lo=n_lo)


def closed_loop(worst):
    print("## Closed loop after calibration [MODEL]\n")
    print("Times from the release of the hold. 'Settled' = the control voltage, averaged over 128 reference "
          "cycles, within 10 Hz (or 100 Hz) at RF of its final value. Wake = calibration + settled (10 Hz); budget "
          "150 µs (spec/rf-frontend.md: 50 µs typical, 150 µs max). Start: 'random' = divider phase arbitrary at "
          "release (as designed); 'aligned' = divider started on a reference edge; '+ fast' = 4 × I_cp and R1 / 2 for "
          "the first 15 µs.\n")
    print("| Bank, rule | Corner | Channel (VCO GHz) | f at V_hold − target (MHz) | V_tune final (V) | Start | "
          "Lock detector (µs) | Settled 100 / 10 Hz (µs) | Wake (µs) | Slips |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for lab, nb, cdiv, rule in (("as designed", 7, 4, "highest"), ("8 bits, f / P", 8, 1, "nearest")):
        CFG.update(nb=nb, cdiv=cdiv)
        for cn in CORNERS:
            lo, hi = worst[(next(o[0] for o in OPTIONS if o[1] == nb and o[2] == cdiv), rule, cn)]
            for v, band, fv in (lo, hi, (0, "VHF", 3.4755e9)):
                for start, align, fast in (("random", False, 0.0), ("aligned", True, 0.0), ("aligned + fast", True, 15e-6)):
                    r = run(fv, band, cn, rule, align=align, fast=fast)
                    tl = f"{r['t_lock']*1e6:.1f}" if r["t_lock"] else "no lock"
                    wake = (r["t_cal"] + r["t_settle"]) * 1e6
                    lo_w, hi_w = WINDOW[cn]
                    flag = "" if lo_w <= r["v_final"] <= hi_w else " **outside**"
                    print(f"| {lab}, {rule} | {cn} | {fv/1e9:.4f} {band} | {r['df0']/1e6:+.1f} | {r['v_final']:.3f}{flag} | "
                          f"{start} | {tl} | {r['t_settle100']*1e6:.0f} / {r['t_settle']*1e6:.0f} | "
                          f"{wake:.0f}{'' if wake <= 150 else ' **over**'} | {r['slips']} |")
    CFG.update(nb=7, cdiv=4)
    print()


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    print("# P2.6 step 1 — behavioural closed loop with circuit data\n")
    print("Loop filter: " + ("as built in P2.5 (about 42 kHz, 35°)" if LF is LF_BUILT else
          f"corrected design, {BW/1e3:.0f} kHz, 55° actual") + ": " + ", ".join(
          f"{k} {v*1e12:.1f} pF" if k.startswith("C") else f"{k} {v/1e3:.1f} kΩ" for k, v in LF.items()) + "\n")
    worst = land_sweep()
    if "land" not in sys.argv[1:]:
        closed_loop(worst)


if __name__ == "__main__":
    main()
