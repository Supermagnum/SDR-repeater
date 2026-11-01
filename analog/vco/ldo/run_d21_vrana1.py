#!/usr/bin/env python3
"""D21: VR_ANA1 = LDO → R=10 Ω → pad → 100 nF; VCO+LO+CP from pad.

No Kelvin sense. Set LDO so pad ≈ 1.2 V at typical LO current.
Check worst-case pad ≥ 1.08 V, ΔV between bands, noise ≤ 11 nV,
stability with board C and with C missing.
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

# Currents on VR_ANA1 (VCO + LO chain + PLL) [HAND] from lo-divider / PLL notes
I_TYP = 9.65e-3       # VHF typ 4.20 GHz ≈ 9.65 mA (D7 figure)
I_UHF = 8.3e-3        # UHF typ
I_VHF_BOT = 9.8e-3    # VHF bottom band
I_MAX = 10.3e-3       # ff max recorded
R_NOM = 10.0
V_PAD_TYP = 1.2
# LDO senses own output: V_LDO = V_pad + I*R
V_LDO_NOM = V_PAD_TYP + I_TYP * R_NOM  # 1.2965 V
VREF = V_LDO_NOM / 2
VIN = 2.7  # min VBAT; LDO from battery now (not intermediate 1.5 V)
LIMIT = 11e-9
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
        raise RuntimeError(open(log).read()[-1500:])
    return log


def header():
    return """parameters title="D21 VR_ANA1 LDO"
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


def ldo_body(cout=100e-12, probe=False):
    """LDO sensing vout (before R). Optional acstb probe in feedback.

    Compensation: Rz=500 Ω + Cg=100 pF to gnd (NOT Miller to mid — that
    path made the OP diverge in transient despite correct DC polarity).
    """
    sc = side(cout * 1e15)
    # Feedback: divider on vout → fb; optional probe to sense (m1 gate)
    if probe:
        # acstb: probe + faces DUT input (error-amp gate = sense)
        fb = """rf1 (vout fb) resistor r=200k noisy=1
rf2 (fb 0) resistor r=200k noisy=1
vprobe (sense fb) vsource dc=0
"""
        g_mid = "sense"
    else:
        fb = """rf1 (vout mid) resistor r=200k noisy=1
rf2 (mid 0) resistor r=200k noisy=1
"""
        g_mid = "mid"
    return f"""
vref (vref 0) vsource dc={VREF:.6g}
vin (vin 0) vsource dc={VIN}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
{fb}ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (d1 {g_mid} t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
rz (vg ncg) resistor r=500
cg (ncg 0) capacitor c=100p
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
"""


def filter_net(r=R_NOM, lb=1.5e-9, cboard=100e-9, iload=I_TYP):
    cboard_line = (f"cboard (pin 0) capacitor c={cboard:.6g}\n"
                   if cboard and cboard > 0 else "")
    return f"""
rser (vout pad) resistor r={r} noisy=1
cpad (pad 0) capacitor c=2p
cesd (pad 0) capacitor c=1p
lbond (pad pin) inductor l={lb}
{cboard_line}il (pad 0) isource dc={iload}
"""


def section_hand():
    print("# D21 pad voltage budget [HAND]\n")
    print(f"I_typ (VHF 4.20) = {I_TYP*1e3:.2f} mA; R = {R_NOM:.0f} Ω")
    print(f"Target V_pad = {V_PAD_TYP:.3f} V → V_LDO (sense) = {V_LDO_NOM:.4f} V "
          f"(Vref = {VREF:.4f} V, β=1/2)")
    print(f"IR_typ = {I_TYP*R_NOM*1e3:.1f} mV\n")

    print("| Case | I (mA) | R (Ω) | V_LDO | V_pad |")
    print("|---|---|---|---|---|")
    for name, i in (("UHF typ", I_UHF), ("VHF typ 4.20", I_TYP),
                    ("VHF bottom", I_VHF_BOT), ("ff max", I_MAX)):
        vp = V_LDO_NOM - i * R_NOM
        print(f"| {name} | {i*1e3:.2f} | {R_NOM:.0f} | {V_LDO_NOM:.4f} | {vp:.4f} |")

    d_band = (I_TYP - I_UHF) * R_NOM
    d_vhf = (I_VHF_BOT - I_TYP) * R_NOM
    print(f"\nΔV_pad UHF→VHF typ: {d_band*1e3:.1f} mV "
          f"(I {I_UHF*1e3:.2f}→{I_TYP*1e3:.2f} mA)")
    print(f"ΔV_pad within VHF (4.20→bottom): {d_vhf*1e3:.1f} mV\n")

    print("Worst-case V_pad = V_LDO_nom·(1−ε_L) − I_max·R_nom·(1+ε_R):\n")
    print("| ε_LDO | ε_R | V_pad_min | ≥ 1.08 V |")
    print("|---|---|---|---|")
    worst = None
    for el in (0.03, 0.05):
        for er in (0.15, 0.20, 0.30):
            vp = V_LDO_NOM * (1 - el) - I_MAX * R_NOM * (1 + er)
            ok = "PASS" if vp >= 1.08 else "MISS"
            print(f"| ±{el*100:.0f}% | ±{er*100:.0f}% | {vp:.4f} V | {ok} |")
            if worst is None or vp < worst:
                worst = vp
    print(f"\nTightest in table: {worst:.4f} V. "
          f"Recommended assume ±5% LDO / ±20% R → "
          f"{V_LDO_NOM*0.95 - I_MAX*R_NOM*1.20:.4f} V.\n")
    return worst


