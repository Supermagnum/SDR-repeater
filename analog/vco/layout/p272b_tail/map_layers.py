#!/usr/bin/env python3
"""Per-child metal/via layer usage for tail_block join routing [GDS]."""
from __future__ import annotations

import json
import os

import pya

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
LAYERS = [
    ("Metal1", 8, 0), ("Via1", 9, 0), ("Metal2", 10, 0), ("Via2", 11, 0),
    ("Metal3", 30, 0), ("Via3", 29, 0), ("Metal4", 50, 0), ("Via4", 51, 0),
    ("Metal5", 67, 0), ("TopVia1", 125, 0), ("TopMetal1", 126, 0),
    ("TopVia2", 127, 0), ("TopMetal2", 134, 0),
]


def main():
    rows = []
    for name in ("dac_array", "tail_mt", "ota_vds", "d9_rc", "cbf"):
        ly = pya.Layout()
        ly.read(os.path.join(OUT, f"{name}.gds"))
        c = ly.top_cell()
        bb = c.bbox().to_dtype(ly.dbu)
        area = round(bb.width() * bb.height() * 1e-6, 4)
        cell = {
            "cell": name,
            "bbox_um": [round(bb.left, 3), round(bb.bottom, 3),
                        round(bb.right, 3), round(bb.top, 3)],
            "area_mm2": area,
            "layers": {},
        }
        for lname, L, D in LAYERS:
            lyr = ly.layer(L, D)
            r = pya.Region(c.begin_shapes_rec(lyr))
            if r.is_empty():
                continue
            b = r.bbox().to_dtype(ly.dbu)
            cell["layers"][lname] = {
                "bbox_um": [round(b.left, 3), round(b.bottom, 3),
                            round(b.right, 3), round(b.top, 3)],
                "area_um2": round(r.area() * ly.dbu * ly.dbu, 3),
            }
        rows.append(cell)
        print(f"=== {name} bbox {bb} area={area:.4f} mm2")
        for ln, info in cell["layers"].items():
            print(f"  {ln:12s} area={info['area_um2']:10.1f} um2  "
                  f"bbox={info['bbox_um']}")
    path = os.path.join(OUT, "summary_join_layer_map.json")
    open(path, "w").write(json.dumps(rows, indent=2) + "\n")
    print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
