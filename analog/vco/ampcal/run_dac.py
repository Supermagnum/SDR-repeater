#!/usr/bin/env python3
"""D22 VCO_BIAS DAC: ideal law + transistor mono/scale [SCH].

1) Ideal I_tail = 1.52 mA + code×0.08 mA through the VCO 1:8 mirror (exact law).
2) Transistor PMOS DAC: monotonicity of I_ref and of I_tail; report I_tail/I_ref.

    python3 -u run_dac.py | tee out/summary_dac.txt
"""
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2

A.load_sizing()
S2.OUT = A.OUT


def read_i(raw, tag):
    d = rawread(raw).get()
    name = next(n for n in d.names if tag in n)
    return abs(float(np.real(d[name]).ravel()[0]))


def run_ideal(code, mos):
    A.set_corner(mos, "cap_typ")
    body = (
        "vdd (vdd 0) vsource dc=1.2\n"
        + A.dac_snippet(code, "iref")
        + "mr (iref iref 0 0) sg13_lv_nmos w=20u l=4u ng=4\n"
        + "mt (tail iref 0 0) sg13_lv_nmos w=160u l=4u ng=32\n"
        + "vs (vdd tail) vsource dc=0\n"
    )
    path = os.path.join(A.OUT, f"dac_id_{mos}_{code}.sim")
    open(path, "w").write(
        S2.HEADER.format(title=f"dac_id_{code}") + body
        + "\ncontrol\n  abort always\n  options rawfile=\"binary\"\n"
        + "  save i(vs)\n  analysis op1 op\nendc\n"
    )
    S2.run(path)
    return read_i(os.path.join(A.OUT, "op1.raw"), "vs")


def run_xistor(code, mos):
    A.set_corner(mos, "cap_typ")
    path = os.path.join(A.OUT, f"dac_x_{mos}_{code}.sim")
    open(path, "w").write(
        S2.HEADER.format(title=f"dac_x_{code}") + A.dac_transistor_body(code)
        + "\ncontrol\n  abort always\n  options rawfile=\"binary\"\n"
        + "  save i(vs) i(vr)\n  analysis op1 op\nendc\n"
    )
    S2.run(path)
    raw = os.path.join(A.OUT, "op1.raw")
    return read_i(raw, "vs"), read_i(raw, "vr")


def main():
    print("# D22 VCO_BIAS DAC [SCH]\n")
    print("## Ideal law through VCO mirror (I_ref = I_tail/8)\n")
    print("| MOS | code | I_tail (mA) | ideal (mA) | err % | mono |")
    print("|---|---|---|---|---|---|")
    ok = True
    for mos in ("mos_tt", "mos_ss", "mos_ff"):
        prev = -1.0
        for code in range(32):
            i = run_ideal(code, mos)
            ideal = A.itail(code)
            err = (i - ideal) / ideal * 100
            mono = i > prev + 1e-7
            if (not mono) or abs(err) > 15:
                ok = False
            print(f"| {mos} | {code} | {i*1e3:.3f} | {ideal*1e3:.3f} | {err:+.1f} | "
                  f"{'PASS' if mono else 'FAIL'} |")
            prev = i
    print()
    print("Ideal DAC:", "PASS" if ok else "FAIL", "`[SCH]`\n")

    print("## Transistor PMOS DAC (ng-weighted) — mono + scale\n")
    print("| MOS | code | I_ref (µA) | I_tail (mA) | ratio | mono_ref | mono_tail |")
    print("|---|---|---|---|---|---|---|")
    xok = True
    for mos in ("mos_tt", "mos_ss", "mos_ff"):
        prev_r, prev_t = -1.0, -1.0
        for code in range(32):
            it, ir = run_xistor(code, mos)
            # vr senses current into iref from vdd — direction may flip
            ratio = it / ir if ir > 1e-9 else float("nan")
            mr = ir > prev_r + 1e-9
            mt = it > prev_t + 1e-9
            if not (mr and mt):
                xok = False
            print(f"| {mos} | {code} | {ir*1e6:.1f} | {it*1e3:.3f} | {ratio:.2f} | "
                  f"{'Y' if mr else 'N'} | {'Y' if mt else 'N'} |")
            prev_r, prev_t = ir, it
    print()
    print("Transistor DAC monotonicity:", "PASS" if xok else "FAIL (DNL — trim in step 2)", "`[SCH]`")
    print("Note: absolute I_tail vs D22 law uses the ideal source in VCO decks until the")
    print("PMOS unit is trimmed to the measured mirror ratio (~4–8×).")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
