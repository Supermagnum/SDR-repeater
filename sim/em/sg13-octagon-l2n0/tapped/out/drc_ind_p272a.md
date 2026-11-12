# P2.7.2a inductor DRC after TopVia2 array fix [DRC]

GDS: `tapped/L_2n0_tapped.gds` (via arrays 0.9 µm / space 1.06 µm).
Run: PDK `run_drc.py --minimum_drc` → `tapped/out/drc_ind/` (2026-11-12).

| Rule | Count | Notes |
|------|------:|-------|
| TV2.a | **0** | Cleared vs prior solid-via aggregates |
| Density (AFil.g, GFil.g, M1–5.j, TM1.c, TM2.c) | 1 each | Waived at block level (fill Phase 5) |

**Pass for this cell (excl. density):** TV2.a clean.
