#!/usr/bin/env python3
"""P2.7.2b bank fix: band-range at least-margin corners after ng≤100 [SCH].

Worst corners from summary_p272c_cover.txt:
  top:    mos_ss / cap_wcs / −40 °C  (margin was 130 MHz)
  bottom: mos_ss / cap_bcs / −40 °C  (margin was 76 MHz)

Pass: both cover 3.12–4.20 GHz (spec/vco-topology.md §9).
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "step2"))
import run_step2 as S2  # noqa: E402
import run_step3 as S3  # noqa: E402
from run_p272c_gate import V_SS, _patch_vdd  # noqa: E402

CASES = [
    ("top", "mos_ss", "cap_wcs", -40, 0, 1.0),
    ("bot", "mos_ss", "cap_bcs", -40, None, 0.3),  # code filled below
]


def main():
    S2.OUT = S3.OUT = OUT
    r, meas = S3.load_sizing()
    i_top = S3.itail_for(4.4e9, meas)
    i_bot = S3.itail_for(2.95e9, meas)
    lines = [
        "# P2.7.2b bank fix — band range after thermo ng=100 (same W) [SCH]\n\n",
        "Finger fix: sch/layout/step2 clamp ng ≤ 100 at W=308.58 µm "
        "(was formula ng=123). V_pad ss = "
        f"{V_SS:.3f} V [HAND].\n\n",
        "| case | MOS | CAP | T | code | Vtune | f (GHz) | limit | margin (MHz) | "
        "Amp | PASS |\n",
        "|---|---|---|---|---|---|---|---|---|---|---|\n",
    ]
    print("".join(lines[:2]), flush=True)
    ok_all = True
    for tag, mos, cap, temp, code, vt in CASES:
        if code is None:
            code = S2.CMAX
        itail = i_top if tag == "top" else i_bot
        S3.set_corner(mos, cap)
        sim = S2.netlist(
            f"ng100_{tag}_{mos}_{cap}_{temp}", code, vt, itail=itail,
            analysis=(f"  options temp={temp}\n  save v(tp) v(tn) v(tail)\n"
                      "  analysis tr tran stop=60n step=5p maxstep=5p"),
            vct=V_SS)
        _patch_vdd(sim, V_SS)
        S2.run(sim)
        m = S2.measure(os.path.join(OUT, "tr.raw"))
        if tag == "top":
            limit, margin = 4.20e9, m["f"] - 4.20e9
            ok = m["f"] >= 4.20e9
        else:
            limit, margin = 3.12e9, 3.12e9 - m["f"]
            ok = m["f"] <= 3.12e9
        ok_all = ok_all and ok
        row = (f"| {tag} | {mos} | {cap} | {temp} | {code} | {vt:.1f} | "
               f"{m['f']/1e9:.3f} | {limit/1e9:.2f} | {margin/1e6:.0f} | "
               f"{m['amp']:.2f} | {'yes' if ok else 'NO'} |")
        print(row, flush=True)
        lines.append(row + "\n")
    lines.append(
        f"\nCoverage PASS: {'yes' if ok_all else 'NO'} "
        "(3.12–4.20 GHz at least-margin corners) [SCH].\n")
    print(lines[-1], flush=True)
    path = os.path.join(OUT, "summary_bank_ng100_range.txt")
    open(path, "w").writelines(lines)
    print(f"Wrote {path}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
