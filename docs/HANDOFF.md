# Project handoff — SDR repeater / LinHT RFIC

**State as of:** 19 October 2026. Reference layout: **`phase1l`** (signed off; pin-map RTL of 2026-10-19). Phase 2 plan: `spec/phase2-plan.md` (draft for review). RF front-end requirements drafted in `spec/rf-frontend.md` (branch `phase2/rf-spec`); VACASK phase-noise analysis validated (`analog/pn-validation/`).
**Purpose:** let an RF/IC engineer (or an AI agent under human review) pick up the work, reproduce every result, and see what is solid, what is provisional and what is open.

> **Nothing in this repository has been submitted for fabrication.** Submission to any MPW shuttle or foundry is a deliberate human decision and is out of scope for all automated work.

---

## 1. What exists and what does not

| Phase | Content | Status |
|---|---|---|
| 0 | Toolchain pinning, EM baseline (inductor L2n0) | Done. Matched-mesh EM study (P2.0): stages 1–2 done (`reports/phase2-review/p20-stage1.md`, `p20-stage2.md`) — filled-metal Palace converged and agrees with openEMS 0.7 µm within 1.6 % in Q; L differs by a constant 3 %. Design Q 15.3 at 3.5 GHz (L 1.69 nH ± 3 %) accepted 2026-10-20, replacing the provisional 14.9 |
| 1 | Digital back end (SPI, decimation, I2S, TX interpolation and Σ-Δ, power control) | **Signed off on `phase1l`** (section 7). Awaiting the human Phase 1 review gate |
| 2 | LO: VCO 3.12–4.20 GHz, ÷8 / ÷24 dividers, quadrature | Plan in `spec/phase2-plan.md`; owner decisions D1–D7 accepted; P2.2 PLL model first run passes (`analog/pll-model/`, 150 kHz loop, VCO ≤ −116 dBc/Hz at 1 MHz); P2.0 EM study done and accepted (flicker check done); P2.3 VCO schematic done 2026-10-20 (`spec/vco-topology.md` §9: 2.90–4.41 GHz, all corners covered, phase noise within limits in all bands and corners, worst margin +3.6 dB; result review done, open points listed), P2.4 divider topology accepted 2026-10-20 (`spec/lo-divider-topology.md`, D12 VCO ≤ 4 mA, D13–D14); step 1 done (TSPC confirmed; CML dividers need ≥ 0.5 V-per-side clock at the slow corner); step 2 done (all 8 cases divide, phase errors ≤ 0.46°, D15 sequenced divider enable, LO current at the 10 mA limit; `spec/lo-divider-topology.md` §8); VCO rerun with the 4 mA cap done (bottom band 0.3–0.7 dB worse, worst margin +3.6 dB unchanged); P2.4 step 3 done 2026-10-21 except the divider noise floor (`spec/lo-divider-topology.md` §9: ÷3 regeneration, AC-coupled converter and buffer stage; all corners and 100/100 Monte Carlo samples divide; UHF raw image rejection 35–40 dB at 3σ; LO total ≈ 9.65 mA typical, ≈ 10.3 mA at ff 1.32 V); requirements in `spec/rf-frontend.md` §5; phase-noise simulation validated (`analog/pn-validation/`) |
| 3 | RX: LNA, passive mixer, TIA, Σ-Δ modulator | Not started. Requirements in `spec/rf-frontend.md` §3 and `spec/derived-limits.md` |
| 4 | TX: Σ-Δ DAC, reconstruction filter, IQ modulator, PA driver | Not started. Requirements in `spec/rf-frontend.md` §4 and `spec/derived-limits.md` |
| 5 | Integration: single-chain die, pad ring, top level | Not started. Analogue–digital interface and the new AFE/LO control block drafted in `spec/analog-digital-interface.md` (needs `rx_on`/`tx_on` exposed from the back end at the next layout run) |

The only layout today is the **digital block**. It contains no RF circuitry.

---

## 2. Design baseline (provisional, see `spec/`)

