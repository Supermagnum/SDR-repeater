#!/usr/bin/env python3
"""Minimal VACASK PSS abort: fewest off bank bias-bypass fingers that break PSS.

Full P2.3 VCO at tt ~4.20 GHz. Adds off bypass NMOS (w=5u l=0.13u ng=2, V_GS=0)
across bank bias R on bits 0..k-1; finds smallest k that fails. Archives the
failing .sim/.log under out/repro_pss/.

    python3 -u repro_pss_bank_bypass.py | tee out/summary_repro_pss_bank_bypass.txt
"""
import os
import shutil
import sys

import run_step3 as s3

s3.OUT = "out"
REPRO = os.path.join(s3.OUT, "repro_pss")
F0 = 4.20e9
TEMP = 27
ORIG = None


def make_bypass(n_bits):
    def fn(nbits=None, groups=("bank",), bank_mode="mos"):
        lines = [f"// repro: off bank bypass on bits 0..{n_bits - 1}\n"]
        for k in range(n_bits):
            lines.append(
                f"mbp_rba{k} (a{k} vbp bb{k} 0) sg13_lv_nmos w=5u l=0.13u ng=2\n"
                f"mbp_rbb{k} (b{k} vbp bb{k} 0) sg13_lv_nmos w=5u l=0.13u ng=2\n"
            )
        return "".join(lines)
    return fn


def try_pss(tag, n_bypass, code, itail):
    if n_bypass <= 0:
        s3.S2.bias_bypass_switches = ORIG
        bypass, groups = False, ()
    else:
        s3.S2.bias_bypass_switches = make_bypass(n_bypass)
        bypass, groups = True, ("bank",)
    analysis = (
        f"  options temp={TEMP} reltol=1e-6 pss_tolscale=1e-3 pss_minpts=8000\n"
        '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
        f'  analysis pn pnoise oscillator=1 tper={1/F0:.6e} tstab=0 ic="ss" icmode="uic" '
        f'maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] outharm=1 values=[1e6] writepss=1'
    )
    name = f"repro_{tag}"
    sim = s3.S2.netlist(
        name, code=code, vtune=s3.S2.VTUNE_MID, itail=itail,
        bypass=bypass, bypass_groups=groups,
        analysis=analysis, extra="iin (0 tp) isource dc=0\n",
    )
    ok, err = True, []
    try:
        s3.S2.run(sim)
    except RuntimeError as e:
        ok = False
        err = [x for x in str(e).splitlines() if x.strip()]
    log = os.path.join(s3.OUT, name + ".log")
    lines = open(log).read().splitlines() if os.path.exists(log) else []
    vacask = [ln for ln in lines
              if any(k in ln for k in ("PSS", "abort", "fail", "iterations", "Timestep"))]
    os.makedirs(REPRO, exist_ok=True)
    for ext in (".sim", ".log"):
        src = os.path.join(s3.OUT, name + ext)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(REPRO, name + ext))
    return ok, vacask, err


def main():
    global ORIG
    print("# Minimal PSS abort: fewest off bank bias-bypass fingers\n")
    s3.load_sizing()
    ORIG = s3.S2.bias_bypass_switches
    s3.set_corner("mos_tt", "cap_typ")
    code = s3.code_for(F0, TEMP, "repro_c")
    it = s3.itail_for(F0, s3.load_sizing()[1])
    nbits = s3.S2.NBITS
    print(f"Netlist: full P2.3 VCO, code {code}, I_tail {it*1e3:.2f} mA, tt 27 °C, ~4.20 GHz.")
    print(f"Bypass: LV NMOS w=5u l=0.13u ng=2, V_GS=0, on bits 0..k-1 (of {nbits}).\n")

    print("## nobypass (k=0)\n")
    ok0, v0, e0 = try_pss("nobypass", 0, code, it)
    print(f"PSS {'OK' if ok0 else 'FAIL'}")
    for ln in v0[-6:] or e0[-3:]:
        print(f"  {ln}")
    print()
    if not ok0:
        print("UNEXPECTED: baseline without bypass must pass.")
        s3.S2.bias_bypass_switches = ORIG
        return 1

    # Ascending k; stop at first FAIL (smallest repro).
    fail_k, fail_v = None, []
    for k in range(1, nbits + 1):
        print(f"## k={k} bank bits with off bypass\n")
        ok, vac, err = try_pss(f"k{k}", k, code, it)
        print(f"PSS {'OK' if ok else 'FAIL'}")
        for ln in vac[-6:] or err[-3:]:
            print(f"  {ln}")
        print()
        if not ok:
            fail_k, fail_v = k, vac
            break

    s3.S2.bias_bypass_switches = ORIG
    print("## Verdict\n")
    if fail_k is None:
        print("UNEXPECTED: even full bank bypass group passed.")
        return 1
    print(f"PASS as reproducer: PSS OK with k=0; first FAIL at k={fail_k} "
          f"({fail_k * 2} off NMOS fingers).")
    print("VACASK error text:")
    for ln in fail_v:
        if any(s in ln for s in ("PSS", "abort", "fail", "iterations")):
            print(f"  {ln}")
    print(f"\nArchived: {REPRO}/repro_nobypass.{{sim,log}}, repro_k{fail_k}.{{sim,log}}")
    # Keep stable names for the draft issue
    for ext in (".sim", ".log"):
        src = os.path.join(REPRO, f"repro_k{fail_k}{ext}")
        dst = os.path.join(REPRO, f"repro_bypass{ext}")
        if os.path.exists(src):
            shutil.copy(src, dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
