#!/usr/bin/env python3
"""Find Cg/Rz/ib such that PM≥60° for both RLC (10Ω/bond/100n) and C-missing."""
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
        raise RuntimeError(name + "\n" + open(log).read()[-500:])


HDR = """parameters title="pm60"
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


def build(comp, filt, il=I_TYP, ib=40e-6, cout=100e-12, probe=False):
    g = "sense" if probe else "mid"
    if probe:
        fb = """rf1 (vout fb) resistor r=200k
rf2 (fb 0) resistor r=200k
vprobe (sense fb) vsource dc=0
"""
        comp = comp.replace(" mid", " sense").replace("(mid", "(sense")
    else:
        fb = """rf1 (vout mid) resistor r=200k
rf2 (mid 0) resistor r=200k
"""
    if filt == "rlc":
        load = f"""rser (vout pad) resistor r=10
cpad (pad 0) capacitor c=2p
lbond (pad pin) inductor l=1.5n
resr (pin cbot) resistor r=0.05
cboard (cbot 0) capacitor c=100n
il (pad 0) isource dc={il}
"""
        save = "v(vout) v(pad) v(vg)"
    else:
        load = f"""rser (vout pad) resistor r=10
cpad (pad 0) capacitor c=2p
lbond (pad pin) inductor l=1.5n
il (pad 0) isource dc={il}
"""
        save = "v(vout) v(pad) v(vg)"
    return f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
{fb}ib (vin nb) isource dc={ib}
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (d1 {g} t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
{comp}xout (vout 0 0) cap_rfcmim w={sc(cout):.3f}u l={sc(cout):.3f}u
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


def eval_one(tag, comp, ib, cout=100e-12):
    rows = {}
    for filt in ("rlc", "noc"):
        # hold
        body, save = build(comp, filt, ib=ib, cout=cout, probe=False)
        text = HDR + body + f"""
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save {save}
  analysis op1 op store="opx"
  analysis tr1 tran stop=10u step=1n nodeset="opx"
endc
"""
        try:
            run(f"h_{tag}_{filt}", text)
        except Exception as e:
            rows[filt] = dict(hold=False, err=str(e)[-80:])
            continue
        tr = rawread(os.path.join(OUT, "tr1.raw")).get()
        vo = np.real(tr["vout"]).ravel()
        hold = abs(vo[-1] - vo[0]) < 2e-3 and vo.std() < 1e-3
        # stb
        body, save = build(comp, filt, ib=ib, cout=cout, probe=True)
        text = HDR + body + f"""
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save {save}
  analysis op1 op
  analysis stb1 acstb probe="vprobe" from=100 to=100Meg mode="dec" points=40
endc
"""
        run(f"s_{tag}_{filt}", text)
        stb = rawread(os.path.join(OUT, "stb1.raw")).get()
        w = np.asarray(stb["w"]).ravel()
        f = np.real(stb["frequency"]).ravel()
        ugf, pm = pm_from_w(f, w)
        rows[filt] = dict(hold=hold, ugf=ugf, pm=pm,
                          wdc=abs(complex(w[0])),
                          ang=np.angle(complex(w[0]), deg=True))
    return rows


def main():
    print("# Sweep ib × Cg × Rz for PM≥60 on RLC and noC\n")
    print("| cfg | RLC hold/PM/UGF | noC hold/PM/UGF | both≥60 |")
    print("|---|---|---|---|")
    winners = []
    for ib in (40e-6, 20e-6, 10e-6, 5e-6):
        for cg in (50e-12, 100e-12, 150e-12, 200e-12, 300e-12, 500e-12,
                   800e-12, 1e-9):
            for rz in (0, 200, 500, 1e3, 2e3, 5e3, 10e3):
                if rz:
                    comp = (f"rz (vg ncg) resistor r={rz}\n"
                            f"cg (ncg 0) capacitor c={cg}\n")
                else:
                    comp = f"cg (vg 0) capacitor c={cg}\n"
                tag = f"ib{ib*1e6:.0f}_cg{cg*1e12:.0f}_rz{rz:.0f}"
                try:
                    rows = eval_one(tag, comp, ib)
                except Exception as e:
                    print(f"| {tag} | EXC | {str(e)[-40:]} | |")
                    continue
                def fmt(r):
                    if not r.get("hold"):
                        return "FAIL"
                    return (f"H PM={r['pm']:.0f}° "
                            f"@{((r['ugf'] or 0)/1e6):.2f}M")
                rlc, noc = rows.get("rlc", {}), rows.get("noc", {})
                ok = (rlc.get("hold") and noc.get("hold")
                      and (rlc.get("pm") or 0) >= 60
                      and (noc.get("pm") or 0) >= 60)
                mark = "YES" if ok else ""
                print(f"| {tag} | {fmt(rlc)} | {fmt(noc)} | {mark} |")
                if ok:
                    winners.append((tag, comp, ib, rlc, noc))
                    # keep searching a few more for margin, but stop early
                    if len(winners) >= 3:
                        break
            if len(winners) >= 3:
                break
        if len(winners) >= 3:
            break

    # Also try miller-to-VOUT (not mid) + cg
    if not winners:
        print("\n# Extra: Cc to vout (true Miller on pass) + Cg\n")
        for ib in (20e-6, 10e-6):
            for cg in (100e-12, 300e-12, 500e-12):
                for cc in (2e-12, 5e-12, 10e-12):
                    for rz in (0, 1e3, 5e3):
                        if rz:
                            comp = (f"rz (vg ncg) resistor r={rz}\n"
                                    f"cg (ncg 0) capacitor c={cg}\n"
                                    f"cm (vg vout) capacitor c={cc}\n")
                        else:
                            comp = (f"cg (vg 0) capacitor c={cg}\n"
                                    f"cm (vg vout) capacitor c={cc}\n")
                        tag = f"m_ib{ib*1e6:.0f}_cg{cg*1e12:.0f}_cc{cc*1e12:.0f}_rz{rz:.0f}"
                        try:
                            rows = eval_one(tag, comp, ib)
                        except Exception:
                            continue
                        rlc, noc = rows.get("rlc", {}), rows.get("noc", {})
                        ok = (rlc.get("hold") and noc.get("hold")
                              and (rlc.get("pm") or 0) >= 60
                              and (noc.get("pm") or 0) >= 60)
                        def fmt(r):
                            if not r.get("hold"):
                                return "FAIL"
                            return f"H PM={r['pm']:.0f}°"
                        print(f"| {tag} | {fmt(rlc)} | {fmt(noc)} | "
                              f"{'YES' if ok else ''} |")
                        if ok:
                            winners.append((tag, comp, ib, rlc, noc))
                            break
                    if winners:
                        break
                if winners:
                    break
            if winners:
                break

    print(f"\n# Winners: {len(winners)}")
    for w in winners:
        print(w[0], "ib", w[2], "RLC PM", w[3]["pm"], "noC PM", w[4]["pm"])
        open(os.path.join(OUT, "winner_comp.txt"), "w").write(
            f"{w[0]}\nib={w[2]}\n{w[1]}\n"
            f"RLC PM={w[3]['pm']} UGF={w[3]['ugf']}\n"
            f"noC PM={w[4]['pm']} UGF={w[4]['ugf']}\n")
    return 0 if winners else 1


if __name__ == "__main__":
    raise SystemExit(main())
