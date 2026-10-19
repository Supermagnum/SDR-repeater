# RF front-end requirements — drop-in RFIC for LinHT and repeater modules

Status: **draft v0.2 for human review** (2026-10-19). Option P chosen by the owner. Provenance tags: `[DS]` datasheet value, `[SCH]` read from the LinHT Rev C schematic, `[DER]` derived in `spec/derived-limits.md`, `[PROP]` proposal to be confirmed.
This document turns the board-level facts into block-level targets for Phases 2–4. It does not choose circuit topologies; those are human-reviewed per the agent rules.

---

## 1. What "drop-in" means

The RFIC replaces the **Semtech SX1255** on the LinHT Rev C board and serves as the transceiver core of the repeater RF modules.

| Level | Requirement |
|---|---|
| Footprint | **Option P (decided 2026-10-19):** same package and pinout as the SX1255 (MLPQ-W 5 × 5 mm, 32 leads + exposed pad) |
| RF ports | Same ports and impedances as the SX1255 as used on the LinHT: single-ended RX input, TX output usable single-ended |
| Supply | Single 2.7–3.6 V supply, like the SX1255 `[DS]`; internal regulators with external decoupling |
| Reference | 32 MHz TCXO into XTB, as on the LinHT `[SCH]`; 36 MHz also supported |
| Control | SPI with the **same frame format** as the SX1255 (mode 0, MSB first, write bit + 7-bit address + 8-bit data, MOSI on rising, MISO on falling) `[DS]` — already what the digital back end implements |
| IQ | I2S on the SX1255 "mode B2" pins: clock on CLK_OUT, word select on DIO2, IQ multiplexed on one data pin per direction `[DS][SCH]`. LinHT runs **500 kSa/s, 16-bit I and Q as left/right audio channels**, read by ALSA / GNU Radio (`sx1255-spi -s 500`) `[M17 blog]`. That is the chip's 32 MHz / 500 kHz setting exactly: 64-clock frame, 16-bit slots, 16 MHz continuous BCLK, 50 % duty |
| Software | **Not** register-compatible. The host driver changes (register map in `rtl/digital/notes.md`); host DC/IQ correction per `decisions.md` 2026-10-18 |

What drop-in cannot give on the current LinHT board: **VHF**. Its PA match, harmonic filter (LFCN-490+) and RX input match are tuned for 70 cm `[SCH]`. VHF needs a board revision (section 8).

---

## 2. Pin map for Option P

SX1255 pinout `[DS]`, LinHT use `[SCH]`, and the proposed RFIC function.

| Pin | SX1255 | LinHT Rev C | RFIC (proposed) |
|---|---|---|---|
| 0 | GND pad | GND | GND pad (also RF ground) |
| 1 | VR_PA | 100 nF | PA-driver regulator decoupling |
| 2 | VBAT1 | +3V3 | Supply |
| 3 | VR_ANA1 | 100 nF | Analogue regulator decoupling (RX/LO) |
| 4, 7, 26, 28, 31 | GND | GND | GND |
| 5 | VR_DIG | 100 nF | 1.2 V digital core regulator decoupling |
| 6 | XTA | n.c. | Crystal option / n.c. with TCXO |
| 8 | XTB | TCXO_CLK (32 MHz) | Reference input (`clk`); 32 or 36 MHz per the `ref_36` strap on pin 11 |
| 9 | RESET | RF_RST from the SoC (100 Ω) | **Active-high** reset, as the SX1255: floating = run, pulled high ≥ 100 µs = reset `[DS]`. Internal pull-down; inverted to `rst_n` and ORed with the on-chip power-on reset |
| 10 | CLK_OUT | I2S_CLK | I2S BCLK (master) / BCLK in (slave) |
| 11 | CLK_IN | n.c. | **`ref_36` strap**: sampled while RESET is active; internal pull-down, so n.c. = 32 MHz (LinHT). High = 36 MHz |
| 12 | Q_IN | n.c. | Spare |
| 13 | I_IN | I2S data to chip | I2S data in (TX IQ) |
| 14 | Q_OUT | n.c. | Spare (`valid_iq`) |
| 15 | I_OUT | I2S data from chip | I2S data out (RX IQ) |
| 16, 32 | VBAT2, VBAT3 | +3V3 | Supply |
| 17–20 | SCK, MISO, MOSI, NSS | SPI | SPI (unchanged frame format) |
| 21 | DIO0 | n.c. | `clk_req` |
| 22 | DIO1 | n.c. | **IRQ out**, active-low (PLL unlock, AGC, RSSI), enabled by register; repeater backplane c1 |
| 23 | DIO2 | I2S_WS | I2S word select (LRCLK) |
| 24 | DIO3 | n.c. | **PTT gate in**, internal pull-down; ignored unless `ptt_pin_en` is set (default: TX over SPI only, as the SX1255); repeater backplane c2 |
| 25 | VR_ANA2 | 100 nF | Second analogue regulator decoupling (TX/DAC) |
| 27 | RF_IN | L-match → 2× PE4312 | **RX input**, single-ended 50 Ω, 130–175 and 400–480 MHz |
| 29 | RF_ON | 27 pF to GND | **TX output −** (AC-grounded on LinHT) |
| 30 | RF_OP | → GRF5604 input match | **TX output +** |

