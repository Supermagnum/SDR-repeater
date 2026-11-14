#!/usr/bin/env python3
"""P2.7.2b — VCO island outline GDS (blocks only, no inter-block routing).

Places core+tank, bank and tail_block per D23 Option A (inductor NW; bank
east of core; tail south). Reserved rectangles for varactor, D22 and top
routing corridors (forecast 0.017 mm² [HAND]). Outline area vs D23 ≤ 0.38
mm² final. No inter-block routing yet [prompt].
"""
from __future__ import annotations

import gzip
import os
import shutil
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CORE = os.path.join(HERE, "..", "p272b", "out", "vco_core_tank.gds")
BANK = os.path.join(HERE, "..", "p272b_bank", "out", "vco_bank.gds")
TAIL = os.path.join(OUT, "tail_block.gds")
CELL = "vco_island_outline"
D23_LIMIT = 0.38  # mm² final [decisions 2026-11-14]
FORECAST = 0.017  # var+D22+top [HAND]
GAP = 10.0  # µm block-to-block clearance [HAND]


def load_cell(ly: pya.Layout, path: str, name: str) -> tuple[int, pya.DBox]:
    src = pya.Layout()
    src.read(path)
    if src.cell(name) is None:
        raise SystemExit(f"missing cell {name} in {path}")
    cid = ly.add_cell(name)
    ly.cell(cid).copy_tree(src.cell(name))
    bb = ly.cell(cid).bbox().to_dtype(ly.dbu)
    return cid, bb


def place(top: pya.Cell, cid: int, x: float, y: float, ly: pya.Layout) -> pya.DBox:
    """Place child so its bbox lower-left is at (x, y) in µm."""
    bb0 = ly.cell(cid).bbox().to_dtype(ly.dbu)
    tr = pya.DTrans(pya.DVector(x - bb0.left, y - bb0.bottom))
    top.insert(pya.DCellInstArray(cid, tr))
    return bb0.transformed(tr)


