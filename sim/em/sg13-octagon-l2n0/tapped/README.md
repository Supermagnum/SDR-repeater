# Tapped SG13_Octagon_L2n0 EM (P2.7 open item)

Status: **CT GDS revised 2026-11-01** (bottom outer-turn mid). Pre-EM net/R checks PASS. EM next.

The P2.0 two-port GDS has no centre tap. The VCO lumped model assumes a symmetric electrical midpoint — confirmed here by layout R match before EM.

## GDS

```bash
python3 tapped/make_tapped_gds.py
python3 tapped/check_tapped_nets.py   # must PASS before EM
```

- **CT via** on the outer-turn bottom flat (electrical mid for P/N at south) — not the north crossover.
- Short TM1 stub to port layer **203**; clear of underpass and P/N leads.
- Review: `tapped/review/L_2n0_tapped_review.png`, `L_2n0_tapped_via_zoom.png`, `net_r_check.txt`.

## EM gates

1. Two-port mode (P–N) L and Q within **2 %** of the untapped P2.0 baseline at 3.12 / 3.5 / 4.2 GHz.
2. Under differential drive, **V(CT) ≈ 0** (common-mode node).

```bash
# inside iic-osic-tools, from sim/em/sg13-octagon-l2n0
EM_NPROC=8 ./tapped/run_tapped_em.sh
```

Deliverable: `tapped/out/summary.md`.
