#!/usr/bin/env python3
"""P2.7.2b — DAC unit W·L from PDK Pelgrom (LV PMOS) for D22 monotonicity.

PDK [sg13g2_moslv_mismatch.lib]:
  σ(ΔVt)   = delvto_mm / sqrt(m·l·w·1e12)   delvto_mm(pmos)=0.0022 V
  σ(Δβ/β)  = factuo_mm / sqrt(m·l·w·1e12)   factuo_mm(pmos)=0.0033
  with w,l in metres → sqrt(W_um·L_um) for m=1.

Current mismatch of two identical devices:
  σ(ΔI/I) = sqrt( (gm/Id)^2 · σ²(ΔVt) + σ²(Δβ/β) )

D22: I_tail = 1.52 + code×0.08 mA, 5-bit binary unit fingers, monotonic.
Worst DNL at MSB (16 vs 15 units): σ_DNL ≈ σ_u · sqrt(31) · I_u/I_LSB = σ_u·√31
Want 3·σ_DNL < 0.5 LSB → σ_u < 0.5/(3·√31) ≈ 0.0299.

gm/Id from OP of unit PMOS at I≈I_MASTER (10.5 µA) into diode-like bias [SCH].
"""
from __future__ import annotations

import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

# PDK LV PMOS mismatch [PDK]
A_VT = 0.0022   # V·µm
A_B = 0.0033    # relative ·µm
I_MASTER = 10.5e-6
W_NOW, L_NOW = 2.0, 2.0  # µm [SCH]
SIG_U_MAX = 0.5 / (3.0 * math.sqrt(31.0))  # 3σ DNL < 0.5 LSB at MSB


def deck(w_um: float, l_um: float) -> str:
    # Two-bias OP: gm ≈ ΔId/ΔVgs via series vsource on gate [SCH]
    return f"""dac unit gm/Id OP [SCH]

ground 0
include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section=mos_tt
load "resistor.osdi"
model resistor resistor
model vsource vsource
model isource isource
vdd (vdd 0) vsource dc=1.2
imaster (pbias 0) isource dc={I_MASTER}
vg (g_m0 pbias) vsource dc=0
mm0 (pbias g_m0 vdd vdd) sg13_lv_pmos w={w_um}u l={l_um}u ng=1
rs (pbias sense) resistor r=1
control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(pbias) v(g_m0) v(sense) i(rs)
  analysis op0 op
  alter vg dc=-0.005
  analysis op1 op
endc
"""


def parse_gmid_from_raw(raw_path: str) -> float | None:
    try:
        sys.path.append("/foss/tools/vacask/lib/vacask/python")
        from vacask.rawfile import rawread
        d0 = rawread(raw_path.replace(".raw", "") + "_op0.raw") if False else None
    except Exception:
        d0 = None
    return None


def run_op(w_um: float, l_um: float) -> float | None:
    """Estimate gm/Id from two OP points ΔId/ΔVgs at I_MASTER [SCH]."""
    name = f"op_gmid_w{w_um:g}_l{l_um:g}"
    sim = os.path.join(OUT, name + ".sim")
    logp = os.path.join(OUT, name + ".log")
    open(sim, "w").write(deck(w_um, l_um))
    try:
        with open(logp, "w") as fh:
            r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                               stdout=fh, stderr=subprocess.STDOUT, timeout=120)
        if r.returncode != 0:
            return None
        sys.path.append("/foss/tools/vacask/lib/vacask/python")
        from vacask.rawfile import rawread
        # vacask names analyses; try common patterns
        id0 = id1 = None
        for suffix in ("op0", "op1", "op"):
            for cand in (os.path.join(OUT, f"{name}.{suffix}.raw"),
                         os.path.join(OUT, f"{name}_{suffix}.raw"),
                         os.path.join(OUT, f"{suffix}.raw")):
                if not os.path.exists(cand):
                    continue
                raw = rawread(cand)
                # find current through rs ≈ Id
                for k in raw[0].keys() if isinstance(raw, tuple) else []:
                    pass
        # Parse log for i(rs) if raw API unknown
        txt = open(logp, errors="ignore").read()
        ids = re.findall(r"i\(rs\)\s*[:=]?\s*([-+eE0-9.]+)", txt, re.I)
        if len(ids) >= 2:
            id0, id1 = abs(float(ids[0])), abs(float(ids[1]))
            gm = abs(id1 - id0) / 0.005
            id_avg = 0.5 * (id0 + id1)
            if id_avg > 0:
                return gm / id_avg
        # Fallback: single Id from log + assume moderate inversion later
        m = re.search(r"i\(rs\)\s*[:=]?\s*([-+eE0-9.]+)", txt, re.I)
        if m:
            # cannot get gm from one point
            return None
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        open(logp, "a").write(f"\nop failed: {e}\n")
    return None


