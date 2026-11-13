#!/usr/bin/env python3
"""Finger-count check for P2.7.2b dac / tail / ota [TOOL].

Counts poly gate boxes in each MOS PCell child (same method as bank
check_fingers). Catches ng clamps that still pass LVS on total W.
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

# Schematic targets [SCH amp_common / gen_xschem / build_cells]
EXPECT = {
    "dac_unit": [("pmos mdb", 1), ("pmos msw", 1)],
    "dac_array": [("pmos per unit", 1)],  # each unit child ng=1; 102 devices
    "tail_mt": [("nmos mt", 96)],
    # ota: mo1/mo2 ng=2, mp1/mp2 ng=2, dummies ng=1 [SCH]
    "ota_vds": [("nmos mo", 2), ("pmos mp", 2), ("nmos dum", 1)],
}


def poly_gate_count(cell) -> int:
    """Count fingers = unique poly gate X (PCell ng=1 draws 2 coincident boxes)."""
    poly = cell.layout().layer(5, 0)
    dbu = cell.layout().dbu
    xs = set()
    for s in cell.shapes(poly).each():
        if not s.is_box():
            continue
        b = s.bbox().to_dtype(dbu)
        xs.add(round(0.5 * (b.left + b.right), 3))
    return len(xs)


def mos_children(top):
    """Yield (inst, cell, ng_poly) for each leaf-ish MOS instance."""
    ly = top.layout()
    for inst in top.each_inst():
        cell = ly.cell(inst.cell_index)
        name = cell.name
        # Recurse one level for array of units
        if cell.each_inst():
            kids = list(cell.each_inst())
            if kids:
                for k in kids:
                    kc = ly.cell(k.cell_index)
                    ng = poly_gate_count(kc)
                    if ng > 0:
                        yield k, kc, ng
                continue
        ng = poly_gate_count(cell)
        if ng > 0:
            yield inst, cell, ng


def check_dac_unit(gds):
    ly = pya.Layout()
    ly.read(gds)
    top = ly.top_cell()
    ngs = sorted(
        poly_gate_count(ly.cell(i.cell_index))
        for i in top.each_inst()
        if poly_gate_count(ly.cell(i.cell_index)) > 0
    )
    # Two pmos children, each ng=1 (mdb L=2, msw L=0.13)
    ok = ngs == [1, 1]
    return ok, f"mos_child_ngs={ngs} expect [1,1]"

def check_dac_array(gds):
    ly = pya.Layout()
    ly.read(gds)
    top = ly.top_cell()
    # Each dac_unit_arr has 2 MOS × ng=1; 51 units → 102 devices
    unit_ngs = []
    for inst in top.each_inst():
        cell = ly.cell(inst.cell_index)
        if "dac_unit" not in cell.name:
            continue
        child_ngs = []
        for k in cell.each_inst():
            kc = ly.cell(k.cell_index)
            ng = poly_gate_count(kc)
            if ng > 0:
                child_ngs.append(ng)
        unit_ngs.append(sorted(child_ngs))
    n_units = len(unit_ngs)
    bad = [u for u in unit_ngs if u != [1, 1]]
    ok = n_units == 51 and not bad
    return ok, (f"n_units={n_units} expect 51; "
                f"bad_units={len(bad)} sample={unit_ngs[:2]}")


def check_tail_mt(gds):
    ly = pya.Layout()
    ly.read(gds)
    top = ly.top_cell()
    ngs = []
    for inst in top.each_inst():
        cell = ly.cell(inst.cell_index)
        ng = poly_gate_count(cell)
        if ng > 0:
            ngs.append((cell.name, ng))
    # Largest MOS child should be mt with 96 fingers
    ngs.sort(key=lambda t: -t[1])
    best = ngs[0][1] if ngs else 0
    ok = best == 96
    return ok, f"mos_children={ngs} expect mt ng=96"


def check_ota_vds(gds):
    ly = pya.Layout()
    ly.read(gds)
    top = ly.top_cell()
    ngs = []
    for inst in top.each_inst():
        cell = ly.cell(inst.cell_index)
        ng = poly_gate_count(cell)
        if ng > 0 and ("nmos" in cell.name or "pmos" in cell.name):
            ngs.append((cell.name, ng))
    # Expect: 2× nmos ng=2 (mo), 2× pmos ng=2 (mp), 2× nmos ng=1 (dum)
    from collections import Counter
    cnt = Counter(ngs)
    ok = (cnt[("nmos", 2)] >= 2 and cnt[("pmos", 2)] >= 2
          and cnt[("nmos", 1)] >= 2)
    # name may be nmos$1 etc — match by ng counts only
    by_ng = Counter(ng for _, ng in ngs)
    # Also count by cell name prefix
    nmos_ngs = sorted(ng for name, ng in ngs if "nmos" in name)
    pmos_ngs = sorted(ng for name, ng in ngs if "pmos" in name)
    ok = (sorted(nmos_ngs) == [1, 1, 2, 2] and sorted(pmos_ngs) == [2, 2])
    return ok, f"nmos_ngs={nmos_ngs} pmos_ngs={pmos_ngs} expect n[1,1,2,2] p[2,2]"


def check_d9_rc(gds):
    ly = pya.Layout()
    ly.read(gds)
    top = ly.top_cell()
    ngs = []
    for inst in top.each_inst():
        cell = ly.cell(inst.cell_index)
        if "nmos" not in cell.name:
            continue
        ng = poly_gate_count(cell)
        if ng > 0:
            ngs.append(ng)
    ok = ngs == [4]
    return ok, f"mbp_rbf ngs={ngs} expect [4]"


def main():
    lines = [
        "# Finger-count check — P2.7.2b dac / tail / ota / d9 [TOOL]\n\n",
        "Method: tall/thin poly boxes in each MOS PCell child "
        "(excludes straps). Catches ng clamp vs total-W LVS pass.\n\n",
        "| cell | check | PASS |\n",
        "|---|---|---|\n",
    ]
    ok_all = True
    checks = [
        ("dac_unit", check_dac_unit),
        ("dac_array", check_dac_array),
        ("tail_mt", check_tail_mt),
        ("ota_vds", check_ota_vds),
        ("d9_rc", check_d9_rc),
    ]
    for name, fn in checks:
        gds = os.path.join(OUT, f"{name}.gds")
        if not os.path.exists(gds):
            # try gunzip
            gz = gds + ".gz"
            if os.path.exists(gz):
                import gzip
                import shutil
                with gzip.open(gz, "rb") as fi, open(gds, "wb") as fo:
                    shutil.copyfileobj(fi, fo)
            else:
                lines.append(f"| {name} | missing gds | NO |\n")
                print(f"{name}: MISSING", flush=True)
                ok_all = False
                continue
        ok, detail = fn(gds)
        ok_all = ok_all and ok
        lines.append(f"| {name} | {detail} | {'yes' if ok else 'NO'} |\n")
        print(f"{name}: {'PASS' if ok else 'FAIL'} — {detail}", flush=True)
    lines.append(f"\nAll match: {'yes' if ok_all else 'NO'}\n")
    path = os.path.join(OUT, "summary_finger_check.txt")
    open(path, "w").writelines(lines)
    print(f"Wrote {path}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
