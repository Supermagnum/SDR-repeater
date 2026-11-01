#!/usr/bin/env python3
"""Bound off-state bank-bypass switch noise vs bank-plate bias resistors.

Bank-omitted PSS (tail+var bypass present). For each of tt 3.65 GHz and ss 85 °C
4.20 GHz: pnoise with bank bias R noisy and noiseless → resistor contribution.
I_leak of one off bypass NMOS from DC at ff/125 °C and ss/85 °C.
Bound [HAND]: ρ = (2 q I_leak) / (4 k T / R) times the resistor PN contribution.
Pass if adding the bound raises L(1 MHz) by < 0.5 dB at both points.

    python3 -u run_bound_bank_switch.py | tee out/summary_bound_bank_switch.txt
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from vacask.rawfile import rawread

import run_step3 as s3
from compare import fundamental_amplitude

s3.OUT = "out"
GROUPS = ("tail", "var")
LIMIT_DB = 0.5
K = 1.380649e-23
Q = 1.602176634e-19
W, L, NG = "5u", "0.13u", 2
VDS_LIST = [0.05, 0.3, 0.6, 1.2]


def pnoise(code, vt, f0, itail, temp, tag, bank_r_noisy):
    vals = ", ".join(f"{x:.0f}" for x in s3.OFFS)
    flag = "nr" if bank_r_noisy else "qr"
    for opts, npts in (("reltol=1e-6 pss_tolscale=1e-3", 16000),
                       ("reltol=1e-6 pss_tolscale=1e-3", 8000)):
        sim = s3.S2.netlist(
            f"s3_bnd_{tag}_{flag}", code, vt, itail=itail, bypass=True,
            bypass_groups=GROUPS, bank_r_noisy=bank_r_noisy,
            analysis=(
                f"  options temp={temp} {opts} pss_minpts={npts}\n"
                '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
                f'  analysis pn pnoise oscillator=1 tper={1/f0:.6e} tstab=0 ic="ss" icmode="uic" '
                f'maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] outharm=1 '
                f"values=[{vals}] writepss=1"
            ),
            extra="iin (0 tp) isource dc=0\n",
        )
        try:
            s3.S2.run(sim)
            break
        except RuntimeError as e:
            print(f"  pss failed ({flag}, {npts}): "
                  f"{[x for x in str(e).splitlines() if x.strip()][-2:]}")
    else:
        return None
    pss = rawread(os.path.join(s3.OUT, "pn.pss.raw")).get()
    a, fp = fundamental_amplitude(pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
    pn = rawread(os.path.join(s3.OUT, "pn.raw")).get()
    off = np.real(pn["frequency"])
    l = 10 * np.log10(np.real(pn["onoise"]) / (a * a / 2))
    return dict(f=fp, amp=a, L={float(o): float(x) for o, x in zip(off, l)})


def _flow(d, src):
    for k in d.names:
        if k.startswith(src + ":") or k == f"i({src})":
            return float(np.real(np.asarray(d[k]).ravel()[0]))
    raise KeyError(d.names)


def ileak_dc(mos, temp, tag):
    """Max |I_D| of one off bank-bypass finger over V_DS list [SCH]."""
    hdr = (
        'ground 0\ninclude "sg13g2_vacask_common.lib"\n'
        f'include "cornerMOSlv.lib" section={mos}\n'
        'load "resistor.osdi"\nload "capacitor.osdi"\n'
        "model resistor resistor\nmodel capacitor capacitor\n"
        "model vsource vsource\nmodel isource isource\n"
    )
    ileaks = []
    for vds in VDS_LIST:
        name = f"bnd_ileak_{tag}_{vds:.2f}".replace(".", "p")
        text = hdr + f"""
vd (dx 0) vsource dc={vds}
vs (s 0) vsource dc=0
vg (g 0) vsource dc=0
vi (d dx) vsource dc=0
m (d g s 0) sg13_lv_nmos w={W} l={L} ng={NG}
control
  abort always
  options temp={temp} reltol=1e-6 rawfile="binary" strictsave=1
  save i(vi)
  analysis op1 op
