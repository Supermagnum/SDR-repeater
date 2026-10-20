# Tank Q (inductor SG13_Octagon_L2n0)

Decision of 2026-10-20, replacing the provisional values of 2026-10-17 (openEMS 1 µm: 11.8 at 2.4 GHz, 14.9 at 3.5 GHz). Source: [EM], `reports/phase2-review/p20-stage2.md` (P2.0 matched-mesh study).

Design values: Palace with filled metals and the via fill-factor correction, 1 µm mesh (converged), de-embedded. openEMS at 0.7 µm agrees within 1.6 % in Q.

| f (GHz) | L (nH) | Q | R (Ω) |
|---|---|---|---|
| 2.40 | 1.678 | 12.1 | 2.10 |
| 3.12 | 1.683 | 14.2 | 2.30 |
| 3.50 | 1.688 | 15.3 | 2.43 |
| 3.65 | 1.690 | 15.5 | 2.46 |
| 4.20 | 1.701 | 16.9 | 2.66 |

- These are conservative: both solvers' mesh trends and the upstream L6n2 measurement point to a slightly higher real Q (about 15.5–17 at 3.5 GHz).
- L carries a ±3 % uncertainty (openEMS reads a constant 3 % lower). VCO tuning (P2.3) must cover 3.12–4.20 GHz over L = 1.64–1.70 nH as well as over the PDK corners.
- They are simulated values. The real inductor is confirmed only by measurement after fabrication.

The file keeps its name so existing references stay valid. The Phase 1 digital back end does not use this Q.
