#!/usr/bin/env python3
"""Compare fab vs LVS GDS for vco_core_tank.

PDK KLayout LVS recognises inductor2/inductor3 only with IND markers + LA/LB
(and LC) pin texts [PDK ind_*.lvs]. Our L2n0 is an EM octagon without those
markers, so LVS uses a pin-only black-box (cell l2n0) and the fab GDS keeps
the spiral in l2n0_em.

Pass: the two GDS differ only by the presence/absence of cell l2n0_em (and
its shapes). All other top-level cells and instance counts match.
"""
from __future__ import annotations

import os
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FAB = os.path.join(OUT, "vco_core_tank.gds")
LVS = os.path.join(OUT, "vco_core_tank_lvs.gds")
REPORT = os.path.join(OUT, "summary_fab_lvs_gds_diff.txt")


def cell_map(ly: pya.Layout) -> dict[str, pya.Cell]:
    return {c.name: c for c in ly.each_cell()}


def inst_summary(cell: pya.Cell, ly: pya.Layout) -> dict[str, int]:
    counts: dict[str, int] = {}
    for i in cell.each_inst():
        name = i.cell.name
        counts[name] = counts.get(name, 0) + 1
    return counts


def shape_count(cell: pya.Cell) -> int:
    n = 0
    for li in cell.layout().layer_indices():
        n += cell.shapes(li).size()
    return n


def main() -> int:
    lines = ["# fab GDS vs LVS GDS — inductor black-box check\n\n"]
    if not (os.path.exists(FAB) and os.path.exists(LVS)):
        lines.append("MISSING GDS\n")
        open(REPORT, "w").writelines(lines)
        print("".join(lines))
        return 1

    fab = pya.Layout()
    fab.read(FAB)
    lvs = pya.Layout()
    lvs.read(LVS)
    fm = cell_map(fab)
    lm = cell_map(lvs)
    lines.append(f"- fab cells: {sorted(fm)}\n")
    lines.append(f"- LVS cells: {sorted(lm)}\n")

    only_fab = sorted(set(fm) - set(lm))
    only_lvs = sorted(set(lm) - set(fm))
    lines.append(f"- only in fab: {only_fab or 'none'}\n")
    lines.append(f"- only in LVS: {only_lvs or 'none'}\n")

    ok = only_fab == ["l2n0_em"] and only_lvs == []
    # shared cells: instance counts at top must match except l2n0_em
    ft = fab.top_cell()
    lt = lvs.top_cell()
    fi = inst_summary(ft, fab)
    li = inst_summary(lt, lvs)
    lines.append(f"- fab top inst: {fi}\n")
    lines.append(f"- LVS top inst: {li}\n")
    fi2 = {k: v for k, v in fi.items() if k != "l2n0_em"}
    if fi2 != li:
        ok = False
        lines.append(f"- FAIL: top instance mismatch after dropping l2n0_em\n")
    else:
        lines.append("- top instances match after dropping l2n0_em\n")

    if "l2n0_em" in fm:
        lines.append(f"- l2n0_em shapes: {shape_count(fm['l2n0_em'])} "
                     f"bbox {fm['l2n0_em'].bbox().to_dtype(fab.dbu)}\n")
    if "l2n0" in fm and "l2n0" in lm:
        lines.append(f"- l2n0 (pin-only) fab shapes {shape_count(fm['l2n0'])}; "
                     f"LVS shapes {shape_count(lm['l2n0'])}\n")

    lines.append("\n## Inductor recognition [PDK]\n")
    lines.append("- Deck has inductor2 / inductor3 extraction (ind_*.lvs) requiring "
                 "IND drawing + IND:pin LA/LB(/LC) + text marker.\n")
    lines.append("- L2n0 EM GDS has no IND recognition layers → pin-only LVS path.\n")
    lines.append(f"\n## Result: {'PASS' if ok else 'FAIL'}\n")
    open(REPORT, "w").writelines(lines)
    print("".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
