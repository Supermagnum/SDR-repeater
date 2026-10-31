# P2.6 result review — for owner acceptance

Date: 2026-10-30 (review); **accepted 2026-10-31** (`decisions.md`). Prerequisites: `reports/status-2026-10-30.md`.

Source table: `spec/pll-topology.md` §13 “P2.6 summary”.

## Results vs limits

| Check | Result | Limit | Tag |
|---|---|---|---|
| Loop (D19) | 60 kHz / 55°; C1 30.8 pF, C2 465 pF, R1 22.9 kΩ, R3 108 kΩ, C3 3.1 pF | corrected design | `[MODEL]` |
| Band cal (D20) | 8-bit, nearest code, 38.8 µs; V_tune 0.34–0.82 V all corners | window 0.25–0.95 V | `[MODEL]` |
| Wake | 83–120 µs | ≤ 150 µs | `[MODEL]` |
| Charge-pump noise | FoM −203.8 … −205.6 dBc/Hz; 1/f 79–141 kHz | P2.2 assumed −218 (accepted as-is) | `[SCH]` |
| LO floor VHF | −154.9 / −154.0 / −155.5 dBc/Hz (1–3 / 3–10 / 10–30 MHz) | ≤ −150 | `[SCH]` |
| LO floor UHF | ≈ −150 dBc/Hz | ≤ −150 | `[HAND]` (no convergence) |
| Total PN @ duplex | VHF worst −138.8 dBc/Hz (+2.8 dB); UHF −145.2 / −143.7 | ≤ −136 (25 W) | `[MODEL]` |
| Closed loop from power-on | locks; ≤ 7 ppm from 16 µs (5× filter scale) | locks | `[SCH]` |
| Reference spur | −109.3 dBc at RF (worst, 5 µA leakage) | ≤ −67 TX | `[MODEL]` |
| Fractional boundary spur | −123.0 VHF / −126.0 UHF (INL 3.9 ps) | ≤ −95 | `[MODEL]` |

All numeric limits that have a converging method are met. Tightest duplex margin is VHF 175 MHz (+2.8 dB).

## Four open points

1. **V_tune window monitor (D20).** Two comparators (~0.30 / 0.90 V) → `PLL_STATUS`[4:5]. Not designed.
2. **Start-up bypass on all VCO bias resistors** (bank plates, varactor bias, tail filter), closed ≥ 0.4 µs (≥ 6–7 τ) at wake; sequencer + VCO schematic (`spec/analog-digital-interface.md` §6). Found in step 3; required for the 150 µs wake on silicon.
3. **UHF LO-chain floor.** Still an estimate at the −150 limit. Transient noise does not converge on the UHF ÷2 / Johnson path. Upstream (IHP #1047 class) will not fix this; needs a different method (prompt 06 item 2(c)), not a pin or VACASK bump.
4. **Charge-pump in-band noise.** Improve only if an in-band requirement appears (optional).

## Owner decision (2026-10-31)

Accepted. Before P2.7: open point **2** then **1**. Open point **3**: one method attempt after those; does not block P2.7; must be closed or a known gap by the Phase 2 gate. Open point **4**: no action unless an in-band requirement appears. Open point 2 closed 2026-10-31 (`afe_seq`, VCO MOS bypass, sequencer timing in p26 step 3).
