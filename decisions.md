# Decisions

Human decisions for the SG13G2 VHF/UHF RFIC. An entry is added only after a person approves it.

## 2026-10-17 — Phase 0 review

Approved:

- Container `hpretl/iic-osic-tools:2026.10`.
- PDK commit `a49358cc0b20635fcb53c0940505e3563763fc7a`, the commit named in that image. It contains the RF MOSFET LVS change (pull request 1246, merge `f7bca326`) and is 26 hours before `dev` `89d42ee`. `89d42ee` is not pinned. The two commits have diverged: 43 commits are only on `dev`, and 48 commits are only in the image, mostly the `sg13g2_stdcell_hv` library.
- KLayout DRC flag `--minimum_drc`.
- EM workflows `gds2palace` `v0.8.2` (`ed063dc9`) and `gds2openEMS` `v0.5.0` (`99d8bd18`). Stack-up XML is taken from the pinned PDK commit.
- CACE `fossi-foundation/cace` 2.13.0.
- cocotb 2.1.0 from the image. No project venv.
- Rejections: `efabless/cace`, `AliSahafi/Analog_OpenSource_ihp`, QUCS-COPEN.
- ngspice 47 experimental PSS is allowed. Phase-noise results stay lower confidence.
- Supply assumption replaced by regulated host rails, with buck ripple and spur tolerance required. See `spec/baseline-decisions.md`.
- PLL references 32 MHz and 36 MHz. Spur map: `spec/integer-boundary-spurs.md`.
- I2S slot width 16 or 32 bits, MSB-justified, 16-bit baseline.
- LinHT facts stay provisional. USB-A part numbers wait.

Recorded after those approvals, not a new topology decision: `SG13_Octagon_L2n0` L and Q at 2.4 GHz and 3.5 GHz are in `reports/phase0-review/em-l2n0.md`. That file is a regression baseline. It is not a pass or fail against a specification.

Not approved at that point: any analog topology, and any push.

## 2026-10-17 — Phase 0 EM review

Approved:

- Stay on PDK `a49358cc`. Do not follow `dev`. Reconsider the PDK pin only at a phase review gate.
- The image commit does contain the RF MOSFET LVS change. `rfmos_extraction.lvs` extracts `rfnmos`. `rfmos_model_mapping.lvs` is not in the image.
- Both EM solvers use the pinned-PDK openEMS stack-up `SG13G2_200um.xml`, sha256 `5d452943`. The Palace workflow XML in the same commit is a different stack and is not used. Hashes are in `reports/phase0-review/em-l2n0.md`.
- Matched mesh, shared port de-embedding, and a comparison to a compact model or IHP measured data are required before Phase 2. They are not a Phase 1 blocker. No compact model and no `L2n0` measured file were found in this PDK commit.
- Provisional tank Q is the openEMS value: 11.8 at 2.4 GHz and 14.9 at 3.5 GHz. See `spec/provisional-tank-q.md`.
- Phase 1 digital back end may start. Analog topology is still not approved.

## 2026-10-17 — Phase 1 review, not approved

The first Phase 1 submission was not approved. The resubmission is on `phase1/digital` and is waiting for review. It is not an approval and it is not a topology decision.

Recorded in `reports/phase1-review/summary.md`:

- SPI frame approved. Register map frozen at this gate, addresses `0x00` through `0x13`.
- I2S master by default, and the b14/b15 direction change, approved as a proposal. 16-bit slots at 500 kHz are the repeater recommendation. The 36 MHz three-clock BCLK cells miss the i.MX93 S12 pulse-width window. The K3 datasheet publishes no slave pulse-width limit.
- Proposed signoff junction temperature is 100 °C. The PDK liberty has no 85 °C or 100 °C corner. The 125 °C slow corner is reported from the post-CTS database.
- The 45 dB alias limit stays provisional pending Phase 3 modulator co-design.
- LinHT IQ stays provisional.
- Placed area is above the 0.25 mm² target. See the review for the measured core and cell area.
- The matched-mesh inductor study may run in parallel. It has not been started. Phase 2 has not been started and still needs approval.


