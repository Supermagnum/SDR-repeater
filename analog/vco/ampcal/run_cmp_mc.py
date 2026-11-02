#!/usr/bin/env python3
"""Comparator input-referred offset Monte Carlo for step-1b detector [SCH].

Trip sense: co - co2 crossing 0 (avoids broken single-ended cmp OP).
Pair: W=4 um L=0.5 um ng=2; sigmaVT = 3.9 mV.um / sqrt(W*L) as P2.4.

    python3 -u run_cmp_mc.py | tee out/summary_cmp_mc.txt
"""
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2

A.load_sizing()
A.OUT = os.path.join(A.OUT, "cmp")
os.makedirs(A.OUT, exist_ok=True)
S2.OUT = A.OUT
N = 40
W, L = 4.0, 0.5
SIG = A.SIG_VT_N / (W * L) ** 0.5


def op_diff(vip, vin, vos, tag):
    body = (
        f"vdd (vdd 0) vsource dc=1.2\n"
        f"vip (vip 0) vsource dc={vip:.6g}\n"
        f"vin (vin 0) vsource dc={vin:.6g}\n"
        f"vo1 (g1 vip) vsource dc={vos[0]:.6g}\n"
        f"vo2 (g2 vin) vsource dc={vos[1]:.6g}\n"
        f"mc1 (co g1 tt 0) sg13_lv_nmos w={W}u l={L}u ng=2\n"
        f"mc2 (co2 g2 tt 0) sg13_lv_nmos w={W}u l={L}u ng=2\n"
        "itt (tt 0) isource dc=20u\n"
        "rc1 (vdd co) resistor r=20k\n"
        "rc2 (vdd co2) resistor r=20k\n"
    )
    path = os.path.join(A.OUT, f"cmp_{tag}.sim")
    open(path, "w").write(
        S2.HEADER.format(title=f"cmp_{tag}") + body
        + "\ncontrol\n  abort always\n  options rawfile=\"binary\" temp=27\n"
        + "  save v(co) v(co2) v(tt)\n  analysis op1 op\nendc\n"
    )
    S2.run(path)
    d = rawread(os.path.join(A.OUT, "op1.raw")).get()
    return {
        "co": float(np.real(d["co"]).ravel()[0]),
        "co2": float(np.real(d["co2"]).ravel()[0]),
        "tt": float(np.real(d["tt"]).ravel()[0]),
        "diff": float(np.real(d["co"]).ravel()[0] - np.real(d["co2"]).ravel()[0]),
    }


def trip_offset(vos, tag):
    """Binary-search dv where co-co2 crosses 0. CM = 0.70 V."""
    cm = 0.70
    try:
        z = op_diff(cm, cm, vos, f"{tag}_z")
    except Exception as e:
        return float("nan"), f"OP fail at bal: {e}"
    if z["tt"] < 0.05:
        return float("nan"), f"tail collapsed tt={z['tt']:.3f} V (OP fail)"
    if z["co"] < 0.05 and z["co2"] < 0.05:
        return float("nan"), f"both loads collapsed co={z['co']:.3f}"
    lo, hi = -0.08, 0.08
    dlo = op_diff(cm + lo, cm, vos, f"{tag}_lo")["diff"]
    dhi = op_diff(cm + hi, cm, vos, f"{tag}_hi")["diff"]
    if dlo * dhi > 0:
        return float("nan"), f"no zero in ±80 mV (dlo={dlo:.4f} dhi={dhi:.4f})"
    for k in range(12):
        mid = 0.5 * (lo + hi)
        dm = op_diff(cm + mid, cm, vos, f"{tag}_m{k}")["diff"]
        if dlo * dm <= 0:
            hi, dhi = mid, dm
        else:
            lo, dlo = mid, dm
    return 0.5 * (lo + hi), "ok"


def main():
    print("# Comparator offset Monte Carlo (step 1b) [SCH]\n")
    print(f"N={N}, sigmaVT/device = {SIG*1e3:.2f} mV (W={W} um L={L} um ng=2).\n")
    print(
        f"Threshold at Amp/2 node: V_th = {A.v_th():.4f} V "
        f"(= {A.A_TARGET}/2 - V_LOSS={A.V_LOSS}) `[HAND]`.\n"
    )
    print("Trip sense: co − co2 = 0 (diff pair loads). `[SCH]`\n")
    A.set_corner("mos_tt", "cap_typ")
    rng = np.random.default_rng(22)
    offs = []
    n_fail = 0
    fail_reasons = []
    for i in range(N):
        vos = rng.normal(0, SIG, size=2)
        o, why = trip_offset(vos, f"mc{i}")
        if o == o:
            offs.append(o)
        else:
            n_fail += 1
            fail_reasons.append(why)
        if (i + 1) % 10 == 0:
            print(f"  … {i+1}/{N}", flush=True)
    offs = np.array(offs)
    print(f"\nSamples OK: {len(offs)}/{N}; OP/trip failures: {n_fail}")
    if fail_reasons:
        for r in sorted(set(fail_reasons))[:5]:
            print(f"  fail: {r}")
    if len(offs) < N // 2:
        print(
            "MC operating point FAILED for majority of samples — "
            "do not trust sigma; see reasons above. `[SCH]`"
        )
        print(
            "Fallback [HAND]: 3*sigma_device*sqrt(2) ≈ "
            f"{3*SIG*1.414*1e3:.1f} mV at Amp/2 → "
            f"{2*3*SIG*1.414*1e3:.1f} mV on Amp."
        )
        return 1
    print(
        f"Offset mean {offs.mean()*1e3:.2f} mV, sigma {offs.std()*1e3:.2f} mV, "
        f"|max| {np.max(np.abs(offs))*1e3:.2f} mV `[SCH]`"
    )
    sig_amp = 2 * offs.std()
    print(
        f"3sigma at Amp/2 = {3*offs.std()*1e3:.1f} mV → "
        f"Amp 3sigma ≈ {3*sig_amp*1e3:.1f} mV `[SCH]`"
    )
    ok = 3 * sig_amp < A.A_WIN
    print("MC vs ±0.10 V Amp window:", "PASS" if ok else "MISS", "`[SCH]`")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
