#!/usr/bin/env python3
"""P2.7.2b — ideal cbf vs PDK rfcmim 50 pF: VCO PN + swing [SCH].

Pass: |ΔL| < 0.1 dB at 100 kHz and 1 MHz; |Δamp|/amp < 2 %.

    python3 -u run_mim_vs_ideal.py | tee out/summary_mim_vs_ideal.txt
"""
from __future__ import annotations

import os
import sys

import numpy as np

import run_d9_mos_vs_mim as R
import run_step3 as S3

PASS_DB = 0.1
PASS_SWING = 0.02  # relative


def main():
    print("# P2.7.2b — cbf ideal vs rfcmim 50 pF [SCH]\n")
    print("Device: rfcmim W=L=182.574 µm (cmim PCell clamps; side≥7 µm → rfcmim) "
          "[PDK/TOOL]. Pass |ΔL|<0.1 dB, |Δamp|/amp<2 %.\n")
    S3.load_sizing()
    code, vt, f0, itail, temp = 91, R.S2.VTUNE_MID, 3.65e9, 4.0e-3, 27.0
    Ls = {}
    for kind in ("ideal", "mim"):
        print(f"  running pnoise kind={kind} …", flush=True)
        r = R.pnoise_kind(kind, code, vt, f0, itail, temp)
        Ls[kind] = r
        if r:
            parts = " ".join(f"L({o/1e3:.0f}k)={r['L'][o]:.2f}" for o in R.OFFS)
            print(f"  {kind}: f={r['f']/1e9:.3f} GHz amp={r['amp']:.3f} {parts}",
                  flush=True)
        else:
            print(f"  {kind}: FAILED", flush=True)

    print("\n| Offset | L ideal | L rfcmim | Δ |")
    print("|---|---|---|---|")
    ok = True
    if Ls.get("ideal") and Ls.get("mim"):
        for o in R.OFFS:
            a, b = Ls["ideal"]["L"][o], Ls["mim"]["L"][o]
            d = b - a
            print(f"| {o/1e3:.0f} kHz | {a:.2f} | {b:.2f} | {d:+.3f} dB |")
            if abs(d) >= PASS_DB:
                ok = False
        a0, a1 = Ls["ideal"]["amp"], Ls["mim"]["amp"]
        rel = (a1 - a0) / a0
        print(f"\nSwing: ideal {a0:.3f} V → rfcmim {a1:.3f} V "
              f"({rel*100:+.2f} %) [SCH]")
        if abs(rel) >= PASS_SWING:
            ok = False
            print("Swing PASS: FAIL")
        else:
            print("Swing PASS: PASS")
        print(f"\nOverall pass: {'PASS' if ok else 'FAIL'}\n")
    else:
        ok = False
        print("\nOverall pass: FAIL (pnoise incomplete)\n")
    open(os.path.join(R.OUT, "mim_vs_ideal_pass.flag"), "w").write(
        "PASS\n" if ok else "FAIL\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