- **Frequency coverage:** **130–175 MHz** and **400–480 MHz** (2 m, 70 cm, land mobile, PMR446) on one single-chain die; band selected per module/handheld. 23 cm deferred.
- **LO plan:** one VCO at **3.12–4.20 GHz** (30 % tuning: switched-capacitor bank or two cores); UHF ÷8, VHF ÷24; quadrature from the final ÷2. `band_sel` output: 0 = ÷8, 1 = ÷24.
- **Reference:** 32 MHz or 36 MHz (`ref_36` strap on pin 11, CLK_IN, sampled at reset; internal pull-down = 32 MHz). Every output rate (25, 50, 100, 200, 500 kHz) is an exact integer ratio. The host picks the clock per channel so no clock harmonic sits on the channel (32 MHz for 2 m / 70 cm; 36 MHz for PMR446 and near 160 / 416 / 448 MHz) — table in `spec/derived-limits.md` §7.2.
- **IQ interface:** Philips I2S, continuous BCLK. RFIC is **master** by default; slave mode through a **4-deep** async FIFO. Maximum IQ rate 500 kHz. The LinHT runs at 32 MHz and uses 500 kSa/s (16-bit I/Q as left/right), every rate there has a 50 % BCLK duty. Boards on 36 MHz should prefer 100 or 500 kHz (36 MHz / 200 kHz has a 40/60 BCLK duty).
- **Calibration:** DC and IQ correction are done **by the host** (decision (a), 2026-10-18). The chip delivers the half-band output word.
- **Repeater sites:** RX and TX share one antenna through an external cavity duplexer. A full-duplex repeater uses one RFIC for RX and one for TX (the shared filter engine makes one chip half-duplex). Norwegian offsets: 600 kHz (2 m), 2 MHz (70 cm). The repeater must keep the channel at DC (zero-IF): the own-TX blocker aliases onto the channel and is removed only by the CIC nulls. The repeater RX front end defaults to the same 2× PE4312 attenuators as the LinHT (system NF ≈ 8 dB); a module designer may use an external LNA instead (≈ 5 dB).
- **Hosts:** repeater modules (DIN 41612 backplane, ECP5-25F PCIe card in the Milk-V Megrez host; SpacemiT K3 secondary) **and** the LinHT handheld (CompuLab MCM-iMX93, 2S battery, SX1255 with a 32 MHz TCXO, read from the Rev C schematic 2026-10-19). The RFIC is planned as a pin-compatible SX1255 replacement (`spec/rf-frontend.md`, option P). Other LinHT facts are provisional (Rev C not yet validated). The LinHT repository is read-only reference.
- **Process:** IHP SG13G2 130 nm SiGe BiCMOS, open PDK.

Decisions and their reasons: `decisions.md`, `spec/baseline-decisions.md`. Derived limits: `spec/derived-limits.md`.

---

## 3. Repository map

Paths are relative to the repository root. This file lives in `docs/`.

| Path | Content |
|---|---|
| `decisions.md` | Human decisions with date and rationale |
| `spec/` | Baseline decisions, I2S clocking, **derived RX/TX limits**, **RF front-end requirements** (`rf-frontend.md`) |
| `analog/pn-validation/` | VACASK phase-noise validation (passed 2026-10-19) |
| `docs/` | System and RF-module documents |
| `rtl/digital/` | Digital back end RTL, `config.yaml`, `constraints.sdc`, `pdn_cfg.tcl`, `notes.md` (register map) |
| `rtl/cocotb/` | Testbenches: `run_sim.py`, `test_backend.py`, `test_power.py`, `gate_sim.py` |
| `reports/` | Review gates, EM report, Magic DRC waiver |
| `tools/` | `check_signoff.py`, `check_area.py`, `derive_limits.py`, tool manifest/lock, PDK contents, LibreLane variable list |
| `rtl/digital/runs/` | Flow results (not in git — regenerate with section 5) |

---

## 4. Pinned toolchain

