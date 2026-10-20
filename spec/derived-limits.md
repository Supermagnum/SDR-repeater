# Derived RX/TX limits at the repeater duplex offsets

Status: draft for human review. This file replaces the provisional limits (open item 5: "RX alias 45 dB, TX OOB").
Numbers: `tools/derive_limits.py`. Input data: Norwegian repeater list `repeaters_merged.csv` (402 rows).

## 1. Duplex offsets in use (Norway)

Offset is rx − tx, i.e. repeater input minus repeater output.

| Band | Entries | Offsets seen | Design offset |
|---|---|---|---|
| 2 m | 274 | 0 (146, mostly APRS/simplex), −600 kHz (112), +600 kHz (3), crossband (7) | **600 kHz** |
| 70 cm | 121 | −2 MHz (104), 0 (13), +2 MHz (3) | **2 MHz** |
| 23 cm | 2 | −6 MHz (2) | 6 MHz (deferred) |

The IARU 7.6 MHz 70 cm split is not used in the list.

By repeater type, the list has 92 FM on 2 m and 45 FM on 70 cm. On 70 cm there are 30 DMR, 9 D-STAR and 6 FM/DMR, plus some C4FM. All are 12.5 kHz class channels.

## 2. Assumptions

A reviewer may change these. Every limit below scales 1:1 in dB with them.

| Symbol | Value | Note |
|---|---|---|
| P | 37 dBm (5 W) baseline; **44 dBm (25 W) design case** | output at the antenna port |
| I | 80 dB | TX→RX isolation of the cavity duplexer at 600 kHz (2 m) and at 2 MHz (70 cm). Typical 6-cavity units give 80–90 dB. Confirmed by the owner: RX and TX share one antenna through a duplexer on both bands. |
| NF | 5 dB | system RX noise figure, **LNA option**. The baseline front end (2× PE4312 attenuators before the chip) gives ≈ 8 dB; §8 re-derives the limits for it |
| B | 12.5 kHz | channel noise bandwidth |
| N | −174 + 41 + 5 = **−128 dBm** | RX noise floor in B |
| Desense | ≤ 1 dB | interference ≤ N − 6 dB = −134 dBm, i.e. **−175 dBm/Hz** at the RX input |
| RFIC share | 10 dB | the RFIC may use the TX budget minus 10 dB; the rest is left for the upconverter/PA |
| Tuning | zero-IF | the wanted channel sits at DC in the IQ stream |

Use cases:
- **Repeater:** RX and TX run at the same time. Two RFICs are needed, because the chip shares the half-band between RX and TX.
- **LinHT:** simplex or half-duplex. The duplex-offset limits do not apply to it.

## 3. Requirements

| # | Requirement | 5 W | 25 W | Formula |
|---|---|---|---|---|
| R1 | Own-TX blocker at the RX input | −43 dBm | −36 dBm | P − I |
| R2 | TX noise at the duplex offset (whole TX chain) | ≤ −132 dBc/Hz | ≤ **−139 dBc/Hz** | −175 + I − P |
| R3 | TX noise at the offset, RFIC output (R2 − 10 dB) | ≤ −142 dBc/Hz | ≤ **−149 dBc/Hz** | |
| R4 | RX LO phase noise at the offset (reciprocal mixing) | ≤ −132 dBc/Hz | ≤ **−139 dBc/Hz** | −175 − R1 |
| R5 | Decimator rejection of a duplex-offset band that aliases onto the wanted channel | ≥ 91 dB | ≥ **98 dB → use 100 dB** | R1 − (−134) |
| R6 | RX ADC: no overload with R1 present, plus 6 dB back-off | FS ≥ −37 dBm | FS ≥ −30 dBm | analog, Phase 3 |
| R7 | RX ADC dynamic range in B (FS to −134 dBm) | ≥ 97 dB | ≥ 104 dB | analog, Phase 3 |
| R8 | Regulatory spurious emissions (ITU RR App. 3, > 30 MHz; 100 kHz ref. BW) | ≥ 50 dBc | ≥ 57 dBc | 43 + 10 log P (W); 70 dBc whichever is less stringent |

R2 is 30+ dB tighter than R8. **Self-interference sets the TX limit, not regulation.**

## 4. Present design against the requirements

### RX: R5

The model of the ideal decimator response is in the table below. It covers a blocker band of ±5.5 kHz around the offset.

| Output rate | 600 kHz (2 m) | 2 MHz (70 cm) |
|---|---|---|
| 25 / 50 / 100 kHz | aliases on-channel, ≥ 162 dB (lands in a CIC null) | on-channel, ≥ 203 dB |
| 200 kHz | on-channel, 106 dB (48 dB bit_front+CIC+comp, 58 dB half-band at fs_in/2): meets R5 | on-channel, ≥ 203 dB |
| 500 kHz | lands at −100 kHz, off-channel. The host must reject it by ≥ 100 dB. 16-bit IQ is enough: the blocker is 75 dB above the floor in 500 kHz. | on-channel, ≥ 203 dB |