endc
"""
        path = os.path.join(s3.OUT, name + ".sim")
        open(path, "w").write(text)
        log = os.path.join(s3.OUT, name + ".log")
        with open(log, "w") as fh:
            r = subprocess.run(["vacask", name + ".sim"], cwd=s3.OUT,
                               stdout=fh, stderr=subprocess.STDOUT)
        if r.returncode:
            raise RuntimeError(open(log).read()[-600:])
        d = rawread(os.path.join(s3.OUT, "op1.raw")).get()
        ileaks.append(abs(_flow(d, "vi")))
    return dict(mos=mos, temp=temp, vds=VDS_LIST, ileak=ileaks, ileak_max=max(ileaks))


def rho(ileak, T, R):
    """(2 q I) / (4 k T / R) = q I R / (2 k T)."""
    return (Q * ileak * R) / (2 * K * T)


def main():
    print("# Bound: off bank-bypass switch noise vs bank bias R [SCH]+[HAND]\n")
    print("Bank-omitted PSS (tail+var). ρ = (2q·I_leak)/(4kT/R) × resistor contribution.\n"
          f"Pass if ΔL(1 MHz) from the bound < {LIMIT_DB} dB at both points.\n")
    s3.load_sizing()
    R = s3.S2.R_BIAS

    print("## I_leak DC [SCH]\n")
    ff = ileak_dc("mos_ff", 125, "ff125")
    ss = ileak_dc("mos_ss", 85, "ss85")
    for lab, d in (("ff / 125 °C", ff), ("ss / 85 °C", ss)):
        print(f"{lab}: I_leak max = {d['ileak_max']:.3e} A "
              f"(V_DS={d['vds'][d['ileak'].index(d['ileak_max'])]:.2f} V)")
    print()

    cases = [
        ("tt_3.65", "mos_tt", "cap_typ", 27, 3.65e9, ff),
        ("ss85_4.20", "mos_ss", "cap_typ", 85, 4.20e9, ss),
    ]
    rows = []
    ok_all = True
    for tag, mos, cap, temp, f0, leak in cases:
        s3.set_corner(mos, cap)
        code = s3.code_for(f0, temp, f"{tag}_bnd")
        it = s3.itail_for(f0, s3.load_sizing()[1])
        T = temp + 273.15
        print(f"## {tag}: code {code}, I_tail {it*1e3:.2f} mA, T={temp} °C\n")
        print("  bank R noisy …")
        on = pnoise(code, s3.S2.VTUNE_MID, f0, it, temp, tag, True)
        print("  bank R quiet …")
        off = pnoise(code, s3.S2.VTUNE_MID, f0, it, temp, tag, False)
        if on is None or off is None:
            print("  STOP: PSS failed\n")
            ok_all = False
            rows.append(dict(tag=tag, ok=False))
            continue
        L1_on = on["L"][1e6]
        L1_off = off["L"][1e6]
        # Linear powers relative to carrier (1/Hz); difference = resistor contribution.
        p_on = 10 ** (L1_on / 10)
        p_off = 10 ** (L1_off / 10)
        p_r = max(0.0, p_on - p_off)
        r = rho(leak["ileak_max"], T, R)
        p_sw = r * p_r
        L1_bound = 10 * math.log10(p_on + p_sw)
        dL = L1_bound - L1_on
        frac_r = p_r / p_on if p_on > 0 else 0.0
        ok = dL < LIMIT_DB
        ok_all = ok_all and ok
        print(f"  L(1 MHz) bank-R noisy  = {L1_on:.2f} dBc/Hz  [SCH]")
        print(f"  L(1 MHz) bank-R quiet  = {L1_off:.2f} dBc/Hz  [SCH]")
        print(f"  resistor share         = {100*frac_r:.1f} % of total power")
        print(f"  I_leak                 = {leak['ileak_max']:.3e} A ({leak['mos']}/{leak['temp']}°C) [SCH]")
        print(f"  ρ = (2q I)/(4kT/R)     = {r:.3e}  [HAND]  (R={R/1e6:g} MΩ, T={T:.2f} K)")
        print(f"  L(1 MHz) + switch bound= {L1_bound:.2f} dBc/Hz  → Δ = {dL:+.3f} dB")
        print(f"  {'PASS' if ok else 'FAIL'} (limit {LIMIT_DB} dB)\n")
        rows.append(dict(
            tag=tag, code=code, itail=it, f=on["f"], amp=on["amp"],
            L_noisy=L1_on, L_quiet=L1_off, frac_r=frac_r,
            ileak=leak["ileak_max"], rho=r, L_bound=L1_bound, dL=dL, ok=ok,
        ))

    print("## Summary\n")
    print("| Point | L noisy | L quiet | ρ | ΔL bound | Verdict |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        if not r.get("L_noisy"):
            print(f"| {r['tag']} | — | — | — | — | PSS FAIL |")
        else:
            print(f"| {r['tag']} | {r['L_noisy']:.1f} | {r['L_quiet']:.1f} | "
                  f"{r['rho']:.2e} | {r['dL']:+.3f} dB | "
                  f"{'PASS' if r['ok'] else 'FAIL'} |")
    print()
    if ok_all:
        print(f"RESULT: PASS — switch-noise bound < {LIMIT_DB} dB at both points.")
    else:
        print(f"RESULT: STOP — bound ≥ {LIMIT_DB} dB or PSS failed.")
    json.dump(dict(R=R, ff=ff, ss=ss, rows=rows, pass_=ok_all),
              open(os.path.join(s3.OUT, "bound_bank_switch.json"), "w"), indent=2,
              default=float)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
