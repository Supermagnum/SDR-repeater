#!/usr/bin/env python3
"""D22 step 1 shared fragments: VCO_BIAS DAC and tank peak detector.

Detector choice: **source-follower peak hold + replica at V_CT**, AC-coupled **4 fF per
side (8 fF total ≤ 10 fF)**. Reason: gate C is set by the series C (not by a rectifier
junction on the tank); the replica cancels V_GS and common-mode; a MOS/diode rectifier
on the tank draws nonlinear RF current and tracks large swings worse at 3–4 GHz `[HAND]`.

Amp estimate from holds: A_est = (V_hp + V_hn) − 2·V_hr  (≈ differential peak).
Threshold for 1.25 V: compare A_est/2 to 0.625 V derived as 10 µA × 62.5 kΩ from the
bias-generator unit current (pll §12 V_REF family).

DAC (D22): I_tail = 1.52 mA + code × 0.08 mA via the existing 1:8 mirror
(I_ref = I_tail/8 = 190 µA + code × 10 µA).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step2"))
sys.path.insert(0, os.path.join(REPO, "analog", "pn-validation"))
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step1"))

import run_step2 as S2

os.makedirs(OUT, exist_ok=True)

I0 = 1.52e-3
LSB = 0.08e-3
A_TARGET = 1.25
A_HARD = 1.40
A_WIN = 0.10
C_AC = 4e-15          # per side; 8 fF total
HOLD_C = 200e-15

# PDK mismatch (P2.4 §9 / P2.5): σV_T 3.9 / 2.2 mV·µm, σβ 0.5 / 0.33 %·µm
SIG_VT_N, SIG_VT_P = 3.9e-3, 2.2e-3
SIG_B_N, SIG_B_P = 0.005, 0.0033


def itail(code):
    return I0 + int(code) * LSB


def load_sizing():
    import json
    r = json.load(open(os.path.join(REPO, "analog", "vco", "step2", "out", "range.json")))
    S2.OUT = OUT
    S2.LSB_FF = r["lsb"]
    S2.C_FIX_FF = r["cfix"]
    S2.NFING = r.get("nfing", 20)
    S2.NBITS = r.get("nbits", 8)
    S2.TRIM = list(r.get("trim", [1.0] * 8)) + [1.0] * 8
    return r


def set_corner(mos, cap):
    S2.HEADER = re.sub(
        r'include "cornerMOSlv.lib" section=\w+', f'include "cornerMOSlv.lib" section={mos}', S2.HEADER)
    S2.HEADER = re.sub(
        r'include "cornerMOShv.lib" section=\w+', f'include "cornerMOShv.lib" section={mos}', S2.HEADER)
    S2.HEADER = re.sub(
        r'include "cornerCAP.lib" section=\w+', f'include "cornerCAP.lib" section={cap}', S2.HEADER)


def dac_snippet(code, nb_node="nb"):
    """Ideal D22 current into the VCO bias diode (I_ref = I_tail/8).

    Transistor binary DAC is checked in run_dac.py (separate deck). VCO Amp/search
    runs use this ideal source so the code↔current law is exact while the mirror
    stays the existing mr/mt pair.
    """
    iref = itail(code) / 8.0
    return (
        f"// D22 ideal DAC code={code} I_tail={itail(code)*1e3:.3f} mA "
        f"I_ref={iref*1e6:.2f} µA\n"
        f"iref (vdd {nb_node}) isource dc={iref:.8g}\n"
    )


def dac_transistor_body(code):
    """Standalone PMOS binary DAC + VCO-style 1:8 mirror for DC characterisation."""
    bits = [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16)]
    n = [
        f"// transistor DAC code={code}\n",
        "vdd (vdd 0) vsource dc=1.2\n",
        "imaster (pbias vdd) isource dc=10u\n",
        "mm0 (pbias pbias vdd vdd) sg13_lv_pmos w=2u l=2u ng=1\n",
        "mfix (iref pbias vdd vdd) sg13_lv_pmos w=2u l=2u ng=19\n",
    ]
    for b, m in bits:
        on = (int(code) >> b) & 1
        g = "pbias" if on else "vdd"
        n.append(f"mdb{b} (iref {g} vdd vdd) sg13_lv_pmos w=2u l=2u ng={m}\n")
    n += [
        "mr (iref iref 0 0) sg13_lv_nmos w=20u l=4u ng=4\n",
        "mt (tail iref 0 0) sg13_lv_nmos w=160u l=4u ng=32\n",
        "vs (vdd tail) vsource dc=0\n",
        "vr (vdd iref) vsource dc=0\n",
    ]
    return "".join(n)


def detector_snippet(en=True):
    """SF peak holds on tp/tn + replica at ct. Saves vhp,vhn,vhr,cmp."""
    n = [
        f"// SF+replica peak detector; C_ac={C_AC*1e15:.0f}fF/side; en={int(en)}\n",
        f"xc_tp (tp gp) capacitor c={C_AC:.6g}\n",
        f"xc_tn (tn gn) capacitor c={C_AC:.6g}\n",
        "rgp (gp ct) resistor r=50k\n",
        "rgn (gn ct) resistor r=50k\n",
        "msfp (vdd gp sfp 0) sg13_lv_nmos w=2u l=0.13u ng=2\n",
        "msfn (vdd gn sfn 0) sg13_lv_nmos w=2u l=0.13u ng=2\n",
        "msfr (vdd ct sfr 0) sg13_lv_nmos w=2u l=0.13u ng=2\n",
        f"isfp (sfp 0) isource dc={'20u' if en else '1p'}\n",
        f"isfn (sfn 0) isource dc={'20u' if en else '1p'}\n",
        f"isfr (sfr 0) isource dc={'20u' if en else '1p'}\n",
        "mdp (sfp sfp vhp 0) sg13_lv_nmos w=1u l=0.13u ng=1\n",
        "mdn (sfn sfn vhn 0) sg13_lv_nmos w=1u l=0.13u ng=1\n",
        "mdr (sfr sfr vhr 0) sg13_lv_nmos w=1u l=0.13u ng=1\n",
        f"chp (vhp 0) capacitor c={HOLD_C:.6g}\n",
        f"chn (vhn 0) capacitor c={HOLD_C:.6g}\n",
        f"chr (vhr 0) capacitor c={HOLD_C:.6g}\n",
        # Comparator: mid = (vhp+vhn)/2 vs vhr + 0.625 V
        "rap (vhp mid) resistor r=200k\n",
        "ran (vhn mid) resistor r=200k\n",
        f"vof (vcref vhr) vsource dc={A_TARGET/2:.6g}\n",
        "mc1 (co mid tt 0) sg13_lv_nmos w=4u l=0.5u ng=2\n",
        "mc2 (co2 vcref tt 0) sg13_lv_nmos w=4u l=0.5u ng=2\n",
        "itt (tt 0) isource dc=20u\n",
        "rc1 (vdd co) resistor r=20k\n",
        "rc2 (vdd co2) resistor r=20k\n",
        "minv (cmp co 0 0) sg13_lv_nmos w=2u l=0.13u ng=1\n",
        "rpu (vdd cmp) resistor r=50k\n",
    ]
    return "".join(n)


def a_est_from_holds(vhp, vhn, vhr):
    return float(vhp + vhn - 2 * vhr)
