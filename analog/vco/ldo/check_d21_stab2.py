#!/usr/bin/env python3
"""Bare LDO vs RC vs RLC transient — find a stable D21 load configuration."""
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
        raise RuntimeError(open(log).read()[-1000:])


HDR = """parameters title="stab2"
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


def ldo(cc=5e-12, cout=100e-12):
    sc = side(cout * 1e15)
    return f"""
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
"""


def analyse(tag, extra, save_pad=False):
    save = "save v(vout) v(pad)" if save_pad else "save v(vout)"
    text = HDR + ldo() + extra + f"""
control
  abort always
  options temp=27 reltol=1e-3 rawfile="binary" strictsave=1
  {save}
  analysis op1 op
  analysis tr1 tran stop=20u step=2n
endc
"""
    run(tag, text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    t = np.real(tr["time"]).ravel()
    vo = np.real(tr["vout"]).ravel()
    node = "pad" if save_pad and "pad" in tr.names else "vout"
    vx = np.real(tr[node]).ravel()
    pre = vx[(t > 3e-6) & (t < 4.5e-6)]
    post = vx[(t > 12e-6) & (t < 18e-6)]
    std = vo[(t > 12e-6) & (t < 18e-6)].std() * 1e3
    print(f"{tag}: OP vout={float(np.real(op['vout']).ravel()[0]):.4f}  "
          f"tran pre={pre.mean():.4f} post={post.mean():.4f} "
          f"dlt={(post.mean()-pre.mean())*1e3:.1f}mV vout_std={std:.1f}mV")


def main():
    print(f"Vref={VREF:.4f} V_LDO_target={VL:.4f}\n")
    analyse("bare_step", """
il0 (vout 0) isource dc=5m
il1 (vout 0) isource type="pulse" val0=0 val1=5m delay=5u rise=20n fall=20n width=20u period=100u
""")
    analyse("rc_noL", f"""
rser (vout pad) resistor r={R}
cboard (pad 0) capacitor c=100n
il0 (pad 0) isource dc=5m
il1 (pad 0) isource type="pulse" val0=0 val1=5m delay=5u rise=20n fall=20n width=20u period=100u
""", save_pad=True)
    analyse("rlc_esr50", f"""
rser (vout pad) resistor r={R}
cpad (pad 0) capacitor c=2p
lbond (pad pin) inductor l=1.5n
resr (pin cbot) resistor r=50m
cboard (cbot 0) capacitor c=100n
il0 (pad 0) isource dc=5m
il1 (pad 0) isource type="pulse" val0=0 val1=5m delay=5u rise=20n fall=20n width=20u period=100u
""", save_pad=True)
    # Heavy miller + big Cout, RLC
    sc = side(500e3)
    analyse("rlc_heavy", f"""
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
cc (vg mid) capacitor c=20p
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
rser (vout pad) resistor r={R}
cpad (pad 0) capacitor c=2p
lbond (pad pin) inductor l=1.5n
resr (pin cbot) resistor r=50m
cboard (cbot 0) capacitor c=100n
il0 (pad 0) isource dc=5m
il1 (pad 0) isource type="pulse" val0=0 val1=5m delay=5u rise=20n fall=20n width=20u period=100u
""")  # broken - duplicates ldo; skip
    return 0


if __name__ == "__main__":
    # Fix: only the three clean cases
    print(f"Vref={VREF:.4f} V_LDO_target={VL:.4f}\n")
    analyse("bare_step", """
il0 (vout 0) isource dc=5m
il1 (vout 0) isource type="pulse" val0=0 val1=5m delay=5u rise=20n fall=20n width=20u period=100u
""")
    analyse("rc_noL", f"""
rser (vout pad) resistor r={R}
cboard (pad 0) capacitor c=100n
il0 (pad 0) isource dc=5m
il1 (pad 0) isource type="pulse" val0=0 val1=5m delay=5u rise=20n fall=20n width=20u period=100u
""", save_pad=True)
    analyse("rlc_esr50", f"""
rser (vout pad) resistor r={R}
cpad (pad 0) capacitor c=2p
lbond (pad pin) inductor l=1.5n
resr (pin cbot) resistor r=50m
cboard (cbot 0) capacitor c=100n
il0 (pad 0) isource dc=5m
il1 (pad 0) isource type="pulse" val0=0 val1=5m delay=5u rise=20n fall=20n width=20u period=100u
""", save_pad=True)
    # Heavy compensation RLC
    text = HDR + ldo(cc=20e-12, cout=200e-12) + f"""
rser (vout pad) resistor r={R}
cpad (pad 0) capacitor c=2p
lbond (pad pin) inductor l=1.5n
resr (pin cbot) resistor r=50m
cboard (cbot 0) capacitor c=100n
il0 (pad 0) isource dc=5m
il1 (pad 0) isource type="pulse" val0=0 val1=5m delay=5u rise=20n fall=20n width=20u period=100u
control
  abort always
  options temp=27 reltol=1e-3 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis op1 op
  analysis tr1 tran stop=20u step=2n
endc
"""
    run("rlc_heavy", text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    t = np.real(tr["time"]).ravel()
    vp = np.real(tr["pad"]).ravel()
    vo = np.real(tr["vout"]).ravel()
    pre = vp[(t > 3e-6) & (t < 4.5e-6)]
    post = vp[(t > 12e-6) & (t < 18e-6)]
    std = vo[(t > 12e-6) & (t < 18e-6)].std() * 1e3
    print(f"rlc_heavy: OP={float(np.real(op['vout']).ravel()[0]):.4f} "
          f"pre={pre.mean():.4f} post={post.mean():.4f} "
          f"dlt={(post.mean()-pre.mean())*1e3:.1f}mV std={std:.1f}mV")

    # Missing C, heavy
    text = HDR + ldo(cc=20e-12, cout=200e-12) + f"""
rser (vout pad) resistor r={R}
cpad (pad 0) capacitor c=2p
cesd (pad 0) capacitor c=1p
lbond (pad pin) inductor l=1.5n
il0 (pad 0) isource dc=5m
il1 (pad 0) isource type="pulse" val0=0 val1=5m delay=5u rise=20n fall=20n width=20u period=100u
control
  abort always
  options temp=27 reltol=1e-3 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis op1 op
  analysis tr1 tran stop=20u step=2n
endc
"""
    run("miss_heavy", text)
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    t = np.real(tr["time"]).ravel()
    vp = np.real(tr["pad"]).ravel()
    vo = np.real(tr["vout"]).ravel()
    pre = vp[(t > 3e-6) & (t < 4.5e-6)]
    post = vp[(t > 12e-6) & (t < 18e-6)]
    std = vo[(t > 12e-6) & (t < 18e-6)].std() * 1e3
    print(f"miss_heavy: pre={pre.mean():.4f} post={post.mean():.4f} "
          f"dlt={(post.mean()-pre.mean())*1e3:.1f}mV std={std:.1f}mV "
          f"min={vp.min():.3f} max={vp.max():.3f}")
