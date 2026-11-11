#!/usr/bin/env python3
"""Resume P2.7.2 gate: reuse ss grid from summary, measure ff, run landing."""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "step2"))
sys.path.insert(0, os.path.join(REPO, "analog", "pll", "p26", "step1"))
import run_step2 as S2  # noqa: E402
import run_step3 as S3  # noqa: E402
import closed_loop as CL  # noqa: E402
import run_p272_gate as G  # noqa: E402

S2.OUT = S3.OUT = G.OUT = OUT
os.makedirs(OUT, exist_ok=True)


def load_ss_grid():
    text = open(os.path.join(OUT, "summary_p272_gate.txt")).read()
    block = text.split("### Steps ss")[0]
    f_mid, k_map = {}, {}
    for m in re.finditer(r"^\| (\d+) \| ([0-9.]+) \| ([0-9.]+) \|$", block, re.M):
        c = int(m.group(1))
        f_mid[c] = float(m.group(2)) * 1e9
        k_map[c] = float(m.group(3)) * 1e6
    return f_mid, k_map


def steps_from_grid(f_mid, k_map):
    rows = []
    codes = np.array(sorted(f_mid))
    fs = np.array([f_mid[c] for c in codes])
    pairs = G.LSB_PAIRS + [(c - 1, c) for c in G.CARRIES]
    print("## Steps [SCH]\n")
    print("| pair | step (MHz) | ratio | KVCO (MHz/V) | ΔV_tune (V) |")
    print("|---|---|---|---|---|")
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
        print(f"| {a}->{b} | {step/1e6:+.2f} | {ratio:.2f} | {k/1e6:.1f} | {dv:.3f} |")
        rows.append(dict(a=a, b=b, step=step, ratio=ratio, k=k, dv=dv))
    return rows


def landing_table(banks):
    def blend_f(code):
        return 0.5 * (banks["ss"][0](code) + banks["ff"][0](code))

    def blend_k(code):
        return 0.5 * (banks["ss"][1](code) + banks["ff"][1](code))

    f_lo = 0.5 * (banks["ss"][2] + banks["ff"][2])
    f_hi = 0.5 * (banks["ss"][3] + banks["ff"][3])
    print("\n## D20 landing with corner-specific SCH steps [MODEL]\n")
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
    print("# P2.7.2 gate (resume) [SCH]+[MODEL]\n")
    f_mid, k_map = load_ss_grid()
    print(f"Loaded ss grid: {len(f_mid)} codes\n")
    print("### ss 85 C\n")
    step_tables = {"ss": steps_from_grid(f_mid, k_map)}
    banks = {"ss": G.make_bank(f_mid, k_map)}

    # Reuse ff grid if already complete in resume summary
    ff_path = os.path.join(OUT, "summary_p272_gate_resume.txt")
    have_ff = False
    if os.path.exists(ff_path):
        t2 = open(ff_path).read()
        if "### Steps ff" in t2 or ("| 255 |" in t2 and "mos_ff" in t2):
            # try parse ff grid
            if "## Grid mos_ff" in t2:
                block = t2.split("## Grid mos_ff")[1]
                if "### Steps" in block:
                    block = block.split("### Steps")[0]
                f_ff, k_ff = {}, {}
                for m in re.finditer(
                        r"^\| (\d+) \| ([0-9.]+) \| ([0-9.]+) \|$", block, re.M):
                    c = int(m.group(1))
                    f_ff[c] = float(m.group(2)) * 1e9
                    k_ff[c] = float(m.group(3)) * 1e6
                if len(f_ff) >= 20 and 255 in f_ff:
                    print(f"\nReusing ff grid ({len(f_ff)} codes) from resume log\n")
                    print("### ff -40 C\n")
                    step_tables["ff"] = steps_from_grid(f_ff, k_ff)
                    banks["ff"] = G.make_bank(f_ff, k_ff)
                    have_ff = True

    if not have_ff:
        rows, f_ff, k_ff = G.measure_corner("mos_ff", "cap_bcs", -40, "ff")
        step_tables["ff"] = rows
        banks["ff"] = G.make_bank(f_ff, k_ff)

    ok_all, results = landing_table(banks)
    ss_msb = next(r for r in step_tables["ss"] if r["a"] == 127)
    ff_msb = next(r for r in step_tables["ff"] if r["a"] == 127)
    print("\n## Gate verdict\n")
    print(f"ss85 127->128: ratio {ss_msb['ratio']:.2f}, "
          f"dV {ss_msb['dv']:.3f} V [SCH]")
    print(f"ff-40 127->128: ratio {ff_msb['ratio']:.2f}, "
          f"dV {ff_msb['dv']:.3f} V [SCH]")
    if ok_all:
        print("D20 landing: PASS — V_tune inside window at tt/ss/ff [MODEL]. "
              "P2.7.2 layout may proceed.")
    else:
        print("D20 landing: FAIL — V_tune outside window. Finding: no layout.")
        print("Proposal: re-trim at ss85, adjust hold/window, or exclude "
              "edge channels.")

    def jsafe(x):
        if isinstance(x, (float, np.floating)):
            return float(x)
        if isinstance(x, (int, np.integer)):
            return int(x)
        return x

    steps_out = {k: [{kk: jsafe(vv) for kk, vv in r.items()} for r in rows]
                 for k, rows in step_tables.items()}
    json.dump(dict(steps=steps_out, landing=results, pass_=ok_all),
              open(os.path.join(OUT, "p272_gate.json"), "w"), indent=1)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
