# SDR Repeater — RF Module and RFIC Specification

**Document:** Module RF Hardware Design Specification  
**Revision:** 0.1  
**Date:** May 2026  
**Relates to:** SDR Multiband Repeater System Design v1.1  

---

## Table of Contents

1. [Design Context and Rationale](#1-design-context-and-rationale)
2. [Why a Custom RFIC](#2-why-a-custom-rfic)
3. [Fabrication Process: IHP SG13G2](#3-fabrication-process-ihp-sg13g2)
4. [RFIC Family Overview](#4-rfic-family-overview)
5. [HT13G-M RFIC — 2 m / 70 cm Module](#5-ht13g-m-rfic--2-m--70-cm-module)
6. [HT13G-S RFIC — 23 cm Module](#6-ht13g-s-rfic--23-cm-module)
7. [RF Signal Chain — Per Module](#7-rf-signal-chain--per-module)
8. [Module PCB Architecture](#8-module-pcb-architecture)
9. [Backplane Interface](#9-backplane-interface)
10. [Software Interface: ZeroMQ IPC](#10-software-interface-zeromq-ipc)
11. [MPW Tapeout Strategy](#11-mpw-tapeout-strategy)
12. [Risk Register](#12-risk-register)
13. [Open Licensing](#13-open-licensing)

---

## 1. Design Context and Rationale

The repeater system described in the companion document uses three pluggable radio modules on a 3U OpenVPX backplane:

- Module A — 2 metre: 144–146 MHz, 500 kHz IQ bandwidth, 5 W TX
- Module B — 70 cm: 432–438 MHz, 500 kHz IQ bandwidth, 5 W TX
- Module C — 23 cm: 1240–1258 MHz, 500 kHz IQ bandwidth, 5 W TX

Each module is a self-contained PCB that plugs into a VITA 46 edgecard slot on the backplane. It carries its own RFIC, RF front end, power amplifier, band-pass filter, T/R switch, variable attenuator, and external LNA. IQ data is transported digitally over the backplane data bus. The default antenna interface is front-panel **RP-SMA**; optional **Type-N** jacks are preferred where panel space and the site coax plan allow (see [Section 9.5](#95-antenna-connector-options-rp-sma-or-type-n)).

This document specifies the RFIC(s) for these modules and the surrounding RF signal chain.

### Key differences from the OpenHT-DB handheld design

The repeater module context differs from a handheld transceiver in several important ways:

| Parameter | OpenHT-DB handheld | Repeater module |
|-----------|-------------------|-----------------|
| Form factor | Single PCB, battery-powered | VITA 46 edgecard, backplane-powered |
| IQ interface | I2S to iMX93 SoM on same PCB | I2S over backplane VITA 46 to SpacemiT K3 |
| Audio hardware | Codec, mic, headphone | Present on module PCB — used for bench test and optional monitoring |
| Display / keypad | On chassis | Not on module — on chassis manager or remote |
| ALSA | Required (audio output to user) | Available; used for bench testing and optional direct monitoring |
| Battery / charging | On-board BMS + USB-C PD | External DC from backplane VITA 62 rails |
| USB-A (security token) | On-board | On main SBC via backplane; Nitrokey token plugged into K3 USB-A |
| Bands per PCB | Dual (VHF + UHF) | Single band per module |
| GNSS on module | No — on main SBC | No — on main SBC |

All hardware present in the OpenHT-DB design is retained on the module PCB. The audio codec, microphone header, and headphone/line output are populated on all variants. In repeater operation they provide an optional audio monitoring tap and greatly simplify bench testing — an operator can plug a PC soundcard into the 3.5 mm jack during bring-up without needing the full backplane. The 3.5 mm jack is present and populated on all builds; there is no DNP variant.

---

## 2. Why a Custom RFIC

No existing commodity RFIC adequately covers all three bands (144 MHz, 432 MHz, 1240 MHz) with sufficient IQ bandwidth, low noise figure, a clean open digital interface, and power consumption appropriate for a modular embedded Linux SDR platform. The following table summarises the commodity chip gap:

| Chip | 144 MHz | 432 MHz | 1240 MHz | IQ BW | Disqualifier |
|------|:-------:|:-------:|:--------:|-------|-------------|
| SX1255 | ✗ | ✓ | ✗ | 500 kHz | 400 MHz lower limit; no VHF |
| CC1200 | ✓ | ✓ | ✗ | ~200 kHz | Bandwidth too narrow; no 23 cm |
| AT86RF215 | ✗ | ✓ | ✗ | 4 MHz | 400 MHz lower limit; no VHF or 23 cm |
| AD9361 | ✓ | ✓ | ✓ | 56 MHz | Power and size prohibitive; 3.3 W typical |
| Si4463/Si4468 | ✓ | ✓ | ✗ | ~1 MHz | Obsolete architecture; no clean IQ stream; no 23 cm |
| RFFC5072 | ✓ | ✓ | partial | wide | Mixer-only; requires external LNA/VCO/ADC |
| MAX2769 | ✗ | ✗ | ✓ | narrow | GNSS receiver only; not a transceiver |

No commodity part covers the full 130 MHz–1300 MHz range with ≥500 kHz IQ bandwidth, sub-5 dB noise figure, full-duplex per band, and an I2S digital baseband interface compatible with Linux. A custom RFIC is the only clean path.

The approach taken here — one dedicated RFIC per module, each covering one amateur band — avoids the power and complexity penalties of a wideband transceiver covering all three bands simultaneously. Each module is a focused, optimised design.

---

## 3. Fabrication Process: IHP SG13G2

**IHP Microelectronics, Frankfurt (Oder), Germany** provides the only open-source PDK for a production-grade SiGe BiCMOS process. All three module RFICs are targeted to this process.

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

IHP runs regular OpenMPW shuttle batches for the SG13G2 process. Each community slot is 2 mm². Based on the published 2025–2026 schedule, shuttles have run approximately every 1–2 months with tapeout deadlines in April, May, July, and September 2025, and an SG13G2 MPW run scheduled for October 2026. Turn-around time is approximately 8 months for SG13G2.

The single-chain die for each band (Section 11 tapeout strategy) is sized to fit within the 2 mm² community slot, making the design accessible to independent validation before any commercial production run.

### Fallback process

The design is intended to be portable to **GlobalFoundries 8XP** (commercial 130 nm SiGe BiCMOS) should production volume require it. The device models at this frequency are comparable, and the circuit topology is not process-specific at sub-1.5 GHz.

---

## 4. RFIC Family Overview

Two RFIC variants are specified, covering all three repeater bands:

| RFIC | Bands covered | Module(s) |
|------|--------------|-----------|
| **HT13G-M** | 130–175 MHz (VHF) + 400–480 MHz (UHF) — dual chain | 2 m module + 70 cm module (one chip, two independent chains) |
| **HT13G-S** | 1200–1300 MHz (L-band / 23 cm) — single chain | 23 cm module |

The HT13G-M is the dual-chain variant adapted from the OpenHT-DB handheld specification, with the handheld-specific interfaces (audio codec, display, battery management) removed and the backplane interfaces (I2S over VITA 46, SPI configuration, ZeroMQ IPC) substituted.

The HT13G-S is a new single-chain design targeting the 23 cm band. The SiGe HBT process easily covers 1.2–1.3 GHz; this is well within the transistor's capabilities at fT of 300 GHz.

---

## 5. HT13G-M RFIC — 2 m / 70 cm Module

This chip is used on both the 2 m module (VHF chain only active) and the 70 cm module (UHF chain only active). Both chains are present on silicon; the inactive chain is powered down via SPI. This approach reuses a single die across two modules, reducing NRE cost and simplifying the OpenMPW submission.

### 5.1 Architecture

Both RX and TX chains use direct-conversion (zero-IF) IQ architecture. Each chain is fully independent: separate LNA, separate PLL/VCO, separate Σ-Δ ADC and DAC, separate I2S port. There is no shared LO between the VHF and UHF chains, providing > 60 dB inter-chain isolation.

```
                    ┌─────────────────────────────────────────────────────┐
                    │                  HT13G-M RFIC                       │
                    │                                                     │
  RF_VHF_IN ───────►│ BPF → LNA_V → IQ Mixer → Σ-Δ ADC → I2S_VHF OUT  │
                    │         ↑                                           │
                    │      PLL_V (130–175 MHz, 32 MHz ref)               │
                    │         ↓                                           │
  RF_VHF_OUT ◄──────│ BPF ← PA Driver ← IQ Mod ← Σ-Δ DAC ← I2S_VHF IN │
                    │                                                     │
  RF_UHF_IN ───────►│ BPF → LNA_U → IQ Mixer → Σ-Δ ADC → I2S_UHF OUT  │
                    │         ↑                                           │
                    │      PLL_U (400–480 MHz, 32 MHz ref)               │
                    │         ↓                                           │
  RF_UHF_OUT ◄──────│ BPF ← PA Driver ← IQ Mod ← Σ-Δ DAC ← I2S_UHF IN │
                    │                                                     │
                    │ SPI config · RSSI · AGC · TEMP · IRQ               │
                    │ VCTCXO_TUNE (0–1.8 V analog)                       │
                    └─────────────────────────────────────────────────────┘
```

### 5.2 Receive Path Specifications

| Parameter | VHF Chain | UHF Chain | Notes |
|-----------|-----------|-----------|-------|
| Frequency range | 130–175 MHz | 400–480 MHz | Covers 2 m and 70 cm globally |
| Architecture | Zero-IF direct conversion IQ | same | |
| LNA topology | Common-emitter SiGe HBT, inductively degenerated | same | |
| Noise figure | < 5 dB | < 4 dB | At matched 50 Ω, 25°C |
| Input impedance | 50 Ω | 50 Ω | External matching network on module PCB |
| IIP3 | > −5 dBm | > −5 dBm | |
| LNA gain | 12–20 dB, 4 programmable steps via SPI | same | |
| Image rejection | > 40 dBc | > 40 dBc | DC offset correction loop required |
| ADC architecture | 1-bit Σ-Δ, 38.4 MHz oversampled, decimated | same | |
| ADC output word | 16-bit I + 16-bit Q signed | same | |
| Sample rates | 25 / 50 / 100 / 200 / 500 kHz selectable | same | |
| Max IQ bandwidth | 500 kHz | 500 kHz | |
| DC offset cancellation | Digital feedback loop, programmable time constant | same | |
| IQ imbalance | < 1 dB amplitude, < 2° phase post-calibration | same | |
| RSSI | 8-bit, ±2 dB, SPI-readable | same | |
| AGC | Programmable threshold + step; manual SPI override | same | |

### 5.3 Transmit Path Specifications

| Parameter | VHF Chain | UHF Chain | Notes |
|-----------|-----------|-----------|-------|
| Architecture | Direct IQ upconversion | same | |
| DAC architecture | 1-bit Σ-Δ interpolating | same | |
| Input sample rates | 25 / 50 / 100 / 200 / 500 kHz | same | |
| Output power (chip) | 0 ± 2 dBm into 50 Ω | same | External 5 W PA on module PCB |
| Harmonic suppression | > 25 dBc | > 25 dBc | Module PCB band filter brings this to > 60 dBc |
| TX/RX isolation | > 40 dB | > 40 dB | On-chip switch + external T/R switch on module |
| PA driver current | Programmable 0 / 50 / 100% via SPI | same | |

### 5.4 PLL / Frequency Synthesis

| Parameter | VHF PLL | UHF PLL |
|-----------|---------|---------|
| Architecture | Integer-N + fractional Σ-Δ extension | same |
| VCO range | 130–175 MHz direct | 400–480 MHz direct |
| Reference | 32 MHz shared VCTCXO (on module PCB) | same |
| VCTCXO tune input | 0–1.8 V analog, ±50 ppm pull | — |
| Phase noise @ 10 kHz offset | < −90 dBc/Hz | < −95 dBc/Hz |
| Lock time | < 1 ms | < 1 ms |
| Frequency resolution | < 100 Hz | < 100 Hz |
| Frequency word | 32-bit via SPI | same |
| Inter-chain isolation | > 60 dB — fully independent PLLs | |

### 5.5 Digital Interface

| Signal | Description |
|--------|-------------|
| I2S_VHF: BCLK / LRCLK / DOUT / DIN | VHF IQ stream; I = Left, Q = Right; 16-bit frames |
| I2S_UHF: BCLK / LRCLK / DOUT / DIN | UHF IQ stream; identical format |
| SPI: CLK / MOSI / MISO / CS | Shared configuration bus; up to 10 MHz |
| PTT_VHF / PTT_UHF | Active-high TX enable per chain; hardware path < 1 µs |
| IRQ | Active-low: PLL unlock, AGC threshold, RSSI update |
| RESET_N | Active-low chip reset |
| VCTCXO_TUNE | Analog in 0–1.8 V; disciplines shared 32 MHz reference |

### 5.6 Power

| Rail | Voltage | RX current | TX current |
|------|---------|------------|------------|
| VDD_RF | 3.3 V | 55 mA (both chains) | 80 mA |
| VDD_CORE | 1.2 V (internal LDO) | 20 mA | 25 mA |
| VDD_IO | 1.8 V or 3.3 V selectable | 5 mA | 5 mA |
| **Total** | | **~265 mW** | **~363 mW** |

On a repeater module, the inactive chain is powered down via SPI register: the 2 m module powers down the UHF chain, the 70 cm module powers down the VHF chain.

### 5.7 Package

- QFN-48, 6×6 mm, 0.5 mm pitch
- Exposed thermal/RF ground pad (EPAD); minimum 9-via array to L2
- WLCSP variant possible after silicon validation

---

## 6. HT13G-S RFIC — 23 cm Module

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
| Output power (chip) | 0 ± 2 dBm into 50 Ω | External 5 W PA on module PCB |
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

Identical to HT13G-M for SPI, PTT, IRQ, RESET_N, and VCTCXO_TUNE. Single I2S port (I2S_23CM) instead of two.

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

```
ANT (RP-SMA, front panel)
    │
    ▼
T/R Switch (SPDT, solid-state)
    │                 │
    ▼ (RX path)       ▼ (TX path)
Variable Attenuator   Band-Pass / Harmonic Filter
(0–31.5 dB, 0.5 dB step)   (7-element Chebyshev, > 60 dBc)
    │                 │
    ▼                 ▲
External LNA          Power Amplifier (5 W)
(NF < 0.8 dB)            │
    │                 ▲
    ▼                 │
  [RFIC RX input]  [RFIC TX output]
```

### 7.2 Component Specifications

#### T/R Switch (Solid-state, per band)

| Parameter | VHF (144 MHz) | UHF (432 MHz) | 23 cm (1240 MHz) |
|-----------|:-------------:|:-------------:|:----------------:|
| Type | SPDT | SPDT | SPDT |
| Part (candidate) | SKY13351-378LF | SKY13351-378LF | SKY13384-350LF or PE4259 |
| Frequency | DC–3 GHz | DC–3 GHz | DC–3 GHz |
| Insertion loss | < 0.5 dB | < 0.5 dB | < 0.6 dB |
| TX→RX isolation | > 30 dB | > 30 dB | > 28 dB |
| Power handling | > 1 W continuous | > 1 W continuous | > 1 W continuous |
| Switching time | < 1 µs | < 1 µs | < 1 µs |
| Control | 2 GPIO from SpacemiT K3 (via backplane) | same | same |

The T/R switch is a key reliability element. Solid-state (PIN diode or CMOS SOI) switching is mandatory — no mechanical relays. All three bands can use the SKY13351 or its equivalent; at 1240 MHz insertion loss is slightly higher but remains acceptable.

**PTT sequencing is hardware-enforced:**

1. RFIC PTT assert (< 1 µs) — disables LNA path, enables TX DAC
2. T/R switch → TX position (< 1 µs)
3. 1 ms hardware delay
4. PA enable assert

On TX→RX transition the sequence reverses: PA de-assert → T/R switch RX → RFIC PTT release. This ensures the external LNA is never exposed to PA output power.

#### Variable Attenuator (RX path, per band)

| Parameter | Value |
|-----------|-------|
| Part | pSemi PE4312 (1 MHz–4 GHz, valid for all three bands) |
| Range | 0–31.5 dB, 0.5 dB steps |
| Insertion loss at 0 dB | < 1 dB |
| Control | 6-bit SPI or parallel; latch enable from module GPIO |
| Purpose | Extends AGC range; prevents RFIC saturation on strong local signals |
| Supply | 3.3 V |

The PE4312 covers DC–4 GHz, making it suitable for all three bands with a single part number. At 1240 MHz, insertion loss increases slightly from the 1 MHz spec but remains under 1 dB.

#### External LNA (RX path, per band)

| Parameter | VHF / UHF | 23 cm |
|-----------|-----------|-------|
| Part (candidate) | PGA-103+ (Mini-Circuits) or BFP840ESD (Infineon) | BFP840ESD or MGFC4919G |
| Noise figure | < 0.8 dB | < 1.0 dB |
| Gain | 16–20 dB | 14–18 dB |
| Bias | 3.3 V, set by on-module bias resistor | same |
| Placement | Immediately after T/R switch, before attenuator | same |

The external LNA defines the system noise figure, which is dominated by the first active stage. Placing the LNA before the attenuator means the attenuator's insertion loss and the RFIC's noise figure are both divided by the LNA gain when referred to the input — a critical system noise figure improvement.

#### Power Amplifier (TX path, per band, 5 W output)

| Parameter | VHF | UHF | 23 cm |
|-----------|-----|-----|-------|
| Target output | 5 W (37 dBm) | 5 W (37 dBm) | 5 W (37 dBm) |
| Input power | 0 dBm from RFIC | same | same |
| Required gain | ~37 dB (two-stage) | ~37 dB | ~37 dB |
| Architecture | Driver + GaAs or LDMOS final | same | GaAs MMIC |
| Supply | 3.3–5 V from module power rail (regulated) | same | same |
| Efficiency | > 40% Class AB | > 40% | > 35% |
| Candidate ICs | VHF: RA07H1317M | UHF: RA07H4047M | 23 cm: RA07H1213M or MAAMSS0060 |
| Enable | GPIO from SpacemiT K3 via backplane, sequenced after T/R switch | same | same |

At 5 W output with 40% efficiency, the PA draws approximately 3.4 A at its supply voltage. The PA supply is provided directly from the backplane +12 V rail with no linear regulator in series — a linear regulator at this current would dissipate > 1.5 W as heat. Decoupling immediately at the PA supply pin: 220 µF electrolytic + 100 µF ceramic + 100 nF ceramic, placed within 2 mm of the supply pin.

#### Band-Pass / Harmonic Filter (TX path, per band)

A 7-element Chebyshev band-pass filter is placed between the PA output and the T/R switch. It carries full TX power; component ratings must reflect this.

| Parameter | VHF filter | UHF filter | 23 cm filter |
|-----------|-----------|-----------|-------------|
| Passband | 130–175 MHz | 400–480 MHz | 1200–1300 MHz |
| Insertion loss | < 0.8 dB | < 0.8 dB | < 1.0 dB |
| Harmonic rejection (2nd) | > 60 dBc | > 60 dBc | > 60 dBc |
| Harmonic rejection (3rd+) | > 70 dBc | > 70 dBc | > 65 dBc |
| Implementation | SMD LC, 0402, tuned at assembly | same | same; consider hairpin microstrip at 1.24 GHz |
| Component ratings | Inductor > 1 A; capacitor > 30 V | same | same |
| PCB footprint | ~25 × 8 mm | ~20 × 8 mm | ~15 × 6 mm |

---

## 8. Module PCB Architecture

Each module is a single PCB on a 3U OpenVPX edgecard form factor (~100 × 100 mm usable area, 160 mm pitch per VITA 46 standard). The module is self-contained: all RF components, RFIC, power conditioning, and backplane interface logic are on-board.

### 8.1 Layer Stack (6-layer, identical for all three modules)

| Layer | Function |
|-------|----------|
| L1 top | RF routing + all RF components (RFIC, LNA, PA, filters, switches, attenuator) |
| L2 | Solid ground plane — unbroken RF reference; via-stitched at RF zone perimeter |
| L3 | Power distribution — 3.3 V, 5 V, 12 V PA rail |
| L4 | Secondary power + slow signals — SPI, I2S, GPIO, I²C |
| L5 | Solid ground plane — shielding between digital and RF |
| L6 bottom | Backplane interface — VITA 46 connector signals, PCIe/GbE routing |

### 8.2 Board Zoning

```
┌─────────────────────────────────────────────────────────────┐
│  RF ZONE (L1, via-fence boundary)                           │
│  RFIC · External LNA · PA (5W) · BPF · T/R Switch          │
│  Variable Attenuator · 50 Ω microstrip L1                   │
├────────────────────────────────────┬────────────────────────┤
│  MIXED ZONE                        │  DIGITAL ZONE          │
│  VCTCXO 32 MHz                     │  VITA 46 edgecard      │
│  VCTCXO_TUNE RC filter             │  connector area        │
│  SPI / I2S traces (short,          │  PCIe / GbE PHY        │
│  series-terminated 33 Ω)           │  Power conditioning    │
│  RP-SMA (front panel)              │  Module control FPGA   │
│  Power regulators                  │  (optional, per rev)   │
└────────────────────────────────────┴────────────────────────┘
│  VITA 46 EDGECARD CONNECTOR (bottom edge)                   │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 RF Signal Routing Rules

| Rule | Value | Reason |
|------|-------|--------|
| 50 Ω microstrip width on L1 (FR4, L1→L2 ~0.18 mm) | ~0.35 mm | Impedance match throughout RF chain |
| Max trace length between RF components | < λ/10 at operating frequency | Minimise stub effects; at 1240 MHz λ/10 ≈ 24 mm |
| Bend style | 45° or curved; no 90° | Impedance discontinuity |
| Component size in RF path | 0402 max; 0201 preferred above 300 MHz | Minimise parasitic inductance |
| RFIC EPAD via array | 9 vias minimum (3×3) | RF and thermal ground |
| PA ground vias | Immediately adjacent to PA ground pad | Minimise source inductance |
| BPF placement | Immediately after PA output, before T/R switch | Harmonics filtered before reaching antenna path |
| RP-SMA connector | Front-panel edge mount; coax land on L1 (default `-SMA` variant) | Use when panel space is tight or cables are short RP-SMA patches |
| Type-N connector | Front-panel bulkhead; same coax land (`-N` variant) | **Preferred when it fits** — fixed sites, outdoor enclosures, large coax |
| Shield cans | Press-fit SMD cans over RF zone (Würth or Laird) | Strongly recommended for production |

### 8.4 Test Points and Audio Monitoring

Every module exposes the following test points for bench characterisation and audio monitoring:

- RF test point between attenuator output and RFIC RX input (SMA footprint, unpopulated)
- RF test point between RFIC TX output and PA input (SMA footprint, unpopulated)
- SPI header (2×4, 2.54 mm) for RFIC direct configuration
- I2S header (1×6, 2.54 mm) for direct audio capture during testing
- **3.5 mm TRRS audio jack (populated on all variants)** — carries stereo IQ (I = Left, Q = Right) at baseband; allows direct monitoring or capture via any PC soundcard without the full backplane. Pinout follows Kenwood convention for compatibility with existing test equipment. In repeater operation, this port is available as a live audio monitoring tap.

---

## 9. Backplane Interface

Each module communicates with the SpacemiT K3 compute module over the VITA 46 backplane fabric.

### 9.1 Data Transport: I2S over VITA 46

The RFIC produces IQ samples as I2S audio streams (I = Left, Q = Right, 16-bit signed). At 500 kHz IQ bandwidth, the I2S bit clock is 16 MHz (500 kHz × 2 channels × 16 bits). This is a slow, deterministic serial bus — entirely compatible with routing over the VITA 46 utility plane or a dedicated serial lane.

On the SpacemiT K3, each I2S stream maps to one SAI (Synchronous Audio Interface) peripheral:

| Module | RFIC I2S port | K3 SAI peripheral | ALSA device |
|--------|--------------|-------------------|-------------|
| 2 m | I2S_VHF | SAI1 | hw:0 (bench testing only) |
| 70 cm | I2S_UHF | SAI2 | hw:1 (bench testing only) |
| 23 cm | I2S_23CM | SAI3 | hw:2 (bench testing only) |

For the production repeater, the I2S streams are not presented to userspace via ALSA. Instead, a kernel driver or DMA path feeds the raw IQ samples directly into the ZeroMQ IPC layer (see Section 10). ALSA mapping is used only during bench testing.

### 9.2 Configuration: SPI over VITA 46

Each module's RFIC is configured via SPI. The SPI bus is carried over the VITA 46 utility plane (J0). Each module has a unique chip-select line, allowing all three modules to share a single SPI bus from the K3.

| Signal | Direction | Notes |
|--------|-----------|-------|
| SPI_CLK | K3 → all modules | Shared clock, up to 10 MHz |
| SPI_MOSI | K3 → all modules | Shared data |
| SPI_MISO | modules → K3 | Tri-stated when CS inactive |
| SPI_CS_2M | K3 → 2 m module | Active-low chip select |
| SPI_CS_70CM | K3 → 70 cm module | Active-low chip select |
| SPI_CS_23CM | K3 → 23 cm module | Active-low chip select |

### 9.3 Control Signals over VITA 46

| Signal | Direction | Function |
|--------|-----------|----------|
| PTT_2M | K3 → module | TX enable, 2 m (step 1 in PTT sequence) |
| SW_2M | K3 → module | T/R switch, 2 m (step 2) |
| PA_EN_2M | K3 → module | PA enable, 2 m (step 3, after 1 ms delay) |
| PTT_70CM | K3 → module | TX enable, 70 cm |
| SW_70CM | K3 → module | T/R switch, 70 cm |
| PA_EN_70CM | K3 → module | PA enable, 70 cm |
| PTT_23CM | K3 → module | TX enable, 23 cm |
| SW_23CM | K3 → module | T/R switch, 23 cm |
| PA_EN_23CM | K3 → module | PA enable, 23 cm |
| ATT_LE_2M | K3 → module | Attenuator latch enable, 2 m |
| ATT_LE_70CM | K3 → module | Attenuator latch enable, 70 cm |
| ATT_LE_23CM | K3 → module | Attenuator latch enable, 23 cm |
| IRQ_2M | module → K3 | RFIC event: PLL unlock, AGC, RSSI |
| IRQ_70CM | module → K3 | same |
| IRQ_23CM | module → K3 | same |
| VCTCXO_TUNE_2M | K3 → module | PWM + RC filter → 0–1.8 V analog |
| VCTCXO_TUNE_70CM | K3 → module | same |
| VCTCXO_TUNE_23CM | K3 → module | same |
| TEMP_2M | module → K3 | I²C temperature sensor (per slot, VITA 46 J0 utility plane) |
| TEMP_70CM | module → K3 | same |
| TEMP_23CM | module → K3 | same |

### 9.4 VITA 46 Connector Pin Assignment

The OpenVPX VITA 46 edgecard connector on each module has three physical connectors: **J0** (utility plane, power, slow signals), **J1** (data plane, primary high-speed fabric), and optionally **J2** (secondary fabric or expansion). Pin designations follow the VITA 46.0 standard naming convention: row letters A–Z (component side) and rows a–z (solder side), columns 1 onward.

**J0 — Utility plane, power, and module control signals**

J0 carries power rails, I²C, SPI configuration, GPIO control signals, I2S IQ streams, and GNSS discipline. All signals here are low-frequency or quasi-static.

| J0 Pin | Signal | Direction | Description |
|--------|--------|-----------|-------------|
| A1 | GND | — | Ground |
| A2 | GND | — | Ground |
| A3 | +12V_PA | PWR in | PA supply rail (direct battery bus, decoupled on module) |
| A4 | +12V_PA | PWR in | PA supply rail (second pin for current capacity) |
| A5 | +5V | PWR in | 5 V from VITA 62 PSU |
| A6 | +3V3 | PWR in | 3.3 V from VITA 62 PSU |
| A7 | +1V8 | PWR in | 1.8 V from VITA 62 PSU |
| A8 | GND | — | Ground |
| B1 | SPI_CLK | In | Shared SPI clock from K3 (up to 10 MHz) |
| B2 | SPI_MOSI | In | SPI data from K3 to RFIC |
| B3 | SPI_MISO | Out | SPI data from RFIC to K3 (tri-state when CS inactive) |
| B4 | SPI_CS_N | In | Active-low chip select (unique per module) |
| B5 | ATT_LE | In | Attenuator latch enable (PE4312 parallel mode LE pin) |
| B6 | RFIC_RESET_N | In | Active-low RFIC reset from K3 |
| B7 | RFIC_IRQ_N | Out | Active-low IRQ: PLL unlock, AGC threshold, RSSI update |
| B8 | GND | — | Ground |
| C1 | PTT | In | TX enable from K3 (step 1 in PTT sequence) |
| C2 | TR_SW | In | T/R switch control from K3 (step 2 in PTT sequence) |
| C3 | PA_EN | In | PA enable from K3 (step 3, after 1 ms delay) |
| C4 | ANT_SW | In | Shared/independent antenna mode select (HT13G-M only; NC on HT13G-S module) |
| C5 | MOD_PRESENT | Out | Module presence detect — pulled low on module, open on empty slot |
| C6 | MOD_ID0 | Out | Module type ID bit 0 (resistor-coded: 00=2m, 01=70cm, 10=23cm, 11=spare) |
| C7 | MOD_ID1 | Out | Module type ID bit 1 |
| C8 | GND | — | Ground |
| D1 | I2C_SCL | In | I²C clock — VITA 46 J0 utility plane bus (shared, 100 kHz) |
| D2 | I2C_SDA | Bidir | I²C data — temperature sensor, module ID EEPROM |
| D3 | VCTCXO_TUNE | In | Analog 0–1.8 V GNSS frequency discipline (from K3 PWM + RC filter) |
| D4 | PPS_REF | In | Optional 1PPS reference input for module-local timestamp (not required for basic operation) |
| D5 | I2S_BCLK | In | I2S bit clock from K3 SAI peripheral |
| D6 | I2S_LRCLK | In | I2S left/right clock (500 kHz IQ sample rate word select) |
| D7 | I2S_DOUT | Out | I2S data out from RFIC to K3 (RX IQ: I=Left, Q=Right, 16-bit) |
| D8 | I2S_DIN | In | I2S data in to RFIC from K3 (TX IQ) |
| E1–E8 | GND | — | Ground (via-fence reference, RF zone boundary) |

**Notes on J0:**

- `MOD_PRESENT` allows the K3 to detect which slots are populated at boot. The K3 reads `MOD_ID[1:0]` to identify the band. An empty slot presents high-impedance on all lines.
- `I2C_SDA/SCL` are shared across all module slots on the J0 utility plane bus. Each module has a unique I²C address for its temperature sensor and EEPROM. Temperature sensors use the LM75 / TMP102 family (7-bit address set by address pins on the module).
- `VCTCXO_TUNE` is a per-module signal — each module has its own RC-filtered PWM input from a separate K3 PWM channel, allowing independent VCTCXO discipline per band.
- `I2S_BCLK`, `I2S_LRCLK`, `I2S_DOUT`, `I2S_DIN` are per-module — each module occupies one SAI peripheral on the K3 (SAI1 = 2 m, SAI2 = 70 cm, SAI3 = 23 cm).
- All GPIO signals (PTT, TR_SW, PA_EN, ATT_LE, RFIC_RESET_N) are 1.8 V logic driven by the K3 EC-IO GPIO. The RFIC `VDD_IO` must be configured to 1.8 V on all modules to match. No level translation is required.
- `RFIC_IRQ_N` is an open-drain output from the module; a 10 kΩ pull-up to 1.8 V is on the module PCB.

**J1 — Data plane (reserved for future high-speed expansion)**

J1 is reserved. In the current design, all IQ data is carried over J0 I2S at 500 kHz bandwidth — well within the J0 signal routing capability. J1 is not connected at this time. If a future module variant requires higher IQ bandwidth (e.g. wideband monitoring beyond 500 kHz), J1 provides PCIe Gen 3 × 1 or GbE lanes per the VITA 65 slot profile.

| J1 Pins | Signal | Notes |
|---------|--------|-------|
| All | NC | Not connected in current revision. PCB pads present; VITA 46 connector populated for mechanical retention. |

**Module identity EEPROM**

Each module carries a small I²C EEPROM (24C02 or equivalent, 256 bytes) at a unique address determined by address pins tied to VCC or GND on the module. The EEPROM stores:

| Byte offset | Content |
|-------------|---------|
| 0x00–0x01 | Module type (0x0001 = 2 m, 0x0002 = 70 cm, 0x0003 = 23 cm) |
| 0x02–0x03 | Hardware revision |
| 0x04–0x13 | Serial number (16 ASCII bytes) |
| 0x14–0x17 | Factory calibration: VCTCXO trim offset (int32, ppb) |
| 0x18–0x1B | Factory calibration: PA output power calibration point (uint32, dBm × 100) |
| 0x1C–0xFF | Reserved |

The `ht-module-daemon` reads this EEPROM at startup to identify each installed module, load its calibration constants, and set the correct VCTCXO trim starting point before GNSS discipline takes over.

### 9.5 Antenna connector options — RP-SMA or Type-N

Analog RF leaves the module T/R switch through one front-panel coax jack. The PCB layout supports **RP-SMA** (default) or **Type-N** on the same 50 Ω microstrip land. This choice affects only the faceplate RF port.

#### Default: RP-SMA

```
T/R switch ── BPF ── RP-SMA (front panel) ── coax ── antenna
```

Standard production fitment. Use when the 3U module front panel lacks depth or clearance for a Type-N bulkhead, or when the site plan uses only short RP-SMA patch cables (bench, indoor cabinet).

#### Option: Type-N (N connector) — preferred when it fits

```
T/R switch ── BPF ── Type-N (front panel) ── coax ── antenna
```

| Why Type-N is better (when it fits) | Detail |
|-------------------------------------|--------|
| Mechanical | Threaded mate; tolerates vibration and repeated tightening on a fixed install |
| Weather | Bulkhead jacks suit outdoor enclosures and exposed repeater cabinets |
| Coax compatibility | Natural mate to LMR-400, LMR-600, and other site feedline used on repeaters |
| Loss | Lower contribution from the connector interface at 432 MHz and 1240 MHz than RP-SMA, especially with large cable |
| Site practice | Common on commercial and amateur repeater hardware at UHF and above |

Order **`-N`** per module when the panel cutout and enclosure depth accommodate a Type-N bulkhead and the antenna run justifies it. **23 cm** modules at permanent sites should default to Type-N unless panel constraints forbid it. **2 m** modules may remain RP-SMA on compact builds.

Type-N does **not** replace the VITA 46 edgecard connector.

**Module PCB variants:**

| Variant | Front-panel RF | When to order |
|---------|----------------|---------------|
| `-SMA` (default) | RP-SMA populated | Compact panel, indoor/cabinet, short patches |
| `-N` | Type-N populated | Type-N fits the panel and site coax — preferred for fixed outdoor repeaters |

One connector type per module at assembly. IQ (I2S on J0), SPI, GPIO, EEPROM, and ZeroMQ are unchanged between variants.

**Layout:** Type-N bulkheads need a larger panel opening and slightly more depth than RP-SMA. If the cutout cannot be made without violating the Section 8.3 λ/10 trace-length rule, stay on `-SMA` rather than forcing Type-N.

---

## 10. Software Interface: ZeroMQ IPC

In the repeater context, IQ data flows from each module RFIC through the backplane into the SpacemiT K3, where it is processed by GNU Radio 4.0 or SDRangel. ZeroMQ (ZMQ) is used as the inter-process communication layer between the low-level hardware driver and the signal processing application.

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
| `ipc:///run/ht-module/iq_2m` | PUB | local | Module → consumers | Raw IQ, int16 interleaved, 500 kHz |
| `ipc:///run/ht-module/iq_70cm` | PUB | local | Module → consumers | Raw IQ, int16 interleaved, 500 kHz |
| `ipc:///run/ht-module/iq_23cm` | PUB | local | Module → consumers | Raw IQ, int16 interleaved, 500 kHz |
| `ipc:///run/ht-module/tx_2m` | SUB | local | GNU Radio → module | TX IQ data stream |
| `ipc:///run/ht-module/tx_70cm` | SUB | local | GNU Radio → module | TX IQ data stream |
| `ipc:///run/ht-module/tx_23cm` | SUB | local | GNU Radio → module | TX IQ data stream |
| `ipc:///run/ht-module/ctrl` | REQ/REP | local | Any process → daemon | Per-module: frequency, gain, PTT, squelch, TX timeout, attenuator ([zeromq-messages.md](zeromq-messages.md)) |
| `ipc:///run/ht-module/status` | PUB | local | Daemon → consumers | RSSI, AGC state, PLL lock, temperature, battery |

For remote monitoring or distributed processing, IPC sockets can be exposed as TCP sockets by changing the address to `tcp://0.0.0.0:<port>` — no other code changes required.

### 10.4 Frame Format

Full binary layout, control commands, status JSON, and gr-ident integration:
**[zeromq-messages.md](zeromq-messages.md)**.

IQ frames are published as length-prefixed binary messages:

```
[ 8 bytes: uint64 timestamp (nanoseconds, GNSS-disciplined) ]
[ 4 bytes: uint32 band identifier (0=2m, 1=70cm, 2=23cm) ]
[ 4 bytes: uint32 sample count in this frame ]
[ N×4 bytes: int16 I, int16 Q interleaved, little-endian ]
```

The 64-bit nanosecond timestamp uses the system clock disciplined by chrony + GNSS PPS (see Section 6 of the main system document), providing accurate cross-band timing for any synchronisation analysis.

### 10.5 `ht-module-daemon` Functions

> **Implementation status:** Specified here and in [zeromq-messages.md](zeromq-messages.md). Source code is **not** in the SDR-repeater repository; implement in a separate **Rust** repo per [docs/implementation-language.md](docs/implementation-language.md) and [docs/repo-map.md](docs/repo-map.md).

The `ht-module-daemon` is a single Rust daemon responsible for:

- Initialising all three module RFICs via SPI on startup
- Reading module temperature sensors via I²C (VITA 46 utility plane) and publishing via status socket
- Managing the PTT sequence (hardware-enforced order: RFIC PTT → T/R switch → 1 ms delay → PA enable) in response to `ctrl` socket commands
- Setting attenuator values via SPI in response to `ctrl` socket commands
- Managing VCTCXO frequency discipline: reading GNSS 1PPS interrupt from K3 GPIO, computing correction, updating PWM duty cycle for each module's VCTCXO_TUNE input
- Monitoring RFIC IRQ lines (PLL unlock, AGC threshold events) and publishing alerts via `status` socket
- Routing TX IQ from ZMQ SUB to SAI DMA TX path

This mirrors the `ht13g-spi` CLI and HT Daemon described in the OpenHT-DB software stack, adapted for three independent modules and the absence of display/keypad/audio hardware.

### 10.6 GNU Radio Integration

A GNU Radio OOT (out-of-tree) module `gr-ht13g` provides:

- `ht13g_source` — ZMQ SUB block; receives IQ from `ht-module-daemon`; outputs `complex float` stream
- `ht13g_sink` — ZMQ PUB block; accepts `complex float` TX stream; sends to daemon
- `ht13g_ctrl` — Python block; sends control commands (frequency, PTT, gain) via `ctrl` REQ/REP socket

For cross-band repeat (e.g. receive on 2 m, retransmit on 70 cm), a single GNU Radio flowgraph subscribes to the `iq_2m` ZMQ source, demodulates, re-encodes, and publishes to the `tx_70cm` ZMQ sink. The daemon handles T/R switching for each band independently, with no coordination required between bands in the flowgraph.

---

## 11. MPW Tapeout Strategy

Full dual-band or triple-band integration on a single die would require approximately 4–6 mm² including the sealring — exceeding the 2 mm² community slot in the OpenMPW program. The strategy is therefore to submit and validate each chain independently before integration.

### 11.1 Recommended Submission Sequence

| Phase | Shuttle | Design | Goal |
|-------|---------|--------|------|
| 1 | SG13G2 (next available) | VHF RX chain only — LNA + IQ mixer + ADC stub | Validate noise figure, IIP3, ADC at 144 MHz |
| 2 | SG13G2 (following) | UHF RX chain only — same topology, 432 MHz | Validate UHF chain performance |
| 3 | SG13G2 | 23 cm RX chain — cascode LNA + IQ mixer + ADC, 1240 MHz | Validate L-band NF and phase noise |
| 4 | SG13G2 | VHF TX chain — DAC + IQ modulator + PA driver | Validate IQ balance, harmonic suppression |
| 5 | SG13G2 | UHF TX chain | same at 432 MHz |
| 6 | SG13G2 | HT13G-M full dual-chain integration | First full die; area ~3–4 mm² → commercial MPW run |
| 7 | SG13G2 | HT13G-S full 23 cm integration | Full 23 cm die; area ~1.5–2 mm² → fits community slot |

Phases 1–5 each fit within the 2 mm² community slot and can be submitted to the IHP OpenMPW program at no cost. Phases 6–7 require either a commercial MPW slot or a larger-area community allocation.

### 11.2 Current MPW Schedule (SG13G2)

Based on the published IHP schedule as of May 2026:

- **Next SG13G2 MPW run:** October 4, 2026 (tapeout deadline approximately August 2026)
- **Following run:** November 15, 2026 (SG13CMOS5L — not applicable)
- Turn-around time for SG13G2: approximately 8 months from tapeout to die delivery

A Phase 1 (VHF RX chain) submission targeting the October 2026 run would receive silicon approximately June 2027. All measurement results must be published open-source per the OpenMPW program requirements.

---

## 12. Risk Register

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| HT13G-M VHF PLL phase noise at 144 MHz | Medium | SiGe HBT VCOs at VHF well-characterised; validate VHF chain in Phase 1 MPW before integration |
| DC offset in zero-IF VHF chain | Medium–High | Standard direct-conversion challenge; digital feedback loop in spec; calibrate on startup via `ht-module-daemon` |
| IQ imbalance at 1240 MHz (HT13G-S) | Medium–High | L-band IQ balance harder than VHF/UHF; on-chip IQ calibration registers; measured and corrected at startup |
| IHP MPW 2 mm² area insufficient for full HT13G-M die | High | Planned; individual chain validation in community slots before commercial MPW submission |
| 5 W PA thermal dissipation on module | Medium | 40% efficiency → 7.5 W total at full power; module PCB copper pour to chassis wall; duty-cycle limiting in firmware; module slot pitch provides ventilation |
| PE4312 insertion loss at 1240 MHz | Low | Rated to 4 GHz; at 1.24 GHz insertion loss rises slightly but remains < 2 dB; acceptable for system NF budget |
| VITA 46 I2S signal integrity over backplane | Low | I2S at 16 MHz bit clock is well within VITA 46 bandwidth; series termination 33 Ω |
| ZMQ IPC latency causing TX audio artefacts | Low | ZMQ PUB/SUB is sub-millisecond at localhost; hardware PTT sequencing (1 ms delay) already dominates latency |
| SG13G2Cu BEOL availability for 23 cm VCO inductors | Medium | Standard Al BEOL thick layer may suffice; Cu BEOL option available from IHP at additional cost if Q is insufficient |
| SKY13351 availability (supply chain) | Low | Multiple equivalent SPDT RF switches available (pSemi, MACOM); footprint-compatible alternatives exist |

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

---

