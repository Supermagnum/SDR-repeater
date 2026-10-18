# Project handoff — SDR repeater / LinHT RFIC

**State as of:** 18 October 2026, branch `phase1/wip-sram`, run `phase1g`
**Purpose:** let an RF/IC engineer (or an AI agent under human review) pick up the work, reproduce every result, and see what is solid, what is provisional and what is open.

> **Nothing in this repository has been submitted for fabrication.** Submission to any MPW shuttle or foundry is a deliberate human decision and is out of scope for all automated work.

---

## 1. What exists and what does not

| Phase | Content | Status |
|---|---|---|
| 0 | Toolchain pinning, EM baseline (inductor L2n0) | Done. Matched-mesh EM study still required before Phase 2 |
| 1 | Digital back end (SPI, decimation, DC/IQ correction, I2S, TX interpolation and Σ-Δ, power control) | **Physically clean** (`phase1g`). Not yet approved — see section 8 |
| 2 | LO: ≈3.44–3.52 GHz VCO, ÷8 / ÷24 dividers, quadrature | Not started |
| 3 | RX: LNA, passive mixer, TIA, Σ-Δ modulator | Not started |
| 4 | TX: Σ-Δ DAC, IQ modulator, PA driver | Not started |
| 5 | Integration: single-chain die, pad ring, top level | Not started |

The only layout today is the **digital block**. It contains no RF circuitry.

---

## 2. Design baseline (provisional, see `spec/`)

- **Bands:** 2 m (144–146 MHz) and 70 cm (430–440 MHz) on one single-chain die, band selected per module/handheld. 23 cm deferred.
- **LO plan:** one LC VCO ≈3.44–3.52 GHz; 70 cm = ÷8, 2 m = ÷24 (÷3 then ÷8); quadrature from the final ÷2 stages.
- **Reference:** 32 MHz or 36 MHz (`ref_36` board strap). The Σ-Δ modulator clock is the reference, so every output rate (25, 50, 100, 200, 500 kHz) is an exact integer ratio.
- **IQ interface:** I2S, RFIC is **master** by default (BCLK/LRCLK from the reference); slave mode with an 8-deep async FIFO. Slot width is chosen per rate. Proposed backplane change for pins b14/b15 is in `spec/i2s-clocking.md` (the RF-modules document itself was not edited).
- **Hosts:** repeater modules (SpacemiT K3 backplane) **and** the LinHT handheld (CompuLab MCM-iMX93, 2S battery, 5 V buck rail, SX1255 at 36 MHz). LinHT facts are provisional: Rev C boards were not yet validated when read. The LinHT repository is treated as read-only reference.
- **Process:** IHP SG13G2 130 nm SiGe BiCMOS, open PDK.

Decisions and their reasons are recorded in `decisions.md` and `spec/baseline-decisions.md`.

---

## 3. Repository map

| Path | Content |
|---|---|
| `decisions.md` | Human decisions with date and rationale |
| `spec/` | Baseline decisions, I2S clocking proposal |
| `docs/` | System and RF-module documents |
| `rtl/digital/` | Digital back end RTL, `config.yaml`, `constraints.sdc`, `pdn_cfg.tcl`, `notes.md` (register map) |
| `rtl/cocotb/` | Testbenches: `run_sim.py`, `test_backend.py`, `test_power.py`, `gate_sim.py` |
| `reports/` | Review gates, EM report, Magic DRC waiver |
| `tools/` | Tool manifest/lock, container tool list, PDK contents, LibreLane variable list |
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
| CACE | 2.11.0 in the image — the Phase 0 manifest names 2.13.0; **resolve this mismatch** |
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

# RTL tests (expect 13/13 PASS)
cd /foss/designs/rtl/cocotb && python3 run_sim.py

# Full flow (~1.5 h)
cd /foss/designs/rtl/digital
librelane --manual-pdk --pdk-root /foss/pdks --pdk ihp-sg13g2 --run-tag phase1g config.yaml