Digital back end changes for Option P: **block-level part done 2026-10-19** (`ref_36` latched at reset from pin 11, PTT gate on DIO3 with `CTRL[3]`, IRQ on DIO1 with `IRQ_EN`, CHIP_ID 0x13; `rtl/digital/notes.md`). The I2S format needs no change (Philips, confirmed on the LinHT). Still at chip top: I2S word select routed to DIO2, `clk_req` to DIO0, the active-high RESET pin inverted and combined with the power-on reset.

---

## 3. Receiver

LinHT front end before the RFIC `[SCH]`: antenna → LFCN-490+ low-pass → SKY13330 T/R switch → 2× PE4312 (0–63 dB, 0.5 dB steps; 2.2–3 dB insertion loss) → L-match → RF_IN. About 3.5–4 dB of loss precedes the chip.

| Parameter | SX1255 `[DS]` | Requirement / target | Basis |
|---|---|---|---|
| Frequency | 400–510 MHz | **130–175 and 400–480 MHz** | `decisions.md` 2026-10-18 |
| Input | 50 Ω or 200 Ω selectable, single-ended | 50 Ω single-ended, S11 < −10 dB across each band with one external match per band `[PROP]` | LinHT board |
| Noise figure, max gain | 4.5 dB | **≤ 4 dB** `[PROP]` | LinHT system NF ≈ 4 dB loss + chip NF ≈ 8 dB; must not be worse than SX1255 |
| Gain control | ≈ 70 dB (LNA 48 dB in 6/12 dB steps + 32 dB PGA in 2 dB) | **≥ 48 dB** total `[PROP]` | The PE4312s add 63 dB externally; the Σ-Δ ADC dynamic range (≥ 97–104 dB, `[DER]` R7) covers the rest |
| IIP3, max gain | −28 to −23 dBm | **≥ −20 dBm** `[PROP]` | Repeater: own TX leakage −43/−36 dBm plus a second signal |
| Input P1dB, max gain | not specified | **≥ −30 dBm** `[PROP]` | Own TX at −36 dBm (25 W, 80 dB duplexer) must not compress, `[DER]` R1/R6 |
| Reciprocal mixing (LO noise at duplex offset) | — | ≤ −139 dBc/Hz at the mixer LO, 25 W case | `[DER]` R4 |
| VHF 3 × LO response | — | ≥ 60 dB rejection (harmonic-reject mixer) plus board preselection `[PROP]` | `[DER]` §7.3 |
| ADC | (SX1255: Σ-Δ, 1-bit, 32–36 MS/s) | 1-bit Σ-Δ at the reference rate, DR ≥ 101 dB in 12.5 kHz (25 W) / 94 dB (5 W), attenuator baseline; anti-alias ≥ 40 dB at ±8/9 MHz, ≥ 70 dB at ±32/36 MHz | `[DER]` R7, §7.6; digital chain already built for it |
| Max input | 0 dBm operating, +6 dBm absolute | Same | `[DS]` |

