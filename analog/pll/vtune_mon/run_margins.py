#!/usr/bin/env python3
"""Combined corner × mismatch margins for the V_tune monitor (both hyst edges).

    python3 -u run_margins.py [n=30] | tee out/summary_margins.txt

Option B (V_hi): at ss, hi_rise+3σ ≤ 0.82 V; at tt/ss, hi_fall−3σ ≥ that corner's
cal landing top (ff may trip below ff cal top 0.82 V).
"""
import os
import sys

import numpy as np

import run_vtune_mon as m

ARGS = sys.argv[1:]
N = 30
for a in ARGS:
    if a.startswith("n="):
        N = int(a.split("=", 1)[1])

CAL_LO, WIN_LO = 0.34, 0.25
# D20 landing tops [MODEL]; ss hi_rise+3σ must stay ≤ SS_HI_CAP
CAL_TOP = {"tt": 0.74, "ss": 0.67, "ff": 0.82}
SS_HI_CAP = 0.82  # option B: ss high trip +3σ ceiling


def corner_family(name):
    if name.startswith("ss"):
        return "ss"
    if name.startswith("ff"):
        return "ff"
    return "tt"


def mc_corner(name, mos, vdd, temp, n, rng):
    edges = {k: [] for k in ("lo_fall", "lo_rise", "hi_rise", "hi_fall")}
    for k in range(n):
        dlo = 1 + 0.01 * rng.standard_normal(2)
        dhi = 1 + 0.01 * rng.standard_normal(2)
        body = m.sweep_body(mos, vdd, slo=dlo, shi=dhi)
        tag = f"mg_{name.replace(' ', '_').replace('−', 'm').replace('°', '')}_{k}"
        m.run_vacask(
            tag, body,
            f"  options temp={temp}\n  save v(vt) v(vtune_lo) v(vtune_hi)\n"
            f"  analysis op1 op\n"
            f'  analysis tr tran stop=102u step=20n maxstep=50n icmode="op"\n',
        )
        tr = m.extract_trips(os.path.join(m.OUT, "tr.raw"), vdd)
        for key in edges:
            edges[key].append(float(tr[key]))
    return {k: np.array(v) for k, v in edges.items()}


def stats(arr):
    mu, sig = float(np.nanmean(arr)), float(np.nanstd(arr))
    return mu, sig, mu + 3 * sig, mu - 3 * sig


def main():
    print("# V_tune monitor — corner × mismatch (option B) [SCH]\n")
    print(f"Thresholds: V_lo = {m.VLO:.3f} V, V_hi = {m.VHI:.3f} V. "
          f"Mismatch: 1 % relative σ on input-pair W, n = {N} per corner.\n")
    print(f"Option B: ss hi_rise+3σ ≤ {SS_HI_CAP} V; "
          f"hi_fall−3σ ≥ cal landing top except ff "
          f"(tt {CAL_TOP['tt']}, ss {CAL_TOP['ss']}, ff {CAL_TOP['ff']} V).\n")

    rng = np.random.default_rng(7)
    rows = []
    print("| Corner | edge | mean (V) | σ (mV) | +3σ (V) | −3σ (V) |")
    print("|---|---|---|---|---|---|")
    by_corner = {}
    for name, mos, vdd, temp in m.CORNERS:
        print(f"  … {name}", flush=True)
        edges = mc_corner(name, mos, vdd, temp, N, rng)
        by_corner[name] = {}
        for key in ("lo_fall", "lo_rise", "hi_rise", "hi_fall"):
            mu, sig, p3, m3 = stats(edges[key])
            print(f"| {name} | {key} | {mu:.4f} | {sig*1e3:.2f} | {p3:.4f} | {m3:.4f} |")
            rows.append((name, key, mu, sig, p3, m3))
            by_corner[name][key] = (mu, sig, p3, m3)

    def worst(key, which):
        cands = [(r[0], r[4] if which == "high" else r[5], r[2], r[3]) for r in rows if r[1] == key]
        return max(cands, key=lambda x: x[1]) if which == "high" else min(cands, key=lambda x: x[1])

    lo_fall_w = worst("lo_fall", "high")
    lo_rise_w = worst("lo_rise", "low")

    print("\n## Option B checks (per corner family)\n")
    print("| Corner | hi_rise +3σ (V) | vs 0.82 (ss only) | hi_fall −3σ (V) | cal top (V) | ≥ cal top? |")
    print("|---|---|---|---|---|---|")
    ok = True
    for name, data in by_corner.items():
        fam = corner_family(name)
        hr_p3 = data["hi_rise"][2]
        hf_m3 = data["hi_fall"][3]
        cal = CAL_TOP[fam]
        if fam == "ss":
            ss_ok = hr_p3 <= SS_HI_CAP + 1e-4
            ss_m = SS_HI_CAP - hr_p3
            ss_cell = f"{'PASS' if ss_ok else 'FAIL'} ({ss_m:+.4f} V)"
            if not ss_ok:
                ok = False
        else:
            ss_cell = "—"
        if fam == "ff":
            cal_cell = "allowed below"
            cal_ok = True
        else:
            cal_ok = hf_m3 >= cal - 1e-4
            cal_cell = f"{'PASS' if cal_ok else 'FAIL'} ({hf_m3 - cal:+.4f} V)"
            if not cal_ok:
                ok = False
        print(f"| {name} | {hr_p3:.4f} | {ss_cell} | {hf_m3:.4f} | {cal} | {cal_cell} |")

    print("\n## Low-side margins (all corners)\n")
    print("| Check | Worst edge (V) | Margin (V) |")
    print("|---|---|---|")
    print(f"| lo_fall+3σ vs cal floor {CAL_LO} | {lo_fall_w[1]:.4f} ({lo_fall_w[0]}) | "
          f"{CAL_LO - lo_fall_w[1]:+.4f} |")
    print(f"| lo_rise−3σ vs window {WIN_LO} | {lo_rise_w[1]:.4f} ({lo_rise_w[0]}) | "
          f"{lo_rise_w[1] - WIN_LO:+.4f} |")
    if CAL_LO - lo_fall_w[1] < 0 or lo_rise_w[1] - WIN_LO < 0:
        ok = False

    print("\n## Verdict\n")
    print("**PASS — option B met.**" if ok else "**FAIL — adjust V_hi or hyst.**")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
