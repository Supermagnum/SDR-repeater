# LO divider and phase-generation topology memo (P2.4)

Status: **topology accepted by the owner, 2026-10-20 (§4: D12 VCO capped at 4 mA, D13 and D14 as proposed). Step 1 done 2026-10-20 (§7): TSPC and the converter pass; the CML ÷2 / ÷3 need a clock of ≥ 0.5 V per side at the slow corner, which becomes the VCO-buffer requirement. Step 2 (buffer and both chains with the VCO) next.** Numbers are hand estimates `[HAND]` unless marked. Inputs: the simulated VCO (`spec/vco-topology.md` §9), D4 and D7 (`spec/phase2-plan.md` §5), `spec/rf-frontend.md` §3–5, `spec/derived-limits.md` §7.3–7.4.

---

## 1. Requirements

| Item | Value | Source |
|---|---|---|
| Input | VCO 2.90–4.41 GHz (band use 3.12–4.20), differential, about 1.0–1.3 V from the VCO buffer | P2.3 |
| UHF | ÷8: 400–480 MHz from 3.20–3.84 GHz; quadrature (I/Q) | `band_sel` = 0 |
| VHF | ÷24: 130–175 MHz from 3.12–4.20 GHz; **8 phases** (45°) for the harmonic-reject mixer | D4, `band_sel` = 1 |
| Harmonic rejection | VHF 3 × LO response ≥ 60 dB **including board preselection**; the mixer's own share is set in Phase 3 | `spec/rf-frontend.md` §3, `[DER]` §7.3 |
| Image | TX image ≥ 40 dB after host calibration; RX the same order | `spec/rf-frontend.md` §4 |
| Phase noise | The divider chain's own floor well below the divided VCO noise at the duplex offsets: VCO −119 dBc/Hz at 600 kHz ÷ 24 → −147 at the LO; **chain floor ≤ −150 dBc/Hz** at the LO output `[PROP]` | R4 (−136 / −139 dBc/Hz) |
| Speed margin | First stages at up to 4.41 GHz at slow corner, 1.08 V, 125 °C | Risk table, `spec/phase2-plan.md` §6 |
| Current | LO total ≤ 10 mA (D7) with the VCO at 3.4–5 mA (P2.3: the 4 mA cap was not chosen) | D7, P2.3 review |
| Users | RX mixer (passive, quadrature, HR on VHF) and TX IQ modulator, one at a time on this single-chain chip | `spec/rf-frontend.md` §7 |

A correction to an older text: `spec/derived-limits.md` §7.4 says "÷24 built as ÷12 then ÷2" (I/Q only). D4 replaced that with ÷3 then an 8-phase ÷8; the text there is updated with this memo.

## 2. Proposed topology

```
                          ┌─► UHF: CML ÷2 ─► CMOS ÷4 Johnson (2 DFF) ─► 4 phases ─► 25 % duty (AND) ─► I/Q drivers
VCO ─► CML buffer ─┤                (≤ 2.2 GHz)        (≤ 0.96 GHz)          (400–480 MHz)
     (P2.3 stand-in)│
                    ├─► VHF: CML ÷3 ─► CML→CMOS ─► CMOS ÷8 Johnson (4 DFF) ─► 8 phases (45°) ─► HR mixer drivers
                    │      (≤ 4.41 GHz)              (≤ 1.47 GHz)               (130–175 MHz)
                    └─► PLL feedback (multi-modulus divider, P2.5)
```

