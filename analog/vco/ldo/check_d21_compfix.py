#!/usr/bin/env python3
"""Find compensation that keeps LDO at OP in VACASK tran (DC load)."""
import math
import os
import subprocess

import numpy as np
from vacask.rawfile import rawread

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
VREF = (1.2 + 9.65e-3 * 10) / 2
VIN = 2.7


def run(name, text):
    open(os.path.join(OUT, name + ".sim"), "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(open(log).read()[-600:])


HDR = """parameters title="compfix"
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


def try_one(tag, cc, rc, cout, rload_filter=False):
    sc = math.sqrt(cout * 1e15 / 1.5)
    # nulling R in series with Cc
    if rc and rc > 0:
        comp = f"rcn (vg ncc) resistor r={rc}\ncc (ncc mid) capacitor c={cc}\n"
    else:
        comp = f"cc (vg mid) capacitor c={cc}\n"
    if rload_filter:
        load = """
rser (vout pad) resistor r=10
cboard (pad 0) capacitor c=100n
il (pad 0) isource dc=5m
"""
        save = "save v(vout) v(pad)"
        node = "pad"
        target = VREF * 2 - 0.05
    else:
        load = "il (vout 0) isource dc=5m\n"
        save = "save v(vout)"
        node = "vout"
        target = VREF * 2
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
{comp}xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
{load}control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  {save}
  analysis op1 op store="opx"
  analysis tr1 tran stop=10u step=2n nodeset="opx"
endc
"""
    run(tag, text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    vo = np.real(tr["vout"]).ravel()
    vx = np.real(tr[node]).ravel()
    opv = float(np.real(op["vout"]).ravel()[0])
    drift = abs(vx[-1] - vx[0])
    std = vo.std() * 1e3
    hold = drift < 5e-3 and std < 5 and abs(vx[-1] - target) < 0.05
    print(f"| {tag} | Cc={cc*1e12:.0f}p Rc={rc or 0:.0f} Cout={cout*1e12:.0f}p | "
          f"OP={opv:.3f} t0={vx[0]:.3f} t1={vx[-1]:.3f} "
          f"drift={drift*1e3:.1f}mV std={std:.1f} | "
          f"{'HOLD' if hold else 'DRIFT'} |")
    return hold


def main():
    print("# Bare LDO: hold OP for 10 µs?\n")
    print("| tag | comps | OP/t0/t1/drift/std | |")
    print("|---|---|---|---|")
    found = None
    for cc in (5e-12, 20e-12, 50e-12, 100e-12):
        for rc in (0, 1e3, 5e3, 20e3):
            for cout in (100e-12, 500e-12, 2e-9, 10e-9):
                tag = f"c{cc*1e12:.0f}_r{rc/1e3:.0f}k_o{cout*1e12:.0f}"
                try:
                    if try_one(tag, cc, rc, cout, False):
                        found = (cc, rc, cout)
                        break
                except Exception as e:
                    print(f"| {tag} | FAIL {str(e)[-40:]} |")
            if found:
                break
        if found:
            break
    if not found:
        # reduce loop gain: smaller pair / more bias current already
        print("\n# Try smaller pass / more Cc\n")
        for cc, rc, cout in ((200e-12, 10e3, 22e-9), (500e-12, 5e3, 47e-9)):
            tag = f"big_c{cc*1e12:.0f}"
            try:
                if try_one(tag, cc, rc, cout, False):
                    found = (cc, rc, cout)
                    break
            except Exception as e:
                print(f"| {tag} | FAIL |")
    if found:
        cc, rc, cout = found
        print(f"\nFound HOLD: Cc={cc*1e12:.0f}p Rc={rc} Cout={cout*1e9:.2f}nF")
        print("\n# Same comps + R=10 + 100n\n")
        try_one("filt_hold", cc, rc, cout, True)
        # + bond L
        sc = math.sqrt(cout * 1e15 / 1.5)
        if rc:
            comp = f"rcn (vg ncc) resistor r={rc}\ncc (ncc mid) capacitor c={cc}\n"
        else:
            comp = f"cc (vg mid) capacitor c={cc}\n"
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
{comp}xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
rser (vout pad) resistor r=10
cpad (pad 0) capacitor c=2p
lbond (pad pin) inductor l=1.5n
cboard (pin 0) capacitor c=100n
il (pad 0) isource dc=5m
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis op1 op store="opx"
  analysis tr1 tran stop=10u step=2n nodeset="opx"
endc
"""
        run("filt_rlc_hold", text)
        tr = rawread(os.path.join(OUT, "tr1.raw")).get()
        vp = np.real(tr["pad"]).ravel()
        print(f"RLC DC: t0={vp[0]:.4f} t1={vp[-1]:.4f} "
              f"drift={(vp[-1]-vp[0])*1e3:.1f}mV std={vp.std()*1e3:.1f}mV")
        # missing C
        text_m = text.replace("cboard (pin 0) capacitor c=100n\n", "")
        run("filt_miss_hold", text_m)
        tr = rawread(os.path.join(OUT, "tr1.raw")).get()
        vp = np.real(tr["pad"]).ravel()
        print(f"miss C: t0={vp[0]:.4f} t1={vp[-1]:.4f} "
              f"drift={(vp[-1]-vp[0])*1e3:.1f}mV "
              f"min={vp.min():.3f} max={vp.max():.3f}")
    else:
        print("\nNo HOLD found in sweep — LDO needs topology fix (follow-up).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
