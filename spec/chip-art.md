# Chip art cell (standalone)

Status: **built 2026-11-17** — TopMetal2 cell only; **not placed** on the die until Phase 5
(`decisions.md` 2026-11-16 — Chip art). Area feeds the P2.7.2c die re-total.

## Source

| Item | Value | Tag |
|---|---|---|
| Graphic | `graphic/graphic.svg` (text “HEIMDALL X1”) | [SVG] |
| Outlines | `graphic/graphic_outlines.svg` (Inkscape CLI text→paths; original unchanged) | [TOOL] |
| Build | `analog/chipart/build_art.py` → raster (`rsvg-convert`) → GDS polygons | [TOOL] |
| Cell / GDS | `chip_art` / `analog/chipart/out/chip_art.gds.gz` | [GDS] |
| Summary | `analog/chipart/out/summary_chip_art.txt` | [TOOL] |
| Renders | `out/chip_art.png`, `out/chip_art_side_by_side.html` (SVG vs raster vs GDS) | [TOOL] |

## Layer and rules [PDK / DS]

| Rule | Value | Source |
|---|---|---|
| Drawing layer | **TopMetal2** 134/0 | [DS] SG13G2_os_layout_rules; logos/art on top metal |
| TM2.a min width | **2.00 µm** | [DS] |
| TM2.b min space | **2.00 µm** | [DS] |
| TM2.c–d density | **25–70 %** | [DS] |

No PDK note was found advising a different layer for logos; TopMetal2 is used.

## Scale and size [TOOL / GDS]

| Item | Value | Tag |
|---|---|---|
| Thinnest stroke (after open2) | 4.47 raster-px = 2.24 SVG-units | [TOOL] |
| Narrowest gap | 2.00 raster-px = 1.00 SVG-unit | [TOOL] |
| Scale (primary) | **1.150 µm / raster-px** = **2.300 µm / SVG-unit** (×1.15 margin) | [HAND] |
| Morph | close/open 2.30 µm + close 3.00 µm (pixel-stair / notch cleanup) | [TOOL] |
| Cell bbox | **884.35 × 984.40 µm** | [GDS] |
| Cell area | **0.8706 mm²** | [GDS] |
| Art TM2 density | **30.7 %** (in band; no density fill) | [GDS] |
| Option smaller | Drop face, re-pack text+circle ~400×80 SVG-units → ~0.169 mm² | [HAND] |
| Option larger | 2.30 µm/raster-px (1 px ≥ TM2.a×margin, less morph dependence) → ~3.48 mm² | [HAND] |

## Pin-1 dot

The source SVG draws a filled circle at the **top-left** of the art; that circle is the
pin-1 marker in the TopMetal2 cell (die pin-1 corner when placed in Phase 5)
[`decisions.md` / SVG]. A second synthetic marker is not added (it fought the circle on
TM2.a/b) [TOOL].

## Phase 5 placement (from `decisions.md`)

- Do **not** place over the inductor EM keep-out.
- Do **not** place over VCO / LO / RF routing.
- Standalone cell only until Phase 5; area is carried in `spec/p27-floorplan.md` §8.

## DRC [TOOL]

- TM2.a / TM2.b / TM2 density: **PASS** (density included for TopMetal2).
- Empty-layer fill / density (AFil.*, M*Fil.h, M*.j, TM1.c, …): waived for this TM2-only
  cell (same class as block-level density waive). Full-chip fill is Phase 5.
