#!/usr/bin/env python3
"""P2.7.2 gate: corner carries + D20 landing with corner-specific steps [SCH]+[MODEL].

1) Measure all seven carries (2^k−1→2^k) and LSB steps 0→1, 1→2 at ss/wcs/85 and
   ff/bcs/−40, with KVCO from V_tune 0.3/1.0 at each grid code.
2) Build corner f_bank(code) / kvco(code) from that grid (f@0.65 shifted to 0.6).
3) Run closed_loop landing (8-bit, f/4P, nearest) at tt/ss/ff hold voltages.
   Pass: V_tune inside window (ss 0.25–0.85, else 0.25–0.95); report margins.

    python3 -u run_p272_gate.py | tee out/summary_p272_gate.txt
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step2"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "analog", "pll", "p26", "step1"))
import run_step2 as S2  # noqa: E402
import run_step3 as S3  # noqa: E402
import closed_loop as CL  # noqa: E402

S2.OUT = OUT
S3.OUT = OUT

SPOTS = (
    ("mos_ss", "cap_wcs", 85, "ss"),
    ("mos_ff", "cap_bcs", -40, "ff"),
)
CARRIES = [1 << k for k in range(1, 8)]
LSB_PAIRS = [(0, 1), (1, 2)]
VT_LO, VT_MID, VT_HI = 0.3, 0.65, 1.0
GRID = sorted(set(
    [0, 1, 2, 3, 4, 7, 8, 15, 16, 31, 32, 63, 64, 127, 128, 191, 192, 254, 255]
    + [c - 2 for c in CARRIES] + [c - 1 for c in CARRIES] + CARRIES
    + [min(255, c + 2) for c in CARRIES]
))


def load():
    return S3.load_sizing()


def meas(code, vt, tag, itail, temp):
    return S3.tran(code, vt, tag, itail, temp)


def measure_corner(mos, cap, temp, key):
    S3.set_corner(mos, cap)
    it = 3.5e-3
    f_mid, k_map = {}, {}
    print(f"\n## Grid {mos}/{cap}/{temp} °C [SCH]\n")
    print("| code | f@0.65 (GHz) | KVCO (MHz/V) |")
    print("|---|---|---|")
    for c in GRID:
        m = meas(c, VT_MID, f"g_{key}_c{c}", it, temp)
        f_mid[c] = m["f"]
        m0 = meas(c, VT_LO, f"g_{key}_c{c}_lo", it, temp)
        m1 = meas(c, VT_HI, f"g_{key}_c{c}_hi", it, temp)
        k_map[c] = abs(m1["f"] - m0["f"]) / (VT_HI - VT_LO)
        print(f"| {c} | {f_mid[c]/1e9:.4f} | {k_map[c]/1e6:.1f} |")

    pairs = LSB_PAIRS + [(c - 1, c) for c in CARRIES]
    print(f"\n### Steps {key} [SCH]\n")
    print("| pair | f0 (GHz) | step (MHz) | ratio | KVCO (MHz/V) | ΔV_tune (V) |")
    print("|---|---|---|---|---|---|")
    rows = []
    for a, b in pairs:
        step = f_mid[a] - f_mid[b]
        lo, hi = max(0, a - 2), min(S2.CMAX, b + 2)
        # ensure neighbours present
        if lo not in f_mid:
            f_mid[lo] = meas(lo, VT_MID, f"g_{key}_c{lo}", it, temp)["f"]
        if hi not in f_mid:
            f_mid[hi] = meas(hi, VT_MID, f"g_{key}_c{hi}", it, temp)["f"]
        mean = (f_mid[lo] - f_mid[hi]) / (hi - lo)
        k = k_map[a]
        dv = step / k
        ratio = step / mean if mean else float("nan")
        print(f"| {a}→{b} | {f_mid[a]/1e9:.4f} | {step/1e6:+.2f} | {ratio:.2f} | "
              f"{k/1e6:.1f} | {dv:.3f} |")
        rows.append(dict(a=a, b=b, step=step, ratio=ratio, k=k, dv=dv))
    return rows, f_mid, k_map


def make_bank(f_mid, k_map):
    k_codes = np.array(sorted(int(c) for c in k_map), dtype=float)
    k_vals = np.array([float(k_map[int(c)]) for c in k_codes], dtype=float)
    # Prefer codes that have mid-f; fill KVCO by interp when a neighbour was
    # added for the step table without a dedicated KVCO sweep.
    codes = np.array(sorted(int(c) for c in f_mid), dtype=float)
    f65 = np.array([float(f_mid[int(c)]) for c in codes], dtype=float)
    ks = np.array([float(np.interp(c, k_codes, k_vals)) for c in codes])
    f60 = f65 - ks * (VT_MID - 0.6)

    def f_bank(code):
        return float(np.interp(float(np.clip(code, 0, S2.CMAX)), codes, f60))

    def kvco(code):
        return float(np.interp(float(np.clip(code, 0, S2.CMAX)), k_codes, k_vals))

    return f_bank, kvco, float(f60[0]), float(f60[-1])


def main():
    load()
    print("# P2.7.2 gate — corner carries + D20 landing [SCH]+[MODEL]\n")
    print(f"Sizing: LSB {S2.LSB_FF:.3f} fF, cfix {S2.C_FIX_FF:.0f} fF, "
          f"trim[7]={S2.TRIM[7]:.4f}\n")

    step_tables, banks = {}, {}
    for mos, cap, temp, key in SPOTS:
        rows, f_mid, k_map = measure_corner(mos, cap, temp, key)
        step_tables[key] = rows
        banks[key] = make_bank(f_mid, k_map)

    def blend_f(code):
        return 0.5 * (banks["ss"][0](code) + banks["ff"][0](code))

    def blend_k(code):
        return 0.5 * (banks["ss"][1](code) + banks["ff"][1](code))

    f_lo = 0.5 * (banks["ss"][2] + banks["ff"][2])
    f_hi = 0.5 * (banks["ss"][3] + banks["ff"][3])

    print("\n## D20 landing with corner-specific SCH steps [MODEL]\n")
    print("Rule: 8-bit, count f/4P, nearest. Hold voltages from closed_loop "
          "(tt 0.568 / ss 0.498 / ff 0.641 V).\n")
    print("| corner | SCH source | hold (V) | window | V min–max | outside % | "
          "margin lo/hi (V) | PASS |")
    print("|---|---|---|---|---|---|---|---|")
    ok_all = True
    results = {}
    for cn, src in (("tt", "blend"), ("ss", "ss"), ("ff", "ff")):
        if src == "blend":
            fb, kv, flo, fhi = blend_f, blend_k, f_lo, f_hi
        else:
            fb, kv, flo, fhi = banks[src]
        CL.F_LO, CL.F_HI = flo, fhi
        CL.f_bank = fb
        CL.kvco = kv
        CL.CFG.update(nb=8, cdiv=4)
        vs, _, _ = CL.landing(cn, "nearest", np.random.default_rng(1))
        lo_w, hi_w = CL.WINDOW[cn]
        out = float(np.mean((vs < lo_w) | (vs > hi_w)) * 100)
        mlo = float(vs.min() - lo_w)
        mhi = float(hi_w - vs.max())
        ok = (out < 1e-9) and (mlo >= 0.0) and (mhi >= 0.0)
        ok_all = ok_all and ok
        print(f"| {cn} | {src} | {CL.CORNERS[cn]['vhold']:.3f} | "
              f"{lo_w:.2f}–{hi_w:.2f} | {vs.min():.3f}–{vs.max():.3f} | "
              f"{out:.2f} | {mlo:+.3f}/{mhi:+.3f} | {'PASS' if ok else 'FAIL'} |")
        results[cn] = dict(src=src, vmin=float(vs.min()), vmax=float(vs.max()),
                           out=out, mlo=mlo, mhi=mhi, ok=ok, flo=flo, fhi=fhi)
    CL.CFG.update(nb=7, cdiv=4)

    ss_msb = next(r for r in step_tables["ss"] if r["a"] == 127)
    ff_msb = next(r for r in step_tables["ff"] if r["a"] == 127)
    print("\n## Gate verdict\n")
    print(f"ss85 127→128: ratio {ss_msb['ratio']:.2f}, ΔV {ss_msb['dv']:.3f} V [SCH]")
    print(f"ff−40 127→128: ratio {ff_msb['ratio']:.2f}, ΔV {ff_msb['dv']:.3f} V [SCH]")
    if ok_all:
        print("D20 landing: **PASS** — V_tune inside window at tt/ss/ff [MODEL]. "
              "P2.7.2 layout may proceed.")
    else:
        print("D20 landing: **FAIL** — V_tune outside window. Finding: no layout.")
        print("Proposal: re-trim at ss85, adjust hold/window, or exclude edge "
              "channels.")

    # JSON-safe steps
    steps_out = {k: [{kk: (float(vv) if isinstance(vv, (float, np.floating)) else vv)
                      for kk, vv in r.items()} for r in rows]
                 for k, rows in step_tables.items()}
    json.dump(dict(steps=steps_out, landing=results, pass_=ok_all),
              open(os.path.join(OUT, "p272_gate.json"), "w"), indent=1)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