1. **Shared CML buffer after the VCO** (replaces the P2.3 stand-in): isolates the tank from the dividers and the band switch; its input capacitance is in the VCO budget. One output branch per user (UHF chain, VHF chain, PLL feedback), unused branches off.
2. **UHF: CML ÷2, then a CMOS ÷4 Johnson counter.** The ÷2 runs at up to 4.41 GHz (static CML latch pair, the textbook circuit). A Johnson (twisted-ring) counter of 2 D flip-flops divides by 4 and gives four outputs 90° apart, edge-timed by the same clock, so the quadrature does not depend on the input duty cycle. **25 % duty** pulses (AND of adjacent phases) are the usual LO for a passive quadrature mixer (lower noise and better I/Q isolation than 50 %).
3. **VHF: CML ÷3 at the VCO rate, then a CMOS ÷8 Johnson counter (D4).** A Johnson counter of 4 flip-flops divides by 8 and gives 8 outputs 45° apart, again timed by single clock edges, so the ÷3's output duty cycle does not matter (only its period, which is exact). This is why D4 needs no 50 %-duty ÷3. Whether the HR mixer wants 50 % or 12.5 % non-overlapping phases is a Phase 3 choice; both come from the same 8 outputs with simple logic.
4. **Retiming:** the last stage of each chain is clocked directly by the fast clock, so phase accuracy is set by flip-flop mismatch (a few ps), not by accumulated delays. At 175 MHz, 1° is 15.9 ps.
5. **Band switching:** `band_sel` powers one chain; the other is off (current and spurs). `FILT[4]` (8-phase enable) already exists in the register map.

**Alternatives considered:**
- ÷24 as ÷12 then ÷2 (the older text): gives I/Q only, no 8 phases for the HR mixer — excluded by D4.
- SiGe HBT (ECL) first stages: easy at 4.4 GHz and low current, but need ≥ 2.5 V and a level shift to CMOS; kept as the fallback if the CML ÷3 lacks speed margin at the slow corner.
- Injection-locked dividers: low power but narrow locking range; cannot cover 30 %.

## 3. Estimates `[HAND]`

| Item | Estimate | Comment |
|---|---|---|
| CML ÷2 at 4.41 GHz | 1.0–1.5 mA | Static CML in 130 nm toggles well above 10 GHz at typical; the slow corner is checked in step 1 |
| CML ÷3 at 4.41 GHz | 1.5–2.5 mA | The tightest stage: three latches plus logic in the loop. **Main speed risk** |
| CML buffer | about 1 mA | |
| CMOS Johnson ÷4 at ≤ 2.2 GHz / ÷8 at ≤ 1.47 GHz | 0.2–0.5 mA (C·V²·f) | True single-phase-clock flip-flops; margin at slow corner and 125 °C checked in step 1; CML if not enough |
| Phase accuracy | about 0.2–0.5° (1σ) from flip-flop mismatch | Monte Carlo in step 3. Untrimmed, about 1° phase and 1 % gain mismatch give roughly 40 dB HR3, so the 60 dB needs board preselection as well (Phase 3 split) |
| Chain noise floor | −155 to −160 dBc/Hz typical for CMOS dividers at the output | Checked with pnoise/noise in step 3 |
| Mixer drivers | 1–3 mA, depending on the mixer switch size (C·V²·f at 130–480 MHz) | Counted with the mixer in Phase 3, not here |

**LO current (D7 ≤ 10 mA), VHF worst case (before D12):** VCO 5 mA (bottom band) + buffer 1 + CML ÷3 2 + Johnson 0.5 + PLL (PFD, CP, MMD, Σ-Δ) about 1.5 mA = **about 10 mA, at the limit**; UHF about 8.5 mA. With the mixer drivers on top, the receive chain's 25 mA budget is affected. After D12 (VCO ≤ 4 mA): about 9 mA VHF, 8 mA UHF.

## 4. Decisions (2026-10-20)

| # | Decision | Proposal | Reason |
|---|---|---|---|
| **D12** | LO current budget | **Decided: cap the VCO at 4 mA**; the LO budget stays ≤ 10 mA (proposed was 11 mA or the cap) | The VHF chain plus a 5 mA VCO reaches the 10 mA of D7 before any margin; the 4 mA cap costs about 2 dB of phase noise at the band bottom (still 6 dB margin) |
| **D13** | UHF LO waveform | **4 phases, 25 % duty** | Standard for passive quadrature mixers; no extra divider stage |
| **D14** | Flip-flop style after the first stage | **CMOS (true single-phase clock)**, CML if step 1 shows less than 1.3× speed margin at slow corner / 1.08 V / 125 °C | Lowest current; the speed check decides |

