#!/usr/bin/env python3
"""Stabilize bare D10 LDO (no R filter) then re-check R=10 / 100n load."""
import math
import os
import subprocess

import numpy as np
from vacask.rawfile import rawread

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
I_TYP = 9.65e-3
R = 10.0
VL = 1.2 + I_TYP * R
VREF = VL / 2
VIN = 2.7


def side(cff):
    return math.sqrt(cff / 1.5)


def run(name, text):
    open(os.path.join(OUT, name + ".sim"), "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(open(log).read()[-800:])


HDR = """parameters title="bare stab"
include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section=mos_tt
include "cornerCAP.lib" section=cap_typ
load "resistor.osdi"
load "capacitor.osdi"
load "inductor.osdi"
model resistor resistor
model capacitor capacitor
model inductor inductor
model vsource vsource
model isource isource
"""


def sim(tag, cc, cout, filt="bare", esr=0.05):
    sc = side(cout * 1e15)
    if filt == "bare":
        load = f"""
il0 (vout 0) isource dc=5m
il1 (vout 0) isource type="pulse" val0=0 val1=5m delay=10u rise=50n fall=50n width=30u period=100u
"""
        save = "save v(vout)"
        node = "vout"
    else:
        esr_net = (f"resr (pin cbot) resistor r={esr}\n"
                   f"cboard (cbot 0) capacitor c=100n\n") if filt == "rlc" else (
                       f"cboard (pad 0) capacitor c=100n\n")
        lbond = "lbond (pad pin) inductor l=1.5n\n" if filt == "rlc" else ""
        pin = "pin" if filt == "rlc" else "pad"
        if filt == "rc":
            esr_net = "cboard (pad 0) capacitor c=100n\n"
            lbond = ""
        load = f"""
rser (vout pad) resistor r={R}
cpad (pad 0) capacitor c=2p
{lbond}{esr_net}il0 (pad 0) isource dc=5m
il1 (pad 0) isource type="pulse" val0=0 val1=5m delay=10u rise=50n fall=50n width=30u period=100u
"""
        save = "save v(vout) v(pad)"
        node = "pad"

    text = HDR + f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
rf1 (vout mid) resistor r=200k
rf2 (mid 0) resistor r=200k
ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (d1 mid t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
cc (vg mid) capacitor c={cc}
rc (vg nz) resistor r=5k
cc2 (nz mid) capacitor c={cc}
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
{load}control
  abort always
  options temp=27 reltol=1e-3 rawfile="binary" strictsave=1
  {save}
  analysis op1 op
  analysis tr1 tran stop=40u step=5n
endc
"""
    # Actually use single Cc first — dual path may confuse. Rebuild simpler:
    text = HDR + f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
rf1 (vout mid) resistor r=200k
rf2 (mid 0) resistor r=200k
ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (d1 mid t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
cc (vg mid) capacitor c={cc}
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
{load}control
  abort always
  options temp=27 reltol=1e-3 rawfile="binary" strictsave=1
  {save}
  analysis op1 op
  analysis tr1 tran stop=40u step=5n
endc
"""
    run(tag, text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    t = np.real(tr["time"]).ravel()
    vx = np.real(tr[node]).ravel()
    vo = np.real(tr["vout"]).ravel()
    pre = vx[(t > 6e-6) & (t < 9e-6)]
    post = vx[(t > 25e-6) & (t < 35e-6)]
    std = vo[(t > 25e-6) & (t < 35e-6)].std() * 1e3
    opv = float(np.real(op["vout"]).ravel()[0])
    ok = abs(pre.mean() - opv) < 0.05 if node == "vout" else abs(pre.mean() - (opv - 0.05)) < 0.08
    quiet = std < 5
    step = abs((post.mean() - pre.mean()) * 1e3 + (50 if node == "pad" else 0)) < 40
    # bare: step load on vout, IR=0, expect small droop
    if node == "vout":
        step = abs((post.mean() - pre.mean()) * 1e3) < 80 and post.mean() > 1.0
    verdict = "STABLE" if (ok and quiet and step) else ("OSC" if std > 50 else "CHECK")
    print(f"| {tag} | Cc={cc*1e12:.0f}p Cout={cout*1e12:.0f}p | OP={opv:.3f} "
          f"pre={pre.mean():.3f} dlt={(post.mean()-pre.mean())*1e3:.1f} "
          f"std={std:.1f} | {verdict} |")
    return verdict


def main():
    print("# Bare LDO compensation sweep\n")
    print("| tag | Cc/Cout | OP/pre/dlt/std | verdict |")
    print("|---|---|---|---|")
    stable_cc = stable_co = None
    for cc in (0.5e-12, 5e-12, 20e-12, 50e-12):
        for cout in (50e-12, 200e-12, 1e-9, 5e-9):
            tag = f"b_c{cc*1e12:.0f}_o{cout*1e12:.0f}"
            try:
                v = sim(tag, cc, cout, "bare")
                if v == "STABLE" and stable_cc is None:
                    stable_cc, stable_co = cc, cout
            except Exception as e:
                print(f"| {tag} | — | FAIL {str(e)[-40:]} |")
    if stable_cc is None:
        print("\nNo bare STABLE — try even larger Cout / Cc\n")
        for cc, cout in ((100e-12, 10e-9), (200e-12, 22e-9)):
            tag = f"b_c{cc*1e12:.0f}_o{cout*1e9:.0f}n"
            try:
                v = sim(tag, cc, cout, "bare")
                if v == "STABLE":
                    stable_cc, stable_co = cc, cout
            except Exception as e:
                print(f"| {tag} | FAIL |")
    if stable_cc is not None:
        print(f"\n# With filter, Cc={stable_cc*1e12:.0f}p Cout={stable_co*1e12:.0f}p\n")
        for filt in ("rc", "rlc", "miss"):
            tag = f"f_{filt}"
            try:
                if filt == "miss":
                    # no board C
                    sc = side(stable_co * 1e15)
                    text = HDR + f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
rf1 (vout mid) resistor r=200k
rf2 (mid 0) resistor r=200k
ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (d1 mid t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
cc (vg mid) capacitor c={stable_cc}
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
rser (vout pad) resistor r={R}
cpad (pad 0) capacitor c=2p
cesd (pad 0) capacitor c=1p
lbond (pad pin) inductor l=1.5n
il0 (pad 0) isource dc=5m
il1 (pad 0) isource type="pulse" val0=0 val1=5m delay=10u rise=50n fall=50n width=30u period=100u
control
  abort always
  options temp=27 reltol=1e-3 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis op1 op
  analysis tr1 tran stop=40u step=5n
endc
"""
                    run(tag, text)
                    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
                    t = np.real(tr["time"]).ravel()
                    vp = np.real(tr["pad"]).ravel()
                    vo = np.real(tr["vout"]).ravel()
                    pre = vp[(t > 6e-6) & (t < 9e-6)]
                    post = vp[(t > 25e-6) & (t < 35e-6)]
                    std = vo[(t > 25e-6) & (t < 35e-6)].std() * 1e3
                    print(f"| {tag} | pre={pre.mean():.3f} dlt={(post.mean()-pre.mean())*1e3:.1f} "
                          f"std={std:.1f} min={vp.min():.2f} max={vp.max():.2f} |")
                else:
                    sim(tag, stable_cc, stable_co, filt)
            except Exception as e:
                print(f"| {tag} | FAIL {str(e)[-50:]} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
