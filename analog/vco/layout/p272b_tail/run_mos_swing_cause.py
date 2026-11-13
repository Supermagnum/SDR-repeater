#!/usr/bin/env python3
"""P2.7.2b — find cause of MOSCAP swing drop 1.20 → 0.93 V (finding only).

1) Bias OP (resistive tail load, no forced Vd): nbf / nb / Itail ideal vs mos.
2) Short VCO PSS: mean Itail, amp, f0 — to see if DC Ig alone explains swing.

    python3 -u run_mos_swing_cause.py | tee out/summary_mos_swing_cause.txt
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import numpy as np
from vacask.rawfile import rawread

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
STEP2 = os.path.join(HERE, "..", "..", "step2")
STEP3 = os.path.join(HERE, "..", "..", "..", "pn-validation")
sys.path[:0] = [STEP2, os.path.join(HERE, "..", "..", "step3"),
                os.path.join(HERE, "..", "..", "..", "pn-validation")]

import run_d9_mos_vs_mim as R  # noqa: E402
import run_step2 as S2  # noqa: E402
from compare import fundamental_amplitude  # noqa: E402

S2.OUT = OUT
MOS_M = 5
MOS_W = MOS_L = 30.0


def mos_cbf():
    return "".join(
        f"Xcbf{i} (nbf 0) sg13_moscap_n w={MOS_W:.0f}u l={MOS_L:.0f}u m=1\n"
        for i in range(MOS_M)
    )


def run(name, text):
    path = os.path.join(OUT, name + ".sim")
    open(path, "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(open(log).read()[-800:])


def deck_op(kind, temp=27):
    if kind == "ideal":
        cbf = "cbf (nbf 0) capacitor c=50p\n"
        mos_inc = ""
    else:
        cbf = mos_cbf()
        mos_inc = 'include "cornerMOSCAP.lib" section=moscap_tt\n'
    # Resistive load on tail (no forced Vd); Itail via 1 Ohm sense.
    return f"""D9 mos swing cause OP {kind}

ground 0
include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section=mos_tt
{mos_inc}load "resistor.osdi"
load "capacitor.osdi"
model resistor resistor
model capacitor capacitor
model vsource vsource
model isource isource
vdd (vdd 0) vsource dc=1.2
imaster (pbias 0) isource dc=10.5u
mm0 (pbias pbias vdd vdd) sg13_lv_pmos w=2u l=2u ng=1
moff (xoff pbias vdd vdd) sg13_lv_pmos w=38u l=2u ng=19
msoff (xraw 0 xoff vdd) sg13_lv_pmos w=38u l=0.13u ng=1
mdb4 (xd4 pbias vdd vdd) sg13_lv_pmos w=32u l=2u ng=16
msw4 (xraw 0 xd4 vdd) sg13_lv_pmos w=32u l=0.13u ng=1
vsense (xraw xref) vsource dc=0
mr (xref nbf 0 0) sg13_lv_nmos w=60u l=4u ng=12
mt (tail_m nbf 0 0) sg13_lv_nmos w=480u l=4u ng=96
rsense (tail_m tail) resistor r=1
rtail (tail 0) resistor r=125
rtf (tail tail_f) resistor r=100k
ctf (tail_f 0) capacitor c=1p
mo1 (d1 xref ss 0) sg13_lv_nmos w=8u l=2u ng=2
mo2 (d2 tail_f ss 0) sg13_lv_nmos w=8u l=2u ng=2
iss (ss 0) isource dc=20u
mp1 (d1 d1 vdd vdd) sg13_lv_pmos w=4u l=2u ng=2
mp2 (d2 d1 vdd vdd) sg13_lv_pmos w=4u l=2u ng=2
rout (d2 nb) resistor r=1
rbf (nb nbf) resistor r=1Meg
{cbf}rpd (nb 0) resistor r=200k
ctail (tail 0) capacitor c=8p
control
  abort always
  options temp={temp} reltol=1e-6 rawfile="binary" strictsave=1
  save v(nbf) v(nb) v(xref) v(tail) v(tail_m) v(d2)
  analysis op1 op
