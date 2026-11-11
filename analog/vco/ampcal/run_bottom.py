#!/usr/bin/env python3
"""D22 step 1c: bottom-band Amp at code 31 with real V_DS-matched DAC [SCH].

Compare vs LO chain minimum (0.54 V differential; 0.66 V at ss −40 °C)
from spec/lo-divider-topology.md §9.
"""
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2

A.load_sizing()
OUT = os.path.join(A.HERE, "out", "bottom")
os.makedirs(OUT, exist_ok=True)
S2.OUT = OUT

CORNERS = [
    ("mos_tt", "cap_typ"),
    ("mos_ss", "cap_wcs"),
    ("mos_ss", "cap_bcs"),
    ("mos_ff", "cap_wcs"),
    ("mos_ff", "cap_bcs"),
]
TEMPS = (-40, 27, 85)
LO_MIN = 0.54
LO_MIN_SS_M40 = 0.66


def measure(mos, cap, temp):
    A.set_corner(mos, cap)
    tag = f"bot_{mos}_{cap}_{temp}"
    sim = S2.netlist(
        tag, 255, 0.3, itail=A.itail(31), bypass=True, drive_vbp=False,
        bypass_groups=("tail",),
        analysis=(
            f"  options temp={temp}\n"
            "  save v(tp) v(tn) v(tail)\n"
            "  analysis tr tran stop=80n step=20p maxstep=20p"
        ),
    )
    A.inject_dac_det(sim, 31, det=False)
    text = open(sim).read()
    text = text.replace(
        "vbptailtie (vbp_tail 0) vsource dc=0",
        "vbptailtie (vbp_tail 0) vsource dc=1.2",
    )
    open(sim, "w").write(text)
    S2.run(sim)
    d = rawread(os.path.join(OUT, "tr.raw")).get()
    t = np.real(d["time"])
    m = t >= t[-1] - 20e-9
    v = np.real(d["tp"])[m] - np.real(d["tn"])[m]
    amp = float(v.max() - v.min()) / 2
    vt = float(np.mean(np.real(d["tail"])[m]))
    return amp, vt


def lo_floor(mos, temp):
    if mos == "mos_ss" and temp == -40:
        return LO_MIN_SS_M40
    return LO_MIN


def main():
    quick = "quick" in sys.argv
    corners = [("mos_tt", "cap_typ")] if quick else CORNERS
    temps = (27,) if quick else TEMPS
    print("# D22 step 1c bottom-band Amp @ code 31 (real DAC) [SCH]\n")
    print(f"LO min = {LO_MIN} V (ss/−40: {LO_MIN_SS_M40} V) — lo-divider-topology.md §9.\n")
    print("| MOS | cap | T | Amp (V) | V(tail) | LO min | margin (V) |")
    print("|---|---|---|---|---|---|---|")
    worst = None
    for mos, cap in corners:
        for temp in temps:
            amp, vt = measure(mos, cap, temp)
            floor = lo_floor(mos, temp)
            margin = amp - floor
            print(
                f"| {mos} | {cap} | {temp} | {amp:.4f} | {vt:.4f} | {floor:.2f} | "
                f"{margin:+.4f} |"
            )
            if worst is None or margin < worst[0]:
                worst = (margin, mos, cap, temp, amp, floor)
    print(
        f"\nWorst margin: {worst[0]:+.4f} V at {worst[1]}/{worst[2]}/{worst[3]} "
        f"(Amp={worst[4]:.4f}, LO min={worst[5]:.2f}) `[SCH]`"
    )
    print("vs LO:", "PASS" if worst[0] >= 0 else "FAIL", "`[SCH]`")
    return 0 if worst[0] >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