## 2026-10-18 — Hold clock uncertainty
Setup uncertainty stays at CLOCK_UNCERTAINTY_CONSTRAINT (0.25 ns). Hold uncertainty is 0.05 ns
(`set_clock_uncertainty -hold 0.05`), because clocks are propagated after CTS and the
TCXO/VCTCXO reference jitter is in the picosecond range. The previous 0.25 ns on hold, plus
the 0.1 ns resizer margin and 5 % derate, drove 6,449 hold buffers.

## 2026-10-18 — SPI mode 0 and power-up reset
MISO changes on the SCLK falling edge; the host samples on the rising edge (mode 0).
Previously MISO changed on the rising edge, which would have shifted every read by one
bit on a real host. Board requirement: rst_n must be held low at power-up until the
supplies and the reference clock are stable (asynchronous reset, level-sensitive).

## 2026-10-18 — CACE version and maximum IQ rate
CACE: use 2.11.0, the version in hpretl/iic-osic-tools:2026.10 (manifest updated).
Maximum RFIC IQ sample rate: 500 kHz (25/50/100/200/500 kHz). README updated from 1 MHz /
32 MHz BCLK to 500 kHz / about 16 MHz BCLK. Matches the LinHT 500 kHz target, keeps BCLK
within the i.MX93 SAI slave limits, and keeps the Sigma-Delta oversampling ratio at 64/72.

