#!/usr/bin/env python3
import math
import os
import subprocess

import numpy as np
from vacask.rawfile import rawread

OUT = os.path.join(os.path.dirname(__file__), "out")


def run(name, text):
    open(os.path.join(OUT, name + ".sim"), "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(open(log).read()[-500:])


def trial(vin, vref, tag):
    sc = math.sqrt(100e3 / 1.5)
    text = f"""parameters title="vin"
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
vref (vref 0) vsource dc={vref}
vin (vin 0) vsource dc={vin}
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
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save v(vout)
  analysis op1 op store="opx"
  analysis tr1 tran stop=5u step=1n nodeset="opx"
endc
"""
    run(tag, text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    vo = np.real(tr["vout"]).ravel()
    print(f"{tag}: Vin={vin} Vref={vref:.3f} OP={float(np.real(op['vout']).ravel()[0]):.4f} "
          f"t0={vo[0]:.4f} t1={vo[-1]:.4f} drift={(vo[-1]-vo[0])*1e3:.1f}mV")


trial(1.5, 0.55, "vin15_old")
trial(1.5, 0.64825, "vin15_newref")
trial(2.7, 0.64825, "vin27")
trial(1.8, 0.64825, "vin18")
