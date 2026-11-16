#!/usr/bin/env python3
"""Finger checks for P2.7.2b D22 cells [TOOL]."""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

sys.path[:0] = [
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python",
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python/pycell4klayout-api/source/python",
]
import pya  # noqa: E402


def poly_gate_count(cell) -> int:
    poly = cell.layout().layer(5, 0)
    dbu = cell.layout().dbu
    xs = set()
    for s in cell.shapes(poly).each():
        if not s.is_box():
            continue
        b = s.bbox().to_dtype(dbu)
        xs.add(round(0.5 * (b.left + b.right), 3))
    return len(xs)


def load(name):
    gds = os.path.join(OUT, f"{name}.gds")
    if not os.path.exists(gds):
        return None
    ly = pya.Layout()
    ly.read(gds)
    return ly


def _walk(ly, cell, pred, out):
    for inst in cell.each_inst():
        child = ly.cell(inst.cell_index)
        if pred(child.name):
            out.append(child)
        _walk(ly, child, pred, out)


def nmos_ngs(ly):
    found = []
    _walk(ly, ly.top_cell(), lambda n: "nmos" in n.lower(), found)
    return sorted(poly_gate_count(c) for c in found if poly_gate_count(c) > 0)


def main():
    lines = ["# Finger check — P2.7.2b D22 [TOOL]\n\n",
             "| cell | check | PASS |\n|---|---|---|\n"]
    ok_all = True
    checks = [
        ("det_sf_pair", lambda ngs: ngs == [1, 1, 1, 1, 1, 1],
         "6× ng=1 (4 SF + 2 dum)"),
        ("cmp_se", lambda ngs: ngs.count(2) >= 4,
         "≥4× ng=2 input/SE (+ dum ng=1)"),
        ("bias_pd", lambda ngs: ngs.count(2) == 2 and ngs.count(1) >= 8,
         "2× ng=2 (tt/ss) + ≥8× ng=1 (sinks+en+diode)"),
    ]
    for name, pred, expect in checks:
        ly = load(name)
        if ly is None:
            lines.append(f"| {name} | missing gds | NO |\n")
            ok_all = False
            continue
        ngs = nmos_ngs(ly)
        ok = pred(ngs)
        ok_all = ok_all and ok
        lines.append(f"| {name} | ngs={ngs} expect {expect} | "
                     f"{'yes' if ok else 'NO'} |\n")
        print(f"{name}: {'PASS' if ok else 'FAIL'} — {ngs}")
    lines.append(f"\nAll match: {'yes' if ok_all else 'NO'}\n")
    path = os.path.join(OUT, "summary_finger_check.txt")
    open(path, "w").writelines(lines)
    print(f"Wrote {path}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
