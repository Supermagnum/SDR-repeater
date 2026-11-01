#!/usr/bin/env python3
"""D10 VCO-supply LDO — first schematic noise vs ≤ 11 nV/√Hz at 1 MHz [SCH].

PMOS-pass LDO from VR_ANA1 stand-in (1.5 V) to VDD_VCO (1.1 V), I_load = 5 mA.
Single-stage OTA (NMOS pair + PMOS mirror) drives the pass gate. Output MIM C_out.
If bare S_v misses 11 nV/√Hz, propose an RC post-filter with area and IR drop.

    mkdir -p out && python3 -u run_ldo_noise.py | tee out/summary_ldo_noise.txt
"""
import math
import os
import subprocess
import sys

import numpy as np
from vacask.rawfile import rawread

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
LIMIT = 11e-9
CAP_AREA = 1.5  # fF/µm²
VIN, VOUT, ILOAD = 1.5, 1.1, 5e-3
VREF = VOUT / 2  # 0.55 V with 1:1 feedback


def side(c_ff):
    return math.sqrt(c_ff / CAP_AREA)


def run(name, text):
    path = os.path.join(OUT, name + ".sim")
    open(path, "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(open(log).read()[-1200:])
    return log


def deck(cout_f, tag, rc_r=None, rc_c=None):
    sc = side(cout_f * 1e15)
    filt = ""
    node = "vout"
    if rc_r is not None and rc_c is not None:
        sf = side(rc_c * 1e15)
        filt = (f"rfil (vout vfil) resistor r={rc_r:g}\n"
                f"xfil (vfil 0 0) cap_rfcmim w={sf:.3f}u l={sf:.3f}u\n")
        node = "vfil"
    return f"""parameters title="D10 VCO LDO noise {tag}"

include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section=mos_tt
include "cornerCAP.lib" section=cap_typ
load "resistor.osdi"
load "capacitor.osdi"
model resistor resistor
model capacitor capacitor
model vsource vsource
model isource isource

vin (vin 0) vsource dc={VIN}
vref (vref 0) vsource dc={VREF}
// PMOS pass (source=vin, drain=vout, gate=vg)
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
// 1:1 feedback
rf1 (vout mid) resistor r=200k noisy=1
rf2 (mid 0) resistor r=200k noisy=1
// OTA: when mid>vref, vg rises → pass turns off
ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (d1 mid t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
cc (vg mid) capacitor c=500f
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
{filt}il ({node} 0) isource dc={ILOAD}
iin (0 {node}) isource dc=0

control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(vout) v(vg) v(mid)
  analysis op1 op
  analysis n1 noise in="iin" out=["{node}"] values=[1Meg]
endc
"""


def sv_from_raw():
    d = rawread(os.path.join(OUT, "n1.raw")).get()
    o = float(np.real(d["onoise"]).ravel()[0])
    return math.sqrt(abs(o))  # VACASK onoise is V²/Hz


def main():
    print("# D10 VCO LDO output noise vs ≤ 11 nV/√Hz @ 1 MHz [SCH]\n")
    print(f"First schematic (no prior LDO deck): PMOS pass, single-stage OTA, "
          f"Vref={VREF} V, Vin={VIN} V → Vout≈{VOUT} V, I_load={ILOAD*1e3:.0f} mA.\n")

    cases = [("c_20p", 20e-12), ("c_50p", 50e-12), ("c_100p", 100e-12), ("c_200p", 200e-12)]
    print("| Tag | C_out | side (µm) | area (µm²) | Vout | Vg | S_v @ 1 MHz | vs 11 nV |")
    print("|---|---|---|---|---|---|---|---|")
    results = []
    for tag, c in cases:
        run(f"ldo_{tag}", deck(c, tag))
        op = rawread(os.path.join(OUT, "op1.raw")).get()
        vout = float(np.real(op["vout"]).ravel()[0])
        vg = float(np.real(op["vg"]).ravel()[0])
        sv = sv_from_raw()
        area = c * 1e15 / CAP_AREA
        reg_ok = abs(vout - VOUT) < 0.05
        ok = "PASS" if (sv <= LIMIT and reg_ok) else ("MISS" if reg_ok else "NO-REG")
        print(f"| {tag} | {c*1e12:.0f} pF | {side(c*1e15):.1f} | {area:.0f} | "
              f"{vout:.3f} | {vg:.3f} | {sv*1e9:.1f} nV/√Hz | {ok} |")
        results.append(dict(tag=tag, c=c, sv=sv, vout=vout, vg=vg, area=area, reg=reg_ok))

    regs = [r for r in results if r["reg"]]
    if not regs:
        print("\nRESULT: LDO OP did not regulate — fix the schematic before noise gate.")
        return 1
    best = min(regs, key=lambda r: r["sv"])
    print()
    if best["sv"] <= LIMIT:
        print(f"RESULT: PASS with {best['tag']} — S_v={best['sv']*1e9:.1f} nV/√Hz ≤ 11 "
              f"(C_out area {best['area']:.0f} µm²).")
        return 0

    bare = best["sv"]
    need = bare / LIMIT
    # fc such that |H|=1/need at 1 MHz: need = sqrt(1+(f/fc)^2) → fc = f/sqrt(need²-1)
    fc_need = 1e6 / math.sqrt(need ** 2 - 1)
    print(f"RESULT: MISS — best regulating S_v={bare*1e9:.1f} nV/√Hz > 11 "
          f"(~{need:.1f}× too high). Closed-loop Rout is low: MIM 20–200 pF barely helps.\n")
    print(f"For ≥{need:.1f}× at 1 MHz need f_c ≤ {fc_need/1e3:.0f} kHz on a post RC.\n")

    # Use ideal capacitor (area as MIM equivalent + MOS-cap note) for large C trials.
    def deck_bigc(cout_f, tag, rc_r, rc_c):
        sc = side(cout_f * 1e15)
        return f"""parameters title="D10 VCO LDO noise {tag}"

include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section=mos_tt
include "cornerCAP.lib" section=cap_typ
load "resistor.osdi"
load "capacitor.osdi"
model resistor resistor
model capacitor capacitor
model vsource vsource
model isource isource

vin (vin 0) vsource dc={VIN}
vref (vref 0) vsource dc={VREF}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
rf1 (vout mid) resistor r=200k noisy=1
rf2 (mid 0) resistor r=200k noisy=1
ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (d1 mid t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
cc (vg mid) capacitor c=500f
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
rfil (vout vfil) resistor r={rc_r:g}
cfil (vfil 0) capacitor c={rc_c:.6g}
il (vfil 0) isource dc={ILOAD}
iin (0 vfil) isource dc=0

control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(vout) v(vg) v(mid) v(vfil)
  analysis op1 op
  analysis n1 noise in="iin" out=["vfil"] values=[1Meg]
endc
"""

    print("| R (Ω) | C | f_c (kHz) | MIM-eq area | MOS-cap ~5 fF/µm² | IR @ 5 mA | S_v @ 1 MHz |")
    print("|---|---|---|---|---|---|---|")
    filt_ok = None
    proposals = [
        (5, 100e-9), (5, 220e-9), (10, 47e-9), (10, 100e-9), (10, 220e-9),
        (20, 47e-9), (20, 68e-9), (20, 100e-9), (50, 22e-9), (50, 47e-9),
    ]
    for r, c in proposals:
        tag = f"fil_r{r}_c{c*1e9:.1f}n"
        run(f"ldo_{tag}", deck_bigc(50e-12, tag, r, c))
        op = rawread(os.path.join(OUT, "op1.raw")).get()
        vout = float(np.real(op["vout"]).ravel()[0])
        sv = sv_from_raw()
        fc = 1 / (2 * math.pi * r * c)
        mim = c * 1e15 / CAP_AREA
        mos = c * 1e15 / 5.0
        print(f"| {r} | {c*1e9:.1f} nF | {fc/1e3:.0f} | {mim/1e6:.1f} mm² | "
              f"{mos/1e6:.2f} mm² | {ILOAD*r*1e3:.0f} mV | {sv*1e9:.1f} |")
        if sv <= LIMIT and abs(vout - VOUT) < 0.08 and filt_ok is None:
            filt_ok = (r, c, sv, mim, mos, ILOAD * r)
    print()
    if filt_ok:
        r, c, sv, mim, mos, ir = filt_ok
        print(f"PROPOSAL [HAND]+[SCH]: series R={r} Ω + shunt C={c*1e9:.1f} nF after the LDO "
              f"(S_v≈{sv*1e9:.1f} nV/√Hz, IR {ir*1e3:.0f} mV @ 5 mA).")
        print(f"  Area: MIM-equivalent {mim/1e6:.1f} mm² (not practical on-chip as rfcmim); "
              f"thin-oxide MOS ~{mos/1e6:.2f} mm²; or one off-chip 0402/0201.")
        print("  Alternative: redesign LDO for ~10 nV/√Hz bare (more bias / quieter refs) "
              "and keep small on-chip C only.")
        print("STOP for owner decision on the filter / LDO redesign.")
    else:
        print("STOP for owner — listed RC did not hit 11 nV/√Hz; need still larger C or quieter LDO.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