| Item | Version |
|---|---|
| Container | `hpretl/iic-osic-tools:2026.10` |
| PDK | IHP-Open-PDK commit `a49358cc` (bundled in the image). Pin is only reconsidered at a phase review gate |
| LibreLane | v3.1.0.dev3 (Classic flow) |
| Yosys / OpenROAD / OpenSTA | 0.70 / 26Q4-407-geb14e40b7 / 3.1.0 |
| KLayout | 0.30.12 |
| ngspice / Xschem | 47 / 3.4.8RC |
| Verilator / Icarus | 5.052 / 14.0 (devel) |
| cocotb | 2.1.0 |
| CACE | 2.11.0 |
| EM | gds2palace v0.8.2, gds2openEMS v0.5.0, stack-up `libs.tech/openems/openems_ihp_sg13g2/workflow/SG13G2_200um.xml` (sha256 `5d4529432b38d7996814f5096af2173d96e8ad5ff84c73ebb57904f1faf03bdf`) |

DRC flag name in this PDK: `--minimum_drc` (the old `--precheck_drc` is deprecated).

---

## 5. Reproduce the results

Host prerequisites: Docker running, user in the `docker` group.

```bash
cd SDR-repeater
docker run -it --rm -v "$PWD":/foss/designs \
  -v ~/.gitconfig:/headless/.gitconfig:ro \
  hpretl/iic-osic-tools:2026.10 --skip bash

# inside the container
iic-pdk ihp-sg13g2

# RTL tests (expect 14/14 PASS)
cd /foss/designs/rtl/cocotb && python3 run_sim.py
SIM=verilator python3 run_sim.py

# Full flow (~1 h 45 min). Do not edit, patch or switch branches in the
# repository while it runs: LibreLane re-checks its input files before every step.
cd /foss/designs/rtl/digital
librelane --manual-pdk --pdk-root /foss/pdks --pdk ihp-sg13g2 --run-tag phase1l config.yaml

# Sign-off (timing, DRC, LVS, antenna, max-cap, area <= 340 000 um^2)
cd /foss/designs
python3 tools/check_signoff.py rtl/digital/runs/phase1l

# Gate-level simulation of the routed netlist (expect 6/6)
cd rtl/cocotb && RUN=phase1l python3 gate_sim.py

# IHP full DRC deck (~10 min)
cd /foss/designs/rtl/digital
python3 /foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py \
  --path=$(ls runs/phase1l/final/gds/*.gds | head -1) --topcell=digital_backend \
  --run_dir=runs/phase1l/ihp-full-drc --mp=4 --antenna --no_density

# Duplex-offset limit derivation
python3 /foss/designs/tools/derive_limits.py
```

The flow exits with "Magic DRC errors found". That is expected and waived (section 7); all views are saved before it.

---

## 6. Digital back end — current architecture

- **SPI** (mode 0, 16-bit frame) clocked by SCLK; MOSI sampled on the rising edge, MISO driven on the falling edge. The bit counter is cleared asynchronously by CS high, so an aborted frame cannot misalign the next one. Configuration crosses into the core clock by toggle synchronisation (bundled data), so the reference may be stopped in shutdown.
- **Reset:** asynchronous, active-low, with a two-flop release synchroniser for the core clock. SPI uses the raw `rst_n`; board requirement: SCLK idle for ≥ 1 µs after `rst_n` rises, and `rst_n` low at power-up until supplies and reference are stable. For the SX1255-compatible package the RESET pin is active-high and floats at power-up, so the complete chip needs an on-chip power-on reset (`spec/rf-frontend.md` §6).
- **RX:** multiplier-free 1-bit front end (8-tap FIR), two order-4 CIC stages per channel, compensation FIR and 31-tap half-band. Full-scale 1-bit input → 16 384 codes at every rate (`norm`, `sh1`, `sh2` in `rate_table.sv`).
- **Shared filter engine:** one 18×16 multiplier and **one** `RM_IHPSG13_1P_64x16_c2` SRAM hold the RX compensation FIR, the RX half-band and the TX half-band. I and Q delay lines use words 0–30 and 32–62. One address generator for all accesses.
- **TX:** I2S input (host-corrected), half-band interpolate-by-2 (shared engine), order-2 CIC interpolator (28-bit, shares the first CIC integrator adders), 2nd-order 1-bit Σ-Δ modulator.
- **I2S:** counter-based Philips master with continuous BCLK; slave samples on the BCLK rising edge and drives on the falling edge.
- **Power:** root clock gates for run/RX/TX built as latch + AND (the PDK marks its ICG cells `dont_use`; deliberate); per-block power-down; duty-cycled RX.
- **Register map:** `rtl/digital/notes.md`. **Proposed, not frozen.** `CHIP_ID` = 0x12. 0x04–0x07 and 0x0D–0x12 are reserved (former calibration registers, read 0); `BLOCK_PD[2:1]`, `CLK_GATE[2:1]` and `CTRL[3]` are reserved.

