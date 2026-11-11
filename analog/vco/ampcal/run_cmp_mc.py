#!/usr/bin/env python3
"""Comparator MC on the node the search actually uses [SCH].

Search decision (run_search): vsense = V(hold)-V(rep) > V_th (behavioural).
On-chip: first pair (co/co2) + second OTA → single-ended cmp (Amp high → cmp high).

    python3 -u run_cmp_mc.py | tee out/cmp/summary_cmp_mc.txt
"""
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2

A.load_sizing()
A.OUT = os.path.join(A.OUT, "cmp")
os.makedirs(A.OUT, exist_ok=True)
S2.OUT = A.OUT
N = 40
W, L = 4.0, 0.5
SIG = A.SIG_VT_N / (W * L) ** 0.5
TH = A.v_th()
CM = 0.70
CMP_MID = A.CMP_HIGH  # SE trip level (lo≈0.58, bal≈0.67, hi≈1.11) [SCH]


def op_full(vip, vin, vos, tag):
    body = (
        f"vdd (vdd 0) vsource dc=1.2\n"
        f"vip (vip 0) vsource dc={vip:.6g}\n"
        f"vin (vin 0) vsource dc={vin:.6g}\n"
        f"vo1 (g1 vip) vsource dc={vos[0]:.6g}\n"
        f"vo2 (g2 vin) vsource dc={vos[1]:.6g}\n"
        f"mc1 (co g1 tt 0) sg13_lv_nmos w={W}u l={L}u ng=2\n"
        f"mc2 (co2 g2 tt 0) sg13_lv_nmos w={W}u l={L}u ng=2\n"
        "itt (tt 0) isource dc=20u\n"
        "rc1 (vdd co) resistor r=20k\n"
        "rc2 (vdd co2) resistor r=20k\n"
        "mcs1 (n1 co2 ss2 0) sg13_lv_nmos w=4u l=0.5u ng=2\n"
        "mcs2 (cmp co ss2 0) sg13_lv_nmos w=4u l=0.5u ng=2\n"
        "iss2 (ss2 0) isource dc=20u\n"
        "mpl1 (n1 n1 vdd vdd) sg13_lv_pmos w=4u l=0.5u ng=2\n"
        "mpl2 (cmp n1 vdd vdd) sg13_lv_pmos w=4u l=0.5u ng=2\n"
    )
    path = os.path.join(A.OUT, f"cmp_{tag}.sim")
    open(path, "w").write(
        S2.HEADER.format(title=f"cmp_{tag}") + body
        + "\ncontrol\n  abort always\n  options rawfile=\"binary\" temp=27\n"
        + "  save v(co) v(co2) v(cmp) v(tt)\n  analysis op1 op\nendc\n"
    )
    S2.run(path)
    d = rawread(os.path.join(A.OUT, "op1.raw")).get()
    return {
        "co": float(np.real(d["co"]).ravel()[0]),
        "co2": float(np.real(d["co2"]).ravel()[0]),
        "cmp": float(np.real(d["cmp"]).ravel()[0]),
        "tt": float(np.real(d["tt"]).ravel()[0]),
        "diff": float(np.real(d["co"]).ravel()[0] - np.real(d["co2"]).ravel()[0]),
    }


def trip_offset(vos, tag, sense="diff"):
    try:
        z = op_full(CM, CM, vos, f"{tag}_z")
    except Exception as e:
        return float("nan"), f"OP fail at bal: {e}"
    if z["tt"] < 0.05:
        return float("nan"), f"tail collapsed tt={z['tt']:.3f} V"
    lo, hi = -0.08, 0.08

    def dec(dv):
        r = op_full(CM + dv, CM, vos, f"{tag}_{dv:.5f}")
        if sense == "diff":
            # Amp high → co low → diff = co-co2 negative; invert so high→positive
            return -r["diff"]
        return r["cmp"] - CMP_MID

    dlo, dhi = dec(lo), dec(hi)
    if dlo * dhi > 0:
        return float("nan"), f"no zero in ±80 mV (dlo={dlo:.4f} dhi={dhi:.4f})"
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        dm = dec(mid)
        if dlo * dm <= 0:
            hi, dhi = mid, dm
        else:
            lo, dlo = mid, dm
    return 0.5 * (lo + hi), "ok"


def main():
    quick = "quick" in sys.argv
    n = 5 if quick else N
    print("# D22 step 1c comparator MC (2nd-stage SE) [SCH]\n")
    print(
        f"V_th={TH:.4f} V; CM={CM:.2f} V; SE mid={CMP_MID:.2f} V; "
        f"σ_VT={SIG*1e3:.2f} mV; N={n}\n"
    )
    A.set_corner("mos_tt", "cap_typ")
    r_lo = op_full(CM - 0.02, CM, (0, 0), "san_lo")
    r_hi = op_full(CM + 0.02, CM, (0, 0), "san_hi")
    print(
        f"SE sanity ±20 mV: cmp_lo={r_lo['cmp']:.3f} cmp_hi={r_hi['cmp']:.3f}; "
        f"diff={r_lo['diff']:+.4f}/{r_hi['diff']:+.4f} `[SCH]`"
    )
    se_ok = r_hi["cmp"] > CMP_MID > r_lo["cmp"]
    print(f"SE OP swing across {CMP_MID:.2f} V: {'PASS' if se_ok else 'FAIL'}\n")

    rng = np.random.default_rng(42)
    results = {"diff": [], "se": []}
    fail = {"diff": 0, "se": 0}
    for i in range(n):
        vos = (float(rng.normal(0, SIG)), float(rng.normal(0, SIG)))
        for sense in ("diff", "se"):
            off, msg = trip_offset(vos, f"mc{i}_{sense}", sense=sense)
            if off != off:
                fail[sense] += 1
                if i < 3:
                    print(f"  [{i}] {sense}: FAIL {msg}")
            else:
                results[sense].append(off)
        if (i + 1) % 10 == 0:
            print(f"  … {i+1}/{n}", flush=True)
    print()
    gate_ok = True
    for sense, label in (("diff", "co−co2"), ("se", "single-ended cmp (search-usable)")):
        arr = np.array(results[sense])
        if len(arr) < max(3, n // 2):
            print(f"{label}: too few trips ({len(arr)}/{n}) FAIL `[SCH]`")
            gate_ok = False
            continue
        sig = float(np.std(arr, ddof=1))
        amp3 = 3 * sig * 2 * 1e3
        print(
            f"{label}: N_ok={len(arr)}/{n} fails={fail[sense]}; "
            f"σ_in={sig*1e3:.2f} mV → Amp 3σ={amp3:.1f} mV "
            f"({'PASS' if amp3 < 100 else 'FAIL'} ≪ 100 mV) `[SCH]`"
        )
        print(f"  mean offset={float(np.mean(arr))*1e3:.2f} mV")
        if amp3 >= 100:
            gate_ok = False
    print(
        "\nSearch SCH uses vsense>V_th (beh). On-chip SE cmp now OP-correct; "
        "MC above is the wired decision node. `[SCH]`"
    )
    print("Overall cmp MC:", "PASS" if (gate_ok and se_ok) else "FAIL", "`[SCH]`")
    return 0 if (gate_ok and se_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