**Repeater modules (decided 2026-10-19):** the baseline module uses the **same RX front end as the LinHT** (2× PE4312 before the chip) — simplest, and the attenuators let a strong site trade sensitivity for blocking. A module designer may replace them with an external LNA (NF ≈ 1 dB, gain 15–20 dB, which raises the linearity the chip sees by that gain); the chip requirements below cover the baseline.

With about 4 dB of loss in front of a 4 dB chip, the baseline system NF is **≈ 8 dB**, not the 5 dB assumed in `spec/derived-limits.md`. Re-derived for 8 dB (noise floor −125 dBm in 12.5 kHz, 1 dB desense threshold −131 dBm = −172 dBm/Hz at the module RX port; 80 dB duplexer):

| | 5 W | 25 W | Was (NF 5 dB, 25 W) |
|---|---|---|---|
| R2 TX noise at duplex offset, whole chain | ≤ −129 dBc/Hz | ≤ −136 dBc/Hz | −139 |
| R3 same, RFIC output (R2 − 10 dB) | ≤ −139 dBc/Hz | ≤ −146 dBc/Hz | −149 |
| R4 LO phase noise at duplex offset | ≤ −129 dBc/Hz | ≤ −136 dBc/Hz | −139 |
| R5 decimator rejection, on-channel duplex alias | ≥ 88 dB | ≥ 95 dB (keep the 100 dB test limit) | 98 |
| R7 ADC DR in 12.5 kHz | ≥ 94 dB | ≥ 101 dB | 104 |

Sensitivity of the baseline: about −117 dBm for 12 dB SINAD (FM, 12.5 kHz), against roughly −119 to −121 dBm for a commercial repeater receiver; the LNA option recovers that. `spec/derived-limits.md` §8 has the same two-case table.

---

## 4. Transmitter

LinHT path after the RFIC `[SCH]`: RF_OP → high-pass T match (33 p / 10 nH / 33 p) → **GRF5604** (two-stage, 100–600 MHz, up to 6 W Psat at 5 V `[DS]`) → output match tuned for ~435 MHz → SKY13330 → LFCN-490+ → antenna. **No attenuators in the TX path** — TX power is set inside the transceiver.

| Parameter | SX1255 `[DS]` | Requirement / target | Basis |
|---|---|---|---|
| Nominal output | −5 dBm average (as used) | **−5 dBm** average, single-ended into the existing match (differential 100 Ω also allowed) | Reuse GRF5604 and its match |
| Saturated output | +4 to +7 dBm | ≥ +4 dBm | Headroom |
| Output P1dB | +2 to +5 dBm | **≥ +2 dBm** | 7 dB back-off at −5 dBm |
| OIP3 at −5 dBm | ≥ +13 dBm (typ. +16) | **≥ +13 dBm** | Linear modes, calibration |
| Gain control | 0 to −9 dB (DAC, 3 dB steps) + ≈ 30 dB (mixer, 2 dB steps) | **≥ 30 dB analogue, ≤ 2 dB steps, after the DAC reconstruction filter** | Lowering power must lower noise too; digital scaling breaks R3 |
| Noise at duplex offset (600 kHz, 2 MHz) | −135 dBc/Hz typ. at 10 MHz | **≤ −146 dBc/Hz** at the RFIC output (25 W, attenuator baseline; −149 with the LNA option) | R3, section 3 |
| Reconstruction filter | — | ≥ 51 dB at 600 kHz and ≥ 71 dB at 2 MHz for IQ rates ≤ 200 kHz (+3 dB with the LNA option); selectable corner | `[DER]` §4, re-derived |
| Image / carrier leakage | LO leakage −8 dBc before calibration | Image ≥ 40 dB after host calibration; LO leakage ≤ −30 dBc before calibration `[PROP]` | Host calibration replaces on-chip DC/IQ registers |
| Harmonics at RFIC output | — | ≤ −30 dBc `[PROP]`; the board filter takes the rest to the regulatory 50–57 dBc | `[DER]` R8 |

