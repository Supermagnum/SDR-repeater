#!/usr/bin/env python3
"""Tapped L2n0 GDS: CT via on the outer-turn bottom segment.

Port arrangement: P (left) / N (right) at the south. The electrical midpoint
is on the outer turn's bottom flat at x=0 — NOT the north crossover (that
taps ~1/4 and ~3/4). CT y is set to the R-midpoint of the P–N path on that
flat (inner edge of the south track), so R(P–CT)≈R(N–CT)≈R(P–N)/2.

Keep the CT stub clear of the TM1 underpass at the north X and of the P/N leads.
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

    l_tm1 = layout.layer(126, 0)
    l_via = layout.layer(133, 0)
    l_p3 = layout.layer(203, 0)

    # Outer-turn bottom flat at x=0: L134 y ≈ 30.0 .. 41.75 µm.
    # P–N shortest-path midpoint is at the inner edge (y≈41.75). Place a
    # 0.9 µm TopVia2 with its top on that edge so the via stays on metal.
    cx = 0.0
    via = 0.9
    y_top = 41.75
    cy = y_top - via / 2  # 41.30
    stub_w = 8.0  # clear of P/N leads (|x| edge ≈ 22 µm)
    y_port = 0.0
    y_stub_top = y_top

    top.shapes(l_tm1).insert(
        pya.Box(um(cx - stub_w / 2), um(y_port),
                um(cx + stub_w / 2), um(y_stub_top)))

    top.shapes(l_via).insert(
        pya.Box(um(cx - via / 2), um(cy - via / 2),
                um(cx + via / 2), um(cy + via / 2)))

    top.shapes(l_p3).insert(
        pya.Box(um(cx - 6.0), um(0.0), um(cx + 6.0), um(4.0)))

    layout.write(OUT)
    print(f"Wrote {OUT}")
    print(f"CT via at ({cx}, {cy}) µm, size {via} µm; "
          f"TM1 stub w={stub_w} µm from y={y_port} to {y_stub_top:.2f}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
