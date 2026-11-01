#!/usr/bin/env python3
"""Does VACASK tran hold the LDO OP with DC load only?"""
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
        raise RuntimeError(open(log).read()[-800:])
    print(open(log).read()[-500:])


HDR = """parameters title="tran dc"
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

sc = math.sqrt(100e3 / 1.5)
body = f"""
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
cc (vg mid) capacitor c=5p
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
il (vout 0) isource dc=5m
"""

# 1) OP then short tran
text = HDR + body + """
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save v(vout) v(vg) v(mid)
  analysis op1 op store="opx"
  analysis tr1 tran stop=5u step=1n nodeset="opx"
endc
"""
print("=== nodeset from OP ===")
run("tran_nodeset", text)
tr = rawread(os.path.join(OUT, "tr1.raw")).get()
op = rawread(os.path.join(OUT, "op1.raw")).get()
t = np.real(tr["time"]).ravel()
vo = np.real(tr["vout"]).ravel()
print(f"OP={float(np.real(op['vout']).ravel()[0]):.4f} "
      f"tran[0]={vo[0]:.4f} tran[-1]={vo[-1]:.4f} "
      f"std={vo.std()*1e3:.2f}mV min={vo.min():.3f} max={vo.max():.3f}")

# 2) plain tran no nodeset
text = HDR + body + """
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save v(vout) v(vg)
  analysis op1 op
  analysis tr1 tran stop=5u step=1n
endc
"""
print("\n=== plain tran after OP ===")
run("tran_plain", text)
tr = rawread(os.path.join(OUT, "tr1.raw")).get()
t = np.real(tr["time"]).ravel()
vo = np.real(tr["vout"]).ravel()
print(f"tran[0]={vo[0]:.4f} tran[-1]={vo[-1]:.4f} "
      f"std={vo.std()*1e3:.2f}mV")

# 3) with R+100n, nodeset
text = HDR + body + f"""
rser (vout pad) resistor r=10
cboard (pad 0) capacitor c=100n
il2 (pad 0) isource dc=5m
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis op1 op store="opx"
  analysis tr1 tran stop=5u step=1n nodeset="opx"
endc
""".replace("il (vout 0) isource dc=5m\n", "")  # load on pad only
# fix: rebuild cleanly
body2 = body.replace("il (vout 0) isource dc=5m\n", "")
text = HDR + body2 + """
rser (vout pad) resistor r=10
cboard (pad 0) capacitor c=100n
il (pad 0) isource dc=5m
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis op1 op store="opx"
  analysis tr1 tran stop=5u step=1n nodeset="opx"
endc
"""
print("\n=== RC filter, nodeset, DC load ===")
run("tran_rc_nodeset", text)
tr = rawread(os.path.join(OUT, "tr1.raw")).get()
op = rawread(os.path.join(OUT, "op1.raw")).get()
vo = np.real(tr["vout"]).ravel()
vp = np.real(tr["pad"]).ravel()
print(f"OP vout={float(np.real(op['vout']).ravel()[0]):.4f} "
      f"pad={float(np.real(op['pad']).ravel()[0]):.4f}")
print(f"tran vout[0]={vo[0]:.4f} [-1]={vo[-1]:.4f} std={vo.std()*1e3:.2f}mV")
print(f"tran pad[0]={vp[0]:.4f} [-1]={vp[-1]:.4f} std={vp.std()*1e3:.2f}mV")
