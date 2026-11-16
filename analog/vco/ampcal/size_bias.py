#!/usr/bin/env python3
"""OP-sweep rbias l and tt W for I_hold=4 µA, I_tt=20 µA [SCH]."""
import subprocess

import numpy as np
from vacask.rawfile import rawread


def op(l_bias, w_tt="2.0u", ng_tt=2, w_diode="1.0u", ng_d=1):
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
vhold (hs 0) vsource dc=0.8
vrep (rs 0) vsource dc=0.5
vtt (ts 0) vsource dc=0.4
vss (ss 0) vsource dc=0.4
rsh (hold hs) resistor r=1
rsr (rep rs) resistor r=1
rst (ttail ts) resistor r=1
rss (ss2 ss) resistor r=1
rbias (vdd nbias 0) rhigh w=0.5u l={l_bias:.3f}u b=0
mdiode (nbias nbias pd_d 0) sg13_lv_nmos w={w_diode} l=1.0u ng={ng_d}
men_d (pd_d en 0 0) sg13_lv_nmos w=2.0u l=0.13u ng=1
mid_h (hold nbias pd_h 0) sg13_lv_nmos w={w_diode} l=1.0u ng={ng_d}
men_h (pd_h en 0 0) sg13_lv_nmos w=2.0u l=0.13u ng=1
mid_r (rep nbias pd_r 0) sg13_lv_nmos w={w_diode} l=1.0u ng={ng_d}
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
    open("bias_sz.sim", "w").write(sim)
    subprocess.run(["vacask", "bias_sz.sim"], capture_output=True, check=False)
    d = rawread("op1.raw").get()

    def f(k):
        return float(np.real(d[k]).ravel()[0])

    return dict(
        nbias=f("nbias"),
        I_hold=(f("hs") - f("hold")) * 1e6,
        I_rep=(f("rs") - f("rep")) * 1e6,
        I_tt=(f("ts") - f("ttail")) * 1e6,
        I_ss=(f("ss") - f("ss2")) * 1e6,
    )


def main():
    print("=== rbias l sweep (diode/sink 1u/1u, tt 2u ng=2) ===")
    for l in (50, 55, 60, 62, 65, 70, 80):
        r = op(l)
        print(
            f"l={l:5.1f} I_hold={r['I_hold']:6.2f} I_rep={r['I_rep']:6.2f} "
            f"I_tt={r['I_tt']:6.2f} nbias={r['nbias']:.3f}"
        )

    print("=== fine l for I_hold~4 ===")
    best_l = None
    best_err = 1e9
    for l in np.arange(55.0, 85.0, 0.5):
        r = op(float(l))
        err = abs(r["I_hold"] - 4.0)
        if err < best_err:
            best_err = err
            best_l = float(l)
        if err < 0.2:
            print(f"l={l:.1f} I_h={r['I_hold']:.3f} I_tt={r['I_tt']:.3f}")
    print(f"best_l={best_l} err={best_err:.3f}")

    print(f"=== tt size at l={best_l} ===")
    best_tt = None
    best_tt_err = 1e9
    for w, ng in [
        ("2.0u", 2), ("2.5u", 2), ("3.0u", 2), ("3.5u", 2),
        ("2.0u", 3), ("2.5u", 3), ("3.0u", 3),
        ("2.0u", 4), ("2.5u", 4), ("3.0u", 4),
        ("4.0u", 2), ("5.0u", 2), ("4.0u", 3),
    ]:
        r = op(best_l, w_tt=w, ng_tt=ng)
        err = abs(r["I_tt"] - 20.0)
        print(
            f"tt {w} ng={ng}: I_h={r['I_hold']:.3f} I_tt={r['I_tt']:.3f} "
            f"I_ss={r['I_ss']:.3f}"
        )
        if err < best_tt_err:
            best_tt_err = err
            best_tt = (w, ng, r)
    print(f"best_tt={best_tt[0]} ng={best_tt[1]} I_tt={best_tt[2]['I_tt']:.3f}")
    print(f"FINAL l={best_l} tt={best_tt[0]}/{best_tt[1]}")
    r = op(best_l, w_tt=best_tt[0], ng_tt=best_tt[1])
    print(
        f"verify I_hold={r['I_hold']:.3f} I_rep={r['I_rep']:.3f} "
        f"I_tt={r['I_tt']:.3f} I_ss={r['I_ss']:.3f} nbias={r['nbias']:.3f}"
    )


if __name__ == "__main__":
    main()
