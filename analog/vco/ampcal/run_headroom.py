#!/usr/bin/env python3
"""D22 step 1c: Amp and V(tail) old diode mirror vs V_DS-matched [SCH].

Reports whether the new mirror raises the tail node enough to cost swing.
"""
import os
import re
import sys

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2

A.load_sizing()
OUT = os.path.join(A.HERE, "out", "headroom")
os.makedirs(OUT, exist_ok=True)
S2.OUT = OUT


def amp_from(d):
    t = np.real(d["time"])
    m = t >= t[-1] - 20e-9
    v = np.real(d["tp"])[m] - np.real(d["tn"])[m]
    return float(v.max() - v.min()) / 2


def mean_tail(d):
    t = np.real(d["time"])
    m = t >= t[-1] - 20e-9
    return float(np.mean(np.real(d["tail"])[m]))


def run_case(tag, bias_code, vds_match):
    A.set_corner("mos_tt", "cap_typ")
    it = A.itail(bias_code)
    sim = S2.netlist(
        tag, 0, S2.VTUNE_MID, itail=it, bypass=True, drive_vbp=False,
        bypass_groups=("tail",),
        analysis=(
            "  options temp=27\n"
            "  save v(tp) v(tn) v(tail) v(nbf) v(nb)\n"
            "  analysis tr tran stop=60n step=20p maxstep=20p"
        ),
    )
    text = open(sim).read()
    text = text.replace(
        "vbptailtie (vbp_tail 0) vsource dc=0",
        "vbptailtie (vbp_tail 0) vsource dc=1.2",
    )
    text = text.replace("vbptie (vbp 0) vsource dc=0", "vbptie (vbp 0) vsource dc=1.2")
    if vds_match:
        # Replace diode bias with V_DS-matched + ideal I_ref at I_tail/8
        iref = it / 8
        block = (
            f"idac (vdd xraw) isource dc={iref:.6g}\n"
            + A.mirror_vds_match_snippet()
        )
        text2, n = A._BIAS_BLOCK_RE.subn(block, text, count=1)
        assert n == 1, "bias block not found"
        text = text2
    open(sim, "w").write(text)
    S2.run(sim)
    d = rawread(os.path.join(OUT, "tr.raw")).get()
    return amp_from(d), mean_tail(d)


def main():
    print("# D22 step 1c headroom: Amp / V(tail) old vs V_DS-matched [SCH]\n")
    print("tt / typ / 27 °C, top bank, bias code 20 (I_tail=3.12 mA ideal).\n")
    a_old, vt_old = run_case("old_diode", 20, False)
    a_new, vt_new = run_case("vds_match", 20, True)
    print(f"| mirror | Amp (V) | V(tail) mean (V) |")
    print(f"|---|---|---|")
    print(f"| old diode 1:8 | {a_old:.4f} | {vt_old:.4f} |")
    print(f"| V_DS-matched  | {a_new:.4f} | {vt_new:.4f} |")
    print(f"\nDelta Amp = {a_new - a_old:+.4f} V; Delta V(tail) = {vt_new - vt_old:+.4f} V `[SCH]`")
    # Also code 31
    a31o, vt31o = run_case("old_c31", 31, False)
    a31n, vt31n = run_case("vds_c31", 31, True)
    print(f"\nCode 31: old Amp={a31o:.4f} V_tail={vt31o:.4f}; "
          f"new Amp={a31n:.4f} V_tail={vt31n:.4f} `[SCH]`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