def section_noise():
    print("# Noise at pad, R=10 Ω, I=10 mA [SCH]\n")
    text = header() + ldo_body() + filter_net(iload=10e-3) + """
iin (0 pad) isource dc=0
control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis op1 op
  analysis n1 noise in="iin" out=["pad"] values=[1Meg]
endc
"""
    run("d21_noise_i10", text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    n = rawread(os.path.join(OUT, "n1.raw")).get()
    vout = float(np.real(op["vout"]).ravel()[0])
    vpad = float(np.real(op["pad"]).ravel()[0])
    sv = math.sqrt(abs(float(np.real(n["onoise"]).ravel()[0])))
    # Also typ current
    text2 = header() + ldo_body() + filter_net(iload=I_TYP) + """
iin (0 pad) isource dc=0
control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis op1 op
  analysis n1 noise in="iin" out=["pad"] values=[1Meg]
endc
"""
    run("d21_noise_ityp", text2)
    op2 = rawread(os.path.join(OUT, "op1.raw")).get()
    n2 = rawread(os.path.join(OUT, "n1.raw")).get()
    vpad2 = float(np.real(op2["pad"]).ravel()[0])
    vout2 = float(np.real(op2["vout"]).ravel()[0])
    sv2 = math.sqrt(abs(float(np.real(n2["onoise"]).ravel()[0])))
    print(f"| I | V_LDO | V_pad | S_v @ 1 MHz | vs 11 nV |")
    print(f"|---|---|---|---|---|")
    for lab, i, vo, vp, s in (("typ 9.65 mA", I_TYP, vout2, vpad2, sv2),
                               ("10 mA", 10e-3, vout, vpad, sv)):
        fl = "PASS" if s <= LIMIT else "MISS"
        print(f"| {lab} | {vo:.4f} | {vp:.4f} | {s*1e9:.2f} nV/√Hz | {fl} |")
    print()
    return sv, vpad2


def pm_from_w(freq, w):
    """Phase margin for VACASK W in closed-loop 1/(1+W).

    Critical point is W=-1. NEG-FB has W_DC ∠≈0° (positive real). At |W|=1,
    PM = 180° − |∠W|.
    """
    mag = np.abs(w)
    ang = np.unwrap(np.angle(w)) * 180 / np.pi
    pm = ugf = None
    for i in range(len(mag) - 1):
        if (mag[i] - 1.0) * (mag[i + 1] - 1.0) <= 0 and mag[i] > mag[i + 1]:
            t = (1.0 - mag[i]) / (mag[i + 1] - mag[i] + 1e-30)
            f = freq[i] + t * (freq[i + 1] - freq[i])
            a = ang[i] + t * (ang[i + 1] - ang[i])
            aa = ((a + 180) % 360) - 180
            p = 180.0 - abs(aa)
            if ugf is None or f > ugf:
                pm, ugf = p, f
    return ugf, pm


def section_stability():
    print("# Stability [SCH]\n")
    print("acstb probe (+)=sense (OTA input), (−)=fb. "
          "Plus load-step transient on pad.\n")
    rows = []
    for tag, cboard in (("with_100n", 100e-9), ("c_missing", 0.0)):
        text = header() + ldo_body(probe=True) + filter_net(
            cboard=cboard, iload=I_TYP) + """
control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(vout) v(pad) v(vg)
  analysis op1 op
  analysis stb1 acstb probe="vprobe" from=1k to=1G mode="dec" points=20
endc
"""
        try:
            run(f"d21_stb_{tag}", text)
            op = rawread(os.path.join(OUT, "op1.raw")).get()
            stb = rawread(os.path.join(OUT, "stb1.raw")).get()
            vpad = float(np.real(op["pad"]).ravel()[0])
            freq = np.real(stb["frequency"]).ravel()
            w = np.asarray(stb["w"]).ravel()
            ugf, pm = pm_from_w(freq, w)
            wdc = complex(w[0])
            peak = float(np.max(np.abs(w)))
            ok = "OK" if (pm is not None and pm > 30) else "CHECK"
            print(f"| acstb {tag} | Vpad={vpad:.3f} | W_DC∠={np.angle(wdc, deg=True):.0f}° "
                  f"|W_DC|={abs(wdc):.0f} | UGF≈{(ugf or 0)/1e6:.2f} MHz | "
                  f"PM≈{pm if pm is not None else float('nan'):.1f}° | {ok} |")
            rows.append(dict(tag=tag, pm=pm, ugf=ugf, vpad=vpad, method="acstb"))
        except Exception as e:
            print(f"| acstb {tag} | FAIL: {str(e).splitlines()[-1][:80]} |")
            rows.append(dict(tag=tag, pm=None, err=str(e)[-200:]))

    # Load-step: 5→10 mA in 1 ns — ring / settle on pad
    print("\nLoad step 5→10 mA in 1 ns (tran):\n")
    print("| load | ΔVpk (mV) | settle <1% of step by | note |")
    print("|---|---|---|---|")
    for tag, cboard in (("with_100n", 100e-9), ("c_missing", 0.0)):
        cboard_line = (f"cboard (pin 0) capacitor c={cboard:.6g}\n"
                       if cboard else "")
        text = header() + ldo_body() + f"""
rser (vout pad) resistor r={R_NOM} noisy=0
cpad (pad 0) capacitor c=2p
cesd (pad 0) capacitor c=1p
lbond (pad pin) inductor l=1.5n
{cboard_line}il (pad 0) isource type="pulse" val0=5m val1=10m delay=1u \
  rise=1n fall=1n width=5u period=20u
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis tr1 tran stop=6u step=0.5n
endc
"""
        try:
            run(f"d21_step_{tag}", text)
            tr = rawread(os.path.join(OUT, "tr1.raw")).get()
            t = np.real(tr["time"]).ravel()
            vp = np.real(tr["pad"]).ravel()
            # after step at 1 us
            mask_pre = (t > 0.5e-6) & (t < 0.95e-6)
            mask_post = t > 1.05e-6
            v0 = float(np.mean(vp[mask_pre]))
            # final ≈ last 0.5 us of first pulse
            mask_fin = (t > 4.5e-6) & (t < 5.5e-6)
            v1 = float(np.mean(vp[mask_fin])) if np.any(mask_fin) else float(vp[-1])
            # peak excursion from pre toward undershoot
            post = vp[mask_post]
            tpost = t[mask_post]
            if len(post) == 0:
                print(f"| {tag} | — | — | no post data |")
                continue
            # undershoot = min after step
            imin = int(np.argmin(post[: min(len(post), 20000)]))
            vpk = float(post[imin])
            dvpk = (vpk - v0) * 1e3
            # settle: |v - v1| < 0.01 * 50 mV IR step = 0.5 mV
            thr = 0.5e-3
            settled = np.where(np.abs(post - v1) < thr)[0]
            # first index after which it stays settled 100 ns
            ts = None
            for i in settled:
                if i + 200 < len(post) and np.all(np.abs(post[i:i+200] - v1) < thr):
                    ts = tpost[i] - 1e-6
                    break
            ring = "ringing" if abs(dvpk) > 20 else "damped"
            # also check oscillatory: count zero crossings of (v-v1) in first 2 us
            early = post[tpost < 3e-6] - v1
            zc = int(np.sum(np.diff(np.sign(early)) != 0)) if len(early) > 2 else 0
            note = f"{ring}, zc≈{zc}"
            if ts is not None and ts < 2e-6 and zc < 6:
                note += "; STABLE"
            elif zc > 20:
                note += "; OSCILLATE?"
            print(f"| {tag} | {dvpk:.1f} | "
                  f"{(ts*1e9 if ts else float('nan')):.0f} ns | {note} |")
            rows.append(dict(tag=f"step_{tag}", dvpk=dvpk, ts=ts, zc=zc,
                             method="tran"))
        except Exception as e:
            print(f"| {tag} | FAIL | — | {str(e).splitlines()[-1][:60]} |")
    print()
    return rows


def main():
    print("# D21 VR_ANA1 filtered LO rail — set / check / noise / stability\n")
    print(f"Architecture: VBAT→LDO(sense vout)→R=10Ω→pad(VR_ANA1)→bond→100nF\n"
          f"VCO+LO+CP from pad. No Kelvin. No option (1).\n")
    section_hand()
    sv, vpad_typ = section_noise()
    stb = section_stability()
    print("# Summary\n")
    print(f"V_LDO set = {V_LDO_NOM:.4f} V → V_pad typ SCH ≈ {vpad_typ:.4f} V "
          f"(target 1.20 V)")
    print(f"S_v @ 1 MHz, 10 mA, R=10: {sv*1e9:.2f} nV/√Hz "
          f"({'PASS' if sv <= LIMIT else 'MISS'} vs 11)")
    for r in stb:
        if r.get("method") == "acstb" and r.get("pm") is not None:
            print(f"acstb {r['tag']}: PM≈{r['pm']:.1f}° @ "
                  f"{(r['ugf'] or 0)/1e6:.2f} MHz")
        if r.get("method") == "tran" and r.get("dvpk") is not None:
            print(f"step {r['tag']}: ΔVpk={r['dvpk']:.1f} mV, "
                  f"zc≈{r.get('zc')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
