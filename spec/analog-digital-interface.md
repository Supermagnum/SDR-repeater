# Analogue–digital interface (HT13G-M)

Status: **draft for human review, 2026-10-19.** It records how the signed-off digital back end (`rtl/digital/`, layout `phase1l`) connects to the analogue blocks of Phases 2–4. It also specifies the new **AFE/LO control block** decided in D3 (`spec/phase2-plan.md`). Signals that exist in the RTL today are marked **[RTL]**; the rest are proposals **[PROP]** for P2.5 and Phases 3–5.

---

## 1. The pieces

```
                  pads (SX1255 pin-out)
                          │
   ┌──────────────────────┴───────────────────────────── chip top (Phase 5) ─────────────┐
   │  RESET (pin 9) + POR ─► rst_n          MISO = miso_be OR miso_afe                     │
   │  level shifters 1.2 V ↔ pad domain     ref_36 strap (pin 11)                          │
   │                                                                                       │
   │   ┌────────────────────────┐   rx_on, tx_on, band_sel   ┌──────────────────────────┐  │
   │   │ digital back end       │ ─────────────────────────► │ AFE/LO control (new, D3) │  │
   │   │ [RTL], 0.34 mm², full  │ ◄──── pll_lock ──────────  │ SPI 0x20–0x3F, enables,  │  │
   │   │ SPI 0x00–0x1F, filters │                            │ gains, frac-N Σ-Δ, band  │  │
   │   │ I2S, Σ-Δ DAC modulator │                            │ calibration              │  │
   │   └───┬───────────────▲────┘                            └──────┬───────────▲───────┘  │
   │       │ dac_bit_i/q   │ adc_bit_i/q                    enables │ gains     │ div_clk  │
   │       ▼               │                                 div_n  ▼           │ lock     │
   │   ┌──────────────────────── analogue (Phases 2–4) ───────────────────────────────┐    │
   │   │ Σ-Δ DAC ► recon. filter ► IQ mod ► TX atten ► PA driver ──► RF_OP / RF_ON     │    │
   │   │ RF_IN ► LNA ► mixer (HR on VHF) ► TIA/AAF ► Σ-Δ ADC                           │    │
   │   │ XTB ► ref buffer ► PFD/CP ► loop filter ► VCO ► ÷8 / ÷24 (I/Q, 8-phase) ► LO  │    │
   │   │                                   ▲ MMD ◄── div_n         │ div_clk           │    │
   │   └──────────────────────────────────────────────────────────────────────────────┘    │
   └───────────────────────────────────────────────────────────────────────────────────────┘
```

- **Digital back end [RTL]:** SPI registers 0x00–0x15, RX decimation, TX interpolation and the 2nd-order Σ-Δ modulator that drives the DAC, I2S, power modes, IRQ. It is signed off and has **383 µm² left**, so it gets no new functions.
- **AFE/LO control [PROP]:** a new small digital block (D3) containing:
  - SPI registers 0x20–0x3F;
  - the analogue enable sequencer;
  - receive and transmit gain words;
  - the fractional-N Σ-Δ modulator (MASH 1-1-1, 24-bit);
  - VCO band calibration.

  Estimate: about 200 flip-flops, roughly 0.02–0.03 mm² of standard cells.
- **Chip top [PROP]:** pad mapping, reset combination, MISO combination, level shifters, supply domains.

---

## 2. Clocks, reset, supplies

| Item | Definition |
|---|---|
| Reference `clk` | 32 or 36 MHz from XTB through the analogue reference buffer. **One clock for both digital blocks and for the converters**: the Σ-Δ ADC samples and the DAC bits update on it, so there is no clock-domain crossing in the data path. [RTL] |
| `div_clk` [PROP] | Output of the multi-modulus feedback divider (≈ f_ref). Clocks the frac-N Σ-Δ modulator so that the next modulus `div_n` is ready one divider cycle ahead. Asynchronous to `clk`; SPI values reach it through a commit handshake (§5). |
| `sclk` | SPI clock (pads). The back-end register file runs on it even with `clk` stopped. [RTL] |
| `bclk_i` | I2S bit clock in slave mode. [RTL] |
| Reset | `rst_n = !RESET_pin_sync && por_n`: the active-high SX1255 RESET pin (internal pull-down) combined with the analogue power-on reset. Asynchronous assertion, released through the two-flop synchroniser already in the back end; the AFE block uses the same scheme. |
| `ref_36` | Pin-11 strap, latched by the back end at reset [RTL]; the AFE block reads the latched value from the back end (INFO[0]) or takes the same pin with its own reset latch. |
| Supplies | Both digital blocks on VR_DIG (1.2 V). Analogue on VR_ANA1 (RX, LO) and VR_ANA2 (TX, DAC); PA driver on VR_PA. Separate supply and ground returns per domain; guard rings between the digital blocks and the LNA/VCO. |
| Level shifting | Every signal between the 1.2 V digital domain and the 2.7–3.6 V pad domain or an analogue domain on another supply crosses a level shifter. The 1-bit converter lines are kept short and shielded. |

