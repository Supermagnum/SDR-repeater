# Tapped L2n0 — DRC + via review (pre-EM)

Date: 2026-11-01

## Via placement

- CT via on layer 133 at **(0, 270.25) µm**, size **8.0 µm** (north-track bridge; 10.8 µm would overhang the ~17 µm-wide crossover neck).
- L134 coverage of the via box: **100 %** (checked with KLayout `Region` intersection before DRC).
- TM1 stub (layer 126, 12 µm wide) from the via south to port row y=0.
- Port marker layer **203** between P (201) and N (202).

## Renders (for owner review)

- `L_2n0_tapped_review.png` — full cell
- `L_2n0_tapped_via_zoom.png` — north crossover + CT via
- `L_2n0_tapped_full.png` — same as review

## DRC

IHP SG13G2 `--minimum_drc --no_density` via `run_drc.py` on `tapped/L_2n0_tapped.gds`, topcell `L_2n0_tapped`, results under `tapped/out/drc/`.

Density rules skipped (EM GDS is not a full chip; density waived for this pre-EM check).

### Result

| Rule | Count | Notes |
|---|---|---|
| **TV2.a** (TopVia2 width = 0.9 µm min/max) | **10** | All five via aggregates (4 pre-existing P/N crossover vias ≈10.8 µm + new CT via 8.0 µm). EM GDS draws via *arrays* as solid rectangles; foundry rule wants 0.9 µm singles. **Same class as the two-port baseline** — not a new CT-only failure. |
| Other minimum-DRC tables | 0 | No TM1/TM2 width/space, enclosure, or filler hits on the CT stub. |

CT via is fully enclosed by L134 (100 % coverage check) and by the TM1 stub. Safe to proceed to EM after owner PNG review.
