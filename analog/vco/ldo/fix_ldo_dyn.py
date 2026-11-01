#!/usr/bin/env python3
"""Dynamic stability: waveform class, probe flip, no-Cc, big Cout, then compensate."""
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


HDR = """parameters title="dyn"
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


def ldo(cc=5e-12, cout=100e-12, rser=None, cboard=None, lb=None, esr=0.05,
        probe=None, il=5e-3):
    sc = math.sqrt(cout * 1e15 / 1.5)
    if probe == "fwd":
        fb = """rf1 (vout fb) resistor r=200k
rf2 (fb 0) resistor r=200k
vprobe (sense fb) vsource dc=0
"""
        g = "sense"
    elif probe == "rev":
        fb = """rf1 (vout fb) resistor r=200k
rf2 (fb 0) resistor r=200k
vprobe (fb sense) vsource dc=0
"""
        g = "sense"
    else:
        fb = """rf1 (vout mid) resistor r=200k
rf2 (mid 0) resistor r=200k
"""
        g = "mid"
    filt = ""
    if rser is not None:
        filt += f"rser (vout pad) resistor r={rser}\n"
        filt += "cpad (pad 0) capacitor c=2p\n"
        if lb:
            filt += f"lbond (pad pin) inductor l={lb}\n"
            node_c = "pin"
        else:
            node_c = "pad"
        if cboard:
            if esr:
                filt += f"resr ({node_c} cbot) resistor r={esr}\n"
                filt += f"cboard (cbot 0) capacitor c={cboard}\n"
            else:
                filt += f"cboard ({node_c} 0) capacitor c={cboard}\n"
        load = f"il (pad 0) isource dc={il}\n"
        out_save = "v(vout) v(pad) v(vg)"
    else:
        load = f"il (vout 0) isource dc={il}\n"
        out_save = "v(vout) v(vg)"
    cc_line = f"cc (vg {g}) capacitor c={cc}\n" if cc and cc > 0 else ""
    return f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
{fb}ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (d1 {g} t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
{cc_line}xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
{filt}{load}""", out_save


