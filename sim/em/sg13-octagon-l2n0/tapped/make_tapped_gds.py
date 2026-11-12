#!/usr/bin/env python3
"""Tapped L2n0 GDS: CT via on the outer-turn bottom segment.

Port arrangement: P (left) / N (right) at the south. The electrical midpoint
is on the outer turn's bottom flat at x=0 — NOT the north crossover (that
taps ~1/4 and ~3/4). CT y is set to the R-midpoint of the P–N path on that
flat (inner edge of the south track), so R(P–CT)≈R(N–CT)≈R(P–N)/2.

Keep the CT stub clear of the TM1 underpass at the north X and of the P/N leads.

P2.7.2a: vendor feed vias were 10.75 µm squares (TV2.a FAIL — TopVia2 must be
exactly 0.9 µm [DS]). Replace with PDK-legal 0.9 µm via arrays, pitch ≥ 1.06 µm
(TV2.b) [DS].
"""
import os
import sys

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "vendor", "gds2openEMS", "workflow", "L_2n0_twoport.gds")
OUT = os.path.join(HERE, "L_2n0_tapped.gds")

# IHP SG13G2 TopVia2: min=max width 0.9 µm; min space 1.06 µm [DS]
VIA = 0.9
VIA_SPACE = 1.06
VIA_PITCH = VIA + VIA_SPACE  # 1.96 µm


def um(layout, u):
    return int(round(u / layout.dbu))


def via_array(layout, cell, layer, x0, y0, x1, y1):
    """Fill bbox with 0.9 µm vias on a legal pitch; centre the grid in the box."""
    w = x1 - x0
    h = y1 - y0
    nx = max(1, int((w - VIA) / VIA_PITCH) + 1)
    ny = max(1, int((h - VIA) / VIA_PITCH) + 1)
    span_x = (nx - 1) * VIA_PITCH + VIA
    span_y = (ny - 1) * VIA_PITCH + VIA
    ox = x0 + (w - span_x) / 2
    oy = y0 + (h - span_y) / 2
    n = 0
    for ix in range(nx):
        for iy in range(ny):
            cx = ox + ix * VIA_PITCH + VIA / 2
            cy = oy + iy * VIA_PITCH + VIA / 2
            cell.shapes(layer).insert(
                pya.Box(um(layout, cx - VIA / 2), um(layout, cy - VIA / 2),
                        um(layout, cx + VIA / 2), um(layout, cy + VIA / 2)))
            n += 1
    return n, nx, ny


def main():
    layout = pya.Layout()
    layout.read(SRC)
    dbu = layout.dbu
    top = layout.cell(next(layout.each_top_cell()))
    top.name = "L_2n0_tapped"

    l_tm1 = layout.layer(126, 0)
    l_via = layout.layer(133, 0)
    l_p3 = layout.layer(203, 0)

    # Collect illegal large vias from vendor GDS, then clear all TopVia2
    old = []
    for s in top.shapes(l_via).each():
        b = s.bbox().to_dtype(dbu)
        old.append((b.left, b.bottom, b.right, b.top, b.width(), b.height()))
    top.shapes(l_via).clear()

    n_rep = 0
    for x0, y0, x1, y1, w, h in old:
        if abs(w - VIA) < 0.02 and abs(h - VIA) < 0.02:
            # already legal — restore
            top.shapes(l_via).insert(
                pya.Box(um(layout, x0), um(layout, y0),
                        um(layout, x1), um(layout, y1)))
            n_rep += 1
        else:
            n, nx, ny = via_array(layout, top, l_via, x0, y0, x1, y1)
            print(f"replaced {w:.3f}×{h:.3f} via at "
                  f"({(x0+x1)/2:.2f},{(y0+y1)/2:.2f}) with {nx}×{ny}={n} "
                  f"× {VIA} µm [DS TV2.a/b]")
            n_rep += n

    # Outer-turn bottom flat CT: 0.9 µm TopVia2 (legal)
    cx = 0.0
    y_top = 41.75
    cy = y_top - VIA / 2  # 41.30
    stub_w = 8.0
    y_port = 0.0

    top.shapes(l_tm1).insert(
        pya.Box(um(layout, cx - stub_w / 2), um(layout, y_port),
                um(layout, cx + stub_w / 2), um(layout, y_top)))

    top.shapes(l_via).insert(
        pya.Box(um(layout, cx - VIA / 2), um(layout, cy - VIA / 2),
                um(layout, cx + VIA / 2), um(layout, cy + VIA / 2)))
    print(f"CT via at ({cx}, {cy}) µm, size {VIA} µm")

    top.shapes(l_p3).insert(
        pya.Box(um(layout, cx - 6.0), um(layout, 0.0),
                um(layout, cx + 6.0), um(layout, 4.0)))

    layout.write(OUT)
    print(f"Wrote {OUT}; TopVia2 shapes now legal arrays + CT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
