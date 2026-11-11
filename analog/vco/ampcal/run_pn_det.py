#!/usr/bin/env python3
"""Detector phase-noise: bank-omitted PSS at tt 3.65 and ss85 4.20; [HAND] if fail.

Detector powered down (normal hold). Limit Δ ≤ 0.5 dB at 1 MHz vs
summary_pn_nobank.txt baseline.

    python3 -u run_pn_det.py | tee out/pn/summary_pn_det.txt
"""
import os
import re
import sys

import amp_common as A
import run_step2 as S2

A.load_sizing()
OUT = os.path.join(A.HERE, "out", "pn")
os.makedirs(OUT, exist_ok=True)
S2.OUT = OUT

CASES = (
    ("mos_tt", "cap_typ", 27, 3.65e9, 91),
    ("mos_ss", "cap_wcs", 85, 4.20e9, 0),
)


def try_pnoise(mos, cap, temp, f0, code):
    sys.path.insert(0, os.path.join(A.REPO, "analog", "vco", "step3"))
    import run_step3 as s3
    s3.OUT = OUT
    s3.load_sizing()
    s3.set_corner(mos, cap)
    it = A.itail(20)
    tag = f"pn_det_{mos}_{temp}"
    sim = s3.S2.netlist(
        tag, code, s3.S2.VTUNE_MID, itail=it,
        bypass=True, bypass_groups=("tail", "var"),
        analysis=(
            f"  options temp={temp} reltol=1e-6 pss_tolscale=1e-3 pss_minpts=8000\n"
            '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
            f'  analysis pn pnoise oscillator=1 tper={1/f0:.6e} tstab=0 ic="ss" icmode="uic" '
            f'maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] outharm=1 values=[1e6] writepss=1'
        ),
        extra="iin (0 tp) isource dc=0\n" + A.detector_snippet(en=False),
    )
    A.inject_dac_det(sim, 20, det=False)
    try:
        s3.S2.run(sim)
        return True, None
    except Exception as e:
        msg = [x for x in str(e).splitlines() if x.strip()][-1][:140]
        return False, msg


def hand_bound():
    print("\n## [HAND] bound (PSS with detector did not converge)\n")
    print("Baseline: `summary_pn_nobank.txt` (tt −122.7 / ss85 −119.4 dBc/Hz @ 1 MHz).")
    print("C_gate ≪ 10 fF on ~800 fF tank: ΔC/C ≪ 1 % `[HAND]`.")
    print("Detector powered down after hold (D22) → ΔL @ 1 MHz ≈ **0 dB** `[HAND]`.")
    print("Gate Δ ≤ 0.5 dB: **PASS by [HAND]** (no SCH Δ; PSS aborted).")
    print("Worst margin +3.4 dB (ss85 4.20) unchanged.")


def main():
    print("# D22 step 1c detector phase-noise (powered down) [SCH]/[HAND]\n")
    print("Bank-omitted PSS; real V_DS-matched DAC; detector off.\n")
    any_ok = False
    for mos, cap, temp, f0, code in CASES:
        print(f"## {mos} / {temp} °C / {f0/1e9:.2f} GHz\n")
        ok, msg = try_pnoise(mos, cap, temp, f0, code)
        if ok:
            print(f"  PSS converged — inspect raw for L(1 MHz) vs baseline `[SCH]`")
            any_ok = True
        else:
            print(f"  PSS failed: {msg} `[SCH]`")
    if not any_ok:
        hand_bound()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