---

## 3. Back end ↔ analogue (exists today) [RTL]

| Signal | Dir. (from back end) | Width | Clock / timing | Meaning |
|---|---|---|---|---|
| `adc_bit_i`, `adc_bit_q` | in | 1 + 1 | sampled on `clk` rising | Σ-Δ ADC output, **1 = +1, 0 = −1**, one bit per reference clock |
| `adc_valid` | in | 1 | `clk` | High while the ADC runs (every clock). Drives the decimator front end |
| `adc_i`, `adc_q` | in | 16 + 16 | `clk` | Test bypass: multi-bit samples straight into the decimator when `BLOCK_PD[0]` is set. Tie to 0 if unused |
| `dac_bit_i`, `dac_bit_q` | out | 1 + 1 | launched on `clk` rising | Σ-Δ DAC drive, **1 = +1** (sign of the modulator state inverted) |
| `dac_bit_valid` | out | 1 | `clk` | High while the TX modulator runs |
| `dac_valid`, `dac_i`, `dac_q` | out | 1 + 16 + 16 | `clk` | Test/observation: the 16-bit TX samples at the I2S frame rate (before interpolation) |
| `band_sel` | out | 1 | static | 0 = ÷8 (UHF), 1 = ÷24 (VHF) for the LO dividers; SPI `BAND` (0x0C). A write starts a 64-clock digital relock window; the real PLL relock is longer (§6) |
| `pll_lock` | in | 1 | asynchronous, 2-flop synchronised | PLL lock detector. Read in INFO[2]; IRQ source with `IRQ_EN[3]` |
| `valid_iq` | out | 1 | `clk` | Valid IQ is on the I2S port (pin 14, Q_OUT, spare) |

**Converter timing [PROP].** The RTL samples ADC bits and launches DAC bits on the rising edge of `clk`; the SDC budgets 20 % of the period for external input/output delay (LibreLane default).
- The ADC comparator latches on the **falling** edge, giving half a period (13.9 ns at 36 MHz) of settling and routing before the digital rising-edge sample.
- The DAC gets a **retiming flip-flop at the DAC itself**, clocked by the clean reference (falling edge). This decouples DAC switching from the digital block's clock-tree jitter and edge timing, which matters for the TX noise floor.

---

## 4. Back end ↔ pads [RTL]

| Back-end port | SX1255 pin | Notes |
|---|---|---|
| `sclk`, `cs_n`, `mosi`, `miso` | 17 SCK, 20 NSS, 19 MOSI, 18 MISO | MISO combined with the AFE block (§5) |
| `bclk_o` / `bclk_i`, `bclk_oe` | 10 CLK_OUT | Bidirectional: master out (default), slave in |
| `lrclk_o` / `lrclk_i`, `lrclk_oe` | 23 DIO2 | I2S word select, bidirectional |
| `dout` | 15 I_OUT | RX IQ |
| `din` | 13 I_IN | TX IQ |
| `clk_req` | 21 DIO0 | Request to the host to start the reference |
| `irq_n` | 22 DIO1 | Active low; open drain on the repeater module |
| `ptt_pin` | 24 DIO3 | Hardware PTT gate, internal pull-down |
| `ref_36` | 11 CLK_IN | Strap, internal pull-down |
| `valid_iq` | 14 Q_OUT | Spare / test |
| `rst_n` | 9 RESET | Through the chip-top reset combination (§2) |

---

## 5. AFE/LO control block [PROP]

### 5.1 SPI sharing

- Same four SPI pads. The back end owns 0x00–0x1F (0x16–0x1F reserved); the AFE block owns **0x20–0x3F**.
- **MISO = miso_back_end OR miso_afe** at chip top. Each block drives 0 when the frame addresses a register it does not own. The back end already does this: unknown addresses read 0 and writes to them are ignored. A write to an AFE address also toggles the back end's configuration-copy handshake, which only re-copies unchanged values.
- Same frame: mode 0, 16 bits, write bit + 7-bit address + 8-bit data.

