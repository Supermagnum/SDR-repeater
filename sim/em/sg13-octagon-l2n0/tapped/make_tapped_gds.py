#!/usr/bin/env python3
"""Tapped L2n0 GDS: clone two-port cell, add CT via on the north track + port 203.

The two-port octagon is a single wide ring (L134). Ports P/N are south; the
electrical midpoint of the winding is the north track centre ≈ (0, 273) µm.
CT via lands there (same 10.8 µm via size as the existing TM1↔L134 vias).
TM1 stub runs south to a new port marker on layer 203.
"""
import os
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "vendor", "gds2openEMS", "workflow", "L_2n0_twoport.gds")
OUT = os.path.join(HERE, "L_2n0_tapped.gds")


def main():
    layout = pya.Layout()
    layout.read(SRC)
    dbu = layout.dbu
    top = layout.cell(next(layout.each_top_cell()))
    top.name = "L_2n0_tapped"

    def um(u):
        return int(round(u / dbu))

    l_tm1 = layout.layer(126, 0)   # TopMetal1 leads
    l_via = layout.layer(133, 0)   # vias TM1↔L134
    l_p3 = layout.layer(203, 0)    # CT port marker

    # North-track electrical mid. Metal at x=0 spans y≈262..279; a narrow
    # bridge at y≈269..271 is only ~17 µm wide, so the CT via is 8 µm
    # (existing P/N vias are ~10.8 µm and sit off-centre on the wide flats).
    cx, cy = 0.0, 270.25
    via = 8.0

    # TM1 stub: from north track down to south port row (y=0), 12 µm wide
    # like the existing P/N leads. Overlaps the existing top TM1 bar.
    w = 12.0
    top.shapes(l_tm1).insert(
        pya.Box(um(cx - w / 2), um(0.0), um(cx + w / 2), um(cy + via / 2)))

    # Via centred on north-track bridge — must sit fully on L134 metal
    top.shapes(l_via).insert(
        pya.Box(um(cx - via / 2), um(cy - via / 2),
                um(cx + via / 2), um(cy + via / 2)))

    # Port 3 rectangle at south, between P and N (same height as 201/202)
    top.shapes(l_p3).insert(
        pya.Box(um(cx - 6.0), um(0.0), um(cx + 6.0), um(4.0)))

    layout.write(OUT)
    print(f"Wrote {OUT}")
    print(f"CT via at ({cx}, {cy}) µm, size {via} µm; TM1 stub w={w} µm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
