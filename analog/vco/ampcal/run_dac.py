#!/usr/bin/env python3
"""D22 step 1b unit-cell VCO_BIAS DAC: mono + DNL/INL + mismatch MC [SCH].

10 uA units, offset 19 + bits 1/2/4/8/16 -> I_tail = 1.52 mA + code x 0.08 mA.

    python3 -u run_dac.py | tee out/summary_dac.txt
    python3 -u run_dac.py quick
"""
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2

A.load_sizing()
A.OUT = os.path.join(A.OUT, "dac")
os.makedirs(A.OUT, exist_ok=True)
S2.OUT = A.OUT

W_U, L_U = 2.0, 2.0
SIG_U = A.SIG_VT_P / (W_U * L_U) ** 0.5


def read_i(raw, tag):
    d = rawread(raw).get()
    name = next(n for n in d.names if tag in n)
    return abs(float(np.real(d[name]).ravel()[0]))


def run_code(code, mos, tag_extra="", mismatch=None):
    A.set_corner(mos, "cap_typ")
    body = A.dac_transistor_body(code, mismatch=mismatch)
    path = os.path.join(A.OUT, f"dac_{mos}_{code}{tag_extra}.sim")
    open(path, "w").write(
        S2.HEADER.format(title=f"dac_{code}") + body
        + "\ncontrol\n  abort always\n  options rawfile=\"binary\"\n"
        + "  save i(vs) i(vr)\n  analysis op1 op\nendc\n"
    )
    S2.run(path)
    raw = os.path.join(A.OUT, "op1.raw")
    return read_i(raw, "vs"), read_i(raw, "vr")


def dnl_inl(i_tail):
    steps = np.diff(i_tail)
    lsb = float(np.mean(steps))
    if abs(lsb) < 1e-12:
        return steps * np.nan, steps * np.nan, lsb
    dnl = steps / lsb - 1.0
    inl = np.cumsum(dnl)
    return dnl, inl, lsb


def main():
    quick = "quick" in sys.argv
    print("# D22 step 1b unit-cell VCO_BIAS DAC [SCH]\n")
    print(
        "10 uA PMOS units: offset 19 + bits 1/2/4/8/16 into 1:8 mirror "
        "(series PMOS switches, gate 0 = on) -> "
        "I_tail = 1.52 mA + code x 0.08 mA.\n"
    )
    print("| MOS | code | I_ref (uA) | I_tail (mA) | ideal (mA) | err % | mono |")
    print("|---|---|---|---|---|---|---|")
    ok = True
    mos_list = ("mos_tt",) if quick else ("mos_tt", "mos_ss", "mos_ff")
    for mos in mos_list:
        prev = -1.0
        itails = []
        for code in range(32):
            it, ir = run_code(code, mos)
            ideal = A.itail(code)
            err = (it - ideal) / ideal * 100
            mono = it > prev + 1e-7
            if not mono:
                ok = False
            itails.append(it)
            print(
                f"| {mos} | {code} | {ir*1e6:.1f} | {it*1e3:.3f} | {ideal*1e3:.3f} | "
                f"{err:+.1f} | {'PASS' if mono else 'FAIL'} |"
            )
            prev = it
        dnl, inl, lsb = dnl_inl(np.array(itails))
        print(
            f"  {mos}: LSB={lsb*1e3:.4f} mA; DNL max|min|={np.nanmax(np.abs(dnl)):.3f} LSB; "
            f"INL max|min|={np.nanmax(np.abs(inl)):.3f} LSB `[SCH]`"
        )
        dnl_ok = np.nanmax(np.abs(dnl)) <= 0.5
        inl_max = float(np.nanmax(np.abs(inl)))
        print(f"  {mos}: DNL {'PASS' if dnl_ok else 'FAIL'} (|DNL|≤0.5); INL max={inl_max:.3f} LSB (Early compression expected)")
        if not dnl_ok:
            ok = False
    print()
    print("Nominal mono+DNL:", "PASS" if ok else "FAIL", "`[SCH]`")
    print("Note: |I_tail − ideal| grows to ~13–18 % at code 31 (Early / Vds mismatch); "
          "DNL still ≤ 0.5 LSB. Cascode deferred. `[SCH]`\n")

    print("## Mismatch Monte Carlo (tt) [SCH]\n")
    A.set_corner("mos_tt", "cap_typ")
    rng = np.random.default_rng(22)
    N = 5 if quick else 20
    mono_fail = 0
    dnl_worst = 0.0
    n_ok = 0
    for i in range(N):
        mm = {
            "m0": float(rng.normal(0, SIG_U)),
            "off": float(rng.normal(0, SIG_U / 19**0.5)),
            "b0": float(rng.normal(0, SIG_U)),
            "b1": float(rng.normal(0, SIG_U / 2**0.5)),
            "b2": float(rng.normal(0, SIG_U / 4**0.5)),
            "b3": float(rng.normal(0, SIG_U / 8**0.5)),
            "b4": float(rng.normal(0, SIG_U / 16**0.5)),
        }
        itails = []
        failed = False
        for code in range(32):
            try:
                it, _ = run_code(code, "mos_tt", tag_extra=f"_mc{i}", mismatch=mm)
                itails.append(it)
            except Exception as e:
                print(f"  MC[{i}] code {code}: OP FAIL ({e}) `[SCH]`")
                failed = True
                break
        if failed or len(itails) < 32:
            mono_fail += 1
            continue
        itails = np.array(itails)
        if np.any(np.diff(itails) <= 0):
            mono_fail += 1
        dnl, inl, lsb = dnl_inl(itails)
        if lsb == lsb and abs(lsb) > 1e-12:
            dnl_worst = max(dnl_worst, float(np.nanmax(np.abs(dnl))))
        n_ok += 1
        if (i + 1) % 5 == 0:
            print(f"  … {i+1}/{N}", flush=True)
    print(f"\nMC sweeps OK: {n_ok}/{N}; mono fails: {mono_fail}")
    print(f"Worst |DNL| across MC: {dnl_worst:.3f} LSB `[SCH]`")
    mc_ok = (mono_fail == 0) and (dnl_worst < 0.5)
    print("MC mono+DNL:", "PASS" if mc_ok else "FAIL", "`[SCH]`")
    return 0 if (ok and mc_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