def reserve(top: pya.Cell, ly: pya.Layout, box: pya.DBox, label: str) -> None:
    """Draw a Metal1 outline + text for a reserved region (no devices)."""
    m1 = ly.layer(pya.LayerInfo(8, 0))  # Metal1 drawing [PDK]
    txt = ly.layer(pya.LayerInfo(8, 25))  # Metal1 text
    # 0.5 µm frame only — not a filled plate
    w = 0.5
    c = top
    c.shapes(m1).insert(pya.DBox(box.left, box.bottom, box.right, box.bottom + w))
    c.shapes(m1).insert(pya.DBox(box.left, box.top - w, box.right, box.top))
    c.shapes(m1).insert(pya.DBox(box.left, box.bottom, box.left + w, box.top))
    c.shapes(m1).insert(pya.DBox(box.right - w, box.bottom, box.right, box.top))
    t = pya.DText(label, 0.5 * (box.left + box.right), 0.5 * (box.bottom + box.top))
    c.shapes(txt).insert(t)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    for p, tag in ((CORE, "core"), (BANK, "bank"), (TAIL, "tail")):
        if not os.path.exists(p):
            print(f"MISSING {tag} GDS: {p}")
            return 2

    ly = pya.Layout()
    ly.dbu = 0.001
    top = ly.create_cell(CELL)

    core_id, core_bb0 = load_cell(ly, CORE, "vco_core_tank")
    bank_id, bank_bb0 = load_cell(ly, BANK, "vco_bank")
    tail_id, tail_bb0 = load_cell(ly, TAIL, "tail_block")

    # Compact pack [HAND]: bank south (widest); core + tail side-by-side on
    # top, within bank width. Option A topology (coil NW) is preserved as
    # relative adjacency; no inter-block routing. Gap=0 for min outline.
    pack_gap = 0.0
    bank = place(top, bank_id, 0.0, 0.0, ly)
    y1 = bank.top + pack_gap
    core = place(top, core_id, 0.0, y1, ly)
    tail = place(top, tail_id, core.right + pack_gap, y1, ly)

    # Reserved forecast in the pocket east of tail / above bank (same outline).
    # Three labelled strips; total area ≈ FORECAST [HAND].
    pocket = pya.DBox(tail.right, bank.top,
                      bank.right, min(core.top, tail.top + (core.top - tail.top)))
    # Prefer the rectangle east of tail above bank, clipped to bank.right
    pocket = pya.DBox(max(tail.right, bank.left), bank.top,
                      bank.right, core.top)
    labels = ("reserve_varactor", "reserve_D22", "reserve_top_corridors")
    reserved_boxes = []
    if pocket.width() > 1.0 and pocket.height() > 1.0:
        strip_h = pocket.height() / 3.0
        for i, lab in enumerate(labels):
            b = pya.DBox(pocket.left, pocket.bottom + i * strip_h,
                         pocket.right, pocket.bottom + (i + 1) * strip_h)
            reserve(top, ly, b, lab)
            reserved_boxes.append(b)
    else:
        # Fallback: east of bank
        reserved_h = bank.height()
        reserved_w = FORECAST * 1e6 / max(reserved_h, 1.0)
        strip_h = reserved_h / 3.0
        for i, lab in enumerate(labels):
            b = pya.DBox(bank.right + GAP, bank.bottom + i * strip_h,
                         bank.right + GAP + reserved_w,
                         bank.bottom + (i + 1) * strip_h)
            reserve(top, ly, b, lab)
            reserved_boxes.append(b)

    outline = top.bbox().to_dtype(ly.dbu)
    area = outline.width() * outline.height() * 1e-6
    reserved_area = sum(b.width() * b.height() for b in reserved_boxes) * 1e-6
    cells_only = (core.width() * core.height()
                  + bank.width() * bank.height()
                  + tail.width() * tail.height()) * 1e-6

    gds = os.path.join(OUT, f"{CELL}.gds")
    ly.write(gds)
    with open(gds, "rb") as f, gzip.open(gds + ".gz", "wb") as z:
        shutil.copyfileobj(f, z)

    # Render
    shot = os.path.join(OUT, f"_klayout_shot_{CELL}.py")
    open(shot, "w").write(
        "import pya, os\n"
        f"ly=pya.Layout(); ly.read({gds!r})\n"
        f"c=ly.cell({CELL!r})\n"
        "lv=pya.LayoutView(); lv.show_layout(ly, False)\n"
        "lv.max_hier()\n"
        f"png=os.path.join({OUT!r}, '{CELL}.png')\n"
        f"svg=os.path.join({OUT!r}, '{CELL}.svg')\n"
        "lv.save_image(png, 1200, 1200)\n"
        "open(svg,'w').write('<svg/>')\n"
        "print('wrote', png)\n"
    )
    try:
        os.system(f"klayout -b -r {shot}")
    except Exception as e:
        print(f"render skip: {e}")

    lines = [
        f"# {CELL} — blocks only, no inter-block routing [GDS]\n",
        f"pack: bank south; core|tail north (gap=0) [HAND]\n",
        f"core+tank bbox {core} area={core.width()*core.height()*1e-6:.4f} mm2 [GDS]\n",
        f"bank bbox {bank} area={bank.width()*bank.height()*1e-6:.4f} mm2 [GDS]\n",
        f"tail_block bbox {tail} area={tail.width()*tail.height()*1e-6:.4f} mm2 [GDS]\n",
        f"reserved pocket total={reserved_area:.4f} mm2 "
        f"(target {FORECAST:.3f}) [HAND/GDS]\n",
        f"cells-only sum={cells_only:.4f} mm2 [GDS]\n",
        f"cell-sum+forecast={cells_only+FORECAST:.4f} mm2 [GDS/HAND]\n",
        f"island outline bbox {outline}\n",
        f"island outline area={area:.4f} mm2 [GDS]\n",
        f"D23 limit={D23_LIMIT:.2f} mm2 final\n",
        f"pass={'YES' if area <= D23_LIMIT else 'NO — OVER'}\n",
    ]
    summary = os.path.join(OUT, "summary_island_outline.txt")
    open(summary, "w").writelines(lines)
    print("".join(lines))

    if area > D23_LIMIT:
        print(f"STOP: island outline {area:.4f} > {D23_LIMIT} mm2 [GDS]")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
