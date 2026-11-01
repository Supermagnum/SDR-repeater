#!/usr/bin/env python3
"""Verify fixed LDO (Cg=100p + Rz=500, no Miller-to-mid): polarity, dual start,
PM≥60 RLC/noC, then noise + pad V + 1mA / 0.3V steps."""
import math
import os
import subprocess
import sys

import numpy as np
from vacask.rawfile import rawread

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
I_TYP = 9.65e-3
R = 10.0
VL = 1.2 + I_TYP * R
VREF = VL / 2
VIN = 2.7
LIMIT = 11e-9

# Fixed compensation: series Rz + Cg to gnd (NOT Miller to mid — that was the bug)
COMP = """rz (vg ncg) resistor r=500
cg (ncg 0) capacitor c=100p
"""
COUT = 100e-12


def run(name, text):
    open(os.path.join(OUT, name + ".sim"), "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(name + "\n" + open(log).read()[-800:])


HDR = """parameters title="ldo_verify"
include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section=mos_tt
include "cornerCAP.lib" section=cap_typ
include "cornerRES.lib" section=res_typ
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


def ldo(probe=False, filt="rlc", il=None, vin_dc=VIN, noisy=False):
    if il is None:
        il = I_TYP
    g = "sense" if probe else "mid"
    if probe:
        fb = """rf1 (vout fb) resistor r=200k
rf2 (fb 0) resistor r=200k
vprobe (sense fb) vsource dc=0
"""
    else:
        fb = """rf1 (vout mid) resistor r=200k
rf2 (mid 0) resistor r=200k
"""
    nflag = "noisy=1" if noisy else "noisy=0"
    # feedback R always present; series R for filter
    if filt == "rlc":
        load = f"""rser (vout pad) resistor r={R} {nflag}
cpad (pad 0) capacitor c=2p
cesd (pad 0) capacitor c=1p
lbond (pad pin) inductor l=1.5n
resr (pin cbot) resistor r=0.05
cboard (cbot 0) capacitor c=100n
il (pad 0) isource dc={il}
"""
        save = "v(vout) v(pad) v(vg)"
    elif filt == "noc":
        load = f"""rser (vout pad) resistor r={R} {nflag}
cpad (pad 0) capacitor c=2p
cesd (pad 0) capacitor c=1p
lbond (pad pin) inductor l=1.5n
il (pad 0) isource dc={il}
"""
        save = "v(vout) v(pad) v(vg)"
    else:
        load = f"il (vout 0) isource dc={il}\n"
        save = "v(vout) v(vg)"
    return f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={vin_dc}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
{fb}ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (d1 {g} t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
{COMP}xout (vout 0 0) cap_rfcmim w={sc(COUT):.3f}u l={sc(COUT):.3f}u
{load}""", save


def pm_from_w(freq, w):
    mag = np.abs(w)
    ang = np.unwrap(np.angle(w)) * 180 / np.pi
    ugf = pm = None
    for i in range(len(mag) - 1):
        if (mag[i] - 1) * (mag[i + 1] - 1) <= 0 and mag[i] >= mag[i + 1]:
            t = (1 - mag[i]) / (mag[i + 1] - mag[i] + 1e-30)
            f = freq[i] + t * (freq[i + 1] - freq[i])
            a = ang[i] + t * (ang[i + 1] - ang[i])
            aa = ((a + 180) % 360) - 180
            p = 180.0 - abs(aa)
            if ugf is None or f > ugf:
                ugf, pm = f, p
    return ugf, pm


def section_polarity():
    print("# 1) Polarity + dual OP (fixed compensation)\n")
    print("Open-loop DC: mid↑→vg↑ = CORRECT for PMOS NEG-FB.")
    print("VACASK W∠≈0° means NEG-FB in 1/(1+W). Miller-to-mid was the bug.\n")
    print("| case | OP | tran | |")
    print("|---|---|---|---|")
    for tag, filt in (("hold_bare", "bare"), ("hold_rlc", "rlc"),
                      ("hold_noc", "noc")):
        body, save = ldo(filt=filt)
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
        ok = abs(vo[-1] - vo[0]) < 2e-3 and vo.std() < 1e-3
        print(f"| {tag} | OP={opv:.3f} | t1={vo[-1]:.3f} "
              f"d={(vo[-1]-vo[0])*1e3:.2f}mV | {'HOLD' if ok else 'FAIL'} |")

    # Soft-start from 0 and near-Vin precharge via long ramp
    print("\n| soft-start | final | |")
    print("|---|---|---|")
    for name, vinit_note in (("start0", "from 0"), ("startVin", "vin first")):
        body, save = ldo(filt="rlc")
        if name == "start0":
            body = body.replace(
                f"vref (vref 0) vsource dc={VREF}",
                f'vref (vref 0) vsource type="pulse" val0=0 val1={VREF} '
                f"delay=1u rise=5u fall=1n width=200u period=400u",
            )
            body = body.replace(
                f"vin (vin 0) vsource dc={VIN}",
                f'vin (vin 0) vsource type="pulse" val0=0 val1={VIN} '
                f"delay=0 rise=0.5u fall=1n width=200u period=400u",
            )
            stop = 40e-6
        else:
            # Vin already up; ramp only vref — start with vout near Vin via
            # weak pull that opens after 0.5u (approx)
            body = body.replace(
                f"vref (vref 0) vsource dc={VREF}",
                f'vref (vref 0) vsource type="pulse" val0=0 val1={VREF} '
                f"delay=2u rise=5u fall=1n width=200u period=400u",
            )
            # precharge pad/vout toward Vin with a gated current into vout
            body += f"""
ipre (vin vout) isource type="pulse" val0=2m val1=0 delay=1.5u rise=10n fall=10n width=1u period=400u
"""
            stop = 40e-6
        text = HDR + body + f"""
control
  abort always
  options temp=27 reltol=1e-3 rawfile="binary" strictsave=1
  save {save}
  analysis tr1 tran stop={stop} step=2n
endc
"""
        run(name, text)
        tr = rawread(os.path.join(OUT, "tr1.raw")).get()
        t = np.real(tr["time"]).ravel()
        vo = np.real(tr["vout"]).ravel()
        m = t > (stop - 5e-6)
        mean, std = float(vo[m].mean()), float(vo[m].std())
        ok = abs(mean - VL) < 0.05 and std < 5e-3
        print(f"| {name} ({vinit_note}) | {mean:.3f}±{std*1e3:.1f}mV | "
              f"{'SETTLE' if ok else 'CHECK'} |")


def section_stb():
    print("\n# 2) stb loop gain (VACASK W in 1/(1+W); NEG-FB ⇒ ∠≈0°)\n")
    print("| case | W_DC | UGF | PM | |")
    print("|---|---|---|---|---|")
    results = {}
    for filt in ("rlc", "noc"):
        body, save = ldo(probe=True, filt=filt)
        text = HDR + body + f"""
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save {save}
  analysis op1 op
  analysis stb1 acstb probe="vprobe" from=100 to=100Meg mode="dec" points=40
endc
"""
        run(f"stb_{filt}", text)
        op = rawread(os.path.join(OUT, "op1.raw")).get()
        stb = rawread(os.path.join(OUT, "stb1.raw")).get()
        w = np.asarray(stb["w"]).ravel()
        f = np.real(stb["frequency"]).ravel()
        wdc = complex(w[0])
        ugf, pm = pm_from_w(f, w)
        sign = "NEG-FB" if abs(np.angle(wdc, deg=True)) < 90 else "POS-FB"
        ok = "PASS" if (pm is not None and pm >= 60) else "MISS"
        pad_key = "pad" if "pad" in op else "vout"
        pad = float(np.real(op[pad_key]).ravel()[0])
        print(f"| {filt} | |W|={abs(wdc):.0f} ∠={np.angle(wdc,deg=True):.0f}° "
              f"{sign} | {(ugf or 0)/1e6:.3f} MHz | {pm:.1f}° | {ok} |")
        results[filt] = dict(pm=pm, ugf=ugf, pad=pad)
    return results


def section_noise_pad():
    print("\n# 3) Noise @ 1 MHz + pad voltage table (fixed LDO)\n")
    rows = []
    for lab, il in (("typ 9.65 mA", I_TYP), ("10 mA", 10e-3)):
        body, save = ldo(filt="rlc", il=il, noisy=True)
        body += 'iin (0 pad) isource dc=0\n'
        text = HDR + body + f"""
control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save {save}
  analysis op1 op
  analysis n1 noise in="iin" out=["pad"] values=[1Meg]
endc
"""
        run(f"noise_{lab.replace(' ', '_')}", text)
        op = rawread(os.path.join(OUT, "op1.raw")).get()
        n = rawread(os.path.join(OUT, "n1.raw")).get()
        vpad = float(np.real(op["pad"]).ravel()[0])
        vout = float(np.real(op["vout"]).ravel()[0])
        sv1 = math.sqrt(abs(float(np.real(n["onoise"]).ravel()[0])))
        gate = "PASS" if sv1 <= LIMIT else "MISS"
        rows.append((lab, vout, vpad, sv1, gate))
    print("| I | V_LDO | V_pad | S_v @ 1 MHz | vs 11 nV |")
    print("|---|---|---|---|---|")
    for lab, vo, vp, s, g in rows:
        print(f"| {lab} | {vo:.4f} | {vp:.4f} | {s*1e9:.2f} nV/√Hz | {g} |")
    print()
    sv1 = rows[-1][3]  # 10 mA figure (matches prior 9.5 claim)
    vpad = rows[0][2]
    vout = rows[0][1]
    print(f"V_out={vout:.4f} V  V_pad={vpad:.4f} V  (target pad typ 1.20 V)\n")

    # Pad voltage table: corners of I and Vin
    print("| Vin | I_load | V_out | V_pad | ΔV_R | worst≥1.08 |")
    print("|---|---|---|---|---|---|")
    for vin in (1.8, 2.7, 3.3):
        for il in (1e-3, I_TYP, 15e-3):
            try:
                body, save = ldo(filt="rlc", il=il, vin_dc=vin)
                text = HDR + body + f"""
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save {save}
  analysis op1 op
endc
"""
                run(f"pad_vin{vin*10:.0f}_i{il*1e3:.0f}", text)
                op = rawread(os.path.join(OUT, "op1.raw")).get()
                vo = float(np.real(op["vout"]).ravel()[0])
                vp = float(np.real(op["pad"]).ravel()[0])
                ok = "OK" if vp >= 1.08 else "LOW"
                print(f"| {vin:.1f} | {il*1e3:.2f} mA | {vo:.3f} | {vp:.3f} | "
                      f"{(vo-vp)*1e3:.1f} mV | {ok} |")
            except Exception as e:
                print(f"| {vin:.1f} | {il*1e3:.2f} mA | FAIL | | | "
                      f"{str(e).splitlines()[-1][:40]} |")
    return sv1, vpad


def section_steps():
    print("\n# 4) Line / load steps (1 mA LO step, 0.3 V VBAT step)\n")
    print("| step | ΔVpk (mV) | settle | note |")
    print("|---|---|---|---|")
    # Load step: I_TYP → I_TYP+1mA on pad
    body, _ = ldo(filt="rlc", il=I_TYP)
    # replace il with pulse
    body = body.replace(
        f"il (pad 0) isource dc={I_TYP}",
        f'il0 (pad 0) isource dc={I_TYP}\n'
        f'il1 (pad 0) isource type="pulse" val0=0 val1=1m delay=5u '
        f"rise=10n fall=10n width=20u period=50u",
    )
    text = HDR + body + """
control
  abort always
  options temp=27 reltol=1e-3 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis tr1 tran stop=30u step=1n
endc
"""
    run("step_load1mA", text)
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    t = np.real(tr["time"]).ravel()
    vp = np.real(tr["pad"]).ravel()
    pre = vp[(t > 3e-6) & (t < 4.5e-6)]
    post = vp[t > 5.05e-6]
    tpost = t[t > 5.05e-6]
    v0 = float(pre.mean())
    v1 = float(vp[(t > 20e-6) & (t < 24e-6)].mean())
    dvpk = (float(post[:5000].min()) - v0) * 1e3
    zc = int(np.sum(np.diff(np.sign(post[tpost < 15e-6] - v1)) != 0))
    print(f"| load +1 mA | {dvpk:.1f} | zc≈{zc} | "
          f"v0={v0:.3f}→{v1:.3f} |")

    # VBAT step 0.3 V around 2.7
    body, _ = ldo(filt="rlc", il=I_TYP)
    body = body.replace(
        f"vin (vin 0) vsource dc={VIN}",
        f'vin (vin 0) vsource type="pulse" val0={VIN} val1={VIN+0.3} '
        f"delay=5u rise=100n fall=100n width=20u period=50u",
    )
    text = HDR + body + """
control
  abort always
  options temp=27 reltol=1e-3 rawfile="binary" strictsave=1
  save v(vout) v(pad) v(vin)
  analysis tr1 tran stop=30u step=1n
endc
"""
    run("step_vbat0p3", text)
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    t = np.real(tr["time"]).ravel()
    vp = np.real(tr["pad"]).ravel()
    pre = vp[(t > 3e-6) & (t < 4.5e-6)]
    post = vp[t > 5.1e-6]
    tpost = t[t > 5.1e-6]
    v0 = float(pre.mean())
    v1 = float(vp[(t > 20e-6) & (t < 24e-6)].mean())
    # peak excursion
    seg = post[tpost < 15e-6]
    dvpk = (float(np.max(np.abs(seg - v0))) ) * 1e3
    # signed: max - v0
    dvp = (float(seg.max()) - v0) * 1e3
    dvn = (float(seg.min()) - v0) * 1e3
    zc = int(np.sum(np.diff(np.sign(seg - v1)) != 0))
    print(f"| VBAT +0.3 V | +{dvp:.1f}/{dvn:.1f} | zc≈{zc} | "
          f"v0={v0:.3f}→{v1:.3f} |")


def main():
    print("# Fixed D21 LDO verification\n")
    print("Compensation: rz=500 Ω + cg=100 pF to gnd (replaces Miller cc to mid).\n")
    print("PRIOR 9.5 nV/√Hz result: UNVERIFIED (was taken before transient HOLD).\n")
    section_polarity()
    stb = section_stb()
    sv, vpad = section_noise_pad()
    section_steps()
    print("\n# Summary\n")
    print(f"Compensation: Rz=500 + Cg=100p to gnd")
    for k, v in stb.items():
        print(f"  stb {k}: PM={v['pm']:.1f}° @ {(v['ugf'] or 0)/1e6:.3f} MHz")
    print(f"  S_v(pad) @ 1 MHz: {sv*1e9:.2f} nV/√Hz "
          f"({'PASS' if sv <= LIMIT else 'MISS'} vs 11)")
    print(f"  V_pad typ: {vpad:.4f} V")
    open(os.path.join(OUT, "summary_ldo_verify.txt"), "w").write(
        open(os.path.join(OUT, "summary_ldo_verify.txt"), "a").read()
        if False else "")
    return 0


if __name__ == "__main__":
    # tee manually
    class Tee:
        def __init__(self, path):
            self.f = open(path, "w")
            self.o = sys.stdout
        def write(self, x):
            self.o.write(x)
            self.f.write(x)
        def flush(self):
            self.o.flush()
            self.f.flush()
    sys.stdout = Tee(os.path.join(OUT, "summary_ldo_verify.txt"))
    try:
        raise SystemExit(main())
    finally:
        sys.stdout.f.close()
        sys.stdout = sys.stdout.o
