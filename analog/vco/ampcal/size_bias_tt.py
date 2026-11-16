#!/usr/bin/env python3
import subprocess
import sys

import numpy as np
from vacask.rawfile import rawread

sys.path.insert(0, ".")
from size_bias import op

print("fine tt at l=78")
for w in ["5.0u", "5.5u", "6.0u", "5.2u", "5.4u", "5.6u", "5.8u"]:
    r = op(78.0, w_tt=w, ng_tt=2)
    print(
        w,
        f"I_h={r['I_hold']:.3f} I_r={r['I_rep']:.3f} I_tt={r['I_tt']:.3f}",
    )

l_bias = 78.0
w_tt = "5.6u"
ng_tt = 2
sim = f"""bias size
include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section=mos_tt
include "cornerMOShv.lib" section=mos_tt
include "cornerCAP.lib" section=cap_typ
include "cornerRES.lib" section=res_typ
load "resistor.osdi"
load "capacitor.osdi"
model resistor resistor
model capacitor capacitor
model vsource vsource
model isource isource
vdd (vdd 0) vsource dc=1.2
ven (en 0) vsource dc=1.2
vhold (hs 0) vsource dc=0.89
vrep (rs 0) vsource dc=0.48
vtt (ts 0) vsource dc=0.4
vss (ss 0) vsource dc=0.4
rsh (hold hs) resistor r=1
rsr (rep rs) resistor r=1
rst (ttail ts) resistor r=1
rss (ss2 ss) resistor r=1
rbias (vdd nbias 0) rhigh w=0.5u l={l_bias:.3f}u b=0
mdiode (nbias nbias pd_d 0) sg13_lv_nmos w=1.0u l=1.0u ng=1
men_d (pd_d en 0 0) sg13_lv_nmos w=2.0u l=0.13u ng=1
mid_h (hold nbias pd_h 0) sg13_lv_nmos w=1.0u l=1.0u ng=1
men_h (pd_h en 0 0) sg13_lv_nmos w=2.0u l=0.13u ng=1
mid_r (rep nbias pd_r 0) sg13_lv_nmos w=1.0u l=1.0u ng=1
men_r (pd_r en 0 0) sg13_lv_nmos w=2.0u l=0.13u ng=1
mid_tt (ttail nbias pd_tt 0) sg13_lv_nmos w={w_tt} l=1.0u ng={ng_tt}
men_tt (pd_tt en 0 0) sg13_lv_nmos w=2.0u l=0.13u ng=1
mid_ss (ss2 nbias pd_ss 0) sg13_lv_nmos w={w_tt} l=1.0u ng={ng_tt}
men_ss (pd_ss en 0 0) sg13_lv_nmos w=2.0u l=0.13u ng=1
control
  abort always
  options rawfile="binary" temp=27
  save v(nbias) v(hold) v(hs) v(rep) v(rs) v(ttail) v(ts) v(ss2) v(ss)
  analysis op1 op
endc
"""
open("out/bias_sz.sim", "w").write(sim)
subprocess.run(["vacask", "out/bias_sz.sim"], cwd=".", capture_output=True)
# vacask writes raw in cwd
import os
os.chdir("out")
d = rawread("op1.raw").get()


def f(k):
    return float(np.real(d[k]).ravel()[0])


print("at det voltages hold=0.89 rep=0.48, tt=5.6u ng=2:")
ih = (f("hs") - f("hold")) * 1e6
ir = (f("rs") - f("rep")) * 1e6
itt = (f("ts") - f("ttail")) * 1e6
print(f"I_hold={ih:.3f} I_rep={ir:.3f} I_tt={itt:.3f} ratio={ih/ir:.3f}")
