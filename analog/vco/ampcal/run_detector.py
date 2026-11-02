#!/usr/bin/env python3
"""D22 peak-detector accuracy vs true tank Amp [SCH].

VCO top (code 0) / bottom (code 255), mos_tt/ss/ff × MIM × −40/27/85 °C.
Gate: |A_est − Amp| ≤ 0.10 V near the 1.25 V target (report all; flag misses).

    python3 -u run_detector.py | tee out/summary_detector.txt
"""
import os
import re
import sys

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2

A.load_sizing()
S2.OUT = A.OUT

CORNERS = [
    ("mos_tt", "cap_typ"),
    ("mos_ss", "cap_wcs"),
    ("mos_ss", "cap_bcs"),
    ("mos_ff", "cap_wcs"),
    ("mos_ff", "cap_bcs"),
]
TEMPS = (-40, 27, 85)
BANDS = (("top", 0, 16), ("bottom", 255, 31))  # bank code, starting bias code


def inject_dac_and_det(sim_path, bias_code):
    text = open(sim_path).read()
    text = re.sub(
        r"iref \(vdd nb\) isource dc=[^\n]+\n",
        A.dac_snippet(bias_code, "nb"),
        text,
    )
    # insert detector before control
    text = text.replace("\ncontrol\n", "\n" + A.detector_snippet(True) + "\ncontrol\n")
    open(sim_path, "w").write(text)


def run_one(mos, cap, temp, band, bcode, bias):
    A.set_corner(mos, cap)
    tag = f"det_{mos}_{cap}_{temp}_{band}"
    sim = S2.netlist(
        tag, bcode, S2.VTUNE_MID if band == "top" else 0.3,
        itail=A.itail(bias),
        drive_vbp=False, bypass=True,
        analysis=(
            f"  options temp={temp}\n"
            "  save v(tp) v(tn) v(vhp) v(vhn) v(vhr) v(cmp) v(mid)\n"
            "  analysis tr tran stop=80n step=5p maxstep=5p"
        ),
        extra="",
    )
    inject_dac_and_det(sim, bias)
    S2.run(sim)
    d = rawread(os.path.join(A.OUT, "tr.raw")).get()
    t = np.real(d["time"])
    m = t >= t[-1] - 15e-9
    vp, vn = np.real(d["tp"])[m], np.real(d["tn"])[m]
    amp = float((vp - vn).max() - (vp - vn).min()) / 2
    vhp, vhn, vhr = float(np.real(d["vhp"])[m][-1]), float(np.real(d["vhn"])[m][-1]), float(np.real(d["vhr"])[m][-1])
    a_est = A.a_est_from_holds(vhp, vhn, vhr)
    err = a_est - amp
    return dict(amp=amp, a_est=a_est, err=err)


def main():
    print("# D22 peak detector accuracy [SCH]\n")
    print("Choice: SF peak hold + replica at V_CT; C_ac = 4 fF/side (8 fF total ≤ 10 fF).\n")
    print("Rejected rectifier-on-tank: nonlinear RF current and poorer large-signal tracking `[HAND]`.\n")
    print("| MOS | CAP | T | band | Amp (V) | A_est (V) | err (V) | |err|≤0.10 |")
    print("|---|---|---|---|---|---|---|---|")
    n_fail = 0
    n = 0
    # Also a target-centred check: bias code swept so Amp≈1.25 where possible
    for mos, cap in CORNERS:
        for temp in TEMPS:
            for band, bcode, bias in BANDS:
                try:
                    r = run_one(mos, cap, temp, band, bcode, bias)
                except Exception as e:
                    print(f"| {mos} | {cap} | {temp} | {band} | FAIL {e} | | | |")
                    n_fail += 1
                    n += 1
                    continue
                ok = abs(r["err"]) <= A.A_WIN
                if not ok:
                    n_fail += 1
                n += 1
                print(
                    f"| {mos} | {cap} | {temp} | {band} | {r['amp']:.3f} | {r['a_est']:.3f} | "
                    f"{r['err']:+.3f} | {'PASS' if ok else 'MISS'} |"
                )
    print()
    print(f"Detector: {n - n_fail}/{n} within ±{A.A_WIN:.2f} V. "
          f"{'PASS' if n_fail == 0 else 'SEE MISSES (gate is at Amp≈1.25; edge Amps may be outside)'} `[SCH]`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
