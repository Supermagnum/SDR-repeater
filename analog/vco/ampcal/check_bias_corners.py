#!/usr/bin/env python3
"""Bias currents over MOS/temp corners; en-off check [SCH]."""
import os
import subprocess

import numpy as np
from vacask.rawfile import rawread

import amp_common as A

OUT = os.path.join(A.OUT, "bias_corners")
os.makedirs(OUT, exist_ok=True)

MOS = ("mos_tt", "mos_ss", "mos_ff")
TEMPS = (-40, 27, 85)


def deck(mos, temp, en=1.2):
    return f"""bias corners
include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section={mos}
include "cornerMOShv.lib" section={mos}
include "cornerCAP.lib" section=cap_typ
include "cornerRES.lib" section=res_typ
load "resistor.osdi"
load "capacitor.osdi"
model resistor resistor
model capacitor capacitor
model vsource vsource
model isource isource
vdd (vdd 0) vsource dc=1.2
ven (en 0) vsource dc={en}
vhold (hs 0) vsource dc=0.8
vrep (rs 0) vsource dc=0.5
vtt (ts 0) vsource dc=0.4
vss (ss 0) vsource dc=0.4
rsh (hold hs) resistor r=1
rsr (rep rs) resistor r=1
rst (ttail ts) resistor r=1
rss (ss2 ss) resistor r=1
rbias (vdd nbias 0) rhigh w=0.5u l={A.RHIGH_BIAS_L} b=0
mdiode (nbias nbias pd_d 0) sg13_lv_nmos w={A.W_SINK_DET} l={A.L_SINK} ng={A.NG_SINK_DET}
men_d (pd_d en 0 0) sg13_lv_nmos w=2.0u l=0.13u ng=1
mid_h (hold nbias pd_h 0) sg13_lv_nmos w={A.W_SINK_DET} l={A.L_SINK} ng={A.NG_SINK_DET}
men_h (pd_h en 0 0) sg13_lv_nmos w=2.0u l=0.13u ng=1
mid_r (rep nbias pd_r 0) sg13_lv_nmos w={A.W_SINK_DET} l={A.L_SINK} ng={A.NG_SINK_DET}
men_r (pd_r en 0 0) sg13_lv_nmos w=2.0u l=0.13u ng=1
mid_tt (ttail nbias pd_tt 0) sg13_lv_nmos w={A.W_SINK_CMP} l={A.L_SINK} ng={A.NG_SINK_CMP}
men_tt (pd_tt en 0 0) sg13_lv_nmos w=2.0u l=0.13u ng=1
mid_ss (ss2 nbias pd_ss 0) sg13_lv_nmos w={A.W_SINK_CMP} l={A.L_SINK} ng={A.NG_SINK_CMP}
men_ss (pd_ss en 0 0) sg13_lv_nmos w=2.0u l=0.13u ng=1
control
  abort always
  options rawfile="binary" temp={temp}
  save v(nbias) v(hold) v(hs) v(rep) v(rs) v(ttail) v(ts) v(ss2) v(ss)
  analysis op1 op
endc
"""


def measure(mos, temp, en=1.2):
    path = os.path.join(OUT, f"bias_{mos}_{temp}_en{int(en)}.sim")
    open(path, "w").write(deck(mos, temp, en))
    subprocess.run(["vacask", path], cwd=OUT, capture_output=True, check=False)
    d = rawread(os.path.join(OUT, "op1.raw")).get()

    def f(k):
        return float(np.real(d[k]).ravel()[0])

    return dict(
        I_hold=(f("hs") - f("hold")) * 1e6,
        I_rep=(f("rs") - f("rep")) * 1e6,
        I_tt=(f("ts") - f("ttail")) * 1e6,
        I_ss=(f("ss") - f("ss2")) * 1e6,
        nbias=f("nbias"),
    )


def main():
    print("# Bias currents over corners [SCH]\n")
    print("| MOS | T | I_hold (µA) | I_rep (µA) | I_tt (µA) | I_ss (µA) |")
    print("|---|---|---|---|---|---|")
    for mos in MOS:
        for temp in TEMPS:
            r = measure(mos, temp, 1.2)
            print(
                f"| {mos} | {temp} | {r['I_hold']:.2f} | {r['I_rep']:.2f} | "
                f"{r['I_tt']:.2f} | {r['I_ss']:.2f} |"
            )
    print("\n## en=0 (tt/27) — tank-path sink current\n")
    r = measure("mos_tt", 27, 0)
    print(
        f"I_hold={r['I_hold']*1e3:.3f} nA  I_rep={r['I_rep']*1e3:.3f} nA  "
        f"I_tt={r['I_tt']*1e3:.3f} nA  [SCH]"
    )
    ok = max(abs(r["I_hold"]), abs(r["I_rep"])) < 1e-3  # < 1 nA in µA units
    print("en-off tank path:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
