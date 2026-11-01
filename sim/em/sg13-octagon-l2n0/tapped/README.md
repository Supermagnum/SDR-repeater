# Tapped SG13_Octagon_L2n0 EM (P2.7 open item)

Status: **started 2026-11-01.** The P2.0 two-port GDS (`L_2n0_twoport.gds`) has **no centre tap**. The VCO lumped model (`analog/vco/models/l2n0_lumped.inc`) assumes a symmetric electrical midpoint — that assumption needs a 3-port EM check before layout sign-off (`spec/vco-topology.md` open point; `analog/vco/step1/README.md`).

## Goal

1. Produce a **tapped** inductor GDS: ports P, N (same as today) plus **CT** at the winding midpoint.
2. Run Palace (filled-metal, ~1 µm) and/or openEMS at the VCO frequencies (2.4–4.2 GHz).
3. Extract differential L, Q and the CT imbalance (Z_P-CT vs Z_N-CT).
4. Refit `l2n0_lumped.inc` if the tap asymmetry or L/Q move by more than ~2 %.

## Baseline GDS facts (L_2n0_twoport)

| Layer | Role (from shapes) |
|---|---|
| 134/0 | Inductor body / fill |
| 126/0 | TopMetal1 leads to ports |
| 133/0 | Vias |
| 201, 202 | Port rectangles (P, N) at y≈0 |
| 210 | Substrate ground |

Bbox ≈ (−127, −15)–(127, 284) µm. Port pitch ±28 µm at the south side.

## Tap approach (proposal)

- Keep P/N ports and ground polygon unchanged so results compare to P2.0.
- Add a **Metal1 (or TM1) stub** from the geometric centre of the octagon body (~(0, 157) µm) south to a new port **203** on the ground side, with vias up into the TopMetal winding at the **innermost turn midpoint** (exact attachment point to be fixed after inspecting the spiral path — do not attach to fill).
- Port 3: same z-directed style as ports 1/2 (`from SUBGND to TopMetal1`, layer 203).

`make_tapped_gds.py` places the CT via on the **north-track crossover** at (0, 270.25) µm (8 µm via, 100 % on L134). Renders: `tapped/out/L_2n0_tapped_review.png`, `L_2n0_tapped_via_zoom.png`. Minimum DRC: only TV2.a on EM via aggregates (same waiver as the two-port baseline) — `tapped/out/drc_summary.md`.

## Run (after GDS review)

```bash
# inside iic-osic-tools, from sim/em/sg13-octagon-l2n0
python3 tapped/make_tapped_gds.py
# then Palace 3-port (script TBD, clone p20/p20_palace.py + port 3)
```

## Deliverable

`tapped/out/summary.md`: L_diff, Q at 3.12 / 3.5 / 4.2 GHz; CT imbalance; pass if |L_diff − L_2port| / L < 2 % and |Z_P-CT − Z_N-CT| / Z < 5 % across the band.
