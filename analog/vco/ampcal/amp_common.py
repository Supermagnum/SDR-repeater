#!/usr/bin/env python3
"""D22 step 1c: differential max detector + V_DS-matched VCO_BIAS DAC.

Detector (1b): two NMOS with gates on tp/tn, shared source = hold; replica
pair gates at ct. C_gate << 10 fF. V_sense = V_hold - V_rep ~= Amp/2 - V_loss.
Threshold = Amp_target/2 - V_LOSS (fixed design-time conduction-angle loss).

DAC: identical ~10 uA PMOS unit cells — offset 19 + bits 1/2/4/8/16 — into a
V_DS-matched 1:8 NMOS mirror -> I_tail = 1.52 mA + code x 0.08 mA (D22).
Master current 10.3 uA so units deliver ~10 uA into the low-V_DS xref node
(PMOS Early vs diode master). Series PMOS switches (gate=0 on).

Mirror: cascode rejected (V_tail ~0.47 V leaves no cascode headroom). OTA
servos nbf so V(xref)=V(tail_f); rbf/cbf keep the D9 noise filter; mbp_rbf
across rbf for wake/search bypass.
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
A_HARD = 1.40          # steady-state differential Amp (owner 2026-11-11)
A_HARD_TRANSIENT = 1.50  # peak during amplitude search only (≈1 µs/step)
A_WIN = 0.10
# Single-ended cmp trip level after 2nd-stage OTA (bal≈0.67, hi≈1.11) [SCH]
CMP_HIGH = 0.85
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

# DAC / mirror (step 1c)
I_MASTER = 10.5e-6    # above 10 uA so code31 stays within ±3% at ss/85 (PMOS Early into low V_DS)
# Wide mirror: lowers V_GS so PMOS units see less Early vs diode master; 3x step-1b
W_MR, NG_MR = "60u", 12     # was 20u / 4
W_MT, NG_MT = "480u", 96    # was 160u / 32  (still 1:8)

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


def dac_pmos_snippet(code, out_node="xraw", mismatch=None):
    """Unit-cell PMOS DAC into out_node (I_ref = I_tail/8 target).

    Master I_MASTER; offset 19 + bits 1/2/4/8/16 of identical 2/2 um fingers
    (P2.5 pm() law). Series PMOS switches L=0.13u, gate 0 = on.
    """
    bits = [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16)]
    n = [
        f"// D22 unit-cell DAC code={code} I_tail={itail(code)*1e3:.3f} mA "
        f"I_master={I_MASTER*1e6:.2f}uA\n",
        f"imaster (pbias 0) isource dc={I_MASTER:.6g}\n",
    ]
    if mismatch:
        n.append(f"vo_m0 (g_m0 pbias) vsource dc={mismatch.get('m0', 0):.6g}\n")
        n.append(f"mm0 (pbias g_m0 vdd vdd) {pm_units(1)}\n")
        n.append(f"vo_off (g_off pbias) vsource dc={mismatch.get('off', 0):.6g}\n")
        g_off = "g_off"
    else:
        n.append(f"mm0 (pbias pbias vdd vdd) {pm_units(1)}\n")
        g_off = "pbias"
    n.append(f"moff (xoff {g_off} vdd vdd) {pm_units(19)}\n")
    n.append(f"msoff ({out_node} 0 xoff vdd) sg13_lv_pmos w=38u l=0.13u ng=1\n")
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
        n.append(
            f"msw{b} ({out_node} {gsw} xd{b} vdd) sg13_lv_pmos "
            f"w={2 * m:g}u l=0.13u ng=1\n"
        )
    return "".join(n)


def mirror_vds_match_snippet(tail_node="tail", sense_from="xraw"):
    """V_DS-matched 1:8 NMOS mirror + OTA gate servo.

    OTA forces V(xref) ~= V(tail_f) so mr sees the same V_DS as mt. Cascode
    rejected: V_tail ~0.44-0.49 V leaves no room for a cascode stack [SCH].
    Keeps rbf/cbf so mbp_rbf (nb/nbf) still bypasses the D9 filter.
    """
    return (
        f"// V_DS-matched 1:8 mirror (OTA servos V(xref)=V(tail_f)); "
        f"mr {W_MR}/{NG_MR} mt {W_MT}/{NG_MT}\n"
        f"vsense ({sense_from} xref) vsource dc=0\n"
        f"mr (xref nbf 0 0) sg13_lv_nmos w={W_MR} l=4u ng={NG_MR}\n"
        f"mt ({tail_node} nbf 0 0) sg13_lv_nmos w={W_MT} l=4u ng={NG_MT}\n"
        # RF-isolated sense of the tail node for the OTA
        "rtf (tail tail_f) resistor r=100k\n"
        "ctf (tail_f 0) capacitor c=1p\n"
        # Diff OTA: vip=xref, vin=tail_f, out -> nb (then rbf -> nbf)
        "mo1 (d1 xref ss 0) sg13_lv_nmos w=8u l=2u ng=2\n"
        "mo2 (d2 tail_f ss 0) sg13_lv_nmos w=8u l=2u ng=2\n"
        "iss (ss 0) isource dc=20u\n"
        "mp1 (d1 d1 vdd vdd) sg13_lv_pmos w=4u l=2u ng=2\n"
        "mp2 (d2 d1 vdd vdd) sg13_lv_pmos w=4u l=2u ng=2\n"
        "rout (d2 nb) resistor r=1\n"
        "rbf (nb nbf) resistor r=1M noisy=1\n"
        "cbf (nbf 0) capacitor c=50p\n"
        "rpd (nb 0) resistor r=200k\n"
    )


def dac_snippet(code, nb_node="nb"):
    """Legacy name: full DAC+mirror inject when nb_node unused.

    Prefer inject_dac_det which replaces the VCO bias block. Kept for callers
    that only swapped iref; those must now use inject_bias_block.
    """
    return dac_pmos_snippet(code, "xraw") + mirror_vds_match_snippet()


def dac_transistor_body(code, mismatch=None, vtail=0.47):
    """Standalone DAC + V_DS-matched 1:8 mirror for DC / MC characterisation.

    I_ref sensed with series 0 V (xraw -> xref). Never short xref to vdd.
    Fixed V(tail)=vtail mimics the oscillating VCO common-source node.
    """
    n = [
        "vdd (vdd 0) vsource dc=1.2\n",
        dac_pmos_snippet(code, "xraw", mismatch=mismatch),
        # Compact mirror (no RF filter on sense; DC V_tail fixed)
        f"vt (tail 0) vsource dc={vtail}\n",
        "vsense (xraw xref) vsource dc=0\n",
        f"mr (xref nbf 0 0) sg13_lv_nmos w={W_MR} l=4u ng={NG_MR}\n",
        f"mt (tail nbf 0 0) sg13_lv_nmos w={W_MT} l=4u ng={NG_MT}\n",
        "mo1 (d1 xref ss 0) sg13_lv_nmos w=8u l=2u ng=2\n",
        "mo2 (d2 tail ss 0) sg13_lv_nmos w=8u l=2u ng=2\n",
        "iss (ss 0) isource dc=20u\n",
        "mp1 (d1 d1 vdd vdd) sg13_lv_pmos w=4u l=2u ng=2\n",
        "mp2 (d2 d1 vdd vdd) sg13_lv_pmos w=4u l=2u ng=2\n",
        "rout (d2 nbf) resistor r=1\n",
        "cl (nbf 0) capacitor c=10p\n",
        "rpd (nbf 0) resistor r=200k\n",
        # I_tail = i(vt); do not also place a 0 V sense from vdd (conflicts with vt).
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
        # Comparator: vip = hold, vin = rep + V_th. Amp high → co < co2.
        # First-stage co only swings ~±70 mV around 1 V — a CMOS inverter never
        # trips. Second OTA (vip=co2, vin=co) makes a real single-ended cmp.
        f"vth (vthn rep) vsource dc={th:.6g}\n",
        "mc1 (co hold ttail 0) sg13_lv_nmos w=4u l=0.5u ng=2\n",
        "mc2 (co2 vthn ttail 0) sg13_lv_nmos w=4u l=0.5u ng=2\n",
        "itt (ttail 0) isource dc=20u\n",
        "rc1 (vdd co) resistor r=20k\n",
        "rc2 (vdd co2) resistor r=20k\n",
        # Diff→SE stage: high when co2 > co (Amp above target).
        # Names mcs* — avoid ms1/ms2 (bank switch fingers in the VCO deck).
        "mcs1 (n1 co2 ss2 0) sg13_lv_nmos w=4u l=0.5u ng=2\n",
        "mcs2 (cmp co ss2 0) sg13_lv_nmos w=4u l=0.5u ng=2\n",
        "iss2 (ss2 0) isource dc=20u\n",
        "mpl1 (n1 n1 vdd vdd) sg13_lv_pmos w=4u l=0.5u ng=2\n",
        "mpl2 (cmp n1 vdd vdd) sg13_lv_pmos w=4u l=0.5u ng=2\n",
        "cl_cmp (cmp 0) capacitor c=50f\n",
    ]
    return "".join(n)


def a_est_from_holds(v_hold, v_rep):
    """Differential amplitude estimate from max-detector nodes."""
    return float(2.0 * ((v_hold - v_rep) + V_LOSS))


_BIAS_BLOCK_RE = re.compile(
    r"mt \(tail nbf 0 0\)[^\n]+\n"
    r"rbf \(nb nbf\)[^\n]+\n"
    r"cbf \(nbf 0\)[^\n]+\n"
    r"mr \(nb nb 0 0\)[^\n]+\n"
    r"iref \(vdd nb\) isource dc=[^\n]+\n",
    re.MULTILINE,
)


def bias_block_vds(code):
    """Full VCO bias: DAC + V_DS-matched mirror (replaces mt/rbf/cbf/mr/iref)."""
    return dac_pmos_snippet(code, "xraw") + mirror_vds_match_snippet()


def inject_dac_det(sim_path, bias_code, det=True):
    """Replace VCO diode+iref bias with DAC + V_DS-matched mirror; optional det."""
    text = open(sim_path).read()
    repl = bias_block_vds(bias_code)
    text2, n = _BIAS_BLOCK_RE.subn(repl, text, count=1)
    if n != 1:
        # Fallback: only swap iref (legacy) — still wrong scale without mirror
        text2 = re.sub(
            r"iref \(vdd nb\) isource dc=[^\n]+\n",
            dac_pmos_snippet(bias_code, "nb"),
            text,
        )
    if det:
        text2 = text2.replace("\ncontrol\n", "\n" + detector_snippet(True) + "\ncontrol\n")
    open(sim_path, "w").write(text2)