---

## 7. Verified results

### Simulation (`run_sim.py`, this tree)
13/13 tests pass on **both Icarus and Verilator**.

| Test | Result | Limit |
|---|---|---|
| `rx_tone_rtl` — passband gain on real RTL | +0.06 dB | ±1 dB |
| `rx_tone_rtl` — alias rejection on real RTL | 59.1 dB | ≥ 45 dB (wideband) |
| `filter_response_limits` (model) | ripple 0.190 dB, wideband alias 47.9 dB; duplex offsets ≥ 108 dB; on-channel aliases ≥ 68.1 dB | 0.25 dB / 45 dB / 100 dB / 65 dB |
| `tx_image_and_noise` — image rejection | 62.6 dB | ≥ 40 dB |
| `tx_image_and_noise` — bitstream noise at 600 kHz | −107.2 dBFS/Hz | ≤ −101 dBFS/Hz |
| `tx_image_and_noise` — bitstream noise at 2 MHz | −88.1 dBFS/Hz | ≤ −81 dBFS/Hz |
| `filter_dc_all_rates` | full scale = 16 384 ± 64 at all 10 rate pairs | — |

### Gate level (`gate_sim.py`, `phase1l` routed netlist with SRAM models)
6/6 port-level tests pass: `spi_reset_and_registers`, `master_frame_lengths`, `rx_chain_ports`, `i2s_slave_philips`, `spi_aborted_frame`, `pinmap_ref36_ptt_irq`.

### Physical (`phase1l`) — `tools/check_signoff.py`: **SIGN-OFF PASS**

`phase1k` values in brackets where `phase1l` was not re-measured in the same detail.

| Check | Result |
|---|---|
| IHP full KLayout DRC (maximum rule set, antenna included, density excluded) | **0** on `phase1l` (573 s) |
| LibreLane KLayout DRC / routing DRC | 0 / 0 |
| LVS | **Circuits match uniquely** (0 errors) |
| Antenna | 0 violating nets (8 antenna cells) |
| Max-cap / max-slew | 0 / 0 |
| Setup worst slack | **+3.99 ns**; TNS 0 [`phase1k`: +3.55 / +11.10 / +11.32 ns slow / typ / fast] |
| Hold worst slack | **+0.089 ns**; TNS 0 (guard ≥ 0.08 ns) [`phase1k`: +0.097 ns] |
| Hold buffers / setup buffers | [`phase1k`: 50 / 0] |
| Real cell area (std cells + SRAM, no filler) | **339 617 µm²** (std cells 324 377 + SRAM 15 240) — limit 340 000 µm²; **383 µm² left** [`phase1k`: 335 044] |
| Die area | 0.597 mm² (filler 212 566 µm²) [`phase1k`: 0.592 mm²] |
| Magic DRC | 7 815 (unchanged from `phase1k`), **all inside the SRAM footprint** (100, 100)–(336.80, 164.36) µm, 0 outside — waived, `reports/phase1-review/magic-drc-waiver.md` |

