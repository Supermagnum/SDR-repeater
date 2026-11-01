# Tapped L2n0 EM extract [EM]

Source: Palace 3-port, CT open → two-port mode; `tapped/extract_tapped.py` on `port-S.csv` (dB/deg, f in GHz). CT via at outer-turn bottom mid; net/R pre-check PASS (`review/net_r_check.txt`).

Baseline (untapped P2.0): L ≈ 1.69 nH; Q 14.2 / 15.3 / 16.9 at 3.12 / 3.5 / 4.2 GHz.

| f (GHz) | L (nH) | Q | ΔL % | ΔQ % | \|Vct/Vdiff\| | L/Q | Vct |
|---|---|---|---|---|---|---|---|
| 3.100 | 1.6851 | 14.13 | −0.29 | −0.51 | 0.0036 | PASS | PASS |
| 3.500 | 1.6904 | 15.15 | +0.02 | −0.96 | 0.0035 | PASS | PASS |
| 4.200 | 1.7030 | 16.66 | +0.77 | −1.40 | 0.0032 | PASS | PASS |

ALL GATES PASS (|ΔL|, |ΔQ| ≤ 2 %; \|Vct/Vdiff\| ≤ 0.05).
