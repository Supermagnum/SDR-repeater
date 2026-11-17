#!/usr/bin/env python3
"""P2.7.2c — band range with island + bank + core tank parasitics [SCH].

Adds per-side shunt C and series R (high end of each reported range) to tp/tn:
  island routing   59.4 fF [HAND]  (p272c summary_build_controls)
  bank wiring      40   fF [HAND]  (p272b_bank summary_rc_bank high end)
  core-internal    30   fF [HAND]  (p272b summary_rc_tank high end)
  series R         3.4  Ω  [HAND]  (island ≈3 Ω + core 0.4 Ω high end)

Model per side: Rseries from tank pin into a node with C to gnd (stub RC).

Least-margin corners from summary_p272c_cover / summary_bank_ng100_range:
  top:    mos_ss / cap_wcs / −40 °C
  bottom: mos_ss / cap_bcs / −40 °C

Pass (decisions 2026-11-17 re-pack result): top margin ≥ 1 % ≈ 40 MHz [SCH].
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "step2"))
import run_step2 as S2  # noqa: E402
import run_step3 as S3  # noqa: E402
from run_p272c_gate import V_SS, _patch_vdd  # noqa: E402

# High end of each range [HAND / prior reports]
C_ISLAND_FF = 59.4
C_BANK_FF = 40.0
C_CORE_FF = 30.0
C_SIDE_FF = C_ISLAND_FF + C_BANK_FF + C_CORE_FF  # 129.4
R_SERIES = 3.4  # Ω

CASES = [
    ("top", "mos_ss", "cap_wcs", -40, 0, 1.0),
    ("bot", "mos_ss", "cap_bcs", -40, None, 0.3),
]

PARASITIC_EXTRA = (
    f"Rr_p (tp nr_p) resistor r={R_SERIES}\n"
    f"Cr_p (nr_p 0) capacitor c={C_SIDE_FF}f\n"
    f"Rr_n (tn nr_n) resistor r={R_SERIES}\n"
    f"Cr_n (nr_n 0) capacitor c={C_SIDE_FF}f\n"
)


def run_case(tag, mos, cap, temp, code, vt, extra=""):
    if code is None:
        code = S2.CMAX
    itail = S3.itail_for(4.4e9 if tag == "top" else 2.95e9, S3.load_sizing()[1])
    S3.set_corner(mos, cap)
    title = f"p272c_rc_{'par' if extra else 'base'}_{tag}_{mos}_{cap}_{temp}"
    sim = S2.netlist(
        title, code, vt, itail=itail,
        analysis=(f"  options temp={temp}\n  save v(tp) v(tn) v(tail)\n"
                  "  analysis tr tran stop=60n step=5p maxstep=5p"),
        vct=V_SS, extra=extra)
    _patch_vdd(sim, V_SS)
    S2.run(sim)
    return S2.measure(os.path.join(OUT, "tr.raw"))


def main():
    S2.OUT = S3.OUT = OUT
    S3.load_sizing()
    lines = [
        "# P2.7.2c band coverage with routing parasitics [SCH]\n\n",
        "Parasitics per tank side (high end of each range):\n",
        f"- island routing C = {C_ISLAND_FF} fF [HAND] "
        "(p272c summary_build_controls)\n",
        f"- bank wiring C = {C_BANK_FF} fF [HAND] "
        "(p272b_bank summary_rc_bank)\n",
        f"- core-internal C = {C_CORE_FF} fF [HAND] "
        "(p272b summary_rc_tank)\n",
        f"- total C/side = {C_SIDE_FF} fF [HAND]\n",
        f"- series R = {R_SERIES} Ω [HAND] "
        "(island ≈3 Ω + core 0.4 Ω)\n",
        "Model: Rseries from tp/tn into C to gnd (stub RC).\n\n",
        "Pass gate: top margin ≥ 1 % ≈ 40 MHz "
        "(decisions 2026-11-17 re-pack result).\n\n",
        "| case | parasitics | MOS | CAP | T | code | Vtune | f (GHz) | "
        "limit | margin (MHz) | Amp | PASS |\n",
        "|---|---|---|---|---|---|---|---|---|---|---|---|\n",
    ]
    print("".join(lines[:8]), flush=True)
    results = {}
    ok_par = True
    for extra, label in (("", "none"), (PARASITIC_EXTRA, "island+bank+core")):
        for tag, mos, cap, temp, code, vt in CASES:
            m = run_case(tag, mos, cap, temp, code, vt, extra=extra)
            if tag == "top":
                limit, margin = 4.20e9, m["f"] - 4.20e9
                ok = m["f"] >= 4.20e9
                if label != "none":
                    ok_par = ok_par and (margin >= 40e6)
            else:
                limit, margin = 3.12e9, 3.12e9 - m["f"]
                ok = m["f"] <= 3.12e9
                if label != "none":
                    ok_par = ok_par and ok
            code_v = code if code is not None else S2.CMAX
            row = (f"| {tag} | {label} | {mos} | {cap} | {temp} | {code_v} | "
                   f"{vt:.1f} | {m['f']/1e9:.3f} | {limit/1e9:.2f} | "
                   f"{margin/1e6:.0f} | {m['amp']:.2f} | "
                   f"{'yes' if ok else 'NO'} |")
            print(row, flush=True)
            lines.append(row + "\n")
            results[(tag, label)] = margin
    # deltas
    lines.append("\n## Margin change (parasitics − none) [SCH]\n\n")
    for tag in ("top", "bot"):
        d = (results[(tag, "island+bank+core")] - results[(tag, "none")]) / 1e6
        lines.append(
            f"- {tag}: {results[(tag, 'none')]/1e6:.0f} → "
            f"{results[(tag, 'island+bank+core')]/1e6:.0f} MHz "
            f"(Δ {d:+.0f} MHz)\n")
    gate = (
        results[("top", "island+bank+core")] >= 40e6
        and results[("bot", "island+bank+core")] > 0
    )
    lines.append(
        f"\nGate (≥ 40 MHz top margin with parasitics): "
        f"{'PASS' if gate else 'FAIL'} [SCH].\n")
    print(lines[-1], flush=True)
    path = os.path.join(OUT, "summary_p272c_route_c_range.txt")
    open(path, "w").writelines(lines)
    # also copy under p272c out for the layout job
    dest = os.path.join(
        HERE, "..", "layout", "p272c", "out", "summary_p272c_route_c_range.txt")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w").writelines(lines)
    print(f"Wrote {path}\nWrote {dest}")
    return 0 if gate else 1


if __name__ == "__main__":
    sys.exit(main())