def hold(tag, **kw):
    body, save = ldo(**kw)
    text = HDR + body + f"""
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save {save}
  analysis op1 op store="opx"
  analysis tr1 tran stop=10u step=0.5n nodeset="opx"
endc
"""
    run(tag, text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    vo = np.real(tr["vout"]).ravel()
    t = np.real(tr["time"]).ravel()
    opv = float(np.real(op["vout"]).ravel()[0])
    # classify: mono drift vs ring
    zc = int(np.sum(np.diff(np.sign(vo - opv)) != 0))
    drift = vo[-1] - vo[0]
    std = vo.std() * 1e3
    hold_ok = abs(drift) < 5e-3 and std < 5
    print(f"| {tag} | OP={opv:.3f} | t1={vo[-1]:.3f} drift={drift*1e3:.1f}mV "
          f"std={std:.1f} zc={zc} | {'HOLD' if hold_ok else 'FAIL'} |")
    return hold_ok, opv, vo, t


def stb(tag, probe="fwd", **kw):
    kw = dict(kw)
    kw["probe"] = probe
    body, save = ldo(**kw)
    text = HDR + body + f"""
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save {save}
  analysis op1 op
  analysis stb1 acstb probe="vprobe" from=100 to=100Meg mode="dec" points=30
endc
"""
    run(tag, text)
    stb = rawread(os.path.join(OUT, "stb1.raw")).get()
    w = np.asarray(stb["w"]).ravel()
    f = np.real(stb["frequency"]).ravel()
    wdc = complex(w[0])
    ang0 = np.angle(wdc, deg=True)
    mag = np.abs(w)
    ang = np.unwrap(np.angle(w)) * 180 / np.pi
    ugf = pm = None
    for i in range(len(mag) - 1):
        if (mag[i] - 1) * (mag[i + 1] - 1) <= 0 and mag[i] > mag[i + 1]:
            tt = (1 - mag[i]) / (mag[i + 1] - mag[i] + 1e-30)
            ff = f[i] + tt * (f[i + 1] - f[i])
            aa = ang[i] + tt * (ang[i + 1] - ang[i])
            # PM relative to -180°
            p = aa + 180
            # normalize to (-180,180]
            while p > 180:
                p -= 360
            while p <= -180:
                p += 360
            ugf, pm = ff, p
            break
    print(f"| {tag} probe={probe} | |W|={abs(wdc):.0f} ∠={ang0:.0f}° | "
          f"UGF={((ugf or 0)/1e6):.3f}MHz PM={pm if pm is not None else float('nan'):.1f}° |")
    return abs(wdc), ang0, ugf, pm


def main():
    print("# A) Hold tests (orig polarity — DC sign is correct for PMOS)\n")
    print("| tag | OP | tran | |")
    print("|---|---|---|---|")
    hold("h_cc5_co100", cc=5e-12, cout=100e-12)
    hold("h_nocc_co100", cc=0, cout=100e-12)
    hold("h_cc5_co1n", cc=5e-12, cout=1e-9)
    hold("h_cc50_co10n", cc=50e-12, cout=10e-9)
    hold("h_cc5_co100_rc", cc=5e-12, cout=100e-12, rser=10, cboard=100e-9, lb=1.5e-9)

    print("\n# B) stb probe orientation (expect NEG-FB ∠≈±180° for correct return ratio)\n")
    print("| tag | W_DC | UGF/PM |")
    print("|---|---|---|")
    stb("stb_fwd", probe="fwd", cc=5e-12, cout=100e-12)
    stb("stb_rev", probe="rev", cc=5e-12, cout=100e-12)

    # If hold fails everywhere, try adding series Rnull with Cc + bigger Cout
    print("\n# C) Nulling R + Cout sweep for HOLD\n")
    print("| tag | | |")
    print("|---|---|---|")
    found = None
    for cc in (2e-12, 10e-12, 50e-12):
        for rn in (0, 2e3, 10e3, 50e3):
            for cout in (200e-12, 2e-9, 20e-9):
                # rebuild with rnull manually
                sc = math.sqrt(cout * 1e15 / 1.5)
                if rn:
                    comp = f"rn (vg ncc) resistor r={rn}\ncc (ncc mid) capacitor c={cc}\n"
                else:
                    comp = f"cc (vg mid) capacitor c={cc}\n"
                text = HDR + f"""
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
{comp}xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
il (vout 0) isource dc=5m
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save v(vout)
  analysis op1 op store="opx"
  analysis tr1 tran stop=10u step=0.5n nodeset="opx"
endc
"""
                tag = f"n_c{cc*1e12:.0f}_r{rn/1e3:.0f}_o{cout*1e9:.0f}n"
                try:
                    run(tag, text)
                    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
                    vo = np.real(tr["vout"]).ravel()
                    op = rawread(os.path.join(OUT, "op1.raw")).get()
                    opv = float(np.real(op["vout"]).ravel()[0])
                    ok = abs(vo[-1] - vo[0]) < 5e-3 and abs(vo[-1] - opv) < 0.05
                    if ok:
                        print(f"| {tag} | OP={opv:.3f} HOLD |")
                        found = (cc, rn, cout)
                        break
                except Exception:
                    pass
            if found:
                break
        if found:
            break
    if not found:
        print("| (none held) | | |")
        # Try reducing OTA gm: smaller pair / less bias — structural
        print("\n# D) Lower OTA gain (ibias 10u, pair ng=1)\n")
        for ib, ng in ((10e-6, 1), (5e-6, 1), (40e-6, 1)):
            sc = math.sqrt(1e9 / 1.5)  # 1nF
            text = HDR + f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
rf1 (vout mid) resistor r=200k
rf2 (mid 0) resistor r=200k
ib (vin nb) isource dc={ib}
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (d1 mid t 0) sg13_lv_nmos w=16u l=2u ng={ng}
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng={ng}
m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
cc (vg mid) capacitor c=20p
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
il (vout 0) isource dc=5m
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save v(vout)
  analysis op1 op store="opx"
  analysis tr1 tran stop=10u step=0.5n nodeset="opx"
endc
"""
            tag = f"gm_ib{ib*1e6:.0f}_ng{ng}"
            run(tag, text)
            tr = rawread(os.path.join(OUT, "tr1.raw")).get()
            vo = np.real(tr["vout"]).ravel()
            opv = float(np.real(rawread(os.path.join(OUT, "op1.raw")).get()["vout"]).ravel()[0])
            ok = abs(vo[-1] - vo[0]) < 5e-3
            print(f"| {tag} | OP={opv:.3f} t1={vo[-1]:.3f} | {'HOLD' if ok else 'FAIL'} |")
            if ok:
                found = ("gm", ib, ng)
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