How this behaves:
- **Every Norwegian duplex offset is an exact multiple of the IQ rate.** So the own-TX blocker always aliases onto the wanted channel, wherever the host places the channel.
- It is harmless only because, at zero-IF, those frequencies sit in the CIC nulls.
- **Consequence:** the repeater must keep the channel at DC. With offset tuning the null protection disappears.
- The ideal-response numbers are not the real limit. The 16-bit output floor (≈ −98 dBFS) and the analog front end (R4, R6, R7) are.

Half-band (31 taps from `fir_seq.sv`): 57 dB stopband from 0.30·fs_in, 57.5 dB at fs_in/2. **R5 is met at every rate.** Reproduce with `python3 tools/derive_limits.py --no-tx` (the RTL taps are built in).

### TX: R3

This figure comes from a generic model: a 2nd-order 1-bit Σ-Δ at 32 MHz, with a −6 dBFS tone.

| Offset | Bitstream noise | R3 (25 W) | Analog reconstruction filter needed |
|---|---|---|---|
| 600 kHz | −102 dBc/Hz | −149 | ≥ 47 dB (≥ 54 dB with the test limit below) |
| 2 MHz | −81 dBc/Hz | −149 | ≥ 68 dB (≥ 74 dB with the test limit below) |

**The digital TX alone cannot meet the duplex requirement.** This is expected for a 1-bit DAC: the shaped noise rises with offset. Without a filter it also fails R8 at 25 W (−102 dBc/Hz + 50 dB = −52 dBc in 100 kHz).

A selectable baseband reconstruction low-pass (4th-order Butterworth, fc chosen per rate) closes the gap. That makes it a Phase 3 analog requirement:

| TX IQ rate | fc | Rejection at 600 kHz | Rejection at 2 MHz | Repeater duty |
|---|---|---|---|---|
| ≤ 100 kHz | 50 kHz | 86 dB | 128 dB | OK |
| 200 kHz | 100 kHz | 62 dB | 104 dB | OK |
| 500 kHz | 250 kHz | 30 dB | 72 dB | **2 m: no. 70 cm: marginal.** |

Decision recorded: **500 kHz TX is for simplex/LinHT use only.** A repeater transmits at ≤ 200 kHz IQ. This is consistent with Decision B (LinHT prefers 100 or 500 kHz; it has no duplex constraint).

## 5. Test and sign-off limits (replace the provisional ones)

| Test | Old | New | Comment |
|---|---|---|---|
| RX alias, duplex offset (tone at 600 kHz + 3 kHz and 2 MHz + 3 kHz, ≤ 200 kHz rates) | — | alias product ≥ 90 dB below an equal in-band tone | 90 dB rather than 100 dB because of the 16-bit output floor; R5 is shown by the model in §4 |
| RX alias, wideband (whole delivered band, host-side multichannel/LinHT) | 45 dB (provisional) | **45 dB, confirmed as the wideband limit** | not on-channel, so R5 does not apply |
| RX alias, on-channel from fs_out ± 5.5 kHz | — | ≥ 65 dB | model 68–71 dB (ideal arithmetic); 70 dB would need a longer half-band, not worth the area (open item 1) |
| TX bitstream noise at 600 kHz | provisional | ≤ −95 dBc/Hz | model −102; the rest is the Phase 3 filter |
| TX bitstream noise at 2 MHz | provisional | ≤ −75 dBc/Hz | model −81 |
| Phase 3 analog | — | R4, R6, R7, reconstruction filter per §4 | go into `spec/` for the analog phase |

## 6. For the reviewer

- **Confirm the assumptions in §2:** duplexer isolation and maximum TX power. (Shared antenna through a duplexer is confirmed.)
- **Confirm R8 against current Nkom licence conditions.** The value here is taken from ITU RR Appendix 3.
- Replace the TX model with a bitstream captured from `tx_image_and_noise`.

## 7. Frequency coverage: 130–175 MHz and 400–480 MHz

Owner requirement: the chip must tune **130–175 MHz (VHF)** and **400–480 MHz (UHF)**. This covers amateur bands, land mobile and PMR446. It replaces the amateur-only baseline: wide tuning is no longer a Phase 2 option.

### 7.1 Digital backend

No change. The backend works at baseband, and nothing in the RTL or the layout depends on the RF frequency.

### 7.2 Reference clock choice (32 vs 36 MHz)

Harmonics of the core clock fall inside the coverage:

| Clock | Harmonics in VHF | Harmonics in UHF |
|---|---|---|
| 32 MHz | 160 | 416, 448, 480 |
| 36 MHz | **144**, 168 | **432**, 468 |

Rule: the host selects the clock whose nearest harmonic is farthest from the tuned channel.
- **2 m (144–146) and 70 cm (430–440):** use 32 MHz.
- **PMR446 and the 160 / 416 / 448 MHz regions:** use 36 MHz.

The firmware should hold this as a table. It is the reason both clocks exist.

### 7.3 VHF mixer harmonic response

A switching mixer tuned to 130–175 MHz also receives at 3 × LO = 390–525 MHz. That range overlaps the UHF band.

Phase 3 requirement: a harmonic-reject mixer, a switched VHF preselector, or both.

**Frequency-planning rule for the multiband repeater:** never pair a UHF TX within ±12.5 kHz of 3 × a VHF RX frequency. Example: VHF RX 145.000 MHz with UHF TX 435.000 MHz.
- Through a diplexer (about 50 dB), that UHF carrier arrives at roughly −6 dBm.
- It would need about 128 dB of rejection, which no on-chip measure provides.
- The same applies the other way: the 3rd harmonic of a VHF TX must not land on a UHF RX channel.

### 7.4 LO plan (matches `band_sel` in the RTL)

The RTL already defines the divider select: `band_sel` 0 = ÷8 (UHF), 1 = ÷24 (VHF).
With one VCO at **3.12–4.20 GHz**:
- **UHF:** ÷8 covers 400–480 MHz from 3.20–3.84 GHz.
- **VHF:** ÷24 covers 130–175 MHz from 3.12–4.20 GHz. Since D4 (2026-10-19) the ÷24 is built as ÷3 then an 8-phase ÷8 (Johnson counter), giving 45° phases for the harmonic-reject mixer; UHF ÷8 is ÷2 then a quadrature ÷4. Topology memo: `spec/lo-divider-topology.md`. (Superseded text: "÷12 then ÷2, the final ÷2 provides I/Q".)

The 30 % tuning range needs a switched-capacitor bank or two VCO cores. The divider ratios are the RF engineer's choice; changing them only changes the comment on `band_sel`.

### 7.5 Other duplex offsets

Land-mobile offsets on 400–480 MHz (for example 10 MHz) are multiples of 100 kHz. They therefore land in the CIC nulls at the 25 and 50 kHz rates, like the amateur offsets do.

Two other cases:
- An offset that is an odd multiple of the IQ rate depends on the half-band.
- Any other offset lands off-channel, and the host filters it.

### 7.6 Far-out aliases

The digital chain gives no protection at these offsets:

| Offset | Digital rejection | Phase 3 analog anti-alias requirement |
|---|---|---|
| ± clk (32 / 36 MHz) | 0 dB | ≥ 70 dB |
| ± clk/4 (8 / 9 MHz) | 31 dB (bit_front only) | ≥ 40 dB |

A continuous-time Σ-Δ ADC provides part of this rejection inherently. Wide coverage makes this more important: strong land-mobile and paging carriers sit within ±8 MHz of many channels.

### 7.7 Regulatory note

- **PMR446:** licence-free only with type-approved equipment that has an integral antenna and at most 0.5 W ERP. Repeaters are not allowed on PMR446.
- **Land mobile:** needs type-approved equipment and a licence.

The chip can cover these bands, but legal use depends on how the finished radio is certified.

## 8. Receiver front-end cases (decided 2026-10-19)

The repeater modules default to the LinHT receive front end: 2× PE4312 step attenuators (2.2–3 dB insertion loss) in front of the RFIC. With about 4 dB of loss ahead of a chip with a 4 dB noise figure, the **baseline system NF is ≈ 8 dB**. A module designer may replace the attenuators with an external LNA (NF ≈ 1 dB, 15–20 dB gain), which gives the 5 dB case used in §2–5.

Baseline (NF 8 dB): noise floor −125 dBm in 12.5 kHz; 1 dB desense threshold −131 dBm = −172 dBm/Hz at the module RX port; 80 dB duplexer.

| | 5 W | 25 W | LNA option, 25 W |
|---|---|---|---|
| R2 TX noise at duplex offset, whole chain | ≤ −129 dBc/Hz | ≤ −136 dBc/Hz | −139 |
| R3 same, RFIC output (R2 − 10 dB) | ≤ −139 dBc/Hz | ≤ −146 dBc/Hz | −149 |
| R4 LO phase noise at duplex offset | ≤ −129 dBc/Hz | ≤ −136 dBc/Hz | −139 |
| R5 decimator rejection, on-channel duplex alias | ≥ 88 dB | ≥ 95 dB | 98 (the test keeps 100 dB) |
| R7 ADC dynamic range in 12.5 kHz | ≥ 94 dB | ≥ 101 dB | 104 |
| TX reconstruction filter at 600 kHz / 2 MHz | | ≥ 51 / 71 dB | 54 / 74 |

