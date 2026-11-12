#!/usr/bin/env python3
"""P2.7.2b gate: D24 segmented bank carries at ss85/ff-40 + D20 landing [SCH]+[MODEL].

Pass: V_tune inside window at every corner (ss 0.25-0.85, else 0.25-0.95).
Uses closed_loop holds after D24 offset-off (0.512 / 0.577 / 0.649 V).
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
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "step2"))
sys.path.insert(0, os.path.join(REPO, "analog", "pll", "p26", "step1"))
import run_step2 as S2  # noqa: E402
import run_step3 as S3  # noqa: E402
import closed_loop as CL  # noqa: E402

S2.OUT = S3.OUT = OUT

# Binary carries + thermometer unit boundaries + a few LSB steps
CARRIES = [1 << k for k in range(1, S2.N_BIN)]  # 2,4,8,16
THERMO = [S2.UNIT_W * u for u in range(1, S2.N_THERMO + 1)]  # 32..224
LSB_PAIRS = [(0, 1), (1, 2)]
VT_LO, VT_MID, VT_HI = 0.3, 0.65, 1.0

GRID = sorted(set(
    [0, 1, 2, 3, 4, 7, 8, 15, 16, 31, 32, 33, 63, 64, 65, 95, 96,
     127, 128, 129, 159, 160, 191, 192, 223, 224, 254, 255]
    + [c - 1 for c in CARRIES + THERMO] + CARRIES + THERMO
    + [min(255, c + 1) for c in CARRIES + THERMO]
))


def measure_corner(mos, cap, temp, key):
    S3.set_corner(mos, cap)
    it = 3.5e-3
    f_mid, k_map = {}, {}
    print(f"\n## Grid {mos}/{cap}/{temp} C [SCH]\n")
    print("| code | f@0.65 (GHz) | KVCO (MHz/V) |")
    print("|---|---|---|")
    for c in GRID:
        m = S3.tran(c, VT_MID, f"g_{key}_c{c}", it, temp)
        f_mid[c] = m["f"]
        m0 = S3.tran(c, VT_LO, f"g_{key}_c{c}_lo", it, temp)
        m1 = S3.tran(c, VT_HI, f"g_{key}_c{c}_hi", it, temp)
        k_map[c] = abs(m1["f"] - m0["f"]) / (VT_HI - VT_LO)
        print(f"| {c} | {f_mid[c]/1e9:.4f} | {k_map[c]/1e6:.1f} |")

    pairs = LSB_PAIRS + [(c - 1, c) for c in CARRIES + THERMO]
    print(f"\n### Steps {key} [SCH]\n")
    print("| pair | f0 (GHz) | step (MHz) | ratio | KVCO (MHz/V) | dV_tune (V) |")
    print("|---|---|---|---|---|---|")
    rows = []
    codes = np.array(sorted(f_mid))
    fs = np.array([f_mid[c] for c in codes])
    for a, b in pairs:
        if a not in f_mid or b not in f_mid:
            print(f"| {a}->{b} | SKIP |")
            continue
        step = f_mid[a] - f_mid[b]
        lo, hi = max(0, a - 2), min(255, b + 2)
        flo = float(np.interp(lo, codes, fs))
        fhi = float(np.interp(hi, codes, fs))
        mean = (flo - fhi) / (hi - lo)
        k = k_map[a]
        dv = step / k
        ratio = step / mean
        print(f"| {a}->{b} | {f_mid[a]/1e9:.4f} | {step/1e6:+.2f} | {ratio:.2f} | "
              f"{k/1e6:.1f} | {dv:.3f} |")
        rows.append(dict(a=a, b=b, step=step, ratio=ratio, k=k, dv=dv))
    return rows, f_mid, k_map


def make_bank(f_mid, k_map):
    codes = np.array(sorted(f_mid))
    fs = np.array([f_mid[c] for c in codes])
    ks = np.array([k_map[c] for c in codes])

    def fb(code):
        return float(np.interp(code, codes, fs))

    def kv(code):
        return float(np.interp(code, codes, ks))

    return fb, kv, float(fs[0]), float(fs[-1])


def landing_table(banks):
    def blend_f(code):
        return 0.5 * (banks["ss"][0](code) + banks["ff"][0](code))

    def blend_k(code):
        return 0.5 * (banks["ss"][1](code) + banks["ff"][1](code))

    f_lo = 0.5 * (banks["ss"][2] + banks["ff"][2])
    f_hi = 0.5 * (banks["ss"][3] + banks["ff"][3])
    print("\n## D20 landing with corner-specific SCH steps (D24 holds) [MODEL]\n")
    print("| corner | SCH source | hold (V) | window | V min-max | outside % | "
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
        ok = (out < 1e-9) and (mlo >= 0) and (mhi >= 0)
        ok_all = ok_all and ok
        hold = CL.CORNERS[cn]["vhold"]
        flag = "PASS" if ok else "FAIL"
        print(f"| {cn} | {src} | {hold:.3f} | {lo_w:.2f}-{hi_w:.2f} | "
              f"{vs.min():.3f}-{vs.max():.3f} | {out:.2f} | "
              f"{mlo:+.3f}/{mhi:+.3f} | {flag} |")
        results[cn] = dict(src=src, vmin=float(vs.min()), vmax=float(vs.max()),
                           out=out, mlo=mlo, mhi=mhi, ok=ok, flo=flo, fhi=fhi)
    CL.CFG.update(nb=7, cdiv=4)
    return ok_all, results


def main():
    S3.load_sizing()
    print("# P2.7.2b gate — D24 segmented bank [SCH]+[MODEL]\n")
    print(f"bank_arch={S2.BANK_ARCH}, cells={S2.n_bank_cells()}, "
          f"trim_bin={S2.TRIM_BIN}, trim_unit={S2.TRIM_UNIT:.4f}\n")
    print(f"Holds (D24 offset-off) [SCH]: "
          f"tt={CL.CORNERS['tt']['vhold']}, ss={CL.CORNERS['ss']['vhold']}, "
          f"ff={CL.CORNERS['ff']['vhold']}\n")

    step_tables, banks = {}, {}
    for mos, cap, temp, key in (
            ("mos_ss", "cap_wcs", 85, "ss"),
            ("mos_ff", "cap_bcs", -40, "ff")):
        rows, f_mid, k_map = measure_corner(mos, cap, temp, key)
        step_tables[key] = rows
        banks[key] = make_bank(f_mid, k_map)

    ok_all, results = landing_table(banks)

    def worst(rows):
        return max(rows, key=lambda r: abs(r["ratio"] - 1.0))

    print("\n## Gate verdict\n")
    for key in ("ss", "ff"):
        w = worst(step_tables[key])
        print(f"{key}: worst-ratio carry {w['a']}->{w['b']} "
              f"ratio {w['ratio']:.2f}, dV {w['dv']:.3f} V [SCH]")
    if ok_all:
        print("D20 landing: PASS — V_tune inside window at tt/ss/ff [MODEL]. "
              "P2.7.2 layout may proceed.")
    else:
        print("D20 landing: FAIL — finding; no layout.")

    def jsafe(x):
        if isinstance(x, (float, np.floating)):
            return float(x)
        if isinstance(x, (int, np.integer)):
            return int(x)
        return x

    steps_out = {k: [{kk: jsafe(vv) for kk, vv in r.items()} for r in rows]
                 for k, rows in step_tables.items()}
    json.dump(dict(steps=steps_out, landing=results, pass_=ok_all,
                   holds={k: CL.CORNERS[k]["vhold"] for k in CL.CORNERS}),
              open(os.path.join(OUT, "p272b_gate.json"), "w"), indent=1)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