### 5.2 Registers

| Addr | Name | Reset | Fields |
|---|---|---|---|
| 0x20 | AFE_ID | 0x01 | Read only |
| 0x21 | RX_GAIN | 0x00 | [1:0] LNA step: 0 / −6 / −12 / −24 dB. [5:2] TIA/PGA gain 0–30 dB in 2 dB steps. Total range 54 dB (requirement ≥ 48 dB) |
| 0x22 | TX_ATT | 0x0F | [3:0] TX attenuation after the reconstruction filter, 0–30 dB in 2 dB steps (requirement ≥ 30 dB, ≤ 2 dB). Reset = maximum attenuation. [7] PA-driver force-off |
| 0x23 | FILT | 0x04 | [2:0] RX anti-alias / TX reconstruction corner for IQ rate 25 / 50 / 100 / 200 / 500 kHz (same coding as RATE; the host writes both). [3] harmonic-reject mixer enable (normally = `band_sel`). [4] 8-phase LO enable (VHF) |
| 0x24 | PLL_CTRL | 0x0E | [0] PLL on in standby (fast wake). [1] MASH enable (0 = integer-N). [2] dither enable. [5:3] charge-pump current, (code + 1) × 25 µA = 25–200 µA (reset code 1 = 50 µA, `analog/pll-model/`). [6] start band calibration (self-clearing). [7] manual band: `VCO_BAND` written by the host, not by the calibration (moved here from `VCO_BAND`[7] with D20) |
| 0x25 | N_INT | — | Integer part of the feedback divider, 86–131 (3.12 GHz / 36 MHz = 86.7 … 4.20 GHz / 32 MHz = 131.25) |
| 0x26–0x28 | N_FRAC | 0 | 24-bit fraction, MSB in 0x26. **A write to 0x28 commits N_INT and N_FRAC together**, applied at the next `div_clk` edge (handshake into the `div_clk` domain) |
| 0x29 | VCO_BAND | 0x80 | [7:0] capacitor-bank code (8 bits since D20, 2026-10-25; 7 bits in D8). Written by the calibration, or by the host when `PLL_CTRL`[7] = 1 (manual) |
| 0x2A | PLL_STATUS | — | Read only. [0] lock (synchronised), [1] calibration busy, [2] calibration failed, [3] committed N not yet applied, [4] V_tune below the monitor window (≈ 0.30 V), [5] V_tune above it (≈ 0.90 V) — D20 V_tune monitor: firmware re-calibrates between transmissions if set |
| 0x2B | AFE_FORCE | 0x00 | Test: [7] override; [6:0] force individual enables (§6) on regardless of mode |
| 0x2C | VCO_BIAS | 0x10 | [4:0] VCO tail-current DAC (D9): amplitude per band, written by the host with the band (or by a later amplitude loop). Range and step set in P2.3 |

RF frequency: **f_RF = (N_INT + N_FRAC / 2²⁴) · f_ref / D**, D = 8 (UHF) or 24 (VHF). Resolution 0.08 Hz (VHF) and 0.24 Hz (UHF) at 32 MHz.

### 5.3 Signals to and from the analogue

| Signal | Dir. (from AFE block) | Width | Meaning |
|---|---|---|---|
| `en_refbuf`, `en_pll`, `en_vco`, `en_lodiv` | out | 4 × 1 | LO chain enables; `en_lodiv` sequenced after `en_vco` (D15, §6) |
| `en_lna`, `en_mix`, `en_tia`, `en_adc` | out | 4 × 1 | RX chain enables |
| `en_dac`, `en_txmod`, `en_padrv` | out | 3 × 1 | TX chain enables |
| `lna_gain`, `tia_gain` | out | 2 + 4 | RX gain steps (static during reception) |
| `tx_att` | out | 4 | TX attenuation |
| `filt_sel` | out | 3 | Filter corner |
| `hr_en`, `lo8_en` | out | 2 | Harmonic-reject mixer, 8-phase LO |
| `cp_cur` | out | 3 | Charge-pump current |
| `vco_band` | out | 7 | Capacitor bank (D8) |
| `vco_bias` | out | 5 | VCO tail-current DAC (D9) |
| `div_n` | out | 8 | Modulus for the multi-modulus divider, updated each `div_clk` |
| `div_clk` | in | 1 | Feedback-divider output (clocks the Σ-Δ and the calibration counter) |
| `pll_lock` | in | 1 | Lock detector (also to the back end) |

