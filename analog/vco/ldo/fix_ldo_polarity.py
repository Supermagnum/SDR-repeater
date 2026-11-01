#!/usr/bin/env python3
"""D21 LDO: loop polarity, dual start-up, stb gain sign. Fix if inverted."""
import math
import os
import subprocess

import numpy as np
from vacask.rawfile import rawread

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

I_TYP = 9.65e-3
R = 10.0
VL = 1.2 + I_TYP * R
VREF = VL / 2
VIN = 2.7


def run(name, text):
    open(os.path.join(OUT, name + ".sim"), "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(open(log).read()[-1200:])


HDR = """parameters title="ldo polarity"
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


def core(polarity="orig", cc=5e-12, cout=50e-12, probe=False):
    """polarity: orig = mid→m1, vref→m2, out=vg (m2 drain)
                 swap = vref→m1, mid→m2, out=vg (m2 drain)  [feedback on output side]
    """
    sc = math.sqrt(cout * 1e15 / 1.5)
    if polarity == "orig":
        # feedback (mid) on diode/mirror branch; ref on output branch
        pair = """m1 (d1 mid t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
"""
    else:
        # feedback (mid) on output branch; ref on diode/mirror branch
        pair = """m1 (d1 vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg mid t 0) sg13_lv_nmos w=16u l=2u ng=4
"""
    if probe:
        fb = """rf1 (vout fb) resistor r=200k
rf2 (fb 0) resistor r=200k
vprobe (sense fb) vsource dc=0
"""
        # reconnect pair gates through sense for mid side
        if polarity == "orig":
            pair = """m1 (d1 sense t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
"""
        else:
            pair = """m1 (d1 vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg sense t 0) sg13_lv_nmos w=16u l=2u ng=4
"""
        mid_node = "sense"
    else:
        fb = """rf1 (vout mid) resistor r=200k
rf2 (mid 0) resistor r=200k
"""
        mid_node = "mid"
    return f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
{fb}ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
{pair}m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
cc (vg {mid_node}) capacitor c={cc}
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
il (vout 0) isource dc=5m
"""


def op_and_hold(tag, pol):
    text = HDR + core(pol) + """
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save v(vout) v(vg) v(mid)
  analysis op1 op store="opx"
  analysis tr1 tran stop=5u step=1n nodeset="opx"
endc
"""
    run(tag, text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    vo = np.real(tr["vout"]).ravel()
    opv = float(np.real(op["vout"]).ravel()[0])
    vg = float(np.real(op["vg"]).ravel()[0])
    drift = (vo[-1] - vo[0]) * 1e3
    hold = abs(vo[-1] - vo[0]) < 10e-3 and abs(vo[-1] - opv) < 0.05
    print(f"| {tag} | OP={opv:.3f} vg={vg:.3f} | t0={vo[0]:.3f} t1={vo[-1]:.3f} "
          f"drift={drift:.1f}mV | {'HOLD' if hold else 'DRIFT'} |")
    return hold, opv


def soft_start(tag, pol, vstart):
    """Ramp vin; init-like start by ramping from vstart context via PWL vin."""
    # Use pulse vin 0→VIN or VIN held; for "from Vin" start with vin already VIN
    # and vout precharged via large C ic — VACASK may not support ic; use
    # slow ramp of load and watch settle.
    sc = math.sqrt(50e3 / 1.5)
    if pol == "orig":
        pair = """m1 (d1 mid t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
"""
    else:
        pair = """m1 (d1 vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg mid t 0) sg13_lv_nmos w=16u l=2u ng=4
"""
    if vstart < 0.1:
        vin_line = f'vin (vin 0) vsource type="pulse" val0=0 val1={VIN} delay=0 rise=20u fall=1u width=1'
    else:
        # start at Vin already; force soft output by ramping vref
        vin_line = f"vin (vin 0) vsource dc={VIN}"
    text = HDR + f"""
vref (vref 0) vsource type="pulse" val0=0 val1={VREF} delay=5u rise=10u fall=1u width=1
{vin_line}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
rf1 (vout mid) resistor r=200k
rf2 (mid 0) resistor r=200k
ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
{pair}m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
cc (vg mid) capacitor c=5p
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
il (vout 0) isource dc=5m
control
  abort always
  options temp=27 reltol=1e-3 rawfile="binary" strictsave=1
  save v(vout) v(vg) v(vin) v(vref)
  analysis tr1 tran stop=80u step=20n
endc
"""
    run(tag, text)
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    t = np.real(tr["time"]).ravel()
    vo = np.real(tr["vout"]).ravel()
    late = vo[t > 60e-6]
    print(f"| {tag} | start≈{vstart:.1f} | final={late.mean():.3f} "
          f"std={late.std()*1e3:.1f}mV min={vo.min():.2f} max={vo.max():.2f} |")
    return float(late.mean())


def stb(tag, pol):
    text = HDR + core(pol, probe=True) + """
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save v(vout) v(vg)
  analysis op1 op
  analysis stb1 acstb probe="vprobe" from=1k to=100Meg mode="dec" points=20
endc
"""
    run(tag, text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    stb = rawread(os.path.join(OUT, "stb1.raw")).get()
    w = np.asarray(stb["w"]).ravel()
    f = np.real(stb["frequency"]).ravel()
    wdc = complex(w[0])
    ang0 = np.angle(wdc, deg=True)
    mag = np.abs(w)
    ang = np.angle(w, deg=True)
    ugf = pm = None
    for i in range(len(mag) - 1):
        if (mag[i] - 1) * (mag[i + 1] - 1) <= 0:
            tt = (1 - mag[i]) / (mag[i + 1] - mag[i] + 1e-30)
            ff = f[i] + tt * (f[i + 1] - f[i])
            aa = ang[i] + tt * (ang[i + 1] - ang[i])
            p = aa + 180
            while p > 180:
                p -= 360
            while p <= -180:
                p += 360
            if ugf is None or ff > ugf:
                ugf, pm = ff, p
    sign = "NEG-FB" if abs(ang0) > 90 else "POS-FB"
    print(f"| {tag} | OP={float(np.real(op['vout']).ravel()[0]):.3f} | "
          f"|W_DC|={abs(wdc):.0f} ∠={ang0:.0f}° {sign} | "
          f"UGF={((ugf or 0)/1e6):.2f}MHz PM={pm if pm is not None else float('nan'):.1f}° |")
    return sign, pm, ang0


def main():
    print("# 1) Polarity: OP hold + stb gain sign\n")
    print("| case | OP | tran | |")
    print("|---|---|---|---|")
    for pol in ("orig", "swap"):
        op_and_hold(f"hold_{pol}", pol)
    print("\n| stb | OP | W_DC | UGF/PM |")
    print("|---|---|---|---|")
    results = {}
    for pol in ("orig", "swap"):
        results[pol] = stb(f"stb_{pol}", pol)

    print("\n# 2) Soft-start from 0 and from Vin (vref ramp)\n")
    print("| case | | settle |")
    print("|---|---|---|")
    for pol in ("orig", "swap"):
        soft_start(f"start0_{pol}", pol, 0.0)
        soft_start(f"startVin_{pol}", pol, VIN)

    # Pick polarity: NEG-FB and HOLD preferred
    print("\n# Verdict")
    for pol, (sign, pm, ang0) in results.items():
        print(f"  {pol}: {sign}, PM={pm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