Clock period 27.778 ns (36 MHz), setup uncertainty 0.25 ns, hold uncertainty 0.05 ns. Density rules are **not** checked at block level; they must be checked at chip level with fill.

### Run history

| Run | RTL | Result |
|---|---|---|
| `phase1i` | before CS counter / continuous BCLK | clean, setup +0.80 ns, 0.434 mm² real area |
| `phase1j` | all fixes, before area work | setup **−0.050 ns** at slow corner (SRAM `A_DOUT` → MAC, placement variation); everything else clean, gate level 5/5. Stopped at step 74 because files were changed mid-run; results reconstructed from step 72 |
| `phase1k` | area patch + timing-driven placement + post-route setup repair | sign-off pass |
| `phase1l` | pin-map RTL: `ref_36` strap, PTT gate, IRQ, INFO (2026-10-19) | **sign-off pass** (above); LVS match, gate level 6/6 |

---

## 8. Open items before Phase 1 can be approved

1. **Human Phase 1 review gate.** All automated checks pass; approval is a human decision.
2. **Lint:** LibreLane reports 106 lint warnings (its own Verilator flags and file set). The changed modules are clean under `verilator -Wall`, but the 106 have not been triaged one by one.
3. ~~`ref_36`~~ — pin-11 strap sampled at reset, with the PTT gate (DIO3) and IRQ (DIO1); signed off on `phase1l`, IHP full KLayout DRC 0.
4. **Register map** is proposed, not frozen. Freeze at the review gate.
5. **Area target:** 0.34 mm² real cell area is met (339 617 µm², **383 µm² left** — no room for further digital logic; the PLL's Σ-Δ modulator needs its own block, `spec/phase2-plan.md` D3). The original 0.30 mm² is not reachable without removing functions (`decisions.md` 2026-10-18).
6. **Hold margin:** +0.089 ns (`phase1l`); the 0.08 ns guard in `check_signoff.py` catches any regression. Re-check after every change.

Closed since the previous handoff: output scale (FS 16 384), SPI/I2S I/O constraints, aborted SPI frames, gapped BCLK (continuous BCLK), `band_c` unused (`band_sel` output), README §11.1, provisional RX/TX limits (`spec/derived-limits.md`), gate-level simulation, area.

---

## 9. Provisional or lower-confidence values

- **Derived limits** (`spec/derived-limits.md`) assume 25 W, 80 dB duplexer isolation, ≤ 1 dB desense, and a system NF of 8 dB with the attenuator front end (baseline) or 5 dB with an LNA (option), see `spec/derived-limits.md` §8. Reviewer to confirm isolation and power. Regulatory limit from ITU RR App. 3; confirm against current Nkom licence conditions.
- **Phase 3/4 analogue requirements** derived from those limits: LO phase noise ≤ −136 dBc/Hz at the duplex offset (25 W, baseline; −139 with the LNA option), RX ADC DR ≥ 101 dB in 12.5 kHz (104), anti-alias ≥ 40 dB at ±8/9 MHz and ≥ 70 dB at ±32/36 MHz, TX reconstruction filter ≥ 51 dB at 600 kHz and ≥ 71 dB at 2 MHz (54 / 74 with the LNA option), VHF third-harmonic rejection (harmonic-reject mixer or preselector).
- **500 kHz TX** is for simplex/LinHT use only; a repeater transmits at ≤ 200 kHz IQ.
- **Tank Q** — EM design values from P2.0 (`spec/provisional-tank-q.md`): Q 14.2 / 15.3 / 16.9 at 3.12 / 3.5 / 4.2 GHz, L 1.69 nH ± 3 %. Conservative simulated values; confirmed only by measurement after fabrication.
- **VCO phase noise** — VACASK `pnoise` (oscillator mode) validated 2026-10-19 against the exact LC result (worst 0.19 dB, 100 kHz–20 MHz) and against transient noise on an SG13G2 oscillator (0.5 dB). Flicker region validated 2026-10-20: exact case 0.2 dB, SG13G2 with a real tail by tone injection 0.48 dB (`reports/phase2-review/p20-flicker.md`). Settings for P2.3: `pss_minpts` 16 000, offsets ≥ 30 kHz. Transient noise is not a usable reference for transistor circuits (14 fs steps).
- **LinHT interface facts** — provisional until Rev C is validated and its board files are read.

---

## 10. Problems found and fixed (lessons)

| Problem | Cause | Fix |
|---|---|---|
| TX image rejection 18 dB | `fir_seq` write address passed through `haddr` twice | Write at age 30 (RX) / 15 (TX). Rejection 62.6 dB |
| Same bug invisible in RX | RX tests used only DC input | Added `rx_tone_rtl` (real Σ-Δ stream, tone + aliasing interferer) |
| 6449 hold buffers | 0.25 ns clock uncertainty applied to hold as well | Hold uncertainty 0.05 ns. Now 50 buffers |
| SRAM power pins unconnected | SRAM power on Metal4, core grid on TopMetal1/2 | `pdn_cfg.tcl`: Metal5 straps over the macro |
| Setup fail at 125 °C | `ref_36` timed as a per-cycle input | False path (static strap) |
| 4 × `NW.d` in IHP full deck | Rows cut by the SRAM keep-out | `FP_MACRO_VERTICAL_HALO: 13.78` |
| Max-cap on SRAM `A_DOUT` | Estimated loads before routing | Post-GRT design repair, 25 % cap margin |
| Full scale was ~64 codes | CIC shifts / `norm` | Rescaled; shift moved into `sh1` to avoid CIC1 truncation; FS 16 384 |
| SPI reads shifted one bit | MISO changed on the sampling edge | MISO from a `negedge sclk` process |
| Aborted SPI frame misaligned the next | Bit counter only cleared by a full frame | Counter cleared asynchronously by CS high |
| I2S word misaligned on real hosts | Non-standard edges; gapped BCLK | Philips format, counter-based master, continuous BCLK |
| Core flops left reset on different edges | Async release | Two-flop reset synchroniser |
| Verilator read every register as 0 | No reset edge at time 0 | Tests drive `rst_n` high, then low |
| Gate sim read all zeros | Testbench raised CS and SCLK at the same instant | CS raised first, as a real host does |
| Address refactor X in Icarus | A function's hidden reads are not in a continuous assignment's sensitivity | Logic written out in `always_comb`; checked bit-identical over 120 000 random cycles |
| "0.708 mm²" area | `design__instance__area` includes 0.274 mm² filler | Real area = stdcell + macro (`check_area.py`) |
| `phase1j` stopped at step 74 | RTL files deleted while the flow ran | Never edit the tree during a run |
| `phase1j` setup −0.05 ns | Placement variation on a thin path; no post-route setup repair | `PL_TIMING_DRIVEN`, `RUN_POST_GRT_RESIZER_TIMING`, 0.1 ns margins → +3.55 ns |

---

## 11. Next steps

0. ~~Run `phase1l`~~ — done: sign-off pass and IHP full KLayout DRC 0.
1. Phase 1 review gate (section 8).
2. Matched-mesh, de-embedded inductor study (Phase 0 EM follow-up).
3. Phase 2 LO (VCO 3.12–4.20 GHz, ÷8/÷24, fractional-N PLL) — plan, budgets, steps P2.0–P2.7 and owner decisions D1–D7 in **`spec/phase2-plan.md`**; hand-designed, human-reviewed topology, against `spec/rf-frontend.md` §5. Phase noise can now be simulated with VACASK `pnoise` at the settings in `analog/pn-validation/README.md`.

The agent instructions (phases, forbidden actions, review gates, provenance tags `[SCH]` `[PEX-C]` `[PEX-RC]` `[EM]` `[HAND]` `[LIT]`) live in the project's agent prompt; follow it for any automated work.