## 2026-10-18 — I2S format: Philips (standard I2S)
Master and slave use Philips I2S: LRCLK low = left (I), high = right (Q), changing one bit
before each MSB; data and LRCLK change on the BCLK falling edge, sampled on the rising edge.
Previously data changed on the rising edge (the host's sampling edge) in both modes.
Reset: clk domain released through a 2-flop synchroniser; SCLK must stay idle >= 1 us after rst_n rises.
Test note: logic on gated clocks updates after clk's rising edge in RTL simulation, so
testbenches drive inputs on clk's falling edge.

## 2026-10-18 — Continuous I2S BCLK
BCLK runs without gaps at every rate: frame = 2 * slot * bit_cell reference clocks.
36 MHz / 500 kHz enabled (BCLK 18 MHz: over the 16 MHz repeater-backplane cap, which applies
to the 32 MHz repeater modules, but within the i.MX93 SAI slave limits for LinHT).
36 MHz / 200 kHz: no 50 % split exists (180 = 2*18*5); 40/60 duty, exactly on the i.MX93 limit.
Accepted and documented; LinHT should prefer 100 kHz or 500 kHz.

## 2026-10-18 — Frequency coverage 130–175 MHz + 400–480 MHz; duplexer confirmed

- **Decision:** the RFIC tunes 130–175 MHz and 400–480 MHz, covering amateur bands, land mobile and PMR446. This replaces the amateur-only baseline (README 11.1).
- **Owner input:** repeater sites share one antenna between RX and TX through a duplexer on 2 m and on 70 cm.
- **Norwegian offsets:** 600 kHz (2 m) and 2 MHz (70 cm), taken from the repeater list.
- **Limits:** derived in `spec/derived-limits.md` and replace the provisional ones.
- **Consequences, Phase 3 analog:**
  - harmonic-reject VHF mixer and/or preselector;
  - LO plan with a VCO at 3.12–4.20 GHz, ÷8 for UHF and ÷24 for VHF (as `band_sel` in the RTL);
  - analog anti-alias of ≥ 40 dB at ±8/9 MHz and ≥ 70 dB at ±32/36 MHz;
  - selectable TX reconstruction filter.
- **Consequences, system:**
  - the host picks the 32 or 36 MHz clock per channel by the harmonic table;
  - 500 kHz TX is for simplex use only.
- **Digital backend:** unchanged.

## 2026-10-18 — Area: calibration moved to the host, target ≤ 0.34 mm²

- **Metric.** Real cell area = `design__instance__area__stdcell` + `design__instance__area__macros` (no filler). Phase1i: 0.434 mm². The earlier 0.708 mm² figure included 0.274 mm² of filler cells. Checked by `tools/check_area.py` (limit 340 000 µm²).
- **Decision (a).** DC and IQ correction for RX and TX are done by the host software. The digital chain is linear, so host-side correction is equivalent. Removed: `iq_cal`, `dc_offset`, the TX calibration stage, and registers 0x04–0x07 and 0x0D–0x12 (now reserved, read 0). `BLOCK_PD[2:1]` and `CLK_GATE[2]` are reserved. `CHIP_ID` 0x11 → 0x12. All other addresses keep their numbers.
- **Other reductions.** `sample_fifo` depth 8 → 4. TX integrators and the shared `cic4` adders 40 → 28 bits (maximum value 32767 × 720 < 2²⁵). One RAM address generator in `fir_seq` (bit-identical: 0 mismatches over 120 000 random cycles against the old module). `relock_cnt` sized from `RELOCK_CYCLES`.
- **Not done.** 0.30 mm² is not reachable without removing functions. CIC1 narrowing (bypass path uses 16-bit input) and reserved-bit trimming were judged not worth the risk.
- **Tests.** `phase_cross_term` and `dc_retained_across_sleep` removed with the blocks they tested. `filter_response_limits` now also checks the duplex-offset (≥ 100 dB) and on-channel (≥ 65 dB) alias limits; `tx_image_and_noise` checks the bitstream noise at 600 kHz and 2 MHz against `spec/derived-limits.md`.

## 2026-10-19 — Timing-driven placement and post-route setup repair

- Phase1j missed setup by 0.050 ns (slow corner, 4 endpoints: SRAM `A_DOUT` → half-band MAC). The same path had +0.80 ns in phase1i; the difference is placement and routing, not the RTL. Everything else in phase1j passed (LVS, DRC, antenna, max-cap 0; gate-level 5/5; Magic 7 818, all inside the SRAM).
- Setup was never repaired with real routing loads (`RUN_POST_GRT_RESIZER_TIMING` false, `PL_TIMING_DRIVEN` false). Both are now on, with a 0.1 ns setup margin and a 0.1 ns post-route hold margin (keeps the 0.08 ns hold guard).

## 2026-10-19 — RF front end: SX1255-compatible drop-in, repeater RX default, phase-noise tool

- **Option P:** the RFIC is pin-compatible with the SX1255 (MLPQ-W 5 × 5 mm, 32 leads), so the LinHT can take it without a respin for UHF. The SPI frame is already identical (mode 0, write bit + 7-bit address + data). IQ uses the SX1255 "mode B2" I2S pins. Not register-compatible: the host driver changes.
- **LinHT Rev C facts (schematic, 2026-07-14):** 32 MHz TCXO; the 2× PE4312 attenuators are in the RX path, TX power is set inside the transceiver; the SX1255 TX output is used single-ended. IQ is 500 kSa/s, 16-bit I/Q as left/right audio (M17 project).
- **Reset:** the SX1255 RESET pin is active-high and floats in normal operation. The RFIC needs an internal pull-down and an on-chip power-on reset.
- **Repeater RX front end:** the 2× PE4312 attenuators are the default (system NF ≈ 8 dB); an external LNA is a module-designer option (≈ 5 dB). Limits re-derived in `spec/derived-limits.md` §8.
- **TX output:** −5 dBm nominal into the existing GRF5604 match; ≥ 30 dB analogue gain control after the reconstruction filter (digital scaling would break the duplex-noise budget).
- **Phase noise:** VACASK `pnoise` validated (`analog/pn-validation/`); use `pss_minpts` ≥ 8000 for close-in offsets.
- Requirements: `spec/rf-frontend.md` (draft for human review).

## 2026-10-19 — Interface pins, duplex module, five slots, VHF filter, 100 W parts
- **`ref_36`:** strap on SX1255 pin 11 (CLK_IN), sampled while RESET is active, internal pull-down: open = 32 MHz (LinHT unchanged), high = 36 MHz. Readable in a status bit. Changing it needs a reset, consistent with the static false path.
- **Backplane c2 (PTT) → RFIC DIO3:** hardware PTT gate with pull-down, ignored unless `ptt_pin_en` is set (default: SPI-only TX, as the SX1255 and the LinHT). **Backplane c1 (IRQ) ← RFIC DIO1:** active-low IRQ, enabled by register; open-drain buffer on the module. RTL change together with the other Option P pin-map changes (Phase 5).
- **LinHT I2S format confirmed** (read-only, `meta-linht-hardware` `sbc-mcm-imx93.dtsi`): `format = "i2s"`, SX1255 is bit-clock and frame master on both links. Matches the chip default.
- **Same-band repeater = one duplex module in one slot:** two RFICs, shared reference; RX RFIC is I2S master, TX RFIC is slave on the same port; TX RFIC chip select on b5 (SWR ADC then I²C); two front-panel ports to the cavity duplexer; no T/R switch. EEPROM types 0x0005 (2 m duplex), 0x0006 (70 cm duplex).
- **Five slots, A–E** (README is canonical): `iq_E` / `tx_E` and `module_id` 4 added in `zeromq-messages.md`, `ht-module-daemon.md` and `RF-modules.md`.
- **VHF harmonic filter covers 130–175 MHz (owner decision):** 7th-order elliptic-type ladder with traps at about 263 / 309 / 511 MHz, ≥ 70 dB from 256 MHz; values and part stress in `docs/rf-switches-and-filters.md`; check with `tools/vhf_lpf_check.py`.
- **100 W parts:** MACOM MSW2040-204 (symmetrical) for band switching, MSW2050-205 (asymmetrical) for T/R; 125 V reverse bias needed at VHF; orderable, quote needed. ATC 100B: 3 W dissipation limit; two in parallel (or 100C/100E) at the 100 W shunt positions until the ESR chart is read.

## 2026-10-19 — Pin-map RTL (block level)
- `ref_36` is latched while the reset synchroniser is in reset (pin-11 strap); `INFO[0]` reads it back.
- `CTRL[3]` (was reserved) enables the hardware PTT gate: in TX mode the core holds standby unless `ptt_pin` (DIO3) is high. Default off.
- `IRQ_EN` (0x14) masks FIFO overflow, FIFO underflow, clk_error and PLL-not-locked onto `irq_n` (DIO1), a registered active-low level. New input `pll_lock` from the analogue PLL.
- `INFO` (0x15, read only): latched `ref_36`, synchronised `ptt_pin` and `pll_lock`.
- CHIP_ID 0x12 → 0x13. New ports: `ptt_pin`, `pll_lock` (in), `irq_n` (out); SDC false paths added for them.
- Chip-top items unchanged in this block: active-high RESET with pull-down and power-on reset, I2S word select on DIO2, `clk_req` on DIO0.
- Tests: RTL suite 14/14 on Icarus (new `pinmap_ref36_ptt_irq`, also in the gate-level list); `master_frame_lengths` now resets after changing `ref_36`. `verilator -Wall` clean. Needs a new layout run (`phase1l`).

## 2026-10-19 — PLL spur limits; 100B capacitors at 100 W
- Spur limits in `spec/derived-limits.md` §9: duplex offset ≤ −95 dBc (25 W) / −88 dBc (5 W) for RX LO and TX; TX elsewhere −67 dBc design target (regulatory −57 dBc); RX elsewhere −84 dBc and adjacent channels −65 dBc as proposals to confirm against the applicable standard.
- Integer-boundary spurs on the duplex offset (**corrected the same day**: the first count divided the spur offset by N; division keeps the offset and only lowers the level). With both references: 2 of 161 2 m channels (144.0125, 144.025 MHz) and 5 of 801 70 cm channels (431.750, 431.875, 432.125, 432.250, 436.250 MHz). Whether the PLL meets the limit there is decided by the Phase 2 model (`spec/phase2-plan.md` P2.2).
- ATC 100B ESR read from the datasheet chart: two 100B in parallel at C3 and C5 of the VHF filter at 100 W; single parts elsewhere and at 5–20 W.

## 2026-10-19 — phase1l signed off; Phase 2 plan drafted
- `phase1l` (pin-map RTL): sign-off pass — setup +3.99 ns, hold +0.089 ns (guard 0.08), LVS match, antenna 0, KLayout DRC 0, Magic DRC 7 815 (unchanged, inside the SRAM, waived), real area 339 617 µm² of 340 000. Gate level 6/6. The digital back end has no area left.
- `spec/phase2-plan.md`: LO budgets (VCO ≤ −116 / −115 dBc/Hz at 1 MHz), loop proposal (100–150 kHz, MASH 1-1-1, fPFD = reference), steps P2.0–P2.7, decisions D1–D7 for the owner.

## 2026-10-19 — Phase 2 owner decisions D1–D7; P2.2 model
Accepted as proposed in `spec/phase2-plan.md` §5:
- D1 VCO core: NMOS cross-coupled (the validated case), SiGe HBT version as comparison.
- D2 one wide-range VCO with a 5–6-bit capacitor bank.
- D3 the Σ-Δ modulator goes in a separate small digital PLL block; the back end stays at 0.34 mm².
- D4 VHF LO: 8 phases (÷3, then 8-phase ÷8) for the harmonic-reject mixer.
- D5 loop bandwidth 100–150 kHz.
- D6 the integer-boundary channels must meet the spur limit in the PLL; host avoidance only if the model shows it cannot.
- D7 LO current ≤ 10 mA of the 25 mA RX budget.

P2.2 linear model (`analog/pll-model/`, all inputs `[PROP]`): passes at 150 kHz (lock 125 µs; 100 kHz needs 187 µs, so 150 kHz is chosen within D5). Duplex-offset phase noise −137.2 dBc/Hz (VHF) and −139.4 (UHF); the VCO term dominates and L(1 MHz) must stay ≤ −115 dBc/Hz. Boundary spurs on the hit channels pass if the raw spur is ≤ −35 dBc (VHF) / −20 dBc (UHF), so D6 holds on this model. Loop filter ≈ 400 pF.
- `phase1l`: IHP full KLayout DRC (maximum rule set, antenna, no density) 0 violations (2026-10-19). Phase 1 is complete pending the human review gate.

## 2026-10-19 — Analogue–digital interface (draft)
- `spec/analog-digital-interface.md`: the signed-off back end keeps its converter, `band_sel` and `pll_lock` interface; the analogue enables, RX/TX gain words, filter selects, PLL frequency word, frac-N Σ-Δ and VCO band calibration go in a new AFE/LO control block (D3) on the same SPI bus at 0x20–0x3F, MISO ORed at chip top.
- Proposed small back-end change for the next layout run: expose `rx_on` / `tx_on` so the enable sequencer follows the effective mode (PTT gate, duty cycling).

## 2026-10-19 — P2.0 stage 1 (EM tank Q)
- Palace (surface conductors) converged at 2 µm: L 1.672 nH, Q 19.70 at 3.65 GHz. openEMS not converged (Q 14.60 → 15.26 from 2 to 1 µm; extrapolated 15.5–15.9).
- The upstream L6n2 measured-vs-simulated data (gds2palace v0.8.2) shows this Palace setup (surface conductors, merged vias without fill-factor correction) reading Q 24 % high at 3.5 GHz; scaled, L2n0 Q ≈ 15.6–15.9, matching openEMS. Provisional design Q 14.9 kept until stage 2 (filled metals + via correction, openEMS 0.7 µm).

## 2026-10-20 — P2.0 EM result accepted (tank Q)
- Design tank Q and L of SG13_Octagon_L2n0 from P2.0 stage 2 (`reports/phase2-review/p20-stage2.md`): Palace, filled metals + via fill-factor correction, 1 µm (converged), de-embedded. Q 14.2 / 15.3 / 15.5 / 16.9 at 3.12 / 3.5 / 3.65 / 4.2 GHz; L 1.69 nH. Replaces the provisional 14.9 (`spec/provisional-tank-q.md`).
- openEMS 0.7 µm agrees within 1.6 % in Q; L differs by a constant 3 %, carried as ±3 % L uncertainty for VCO tuning (P2.3).
- Stage 3 not run (not needed for the decision). The flicker-region pnoise check remains open in P2.0.

## 2026-10-20 — VCO topology (P2.3), D8–D10
Accepted as proposed in `spec/vco-topology.md` §5, after a comparison with common industry practice:
- D8 capacitor bank 7 bits instead of D2's 5–6: KVCO 14–47 MHz/V instead of 29–94; at 94 MHz/V the loop-filter resistor noise failed the VHF duplex limit (P2.2 rerun: −135.3 against −136 dBc/Hz) unless the loop filter grew to about 950 pF. `VCO_BAND` becomes [6:0].
- D9 VCO tail: NMOS current source, RC-filtered bias (pole ≤ 10 kHz), tail capacitor 5–10 pF; class-C biasing evaluated as a variant in P2.3. New register `VCO_BIAS` (0x2C) for the tail-current DAC.
- D10 dedicated LDO for the VCO, voltage set by the LV device limits (about 1.0–1.2 V).
- Core as D1 (NMOS cross-coupled, HBT comparison); varactor `sg13_hv_svaricap`; CML buffer before the dividers. Next: device checks (`spec/vco-topology.md` §6).

## 2026-10-20 — VCO step 1 results; D11 varactor bias
- Step 1 device checks (`spec/vco-topology.md` §8): 1.5 V differential swing at a 1.1 V centre tap (LV oxide limit with 10 % margin); bank cell about 100 µm of switch per 60 fF with 200 kΩ bias resistors (bank keeps 0.89–0.97 of tank Q, +226 fF budget margin); tail LV NMOS ≥ 160/4 µm; L2n0 lumped model within 0.71 %.
- D11: **AC-coupled varactor** (option A): `sg13_hv_svaricap` behind coupling MIMs of about 5×, gates biased through ≥ 200 kΩ, so the steep part of the C–V curve falls in the 1.2 V charge-pump range. Option B (charge pump and loop filter on the 2.7–3.6 V supply) not chosen: about twice the loop-filter area.

## 2026-10-20 — P2.3 VCO result review
- Accepted: about 5 % more switched capacitance in the bank (`spec/vco-topology.md` §9, point 2), so the bottom edge keeps margin below 3.12 GHz at the MIM best-case corner with the ± 3 % inductance uncertainty. Step 2 sizing target 955 → 1003 fF; steps 2–3 to be rerun.
- Not chosen at this review: the 4 mA cap on the tail current (the bottom bands keep 5 mA; the LO current budget D7 is checked again with the dividers in P2.4) and an amplitude calibration. The remaining items of §9 (supply pushing, real buffer and divider load, HBT comparison, tapped-inductor EM) stay open.
- Rerun after the review (2026-10-20): range 2.90–4.41 GHz; bottom edge at the MIM best-case corner 3.036–3.047 GHz (73–84 MHz margin); phase noise unchanged within 1 dB, worst margin +3.6 dB (4.20 GHz, slow corner, 85 °C). P2.3 schematic phase closed; open points in `spec/vco-topology.md` §9.

## 2026-10-20 — P2.4 divider topology, D12–D14
- Topology as proposed in `spec/lo-divider-topology.md`: CML buffer after the VCO; UHF CML ÷2 then a Johnson ÷4 (quadrature); VHF CML ÷3 then a Johnson ÷8 (8 phases, D4); one chain powered per band.
- D12: the LO current budget stays ≤ 10 mA (D7); the **VCO tail current is capped at 4 mA** (this reverses the P2.3 review, where the cap was not chosen). Bottom-band phase noise about 2 dB worse, expected margin still about 6 dB; VCO step 3 to be rerun.
- D13: UHF LO as **four phases at 25 % duty**.
- D14: flip-flops after the first stage in **CMOS TSPC**; CML only if step 1 shows less than 1.3× speed margin at the slow corner, 1.08 V, 125 °C.

## 2026-10-20 — P2.4 step 2: divider start-up, D15
- Finding: with the dividers on while the VCO starts up, the CML ÷3 free-runs and at the slow corner stays there (VHF 4.20 GHz failed in the full chain; stand-alone `div3s` fails at 4.41 GHz with any clock ramp, also with 0.6–0.75 V final swing). Clock shape, duty cycle, load and latch current were ruled out (`div3x`).
- D15: **sequenced divider enable** — the AFE sequencer raises `en_lodiv` about 1 µs after `en_vco` and pulses it low again after a band change or a failed PLL lock; both chains. With the divider enabled after start-up the VHF slow 4.20 GHz case divides correctly (8 phases, errors ≤ 0.12°). Circuit-level removal of the free-running state was not chosen.

## 2026-10-20 — VCO rerun with the 4 mA cap; P2.4 step 2 done
- VCO step 3 rerun with D12 (`analog/vco/step3/out/summary_4ma.txt`): range and corners unchanged (2.90–4.44 GHz typical, bottom edge 3.040–3.050 GHz at the MIM best case); bottom-band phase noise 0.3–0.7 dB worse than with 5 mA, worst margin still +3.6 dB (4.20 GHz, slow, 85 °C).
- P2.4 step 2: all 8 cases (UHF / VHF, typical / slow, two frequencies) divide correctly with D15; phase errors ≤ 0.46° (UHF), ≤ 0.12° (VHF); UHF retiming output PMOS 2× for the 25 % duty (22.6–25.0 % at slow); LO current about 9.7–10.1 mA at VHF worst case, at the D7 limit.
