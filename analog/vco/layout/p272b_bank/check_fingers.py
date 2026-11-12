#!/usr/bin/env python3
"""Count switch fingers vs cell_sizes.json ng [TOOL].

Uses poly gate boxes inside the nmos child instance (same method as
build_cells.poly_gates), not flattened M1.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SIZES = json.load(open(os.path.join(HERE, "cell_sizes.json")))

sys.path[:0] = [
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python",
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python/pycell4klayout-api/source/python",
]
import pya  # noqa: E402


def count_ng(gds_path: str) -> int:
    ly = pya.Layout()
    ly.read(gds_path)
    top = ly.top_cell()
    poly = ly.layer(5, 0)
    # Largest child by bbox area is the switch (thermo / MSB)
    best = None
    best_a = -1.0
    for inst in top.each_inst():
        bb = inst.bbox().to_dtype(ly.dbu)
        a = bb.width() * bb.height()
        # Prefer wide short devices (fingered MOS), skip MIMs (square-ish large)
        aspect = bb.width() / max(bb.height(), 0.1)
        if aspect < 3.0:
            continue
        if a > best_a:
            best_a = a
            best = inst
    if best is None:
        # fallback: most poly boxes in any child
        nmax = 0
        for inst in top.each_inst():
            cell = ly.cell(inst.cell_index)
            n = sum(1 for s in cell.shapes(poly).each() if s.is_box())
            nmax = max(nmax, n)
        return nmax
    cell = ly.cell(best.cell_index)
    boxes = [s.bbox() for s in cell.shapes(poly).each() if s.is_box()]
    # One poly box per finger gate
    return len(boxes)


def main():
    lines = ["# Finger-count check vs cell_sizes.json [TOOL]\n\n",
             "Method: poly gate boxes in the widest MOS child instance.\n\n",
             "| cell | sch ng | layout ng | PASS |\n",
             "|---|---|---|---|\n"]
    ok = True
    checks = [
        ("bank_cell_u", SIZES[5]["ng"]),
        ("bank_cell_dummy", SIZES[5]["ng"]),
        ("bank_cell_u0", SIZES[5]["ng"]),
        ("bank_cell_b4", SIZES[4]["ng"]),
        ("bank_cell_b0", SIZES[0]["ng"]),
    ]
    for name, sch_ng in checks:
        gds = os.path.join(OUT, f"{name}.gds")
        if not os.path.exists(gds):
            lines.append(f"| {name} | {sch_ng} | missing | NO |\n")
            ok = False
            continue
        ng_lay = count_ng(gds)
        pass_ = ng_lay == int(sch_ng)
        ok = ok and pass_
        lines.append(
            f"| {name} | {sch_ng} | {ng_lay} | {'yes' if pass_ else 'NO'} |\n")
        print(f"{name}: sch={sch_ng} lay={ng_lay} "
              f"{'PASS' if pass_ else 'FAIL'}", flush=True)
    lines.append(f"\nAll match: {'yes' if ok else 'NO'}\n")
    path = os.path.join(OUT, "summary_finger_check.txt")
    open(path, "w").writelines(lines)
    print(f"Wrote {path}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
