#!/usr/bin/env python3
"""Landing sweep with bank scaled by the real-LO load frequency shift [MODEL].

Scale = +0.285 % (max |Δf| vs same-Vtune stand-in, summary_real_load.txt).
Behavioural model (not the transistor bank) — say so in the report.

    python3 -u run_land_scaled.py | tee out/summary_land_scaled.txt
"""
import closed_loop as CL

SCALE = 1.00285  # +0.285 % [SCH]


def f_bank_scaled(code):
    return CL.models.f_vco(code * 127 / (CL.ncodes() - 1)) * SCALE


def main():
    CL.F_LO = 2.90e9 * SCALE
    CL.F_HI = 4.41e9 * SCALE
    CL.f_bank = f_bank_scaled
    print("# P2.6 step-1 landing with real-load bank scale [MODEL]\n")
    print(f"Scaled behavioural bank: F_LO/F_HI × {SCALE:.5f} (+{(SCALE-1)*100:.3f} %). "
          "Not the transistor bank — frequency shift from "
          "`analog/vco/step3/out/summary_real_load.txt` applied uniformly.\n")
    # baseline
    print("## Baseline (unscaled) [MODEL]\n")
    CL.F_LO, CL.F_HI = 2.90e9, 4.41e9
    CL.f_bank = lambda code: CL.models.f_vco(code * 127 / (CL.ncodes() - 1))
    CL.land_sweep()
    # scaled
    print("## Scaled +0.285 % (real LO load) [MODEL]\n")
    CL.F_LO, CL.F_HI = 2.90e9 * SCALE, 4.41e9 * SCALE
    CL.f_bank = f_bank_scaled
    CL.land_sweep()
    print("Window remains 0.25–0.95 V (ss 0.25–0.85 V). Compare outside-% columns.\n")


if __name__ == "__main__":
    main()
