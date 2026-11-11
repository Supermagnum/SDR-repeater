#!/usr/bin/env python3
"""D22 step 1c V_DS-matched VCO_BIAS DAC: scale + mono + DNL/INL + MC [SCH].

Requirements: code 31 = 4.0 mA ± 3 % at tt/ss/ff and −40/27/85 °C; never above
4.0 mA + 3 % (D12); |INL| ≤ 1 LSB; monotonic in mismatch Monte Carlo (N ≥ 20).

    python3 -u run_dac.py | tee out/dac/summary_dac.txt
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
I31_NOM = 4.0e-3
I31_TOL = 0.03
I31_MAX = I31_NOM * (1.0 + I31_TOL)


def read_i(raw, tag):
    d = rawread(raw).get()
    name = next(n for n in d.names if tag in n)
    return abs(float(np.real(d[name]).ravel()[0]))


def run_code(code, mos, temp=27, tag_extra="", mismatch=None, vtail=0.47):
    A.set_corner(mos, "cap_typ")
    body = A.dac_transistor_body(code, mismatch=mismatch, vtail=vtail)
    path = os.path.join(A.OUT, f"dac_{mos}_t{temp}_{code}{tag_extra}.sim")
    open(path, "w").write(
        S2.HEADER.format(title=f"dac_{code}") + body
        + "\ncontrol\n  abort always\n  options rawfile=\"binary\" "
        + f"temp={temp}\n"
        + "  save i(vt) i(vsense) v(xref) v(nbf) v(tail)\n  analysis op1 op\nendc\n"
    )
    S2.run(path)
    raw = os.path.join(A.OUT, "op1.raw")
    return read_i(raw, "vt"), read_i(raw, "vsense")


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
    print("# D22 step 1c V_DS-matched VCO_BIAS DAC [SCH]\n")
    print(
        f"I_master={A.I_MASTER*1e6:.2f} uA; PMOS units offset 19 + bits 1/2/4/8/16; "
        f"V_DS-matched 1:8 mirror (mr {A.W_MR} ng={A.NG_MR}, mt {A.W_MT} ng={A.NG_MT}); "
        f"V(tail)=0.47 V fixed. Target I_tail = 1.52 + code x 0.08 mA.\n"
    )

    mos_list = ("mos_tt",) if quick else ("mos_tt", "mos_ss", "mos_ff")
    temps = (27,) if quick else (-40, 27, 85)
    ok = True

    # --- Full-scale code 31 across MOS x temp ---
    print("## Code 31 full scale (limit 4.0 mA ± 3 %, never > 4.0+3 %) [SCH]\n")
    print("| MOS | T | I_ref (uA) | I_tail (mA) | err % | gate |")
    print("|---|---|---|---|---|---|")
    for mos in mos_list:
        for temp in temps:
            it, ir = run_code(31, mos, temp=temp, tag_extra="_fs")
            err = (it - I31_NOM) / I31_NOM * 100
            in_tol = abs(it - I31_NOM) <= I31_NOM * I31_TOL
            not_high = it <= I31_MAX
            gate = "PASS" if (in_tol and not_high) else "FAIL"
            if gate != "PASS":
                ok = False
            print(
                f"| {mos} | {temp} | {ir*1e6:.1f} | {it*1e3:.3f} | {err:+.2f} | {gate} |"
            )
    print()

    # --- Full code sweep mono + INL at tt/ss/ff @ 27 ---
    print("## Code sweep mono + DNL/INL @ 27 °C [SCH]\n")
    print("| MOS | code | I_ref (uA) | I_tail (mA) | ideal (mA) | err % | mono |")
    print("|---|---|---|---|---|---|---|")
    for mos in mos_list:
        prev = -1.0
        itails = []
        for code in range(32):
            it, ir = run_code(code, mos, temp=27)
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
        dnl_max = float(np.nanmax(np.abs(dnl)))
        inl_max = float(np.nanmax(np.abs(inl)))
        # Gate: |INL| ≤ 1 LSB (step 1c). |DNL| ≤ 0.5 reported; major-carry may exceed on ss.
        inl_ok = inl_max <= 1.0
        dnl_ok = dnl_max <= 0.5
        if not inl_ok:
            ok = False
        print(
            f"  {mos}: LSB={lsb*1e3:.4f} mA; |DNL|max={dnl_max:.3f} "
            f"({'PASS' if dnl_ok else 'NOTE'} ≤0.5); "
            f"|INL|max={inl_max:.3f} ({'PASS' if inl_ok else 'FAIL'} ≤1.0) `[SCH]`"
        )
    print()

    # --- Mismatch MC ---
    print("## Mismatch Monte Carlo (tt / 27 °C) [SCH]\n")
    A.set_corner("mos_tt", "cap_typ")
    rng = np.random.default_rng(22)
    N = 5 if quick else 20
    mono_fail = 0
    dnl_worst = 0.0
    inl_worst = 0.0
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
                it, _ = run_code(code, "mos_tt", temp=27, tag_extra=f"_mc{i}", mismatch=mm)
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
            inl_worst = max(inl_worst, float(np.nanmax(np.abs(inl))))
        n_ok += 1
        if (i + 1) % 5 == 0:
            print(f"  … {i+1}/{N}", flush=True)
    print(f"\nMC sweeps OK: {n_ok}/{N}; mono fails: {mono_fail}")
    print(f"Worst |DNL| across MC: {dnl_worst:.3f} LSB; worst |INL|: {inl_worst:.3f} LSB `[SCH]`")
    mc_ok = (mono_fail == 0) and (dnl_worst < 0.5) and (inl_worst <= 1.0)
    print("MC mono+DNL+INL:", "PASS" if mc_ok else "FAIL", "`[SCH]`")
    print("\nOverall DAC:", "PASS" if (ok and mc_ok) else "FAIL", "`[SCH]`")
    return 0 if (ok and mc_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
