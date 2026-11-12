# P2.7.2a tapped L2n0 EM after TopVia2 arrays [EM]

Source: same Palace runner as `review/em_summary.md`; GDS with 0.9 µm TopVia2
arrays (`make_tapped_gds.py`). Net/R pre-check PASS (`review/net_r_check.txt`,
`out/net_r_check_p272a.txt`). Extract: `out/summary.md` / `out/port-S.csv`
(2026-11-12).

## vs recorded tapped values (`review/em_summary.md`)

| f (GHz) | L new | L old | ΔL % | Q new | Q old | ΔQ % | \|Vct/Vdiff\| new | old |
|--------:|------:|------:|-----:|------:|------:|-----:|------------------:|----:|
| 3.100 | 1.6854 | 1.6851 | **+0.02** | 13.59 | 14.13 | **−3.82** | 0.0039 | 0.0036 |
| 3.500 | 1.6907 | 1.6904 | **+0.02** | 14.60 | 15.15 | **−3.63** | 0.0037 | 0.0035 |
| 4.200 | 1.7034 | 1.7030 | **+0.02** | 16.11 | 16.66 | **−3.30** | 0.0034 | 0.0032 |

## Pass criteria (P2.7.2a)

| Gate | Limit | Result |
|------|-------|--------|
| \|ΔL\| | < 1 % | **PASS** (≤ 0.02 %) |
| \|ΔQ\| | < 1 % | **FAIL** (3.3–3.8 %) |
| \|V_CT/V_diff\| | unchanged (same order) | **PASS** (~0.003–0.004) |

`out/summary.md` “GATES FAILED” uses the older ≤2 % vs **untapped** P2.0 baseline
(ΔQ ≈ −4.3 to −4.7 % there); the P2.7.2a gate is vs the **tapped** record above.

## Notes

- TV2.a DRC clean after arrays (`out/drc_ind_p272a.md`); density only.
- Q drop may be real (via array vs solid stub resistance) or mesh/run scatter;
  not re-meshed for a second seed. Owner: accept ~4 % Q hit, tighten via layout,
  or re-run EM once for scatter.