endc
"""


def op_compare():
    print("## 1) Bias OP (Rtail=125 Ohm, no forced Vd) [SCH]\n")
    rows = {}
    for kind in ("ideal", "mos"):
        run(f"swing_op_{kind}", deck_op(kind))
        d = rawread(os.path.join(OUT, "op1.raw")).get()

        def v(n):
            return float(np.real(np.asarray(d[n]).ravel()[0]))

        it = abs(v("tail_m") - v("tail"))  # through 1 Ohm
        nbf, nb = v("nbf"), v("nb")
        rows[kind] = dict(nbf=nbf, nb=nb, xref=v("xref"), d2=v("d2"),
                          itail=it, vtail=v("tail"), dv_rbf=nb - nbf)
        print(f"| {kind} | nbf={nbf:.4f} V | nb={nb:.4f} V | "
              f"dV(rbf)={nb-nbf:.4f} V | Itail={it*1e3:.3f} mA | "
              f"Vtail={v('tail'):.3f} | d2={v('d2'):.4f} |")
    return rows


def pss_amp_itail(kind: str):
    """Short PSS: amp + sample mean drain current proxy via V(nbf)."""
    code, vt, f0, itail, temp = 91, S2.VTUNE_MID, 3.65e9, 4.0e-3, 27.0
    sim = S2.netlist(
        f"swing_pss_{kind}", code, vt, itail=itail, bypass=True,
        bypass_groups=("tail", "var"),
        analysis=(
            "  options temp=27 reltol=1e-6 pss_tolscale=1e-3 pss_minpts=8000\n"
            '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
            f'  analysis pn pnoise oscillator=1 tper={1/f0:.6e} tstab=0 '
            f'ic="ss" icmode="uic" maxharm=16 truncharm=8 in="iin" '
            f'out=["tp", "tn"] outharm=1 values=[1e5] writepss=1'
        ),
        extra="iin (0 tp) isource dc=0\n",
    )
    text = open(sim).read()
    text = R.patch_cbf(text, kind)
    # save nbf / nb / tail for post
    if "save " not in text:
        text = text.replace(
            "control\n",
            "control\n  save v(nbf) v(nb) v(tail) v(tp) v(tn)\n",
            1,
        )
    open(sim, "w").write(text)
    S2.run(sim)
    pss = rawread(os.path.join(OUT, "pn.pss.raw")).get()
    a, fp = fundamental_amplitude(
        pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
    names = list(pss.names) if hasattr(pss, "names") else []
    # mean bias nodes if present
    def mean(n):
        if n not in names and n not in getattr(pss, "nameToIndex", {}):
            try:
                return float(np.mean(np.real(np.asarray(pss[n]))))
            except Exception:
                return float("nan")
        return float(np.mean(np.real(np.asarray(pss[n]))))

    out = dict(amp=a, f=fp, nbf=mean("nbf"), nb=mean("nb"), tail=mean("tail"))
    return out


def main():
    print("# MOSCAP swing-drop cause (finding only) [SCH]\n")
    print("Prior VCO: amp 1.201 → 0.933 V (−22.5 %), ΔL +0.516 dB @ 100 kHz "
          "[SCH summary_d9_finding].\n")
    print("Prior Ig @ 0.6 V (5x moscap): ~42 nA tt/27 → Ig*1MOhm ~42 mV [SCH].\n")

    rows = op_compare()
    print("\nPrior Ig @ 0.6 V (5x moscap): ~42 nA tt/27 -> Ig*1MOhm ~42 mV [SCH].")
    if "ideal" in rows and "mos" in rows:
        dnbf = rows["mos"]["nbf"] - rows["ideal"]["nbf"]
        dit = rows["mos"]["itail"] - rows["ideal"]["itail"]
        dnb = rows["mos"]["nb"] - rows["ideal"]["nb"]
        iref = max(rows["ideal"]["itail"], 1e-9)
        print(f"dnbf (mos-ideal) = {dnbf*1e3:.1f} mV")
        print(f"dnb  (mos-ideal) = {dnb*1e3:.1f} mV  "
              f"(OTA raises nb to fight Ig through rbf)")
        print(f"dItail = {dit*1e3:.3f} mA ({100*dit/iref:+.1f} %)")

    print("\n## 2) Short VCO PSS mean bias + amp [SCH]\n")
    pss = {}
    for kind in ("ideal", "mos"):
        print(f"  PSS {kind} …", flush=True)
        try:
            pss[kind] = pss_amp_itail(kind)
            r = pss[kind]
            print(f"  {kind}: amp={r['amp']:.3f} f={r['f']/1e9:.3f} GHz "
                  f"nbf={r['nbf']:.4f} nb={r['nb']:.4f} tail={r['tail']:.3f}",
                  flush=True)
        except Exception as e:
            print(f"  {kind}: FAILED {e}", flush=True)
            pss[kind] = None

    print("\n## Cause [SCH/HAND]\n")
    if rows.get("ideal") and rows.get("mos"):
        dnbf = rows["mos"]["nbf"] - rows["ideal"]["nbf"]
        dit = rows["mos"]["itail"] - rows["ideal"]["itail"]
        iref = max(rows["ideal"]["itail"], 1e-9)
        dnb = rows["mos"]["nb"] - rows["ideal"]["nb"]
        print(f"- DC OP: OTA holds nbf (dnbf={dnbf*1e3:.1f} mV) by raising nb "
              f"({dnb*1e3:.1f} mV ≈ Ig*rbf); Itail change {100*dit/iref:+.1f} %.")
        print("- Therefore DC Ig×1 MΩ alone does **not** explain the −22.5 % "
              "swing drop (Itail would need ~−22 %).")
    if pss.get("ideal") and pss.get("mos"):
        a0, a1 = pss["ideal"]["amp"], pss["mos"]["amp"]
        rel = (a1 - a0) / a0
        dnbf_p = pss["mos"]["nbf"] - pss["ideal"]["nbf"]
        print(f"- Under oscillation: amp {a0:.3f} → {a1:.3f} V ({rel*100:+.1f} %); "
              f"mean nbf Δ={dnbf_p*1e3:.1f} mV [SCH].")
        if abs(rel) > 0.1 and abs(dnbf_p) < 0.02:
            print("- Swing drops while mean nbf stays → not a static Vgs/Itail "
                  "shift. Likely moscap C(V)/channel conductance under the "
                  "large-signal bias filter, or PSS settle to a lower-amp "
                  "state with the nonlinear moscap [SCH/HAND].")
        elif abs(dnbf_p) >= 0.02:
            print("- Mean nbf drops under PSS → leakage / OTA headroom under "
                  "large-signal; reduced Vgs → Itail → swing [SCH].")
        else:
            print("- Amp nearly unchanged in this short PSS; prior −22 % may "
                  "need the full pnoise settle (re-check) [SCH].")
    print("- Ideal/MIM have negligible Ig and flat C; rfcmim keeps the filter.")
    print("- Design unchanged: MOS rejected (decisions D9); this is a finding.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
