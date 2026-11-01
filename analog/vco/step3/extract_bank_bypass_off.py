#!/usr/bin/env python3
"""Extract off-state linear equivalent of one bank bypass NMOS (w=5u l=0.13u ng=2).

Reports R_off, junction C (drain-source and to bulk), and |I_leak| at ff / 125 °C
with V_DS spanning the bias window. Used by bias_bypass_switches(bank_mode=\"linear\").

    python3 -u extract_bank_bypass_off.py | tee out/summary_bank_bypass_off.txt
"""
import json
import math
import os
import subprocess

import numpy as np
from vacask.rawfile import rawread

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

# Device matches bias_bypass_switches bank finger
W, L, NG = "5u", "0.13u", 2
# Bias plates: bottom plate ~0..1.2 V, bb tied 0 (switch on) or 1.2 (switch off).
# Off-state bypass: vbp=0; typical |V_DS| up to ~1.2 V.
VDS_LIST = [0.05, 0.3, 0.6, 1.2]
FAC = 1e9  # GHz for AC


def run_vacask(name, text):
    path = os.path.join(OUT, name + ".sim")
    open(path, "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(open(log).read()[-800:])
    return log


def deck_header(mos, temp):
    return f"""ground 0
include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section={mos}
load "resistor.osdi"
load "capacitor.osdi"
model resistor resistor
model capacitor capacitor
model vsource vsource
model isource isource
"""


def ctrl_opts(temp):
    return f'  options temp={temp} reltol=1e-6 rawfile="binary" strictsave=1\n'


def _flow(d, src):
    """Branch current for vsource `src` from an OP/AC raw (name like 'src:flow(br)')."""
    for k in d.names:
        if k.startswith(src + ":") or k == f"i({src})":
            return np.asarray(d[k]).ravel()[0]
    raise KeyError(d.names)


def extract_one(mos, temp, tag):
    """R_off and I_leak from DC; C from AC Y at 1 GHz, V_DS=0.6 V."""
    ileaks, roffs = [], []
    for vds in VDS_LIST:
        name = f"bpoff_i_{tag}_{vds:.2f}".replace(".", "p")
        text = deck_header(mos, temp) + f"""
vd (dx 0) vsource dc={vds}
vs (s 0) vsource dc=0
vg (g 0) vsource dc=0
vi (d dx) vsource dc=0
m (d g s 0) sg13_lv_nmos w={W} l={L} ng={NG}
control
  abort always
{ctrl_opts(temp)}  save i(vi)
  analysis op1 op
endc
"""
        run_vacask(name, text)
        d = rawread(os.path.join(OUT, "op1.raw")).get()
        ids = float(np.real(_flow(d, "vi")))
        ileaks.append(abs(ids))
        roffs.append(vds / abs(ids) if abs(ids) > 0 else float("inf"))

    name = f"bpoff_ac_{tag}"
    text = deck_header(mos, temp) + f"""
vd (d 0) vsource dc=0.6 mag=1
vs (s 0) vsource dc=0
vg (g 0) vsource dc=0
m (d g s 0) sg13_lv_nmos w={W} l={L} ng={NG}
control
  abort always
{ctrl_opts(temp)}  save i(vd) i(vs)
  analysis ac1 ac values=[1G]
endc
"""
    run_vacask(name, text)
    d = rawread(os.path.join(OUT, "ac1.raw")).get()
    f = float(np.real(d["frequency"]).ravel()[0])
    id_ = complex(_flow(d, "vd"))
    c_d = abs(id_.imag) / (2 * math.pi * f)

    name2 = f"bpoff_ac2_{tag}"
    text = deck_header(mos, temp) + f"""
vd (d 0) vsource dc=0.6
vs (s 0) vsource dc=0 mag=1
vg (g 0) vsource dc=0
m (d g s 0) sg13_lv_nmos w={W} l={L} ng={NG}
control
  abort always
{ctrl_opts(temp)}  save i(vs) i(vd)
  analysis ac1 ac values=[1G]
endc
"""
    run_vacask(name2, text)
    d2 = rawread(os.path.join(OUT, "ac1.raw")).get()
    is_ = complex(_flow(d2, "vs"))
    c_s = abs(is_.imag) / (2 * math.pi * f)

    c_ds = min(c_d, c_s)
    c_db = max(0.0, c_d - c_ds)
    c_sb = max(0.0, c_s - c_ds)
    return dict(
        mos=mos, temp=temp, vds=VDS_LIST, ileak=ileaks, roff_vs_vds=roffs,
        roff=roffs[0], ileak_max=max(ileaks),
        c_d=c_d, c_s=c_s, c_ds=c_ds, c_db=c_db, c_sb=c_sb, f_ac=f,
    )


def main():
    print("# Off-state bank bypass NMOS linear equivalent\n")
    print(f"Device: sg13_lv_nmos w={W} l={L} ng={NG}, V_GS=0 (off).\n")
    # Leakage worst: ff hot
    ff = extract_one("mos_ff", 125, "ff125")
    tt = extract_one("mos_tt", 27, "tt27")
    print("## ff / 125 °C (leakage corner)\n")
    print("| V_DS (V) | |I_D| (A) | R_off (Ohm) |")
    print("|---|---|---|")
    for v, i, r in zip(ff["vds"], ff["ileak"], ff["roff_vs_vds"]):
        print(f"| {v:.2f} | {i:.3e} | {r:.3e} |")
    print(f"\nC at 1 GHz, V_DS=0.6 V: C_d={ff['c_d']*1e15:.2f} fF, C_s={ff['c_s']*1e15:.2f} fF "
          f"→ C_ds≈{ff['c_ds']*1e15:.2f} fF, C_db≈{ff['c_db']*1e15:.2f} fF, C_sb≈{ff['c_sb']*1e15:.2f} fF")
    print(f"\n## tt / 27 °C (reference)\nR_off(50 mV)={tt['roff']:.3e} Ohm, I_leak(max)={tt['ileak_max']:.3e} A, "
          f"C_ds≈{tt['c_ds']*1e15:.2f} fF")

    # Model params for netlist: use ff-hot leakage for noise; C and R_off from ff (pessimistic C often at ss — use max C)
    c_ds = max(ff["c_ds"], tt["c_ds"])
    c_db = max(ff["c_db"], tt["c_db"])
    c_sb = max(ff["c_sb"], tt["c_sb"])
    # R_off: use small-V_DS ff value (worst leakage → lowest R_off)
    roff = ff["roff"]
    ileak = ff["ileak_max"]
    # Shot ↔ thermal: 4 k T / R_n = 2 q I  →  R_n = 2 k T / (q I), T=398 K (125 °C)
    k, q = 1.380649e-23, 1.602176634e-19
    T = 125 + 273.15
    r_shot = 2 * k * T / (q * ileak) if ileak > 0 else 1e15

    params = dict(
        w=W, l=L, ng=NG,
        roff=roff, c_ds=c_ds, c_db=c_db, c_sb=c_sb,
        ileak_ff_hot=ileak, r_shot=r_shot, T_shot=T,
        note="R_off and C from device; leakage noise = shot of |I|_max at mos_ff/125C via R_shot=2kT/(qI)",
    )
    json.dump(params, open(os.path.join(OUT, "bank_bypass_off.json"), "w"), indent=2)
    print("\n## Netlist parameters (bank_bypass_off.json)\n")
    print(f"R_off = {roff:.3e} Ohm")
    print(f"C_ds = {c_ds*1e15:.2f} fF, C_db = {c_db*1e15:.2f} fF, C_sb = {c_sb*1e15:.2f} fF")
    print(f"I_leak (ff/125) = {ileak:.3e} A → R_shot = {r_shot:.3e} Ohm at {T:.0f} K")
    print(f"\nwrote out/bank_bypass_off.json")


if __name__ == "__main__":
    main()
