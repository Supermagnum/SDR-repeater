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

### Centre-tapped L2n0 (P2.7 pre-layout) [EM]

Palace 3-port, CT open → two-port mode; CT via at outer-turn bottom midpoint (`sim/em/sg13-octagon-l2n0/tapped/`, summary `tapped/review/em_summary.md`). Net extract: P, N, CT distinct; R(P–CT) ≈ R(N–CT) ≈ R(P–N)/2 within 2 %.

| f (GHz) | L (nH) | Q | vs untapped | \|V_CT / V_diff\| |
|---|---|---|---|---|
| 3.1 | 1.685 | 14.13 | within 2 % | ≤ 0.0036 |
| 3.5 | 1.690 | 15.15 | within 2 % | ≤ 0.0036 |
| 4.2 | 1.703 | 16.66 | within 2 % (ΔQ −1.4 %) | ≤ 0.0036 |

**[HAND]** Effect of the 1.4 % lower Q at 4.2 GHz on VCO phase noise: ≈ 0.1 dB (Leeson ∝ 1/Q²). At ss 85 °C, 4.20 GHz the bank-omitted margin was +3.6 dB at 1 MHz (`spec/vco-topology.md` §9); remaining margin ≈ **+3.5 dB**.

The file keeps its name so existing references stay valid. The Phase 1 digital back end does not use this Q.
