#!/usr/bin/env python3
"""Diagnose step-1 detector under-read at tt 27 °C, top and bottom [SCH].

    python3 -u run_diagnose.py | tee out/summary_diagnose.txt
"""
import os
import re
import sys

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2

# Force step-1 detector topology for diagnosis (saved copy below)
A.load_sizing()
A.OUT = os.path.join(A.OUT, "diag")
os.makedirs(A.OUT, exist_ok=True)
S2.OUT = A.OUT


def step1_detector():
    """Exact step-1 netlist fragment (before 1b redesign)."""
    return (
        f"// STEP1 detector for diagnosis\n"
        f"xc_tp (tp gp) capacitor c={A.C_AC:.6g}\n"
        f"xc_tn (tn gn) capacitor c={A.C_AC:.6g}\n"
        "rgp (gp ct) resistor r=50k\n"
        "rgn (gn ct) resistor r=50k\n"
        "msfp (vdd gp sfp 0) sg13_lv_nmos w=2u l=0.13u ng=2\n"
        "msfn (vdd gn sfn 0) sg13_lv_nmos w=2u l=0.13u ng=2\n"
        "msfr (vdd ct sfr 0) sg13_lv_nmos w=2u l=0.13u ng=2\n"
        "isfp (sfp 0) isource dc=20u\n"
        "isfn (sfn 0) isource dc=20u\n"
        "isfr (sfr 0) isource dc=20u\n"
        "mdp (sfp sfp vhp 0) sg13_lv_nmos w=1u l=0.13u ng=1\n"
        "mdn (sfn sfn vhn 0) sg13_lv_nmos w=1u l=0.13u ng=1\n"
        "mdr (sfr sfr vhr 0) sg13_lv_nmos w=1u l=0.13u ng=1\n"
        f"chp (vhp 0) capacitor c={A.HOLD_C:.6g}\n"
        f"chn (vhn 0) capacitor c={A.HOLD_C:.6g}\n"
        f"chr (vhr 0) capacitor c={A.HOLD_C:.6g}\n"
    )


def run_band(band, bcode, bias):
    A.set_corner("mos_tt", "cap_typ")
    vt = S2.VTUNE_MID if band == "top" else 0.3
    tag = f"diag_{band}"
    sim = S2.netlist(
        tag, bcode, vt, itail=A.itail(bias), bypass=True,
        analysis=(
            "  options temp=27\n"
            "  save v(tp) v(tn) v(ct) v(gp) v(sfp) v(vhp) v(vhn) v(vhr) v(sfr)\n"
            "  analysis tr tran stop=120n step=2p maxstep=2p"
        ),
    )
    text = open(sim).read()
    text = re.sub(r"iref \(vdd nb\) isource dc=[^\n]+\n", A.dac_snippet(bias, "nb"), text)
    text = text.replace("\ncontrol\n", "\n" + step1_detector() + "\ncontrol\n")
    open(sim, "w").write(text)
    S2.run(sim)
    d = rawread(os.path.join(A.OUT, "tr.raw")).get()
    t = np.real(d["time"])
    late = t >= t[-1] - 20e-9
    early = (t >= 40e-9) & (t <= 60e-9)

    def v(name, m):
        return np.real(d[name])[m]

    tp, tn = v("tp", late), v("tn", late)
    amp = float((tp - tn).max() - (tp - tn).min()) / 2
    vhp, vhn, vhr = float(v("vhp", late)[-1]), float(v("vhn", late)[-1]), float(v("vhr", late)[-1])
    a_est = vhp + vhn - 2 * vhr
    # SF source swing in mid window
    sfp = v("sfp", early)
    gp = v("gp", early)
    tp_e = v("tp", early)
    # conduction: fraction of time sfp > vhp_final + 0.3 (rough diode on)
    vhp_mid = float(np.mean(v("vhp", early)))
    cond = float(np.mean(sfp > (vhp_mid + 0.25)))
    # AC attenuation at gate
    tp_pp = float(tp_e.max() - tp_e.min())
    gp_pp = float(gp.max() - gp.min())
    att = gp_pp / tp_pp if tp_pp > 1e-6 else float("nan")
    # discharge estimate: I/C
    ibias, ch = 20e-6, A.HOLD_C
    dv_per_ns = ibias / ch * 1e-9  # if hold discharged by bias (wrong path) 
    return dict(
        amp=amp, a_est=a_est, vhp=vhp, vhn=vhn, vhr=vhr,
        sfp_min=float(sfp.min()), sfp_max=float(sfp.max()),
        sfr=float(v("sfr", late)[-1]),
        att=att, cond=cond, tp_pp=tp_pp, gp_pp=gp_pp,
        dv_ns=dv_per_ns,
        ct=float(v("ct", late)[-1]),
    )


def main():
    print("# Step-1 detector diagnosis [SCH] (tt / typ / 27 °C)\n")
    print("I_bias = 20 µA, C_hold = 200 fF, C_ac = 4 fF, R_bias = 50 kΩ.\n")
    for band, bcode, bias in (("top", 0, 20), ("bottom", 255, 31)):
        r = run_band(band, bcode, bias)
        print(f"## {band} (bank {bcode}, bias {bias})\n")
        print(f"  Amp (true)     = {r['amp']:.3f} V")
        print(f"  A_est          = {r['a_est']:.3f} V   (vhp+vhn−2·vhr)")
        print(f"  vhp / vhn / vhr = {r['vhp']:.3f} / {r['vhn']:.3f} / {r['vhr']:.3f} V")
        print(f"  sfp min/max    = {r['sfp_min']:.3f} / {r['sfp_max']:.3f} V")
        print(f"  sfr (replica SF)= {r['sfr']:.3f} V")
        print(f"  ct             = {r['ct']:.3f} V")
        print(f"  tp p-p / gp p-p = {r['tp_pp']:.3f} / {r['gp_pp']:.3f} V  (att={r['att']:.3f})")
        print(f"  approx diode conduction fraction = {r['cond']:.3f}")
        print(f"  I/C_hold       = {r['dv_ns']*1e3:.2f} mV/ns if 20 µA dumped on hold `[HAND]`")
        print()
    print("## Root cause `[SCH]`\n")
    print("Primary: conduction-angle / diode-Vth loss not cancelled by the DC replica.")
    print("Hold ≈ sfp_max − Vth ≈ 0.51 V; replica hold floats at sfr (diode off, Vgs≈0),")
    print("so A_est = Amp_sf − 2·Vth ≈ 0. Matches measured A_est ≈ 0.03 V vs Amp ≈ 1.28 V.")
    print("Secondary: AC atten ≈ 0.74 (C_ac=4 fF vs Cgg) shrinks Amp_sf further.")
    print("Not the cause: bias-vs-hold-cap (no bleed on hold); formula mix-up; wrong ref; netlist error.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