# IHP full DRC deck on the result (~12 min)
python3 /foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py \
  --path=$(ls runs/phase1g/final/gds/*.gds | head -1) --topcell=digital_backend \
  --run_dir=runs/phase1g/ihp-full-drc --mp=4 --antenna --no_density
```

The flow exits with "Magic DRC errors found". That is expected and waived (section 7).

---

## 6. Digital back end — current architecture

- **SPI** (mode 0, 16-bit frame) clocked by SCLK; configuration crosses into the core clock by toggle synchronisation, so the reference may be stopped in shutdown.
- **RX:** multiplier-free 1-bit front end (8-tap FIR), two order-4 CIC stages per channel, compensation FIR and 31-tap half-band.
- **Shared filter engine:** one multiplier and **one** `RM_IHPSG13_1P_64x16_c2` SRAM hold the RX compensation FIR, the RX half-band and the TX half-band (the chain is half-duplex). I and Q delay lines use words 0–30 and 32–62.
- **TX:** I2S input, DC and IQ correction, half-band interpolate-by-2 (shared engine), order-2 CIC interpolator (shares the first CIC integrator adders), 2nd-order 1-bit Σ-Δ modulator.
- **Correction:** DC loop (state kept across RX sleep), IQ gain and phase cross-term (1/128 rad per LSB, about ±57° range).
- **Power:** root clock gates for run/RX/TX built as latch + AND (the PDK marks its ICG cells `dont_use`; this is deliberate); per-block power-down; duty-cycled RX.
- **Register map:** `rtl/digital/notes.md`. **Proposed, not frozen** — CTRL[3] is reserved after the per-rate slot-width change.

---

## 7. Verified results

### Simulation (`run_sim.py`, this tree)
13/13 tests pass, including:

| Test | Result | Limit |
|---|---|---|
| `rx_tone_rtl` — passband gain on real RTL | +0.39 dB | ±1 dB |
| `rx_tone_rtl` — alias rejection on real RTL | 47.2 dB | ≥ 45 dB (provisional) |
| `tx_image_and_noise` — image rejection | 64.3 dB | ≥ 40 dB |
| `filter_response_limits` (model) | ripple 0.189 dB, alias 48.1 dB worst case | 0.25 dB / 45 dB |

Verilator and gate-level simulation were run on earlier trees (12/12); **re-run them on this tree**.

### Physical (`phase1g`)

| Check | Result |
|---|---|
| IHP full KLayout DRC (maximum rule set, antenna included, density excluded) | **0** |
| LibreLane KLayout DRC | 0 |
| LVS (devices, nets, pins, properties) | **0 differences** |
| Antenna | 0 violations (16 diodes inserted) |
| Routing DRC | 0 (converged after 3 iterations) |
| Setup worst slack / TNS (all corners) | +1.20 ns / 0 |
| Hold worst slack / TNS (all corners) | +0.05 ns / 0 — thin, monitor |
| Hold buffers inserted | 135 |
| Cell area | 0.694 mm² |
| Magic DRC | 7816, **all inside the SRAM footprint** — waived, see `reports/phase1-review/magic-drc-waiver.md` |

Density rules are **not** checked at block level. They must be checked at chip level with fill.

---

## 8. Open items before Phase 1 can be approved

1. **Area:** 0.694 mm² against a 0.30 mm² target (goal 0.25 mm²). Needs structural work, mainly the TX chain and CIC; `DROP = 0` in `cic4.sv` currently disables Hogenauer pruning.
2. **Output scale:** a full-scale 1-bit input gives about **64 codes** out of ±32767. Rescale `norm`/CIC shifts so full scale lands near ±16 000–32 000. This currently limits RX dynamic range.
3. **I/O constraints:** SPI pins must be timed against `sclk` and I2S-slave pins against `bclk_i`, not `clk`.
4. **`ref_36`:** declared a false path (static board strap). Also enforce in RTL that changes only take effect under reset, and state it in the spec.
5. **Clean-up:** debug `$display` in `fir_seq.sv`; unused `band_c` and `bitn`; width warnings in `i2s_master.sv`; deprecated `PL_TARGET_DENSITY`; 127 lint warnings to triage.
6. **Re-run** Verilator and gate-level simulation on this tree.
7. **Hold margin** of 50 ps: re-check after every change.

---

## 9. Provisional or lower-confidence values

- **Alias limit 45 dB** — to be derived in Phase 3 together with the Σ-Δ modulator design.
- **TX out-of-band limit** (1–8 MHz, 20 dB below tone) — far too loose; Phase 4 must derive it from the emission mask (expected ≥ 60–70 dB below carrier near the carrier), including the reconstruction filter and modulator order.
- **Tank Q** — provisional openEMS values 11.8 (2.4 GHz) / 14.9 (3.5 GHz); Palace gives about 20–26 % higher. Matched-mesh, de-embedded study required before Phase 2.
- **VCO phase noise** — open tools offer only experimental PSS and no PNOISE; all phase-noise results are lower confidence and must be cross-checked by hand.
- **LinHT interface facts** — provisional until Rev C is validated and its board files are read.

---

## 10. Problems found and fixed (lessons)

| Problem | Cause | Fix |
|---|---|---|
| TX image rejection 18 dB | `fir_seq` wrote each new sample at `2·wp−1` instead of `wp−1` (write address passed through `haddr` twice) | Write at age 30 (RX) / 15 (TX). Rejection back to 64.3 dB |
| Same bug invisible in RX | RX tests used only DC input; a scrambled delay line still passes DC | Added `rx_tone_rtl` (real Σ-Δ stream, tone + aliasing interferer) |
| 6449 hold buffers | 0.25 ns clock uncertainty applied to hold as well as setup, plus margin and derate, on direct flip-flop chains | Hold uncertainty 0.05 ns after CTS (`decisions.md`). Result: 135 buffers |
| SRAM power pins unconnected | SRAM power pins are vertical Metal4; core grid is TopMetal1/TopMetal2; LibreLane's macro grid only connects TopMetal1–TopMetal2 | `pdn_cfg.tcl`: horizontal Metal5 straps over the macro, connects Metal4↔Metal5↔TopMetal1 |
| Setup fail −0.68 ns at 125 °C | `ref_36` timed as a per-cycle input | False path (static strap) |
| 4 × `NW.d` in IHP full deck | Standard-cell rows cut by the SRAM keep-out on N-well (power) boundaries | `FP_MACRO_VERTICAL_HALO: 13.78` (one row) |
| Lint stop in `hb_sram.sv` | `dout` assigned in `initial` and `always_ff` | Simulation model uses plain `always` |

---

## 11. Next steps

1. Close the Phase 1 open items (section 8) and pass the Phase 1 review gate.
2. Matched-mesh, de-embedded inductor study (Phase 0 EM follow-up).
3. Phase 2 LO test chip — hand-designed, human-reviewed topology.

The agent instructions (phases, forbidden actions, review gates, provenance tags `[SCH]` `[PEX-C]` `[PEX-RC]` `[EM]` `[HAND]` `[LIT]`) live in the project's agent prompt; follow it for any automated work.
