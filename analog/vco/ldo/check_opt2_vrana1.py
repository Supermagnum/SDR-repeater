#!/usr/bin/env python3
"""Option (2) through VR_ANA1 at full LO current — study only, no LDO change."""
import math
import os
import subprocess

import numpy as np
from vacask.rawfile import rawread

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

VIN, VREF = 1.5, 0.55
CAP_AREA = 1.5


def side(c_ff):
    return math.sqrt(c_ff / CAP_AREA)


def run(name, text):
    path = os.path.join(OUT, name + ".sim")
    open(path, "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(open(log).read()[-1200:])


def header():
    return """parameters title="opt2 VR_ANA1"
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


def core():
    sc = side(20e3)
    return f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
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
"""


def sim_pad(iload, r, lb, tag):
    text = header() + core() + f"""
rser (vout pad) resistor r={r} noisy=1
cpad (pad 0) capacitor c=2p
cesd (pad 0) capacitor c=1p
lbond (pad pin) inductor l={lb}
cboard (pin 0) capacitor c=100n
il (pad 0) isource dc={iload}
iin (0 pad) isource dc=0
control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(vout) v(pad) v(pin)
  analysis op1 op
  analysis n1 noise in="iin" out=["pad"] values=[1Meg]
endc
"""
    run(tag, text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    n = rawread(os.path.join(OUT, "n1.raw")).get()
    vpad = float(np.real(op["pad"]).ravel()[0])
    vout = float(np.real(op["vout"]).ravel()[0])
    sv = math.sqrt(abs(float(np.real(n["onoise"]).ravel()[0])))
    return vout, vpad, sv


def main():
    print("# Option (2) through VR_ANA1 — noise at full LO current [SCH]\n")
    print("## R=5 Ω, I and L sweep")
    print("| I_load | L_bond | Vout | Vpad | IR (mV) | S_v @ 1 MHz | vs 11 nV |")
    print("|---|---|---|---|---|---|---|")
    for iload, lb in ((5e-3, 1.5e-9), (10e-3, 1e-9), (10e-3, 1.5e-9), (10e-3, 2e-9)):
        vout, vpad, sv = sim_pad(iload, 5, lb, f"opt2_i{iload*1e3:.0f}_l{lb*1e9:.1f}")
        flag = "PASS" if sv <= 11e-9 else "MISS"
        print(f"| {iload*1e3:.0f} mA | {lb*1e9:.1f} nH | {vout:.3f} | {vpad:.3f} | "
              f"{(vout-vpad)*1e3:.1f} | {sv*1e9:.2f} nV/√Hz | {flag} |")

    print("\n## R sweep at I=10 mA, L=1.5 nH (no option-1)")
    print("| R | IR @ 10 mA | S_v @ 1 MHz | vs 11 nV |")
    print("|---|---|---|---|")
    for r in (5, 6, 7, 8, 10):
        vout, vpad, sv = sim_pad(10e-3, r, 1.5e-9, f"opt2_r{r}_i10")
        flag = "PASS" if sv <= 11e-9 else "MISS"
        print(f"| {r} Ω | {r*10:.0f} mV | {sv*1e9:.2f} nV/√Hz | {flag} |")

    print("\n# |Z_pad| at divider frequencies [HAND]")
    print("Looking into pad: Cpad+ESD=3 pF || (jωL_bond to board C ≈ AC ground).\n")
    print("| f | what | L | |Z_pad| | ΔV @ 1 mA | Δf_ss (K=50 MHz/V) |")
    print("|---|---|---|---|---|---|")
    cases = [
        (1e6, "duplex-band noise"),
        (36e6, "f_ref / CP"),
        (175e6, "VHF LO out"),
        (525e6, "UHF LO out"),
        (1.4e9, "VHF CML÷3 clk"),
        (2.1e9, "UHF CML÷2 clk"),
        (4.2e9, "VCO rate"),
    ]
    for f, what in cases:
        w = 2 * math.pi * f
        for lb in (1e-9, 2e-9):
            zL = 1j * w * lb
            zC = 1 / (1j * w * 3e-12)
            z = 1 / (1 / zL + 1 / zC)
            dv = abs(z) * 1e-3  # 1 mA
            df = 50e6 * dv
            print(f"| {f/1e6:.0f} MHz | {what} | {lb*1e9:.0f} nH | {abs(z):.2f} Ω | "
                  f"{dv*1e3:.2f} mV | {df/1e3:.1f} kHz |")

    print("\nDiscrete-spur L at f_m (β = K·Vpk/f_m, L≈20log(β/2)), Vpk from 1 mA:\n")
    for f, what in cases[2:]:
        w = 2 * math.pi * f
        zL = 1j * w * 1.5e-9
        zC = 1 / (1j * w * 3e-12)
        z = abs(1 / (1 / zL + 1 / zC))
        vpk = z * 1e-3
        beta = 50e6 * vpk / f
        Ldbc = 20 * math.log10(max(beta / 2, 1e-20))
        print(f"  {what} @ {f/1e6:.0f} MHz: |Z|={z:.2f} Ω → Vpk={vpk*1e3:.2f} mV → "
              f"L≈{Ldbc:.1f} dBc (offset = f_m, not duplex)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
