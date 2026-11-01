#!/usr/bin/env python3
"""Fix LDO: polarity is NEG-FB (W∠≈0° in VACASK 1/(1+W)). Find compensation that HOLDs
then get PM≥60° (critical W=-1) with R=10/bond/100n and with C missing."""
import math
import os
import subprocess

import numpy as np
from vacask.rawfile import rawread

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
VREF = (1.2 + 9.65e-3 * 10) / 2
VIN = 2.7
I_TYP = 9.65e-3


def run(name, text):
    open(os.path.join(OUT, name + ".sim"), "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(name + "\n" + open(log).read()[-600:])


HDR = """parameters title="comp"
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


def sc(c):
    return math.sqrt(c * 1e15 / 1.5)


def net(comp, cout=100e-12, filt=None, il=5e-3, probe=False,
        mp_w=400e-6, mp_ng=80, ib=40e-6, pair_ng=4):
    """comp: netlist fragment for compensation on vg/mid."""
    if probe:
        fb = """rf1 (vout fb) resistor r=200k
rf2 (fb 0) resistor r=200k
vprobe (sense fb) vsource dc=0
"""
        g = "sense"
        # rewrite mid→sense in comp
        comp = comp.replace(" mid", " sense").replace("(mid", "(sense")
    else:
        fb = """rf1 (vout mid) resistor r=200k
rf2 (mid 0) resistor r=200k
"""
        g = "mid"
    filt_n = ""
    if filt == "rlc":
        filt_n = f"""rser (vout pad) resistor r=10
cpad (pad 0) capacitor c=2p
lbond (pad pin) inductor l=1.5n
resr (pin cbot) resistor r=0.05
cboard (cbot 0) capacitor c=100n
il (pad 0) isource dc={il}
"""
        save = "v(vout) v(pad) v(vg)"
    elif filt == "noc":
        filt_n = f"""rser (vout pad) resistor r=10
cpad (pad 0) capacitor c=2p
lbond (pad pin) inductor l=1.5n
il (pad 0) isource dc={il}
"""
        save = "v(vout) v(pad) v(vg)"
    else:
        filt_n = f"il (vout 0) isource dc={il}\n"
        save = "v(vout) v(vg)"
    return f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
mp (vout vg vin vin) sg13_lv_pmos w={mp_w} l=0.13u ng={mp_ng}
{fb}ib (vin nb) isource dc={ib}
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (d1 {g} t 0) sg13_lv_nmos w=16u l=2u ng={pair_ng}
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng={pair_ng}
m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
{comp}xout (vout 0 0) cap_rfcmim w={sc(cout):.3f}u l={sc(cout):.3f}u
{filt_n}""", save


def hold(tag, comp, **kw):
    body, save = net(comp, **kw)
    text = HDR + body + f"""
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save {save}
  analysis op1 op store="opx"
  analysis tr1 tran stop=20u step=1n nodeset="opx"
endc
"""
    run(tag, text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    vo = np.real(tr["vout"]).ravel()
    opv = float(np.real(op["vout"]).ravel()[0])
    ok = abs(vo[-1] - vo[0]) < 2e-3 and abs(vo.std()) < 1e-3 and abs(vo[-1] - opv) < 0.02
    print(f"| {tag} | OP={opv:.3f} t1={vo[-1]:.3f} d={(vo[-1]-vo[0])*1e3:.2f}mV "
          f"std={vo.std()*1e3:.3f}mV | {'HOLD' if ok else 'FAIL'} |")
    return ok, opv


def pm_from_w(freq, w):
    """PM for VACASK W in 1/(1+W): critical W=-1. PM = 180+|∠W| if ∠ near 0..-180
    at |W|=1, or equivalently how far ∠W is from ±180°."""
    mag = np.abs(w)
    ang = np.unwrap(np.angle(w)) * 180 / np.pi
    ugf = pm = None
    for i in range(len(mag) - 1):
        if (mag[i] - 1) * (mag[i + 1] - 1) <= 0 and mag[i] >= mag[i + 1]:
            t = (1 - mag[i]) / (mag[i + 1] - mag[i] + 1e-30)
            f = freq[i] + t * (freq[i + 1] - freq[i])
            a = ang[i] + t * (ang[i + 1] - ang[i])
            # distance from -180° (or +180°)
            # normalize a to (-180, 180]
            aa = ((a + 180) % 360) - 180
            # PM = 180 - |aa| when aa is the phase at UGF for W starting near 0
            # more carefully: critical phase is ±180; PM = 180 - |aa|
            p = 180.0 - abs(aa)
            # If aa is positive (lead) and W_DC was +ve, still OK
            if ugf is None or f > ugf:
                ugf, pm = f, p
    return ugf, pm


def stb(tag, comp, **kw):
    kw = dict(kw)
    kw["probe"] = True
    body, save = net(comp, **kw)
    text = HDR + body + f"""
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save {save}
  analysis op1 op
  analysis stb1 acstb probe="vprobe" from=100 to=100Meg mode="dec" points=40
endc
"""
    run(tag, text)
    stb = rawread(os.path.join(OUT, "stb1.raw")).get()
    w = np.asarray(stb["w"]).ravel()
    f = np.real(stb["frequency"]).ravel()
    wdc = complex(w[0])
    ugf, pm = pm_from_w(f, w)
    sign = "NEG-FB" if abs(np.angle(wdc, deg=True)) < 90 else "POS-FB"
    print(f"| {tag} | |W|={abs(wdc):.0f} ∠={np.angle(wdc, deg=True):.0f}° {sign} | "
          f"UGF={(ugf or 0)/1e6:.3f}MHz PM={pm if pm is not None else float('nan'):.1f}° |")
    return abs(wdc), np.angle(wdc, deg=True), ugf, pm


def soft(tag, comp, v0=0.0, **kw):
    """Ramp vref, start vout near v0 via ic through light R."""
    body, save = net(comp, **kw)
    # force soft start: ramp vin and vref together
    body = body.replace(
        f"vref (vref 0) vsource dc={VREF}",
        f'vref (vref 0) vsource type="pulse" val0=0 val1={VREF} delay=0.5u '
        f"rise=2u fall=1n width=100u period=200u",
    )
    body = body.replace(
        f"vin (vin 0) vsource dc={VIN}",
        f'vin (vin 0) vsource type="pulse" val0=0 val1={VIN} delay=0 '
        f"rise=0.2u fall=1n width=100u period=200u",
    )
    # initial condition via nodeset file is hard; use UIC with capacitor precharge
    # instead: add weak pull of vout to v0 for first 0.1us then open — skip, use
    # long settle and look at final
    text = HDR + body + f"""
control
  abort always
  options temp=27 reltol=1e-3 rawfile="binary" strictsave=1
  save {save}
  analysis tr1 tran stop=30u step=2n
endc
"""
    run(tag, text)
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    vo = np.real(tr["vout"]).ravel()
    t = np.real(tr["time"]).ravel()
    # last 5 us mean/std
    m = t > 25e-6
    mean = float(vo[m].mean())
    std = float(vo[m].std())
    ok = abs(mean - 2 * VREF) < 0.05 and std < 5e-3
    print(f"| {tag} | final={mean:.3f} std={std*1e3:.2f}mV | "
          f"{'SETTLE' if ok else 'FAIL'} |")
    return ok, mean, std


def main():
    print("# 0) Confirm tiny still holds; scale to full pass\n")
    print("| tag | | |")
    print("|---|---|---|")

    # Comp candidates on full-size LDO
    cands = [
        ("cg50", "cg (vg 0) capacitor c=50p\n"),
        ("cg200", "cg (vg 0) capacitor c=200p\n"),
        ("cg500", "cg (vg 0) capacitor c=500p\n"),
        ("cg1n", "cg (vg 0) capacitor c=1n\n"),
        ("miller5", "cc (vg mid) capacitor c=5p\n"),
        ("miller50", "cc (vg mid) capacitor c=50p\n"),
        ("rnull", "rn (vg ncc) resistor r=10k\ncc (ncc mid) capacitor c=50p\n"),
        ("cg50_co1n", "cg (vg 0) capacitor c=50p\n"),
    ]

    held = []
    for name, comp in cands:
        cout = 1e-9 if "co1n" in name else 100e-12
        try:
            ok, _ = hold(f"h_{name}", comp, cout=cout)
            if ok:
                held.append((name, comp, cout))
        except Exception as e:
            print(f"| h_{name} | EXC {str(e)[-60:]} |")

    # If none held at full size, try reducing ib / adding more C
    if not held:
        print("\n# 1) Full pass + stronger gate C / lower ib\n")
        print("| tag | | |")
        print("|---|---|---|")
        for cg in (2e-9, 5e-9, 10e-9):
            for ib in (40e-6, 10e-6, 5e-6):
                for cout in (100e-12, 1e-9, 10e-9):
                    tag = f"h_cg{cg*1e9:.0f}n_ib{ib*1e6:.0f}_co{cout*1e9:.0f}n"
                    comp = f"cg (vg 0) capacitor c={cg}\n"
                    try:
                        ok, _ = hold(tag, comp, cout=cout, ib=ib)
                        if ok:
                            held.append((tag, comp, cout, ib))
                            break
                    except Exception as e:
                        print(f"| {tag} | EXC |")
                if held:
                    break
            if held:
                break

    if not held:
        print("\n# still no hold — try source follower buffer on gate\n")
        # Buffer: OTA drives vg_pre, source follower to vg
        # Skip for now; try smaller pass first to confirm path
        for mp_ng in (8, 20, 40, 80):
            for cg in (50e-12, 200e-12, 1e-9):
                tag = f"h_ng{mp_ng}_cg{cg*1e12:.0f}p"
                comp = f"cg (vg 0) capacitor c={cg}\n"
                ok, _ = hold(tag, comp, cout=1e-9, mp_ng=mp_ng, ib=10e-6, pair_ng=1)
                if ok:
                    held.append((tag, comp, 1e-9, 10e-6, mp_ng))
                    break
            if held:
                break

    print(f"\nHeld configs: {len(held)}")
    if not held:
        print("NONE — abort")
        return 1

    # Take first held, run stb + soft-start + RLC
    best = held[0]
    name, comp = best[0], best[1]
    cout = best[2] if len(best) > 2 else 100e-12
    extra = {}
    if len(best) > 3:
        extra["ib"] = best[3]
    if len(best) > 4:
        extra["mp_ng"] = best[4]

    print(f"\n# Best hold: {name}\n")
    print("| tag | W | UGF/PM |")
    print("|---|---|---|")
    stb(f"stb_{name}_bare", comp, cout=cout, filt=None, **extra)
    stb(f"stb_{name}_rlc", comp, cout=cout, filt="rlc", il=I_TYP, **extra)
    stb(f"stb_{name}_noc", comp, cout=cout, filt="noc", il=I_TYP, **extra)

    print("\n# Soft-start / dual attractor\n")
    print("| tag | | |")
    print("|---|---|---|")
    soft(f"ss_{name}", comp, cout=cout, **extra)
    hold(f"hold_rlc_{name}", comp, cout=cout, filt="rlc", il=I_TYP, **extra)
    hold(f"hold_noc_{name}", comp, cout=cout, filt="noc", il=I_TYP, **extra)

    # Sweep cg for PM≥60 on both loads if needed
    print("\n# PM sweep on RLC / noC\n")
    print("| tag | | |")
    print("|---|---|---|")
    for cg in (50e-12, 100e-12, 200e-12, 500e-12, 1e-9, 2e-9, 5e-9):
        c = f"cg (vg 0) capacitor c={cg}\n"
        for filt in ("rlc", "noc"):
            tag = f"pm_cg{cg*1e12:.0f}_{filt}"
            try:
                # need hold first
                ok, _ = hold(f"h_{tag}", c, cout=max(cout, 100e-12), filt=filt,
                             il=I_TYP, **extra)
                if not ok:
                    continue
                stb(tag, c, cout=max(cout, 100e-12), filt=filt, il=I_TYP, **extra)
            except Exception as e:
                print(f"| {tag} | EXC {str(e)[-40:]} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
