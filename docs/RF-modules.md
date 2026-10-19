# SDR Repeater — RF Module and RFIC Specification

**Document:** Module RF Hardware Design Specification  
**Revision:** 0.4.2  
**Date:** October 2026  
**Relates to:** SDR Multiband Repeater System Design v1.9  

**Status:** This document records **design ideas and a target architecture** — not committed tapeout data, BOMs, or shipping hardware. **No fabrication is planned in this phase** (Section 11). The binding RFIC requirements are in [spec/rf-frontend.md](../spec/rf-frontend.md); the limits behind them in [spec/derived-limits.md](../spec/derived-limits.md); the design status in [HANDOFF.md](HANDOFF.md). Where this document and those files disagree, those files win.

**Change summary (r0.3 → r0.4):** HT13G-M is now **one band-switched chain** (130–175 MHz and 400–480 MHz) on an **SX1255-compatible pin-out**, so the same chip is a drop-in for the LinHT. TX output is **−5 dBm** (was 0 dBm) into a GRF5604 driver. The RFIC reset is **active-high with an on-chip power-on reset**; the backplane keeps `RFIC_RESET_N` and the module inverts it. **DC-offset and IQ-imbalance correction moved to the host.** Reference 32 or 36 MHz. **Attenuators are the default RX front end**; the external LNA is optional. A same-band repeater needs **separate RX and TX RFICs**. Backplane pin c5 (`ANT_SW`) is now **VHF/UHF band-path select**. The host side of the backplane is the ECP5 interface card in the Milk-V Megrez (host as secondary platform). The MPW submission plan is replaced by "no fabrication in this phase". HT13G-S (23 cm) is deferred and not updated.

**Change (r0.4 → r0.4.1):** T/R switch corrected — the SKY13351 (about 1 W) is replaced by the PE42820 (5 W variant) and a PIN-diode switch (20 W variant). Filter-part limits added. Parts survey for 5 W, 20 W and 100 W in [rf-switches-and-filters.md](rf-switches-and-filters.md).

**Change (r0.4.1 → r0.4.2):** Interface open items closed: `ref_36` strap on pin 11, hardware PTT gate on DIO3 (backplane c2), IRQ on DIO1 (backplane c1), LinHT I2S format confirmed. A same-band repeater is **one duplex module** with two RFICs. Five slots, A–E. VHF harmonic filter for full 130–175 MHz in [docs/rf-switches-and-filters.md](rf-switches-and-filters.md).

**Earlier change (r0.2 → r0.3):** PA output power updated to 5 W standard / 20 W maximum across all bands. PA candidate parts, harmonic filter component ratings, +12 V PA rail current budget, duty cycle firmware limit, and risk register updated accordingly.

