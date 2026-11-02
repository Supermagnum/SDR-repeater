#!/usr/bin/env python3
"""D22 step 1b differential-max detector accuracy vs true tank Amp [SCH].

VCO top (code 0) / bottom (code 255), mos_tt/ss/ff × MIM × −40/27/85 °C.
Gate: |A_est − Amp| ≤ 0.10 V near the 1.25 V target.

    python3 -u run_detector.py | tee out/summary_detector.txt
    python3 -u run_detector.py quick
"""
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2

A.load_sizing()
A.OUT = os.path.join(A.OUT, "det")
os.makedirs(A.OUT, exist_ok=True)
S2.OUT = A.OUT

CORNERS = [
    ("mos_tt", "cap_typ"),
    ("mos_ss", "cap_wcs"),
    ("mos_ss", "cap_bcs"),
    ("mos_ff", "cap_wcs"),
    ("mos_ff", "cap_bcs"),
]
TEMPS = (-40, 27, 85)
# Bias so Amp near 1.25 V where possible: top ~code 20, bottom still at 31
BANDS = (("top", 0, 20), ("bottom", 255, 31))


def run_one(mos, cap, temp, band, bcode, bias):
    A.set_corner(mos, cap)
    tag = f"det_{mos}_{cap}_{temp}_{band}"
    sim = S2.netlist(
        tag, bcode, S2.VTUNE_MID if band == "top" else 0.3,
        itail=A.itail(bias),
        drive_vbp=False, bypass=True,
        analysis=(
            f"  options temp={temp}\n"
            "  save v(tp) v(tn) v(ct) v(hold) v(rep) v(cmp)\n"
            "  analysis tr tran stop=200n step=5p maxstep=5p"
        ),
        extra="",
    )
    A.inject_dac_det(sim, bias, det=True)
    S2.run(sim)
    d = rawread(os.path.join(A.OUT, "tr.raw")).get()
    t = np.real(d["time"])
    m = t >= t[-1] - 30e-9
    vp, vn = np.real(d["tp"])[m], np.real(d["tn"])[m]
    amp = float((vp - vn).max() - (vp - vn).min()) / 2
    vh = float(np.real(d["hold"])[m][-1])
    vr = float(np.real(d["rep"])[m][-1])
    a_est = A.a_est_from_holds(vh, vr)
    err = a_est - amp
    return dict(amp=amp, a_est=a_est, err=err, vh=vh, vr=vr, vsense=vh - vr)


def main():
    quick = "quick" in sys.argv
    corners = [("mos_tt", "cap_typ")] if quick else CORNERS
    temps = (27,) if quick else TEMPS
    print("# D22 step 1b differential-max detector accuracy [SCH]\n")
    print(
        f"Topology: shared-source max(tp,tn) vs CT replica; "
        f"W={A.W_DET} L={A.L_DET}; I={A.I_DET*1e6:.1f} µA; C={A.C_HOLD*1e15:.0f} fF; "
        f"V_LOSS={A.V_LOSS:.3f} V (design-time) `[SCH]`/`[HAND]`.\n"
    )
    print(f"Tank gate load ≈ 2 × Cgg ≪ 10 fF `[HAND]`.\n")
    print("| MOS | CAP | T | band | Amp (V) | A_est (V) | err (V) | Vh-Vr | |err|≤0.10 |")
    print("|---|---|---|---|---|---|---|---|---|")
    n_fail = 0
    n = 0
    near = []  # cases with Amp in 1.15..1.35 for the gate
    for mos, cap in corners:
        for temp in temps:
            for band, bcode, bias in BANDS:
                try:
                    r = run_one(mos, cap, temp, band, bcode, bias)
                except Exception as e:
                    print(f"| {mos} | {cap} | {temp} | {band} | FAIL {e} | | | | |")
                    n_fail += 1
                    n += 1
                    continue
                ok = abs(r["err"]) <= A.A_WIN
                if not ok:
                    n_fail += 1
                n += 1
                if 1.15 <= r["amp"] <= 1.35:
                    near.append(r)
                print(
                    f"| {mos} | {cap} | {temp} | {band} | {r['amp']:.3f} | {r['a_est']:.3f} | "
                    f"{r['err']:+.3f} | {r['vsense']:.3f} | {'PASS' if ok else 'MISS'} |"
                )
    print()
    print(
        f"All cases: {n - n_fail}/{n} within ±{A.A_WIN:.2f} V. "
        f"{'PASS' if n_fail == 0 else 'SEE MISSES'} `[SCH]`"
    )
    if near:
        e = [abs(x["err"]) for x in near]
        print(
            f"Near-target (Amp 1.15–1.35 V): {len(near)} cases, "
            f"|err| max {max(e):.3f} V, mean {sum(e)/len(e):.3f} V `[SCH]`"
        )
        gate = all(x <= A.A_WIN for x in e)
        print(f"Gate at Amp≈1.25 V: {'PASS' if gate else 'MISS'} `[SCH]`")
    else:
        print("No near-target Amp cases in this matrix (bottom stays below 1.25) `[SCH]`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
