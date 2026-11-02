#!/usr/bin/env python3
"""D22 step 1b: differential max detector + unit-cell VCO_BIAS DAC.

Detector (redesign): two NMOS with gates on tp/tn, shared source = hold; replica
pair gates at ct. C_gate << 10 fF. V_sense = V_hold - V_rep ~= Amp/2 - V_loss.
Threshold = Amp_target/2 - V_LOSS (fixed design-time conduction-angle loss).

DAC: identical 10 uA PMOS unit cells — offset 19 + bits 1/2/4/8/16 — into the
VCO 1:8 mirror -> I_tail = 1.52 mA + code x 0.08 mA (D22). Series PMOS switches
(gate=0 on), same style as the P2.5 I_cp DAC.
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
# Step-1 topology constants (diagnosis only)
C_AC = 4e-15
HOLD_C = 200e-15
# Design-time conduction-angle loss at the Amp/2 node.
# Tuned at tt/27 top: Vsense=0.419, Amp/2=0.642 -> loss~0.223 V [SCH]
V_LOSS = 0.22
C_HOLD = 400e-15
I_DET = 4e-6          # few uA
# Gate devices: W=0.5u L=0.13 -> Cgg ~ 0.5-1 fF each; 2 on tank << 10 fF
W_DET = "0.5u"
L_DET = "0.13u"

SIG_VT_N, SIG_VT_P = 3.9e-3, 2.2e-3
SIG_B_N, SIG_B_P = 0.005, 0.0033


def itail(code):
    return I0 + int(code) * LSB


def v_th():
    """Comparator threshold at (hold - rep): Amp/2 - V_LOSS."""
    return A_TARGET / 2.0 - V_LOSS


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


def pm_units(m):
    """P2.5 unit-finger PMOS: m parallel 2/2 um fingers (w and ng both scale)."""
    return f"sg13_lv_pmos w={2 * m:g}u l=2u ng={m}"


def dac_snippet(code, nb_node="nb"):
    """Unit-cell PMOS DAC into VCO bias diode node (I_ref = I_tail/8).

    Master 10 uA; offset 19 + bits 1/2/4/8/16 of identical 2/2 um fingers
    (P2.5 pm() law). Series PMOS switches L=0.13u, gate 0 = on.
    """
    bits = [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16)]
    n = [
        f"// D22 unit-cell DAC code={code} I_tail={itail(code)*1e3:.3f} mA\n",
        "imaster (pbias 0) isource dc=10u\n",
        f"mm0 (pbias pbias vdd vdd) {pm_units(1)}\n",
        f"moff (xoff pbias vdd vdd) {pm_units(19)}\n",
        f"msoff ({nb_node} 0 xoff vdd) sg13_lv_pmos w=38u l=0.13u ng=1\n",
    ]
    for b, m in bits:
        on = (int(code) >> b) & 1
        gsw = "0" if on else "vdd"
        n.append(f"mdb{b} (xd{b} pbias vdd vdd) {pm_units(m)}\n")
        n.append(f"msw{b} ({nb_node} {gsw} xd{b} vdd) sg13_lv_pmos w={2 * m:g}u l=0.13u ng=1\n")
    return "".join(n)


def dac_transistor_body(code, mismatch=None):
    """Standalone DAC + VCO 1:8 mirror for DC / MC characterisation.

    I_ref sensed with series 0 V (xref -> iref). Never short iref to vdd.
    """
    bits = [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16)]
    n = ["vdd (vdd 0) vsource dc=1.2\n", "imaster (pbias 0) isource dc=10u\n"]
    if mismatch:
        n.append(f"vo_m0 (g_m0 pbias) vsource dc={mismatch.get('m0', 0):.6g}\n")
        n.append(f"mm0 (pbias g_m0 vdd vdd) {pm_units(1)}\n")
        n.append(f"vo_off (g_off pbias) vsource dc={mismatch.get('off', 0):.6g}\n")
        g_off = "g_off"
    else:
        n.append(f"mm0 (pbias pbias vdd vdd) {pm_units(1)}\n")
        g_off = "pbias"
    n.append(f"moff (xoff {g_off} vdd vdd) {pm_units(19)}\n")
    n.append("msoff (xref 0 xoff vdd) sg13_lv_pmos w=38u l=0.13u ng=1\n")
    for b, m in bits:
        on = (int(code) >> b) & 1
        gsw = "0" if on else "vdd"
        if mismatch:
            dv = mismatch.get(f"b{b}", 0.0)
            n.append(f"vo_b{b} (g_b{b} pbias) vsource dc={dv:.6g}\n")
            gg = f"g_b{b}"
        else:
            gg = "pbias"
        n.append(f"mdb{b} (xd{b} {gg} vdd vdd) {pm_units(m)}\n")
        n.append(f"msw{b} (xref {gsw} xd{b} vdd) sg13_lv_pmos w={2 * m:g}u l=0.13u ng=1\n")
    n += [
        "vr (xref iref) vsource dc=0\n",
        "mr (iref iref 0 0) sg13_lv_nmos w=20u l=4u ng=4\n",
        "mt (tail iref 0 0) sg13_lv_nmos w=160u l=4u ng=32\n",
        "vs (vdd tail) vsource dc=0\n",
    ]
    return "".join(n)


def detector_snippet(en=True):
    """Differential max detector + replica; <= 10 fF tank gate load.

    hold charges to ~= max(tp,tn) - Vgs; rep ~= ct - Vgs.
    A_est = 2 * (V_hold - V_rep + V_LOSS)  (V_LOSS folds conduction-angle loss).
    cmp high when (hold - rep) > V_th = Amp_target/2 - V_LOSS.
    """
    ib = f"{I_DET:.6g}" if en else "1e-12"
    th = v_th()
    n = [
        f"// D22 1b diff-max det; I={I_DET*1e6:.1f}uA C={C_HOLD*1e15:.0f}fF V_LOSS={V_LOSS:.3f}\n",
        # Detector pair: shared source = hold
        f"mdtp (vdd tp hold 0) sg13_lv_nmos w={W_DET} l={L_DET} ng=1\n",
        f"mdtn (vdd tn hold 0) sg13_lv_nmos w={W_DET} l={L_DET} ng=1\n",
        f"idet (hold 0) isource dc={ib}\n",
        f"chold (hold 0) capacitor c={C_HOLD:.6g}\n",
        # Replica pair: both gates at centre tap
        f"mrtp (vdd ct rep 0) sg13_lv_nmos w={W_DET} l={L_DET} ng=1\n",
        f"mrtn (vdd ct rep 0) sg13_lv_nmos w={W_DET} l={L_DET} ng=1\n",
        f"irep (rep 0) isource dc={ib}\n",
        f"crep (rep 0) capacitor c={C_HOLD:.6g}\n",
        # Comparator: vip = hold, vin = rep + V_th
        f"vth (vthn rep) vsource dc={th:.6g}\n",
        "mc1 (co hold ttail 0) sg13_lv_nmos w=4u l=0.5u ng=2\n",
        "mc2 (co2 vthn ttail 0) sg13_lv_nmos w=4u l=0.5u ng=2\n",
        "itt (ttail 0) isource dc=20u\n",
        "rc1 (vdd co) resistor r=20k\n",
        "rc2 (vdd co2) resistor r=20k\n",
        "minv (cmp co 0 0) sg13_lv_nmos w=2u l=0.13u ng=1\n",
        "rpu (vdd cmp) resistor r=50k\n",
    ]
    return "".join(n)


def a_est_from_holds(v_hold, v_rep):
    """Differential amplitude estimate from max-detector nodes."""
    return float(2.0 * ((v_hold - v_rep) + V_LOSS))


def inject_dac_det(sim_path, bias_code, det=True):
    text = open(sim_path).read()
    text = re.sub(
        r"iref \(vdd nb\) isource dc=[^\n]+\n",
        dac_snippet(bias_code, "nb"),
        text,
    )
    if det:
        text = text.replace("\ncontrol\n", "\n" + detector_snippet(True) + "\ncontrol\n")
    open(sim_path, "w").write(text)