**LinHT:** HT13G-M is pin- and SPI-frame-compatible with the Semtech SX1255 used in the [LinHT](https://linux-radio.eu/) handheld: same footprint, 32 MHz reference, 500 kSa/s 16-bit IQ (0.5 MHz of RF spectrum), −5 dBm into the existing GRF5604 PA. VHF on the LinHT needs a board revision ([spec/rf-frontend.md](../spec/rf-frontend.md) §8).

---

## Table of Contents

1. [Design Context and Rationale](#1-design-context-and-rationale)
2. [Why a Custom RFIC](#2-why-a-custom-rfic)
   - [LinHT and the SX1255 path](#linht-and-the-sx1255-path)
   - [Wideband integrated transceivers (LMS7002M, AD9361)](#wideband-integrated-transceivers-lms7002m-ad9361)
3. [Fabrication Process: IHP SG13G2](#3-fabrication-process-ihp-sg13g2)
4. [RFIC Family Overview](#4-rfic-family-overview)
5. [HT13G-M RFIC — 2 m / 70 cm Module](#5-ht13g-m-rfic--2-m--70-cm-module)
6. [HT13G-S RFIC — 23 cm Module](#6-ht13g-s-rfic--23-cm-module)
7. [RF Signal Chain — Per Module](#7-rf-signal-chain--per-module)
8. [Module PCB Architecture](#8-module-pcb-architecture)
9. [Backplane Interface](#9-backplane-interface)
10. [Software Interface: ZeroMQ IPC](#10-software-interface-zeromq-ipc)
11. [Path to Silicon](#11-path-to-silicon)
12. [Risk Register](#12-risk-register)
13. [Open Licensing](#13-open-licensing)

---

## 1. Design Context and Rationale

The repeater system described in the companion document uses up to five pluggable radio modules on a 3U Eurocard backplane (IEC 60297), in slots **A** through **E**. Each slot has a fixed **module address** (letter). The band a module covers comes from the module PCB and EEPROM, not from the slot letter — two slots can hold the same band (for example 70 cm in B and 70 cm in C).

Example default install:

- Slot A — 2 metre: 144–146 MHz, 500 kHz IQ bandwidth, 5 W TX standard / 20 W TX maximum
- Slot B — 70 cm: 432–438 MHz, 500 kHz IQ bandwidth, 5 W TX standard / 20 W TX maximum
- Slot C — 23 cm: 1240–1258 MHz, 500 kHz IQ bandwidth, 5 W TX standard / 20 W TX maximum (or a second 70 cm link module)
- Slots D and E — spare or expansion

Each module is a self-contained PCB that plugs into a DIN 41612 Eurocard connector slot on the backplane. It carries its own RFIC, RF front end, power amplifier, band-pass filter, T/R switch (or duplexer ports, Section 7.1), variable attenuators, SWR bridge, and optionally an external LNA. IQ data is transported digitally over the backplane data bus. The default antenna interface is front-panel **RP-SMA**; optional **Type-N** jacks are preferred where panel space and the site coax plan allow (see [Section 9.6](#96-antenna-connector-options-rp-sma-or-type-n)).

### PA output power levels

Two PA output power levels are defined for all module variants:

| Level | RF output power | Typical use |
|-------|----------------|-------------|
| **Standard** | 5 W (37 dBm) | Indoor cabinets, low-interference sites, battery-backed installs |
| **Maximum** | 20 W (43 dBm) | Hilltop sites, portable deployments, secondary links requiring range |

The standard 5 W level is the default factory configuration. The 20 W level is selected by operator command via the `ctrl` ZMQ socket and stored in the module EEPROM. A firmware-enforced 50% duty cycle limit applies at all times when operating at 20 W output (see [Section 10.5](#105-ht-module-daemon-functions)). Forced-air cooling (120 mm fan beneath the module card cage) is required for sustained 20 W operation; see [Section 8.5](#85-ground-plane-and-copper-pour-thermal-policy).

Higher power (for example 100 W) is an **external amplifier** after the module: about 250 W DC and 150 W of heat do not fit the 72 W slot budget or the module cooling. Switch and filter parts for that level are in [rf-switches-and-filters.md](rf-switches-and-filters.md) §3.

### Key differences from the OpenHT-DB handheld design

The repeater module context differs from a handheld transceiver in several important ways:

| Parameter | OpenHT-DB handheld | Repeater module |
|-----------|-------------------|-----------------|
| Form factor | Single PCB, battery-powered | 3U Eurocard (100 × 160 mm), DIN 41612 backplane connector, backplane-powered |
| IQ interface | I2S to iMX93 SoM on same PCB | I2S over backplane DIN 41612 to the host's ECP5 interface card |
| Audio hardware | Codec, mic, headphone | Present on module PCB — used for bench test and optional monitoring |
| Display / keypad | On chassis | Not on module — on chassis manager or remote |
| ALSA | Required (audio output to user) | Available; used for bench testing and optional direct monitoring |
| Battery / charging | On-board BMS + USB-C PD | External DC from backplane PSU rails (+12 V PA, +5 V, +3.3 V, +1.8 V) |
| USB-A (security token) | On-board | On the host; Nitrokey token plugged into the host's USB-A |
| Bands per PCB | Dual (VHF + UHF) | Single band per module; dual-band 2 m / 70 cm optional (band-path switch, Section 7.3) |
| GNSS on module | No — on main SBC | No — on main SBC |
| SWR monitoring | Not applicable (handheld) | On-module SWR bridge + ADC; auto-disable on SWR > 3.0 |

All hardware present in the OpenHT-DB design is retained on the module PCB. The audio codec, microphone header, and headphone/line output are populated on all variants. In repeater operation they provide an optional audio monitoring tap and greatly simplify bench testing — an operator can plug a PC soundcard into the 3.5 mm jack during bring-up without needing the full backplane. The 3.5 mm jack is present and populated on all builds; there is no DNP variant.

---

## 2. Why a Custom RFIC

No existing commodity RFIC adequately covers all three bands (144 MHz, 432 MHz, 1240 MHz) with sufficient IQ bandwidth, low noise figure, a clean open digital interface, and power consumption appropriate for a modular embedded Linux SDR platform.

### LinHT and the SX1255 path

The **[LinHT](https://linux-radio.eu/)** handheld project (OpenHT lineage) uses the Semtech **SX1255** for its UHF transceiver path — a reasonable fit at 432 MHz with 500 kHz IQ bandwidth. There is **no comparable commodity transceiver IC with a clean IQ interface at 144 MHz (VHF)** in the same class: the SX1255 family does not operate below roughly 400 MHz. That gap affects LinHT as well as this repeater concept. Both need true VHF coverage, not merely a UHF chip with an external upconverter or a compromised narrowband sub-GHz part.

HT13G-M closes that gap from the other side: it keeps the SX1255 pin-out and SPI frame, so it drops into the LinHT, and adds 130–175 MHz to the same single chain ([spec/rf-frontend.md](../spec/rf-frontend.md)).

The repeater addresses multiband service differently — one module PCB per band (or per role), each with a purpose-narrow RFIC — but the underlying commodity-silicon problem is the same: **no single off-the-shelf part spans VHF, UHF, and 23 cm** with the IQ interface and noise figure this architecture expects.

### Commodity parts considered (summary)

The following table summarises the commodity chip gap:

| Chip | 144 MHz | 432 MHz | 1240 MHz | IQ BW | Disqualifier |
|------|:-------:|:-------:|:--------:|-------|-------------|
| SX1255 | ✗ | ✓ | ✗ | 500 kHz | 400 MHz lower limit; no VHF (LinHT UHF path only) |
| CC1200 | ✓ | ✓ | ✗ | ~200 kHz | Bandwidth too narrow; no 23 cm |
| AT86RF215 | ✗ | ✓ | ✗ | 4 MHz | 400 MHz lower limit; no VHF or 23 cm |
| LMS7002M | ✓ | ✓ | ✓ | wide | 2×2 MIMO LTE/5G platform; cost and complexity (see below) |
| AD9361 | ✓ | ✓ | ✓ | 56 MHz | 2×2 MIMO; power, size, cost (see below) |
| Si4463/Si4468 | ✓ | ✓ | ✗ | ~1 MHz | Obsolete architecture; no clean IQ stream; no 23 cm |
| RFFC5072 | ✓ | ✓ | partial | wide | Mixer-only; requires external LNA/VCO/ADC |
| MAX2769 | ✗ | ✗ | ✓ | narrow | GNSS receiver only; not a transceiver |

### Wideband integrated transceivers (LMS7002M, AD9361)

**LMS7002M** (Lime Microsystems) is a remarkable device, and Lime's open-source stance is genuinely admirable — it has enabled a generation of SDR experimentation. For LinHT and for this repeater idea, however, it carries significant drawbacks:

- It is a **2×2 MIMO transceiver** aimed primarily at LTE and 5G research platforms. LinHT needs only a **single TX and single RX chain**; a fixed-site repeater module needs one chain per band. Much of the chip's analogue and digital complexity goes unused.
- **Cost** (roughly **$100** in low quantities) is prohibitive for an open community hardware project targeting amateur radio operators.
- While it solves the **frequency coverage** problem in one package, it introduces **cost, power, and integration overhead** that a purpose-designed RFIC on **IHP SG13G2** would avoid.

**AD9361** (Analog Devices) is in the same class: a **2×2 RF transceiver** with integrated 12-bit DACs and ADCs, wide tuning, and substantial digital backend. For a focused **1240 MHz module** — or any single-band repeater slot — that level of MIMO and converter capacity is unnecessary. Typical power is on the order of **3.3 W**, which is acceptable on a mains-powered repeater module but is also a serious concern on a **battery-powered handheld** (the LinHT context). Again, the part solves bandwidth and tuning in one die at the price of silicon area, BOM, and software stack complexity.

No commodity part in this survey covers the full 130 MHz–1300 MHz range with ≥500 kHz IQ bandwidth, sub-5 dB noise figure, full-duplex per band, and an I2S digital baseband interface compatible with Linux — **without** paying for unused MIMO channels and wideband research features.

A custom RFIC is the only clean path for the goals stated here.

The approach taken — **one RFIC design for 2 m and 70 cm (HT13G-M) and a separate one for 23 cm (HT13G-S)** — avoids the power and complexity penalties of a wideband transceiver covering all three bands simultaneously. A module uses HT13G-M for one band, or for both bands with a band-path switch (Section 7.3).

---

## 3. Fabrication Process: IHP SG13G2

**IHP Microelectronics, Frankfurt (Oder), Germany** provides the only open-source PDK for a production-grade SiGe BiCMOS process. All three module RFICs are targeted to this process. **IHP SG13CMOS5L** and **GlobalFoundries 8XP** are documented as alternatives in [Alternative processes](#alternative-processes).

### Process characteristics

| Parameter | Value |
|-----------|-------|
| Node | 130 nm BiCMOS |
| HBT type | SiGe:C npn-HBT |
| fT | up to 300–350 GHz |
| fmax | up to 450–500 GHz |
| CMOS gate length | 130 nm (1.2 V core), 3.3 V I/O available |
| Metal stack | 5 thin + 2 thick Al layers; MIM capacitors |
| PDK license | Apache 2.0 (open source) |
| EDA toolchain | KLayout, Xschem, OpenEMS, ngspice |
| PDK repository | github.com/IHP-GmbH/IHP-Open-PDK |

The SiGe HBT's fT of 300+ GHz means the transistors are operating well below their transit frequency at all three target bands (144 MHz, 432 MHz, 1240 MHz). This provides substantial margin for achieving the target noise figures and phase noise specifications without exotic circuit techniques.

### OpenMPW shuttle program

IHP runs regular OpenMPW shuttle batches for the SG13G2 and SG13CMOS5L processes. Each community slot is 2 mm². Based on the published 2025–2026 schedule, shuttles have run approximately every 1–2 months with tapeout deadlines in April, May, July, and September 2025, and an SG13G2 MPW run scheduled for October 2026. Turn-around time is approximately 8 months for SG13G2.

The development chain stops before fabrication (Section 11). For scale: the signed-off HT13G-M digital back end occupies about 0.34 mm²; the analogue area is not yet estimated.

### Alternative processes

The primary RFIC blocks (LNA, mixer, VCO, PA driver) depend on the SiGe HBT devices available only in SG13G2. Two additional processes are documented as alternatives for production scaling or OpenMPW prototyping where SG13G2 slots are unavailable.

**GlobalFoundries 8XP** (commercial 130 nm SiGe BiCMOS) is the production-volume fallback. The device models at sub-1.5 GHz are comparable to SG13G2, and the circuit topology is not process-specific at the target bands.

**IHP SG13CMOS5L** is a CMOS-only variant derived from the SG13 front-end, offered by IHP for open-source educational and prototyping runs. It shares the 130 nm CMOS core (1.2 V logic, 3.3 V I/O) but omits the SiGe HBT, MIM capacitors, and the upper metal layers present in SG13G2. The metal stack is four thin layers plus one 2 µm thick TopMetal (M1–M4 + TM1). An Apache 2.0 PDK is available in the IHP-Open-PDK repository (`ihp-sg13cmos5l`). Shuttle runs are scheduled more frequently and at lower cost than SG13G2.

SG13CMOS5L cannot implement the full HT13G-M or HT13G-S RFIC as specified — the noise figure, IIP3, and VCO phase noise targets require SiGe HBT performance. It remains a viable alternative for:

- Digital control logic, SPI/I2S interface blocks, and configuration registers that do not need RF devices
- Early tapeout of ADC/DAC digital back-end stubs before committing an SG13G2 RF front-end run
- Independent validation of non-RF die area and pad-frame layout within the 2 mm² OpenMPW community slot
- Designs that accept reduced RF performance using CMOS-only circuit techniques at VHF/UHF

Designs targeting SG13CMOS5L should be maintained as a separate PDK variant (`$PDK=ihp-sg13cmos5l`) alongside the primary SG13G2 netlist.

---

## 4. RFIC Family Overview

| RFIC | Coverage | Used in | Status |
|------|----------|---------|--------|
| **HT13G-M** | 130–175 MHz (VHF) **and** 400–480 MHz (UHF) — **one band-switched chain** | 2 m, 70 cm and dual-band repeater modules; LinHT handheld (SX1255 drop-in) | Digital back end signed off (Phase 1); analogue part specified, not yet designed |
| **HT13G-S** | 1200–1300 MHz (L-band / 23 cm) — single chain | 23 cm module | Deferred |

Up to r0.3 the HT13G-M was a dual-chain chip: two LNAs, two PLLs, two I2S ports and two PTT inputs, with one chain powered down on each module. It is now a **single chain**: one LNA input, one quadrature mixer, one VCO at 3.12–4.20 GHz divided by 8 (UHF) or 24 (VHF), one Σ-Δ ADC and one Σ-Δ DAC. The band is chosen by register (`band_sel`). The same die serves 2 m, 70 cm, VHF/UHF land mobile and PMR446, and — because it keeps the **Semtech SX1255 pin-out and SPI frame** — the LinHT handheld.

The full requirements are in [spec/rf-frontend.md](../spec/rf-frontend.md); the limits they come from (Norwegian duplex offsets: 600 kHz on 2 m, 2 MHz on 70 cm) are in [spec/derived-limits.md](../spec/derived-limits.md); the design status and sign-off numbers are in [HANDOFF.md](HANDOFF.md). Section 5 summarises them.

The HT13G-S is a separate single-chain design for 23 cm (Section 6), deferred until VHF/UHF is done.

---

## 5. HT13G-M RFIC — 2 m / 70 cm Module

One HT13G-M is a **half-duplex** transceiver: the receive and transmit paths share the on-chip filter engine. A same-band repeater therefore uses **two** HT13G-M, one for RX and one for TX (Section 7.1). A simplex or cross-band module uses one.

### 5.1 Architecture

Direct-conversion (zero-IF) IQ in both directions, one chain for both bands:

```
RF_IN (pin 27) → LNA with gain steps → quadrature mixer (harmonic-reject on VHF) → TIA + anti-alias → Σ-Δ ADC → decimation ─┐
                                              ↑ LO                                                                     │
        XTB (pin 8, 32 or 36 MHz) → PLL → VCO 3.12–4.20 GHz → ÷8 (UHF) / ÷24 (VHF) → I/Q LO                            ├─ I2S + SPI
                                              ↓ LO                                                                     │  (digital back
RF_OP / RF_ON (pins 30 / 29) ← PA driver ← TX gain ≥ 30 dB ← IQ modulator ← reconstruction filter ← Σ-Δ DAC ← interpolation ─┘   end, signed off)
```

### 5.2 Receive Path Specifications

Targets for the **attenuator baseline** (two PE4312 in front of the chip, as on the LinHT; Section 7.1). `[PROP]` values in [spec/rf-frontend.md](../spec/rf-frontend.md) §3 are proposals for review.

| Parameter | Target | Notes |
|-----------|--------|-------|
| Frequency range | 130–175 MHz and 400–480 MHz | One chain; band by register |
| Input | 50 Ω single-ended (pin 27) | One external match per band |
| Noise figure (max gain) | ≤ 4 dB | Not worse than the SX1255 (4.5 dB); baseline system NF ≈ 8 dB with the attenuators |
| Gain control on chip | ≥ 48 dB | The PE4312s add 0–63 dB externally |
| IIP3 (max gain) | ≥ −20 dBm | Own TX leakage plus a second signal at a repeater |
| Input P1 dB (max gain) | ≥ −30 dBm | Own TX at −36 dBm (25 W, 80 dB duplexer) must not compress |
| LO phase noise at the duplex offset | ≤ −136 dBc/Hz (25 W), ≤ −129 dBc/Hz (5 W) | Reciprocal mixing; −139 with the LNA option |
| VHF 3 × LO response | ≥ 60 dB rejection | Harmonic-reject mixer plus board preselection |
| ADC | 1-bit Σ-Δ at the reference rate (32 or 36 MHz) | DR ≥ 101 dB in 12.5 kHz (25 W) / 94 dB (5 W); anti-alias ≥ 40 dB at ±8/9 MHz, ≥ 70 dB at ±32/36 MHz |
| IQ output | 16-bit I + 16-bit Q | 25 / 50 / 100 / 200 / 500 kHz; 500 kHz maximum |
| DC offset, IQ imbalance | **Corrected on the host** | Removed from the chip in 2026-10 to meet the 0.34 mm² digital area target |
| Maximum input | 0 dBm operating, +6 dBm absolute | As the SX1255 |

### 5.3 Transmit Path Specifications

| Parameter | Target | Notes |
|-----------|--------|-------|
| Output | **−5 dBm** average into 50 Ω, single-ended on RF_OP (differential 100 Ω allowed) | Same as the SX1255 on the LinHT, so the GRF5604 and its match are reused |
| Output P1 dB | ≥ +2 dBm | 7 dB back-off |
| OIP3 at −5 dBm | ≥ +13 dBm | Linear modes |
| Gain control | ≥ 30 dB analogue, ≤ 2 dB steps, **after** the reconstruction filter | Lowering power must lower the noise too |
| Noise at the duplex offset | ≤ −146 dBc/Hz at the RFIC output (25 W) | −149 with the LNA option |
| Reconstruction filter | ≥ 51 dB at 600 kHz, ≥ 71 dB at 2 MHz (IQ rates ≤ 200 kHz) | Selectable corner |
| Image / LO leakage | Image ≥ 40 dB after host calibration; LO leakage ≤ −30 dBc before | |
| Harmonics at the RFIC output | ≤ −30 dBc | The module filter does the rest |
| TX enable | SPI register write (the SX1255 pin-out has no PTT pin) | See open item 2 in Section 5.9 |

### 5.4 LO / Frequency Synthesis

| Parameter | Target |
|-----------|--------|
| VCO | 3.12–4.20 GHz; ÷8 for UHF, ÷24 for VHF; quadrature from the last ÷2 |
| Phase noise at the LO | ≤ −136 dBc/Hz at 600 kHz (VHF) and 2 MHz (UHF), 25 W baseline |
| Frequency resolution | ≤ 10 Hz at RF; < 1 Hz preferred so ppm correction can be done in the LO |
| Synthesizer wake-up | ≤ 150 µs |
| TX/RX turnaround | ≤ 0.5 ms including PLL settling (DMR TDMA) |
| Reference | 32 MHz or 36 MHz on XTB; the host picks per channel so that no clock harmonic lands on it (32 MHz for 2 m / 70 cm, 36 MHz for PMR446 and near 160 / 416 / 448 MHz). LinHT: 32 MHz only |
| Spurs | ≤ −95 dBc at the duplex offset (25 W), TX ≤ −67 dBc elsewhere (design target), RX ≤ −84 dBc elsewhere — [spec/derived-limits.md](../spec/derived-limits.md) §9 |

The chip has no tuning-voltage pin. The module's reference oscillator (VCTCXO) is tuned through backplane pin a12 as before; how the RFIC modules are frequency-disciplined is not decided yet.

The open-source phase-noise simulation (VACASK `pnoise`) used for the VCO has been validated against an exact result and against transient noise on an SG13G2 oscillator ([analog/pn-validation/](../analog/pn-validation/README.md)); the flicker region is not yet validated.

### 5.5 Digital Interface (SX1255 pin-out, "Option P")

| Pin(s) | SX1255 name | HT13G-M function |
|--------|-------------|------------------|
| 17–20 | SCK, MISO, MOSI, NSS | SPI, same frame as the SX1255 (mode 0, write bit + 7-bit address + 8-bit data). **Register map differs** — the host driver changes |
| 10 | CLK_OUT | I2S BCLK (out when master, in when slave) |
| 23 | DIO2 | I2S word select (LRCLK) |
| 15 | I_OUT | I2S data out (RX IQ: I = left, Q = right, 16-bit) |
| 13 | I_IN | I2S data in (TX IQ) |
| 9 | RESET | **Active-high** reset, internal pull-down; ORed with the on-chip power-on reset |
| 8 | XTB | 32 or 36 MHz reference input |
| 21 | DIO0 | `clk_req` |
| 11 | CLK_IN | **`ref_36` strap:** sampled while RESET is active, internal pull-down. Low / open = 32 MHz (LinHT, pin not connected), high = 36 MHz. Read back in a status bit |
| 22 | DIO1 | **IRQ out**, active-low (PLL unlock, AGC threshold, RSSI update), enabled by register; idle as the SX1255 DIO default |
| 24 | DIO3 | **PTT gate in**, internal pull-down. Ignored unless the register bit `ptt_pin_en` is set (default off: TX over SPI only, as the SX1255); when set, TX runs only while SPI selects TX **and** this pin is high |
| 12, 14 | Q_IN, Q_OUT | Spare / test |

I2S is Philips format with a continuous bit clock. The RFIC is **master** by default; slave mode goes through a 4-deep asynchronous FIFO. At 500 kSa/s and 32 MHz the bit clock is 16 MHz (32 bit clocks per frame, 50 % duty). Full pin map: [spec/rf-frontend.md](../spec/rf-frontend.md) §2.

The digital I/O runs at the chip supply (2.7–3.6 V), as on the SX1255; there is no separate VDD_IO. On a repeater module, level translators sit between the 1.8 V backplane and the RFIC (Section 9.5 notes).

### 5.6 Power

| Item | Target |
|------|--------|
| Supply | Single 2.7–3.6 V (VBAT1–3), internal regulators decoupled on VR_PA, VR_ANA1, VR_ANA2, VR_DIG |
| Sleep | ≤ 1 µA |
| Standby (reference running) | ≤ 1.5 mA |
| RX | ≤ 25 mA |
| TX at −5 dBm | ≤ 60 mA |
| Temperature | −40 to +85 °C ambient |
| ESD | ±2 kV HBM all pins; RF pins ≥ ±1 kV |
| Power-on reset | On-chip; SPI usable ≤ 5 ms after power-on and after a manual reset |

### 5.7 Package

- Same as the SX1255: MLPQ-W 5 × 5 mm, 32 leads plus exposed pad (pin 0 = ground, also RF ground)
- Exposed pad: minimum 9-via array to L2

### 5.8 Work Done on the Host

- **DC-offset and IQ-imbalance correction** of the RX stream, and pre-correction of the TX stream, in the host software (GNU Radio 4, planned under `host/gr4/`). The RFIC has no calibration registers for these.
- Choice of the 32 or 36 MHz reference per channel.
- A new SPI driver (the LinHT's `sx1255-spi` equivalent) for the HT13G-M register map.

### 5.9 Open Items (interface)

1. ~~`ref_36`~~ — strap on pin 11 (CLK_IN), sampled at reset, pull-down = 32 MHz (decided 2026-10-19). Changing it needs a reset, which matches the static false path in timing.
2. ~~Backplane PTT (c2) and RFIC_IRQ_N (c1)~~ — c2 → DIO3 as a hardware PTT gate (off by default), c1 ← DIO1 as IRQ (decided 2026-10-19). Small RTL change, together with the other Option P pin-map changes.
3. ~~I2S format on the LinHT~~ — confirmed from the LinHT Yocto layer (`meta-linht-hardware`, `sbc-mcm-imx93.dtsi`): `format = "i2s"`, `bitclock-master` and `frame-master` = the SX1255 on both the RX and the TX link; SAI1 uses TX_BCLK, TX_SYNC, TXD0 and RXD0. That is the chip's default (Philips I2S, RFIC master).

## 6. HT13G-S RFIC — 23 cm Module

> **Deferred — not updated since r0.3.** When work on 23 cm starts, HT13G-S takes over the HT13G-M decisions: active-high reset with on-chip power-on reset, DC-offset and IQ correction on the host, 32 or 36 MHz reference, −5 dBm TX output, no fabrication in the development phase. The numbers below are the r0.3 ideas.

The 23 cm band (1240–1258 MHz) requires a separate RFIC. At 1.24 GHz the circuit topology changes compared to sub-500 MHz design — microstrip matching networks become practical and transmission line effects must be accounted for in layout. The SiGe HBT process remains entirely appropriate; fT of 300 GHz gives > 200× frequency headroom.

### 6.1 Architecture

Single-chain, single-band. Zero-IF direct conversion with on-chip LNA, IQ mixer, PLL/VCO, Σ-Δ ADC, Σ-Δ DAC, and IQ modulator. A single I2S port carries the IQ stream.

```
                    ┌──────────────────────────────────────────────────┐
                    │                 HT13G-S RFIC                     │
                    │                                                  │
  RF_23CM_IN ──────►│ BPF → LNA → IQ Mixer → Σ-Δ ADC → I2S_23CM OUT │
                    │       ↑                                          │
                    │   PLL (1200–1300 MHz, 32 MHz ref)               │
                    │       ↓                                          │
  RF_23CM_OUT ◄─────│ BPF ← PA Driver ← IQ Mod ← Σ-Δ DAC ← I2S IN  │
                    │                                                  │
                    │ SPI config · RSSI · AGC · TEMP · IRQ            │
                    │ VCTCXO_TUNE (0–1.8 V analog)                   │
                    └──────────────────────────────────────────────────┘
```

### 6.2 Receive Path Specifications

| Parameter | 23 cm Chain | Notes |
|-----------|-------------|-------|
| Frequency range | 1200–1300 MHz | Covers 23 cm globally; headroom beyond 1240–1258 |
| Architecture | Zero-IF direct conversion IQ | |
| LNA topology | Cascode SiGe HBT; inductive source degeneration | Cascode preferred at L-band for better reverse isolation |
| Noise figure | < 4 dB | At matched 50 Ω, 25°C |
| Input impedance | 50 Ω | On-chip transmission line matching + external PCB network |
| IIP3 | > −3 dBm | |
| LNA gain | 14–22 dB, 4 programmable steps | |
| Image rejection | > 40 dBc | DC offset correction loop |
| ADC architecture | 1-bit Σ-Δ, 38.4 MHz oversampled, decimated | |
| ADC output word | 16-bit I + 16-bit Q signed | |
| Sample rates | 25 / 50 / 100 / 200 / 500 kHz | |
| Max IQ bandwidth | 500 kHz | |
| DC offset cancellation | Digital feedback loop | |
| IQ imbalance | < 1 dB amplitude, < 2° phase post-calibration | L-band IQ balance is tighter to achieve; calibrated on startup |
| RSSI | 8-bit, ±2 dB, SPI-readable | |
| AGC | Programmable threshold + step; manual SPI override | |

### 6.3 Transmit Path Specifications

| Parameter | 23 cm Chain | Notes |
|-----------|-------------|-------|
| Architecture | Direct IQ upconversion | |
| DAC architecture | 1-bit Σ-Δ interpolating | |
| Input sample rates | 25 / 50 / 100 / 200 / 500 kHz | |
| Output power (chip) | 0 ± 2 dBm into 50 Ω | External PA on module PCB (see Section 7.3) |
| Harmonic suppression | > 25 dBc on-chip | PCB BPF brings to > 60 dBc |
| TX/RX isolation | > 40 dB | On-chip switch + external T/R switch |

### 6.4 PLL / Frequency Synthesis

| Parameter | Value |
|-----------|-------|
| Architecture | Integer-N + fractional Σ-Δ |
| VCO range | 1200–1300 MHz direct (no division) |
| Reference | 32 MHz VCTCXO on module PCB |
| VCTCXO tune input | 0–1.8 V analog, ±50 ppm pull |
| Phase noise @ 10 kHz offset | < −100 dBc/Hz |
| Lock time | < 1 ms |
| Frequency resolution | < 200 Hz |
| Frequency word | 32-bit via SPI |

> **Note on VCO design at 1.24 GHz:** At this frequency the on-chip VCO inductor can be integrated as a bondwire-style element or a spiral inductor with adequate Q in the thick top metal layer (2–3 µm) of the SG13G2 Al BEOL. Phase noise is more challenging at L-band than at VHF/UHF. The target of < −100 dBc/Hz at 10 kHz offset is achievable with a high-Q LC tank; the SG13G2 Cu-BEOL option (SG13G2Cu) may be preferred for this design if the thick Cu layers provide sufficient inductor Q.

### 6.5 Digital Interface

To follow HT13G-M (Section 5.5) for SPI, I2S and reset when the design is resumed.

### 6.6 Power

| Rail | Voltage | RX current | TX current |
|------|---------|------------|------------|
| VDD_RF | 3.3 V | 45 mA (single chain) | 70 mA |
| VDD_CORE | 1.2 V (internal LDO) | 15 mA | 20 mA |
| VDD_IO | 1.8 V or 3.3 V selectable | 4 mA | 4 mA |
| **Total** | | **~200 mW** | **~282 mW** |

### 6.7 Package

- QFN-32 or QFN-40, 5×5 mm, 0.5 mm pitch
- EPAD; 9-via minimum
- Single-chain die is smaller than HT13G-M; likely fits within ~1 mm² active area

---

## 7. RF Signal Chain — Per Module

Each module presents the same external signal chain architecture regardless of band. Part numbers differ per band where necessary.

### 7.1 Full RF Chain Block

One HT13G-M is half-duplex (Section 5). Two module configurations follow from that.

**A. Repeater (same-band duplex):** RX and TX run at the same time, so two RFICs are needed — one receiving, one transmitting — sharing one reference oscillator, with RX and TX joined at the site's external cavity duplexer (80 dB TX→RX isolation assumed in [spec/derived-limits.md](../spec/derived-limits.md)).

```
ANT ── cavity duplexer (external, at the site)
          ├── RX port ── 2× PE4312 (0–63 dB) [── optional LNA in front] ── HT13G-M (RX)
          └── TX port ── SWR bridge ── harmonic filter ── PA (GRF5604 driver + final) ── HT13G-M (TX)
```

**Decided 2026-10-19: one duplex module per repeater, in one slot.**

- Both RFICs share the module's reference oscillator.
- **I2S:** the RX RFIC is master on the slot's I2S port (BCLK, LRCLK, DOUT); the TX RFIC runs as slave on the same BCLK/LRCLK and takes DIN. One slot, one I2S port, no backplane change.
- **SPI:** RX RFIC on `SPI_CS_N` (b4), TX RFIC on `SPI_CS_ADC_N` (b5). The SWR ADC on a duplex module is therefore the I²C variant (ADS1015).
- **PTT (c2)** gates the TX RFIC; there is no T/R switch. `TR_SW` (c3) is unused.
- **Front panel:** two ports, RX and TX, to the site's cavity duplexer.
- **Software:** unchanged — `iq_X` carries the RX RFIC's stream and `tx_X` feeds the TX RFIC of the same slot.
- **Identity:** MOD_ID gives the band as before; the EEPROM module type says duplex (Section 9.5).
- Five slots therefore hold up to five repeaters, or a mix with simplex link modules.

**B. Simplex, half-duplex link or cross-band module** (and the LinHT): one RFIC and a T/R switch.

```
ANT (RP-SMA or Type-N, front panel)
    │
T/R switch (SPDT, solid-state)
    ├── RX path: 2× PE4312 variable attenuator (0–63 dB) [── optional external LNA in front] ── HT13G-M RF_IN
    └── TX path: SWR bridge ── harmonic filter ── PA (GRF5604 driver + final, 5 W / 20 W) ── HT13G-M RF_OP
```

The **default RX front end is the attenuators alone**, as on the LinHT (system NF ≈ 8 dB, sensitivity about −117 dBm for 12 dB SINAD in 12.5 kHz FM). A module designer may fit an external LNA in front of them (NF ≈ 5 dB system); the RFIC limits are given for both cases in [spec/derived-limits.md](../spec/derived-limits.md) §8. A dual-band module adds the band-path switches of Section 7.3.

The SWR bridge is placed **between the PA output and the T/R switch**, after the harmonic filter, so it measures the power actually reaching the antenna port — including any mismatch at the connector and feedline. Forward and reflected power detector outputs feed a dual-channel ADC on the module PCB; the ADC result is read by the `ht-module-daemon` via I²C or SPI during transmit.

### 7.2 SWR Bridge and Power Measurement

#### 7.2.1 Directional Coupler / Bridge

A small-format directional coupler is placed in the TX path between the harmonic filter output and the T/R switch antenna port. At 20 W maximum output power the coupler must handle full PA output continuously at the standard 5 W level and at the maximum 20 W level under the 50% duty cycle firmware constraint.

| Parameter | VHF (144 MHz) | UHF (432 MHz) | 23 cm (1240 MHz) |
|-----------|:-------------:|:-------------:|:----------------:|
| Topology | Transmission-line coupler or toroidal transformer coupler | same | Microstrip coupled-line section |
| Coupling factor | 20 dB (forward), 20 dB (reflected) | same | same |
| Directivity | > 20 dB | > 20 dB | > 18 dB |
| Insertion loss | < 0.3 dB | < 0.3 dB | < 0.5 dB |
| Power rating | > 25 W continuous | > 25 W continuous | > 25 W continuous |
| Implementation | SMD toroidal transformer (e.g. Coilcraft WBC series) | same | Hairpin microstrip on L1 |
| Termination | 50 Ω load on isolated port (forward detector); 50 Ω on through port (reflected detector) | same | same |

At VHF and UHF a small toroidal transformer coupler (wound on a ferrite bead, 4–6 turns, SMD construction) is practical and well-characterised. At 1240 MHz a microstrip coupled-line section on L1 is more reproducible and avoids ferrite performance variation at L-band.

#### 7.2.2 RF Power Detectors

Each coupler output (forward and reflected) drives an RF power detector diode. The detector output is a DC voltage proportional to the envelope of the coupled RF signal.

| Parameter | Value |
|-----------|-------|
| Detector diode | Skyworks SMS7630 or equivalent zero-bias Schottky |
| Detection range | −20 dBm to +10 dBm at detector input (20 dB coupling factor → 20 W = +43 dBm forward → +23 dBm at detector) |
| Output voltage range | ~50 mV to ~800 mV DC (log-linear characteristic) |
| Low-pass filter | 10 kΩ + 100 nF RC after each detector (3 dB at ~160 Hz — envelope following for CW/FM; not audio-following) |
| Supply | No supply required — zero-bias detector |

#### 7.2.3 Dual-Channel ADC

The two detector outputs (forward power, reflected power) are read by a dedicated dual-channel ADC on the module PCB. This ADC is separate from the RFIC and from the audio codec.

| Parameter | Value |
|-----------|-------|
| Part (candidate) | MCP3202 (Microchip, 12-bit, dual-channel, SPI) or ADS1015 (TI, 12-bit, 4-channel, I²C) |
| Resolution | 12-bit |
| Interface | SPI (MCP3202) or I²C at address set by module address pins (ADS1015) |
| Sample rate | On-demand polling by `ht-module-daemon` during TX; no continuous streaming required |
| Supply | 3.3 V from module power rail |
| Reference | 3.3 V supply reference (adequate for SWR ratio computation; absolute accuracy not critical) |

#### 7.2.4 SWR Computation

The `ht-module-daemon` reads both ADC channels during TX and computes:

```
V_fwd  = ADC channel 0 (forward detector output, mV)
V_ref  = ADC channel 1 (reflected detector output, mV)

Gamma  = V_ref / V_fwd          (voltage reflection coefficient, linear)
SWR    = (1 + Gamma) / (1 - Gamma)

P_fwd  = calibrated from V_fwd using factory calibration table in module EEPROM
P_ref  = calibrated from V_ref using factory calibration table in module EEPROM
```

Factory calibration maps detector voltage to power in dBm at three reference points per band (stored in module EEPROM at offset 0x18 onwards — see [Section 9.5](#95-din-41612-connector-pin-assignment)). This allows accurate absolute power reporting without requiring the 3.3 V ADC reference to be a precision source.

**Automatic protection:** If SWR > 3.0 is measured during transmit, `ht-module-daemon` immediately:

1. De-asserts PA_EN (PA disabled)
2. De-asserts TR_SW (T/R switch returns to RX)
3. De-asserts PTT (RFIC TX path disabled)
4. Sets module fault state (`fault: true`, `fault_reason: "swr_high"`)
5. Publishes `swr_high` alert on the `status` ZMQ socket

The module will not transmit again until an operator issues `MOD_CLEAR_FAULT` after physically inspecting and correcting the antenna system. See [zeromq-messages.md Section 5.3](zeromq-messages.md#53-alert-messages) for the alert wire format.

#### 7.2.5 SWR Bridge Placement and Layout

- The coupler is placed on L1 in the RF zone, **after** the harmonic filter and **before** the T/R switch antenna port
- The two detector circuits (diode + RC filter) are placed immediately adjacent to the coupler ports, within 5 mm, to minimise parasitic pickup
- The ADC is placed in the mixed zone, away from the PA
- SPI or I²C traces from the ADC to the backplane run on L4, below the L5 ground plane shield
- At 1240 MHz, the microstrip coupler geometry is calculated for the L1 substrate (FR4, εr ≈ 4.5, h ≈ 0.18 mm to L2 ground plane)

### 7.3 Component Specifications

#### T/R Switch (Solid-state, configuration B modules)

| Parameter | VHF (144 MHz) | UHF (432 MHz) | 23 cm (1240 MHz) |
|-----------|:-------------:|:-------------:|:----------------:|
| Type | SPDT | SPDT | SPDT |
| Part (candidate), 5 W variant | pSemi PE42820 (SOI, +43 dBm CW) | same | same (to 2.7 GHz) |
| Part (candidate), 20 W variant | PIN-diode SPDT ≥ 50 W, e.g. Skyworks SKY12208-306LF or MACOM MSW2030-203 | same | SKY12208-306LF (to 2.7 GHz; the MSW2030 stops at 1 GHz) |
| Frequency | 30 MHz–2.7 GHz (PE42820) | same | same |
| Insertion loss | < 0.5 dB | < 0.5 dB | < 0.6 dB |
| TX→RX isolation | > 30 dB | > 30 dB | > 28 dB |
| Power handling | ≥ 2 dB above the PA level: ≥ +39 dBm (5 W variant), ≥ +45 dBm (20 W variant) | same | same |
| Switching time | ≤ 10 µs (the PTT sequence allows 1 ms) | same | same |
| Control | 2 GPIO from the host (via backplane) | same | same |

The T/R switch is a key reliability element. Solid-state (PIN diode or CMOS SOI) switching is mandatory — no mechanical relays. The PE42820 runs from a single 2.3–5.5 V supply and switches from 1.8 V logic, so it needs no extra rail; it has no margin at 20 W, hence a PIN switch for the 20 W variant (PIN switches need a bias supply, up to 28–125 V for the MACOM parts). The LinHT uses the SKY13330 (P0.1dB +38.5 dBm, about 7 W), adequate at 5 W only. **The SKY13351 named up to r0.4 is a 1 W part and is not suitable.** **Power handling must be verified at the selected part's rated continuous power and at SWR 3; derate to 50% duty cycle where continuous rating is marginal.** Candidates and datasheet numbers: [rf-switches-and-filters.md](rf-switches-and-filters.md).

**PTT sequencing is hardware-enforced:**

1. RFIC PTT assert (< 1 µs) — disables LNA path, enables TX DAC
2. T/R switch → TX position (< 1 µs)
3. 1 ms hardware delay
4. PA enable assert

On TX→RX transition the sequence reverses: PA de-assert → T/R switch RX → RFIC PTT release. This ensures the external LNA is never exposed to PA output power.

#### Band-path switch (ANT_SW, dual-band modules only)

The single-chain RFIC tunes 130–175 MHz and 400–480 MHz, but the parts around it cannot be shared between bands: the PA output match, the harmonic filter (a 2 m low-pass must cut off near 180 MHz; the 70 cm filter passes up to about 490 MHz and therefore passes the 2nd and 3rd harmonics of 2 m) and the RX input match differ per band. A module built for both bands therefore has a VHF path and a UHF path, chosen by backplane pin c5 (`ANT_SW`). Fixed-band modules (2 m only or 70 cm only) do not fit the switches and leave c5 unconnected.

| Item | Definition |
|------|------------|
| Logic | 1.8 V CMOS from the ECP5 interface card. **High = VHF path, low = UHF path** |
| Default | 100 kΩ pull-down on the module, so an unconfigured or unpowered backplane selects UHF |
| Interlock | `ht-module-daemon` changes ANT_SW only in RX state, with PTT, PA_EN and TR_SW de-asserted; the RFIC is retuned in the same step |
| Module ID | A dual-band module identifies itself as MOD_ID = 11 (previously spare) plus EEPROM module type |

**Low-power side — pSemi PE4259 (SPDT, 10 MHz–3 GHz, SC-70-6), candidate.** Two switches, one between the RFIC TX output (−5 dBm) and the two PA input matches, one between the two RX input matches and the RFIC RX input. From the PE4259 datasheet (DOC-03694-5.01): insertion loss about 0.3 dB, input-to-output isolation about 50 dB at 150 MHz and 40 dB at 450 MHz, return loss about 29 dB, IIP3 +55 dBm, 1.5 µs switching. At these levels it is far from its limits.

- **Supply:** run the PE4259 at **VDD = 1.8 V** (its minimum). In single-pin mode the control threshold is 0.7 × VDD, so a 3.0 V supply would need 2.1 V on CTRL and the 1.8 V backplane GPIO would not switch it reliably. At 1.8 V the P1 dB falls to about +30.5 dBm, which does not matter on the low-power side.
- **Wiring:** CTRL (pin 4) from ANT_SW; VHF path on RF1 (CTRL high), UHF path on RF2. All RF pins DC-blocked with series capacitors. Fit the shunt tuning capacitor at RFC shown in the datasheet evaluation schematic if return loss needs it.

**High-power side — not the PE4259.** After the PA the switch would see the full output: 5 W (+37 dBm) standard, 20 W (+43 dBm) maximum, 6 W from a GRF5604 on its own. The PE4259 is rated for about +34.5 dBm maximum at 150–450 MHz (datasheet Figure 3) and +31.5 dBm minimum P1 dB at 3 V. The PA-side band selection needs a part rated for the full PA power (PIN-diode switching, as in commercial dual-band transceivers, or a high-power SOI switch), or two PA output paths that meet in a diplexer **after** each band's own harmonic filter. ANT_SW drives that switch too. Which of these to use is still open. Candidate parts by power level: [rf-switches-and-filters.md](rf-switches-and-filters.md).

#### Variable Attenuator (RX path, per band)

| Parameter | Value |
|-----------|-------|
| Part | pSemi PE4312 (1 MHz–4 GHz, valid for all three bands) |
| Range | 0–31.5 dB per device, 0.5 dB steps; **two in series (0–63 dB)** as on the LinHT |
| Insertion loss at 0 dB | < 1 dB |
| Control | 6-bit SPI or parallel; latch enable from module GPIO |
| Purpose | Default RX front end: extends the gain-control range and lets a strong site trade sensitivity for blocking |
| Supply | 3.3 V |

The PE4312 covers DC–4 GHz, making it suitable for all three bands with a single part number. At 1240 MHz, insertion loss increases slightly from the 1 MHz spec but remains under 1 dB.

#### External LNA (RX path, optional)

| Parameter | VHF / UHF | 23 cm |
|-----------|-----------|-------|
| Part (candidate) | PGA-103+ (Mini-Circuits) or BFP840ESD (Infineon) | BFP840ESD or MGFC4919G |
| Noise figure | < 0.8 dB | < 1.0 dB |
| Gain | 16–20 dB | 14–18 dB |
| Bias | 3.3 V, set by on-module bias resistor | same |
| Placement | When fitted: immediately after the T/R switch or duplexer RX port, before the attenuators | same |

The external LNA defines the system noise figure, which is dominated by the first active stage. Placing the LNA before the attenuator means the attenuator's insertion loss and the RFIC's noise figure are both divided by the LNA gain when referred to the input — a system noise figure improvement from about 8 dB to about 5 dB. The LNA is **optional**: the baseline module has none, and the LNA gain raises the linearity the RFIC sees by the same amount.

#### Power Amplifier (TX path, per band)

Two PA configurations are supported. Both share the same PCB footprint family where possible. The 20 W parts are assembled when the operator orders the **`-20W`** module variant; the 5 W parts are fitted by default.

| Parameter | VHF | UHF | 23 cm |
|-----------|-----|-----|-------|
| **Standard output (5 W)** | | | |
| Target output | 5 W (37 dBm) | 5 W (37 dBm) | 5 W (37 dBm) |
| Candidate IC | RA07H1317M | RA07H4047M | RA07H1213M or MAAMSS0060 |
| Required gain | ~42 dB from −5 dBm (driver + final) | ~42 dB | ~42 dB |
| PA supply | 3.3–5 V regulated | same | same |
| Efficiency | > 40% Class AB | > 40% | > 35% |
| Heat dissipation at 5 W TX | ~7.5 W at 40% efficiency | same | ~8.6 W at 37% |
| **Maximum output (20 W)** | | | |
| Target output | 20 W (43 dBm) | 20 W (43 dBm) | 20 W (43 dBm) |
| Candidate IC | RA30H1317M | RA30H4047M | MAAMSS0060 or equivalent GaAs MMIC |
| Required gain | ~48 dB from −5 dBm (driver + final) | ~48 dB | ~48 dB |
| PA supply | +12 V from backplane (direct, no linear regulator in series) | same | same |
| Efficiency | > 40% Class AB | > 40% | > 35% |
| Heat dissipation at 20 W TX | ~30 W at 40% efficiency; **15 W average at 50% duty cycle** | same | ~34 W at 37%; **17 W average** |
| **Common** | | | |
| Input power | **−5 dBm** from the RFIC | same | same |
| Architecture | GRF5604 driver (100–600 MHz, as on the LinHT) + GaAs or LDMOS final; check the final's drive requirement against the GRF5604 output | same | GaAs MMIC |
| Enable | GPIO from the host via backplane, sequenced after T/R switch | same | same |

> **Thermal note (20 W variant):** At 20 W output with 40% efficiency the PA dissipates ~30 W instantaneously and ~15 W average at 50% duty cycle. This exceeds the passive cooling capacity of the 100 × 160 mm module PCB (~5 W passively). A 120 mm fan mounted below the card cage is **required** for sustained 20 W operation. The copper pour and via array described in Section 8.5 conduct heat from the PA package to the board surface; forced air removes it from there. The per-card temperature sensors (LM75/TMP102, Section 9.4) feed the fan controller; fan speed should begin ramping at 35°C board temperature and reach full speed by 45°C. A firmware transmit inhibit triggers at 55°C regardless of PA level.

> **Supply current note (20 W variant):** At 20 W output with 40% efficiency, PA supply current at +12 V is approximately 4.2 A instantaneous, 2.1 A average at 50% duty cycle — well within the har-bus 64 contact rating. At full-load peak the slot draws ~50 W; the per-slot budget of 72 W (6 A × 12 V) provides adequate headroom. If two 20 W modules transmit simultaneously, verify total PSU capacity against the populated slot count.

#### Band-Pass / Harmonic Filter (TX path, per band)

A 7-element Chebyshev band-pass filter is placed between the PA output and the SWR bridge. It carries full TX power; component ratings must reflect the **20 W maximum** level.

| Parameter | VHF filter | UHF filter | 23 cm filter |
|-----------|-----------|-----------|-------------|
| Passband | 130–175 MHz | 400–480 MHz | 1200–1300 MHz |
| Insertion loss | < 0.8 dB | < 0.8 dB | < 1.0 dB |
| Harmonic rejection (2nd) | > 60 dBc | > 60 dBc | > 60 dBc |
| Harmonic rejection (3rd+) | > 70 dBc | > 70 dBc | > 65 dBc |
| Implementation | SMD LC, 0402, tuned at assembly | same | same; consider hairpin microstrip at 1.24 GHz |
| Inductor rating | > 2 A continuous | > 2 A continuous | > 2 A continuous |
| Capacitor voltage rating | ≥ 100 V | ≥ 100 V | ≥ 100 V |
| PCB footprint | ~25 × 8 mm | ~20 × 8 mm | ~15 × 6 mm |

> **Rating note:** At 20 W into 50 Ω the peak voltage across filter components is approximately 45 V and peak current approximately 900 mA. Capacitors rated at 30 V (adequate for 5 W) are insufficient at 20 W — 100 V rated parts are required. Inductors must be rated above 2 A with adequate core saturation margin. Verify component ratings at the selected 20 W PA output level before assembly.

> **Parts note:** surface-mount LTCC filters (Mini-Circuits LFCN, LFHK) are rated about 8–10 W at 25 °C, falling with temperature, so they suit only the 5 W level; the 20 W filter is discrete LC. On VHF the LFCN-160+ and LFCN-180+ reject the 2 m 2nd harmonic by only about 7–18 dB, so the VHF filter is a discrete elliptic design. Full 130–175 MHz coverage is decided (2026-10-19): a 7th-order elliptic-type filter with three traps (33 pF, 36 nH ∥ 2.7 pF, 75 pF, 22 nH ∥ 12 pF, 68 pF, 24.5 nH ∥ 15 pF, 27 pF), ≥ 70 dB from 256 MHz; values, part stress per power level and `tools/vhf_lpf_check.py` in [docs/rf-switches-and-filters.md](rf-switches-and-filters.md).

---

## 8. Module PCB Architecture

Each module is a single PCB on a **3U Eurocard form factor (100 × 160 mm per IEC 60297)**. The module is self-contained: all RF components, RFIC, SWR bridge, power conditioning, and backplane interface logic are on-board. The backplane interface uses a **Harting DIN 41612 Type C 96-pin connector** (2.54 mm pitch) plus **har-bus 64 hybrid power contacts** for the +12 V PA rail. KiCad standard library includes DIN 41612 footprints; no custom footprint is required.

### 8.1 Layer Stack (6-layer, identical for all three modules)

| Layer | Function |
|-------|----------|
| L1 top | RF routing + all RF components (RFIC, LNA, PA, BPF, SWR bridge, switches, attenuator) |
| L2 | Solid ground plane — unbroken RF reference; via-stitched at RF zone perimeter |
| L3 | Power distribution — 3.3 V, 5 V, 12 V PA rail |
| L4 | Secondary power + slow signals — SPI, I2S, GPIO, I²C, SWR ADC signals |
| L5 | Solid ground plane — shielding between digital and RF |
| L6 bottom | Backplane interface — DIN 41612 connector signals and power distribution |

### 8.2 Board Zoning

```
┌─────────────────────────────────────────────────────────────┐
│  RF ZONE (L1, double-row via-fence boundary)                │
│  RFIC · External LNA · PA (5W std / 20W max) · BPF         │
│  SWR Bridge · Detector diodes · T/R Switch                  │
│  Variable Attenuator                                        │
│  50 Ω microstrip L1 · mandatory shield cans (Würth/Laird)   │
├────────────────────────────────────┬────────────────────────┤
│  MIXED ZONE                        │  DIGITAL ZONE          │
│  VCTCXO 32 or 36 MHz               │  DIN 41612 connector   │
│  VCTCXO_TUNE RC filter             │  area (96-pin + har-bus)│
│  SWR ADC (MCP3202 / ADS1015)       │  power contacts)       │
│  SPI / I2S traces (short,          │  Power conditioning    │
│  series-terminated 33 Ω,            │  Module control logic  │
│  via-fenced both sides)            │  (optional FPGA per rev)│
│  RP-SMA / Type-N (front panel)     │                        │
│  Power regulators                  │                        │
└────────────────────────────────────┴────────────────────────┘
│  DIN 41612 CONNECTOR + har-bus POWER (bottom edge)          │
└─────────────────────────────────────────────────────────────┘
```

The RF zone perimeter is enclosed by a **double row of vias** connecting L2 to L5 at the boundary shown above. Via fences on I2S and SPI traces continue to within **2 mm** of the DIN 41612 connector footprint pads at the bottom edge.

### 8.3 RF Signal Routing Rules

| Rule | Value | Reason |
|------|-------|--------|
| 50 Ω microstrip width on L1 (FR4, L1→L2 ~0.18 mm) | ~0.35 mm | Impedance match throughout RF chain |
| Max trace length between RF components | < λ/10 at operating frequency | Minimise stub effects; at 1240 MHz λ/10 ≈ 24 mm |
| Bend style | 45° or curved; no 90° | Impedance discontinuity |
| Component size in RF path | 0402 max; 0201 preferred above 300 MHz | Minimise parasitic inductance |
| RFIC EPAD via array | 9 vias minimum (3×3) | RF and thermal ground |
| PA ground vias | Immediately adjacent to PA ground pad | Minimise source inductance |
| BPF placement | Immediately after PA output, before SWR bridge | Harmonics filtered before power measurement and antenna path |
| SWR bridge placement | After BPF, before T/R switch antenna port | Measures power at antenna interface, after filtering |
| Detector circuits | Within 5 mm of coupler ports | Minimise parasitic pickup on low-level detector outputs |
| SWR ADC traces | L4, below L5 ground plane | Isolate from RF zone |
| RP-SMA connector | Front-panel edge mount; coax land on L1 (default `-SMA` variant) | Use when panel space is tight or cables are short RP-SMA patches |
| Type-N connector | Front-panel bulkhead; same coax land (`-N` variant) | **Preferred when it fits** — fixed sites, outdoor enclosures, large coax |
| **Via fence — RF and high-speed data** | **Mandatory continuous via fences on both sides of the trace for the full routed length** | All RF signal paths and high-speed data lanes (I2S, SPI) must be enclosed; complements but does not replace shield cans |
| Via spacing (fence / stitch array) | ≤ λ/20 at highest operating frequency (12 mm @ 1240 MHz); **2–3 mm in practice** | Adequate isolation; via fences must connect L2 ground plane to L5 ground plane at regular intervals, stitching all ground layers together |
| RF zone perimeter via fence | **Double row** of vias at RF zone boundary (see Section 8.2) | RF isolation from digital and mixed zones |
| I2S / SPI via fence at connector | Continue to within **2 mm** of DIN 41612 connector footprint pads | Prevent backplane-edge coupling on high-speed lanes |
| Shield cans | **Mandatory** press-fit SMD cans over RF zone (Würth or Laird) | Physical shielding required; via fences complement but do not replace shield cans |

### 8.4 Test Points and Audio Monitoring

Every module exposes the following test points for bench characterisation and audio monitoring:

- RF test point between attenuator output and RFIC RX input (SMA footprint, unpopulated)
- RF test point between RFIC TX output and PA input (SMA footprint, unpopulated)
- RF test point between BPF output and SWR bridge input (SMA footprint, unpopulated) — allows calibration of the SWR bridge with a known source
- SWR detector output test points: two 0.1" pads (forward, reflected) for DC voltmeter connection during calibration
- SPI header (2×4, 2.54 mm) for RFIC direct configuration
- I2S header (1×6, 2.54 mm) for direct audio capture during testing
- **3.5 mm TRRS audio jack (populated on all variants)** — carries stereo IQ (I = Left, Q = Right) at baseband; allows direct monitoring or capture via any PC soundcard without the full backplane. Pinout follows Kenwood convention for compatibility with existing test equipment. In repeater operation, this port is available as a live audio monitoring tap.

### 8.5 Ground Plane and Copper Pour Thermal Policy

All ground copper pours on L1 (top) and L6 (bottom) serve a dual purpose: RF/signal reference and thermal mass/heatspreading.

- **L1 and L6 ground pours** must be thermally and electrically tied together through a regular array of thermal vias across the full board area (not only the RF zone).
- **L2 and L5 solid ground planes** must also be interconnected to L1 and L6 pours via the same via array — all six layers share a common ground with low thermal impedance between them.
- The **PA copper pour** immediately beneath and surrounding the PA footprint must be a **dedicated high-density via array** (minimum 3×3, 0.4 mm drill, 1 mm pitch) connecting L1 through to L2 and L3 to spread heat into the power plane. At the 20 W maximum level this pour is the primary path for removing heat from the PA package; it must extend to cover the full PA thermal pad area and continue at least 10 mm beyond the package boundary on all sides where board space allows.
- The module PCB must be designed to conduct heat **laterally to the card guide rails and chassis wall** — do not rely solely on convection. Copper pour continuity to the PCB edges (within DRC rules) is required on all layers connected by the via array.
- **KiCad thermal relief settings:** disable thermal relief spokes on all ground pour connections in the RF zone and PA area; use solid fills only — spokes increase thermal and RF impedance.
- **Forced-air cooling:** a 120 mm fan mounted below the card cage (e.g. Noctua NF-A12x25 or equivalent) is **required for sustained 20 W operation** and is recommended for all installations. The fan provides approximately 50–80 W/m²·K convective cooling across the module surface at moderate speed, sufficient to handle the 15 W average dissipation of the 20 W PA at 50% duty cycle with margin. At the standard 5 W level passive cooling is sufficient, but the fan extends operating temperature margin and component life. Fan speed is controlled by the chassis manager via PWM using the hottest reported module temperature sensor reading.

---

## 9. Backplane Interface

Each module communicates with the host over the backplane via a **DIN 41612 Eurocard connector system**. The host side of the backplane is the **ECP5-25F PCIe interface card** in the Milk-V Megrez (primary platform); a host (secondary platform) with equivalent GPIO and I2S can take its place. Both are called **host** below. The module PCB retains the 3U Eurocard form factor (100 × 160 mm per IEC 60297).

### 9.1 Connector System

| Connector | Type | Pitch | Rating | Function |
|-----------|------|-------|--------|----------|
| **J_BACKPLANE** | Harting DIN 41612 Type C, 96-pin (3-row: a/b/c) | 2.54 mm | 2 A per signal contact; gold over nickel mating surface | I2S, SPI, GPIO, I²C, VCTCXO_TUNE, and low-current power rails (+3.3 V, +1.8 V, +5 V) |
| **J_POWER** | Harting har-bus 64 hybrid power contacts | 5.08 mm | 6–15 A per contact | +12 V PA rail — minimum one dedicated power contact per module slot; at 20 W maximum output verify contact current against peak draw (see Section 7.3 supply current note) |

Where dedicated har-bus power contacts are not used for a high-current rail, a **minimum of four signal pins in parallel** per rail is required, with matched trace widths on the module PCB.

The 96-pin DIN 41612 connector provides sufficient capacity for all current and future module signals within the pin budget. No separate data-plane connector is required or populated.

KiCad standard library includes DIN 41612 footprints; no custom footprint is required.

### 9.2 Data Transport: I2S over Backplane

The RFIC produces IQ samples as I2S audio streams (I = Left, Q = Right, 16-bit signed). At 500 kHz IQ bandwidth, the I2S bit clock is 16 MHz (500 kHz × 2 channels × 16 bits). This is a slow, deterministic serial bus — entirely compatible with routing over the DIN 41612 signal connector.

Each slot has its own I2S port on the host interface card (BCLK, LRCLK, DOUT, DIN). The RFIC is the I2S **master** by default, so BCLK and LRCLK come from the module; the RFIC can also run as slave. At 500 kSa/s with a 32 MHz reference the bit clock is 16 MHz.

For the production repeater the IQ stream is not presented to userspace via ALSA: the interface card's DMA path feeds the raw IQ samples into the ZeroMQ IPC layer (see Section 10). ALSA (as on the LinHT) is used only for bench testing.

### 9.3 Configuration: SPI over Backplane

Each module's RFIC is configured via SPI. The SPI bus is carried over the DIN 41612 signal connector. Each module has a unique chip-select line, allowing all three modules to share a single SPI bus from the host.

The SWR ADC (MCP3202) shares the same SPI bus with a dedicated chip-select line per module, or uses I²C (ADS1015 variant) on the shared I²C backplane bus.

| Signal | Direction | Notes |
|--------|-----------|-------|
| SPI_CLK | host → all modules | Shared clock, up to 10 MHz |
| SPI_MOSI | host → all modules | Shared data |
| SPI_MISO | modules → host | Tri-stated when CS inactive |
| SPI_CS_2M | host → 2 m module | Active-low chip select (RFIC) |
| SPI_CS_70CM | host → 70 cm module | Active-low chip select (RFIC) |
| SPI_CS_23CM | host → 23 cm module | Active-low chip select (RFIC) |
| SPI_CS_ADC_2M | host → 2 m module | Active-low chip select (SWR ADC, MCP3202 variant) |
| SPI_CS_ADC_70CM | host → 70 cm module | same |
| SPI_CS_ADC_23CM | host → 23 cm module | same |

### 9.4 Control Signals over Backplane

| Signal | Direction | Function |
|--------|-----------|----------|
| PTT_2M | host → module | TX enable, 2 m (step 1 in PTT sequence) |
| SW_2M | host → module | T/R switch, 2 m (step 2) |
| PA_EN_2M | host → module | PA enable, 2 m (step 3, after 1 ms delay) |
| PTT_70CM | host → module | TX enable, 70 cm |
| SW_70CM | host → module | T/R switch, 70 cm |
| PA_EN_70CM | host → module | PA enable, 70 cm |
| PTT_23CM | host → module | TX enable, 23 cm |
| SW_23CM | host → module | T/R switch, 23 cm |
| PA_EN_23CM | host → module | PA enable, 23 cm |
| ATT_LE_2M | host → module | Attenuator latch enable, 2 m |
| ATT_LE_70CM | host → module | Attenuator latch enable, 70 cm |
| ATT_LE_23CM | host → module | Attenuator latch enable, 23 cm |
| IRQ_2M | module → host | RFIC event: PLL unlock, AGC, RSSI |
| IRQ_70CM | module → host | same |
| IRQ_23CM | module → host | same |
| VCTCXO_TUNE_2M | host → module | PWM + RC filter → 0–1.8 V analog |
| VCTCXO_TUNE_70CM | host → module | same |
| VCTCXO_TUNE_23CM | host → module | same |
| TEMP_2M | module → host | I²C temperature sensor (per slot, shared I²C backplane bus) |
| TEMP_70CM | module → host | same |
| TEMP_23CM | module → host | same |

### 9.5 DIN 41612 Connector Pin Assignment

Pin designations follow the DIN 41612 / IEC 60603-2 naming convention: **rows a, b, c** (component side, viewed from the mating face); **columns 1–32**. The 96-pin Type C connector occupies columns 1–32 on all three rows.

**har-bus power contacts (J_POWER) — +12 V PA rail**

| Contact | Signal | Direction | Description |
|---------|--------|-----------|-------------|
| P1 | +12V_PA | PWR in | PA supply rail (direct backplane bus, decoupled on module); minimum one contact per slot, rated > 6 A; verify against 20 W PA peak draw per Section 7.3 |
| P2 | +12V_PA_RET | PWR return | PA return; paired with P1 |

A second har-bus contact pair may be populated for redundancy or current sharing on high-duty-cycle installs. If har-bus contacts are unavailable on a prototype backplane, use **four or more paralleled signal pins** on J_BACKPLANE with matched PCB trace widths (see paralleling note in Section 9.1).

**J_BACKPLANE — 96-pin signal connector (columns 1–16 assigned; 17–32 GND fence / reserved)**

Columns 1–8 carry power (low-current), SPI, and GPIO. Columns 9–16 carry I²C, VCTCXO, and I2S. Columns 17–32 are tied to GND on the module PCB (via-fence reference and reserved capacity).

| Pin | Signal | Direction | Description |
|-----|--------|-----------|-------------|
| a1 | GND | — | Ground |
| a2 | GND | — | Ground |
| a3 | +5V | PWR in | 5 V from backplane PSU |
| a4 | +3V3 | PWR in | 3.3 V from backplane PSU |
| a5 | +1V8 | PWR in | 1.8 V from backplane PSU |
| a6 | +3V3 | PWR in | 3.3 V (second pin for current capacity) |
| a7 | GND | — | Ground |
| a8 | GND | — | Ground |
| b1 | SPI_CLK | In | Shared SPI clock from the host (up to 10 MHz) |
| b2 | SPI_MOSI | In | SPI data from the host to RFIC and SWR ADC |
| b3 | SPI_MISO | Out | SPI data from RFIC / SWR ADC to the host (tri-state when CS inactive) |
| b4 | SPI_CS_N | In | Active-low chip select for RFIC (unique per module) |
| b5 | SPI_CS_ADC_N | In | Active-low chip select for SWR ADC (unique per module; NC if I²C ADC variant fitted). On a **duplex module**: chip select of the TX RFIC (SWR ADC is then the I²C variant) |
| b6 | ATT_LE | In | Attenuator latch enable (PE4312 parallel mode LE pin) |
| b7 | RFIC_RESET_N | In | Active-low module reset from the host. 100 kΩ pull-down on the module (reset held until the host drives it high); **inverted on the module** to the RFIC's active-high RESET (pin 9) |
| b8 | GND | — | Ground |
| c1 | RFIC_IRQ_N | Out | Active-low IRQ: PLL unlock, AGC threshold, RSSI update. From RFIC DIO1 through an open-drain buffer on the module (on a duplex module, both RFICs' DIO1 wired-OR) |
| c2 | PTT | In | TX enable from the host (step 1 in PTT sequence). To RFIC DIO3 (hardware PTT gate, active when `ptt_pin_en` is set) through the level translator; the RFIC is also set to TX over SPI |
| c3 | TR_SW | In | T/R switch control from the host (step 2 in PTT sequence) |
| c4 | PA_EN | In | PA enable from the host (step 3, after 1 ms delay) |
| c5 | ANT_SW | In | VHF/UHF band-path select on dual-band modules: high = VHF, low = UHF; 100 kΩ pull-down on module; NC on fixed-band modules (see Section 7.3, Band-path switch) |
| c6 | MOD_PRESENT | Out | Module presence detect — pulled low on module, open on empty slot |
| c7 | MOD_ID0 | Out | Module type ID bit 0 (resistor-coded: 00=2m, 01=70cm, 10=23cm, 11=dual-band 2m/70cm) |
| c8 | MOD_ID1 | Out | Module type ID bit 1 |
| a9 | GND | — | Ground |
| a10 | I2C_SCL | In | I²C clock — shared backplane bus (100 kHz); temperature sensor, EEPROM, SWR ADC (ADS1015 variant) |
| a11 | I2C_SDA | Bidir | I²C data |
| a12 | VCTCXO_TUNE | In | Analog 0–1.8 V to the module's reference oscillator (host PWM + RC filter); discipline method not decided |
| a13 | PPS_REF | In | Optional 1PPS reference input for module-local timestamp (not required for basic operation) |
| a14 | GND | — | Ground |
| a15 | GND | — | Ground |
| a16 | GND | — | Ground |
| b9 | GND | — | Ground |
| b10 | GND | — | Ground |
| b11 | GND | — | Ground |
| b12 | GND | — | Ground |
| b13 | GND | — | Ground |
| b14 | I2S_BCLK | Out | I2S bit clock from the RFIC (master, default); In when the RFIC is set to slave |
| b15 | I2S_LRCLK | Out | I2S word select (IQ sample rate, 500 kHz maximum); In when the RFIC is set to slave |
| b16 | GND | — | Ground |
| c9 | I2S_DOUT | Out | I2S data out from RFIC to the host (RX IQ: I=Left, Q=Right, 16-bit) |
| c10 | I2S_DIN | In | I2S data in to RFIC from the host (TX IQ) |
| c11–c16 | GND | — | Ground (via-fence reference) |
| a17–a32 | GND | — | Ground / reserved |
| b17–b32 | GND | — | Ground / reserved |
| c17–c32 | GND | — | Ground / reserved |

**Notes on J_BACKPLANE:**

- `MOD_PRESENT` allows the host to detect which slots are populated at boot. The host reads `MOD_ID[1:0]` and module EEPROM to learn each module's band type and PA level variant. An empty slot presents high-impedance on all lines.
- `I2C_SDA/SCL` are shared across all module slots on the backplane I²C bus. Each module has a unique I²C address for its temperature sensor, EEPROM, and (if the ADS1015 ADC variant is fitted) SWR ADC. Temperature sensors use the LM75 / TMP102 family (7-bit address set by address pins on the module).
- `VCTCXO_TUNE` is a per-module signal — each module has its own RC-filtered PWM input from a separate host PWM channel, allowing independent VCTCXO discipline per band.
- `I2S_BCLK`, `I2S_LRCLK`, `I2S_DOUT`, `I2S_DIN` are per slot — each populated module occupies one I2S port on the host interface card.
- All GPIO signals (PTT, TR_SW, PA_EN, ATT_LE, ANT_SW, RFIC_RESET_N) are 1.8 V logic driven by the host. The HT13G-M has no separate `VDD_IO`: its digital pins run at its 2.7–3.6 V supply, as on the SX1255. The module therefore has **level translators** between the backplane and the RFIC on SPI, I2S and reset. GPIO that drives only module parts is used at 1.8 V where the part accepts it — check each part's input threshold (the PE4259 example is in Section 7.3).
- `RFIC_RESET_N` stays active-low on the backplane. The module inverts it (one inverter or an NMOS) to drive the RFIC's active-high RESET pin; the RFIC's on-chip power-on reset covers power-up on its own.
- `RFIC_IRQ_N` is an open-drain output from the module; a 10 kΩ pull-up to 1.8 V is on the module PCB.
- `SPI_CS_ADC_N` is a separate chip-select for the SWR ADC (MCP3202 variant). If the I²C ADC variant (ADS1015) is fitted instead, this pin is NC and the ADC is addressed via `I2C_SDA/SCL`.
- I2S and SPI traces require continuous via fences on both sides for their full routed length, extending to within 2 mm of the connector pads (see Section 8.3).

**Module identity EEPROM**

Each module carries a small I²C EEPROM (24C02 or equivalent, 256 bytes) at a unique address determined by address pins tied to VCC or GND on the module. The EEPROM stores:

| Byte offset | Content |
|-------------|---------|
| 0x00–0x01 | Module type (0x0001 = 2 m, 0x0002 = 70 cm, 0x0003 = 23 cm, 0x0004 = dual-band 2 m / 70 cm, 0x0005 = 2 m duplex, 0x0006 = 70 cm duplex) |
| 0x02–0x03 | Hardware revision |
| 0x04–0x13 | Serial number (16 ASCII bytes) |
| 0x14–0x15 | PA level variant (0x0001 = 5 W standard, 0x0002 = 20 W maximum) |
| 0x16–0x17 | Factory calibration: VCTCXO trim offset (int16, ppb) |
| 0x18–0x1F | Factory calibration: SWR forward detector — 3-point table (voltage → dBm), 3 × int16 pairs |
| 0x20–0x27 | Factory calibration: SWR reflected detector — 3-point table (voltage → dBm), 3 × int16 pairs |
| 0x28–0x2B | Factory calibration: PA output power calibration point (uint32, dBm × 100) |
| 0x2C–0xFF | Reserved |

The `ht-module-daemon` reads this EEPROM at startup to identify each installed module, load its calibration constants, PA level variant, and VCTCXO trim starting point before GNSS discipline takes over.

### 9.6 Antenna connector options — RP-SMA or Type-N

Analog RF leaves the module T/R switch through one front-panel coax jack (a duplex module has two: RX and TX, to the cavity duplexer). The PCB layout supports **RP-SMA** (default) or **Type-N** on the same 50 Ω microstrip land. This choice affects only the faceplate RF port.

#### Default: RP-SMA

```
T/R switch ── SWR Bridge ── BPF ── RP-SMA (front panel) ── coax ── antenna
```

Standard production fitment. Use when the 3U module front panel lacks depth or clearance for a Type-N bulkhead, or when the site plan uses only short RP-SMA patch cables (bench, indoor cabinet).

#### Option: Type-N (N connector) — preferred when it fits

```
T/R switch ── SWR Bridge ── BPF ── Type-N (front panel) ── coax ── antenna
```

| Why Type-N is better (when it fits) | Detail |
|-------------------------------------|--------|
| Mechanical | Threaded mate; tolerates vibration and repeated tightening on a fixed install |
| Weather | Bulkhead jacks suit outdoor enclosures and exposed repeater cabinets |
| Coax compatibility | Natural mate to LMR-400, LMR-600, and other site feedline used on repeaters |
| Loss | Lower contribution from the connector interface at 432 MHz and 1240 MHz than RP-SMA, especially with large cable |
| Site practice | Common on commercial and amateur repeater hardware at UHF and above |
| Power handling | At 20 W output Type-N's higher power rating provides additional margin over RP-SMA |

Order **`-N`** per module when the panel cutout and enclosure depth accommodate a Type-N bulkhead and the antenna run justifies it. **23 cm** modules at permanent sites should default to Type-N unless panel constraints forbid it. **2 m** modules may remain RP-SMA on compact builds.

Type-N does **not** replace the DIN 41612 backplane connector.

**Module PCB variants:**

| Variant | Front-panel RF | PA level | When to order |
|---------|----------------|----------|---------------|
| `-SMA` (default) | RP-SMA populated | 5 W standard | Compact panel, indoor/cabinet, short patches |
| `-N` | Type-N populated | 5 W standard | Type-N fits the panel and site coax — preferred for fixed outdoor repeaters |
| `-SMA-20W` | RP-SMA populated | 20 W maximum | As `-SMA` but with 20 W PA fitted; forced-air cooling required |
| `-N-20W` | Type-N populated | 20 W maximum | Preferred variant for hilltop, portable, and high-power fixed sites |

One connector type and one PA level per module at assembly. IQ (I2S on J_BACKPLANE), SPI, GPIO, EEPROM, SWR monitoring, and ZeroMQ are unchanged between variants.

**Layout:** Type-N bulkheads need a larger panel opening and slightly more depth than RP-SMA. If the cutout cannot be made without violating the Section 8.3 λ/10 trace-length rule, stay on `-SMA` rather than forcing Type-N.

---

## 10. Software Interface: ZeroMQ IPC

In the repeater context, IQ data flows from each module RFIC through the backplane into the host, where it is processed by GNU Radio 4.0 or SDRangel. ZeroMQ (ZMQ) is used as the inter-process communication layer between the low-level hardware driver and the signal processing application.

### 10.1 Why ZeroMQ for IQ transport

ZeroMQ provides:

- **Decoupling** — the hardware driver and the signal processing application are separate processes; neither blocks the other
- **Flexibility** — the same ZMQ socket can be consumed by GNU Radio, SDRangel, a recording daemon, and a monitoring process simultaneously (PUB/SUB pattern)
- **Network transparency** — a ZMQ PUB socket can publish IQ data over TCP to a remote workstation for off-site processing or monitoring, with no code changes
- **Native GNU Radio support** — GNU Radio 4.0 includes ZMQ source and sink blocks (`gr-zeromq`) as first-class blocks

### 10.2 IQ Data Flow

```
RFIC (I2S) → DMA → ring buffer in kernel driver
                              │
                              ▼
                    ht-module-daemon (Rust)
                    │ reads ring buffer
                    │ packs IQ frames (interleaved int16 I, int16 Q)
                    │ polls SWR ADC during TX; computes SWR; auto-disables on SWR > 3.0
                    │ enforces 50% duty cycle limit at 20 W PA level
                    │ publishes on ZMQ PUB socket
                              │
                    ┌─────────┼─────────────────────────────┐
                    ▼         ▼                             ▼
             GNU Radio    SDRangel                   Recording
             ZMQ SUB      ZMQ SUB                   daemon
             Source       IQ input                  ZMQ SUB
             block        plugin
```

### 10.3 ZeroMQ Socket Layout

| Socket | Pattern | Address | Direction | Contents |
|--------|---------|---------|-----------|----------|
| `ipc:///run/ht-module/iq_A` | PUB | local | Module A -> consumers | Raw IQ, int16 interleaved, 500 kHz |
| `ipc:///run/ht-module/iq_B` | PUB | local | Module B -> consumers | Raw IQ, int16 interleaved, 500 kHz |
| `ipc:///run/ht-module/iq_C` | PUB | local | Module C -> consumers | Raw IQ, int16 interleaved, 500 kHz |
| `ipc:///run/ht-module/iq_D` | PUB | local | Module D -> consumers | Raw IQ, int16 interleaved, 500 kHz |
| `ipc:///run/ht-module/iq_E` | PUB | local | Module E -> consumers | Raw IQ, int16 interleaved, 500 kHz |
| `ipc:///run/ht-module/tx_A` | SUB | local | GNU Radio -> module A | TX IQ data stream |
| `ipc:///run/ht-module/tx_B` | SUB | local | GNU Radio -> module B | TX IQ data stream |
| `ipc:///run/ht-module/tx_C` | SUB | local | GNU Radio -> module C | TX IQ data stream |
| `ipc:///run/ht-module/tx_D` | SUB | local | GNU Radio -> module D | TX IQ data stream |
| `ipc:///run/ht-module/tx_E` | SUB | local | GNU Radio -> module E | TX IQ data stream |
| `ipc:///run/ht-module/ctrl` | REQ/REP | local | Any process -> daemon | Per-module: frequency, gain, PTT, squelch, TX timeout, attenuator, PA level, duty cycle watchdog, SWR query, fault clear ([zeromq-messages.md](zeromq-messages.md)) |
| `ipc:///run/ht-module/status` | PUB | local | Daemon -> consumers | RSSI, AGC state, PLL lock, temperature, SWR, forward/reflected power, PA level, duty cycle, fault state |

For remote monitoring or distributed processing, IPC sockets can be exposed as TCP sockets by changing the address to `tcp://0.0.0.0:<port>` — no other code changes required.

### 10.4 Frame Format

Full binary layout, control commands, status JSON (including SWR and PA level fields), and gr-ident integration:
**[zeromq-messages.md](zeromq-messages.md)**.

IQ frames are published as length-prefixed binary messages:

```
[ 8 bytes: uint64 timestamp (nanoseconds, GNSS-disciplined) ]
[ 4 bytes: uint32 module identifier (0=A, 1=B, 2=C, 3=D, 4=E) ]
[ 4 bytes: uint32 sample count in this frame ]
[ N×4 bytes: int16 I, int16 Q interleaved, little-endian ]
```

The 64-bit nanosecond timestamp uses the system clock disciplined by chrony + GNSS PPS (see Section 6 of the main system document), providing accurate cross-band timing for any synchronisation analysis.

### 10.5 `ht-module-daemon` Functions

> **Implementation status:** Specified here and in [zeromq-messages.md](zeromq-messages.md). Source code is **not** in the SDR-repeater repository; implement in a separate **Rust** repo per [implementation-language.md](implementation-language.md) and [repo-map.md](repo-map.md).

The `ht-module-daemon` is a single Rust daemon responsible for:

- Initialising all module RFICs via SPI on startup (HT13G-M register map, not the SX1255's); loading SWR calibration tables and PA level variant from each module's EEPROM
- Reading module temperature sensors via I²C (backplane bus) and publishing via status socket; forwarding temperature readings to the chassis fan controller
- Managing the PTT sequence (hardware-enforced order: RFIC PTT → T/R switch → 1 ms delay → PA enable) in response to `ctrl` socket commands
- Setting attenuator values via SPI in response to `ctrl` socket commands
- **Enforcing 50% duty cycle at 20 W PA level:** tracking cumulative TX time per module within a rolling 10-second window; refusing PTT assert if the duty cycle limit would be exceeded; publishing `duty_cycle_limit` alert on the `status` socket when the limit is approached or reached; logging the event. This limit is active regardless of mode or signal type.
- **Enforcing transmit inhibit at 55°C board temperature:** immediately de-asserting PA_EN, TR_SW, and PTT on any module whose temperature sensor exceeds 55°C; setting `fault_reason: "over_temp"`; blocking PTT until temperature drops below 50°C and the operator clears the fault via `MOD_CLEAR_FAULT`
- **Polling the SWR ADC on each transmitting module** at regular intervals during TX (recommended: every 100 ms); computing SWR from forward and reflected detector voltages using the EEPROM calibration table; publishing `swr`, `fwd_w`, and `ref_w` in the `status` JSON
- **Auto-disabling any module whose SWR exceeds 3.0:** immediately de-asserting PA_EN, TR_SW, and PTT in that order; setting the module's fault state; publishing a `swr_high` alert; blocking subsequent PTT commands until `MOD_CLEAR_FAULT` is received
- Managing VCTCXO frequency discipline: reading GNSS 1PPS interrupt from the host GPIO, computing correction, updating PWM duty cycle for each module's VCTCXO_TUNE input
- Monitoring RFIC IRQ lines (PLL unlock, AGC threshold events) and publishing alerts via `status` socket
- Routing TX IQ from ZMQ SUB to the interface card's DMA TX path
- Changing `ANT_SW` on dual-band modules only in RX state (Section 7.3)

RX DC-offset and IQ-imbalance correction and TX pre-correction are **not** in the RFIC; they run in the host signal chain (GNU Radio 4 blocks, planned under `host/gr4/`).

This mirrors the `ht13g-spi` CLI and HT Daemon described in the OpenHT-DB software stack, adapted for three independent modules and the absence of display/keypad/audio hardware.

### 10.6 GNU Radio Integration

A GNU Radio OOT (out-of-tree) module `gr-ht13g` provides:

- `ht13g_source` — ZMQ SUB block; receives IQ from `ht-module-daemon`; outputs `complex float` stream
- `ht13g_sink` — ZMQ PUB block; accepts `complex float` TX stream; sends to daemon
- `ht13g_ctrl` — Python block; sends control commands (frequency, PTT, gain, PA level, fault clear) via `ctrl` REQ/REP socket
- `ht13g_monitor` — Python block; subscribes to `status` PUB socket; exposes RSSI, SWR, PLL lock, PA level, duty cycle, and fault state as GRC variables for flowgraph-level monitoring and alerting

For cross-band repeat (e.g. receive on module A, 2 m, retransmit on module B, 70 cm), a single GNU Radio flowgraph subscribes to `iq_A`, demodulates, re-encodes, and publishes to `tx_B`. The daemon handles T/R switching, duty cycle enforcement, and SWR protection for each module independently, with no coordination required between modules in the flowgraph.

---

## 11. Path to Silicon

**No fabrication is planned in this phase.** The development chain stops before fabrication: the design is prepared for human review and for an RF engineer, and any submission is a separate decision by the project owner after that review.

Status (see [HANDOFF.md](HANDOFF.md)):

- HT13G-M digital back end (Phase 1): signed off on IHP SG13G2, about 0.34 mm².
- Analogue part (Phases 2–4): requirements in [spec/rf-frontend.md](../spec/rf-frontend.md); the phase-noise simulation for the VCO is validated ([analog/pn-validation/](../analog/pn-validation/README.md)).
- HT13G-S: deferred.

Background kept from r0.3, for whoever makes the fabrication decision later: IHP OpenMPW community slots are 2 mm², and SG13G2 turn-around is about 8 months. Validating the receive chain on its own (LNA, mixer, ADC) before a full die is the lower-risk order. The single-chain HT13G-M removes the r0.3 "dual-chain integration" step.

---

## 12. Risk Register

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| HT13G-M LO phase noise at the duplex offset | Medium | ≤ −136 dBc/Hz at 600 kHz / 2 MHz from a 3.12–4.20 GHz VCO divided by 24 / 8; VACASK `pnoise` validated for the VCO design (thermal region; flicker region still open) |
| DC offset in zero-IF VHF chain | Medium–High | Standard direct-conversion challenge; corrected on the host (no on-chip loop since 2026-10); host correction must track temperature and gain changes |
| IQ imbalance at 1240 MHz (HT13G-S) | Medium–High | L-band IQ balance harder than VHF/UHF; corrected on the host, as for HT13G-M |
| Die area for a full HT13G-M | Open | No fabrication in this phase; digital back end 0.34 mm²; analogue area to be estimated in Phases 2–4 |
| VHF on the LinHT | Medium | The drop-in gives UHF only on the current board; VHF needs a harmonic filter, PA match, RX match and band switch ([spec/rf-frontend.md](../spec/rf-frontend.md) §8) |
| RFIC I/O level against the 1.8 V backplane | Low | Level translators on the module (Section 9.5 notes) |
| PA-side band switching on dual-band modules | Medium | PE4259 only on the low-power side; the PA side needs a part rated for full power, or a diplexer after per-band filters (Section 7.3) |
| Backplane PTT / IRQ without RFIC pins | Low–Medium | The SX1255 pin-out has neither; open item 2 in Section 5.9 |
| 20 W PA thermal dissipation on module | Medium–High | 40% efficiency → ~30 W instantaneous, ~15 W average at 50% duty cycle; dedicated PA copper pour with high-density via array (3×3 minimum, 0.4 mm drill, 1 mm pitch, L1–L3); L1/L6 ground pour heatspreading to card guides and chassis wall per Section 8.5; 120 mm fan below card cage required for 20 W operation; firmware transmit inhibit at 55°C board temperature; 50% duty cycle enforced by daemon |
| 5 W PA thermal dissipation on module | Low | 40% efficiency → ~7.5 W; within passive cooling budget with copper pour heatspreading; fan extends margin |
| 20 W filter and coupler component ratings | Medium | Peak voltage ~45 V and peak current ~900 mA at 20 W; 30 V capacitors (adequate at 5 W) insufficient — 100 V rated capacitors required; inductor current rating > 2 A; coupler power rating > 25 W; verify all TX-path passive component ratings before assembly |
| 20 W PA supply current on har-bus contacts | Low | Peak ~4.2 A per slot at +12 V; within har-bus 64 contact rating; verify PSU total capacity when multiple 20 W modules transmit simultaneously |
| T/R switch power handling at 20 W | Low–Medium | PE42820 has no margin at 20 W; 20 W variant uses a PIN switch rated ≥ 50 W with its bias supply; verify at SWR 3; parts in [rf-switches-and-filters.md](rf-switches-and-filters.md) |
| SWR bridge directivity at VHF (144 MHz) | Medium | Toroidal transformer couplers at VHF can exhibit reduced directivity below 150 MHz; validate directivity at 144 MHz on bench; adjust winding ratio or use transmission-line coupler if directivity < 20 dB |
| SWR detector calibration drift with temperature | Low–Medium | Schottky detector diodes have temperature-dependent characteristics; three-point calibration table in EEPROM covers nominal temperature; consider two-temperature calibration table in future EEPROM revision |
| PE4312 insertion loss at 1240 MHz | Low | Rated to 4 GHz; at 1.24 GHz insertion loss rises slightly but remains < 2 dB; acceptable for system NF budget |
| DIN 41612 I2S signal integrity over backplane | Low | I2S at 16 MHz bit clock is well within DIN 41612 routing capability; series termination 33 Ω; mandatory via fences on I2S and SPI traces per Section 8.3 |
| ZMQ IPC latency causing TX audio artefacts | Low | ZMQ PUB/SUB is sub-millisecond at localhost; hardware PTT sequencing (1 ms delay) already dominates latency |
| SG13G2Cu BEOL availability for 23 cm VCO inductors | Medium | Standard Al BEOL thick layer may suffice; Cu BEOL option available from IHP at additional cost if Q is insufficient |
| T/R and band switch availability | Low | Several makers (pSemi, Skyworks, MACOM, Mini-Circuits); alternatives listed in [rf-switches-and-filters.md](rf-switches-and-filters.md) |

---

## 13. Open Licensing

All design work produced for this project follows the same licensing as the OpenHT-DB source project from which the RFIC specification is adapted.

| Asset | License |
|-------|---------|
| Module PCB design (KiCad) | CERN OHL-S v2 |
| RFIC design (GDS / Xschem / ngspice) | Apache 2.0 (matching IHP PDK) |
| `ht-module-daemon` (Rust) | GPL-3.0-or-later |
| `repeater-supervisord` / `repeater-authd` (Rust) | GPL-3.0-or-later |
| `gr-ht13g` GNU Radio OOT blocks | GPL v3 |
| Documentation | CC-BY-SA 4.0 |

RFIC measurement results from OpenMPW submissions are published as open data per the IHP OpenMPW program participation agreement.
