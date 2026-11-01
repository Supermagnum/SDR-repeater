#!/usr/bin/env python3
"""D21 LDO stability sweep: Cc, on-chip Cout, board ESR; with/without 100 nF."""
import math
import os
import subprocess

import numpy as np
from vacask.rawfile import rawread

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

I_TYP = 9.65e-3
R_NOM = 10.0
V_LDO_NOM = 1.2 + I_TYP * R_NOM
VREF = V_LDO_NOM / 2
VIN = 2.7
CAP_AREA = 1.5


def side(c_ff):
    return math.sqrt(max(c_ff, 1.0) / CAP_AREA)


def run(name, text):
    open(os.path.join(OUT, name + ".sim"), "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(open(log).read()[-1200:])


def hdr():
    return """parameters title="D21 stab sweep"
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


def deck(cc=2e-12, cout=50e-12, cboard=100e-9, esr=50e-3, lb=1.5e-9):
    sc = side(cout * 1e15)
    cb = ""
    if cboard and cboard > 0:
        if esr and esr > 0:
            cb = (f"resr (pin cbot) resistor r={esr}\n"
                  f"cboard (cbot 0) capacitor c={cboard:.6g}\n")
        else:
            cb = f"cboard (pin 0) capacitor c={cboard:.6g}\n"
    return hdr() + f"""
vref (vref 0) vsource dc={VREF:.8g}
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
cc (vg mid) capacitor c={cc:.6g}
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
rser (vout pad) resistor r={R_NOM}
cpad (pad 0) capacitor c=2p
cesd (pad 0) capacitor c=1p
lbond (pad pin) inductor l={lb}
{cb}il0 (pad 0) isource dc=5m
il1 (pad 0) isource type="pulse" val0=0 val1=5m delay=5u rise=20n fall=20n width=20u period=100u
control
  abort always
  options temp=27 reltol=1e-3 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis tr1 tran stop=25u step=2n
endc
"""


def verdict_tran(tag, text):
    run(tag, text)
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    t = np.real(tr["time"]).ravel()
    vp = np.real(tr["pad"]).ravel()
    vo = np.real(tr["vout"]).ravel()
    pre = vp[(t > 3e-6) & (t < 4.5e-6)]
    post = vp[(t > 15e-6) & (t < 20e-6)]
    vo_post = vo[(t > 15e-6) & (t < 20e-6)]
    early = vp[(t > 5.05e-6) & (t < 8e-6)]
    if len(pre) < 10 or len(post) < 10:
        return None
    dlt = (post.mean() - pre.mean()) * 1e3
    std = vo_post.std() * 1e3
    pre_ok = abs(pre.mean() - (V_LDO_NOM - 0.05)) < 0.08
    step_ok = abs(dlt + 50) < 30
    quiet = std < 5
    # overshoot beyond IR
    over = (early.min() - pre.mean()) * 1e3 if len(early) else 0
    if pre_ok and step_ok and quiet:
        v = "STABLE"
    elif std > 50 or not pre_ok:
        v = "OSC"
    else:
        v = "CHECK"
    return dict(pre=pre.mean(), post=post.mean(), dlt=dlt, std=std,
                over=over, v=v, emin=early.min() if len(early) else 0,
                emax=early.max() if len(early) else 0)


def main():
    print(f"V_LDO={V_LDO_NOM:.4f} V (pad≈1.20 @ {I_TYP*1e3:.2f} mA)\n")
    print("# Sweep with board 100 nF\n")
    print("| Cc | Cout | ESR | pre | ΔmV | std mV | over mV | verdict |")
    print("|---|---|---|---|---|---|---|---|")
    best = None
    for cc in (0.5e-12, 2e-12, 5e-12, 10e-12):
        for cout in (20e-12, 50e-12, 100e-12, 200e-12):
            for esr in (0.0, 0.05, 0.2):
                tag = f"s_cc{cc*1e12:.0f}_co{cout*1e12:.0f}_e{esr*1e3:.0f}"
                try:
                    r = verdict_tran(tag, deck(cc=cc, cout=cout, esr=esr))
                except Exception as e:
                    print(f"| {cc*1e12:.0f}p | {cout*1e12:.0f}p | {esr*1e3:.0f}m | "
                          f"FAIL | — | — | — | {str(e)[-40:]} |")
                    continue
                if not r:
                    continue
                print(f"| {cc*1e12:.0f}p | {cout*1e12:.0f}p | {esr*1e3:.0f}mΩ | "
                      f"{r['pre']:.3f} | {r['dlt']:.1f} | {r['std']:.1f} | "
                      f"{r['over']:.1f} | {r['v']} |")
                if r["v"] == "STABLE" and (
                        best is None or cout < best["cout"] or
                        (cout == best["cout"] and cc < best["cc"])):
                    best = dict(cc=cc, cout=cout, esr=esr, **r)

    if best:
        print(f"\nBest small stable: Cc={best['cc']*1e12:.0f} pF, "
              f"Cout={best['cout']*1e12:.0f} pF, ESR={best['esr']*1e3:.0f} mΩ\n")
        # Missing C with same compensation
        print("# Same compensation, board C missing\n")
        tag = "miss_best"
        try:
            r = verdict_tran(tag, deck(cc=best["cc"], cout=best["cout"],
                                       cboard=0.0, esr=0.0))
            if r:
                print(f"missing C: pre={r['pre']:.3f} Δ={r['dlt']:.1f} mV "
                      f"std={r['std']:.1f} mV → {r['v']}")
                print(f"  early pad {r['emin']:.3f} .. {r['emax']:.3f} V")
        except Exception as e:
            print(f"missing C: FAIL {e}")
        # Also missing C but with large on-chip only
        print("\n# Missing board C, large on-chip Cout only\n")
        for cout in (200e-12, 500e-12, 1e-9):
            tag = f"miss_co{cout*1e12:.0f}"
            try:
                r = verdict_tran(tag, deck(cc=best["cc"], cout=cout,
                                           cboard=0.0, esr=0.0))
                if r:
                    print(f"Cout={cout*1e12:.0f}p: pre={r['pre']:.3f} "
                          f"Δ={r['dlt']:.1f} std={r['std']:.1f} → {r['v']}")
            except Exception as e:
                print(f"Cout={cout*1e12:.0f}p: FAIL")
    else:
        print("\nNo STABLE point in sweep — expand range.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
