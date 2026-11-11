#!/usr/bin/env python3
"""P2.7.1c: band-step spot-check at ss/85 °C and ff/−40 °C [SCH].

Carries 63→64, 127→128, 191→192. Same pass band as tt: step 0.24–0.29 V of
V_tune and ratio 0.94–1.07× local mean (report; corners may sit outside).

    python3 -u run_spot_steps.py | tee out/summary_spot_steps.txt
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step2"))
import run_step2 as S2  # noqa: E402
import run_step3 as S3  # noqa: E402

S2.OUT = OUT
CARRIES = (64, 128, 192)
SPOTS = (("mos_ss", "cap_wcs", 85), ("mos_ff", "cap_bcs", -40))


def main():
    r, meas = S3.load_sizing()
    print("# P2.7.1c band-step spot-check [SCH]\n")
    print(f"Sizing from step2 range.json: LSB {S2.LSB_FF:.3f} fF, "
          f"cfix {S2.C_FIX_FF:.0f} fF, trim[7]={S2.TRIM[7]:.4f}\n")
    kv = {}
    for c in S2.CODES:
        a = meas.get((float(c), float(S2.VTUNE_WIN[0])))
        b = meas.get((float(c), float(S2.VTUNE_WIN[1])))
        if a and b:
            kv[c] = abs(b["f"] - a["f"]) / (S2.VTUNE_WIN[1] - S2.VTUNE_WIN[0])
    print("| corner | carry | Step (MHz) | ratio | KVCO (MHz/V) | "
          "Step in V_tune (V) |")
    print("|---|---|---|---|---|---|")
    for mos, cap, temp in SPOTS:
        S3.set_corner(mos, cap)
        it = 3.5e-3
        for c in CARRIES:
            c0, c1 = c - 1, c
            m0 = S3.tran(c0, S2.VTUNE_MID, f"sp_{mos}_{temp}_c{c0}", it, temp)
            m1 = S3.tran(c1, S2.VTUNE_MID, f"sp_{mos}_{temp}_c{c1}", it, temp)
            ma = S3.tran(max(0, c0 - 2), S2.VTUNE_MID,
                         f"sp_{mos}_{temp}_c{max(0, c0-2)}", it, temp)
            mb = S3.tran(min(S2.CMAX, c1 + 2), S2.VTUNE_MID,
                         f"sp_{mos}_{temp}_c{min(S2.CMAX, c1+2)}", it, temp)
            step = m0["f"] - m1["f"]
            mean = (ma["f"] - mb["f"]) / (min(S2.CMAX, c1 + 2) - max(0, c0 - 2))
            k = float(np.interp(c0, sorted(kv), [kv[x] for x in sorted(kv)]))
            print(f"| {mos}/{cap}/{temp} | {c0}→{c1} | {step/1e6:+.2f} | "
                  f"{step/mean:.2f} | {k/1e6:.1f} | {step/k:.3f} |")
    print("\nPass criteria quoted for tt 27 °C (0.24–0.29 V, 0.94–1.07×); "
          "corners are spot-checks only.")


if __name__ == "__main__":
    main()
