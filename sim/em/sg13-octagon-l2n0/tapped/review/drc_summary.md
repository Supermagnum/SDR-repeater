# Tapped L2n0 — CT on outer-turn bottom (pre-EM)

Date: 2026-11-01 (revised)

## Placement

- Previous north-crossover via tapped ~1/4 and ~3/4 of the winding and the long TM1 stub overlapped the underpass (shorting the X). Removed.
- **CT via** on the outer-turn bottom flat at **(0, 41.30) µm**, size **0.9 µm** (top edge on the P–N path midpoint at y=41.75). L134 coverage **100 %**.
- **Short TM1 stub** (8 µm wide) from the via south to port 203 only — clear of P/N leads and of the north underpass.

## Pre-EM checks (`check_tapped_nets.py`)

See `net_r_check.txt`.

| Check | Result |
|---|---|
| TM1 nets P / N / CT distinct | PASS |
| CT stub ∩ north underpass | NONE |
| CT via on L134 | 100 % |
| R(P–CT) ≈ R(N–CT) ≈ R(P–N)/2 within 2 % | PASS (arms 1.34 %, vs half 0.67 %) |

## Renders

- `L_2n0_tapped_review.png` — full cell
- `L_2n0_tapped_via_zoom.png` — south CT via + stub