---

## 5. Local oscillator and synthesizer

| Parameter | SX1255 `[DS]` | Requirement / target | Basis |
|---|---|---|---|
| VCO / division | (400–510 MHz only) | VCO 3.12–4.20 GHz; ÷8 UHF, ÷24 VHF; quadrature from the last ÷2 | `band_sel` in RTL |
| Phase noise at the LO | −108 dBc/Hz @ 100 kHz, −128 @ 1 MHz | ≤ −136 dBc/Hz at 600 kHz (VHF) and at 2 MHz (UHF), 25 W attenuator baseline (−139 with the LNA option); ≈ −108 / −118 dBc/Hz at the VCO after division credit | R4, section 3 |
| Frequency resolution | Fxosc / 2¹⁹ ≈ 31–34 Hz | **≤ 10 Hz** at RF; < 1 Hz preferred so GNSS/ppm correction can be done in the LO | Frequency-discipline note |
| Spurs (reference and fractional) | — | At the duplex offset ≤ −95 dBc (25 W) / ≤ −88 dBc (5 W), RX and TX; elsewhere TX ≤ −67 dBc design target (regulatory −57 dBc at 25 W), RX ≤ −84 dBc `[PROP]` | `spec/derived-limits.md` §9 |
| Synthesizer wake-up | 50 µs typ (150 max) | ≤ 150 µs | DMR TDMA turnaround |
| TX/RX turnaround | 120 µs TX wake-up | ≤ 0.5 ms including PLL settling `[PROP]` | DMR 30 ms slots |
| Reference | 32–36.864 MHz crystal or TCXO | 32 MHz or 36 MHz TCXO on XTB; host chooses per channel (`[DER]` §7.2) | LinHT: 32 MHz only |

---

## 6. Power and environment

| Parameter | SX1255 `[DS]` | Target `[PROP]` |
|---|---|---|
| Supply | 2.7–3.6 V (3.9 V abs. max) | Same |
| Sleep | 0.2 µA | ≤ 1 µA |
| Standby (reference running) | 1.15 mA | ≤ 1.5 mA |
| RX | 18 mA typ | ≤ 25 mA (the 3.1–4.2 GHz VCO costs more than the SX1255 LO) |
| TX at −5 dBm | 60 mA typ | ≤ 60 mA |
| Temperature | −40 to +85 °C | −40 to +85 °C ambient (the digital block is already signed off to 125 °C junction) |
| ESD | — | ±2 kV HBM all pins; RF pins ≥ ±1 kV HBM |
| Power-on reset | Internal POR; SPI usable 10 ms after POR, 5 ms after a manual reset `[DS]` | **On-chip POR required**: on the LinHT the RESET pin floats at power-up, so the board no longer provides the "`rst_n` low at power-up" that the digital block assumes today. SPI usable ≤ 5 ms after POR and after a manual reset, so existing host timing still works |

---

## 7. Block allocation (first cut, for the Phase 3/4 budget study)

| Block | Key targets |
|---|---|
| LNA (with gain steps) | NF ≤ 2.5 dB, gain ≈ 20 dB, steps 0 / −6 / −12 / −24 dB, 50 Ω input on both bands with external match |
| Mixer (passive, quadrature, harmonic-reject on VHF) | IIP3 high enough for the chip-level ≥ −20 dBm; 3 × LO rejection ≥ 60 dB on VHF |
| TIA + anti-alias filter | Anti-alias ≥ 40 dB at ±8/9 MHz together with the ADC's inherent filtering |
| Σ-Δ ADC (1-bit output) | DR ≥ 101 dB in 12.5 kHz (104 with the LNA option), stable with the blocker of R1, output = existing digital chain input |
| Σ-Δ DAC + reconstruction filter | Selectable corner per IQ rate; ≥ 54 / 74 dB at 600 kHz / 2 MHz |
| IQ modulator + TX gain control | ≥ 30 dB in ≤ 2 dB steps after the filter |
| PA driver | −5 dBm average, P1dB ≥ +2 dBm, single-ended or differential output |
| PLL (VCO, dividers, fractional-N) | Section 5 |
| Regulators | VR_PA, VR_ANA1, VR_ANA2, VR_DIG from 2.7–3.6 V |