Interface consequences: none for the register map (`band_sel`, `FILT[3:4]` exist). `spec/derived-limits.md` §7.4 is corrected to the D4 structure.

## 5. Step 1 — device checks before the schematic

Small VACASK transients, typical and slow corner (1.08 V, 125 °C):
1. **CML latch / ÷2:** maximum input frequency against tail current and load; pick the current for ≥ 1.3 × 4.41 GHz at the slow corner.
2. **CML ÷3:** the same at 4.41 GHz.
3. **TSPC flip-flop:** maximum toggle frequency against size at the slow corner, for the 1.47 GHz (VHF) and 2.2 GHz (UHF) clocks.
4. **CML→CMOS converter:** duty cycle and delay at 1.47 GHz.

## 6. After the review

| Step | Work | Gate |
|---|---|---|
| 1 | Device checks (§5) | Result review: confirms or changes §2 |
| 2 | Schematic of both chains with the VCO buffer; transient with the P2.3 VCO | — |
| 3 | Corners and temperature: maximum frequency, duty cycle, I/Q and 8-phase errors (Monte Carlo), noise floor, current | Result review against §1 |

## 7. Step 1 results (2026-10-20)

Source: `analog/lo/step1/` (VACASK, PDK `a49358cc`) `[SCH]`. Ideal clocks and supplies; tails ideal current sources.

| Block | Result | Consequence |
|---|---|---|
| TSPC flip-flop (D14) | Toggles up to 6–7 GHz typical, **4.0 GHz at slow corner** (1.08 V, 125 °C) for all three sizes: 2.7× margin for the VHF Johnson clock (1.47 GHz), 1.8× for UHF (2.2 GHz) | **CMOS TSPC confirmed** (≥ 1.3×); smallest size is enough |
| CML-to-CMOS converter | Duty 50–51 % typical, 45–46 % slow corner, full CMOS levels at 1.47 and 2.2 GHz | Adequate: the Johnson counters use one clock edge |
| CML ÷2 | 0.5 mA per latch, **1.0 mA**; with enough clock swing divides 2–8 GHz at slow corner, 2–12+ GHz typical | UHF first stage as proposed |
| CML ÷3 (two CML flip-flops + single-level NOR) | 0.5 mA per latch, **2.5 mA**; with enough clock swing divides 2–6.5 GHz at slow corner, 2–8 GHz typical | VHF first stage as proposed; 1.3× margin over 4.41 GHz at slow corner holds |
| **Clock swing** | With 0.27 V per side both fail below about 5 GHz at the slow corner (they free-run instead of following the input). Minimum swing for the whole window (÷2 2.9–5.0, ÷3 2.9–5.7 GHz): slow 0.35 V (÷2) / **0.40 V (÷3)**, typical and fast (1.32 V, −40 °C) 0.30 V; values at a 1.2 V scale (×0.9 at 1.08 V) | **Requirement for the VCO buffer: ≥ 0.5 V per side** (25 % over the ÷3 minimum) at a common mode about 0.55 V below V_DD |
| Variants rejected | A latch pair twice as wide adds nothing; a tail-less latch is starved at the slow corner (fails everywhere) | Keep the plain CML latch with a tail source |

**LO current with D12** `[HAND]`: VHF ≈ VCO 4 + buffer 1 + ÷3 2.5 + Johnson and converter 0.6 + PLL 1.5 = **9.6 mA**; UHF ≈ 4 + 1 + 1.0 + 0.6 + 1.5 = **8.1 mA** (D7: ≤ 10 mA). The VHF margin is small; the buffer is the item to watch.

**Buffer note for step 2:** the VCO tank swings about 0.41 V per side at the bottom band with the 4 mA cap, so a capacitor-coupled tap of the tank alone does not reach 0.5 V with margin. Step 2 designs the buffer for ≥ 0.5 V per side into the divider inputs at all corners.