def sigma_i(wl_um2: float, gmid: float) -> float:
    s = math.sqrt(wl_um2)
    s_vt = A_VT / s
    s_b = A_B / s
    return math.sqrt((gmid * s_vt) ** 2 + s_b ** 2)


def wl_min(gmid: float) -> float:
    # Solve σ_I = SIG_U_MAX for WL
    # σ = sqrt( (gmid·A_VT)^2 + A_B^2 ) / sqrt(WL)
    num = math.sqrt((gmid * A_VT) ** 2 + A_B ** 2)
    return (num / SIG_U_MAX) ** 2


def main():
    lines = []
    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    say("# P2.7.2b DAC unit Pelgrom sizing [PDK / HAND]")
    say(f"A_Vt(pmos)={A_VT} V·µm  A_β={A_B}  [PDK sg13g2_moslv_mismatch.lib]")
    say(f"Target σ(ΔI/I)_unit ≤ {SIG_U_MAX:.4f} "
        f"(3σ·√31 DNL < 0.5 LSB, 5-bit binary) [HAND]")

    gmid = run_op(W_NOW, L_NOW)
    if gmid is None:
        # Moderate-inversion fallback for W/L=1, Id≈10.5 µA, L=2 µm [HAND]
        gmid = 8.0
        say(f"gm/Id from OP: UNAVAILABLE — using fallback {gmid:.1f} 1/V [HAND]")
    else:
        say(f"gm/Id from OP at W={W_NOW} L={L_NOW} I={I_MASTER*1e6:.1f}µA: "
            f"{gmid:.2f} 1/V [SCH]")

    wl_req = wl_min(gmid)
    say(f"Minimum W·L = {wl_req:.3f} µm² [HAND]")
    say(f"Current unit W·L = {W_NOW*L_NOW:.3f} µm² [SCH]")

    sig_now = sigma_i(W_NOW * L_NOW, gmid)
    say(f"σ(ΔI/I) at current size = {sig_now*100:.2f} %  "
        f"(3σ·√31 = {3*sig_now*math.sqrt(31)*100:.1f} % LSB) [HAND]")

    if W_NOW * L_NOW >= wl_req:
        say("KEEP W=2u L=2u — already above Pelgrom floor; no sch resize. [HAND]")
        w_use, l_use = W_NOW, L_NOW
        resized = False
    else:
        # Prefer keep L=2 for Early / flicker; grow W
        l_use = L_NOW
        w_use = max(W_NOW, wl_req / l_use)
        say(f"RESIZE to W={w_use:.3f}u L={l_use:.3f}u [HAND]")
        resized = True

    # D22 search accuracy note: unit current law unchanged if size kept
    say("")
    say("D22 search accuracy: unit finger law unchanged "
        "(I_tail=1.52+code×0.08 mA) if size kept; "
        "no re-search needed when KEEP. [SCH]")
    say(f"RESULT resized={resized} W={w_use} L={l_use}")

    out = os.path.join(OUT, "summary_pelgrom_dac_unit.txt")
    open(out, "w").write("\n".join(lines) + "\n")
    open(os.path.join(OUT, "pelgrom_dac_unit.json"), "w").write(
        '{"A_Vt": %s, "A_beta": %s, "gmid": %s, "wl_min_um2": %s, '
        '"W_um": %s, "L_um": %s, "resized": %s, "sig_u": %s}\n'
        % (A_VT, A_B, gmid, wl_req, w_use, l_use,
           "true" if resized else "false", sig_now))
    return 0


if __name__ == "__main__":
    sys.exit(main())