The study that confirms or moves these numbers is "tier 2" in the plan: Σ-Δ ADC architecture and a system budget model of the full RX chain.

---

## 8. Board-level work outside the RFIC

**LinHT (VHF needs a board revision):**
- VHF TX harmonic filter: the LFCN-490+ passes the 2nd and 3rd harmonics of 2 m; add a VHF low-pass and a band switch. The small LTCC low-passes (LFCN-160+, LFCN-180+) reject the 2nd harmonic by only about 7–18 dB, so the VHF filter is a discrete elliptic LC design; full 130–175 MHz coverage needs notches or two sub-bands. A second SKY13330 (about 7 W, 1.8 V control) can be the PA-side band switch at 5 W. Parts: [docs/rf-switches-and-filters.md](../docs/rf-switches-and-filters.md).
- PA output match: second matched path (same GRF5604, VHF match) or a switched match.
- RX input match for VHF.
- Dual-band antenna.

**Repeater RF modules:**
- One band per module: one PA match, one harmonic filter, one RX match.
- RX and TX on separate RFICs sharing one reference (`[DER]`), **on one duplex module in one slot** (TX RFIC as I2S slave; `docs/RF-modules.md` §7.1); cavity duplexer; optional external LNA (section 3).
- 25 W needs a PA stage after the GRF5604 (6 W max).

---

## 9. Verification plan

- Each requirement above becomes a CACE parameter with a limit, run across the PDK corners and −40 to +85 °C.
- Phase noise: VACASK `pnoise` in oscillator mode, validated 2026-10-19 (`analog/pn-validation/`: 0.19 dB against the exact LC result, 0.5 dB against transient noise on an SG13G2 oscillator) at `pss_minpts` ≥ 8000. Flicker region still to be validated.
- EM for the VCO tank and any on-chip RF inductors (openEMS/Palace with open/short de-embedding, as in arXiv:2607.08852).
- Board-level co-simulation with S-parameter models of the GRF5604, PE4312, SKY13330 and LFCN-490+ (scikit-rf).

---

## 10. Open items

1. ~~Option P or N~~ — **P**, decided 2026-10-19.
2. ~~LinHT IQ rate~~ — 500 kSa/s, 16-bit I/Q as L/R (M17 project blog, 2025-09-30). Matches the chip's maximum rate. The host needs an `sx1255-spi` equivalent for the new register map.
3. ~~`ref_36` on Option P~~ — pin 11 (CLK_IN) strap, sampled at reset, pull-down = 32 MHz (decided 2026-10-19). DIO1 = IRQ and DIO3 = PTT gate decided at the same time.
4. ~~Reset polarity~~ — active-high, floating in normal operation (SX1255 datasheet §6.2; owner confirms the LinHT pulls it high to reset). Needs an internal pull-down, an inverter to `rst_n`, and an on-chip POR (section 6).
5. ~~I2S alignment and master/slave on the LinHT~~ — confirmed in `meta-linht-hardware` (`sbc-mcm-imx93.dtsi`, read 2026-10-19): simple-audio-card `format = "i2s"`, `bitclock-master` and `frame-master` = the SX1255 on both the RX and TX links; SAI1 on TX_BCLK, TX_SYNC, TXD0, RXD0. Philips I2S with the transceiver as master — the chip's default.
6. ~~Reference-spur requirement~~ — derived in `spec/derived-limits.md` §9 (2026-10-19). Integer-boundary spurs land on the duplex offset on 2 channels on 2 m and 5 on 70 cm with either reference (e.g. 432.250 MHz); the Phase 2 model (`spec/phase2-plan.md`) decides whether the PLL meets the limit there.
7. ~~Repeater module RX~~ — attenuators as baseline, LNA allowed as a module-designer option (decided 2026-10-19). `spec/derived-limits.md` §8 updated.
8. Confirm the SX1255 datasheet values marked `[DS]` that were read from extracted text (NF and IIP3 columns).