### 5.4 Signals from the back end (needs a small back-end change)

The enable sequencer has to follow the back end's **effective** mode, including the PTT gate (`CTRL[3]` + `ptt_pin`) and RX duty-cycling. Those are internal signals today.

- **Proposal: expose `rx_on` and `tx_on`** (the back end's `rx_en` / `tx_en`) as two new output ports. No new logic, so the area cost is close to zero, but it needs a new back-end layout run (`phase1m`). Do it together with the next back-end change.
- Alternative without a back-end change: the AFE block snoops SPI writes to CTRL (0x00) and takes `ptt_pin` itself. This duplicates the mode logic and misses duty-cycled blanking, so it is not recommended.

---

## 6. Modes and sequencing [PROP]

| Back-end mode | LO chain | RX chain | TX chain |
|---|---|---|---|
| Shutdown | off (reference may be stopped; SPI works) | off | off |
| Standby | ref buffer on; PLL + VCO on if `PLL_CTRL[0]` (fast wake) | off | off |
| RX (`rx_on`) | on | on | off |
| TX (`tx_on`) | on | **LNA off** (protection), rest off | on; **PA driver only after `pll_lock`** |

- **Wake:** the back end already waits `WAKE` output frames before `valid_iq`. The host sets `WAKE` to cover the analogue settling plus PLL lock: at 500 kHz one frame is 2 µs, so the 125 µs PLL lock (`analog/pll-model/`) needs `WAKE` ≥ 63 when the PLL starts cold, and much less with `PLL_CTRL[0]`. Cold wake includes the VCO bias start-up bypass below (0.50 µs at 36 MHz), inside the 150 µs budget.
- **Band change:** write `BAND`, `N_INT`/`N_FRAC`, start calibration, then wait for `pll_lock` (IRQ). The back end's 64-clock relock window is only a digital handshake.
- **VCO bias start-up bypass (P2.6 open point 2, 2026-10-31):** `afe_seq` (`rtl/afe/afe_seq.sv`) drives `en_vco_bias_bp` high for **36 reference cycles** (1.00 µs at 36 MHz, 1.12 µs at 32 MHz; ≥ 0.4 µs / ≥ 6–7 τ of the bypassed tail filter). That signal gates LV NMOS switches across every VCO bias resistor (tail `rbf` 20 µm/0.13 µm ng=4; bank/varactor 5 µm/0.13 µm ng=2, smaller to limit tank C) in the VCO schematic (`analog/vco/step2/run_step2.py`). Timing constants are shared with `analog/pll/p26/wake_timing.py`. After the bypass opens, the resistors keep their noise filtering for lock.
- **LO divider enable (D15):** `en_lodiv` rises **48 reference cycles** after `en_vco` (1.33 µs at 36 MHz; after the bias bypass has opened), from the same sequencer. It is pulsed low for the same time and raised again after a write to `BAND` or `VCO_BAND`, and when calibration or lock fails (`PLL_STATUS[2]`, or no `pll_lock` within the lock window), before the next attempt. Reason: a CML divider on during VCO start-up can lock into its free-running state (P2.4 step 2, `spec/lo-divider-topology.md` §8). `AFE_FORCE` can still force it for test.
- **TX protection:** `en_padrv` is held low while `pll_lock` is low or `TX_ATT[7]` is set, so an unlocked LO never reaches the PA.

---

## 7. Open items

1. Expose `rx_on` / `tx_on` from the back end (§5.4) at the next back-end layout run.
2. Gain-step values and filter corners: confirm in the Phase 3/4 budget study.
3. Multi-modulus divider range and `div_n` width (8 bits covers 86–131 plus the MASH 1-1-1 excursion of −3…+4).
4. Band-calibration algorithm (counter on `div_clk` against `clk`, binary search over 7 bits, D8) and its time inside the 150 µs wake budget. The charge-pump code (`PLL_CTRL` [5:3]) and `VCO_BIAS` are set per band so loop bandwidth and swing stay constant while KVCO varies about 3× across the range.
5. Whether the test-bypass ports (`adc_i/q`, `dac_i/q`) are bonded to anything at chip top or left for simulation only.
6. Floorplan: digital blocks away from the VCO and LNA, converter lines short, separate supply pads per domain.
