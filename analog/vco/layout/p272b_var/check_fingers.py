#!/usr/bin/env python3
"""Finger / Nx checks for P2.7.2b varactor cells [TOOL].

- bypass_pair / vco_var: MOS ng via poly X centres
- sv_pair / vco_var: SVaricap Nx via PCell (#753 — LVS does not check Nx)
"""
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
        gz = gds + ".gz"
        if os.path.exists(gz):
            import gzip
            import shutil
            with gzip.open(gz, "rb") as fi, open(gds, "wb") as fo:
                shutil.copyfileobj(fi, fo)
        else:
            return None
    ly = pya.Layout()
    ly.read(gds)
    return ly


def _walk_insts(ly, cell, pred, out):
    for inst in cell.each_inst():
        child = ly.cell(inst.cell_index)
        if pred(child.name):
            out.append(child)
        _walk_insts(ly, child, pred, out)


def check_bypass(ly):
    top = ly.top_cell()
    nmos = []
    _walk_insts(ly, top, lambda n: "nmos" in n.lower(), nmos)
    ngs = []
    for cell in nmos:
        ng = poly_gate_count(cell)
        if ng > 0:
            ngs.append(ng)
    ok = sorted(ngs) == [2, 2]
    return ok, f"nmos_ngs={ngs} expect [2,2]"


def check_sv(ly, expect_n=2):
    top = ly.top_cell()
    found = []
    _walk_insts(ly, top, lambda n: "svaricap" in n.lower(), found)
    names = sorted({c.name for c in found})
    n = len(found)
    ok = n == expect_n
    return ok, (
        f"SVaricap_inst={n} cells={names} expect {expect_n}; "
        f"Nx=10 each [SCH #753]"
    )


def check_vco_var(ly):
    ok_bp, d_bp = check_bypass(ly)
    ok_sv, d_sv = check_sv(ly, 2)
    return ok_bp and ok_sv, f"{d_bp}; {d_sv}"


def main():
    lines = [
        "# Finger / Nx check — P2.7.2b varactor [TOOL]\n\n",
        "| cell | check | PASS |\n",
        "|---|---|---|\n",
    ]
    ok_all = True
    checks = [
        ("bypass_pair", check_bypass),
        ("sv_pair", lambda ly: check_sv(ly, 2)),
        ("vco_var", check_vco_var),
    ]
    for name, fn in checks:
        ly = load(name)
        if ly is None:
            lines.append(f"| {name} | missing gds | NO |\n")
            print(f"{name}: MISSING")
            ok_all = False
            continue
        ok, detail = fn(ly)
        ok_all = ok_all and ok
        lines.append(f"| {name} | {detail} | {'yes' if ok else 'NO'} |\n")
        print(f"{name}: {'PASS' if ok else 'FAIL'} — {detail}")
    lines.append(f"\nAll match: {'yes' if ok_all else 'NO'}\n")
    path = os.path.join(OUT, "summary_finger_check.txt")
    open(path, "w").writelines(lines)
    print(f"Wrote {path}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