Baseline sensitivity is about −117 dBm for 12 dB SINAD (FM, 12.5 kHz); the LNA option recovers about 3 dB. The attenuators let a strong site trade sensitivity for blocking. The RFIC is specified for the baseline, which is also the harder case for its linearity (`spec/rf-frontend.md` §3).

## 9. PLL spurs (derived 2026-10-19)

Discrete spurs (dBc, total power of the spur relative to the carrier), as opposed to the noise limits in dBc/Hz above. Baseline receiver (§8): 1 dB desense threshold −131 dBm in 12.5 kHz at the module RX port; 80 dB duplexer; own TX at the RX input R1 = −43 dBm (5 W) / −36 dBm (25 W). With the LNA option (threshold −134 dBm) every duplex-offset limit is 3 dB tighter.

| # | Spur | 5 W | 25 W | Derivation |
|---|---|---|---|---|
| S1 | RX LO spur at the duplex offset (600 kHz on 2 m, 2 MHz on 70 cm, ± half a channel) — mixes the own TX onto the channel | ≤ **−88 dBc** | ≤ **−95 dBc** | −131 − R1 |
| S2 | TX spur at the duplex offset — lands in the own RX through the duplexer | ≤ **−88 dBc** | ≤ **−95 dBc** | −131 + I − P |
| S3 | TX spur anywhere else outside the necessary bandwidth, incl. reference spurs at ±32 / ±36 MHz (in the 130–175 MHz passband at VHF, so the harmonic filter does not help) | ≤ −50 dBc | ≤ −57 dBc | R8 (ITU RR App. 3); **design target −67 dBc at the RFIC output**, 10 dB margin |
| S4 | RX LO spur at any other offset ≥ 1 MHz — reciprocal mixing with a strong off-channel signal | ≤ −84 dBc `[PROP]` | ≤ −84 dBc `[PROP]` | an 84 dB blocking class: a −33 dBm blocker may raise the channel to the −117 dBm sensitivity level; confirm against the applicable standard |
| S5 | LO spur in the adjacent channels (±12.5 / ±25 kHz) | ≤ −65 dBc `[PROP]` | ≤ −65 dBc `[PROP]` | adjacent-channel selectivity and adjacent-channel power of the order of 60–70 dB; confirm |

**Where fractional-N spurs land** (corrected 2026-10-19 — the first version divided the offset by N, which is wrong). The integer-boundary spur sits at d = |f_VCO − k·f_ref| from the carrier, the VCO's distance to the nearest multiple of the reference. Frequency division does **not** change that offset in hertz (it lowers the level by 20·log10(N)), so the spur appears at **d** from the RF carrier too (as in `spec/integer-boundary-spurs.md`). It hits the duplex offset when the RF carrier is 600 kHz / 24 = **25 kHz** (2 m) or 2 MHz / 8 = **250 kHz** (70 cm) from a boundary channel k·f_ref / N. For 12.5 kHz channels in 144–146 MHz and 430–440 MHz (spur or its 2nd/3rd harmonic within ±6.25 kHz of the duplex offset):

| Band | Channels | Hit with 32 MHz | Hit with 36 MHz | Hit with both |
|---|---|---|---|---|
| 2 m (600 kHz) | 161 | 3 | 6 | 2: 144.0125, 144.0250 MHz |
| 70 cm (2 MHz) | 801 | 10 | 8 | 5: 431.750, 431.875, 432.125, 432.250, 436.250 MHz |

Example: 432.250 MHz → VCO 3458 MHz, 2 MHz from 108 × 32 MHz = 96 × 36 MHz = 3456 MHz, so the boundary spur lands on the 2 MHz duplex offset with either reference.

- The host's per-channel choice of 32 or 36 MHz (§7.2) should also avoid these hits; it removes most of them.
- For the remaining channels the spur must meet S1/S2 after the 20·log10(N) division credit (27.6 dB VHF, 18.1 dB UHF) and the loop-filter attenuation at 600 kHz / 2 MHz. The PLL model in `spec/phase2-plan.md` (step P2.2) decides whether that holds or whether those channels are avoided by the host.
- Reference spurs appear at ±f_ref (±32 / ±36 MHz) at RF, as S3 says; there the loop filter attenuates strongly.

Count: for each channel f, d = |f·N − round(f·N/f_ref)·f_ref|; hit if m·d (m = 1…3) is within ±6.25 kHz of the duplex offset. The per-channel rule belongs in the host's channel planner next to the clock-harmonic table.
