# SDR Multiband Repeater System Design

**Revision:** 1.8  
**Date:** June 2026  
**Architecture:** Open Silicon · Linux · Modular Eurocard  

> **Revision 1.8 changes:** Primary compute platform changed from Milk-V Titan to Milk-V Megrez (ESWIN EIC7700X, 19.95 TOPS NPU); SpacemiT K3 Pico-ITX designated secondary platform; full compute board comparison table added; computational overhead estimate updated for Megrez 4-core SiFive P550 with NPU offload; 5-slot operation confirmed within compute budget.  

---

## Table of Contents

1. [System Overview](#1-system-overview)
   - [Inter-rack and inter-site communication](#inter-rack-and-inter-site-communication)
2. [Radio Modules](#2-radio-modules)
3. [Backplane Architecture](#3-backplane-architecture)
4. [Compute Module](#4-compute-module)
   - [Computational overhead estimate](#computational-overhead-estimate)
5. [Storage](#5-storage)
6. [GNSS Timing and Frequency Reference](#6-gnss-timing-and-frequency-reference)
7. [Software Stack](#7-software-stack)
   - [7.1 Operating system](#71-operating-system)
   - [7.2 GNU Radio 4.0](#72-gnu-radio-40)
   - [7.3 User-friendly frontends](#73-user-friendly-frontends-gnu-radio-based-or-gnu-radio-compatible)
   - [7.4 gr-ident — radio mode identification](#74-gr-ident--radio-mode-identification)
   - [7.5 ZeroMQ IPC](#75-zeromq-ipc)
8. [Authenticated Remote Control](#8-authenticated-remote-control)
9. [Power Architecture](#9-power-architecture)
10. [Optional Solar Power](#10-optional-solar-power)
11. [Commercial and Licensed Private Network Applications](#11-commercial-and-licensed-private-network-applications)
12. [System Integration Summary](#12-system-integration-summary)
13. [ZeroMQ transport security (general reference)](docs/ZMQ_TRANSPORT_SECURITY.md)

**Wire formats:** [docs/zeromq-messages.md](docs/zeromq-messages.md) — canonical ZeroMQ message reference (repeater IQ/control, gr-ident, LinHT).

**RF hardware:** [docs/RF-modules.md](docs/RF-modules.md) — RFIC, module PCB, backplane, daemon integration.


**Note:**
The linHT projects bandwidth target is currently up to 500 kHz IQ, that has a rf spectrum coverage of 0.5 MHz.
It can be found here: 
https://linux-radio.eu/

**Developer documentation:** [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) · [docs/repo-map.md](docs/repo-map.md) · [docs/runtime/](docs/runtime/README.md) (per-repo specs) · [docs/roadmap.md](docs/roadmap.md) · [docs/dev-environment.md](docs/dev-environment.md) · [docs/repeater-logic.md](docs/repeater-logic.md) · [docs/ota-remote-control.md](docs/ota-remote-control.md) · [docs/release-integrity.md](docs/release-integrity.md) · [docs/implementation-language.md](docs/implementation-language.md) · [ADR 001: I2S + ZMQ](docs/adr/001-iq-transport-i2s-zmq.md)

---

## 1. System Overview

### What is a repeater?

A radio repeater receives a signal on one frequency and simultaneously retransmits it on another, typically from an elevated location such as a hilltop or tall building. This extends the usable range of radio communications far beyond what a handheld or mobile radio could achieve on its own — a portable radio may reach a few kilometres directly, but through a well-sited repeater it can cover tens or hundreds of kilometres.

### What is a repeater network?

A repeater network links multiple repeater sites together, so that a transmission into any one site is relayed across all of them simultaneously. This extends coverage across large geographic areas — across a county, a mountain range, or an entire country — while allowing users anywhere on the network to communicate with each other.

### Inter-rack and inter-site communication

Each 3U Eurocard rack unit is a self-contained repeater chassis: RF modules in slots A–E connect to the local compute host only through the **internal DIN 41612 backplane** and **ECP5 PCIe interface card**. That backplane does **not** extend between rack units — it is not a site-to-site link.

**Rack unit to rack unit** communication uses standard **IP networking**:

| Link scope | Transport | Purpose |
|------------|-----------|---------|
| Within one rack unit | DIN 41612 backplane + ECP5 card | I2S IQ, SPI, I²C, GPIO between RF modules and local host |
| Between rack units / sites | **GbE RJ45** (primary) | Inter-site audio linking, ZeroMQ IQ/control over TCP, EchoLink/AllStar/VoIP, simulcast coordination, remote management, NTP |
| Between rack units / sites | **Fiber** (optional) | Long cable runs, tower-to-shack links, or electrically isolated paths where copper is impractical |

The Milk-V Megrez provides **two GbE RJ45 ports**. Typical site wiring:

- **Port 1** — local site LAN (management, SSH, OpenWebRX+, operator access)
- **Port 2** — dedicated inter-site link to another repeater rack, a hub switch, or a WAN router

For fiber, use a **managed switch with SFP/SFP+ uplinks** between buildings or compounds, **fiber media converters** on an existing copper run, or a **PCIe fiber NIC** in the host where direct attachment is preferred. Fiber is optional — most linked repeater networks operate entirely over copper GbE within a few hundred metres, or over GbE to an IP router for wider-area links.

Software transport on the LAN includes:

- **ZeroMQ** `tcp://` bindings for IQ streaming and control between sites (same frame format as local IPC; see [Section 7.5](#75-zeromq-ipc))
- **QRadioLink / EchoLink / AllStar** and similar ROIP stacks for voice linking
- **Authenticated remote control** ([Section 8](#8-authenticated-remote-control)) — signed commands propagate across linked sites on the IP network
- **GNSS time discipline** ([Section 6](#6-gnss-timing-and-frequency-reference)) — common UTC reference at each site independent of network latency; required for simulcast and coordinated transmit scheduling

No proprietary inter-rack bus is defined. Any two rack units that can reach each other on IP — copper GbE or fiber — can participate in the same repeater network.

### Who uses repeaters?

Repeaters are used across a wide range of applications:

- **Amateur radio** — operators use repeater networks for local communication, emergency coordination, and as infrastructure for digital modes and weak-signal work
- **Public safety** — police, fire, and ambulance services depend on repeater networks for reliable coverage across their operational areas
- **Hospitals and healthcare** — on-site and regional repeater systems support staff communications and emergency response coordination
- **Utilities and infrastructure** — electricity networks, water authorities, and other utilities use private repeater networks for operational communications across large and often remote service areas
- **Forestry and hunting** — repeaters provide communication in remote terrain where direct radio contact is impossible; specialised radios used in these environments include a dedicated emergency button that transmits an alert with a GPS position, allowing search and rescue to locate a person in distress
- **County and municipal services** — local government services use repeater infrastructure for coordination across their areas
- **VoIP and telephone integration** — repeaters are commonly linked to Voice over IP systems and telephone networks, allowing radio users to make and receive telephone calls, and enabling remote sites to be connected over the internet; systems such as EchoLink and AllStar are widely used for this purpose

This document describes a modular, Linux-based, software-defined radio (SDR) repeater system capable of simultaneous operation across the 2 metre, 70 cm, and 23 cm amateur radio bands. The system is designed around open standards throughout: open silicon CPU, open backplane standards, and open-source software. It runs from AC mains with seamless battery backup, and optionally from solar power. No generator is used or required.

> **This is a design concept.** The specifications in this document represent a practical starting point, not fixed constraints. The modular architecture is deliberately chosen so that the system can be adapted: additional RF modules beyond the three described here may fit depending on backplane slot count and power budget; mains voltage and power supply selection can be adjusted for local grid standards; battery bank capacity can be scaled from small to very large depending on site autonomy requirements; and RF output power levels can be varied — 5 W is used as a standard throughout this document but the module design can accommodate different power levels. The guiding principle is open standards all the way from DC or AC power input to software: all circuit diagrams, PCB layouts, and enclosure designs are to be produced in **KiCad** and published openly, so that any operator with appropriate soldering equipment, test gear, and RF experience can build, maintain, and service the system without dependency on any vendor or proprietary toolchain.

### Design principles

- All hardware uses open or openly-documented standards (RISC-V ISA, IEC 60297 Eurocard, DIN 41612 / IEC 60603-2)
- All software is free and open source (Linux, GNU Radio ecosystem)
- All schematics, PCB layouts, and enclosure designs produced in KiCad and publicly available
- Pluggable modular architecture — radio modules are field-replaceable
- Single DC bus throughout — no AC/DC inversion on the load side
- Battery backup is zero-switchover (DC UPS topology)
- Power sources: AC mains + optional solar — no generator
- Temperature and battery state monitored in Linux userspace via standard kernel interfaces
- SWR (Standing Wave Ratio) monitored per module and reported via ZeroMQ status messages
- System time disciplined by GNSS (GPS/GLONASS/Galileo/BeiDou) — no internet dependency
- Optional GNSS-disciplined frequency reference for SDR oscillator correction
- IQ data between hardware drivers and signal processing over **ZeroMQ** IPC (see [Section 7.5](#75-zeromq-ipc))

### System architecture

```
Milk-V Megrez (Mini-ITX)
├── ESWIN EIC7700X SoC
│   ├── 4× SiFive P550 CPU cores
│   └── 19.95 TOPS NPU (AI-assisted squelch / interference detection)
├── 32 GB LPDDR5 RAM (soldered)
├── NVMe SSD (M.2 M-Key)
├── PCIe Gen3 ×4 slot
│   └── ECP5-25F PCIe backplane interface card
│       └── DIN 41612 backplane (ribbon cable / header)
│           ├── Slot A — RF module (2 m)
│           ├── Slot B — RF module (70 cm)
│           ├── Slot C — RF module (23 cm)
│           ├── Slot D — spare / expansion
│           └── Slot E — spare / expansion
├── 2× GbE — site LAN + inter-rack / inter-site link (optional fiber via switch or media converter)
├── Wi-Fi 6 / BT — optional wireless management
└── USB — peripheral / debug
```

The **Milk-V Megrez** Mini-ITX host runs Linux and all repeater application software. All backplane signal interfacing (I2S, SPI, I²C, GPIO, PWM) is handled by the **ECP5-25F PCIe interface card** in the Megrez PCIe Gen3 ×4 slot — the Megrez motherboard does not route these signals directly.

---

## 2. Radio Modules

The system supports up to five pluggable radio modules on the backplane. Three bands are defined by default; remaining slots are spare or expansion. Full RFIC, PCB, and backplane detail is in **[docs/RF-modules.md](docs/RF-modules.md)**.

### Module specifications

| Module | Band | Frequency Range | IQ Bandwidth | TX Power | Antenna |
|--------|------|-----------------|--------------|----------|---------|
| 2 metre | VHF | 144–146 MHz | 1 MHz max | 5 W | RP-SMA (front panel) |
| 70 cm | UHF | 432–438 MHz | 1 MHz max | 5 W | RP-SMA (front panel) |
| 23 cm | UHF/SHF | 1240–1258 MHz | 1 MHz max | 5 W | RP-SMA (front panel) |
| Expansion | — | User-defined | — | — | RP-SMA (front panel) |

Sample rates of 25 / 50 / 100 / 200 / 500 kHz / 1 MHz are selectable per module via SPI register. At the maximum 1 MHz IQ bandwidth, the I2S bit clock is 32 MHz (1 MHz × 2 channels × 16 bits).

### Module interface

Each module connects to the backplane via:

- **Backplane connector:** DIN 41612 Type C, 96-pin (Harting or equivalent), 2.54 mm pitch — standard Eurocard backplane interface replacing all former VITA 46 edgecard references
- **IQ data:** **I2S** at up to 32 MHz bit clock (1 MHz IQ bandwidth maximum) over DIN 41612 signal contacts — well within the connector's signal bandwidth capability; see [ADR 001](docs/adr/001-iq-transport-i2s-zmq.md)
- **Configuration:** SPI at 10 MHz, I²C utility bus, GPIO control signals — all carried on standard DIN 41612 signal contacts
- **Power:** +12 V PA rail via dedicated **har-bus 64** high-current power contacts (6–15 A per slot); logic rails (+3.3 V, +5 V, +1.8 V) on standard 2 A signal contacts
- **Temperature monitoring:** I²C on the shared backplane bus (per-slot sensor readable by the chassis manager and Linux `hwmon`)
- **RF antenna port:** RP-SMA on the module front panel for the antenna connection. IQ data is transported digitally over the DIN 41612 backplane; the RP-SMA is the antenna interface only, not a backplane RF path.
- **Userspace IQ:** The **`ht-module-daemon`** (Rust; specified, see [docs/repo-map.md](docs/repo-map.md)) on the Linux host publishes per-band RX IQ and accepts TX IQ over **ZeroMQ** sockets (see [Section 7.5](#75-zeromq-ipc))

The DIN 41612 architecture is sized for the actual signal requirements of this repeater. Module interconnect is carried on DIN 41612 signal and power contacts; the host connects to the backplane only through the **ECP5-25F PCIe interface card** (see [Section 4](#4-compute-module)). High-speed differential fabric or PCIe on the module backplane itself is not used.

> **Note on analog RF through the backplane:** RF is digitised at each module; analog RF exits only through the front-panel RP-SMA (or optional Type-N) connector. At 144–1258 MHz with up to 1 MHz IQ bandwidth, digital I2S transport over DIN 41612 is the preferred and simpler approach.

### Module PCB design standards

Mandatory layout standards apply to all module PCBs. Full detail is in **[docs/RF-modules.md](docs/RF-modules.md)** Sections 8.3 and 8.5; summary:

- **Via fences:** All RF paths and high-speed data lanes (I2S, SPI) are enclosed by continuous via fences for their full routed length; maximum via spacing 2–3 mm; fences stitch L2 and L5 ground planes at regular intervals; double-row via fence at RF zone perimeter
- **Ground planes:** All ground copper pours on all layers are interconnected via a regular thermal/ground via array (5 mm grid minimum) across the full board area; solid fill only in RF and PA zones — no thermal relief spokes
- **Thermal management:** Ground and power copper pours serve dual RF reference and heatspreading roles; thermal path is PA junction → L1 copper → thermal vias → inner planes → PCB edge → card guide → chassis wall; PA area uses minimum 3×3 high-density via array (0.4 mm drill, 1 mm pitch) beneath the package connecting L1 through L3
- **Shield cans:** Press-fit SMD shield cans (Würth or Laird) over the RF zone on all module variants; via fences complement but do not replace physical shielding
- **Impedance:** 50 Ω microstrip on L1 throughout RF zone; all RF routing rules from the RF Module Hardware Design Specification apply

---

## 3. Backplane Architecture

### Standard: 3U Eurocard (IEC 60297)

The backplane uses a **3U Eurocard** modular architecture with **DIN 41612** connectors. Module slots **A–E** accept 100 × 160 mm PCBs per IEC 60297. Chassis and card guides are standard 3U Eurocard rack hardware (Schroff, Elma, Pico, or equivalent) — widely available and significantly cheaper than VPX chassis hardware.

Key characteristics:

- **Form factor:** 3U Eurocard (100 mm × 160 mm module PCB)
- **Module slots:** A–E — five pluggable radio module slots
- **Signal connector:** DIN 41612 Type C, 96-pin (Harting or equivalent), 2.54 mm pitch, 2 A per signal contact, gold over nickel mating surface
- **Power connector:** Harting har-bus 64 hybrid power contacts, 5.08 mm pitch, 6–15 A per contact for the +12 V PA rail; logic rails (+3.3 V, +5 V, +1.8 V) carried on standard signal contacts
- **Interconnect:** I2S (up to 32 MHz bit clock), SPI (10 MHz), I²C utility bus, GPIO — all on DIN 41612 signal contacts, driven by the ECP5 interface card; **internal to one rack unit only** (see [Inter-rack and inter-site communication](#inter-rack-and-inter-site-communication))
- **Power distribution:** External PSU (Mean Well DRC series or equivalent) feeds a 24 V DC bus; backplane distributes +12 V PA (har-bus), +5 V, +3.3 V, and +1.8 V per slot
- **KiCad:** Standard library includes DIN 41612 footprints; no custom connector footprint required for the backplane interface

### Backplane signal summary

**Serial buses (shared across all modules):**

- **SPI** — CLK, MOSI, MISO, plus individual CS lines per module (RFIC and SWR ADC)
- **I²C** — SCL, SDA (shared utility bus — temperature sensors, EEPROMs, ADS1015 ADC variant)

**Per-module I2S (one set per slot):**

- BCLK, LRCLK, DOUT, DIN — four lines per module, 20 lines total across five slots

**Per-module GPIO (one set per slot):**

- PTT, TR_SW, PA_EN, ATT_LE, RFIC_RESET_N — control outputs from ECP5 interface card
- RFIC_IRQ_N, MOD_PRESENT, MOD_ID0, MOD_ID1 — status inputs to ECP5 interface card
- VCTCXO_TUNE — analog 0–1.8 V per module
- PPS_REF — optional 1PPS reference
- ANT_SW — HT13G-M modules only

**Power rails:**

- +12 V PA (high current, 6 A per slot)
- +5 V, +3.3 V, +1.8 V
- GND (multiple pins)

Rough total: approximately 75–85 lines across five populated slots, comfortably within the 96-pin DIN 41612 Type C budget with pins to spare for ground and future expansion.

### Recommended chassis

Standard 3U Eurocard subracks from **Schroff**, **Elma**, **Pico**, or equivalent vendors, with card guides and a custom or off-the-shelf DIN 41612 backplane. These are widely stocked by industrial distributors at substantially lower cost than OpenVPX/VPX enclosures.

### Backplane interconnect summary

| Signal class | Transport | Detail |
|--------------|-----------|--------|
| IQ data | I2S over DIN 41612 | Up to 32 MHz bit clock (1 MHz IQ × 2 channels × 16 bits) |
| Configuration | SPI @ 10 MHz | Shared bus, per-module chip select |
| Management | I²C @ 100 kHz | Temperature sensor, EEPROM, optional SWR ADC |
| Control | GPIO | PTT, T/R switch, PA enable, attenuator |
| Power (PA) | har-bus 64 contacts | +12 V, 6–15 A per slot |
| Power (logic) | DIN 41612 signal contacts | +3.3 V, +5 V, +1.8 V at 2 A per contact |

### Open hardware and connector sourcing

- DIN 41612 connectors conform to **IEC 60603-2** — a mature, widely sourced open standard with no licensing encumbrances
- **KiCad** standard libraries include DIN 41612 footprints; no proprietary or custom footprints are required for the backplane interface
- Compatible parts are available from Harting, TE Connectivity, Molex, Amphenol, and many other manufacturers — no single-source dependency

### Backplane standards reference

| Standard | Role |
|----------|------|
| IEC 60297 | 3U Eurocard mechanical dimensions and rack practice |
| DIN 41612 / IEC 60603-2 | 96-pin Type C backplane signal connector |
| DIN 41612 har-bus 64 | Hybrid high-current power contacts (+12 V PA rail) |

---

## 4. Compute Module

### Host board: Milk-V Megrez (Mini-ITX)

The main compute platform is the **Milk-V Megrez** Mini-ITX motherboard (170 × 170 mm), based on the **ESWIN EIC7700X** SoC. The Megrez provides PCIe, NVMe, dual GbE, Wi-Fi, and a 19.95 TOPS on-chip NPU suitable for AI-assisted squelch and signal classification at the repeater site without cloud dependency. Like other Mini-ITX RISC-V boards in this class, it does **not** expose I2S/SAI peripherals on standard external headers. All module backplane signalling is handled by the ECP5 PCIe interface card described below.

#### Processor and board specifications

| Parameter | Value |
|-----------|-------|
| SoC | ESWIN EIC7700X |
| CPU | 4× SiFive P550 cores, up to 1.8 GHz, RV64GCH, 13-stage out-of-order triple-issue pipeline |
| AI / NPU | 19.95 TOPS INT8 — on-chip neural processing unit; available for AI-assisted squelch, interference detection, and signal classification directly on the repeater without cloud dependency |
| GPU | Imagination AXM-8-256; OpenGL ES 3.2, OpenCL 1.2/2.1, Vulkan 1.2 |
| RAM | 16 GB or 32 GB LPDDR5-6400 — soldered, not user-upgradeable; **32 GB variant specified for production builds** |
| Storage | M.2 M-Key NVMe (PCIe 2.0 ×2); eMMC connector; microSD slot |
| PCIe | 1× PCIe Gen3 ×4 slot (tested with AMD Radeon RX 7900 XTX; adequate for ECP5-25F backplane interface card) |
| Networking | 2× GbE RJ45; onboard Wi-Fi and Bluetooth |
| USB | Multiple USB 3.0 and USB 2.0 ports |
| Power | ATX 24-pin or DC 12 V input |
| Form factor | Mini-ITX, 170 × 170 mm |
| OS | Ubuntu 24.04 LTS, Fedora, Debian; mainline Linux support in progress |
| Price | $199 (16 GB) / $269 (32 GB) |

The EIC7700X, like the UR-DP1000 on the Milk-V Titan, does not expose I2S/SAI on accessible headers. **All backplane signal interfacing remains via the ECP5-25F PCIe interface card.** The PCIe Gen3 ×4 slot provides far more bandwidth than the ECP5 IQ data rate requires — the interface is not a bottleneck.

### ECP5-25F PCIe backplane interface card

A custom PCIe card plugs into the Megrez PCIe Gen3 ×4 slot and provides all backplane signal interfacing between the Linux host and the DIN 41612 module backplane.

| Parameter | Value |
|-----------|-------|
| FPGA | Lattice ECP5-25F (~$15–25 in singles); open source toolchain — Yosys, nextpnr, Project Trellis |
| Host interface (primary) | PCIe Gen1 ×1 hard IP in ECP5 — plugs into Megrez PCIe Gen3 ×4 slot; ×1 card is electrically compatible |
| Host interface (fallback/debug) | USB 2.0 high-speed via LUNA gateware framework and external USB3343 PHY (~$2); connects to Megrez USB port; fully open source stack |
| Backplane connector | Ribbon cable or direct header to DIN 41612 backplane |
| Power | From PCIe slot (3.3 V and 12 V available on PCIe connector) |
| Gateware license | Apache 2.0 / open hardware, consistent with project licensing |
| Toolchain | Fully open source — no proprietary tools required |

**Backplane signals handled by ECP5 fabric:**

- **I2S × 5** (one per module slot) — BCLK, LRCLK, DOUT, DIN per slot
- **SPI** — CLK, MOSI, MISO, CS lines per module (RFIC and SWR ADC)
- **I²C** — SCL, SDA utility bus
- **GPIO** — PTT, TR_SW, PA_EN, ATT_LE, RFIC_RESET_N, IRQ, MOD_PRESENT, MOD_ID per slot
- **PWM** — VCTCXO_TUNE analog output (PWM + RC filter on module PCB) per slot

The ECP5-25F is chosen for cost, open toolchain, proven PCIe hard IP, and widespread use in open SDR and open hardware projects. PCIe Gen1 ×1 provides ~250 MB/s — five modules at 1 MHz IQ, 16-bit stereo is less than 2.5 MB/s total, so the interface is massively over-provisioned relative to actual data rate, which is intentional for low-risk implementation.

The Linux driver stack reads IQ samples from the ECP5 card over PCIe (or USB in debug mode) and feeds **`ht-module-daemon`**, which publishes ZeroMQ IQ streams to GNU Radio and other consumers (see [Section 7.5](#75-zeromq-ipc)).

### Computational overhead estimate

The following estimates cover **5-slot operation** with frame signing and optional encryption on the Milk-V Megrez (ESWIN EIC7700X, 4× SiFive P550 @ 1.8 GHz, 19.95 TOPS NPU).

#### IQ data throughput

- Per slot at 1 MHz IQ bandwidth: **32 Mbps** (1 MHz × 2 channels × 16 bits)
- 5 slots aggregate: **160 Mbps = 20 MB/s** total IQ throughput into the host via ECP5 PCIe interface card

#### GNU Radio / signal processing (CPU cores)

- Cross-band repeat path per slot (demodulate + re-encode): approximately **50–100 MFLOPS** on a modern RISC-V core
- 5 simultaneous slots: **~250–500 MFLOPS** total
- SiFive P550 at 1.8 GHz, triple-issue out-of-order: approximately **3–5 GFLOPS** sustained on general DSP workloads
- 4 cores total available: **~12–20 GFLOPS** aggregate capacity
- **Estimated CPU load for IQ processing:** well under 2 cores for all 5 slots

#### NPU — AI-assisted processing

- The EIC7700X **19.95 TOPS NPU** is available for signal classification, interference detection, and AI-assisted squelch entirely independently of the CPU cores
- NPU load for 5-slot monitoring at 1 MHz IQ bandwidth: **low** — the NPU is designed for INT8 neural network inference; signal classification models for amateur radio are small (well under 1M parameters) and run at a fraction of NPU capacity
- NPU and CPU operate concurrently — AI inference does not compete with GNU Radio processing for CPU resources
- **Estimated NPU utilisation** for signal classification across 5 slots: **less than 10% of 19.95 TOPS**

#### ZeroMQ IPC

- Sub-millisecond latency at localhost; negligible CPU at 20 MB/s aggregate
- **Estimated CPU load:** less than 0.5 core

#### Frame signing (Ed25519, mandatory)

- Ed25519 on RV64GCH RISC-V software (OpenSSL 3.x): **~50,000–100,000 signatures/second** per core
- At typical ZMQ frame rates (one frame per 10 ms per slot at 1 MHz IQ), signing cost is microseconds per frame
- **Estimated CPU load:** less than 0.1 core across all 5 slots

#### Optional encryption (AES-256-GCM)

- EIC7700X implements the RISC-V **Zkn** scalar cryptography extension (part of RVA22 / RV64GCH); OpenSSL on Linux uses Zkn instructions automatically for AES and SHA acceleration
- Software AES-256-GCM throughput on RV64GCH with Zkn: approximately **400–600 MB/s** per core
- 5 slots at 20 MB/s total IQ: well under 5% of one core for encryption
- **Estimated CPU load:** less than 0.5 core

#### Aggregate estimate — 5 slots, signing enabled, encryption enabled, AI classification enabled

| Task | Estimated load |
|------|----------------|
| IQ processing — GNU Radio, 5 slots | ~1–2 CPU cores |
| ZeroMQ IPC | < 0.5 CPU core |
| Ed25519 frame signing | < 0.1 CPU core |
| AES-256-GCM encryption (optional) | < 0.5 CPU core |
| ht-module-daemon, SWR monitoring, housekeeping | < 0.5 CPU core |
| AI signal classification / squelch (5 slots) | < 10% of 19.95 TOPS NPU |
| **Total CPU** | **~2–3 cores of 4** |
| **Total NPU** | **< 10% of 19.95 TOPS** |

The SiFive P550's 4 cores leave approximately **1–2 cores free** at full 5-slot operation with all security features and AI classification enabled. This headroom accommodates logging, remote SSH access, web management, and modest additional processing. Builds requiring more CPU headroom should consider the **K3 Pico-ITX** (8 cores, 60 TOPS) or **DC-ROMA** (8 cores, 50 TOPS) as compute platforms.

> **Note on Megrez RAM:** The **32 GB LPDDR5** variant is strongly recommended for production builds. At 5-slot operation with GNU Radio flowgraphs, ZMQ ring buffers, AI model loading, and OS overhead, 16 GB is workable but leaves little margin for logging or future expansion. 32 GB is comfortable.

### Compute board comparison

The following boards were seriously evaluated for the repeater host role:

| Board | SoC | CPU | AI / NPU | PCIe slot | RAM | Price | Form factor | Status |
|-------|-----|-----|----------|-----------|-----|-------|-------------|--------|
| Milk-V Megrez | ESWIN EIC7700X | 4× SiFive P550 @ 1.8 GHz | 19.95 TOPS | Gen3 ×4 | 16–32 GB LPDDR5 soldered | $199–$269 | Mini-ITX | **Primary — selected** |
| SpacemiT K3 Pico-ITX | SpacemiT K3 | 8× X100 @ 2.4 GHz | 60 TOPS | Gen3 ×4 (M.2) | Up to 32 GB LPDDR5 | $299–$399 | Pico-ITX Plus | Secondary — preferred if I2S access confirmed |
| Milk-V Titan | UltraRISC UR-DP1000 | 8× UR-CP100 @ 2.0 GHz | None | Gen4 ×16 | Up to 64 GB DDR4 ECC DIMM | $329 | Mini-ITX | Alternative — highest CPU performance; no NPU |
| DeepComputing DC-ROMA | ESWIN EIC7702X | 8× SiFive P550 @ 2.0 GHz | 50 TOPS | Framework mainboard | 32–64 GB LPDDR5 | $349 | Framework / Cooler Master | Noted — strongest NPU; non-standard chassis |

**Notes:**

- The **K3 Pico-ITX** remains the preferred secondary platform due to its 60 TOPS NPU and native I2S/SAI peripherals which could eliminate the need for the ECP5 PCIe interface card entirely. It is listed as secondary rather than primary because the SAI pin accessibility on the Pico-ITX board has not yet been confirmed from publicly available hardware documentation as of June 2026. If SpacemiT or Sipeed publish a full pinout confirming SAI is accessible on the RTI FPC connector, the K3 Pico-ITX should be re-evaluated as primary.
- The **Milk-V Titan** is retained as an alternative for builds prioritising raw CPU performance, ECC memory, and PCIe Gen4 bandwidth over NPU capability. It has no AI cores and is not recommended for builds where on-device signal classification is desired.
- The **DC-ROMA** is noted for completeness. Its Framework laptop chassis form factor is incompatible with a rack-mounted repeater enclosure without significant mechanical adaptation.
- All K3 Pico-ITX board variants (SpacemiT/Sipeed K3 Pico-ITX, Milk-V Jupiter 2, Banana Pi BPI-SM10) share the same SoC and are software-compatible with each other.

---

## 5. Storage

### Configuration: NVMe SSD on onboard M.2

The Megrez provides an **M.2 M-Key NVMe** slot (PCIe 2.0 ×2), plus eMMC and microSD connectors. A 240 GB or larger NVMe SSD is the primary system drive. Specify the **32 GB RAM** Megrez variant for production builds (see [Section 4](#4-compute-module)).

For sites requiring drive redundancy, options include:

- Scheduled backup to a USB-attached SSD or network storage
- microSD or eMMC as a secondary boot/recovery medium

Sustained NVMe throughput on PCIe 2.0 ×2 far exceeds any GNU Radio or repeater workload.

#### Optional RAID setup (two-drive configuration)

If a second NVMe drive is added (for example via USB enclosure or future PCIe storage adapter), Linux software RAID 1 remains supported:

```bash
mdadm --create /dev/md0 --level=1 --raid-devices=2 /dev/nvme0n1 /dev/nvme1n1
```

The kernel `mdadm` RAID 1 array appears as `/dev/md0` and is treated as a single block device. Status is readable via:

```bash
cat /proc/mdstat
mdadm --detail /dev/md0
```

Systemd monitors the array and alerts on drive failure.

---

## 6. GNSS Timing and Frequency Reference

A multi-constellation GNSS receiver serves two distinct roles in this system:

1. **System time discipline** — provides accurate UTC time at the repeater site without any internet connectivity, making the system fully self-contained for timekeeping
2. **Optional SDR frequency reference** — the GNSS 1PPS signal and/or 10 MHz output can discipline the SDR module local oscillators, correcting crystal frequency errors for accurate on-frequency operation

### 6.1 Why GNSS matters for a remote repeater

Remote repeater sites frequently have no reliable internet connection. NTP requires network access; GNSS does not. The system becomes a Stratum 1 time source using satellite signals directly, which is also important for time-stamped logging, digital mode operation (FT8 requires time accuracy to within 1 second), and any future network time serving to linked nodes.

The four supported constellations — GPS (USA), GLONASS (Russia), Galileo (Europe), BeiDou (China) — provide redundancy. At any location in the world, multiple constellations are simultaneously visible, so the receiver maintains lock even if one system has degraded availability.

### 6.2 Recommended GNSS receiver: two-tier selection

#### Tier 1 — Standard timing: u-blox NEO-M9N

The **u-blox NEO-M9N** is a 92-channel GNSS receiver supporting concurrent reception of GPS, GLONASS, Galileo, and BeiDou. It connects via USB, UART, I²C, or SPI, outputs standard NMEA sentences and u-blox UBX binary protocol, and provides a 1PPS (pulse-per-second) output pin.

| Parameter | Value |
|-----------|-------|
| Constellations | GPS, GLONASS, Galileo, BeiDou (concurrent) |
| Channels | 92 |
| Position accuracy | ~1.5 m CEP |
| Timing accuracy (1PPS) | ~30 ns RMS (surveyed/stationary mode) |
| Interfaces | USB, UART, I²C (address 0x42), SPI |
| PPS output | Yes — GPIO pin, configurable pulse width |
| Cold start TTFF | ~24 s |
| Hot start TTFF | ~2 s (battery-backed RTC) |
| Power | ~25 mA @ 3.3 V |
| Form factor | 12.2 × 16.0 mm module; breakout boards available (SparkFun, others) |

This is the practical choice for most deployments. It gives millisecond-class system time and tens-of-nanoseconds 1PPS accuracy in stationary mode — more than sufficient for NTP Stratum 1 service, FT8, APRS, and repeater logging.

#### Tier 2 — High-precision timing: u-blox ZED-F9T

The **u-blox ZED-F9T** is a multi-band (L1/L2/E5b) dedicated timing receiver supporting all four constellations. It is specifically designed for nanosecond-level time transfer and frequency discipline applications.

| Parameter | Value |
|-----------|-------|
| Constellations | GPS, GLONASS, Galileo, BeiDou (concurrent, multi-band) |
| Timing accuracy (1PPS) | 5 ns RMS (stationary, surveyed) |
| Interfaces | USB-C, UART, I²C, SPI |
| PPS outputs | 2 × dedicated SMA timing outputs |
| Multi-band | L1 + L2 + E5b — better ionospheric correction |
| Form factor | SparkFun ZED-F9T breakout with USB-C and dual SMA connectors |

The ZED-F9T is the right choice if SDR module oscillator discipline is a primary goal, or if the system will serve as a precision time reference for a network of nodes. Its 5 ns 1PPS accuracy is overkill for NTP but ideal for GNSS-disciplined oscillator (GPSDO) applications.

### 6.3 Antenna

Both receivers require an active GNSS antenna with a clear view of the sky. For a fixed repeater site, a roof- or mast-mounted **L1/L2 multi-band active patch antenna** with an SMA or TNC connector and LNA is appropriate. Cable runs up to ~10 m with RG-58 or LMR-195 are typical; longer runs require LMR-400 or an inline amplifier.

For the ZED-F9T with multi-band reception, a dual-band (L1 + L2) active antenna is required (e.g. u-blox ANN-MB series or equivalent).

### 6.4 Linux integration: gpsd + chrony

The standard Linux GNSS timekeeping stack is `gpsd` + `chrony`. This is well-established, mainline, and works with all u-blox receivers out of the box.

#### Software stack

```
GNSS receiver (USB or UART)
        │
        ▼
   gpsd daemon
   (parses NMEA/UBX, extracts time, exposes via shared memory)
        │
        ├──► /dev/pps0  (kernel PPS device from 1PPS GPIO)
        │
        ▼
   chrony
   (combines NMEA time from SHM + precise PPS edge)
        │
        ▼
   Linux system clock  (disciplined to GNSS UTC)
        │
        ▼
   NTP server (optional — serves time to local network)
```

#### chrony configuration for GNSS + PPS

```
# /etc/chrony/chrony.conf

# GPS NMEA via gpsd shared memory (coarse time — millisecond class)
refclock SHM 0 refid GPS offset 0.0 delay 0.2

# PPS pulse from GNSS receiver GPIO via kernel pps device (precise edge)
refclock PPS /dev/pps0 lock GPS refid PPS offset 0.0

# Allow local network to query this as NTP server
allow 192.168.0.0/16

# Step the clock if offset > 1 s on first three updates, then slew only
makestep 1 3
```

With a good antenna and stationary mode enabled on the receiver, chrony achieves PPS jitter below 400 ns and frequency stability below 200 ppb — qualifying the system as a Stratum 1 NTP server for the local network or linked repeater nodes.

#### gpsd setup

```bash
# Install
apt install gpsd gpsd-clients chrony

# Configure /etc/default/gpsd
DEVICES="/dev/ttyACM0"       # USB CDC ACM for u-blox USB
GPSD_OPTIONS="-n"            # No-wait — start without client
START_DAEMON="true"

# Enable PPS discipline (1PPS wired to GPIO — ECP5 card or USB GPIO adapter)
# Platform-specific device tree or pps-gpio overlay as required
```

#### Verifying GNSS lock and time quality

```bash
cgps              # Live satellite view and position
chronyc sources   # Show time sources and offsets
chronyc tracking  # System clock status vs reference
```

### 6.5 Optional: SDR frequency discipline

At VHF/UHF frequencies, the crystal oscillators in SDR modules introduce frequency errors. A typical TCXO has ±1–2 ppm error, translating to ±144 Hz at 144 MHz and ±432 Hz at 432 MHz — noticeable on narrow digital modes and problematic for precise frequency coordination between linked repeater sites.

Two approaches are available for GNSS-based frequency correction:

#### Approach A — Software correction via measured offset (recommended)

GNU Radio and SDRangel both support runtime frequency correction via a PPM offset parameter. The procedure is:

1. Receive a known-frequency reference signal (e.g. a beacon, WSPR transmission, or the GNSS receiver's own 1 Hz signal)
2. Measure the observed frequency error in GNU Radio's spectrum
3. Enter the PPM correction value into the SDR source block or SDRangel's device settings
4. The software applies the correction digitally at all times

This requires no hardware modification and is fully adequate for amateur radio repeater use.

#### Approach B — Hardware 10 MHz reference injection (advanced)

Some SDR modules (LimeSDR, USRP, PlutoSDR with modification) accept an external 10 MHz reference clock input. The GNSS receiver's 10 MHz output (where available, e.g. ZED-F9T with GPSDO option, or a standalone GPSDO unit) locks the SDR's internal PLL directly, providing true hardware frequency discipline at the parts-per-billion level.

This approach requires:

- A GNSS receiver or GPSDO with a stable 10 MHz CMOS/sinewave output
- SDR module hardware that accepts an external 10 MHz reference
- A short coaxial connection between the reference output and the SDR reference input

For most repeater deployments, Approach A (software PPM correction) is sufficient and simpler. Approach B is worth implementing if the system will be used for weak-signal work, EME, or precise frequency standard duties.

### 6.6 GNSS receiver comparison summary

| | NEO-M9N | ZED-F9T |
|--|---------|---------|
| Constellations | GPS, GLONASS, Galileo, BeiDou | GPS, GLONASS, Galileo, BeiDou |
| Bands | L1 only | L1 + L2 + E5b |
| 1PPS accuracy | ~30 ns RMS | ~5 ns RMS |
| Interfaces | USB, UART, I²C, SPI | USB-C, UART, I²C, SPI |
| PPS outputs | 1 × GPIO | 2 × SMA |
| Linux support | gpsd (plug-and-play) | gpsd (plug-and-play) |
| Use case | NTP Stratum 1, time sync, software PPM | Precision timing, hardware GPSDO |
| Approx. cost (breakout) | ~$25–$50 | ~$150–$200 |

**Recommendation:** Start with the NEO-M9N for the vast majority of repeater deployments. Upgrade to ZED-F9T only if hardware frequency discipline or sub-10 ns timing is required.

---

## 7. Software Stack

### 7.1 Operating system

**Ubuntu 24.04 LTS**, **Debian**, or **Fedora** on the Milk-V Megrez (ESWIN EIC7700X, RV64GCH). Mainline Linux support for the EIC7700X is in progress; vendor or distribution images are used until then. Dual **GbE** ports and onboard **Wi-Fi 6 / Bluetooth** support site networking and optional wireless management.

### 7.2 GNU Radio 4.0

GNU Radio 4.0 reached Release Candidate 1 in March 2026. The core architecture is stable, the execution model is well-defined, and the API is no longer expected to undergo major breaking changes. It is the signal processing foundation of the repeater — handling IQ data ingestion from modules, filtering, demodulation, repeater logic (CTCSS/DCS detection, squelch, crossband linking), and re-modulation.

**VOLK 3.3.0** (February 2026) added RISC-V vector optimisations. Where the host CPU supports RVV, VOLK uses SIMD-accelerated kernels — filters, FFTs, correlators — without manual tuning.

GNU Radio is the most powerful and flexible option but has a steep learning curve due to its flowgraph / block-programming paradigm. For operators who prefer a more direct interface, the following GNU Radio-based frontends are available.

When the repeater should identify the incoming modulation type and route IQ data to the correct demodulator automatically (rather than relying on manual mode selection or statistical classification), the flowgraph can implement the **[gr-ident](https://github.com/Supermagnum/gr-ident)** preamble specification — see [Section 7.4](#74-gr-ident--radio-mode-identification).

IQ streams enter and leave the flowgraph over **[ZeroMQ](https://zeromq.org/)** PUB/SUB sockets provided by `ht-module-daemon` and the `gr-ht13g` blocks — see [Section 7.5](#75-zeromq-ipc).

---

### 7.3 User-friendly frontends (GNU Radio-based or GNU Radio-compatible)

These applications sit on top of GNU Radio or share its ecosystem, offering conventional point-and-click interfaces instead of flowgraph programming.

#### GQRX

GQRX is a software-defined radio receiver built on top of GNU Radio and the Qt graphical toolkit. It provides a simple, familiar receiver interface — waterfall display, tuning dial, demodulator selector, audio output, bookmark manager, and TCP remote control. It is the most widely used GNU Radio-based frontend on Linux, reliable and lightweight. It does not support transmit.

- **Best for:** Monitoring, receive-only operations, scripting via its TCP control interface
- **Limitations:** No digital voice decoding built in; no transmit; limited plugin ecosystem

#### SDRangel (upstream fork base)

**Upstream for application forks:** [f4exb/sdrangel](https://github.com/f4exb/sdrangel) on GitHub. Among the maintained Linux SDR frontends compared here, it is the preferred base because it supports real **TX and RX** (including concurrent RX and TX on separate devices), ships a large built-in digital-mode suite, and is actively maintained (GPL-3.0).

SDRangel is a Qt5/OpenGL SDR frontend. It includes decoders and channel plugins for DMR, D-Star, NXDN, YSF, FT8, APRS, AIS, ADS-B, M17 (`modemm17`), and others. For a headless repeater site, the **server** build (`sdrsrv` / `appsrv`) plus the REST API (and optional [SDRangelcli](https://github.com/f4exb/sdrangelcli) web UI) fits better than the desktop GUI alone. Custom work for this project is expected as **device/sample-source plugins** (for example IQ from [ZeroMQ](#75-zeromq-ipc) via `ht-module-daemon`) and repeater-oriented channel presets, not a greenfield TX/RX application.

- **Best for:** Repeater TX/RX, digital voice, multi-mode monitoring, headless remote control
- **Limitations:** Steep learning curve; resource-intensive on lower-end hardware; no native ZMQ IQ path until a plugin or bridge is added
- **RISC-V status:** Confirmed running on Banana Pi BPI-F3 (SpacemiT K1, RISC-V)

#### QRadioLink and gr-qradiolink

QRadioLink is a multimode SDR transceiver application built directly on top of GNU Radio, specifically designed for Linux and repeater/VOIP bridging use cases. It supports radio-over-IP (ROIP) bridging using Internet protocols, making it useful for linking the repeater to EchoLink, AllStar, or similar networks. It supports analog and digital modes and uses a Qt5 UI.

**[gr-qradiolink](https://github.com/Supermagnum/gr-qradiolink)** is a companion GNU Radio out-of-tree (OOT) module that extracts the QRadioLink signal processing blocks into reusable GNU Radio components, making the full QRadioLink modulation and digital voice suite available in any GNU Radio flowgraph — including this repeater system — independently of the QRadioLink application itself.

The module provides a comprehensive set of validated blocks covering:

**Modulation/demodulation:** 2FSK, 4FSK, 8FSK, CPM-4FSK, GMSK, BPSK, QPSK, SOQPSK, AM, SSB (USB/LSB), NBFM, WBFM — all validated against the upstream QRadioLink source.

**Digital voice:** FreeDV, M17, DMR (Tier I/II/III), dPMR (ETSI TS 102 658, 6.25 kHz), NXDN (NXDN48 and NXDN96), and MMDVM-compatible protocols including POCSAG, D-STAR, YSF, and P25 Phase 1 C4FM.

**FEC:** Soft-decision LDPC encoder/decoder with configurable code rates (1/2, 2/3, 3/4) and block lengths (576, 1152, 2304 bits); HF burst interleaver.

The module has been fuzz-tested with over 104 million executions across all blocks with zero crashes or memory leaks. All C++ unit tests pass (100%), and 41 MMDVM protocol tests pass (100%).

For this repeater system, `gr-qradiolink` provides the signal processing blocks for any mode not covered by SDRangel's built-in plugins, and is the natural choice when building GNU Radio 4.0 flowgraphs that need DMR, dPMR, NXDN, P25, or multimode digital voice operation.

- **Best for:** Repeater linking, radio-over-IP, multimode digital voice flowgraphs, spread-spectrum operation
- **Limitations:** Smaller community than GQRX or SDRangel; QRadioLink application UI less polished than SDRangel

#### SDR++ (SDRPlusPlus)

SDR++ is a modern, cross-platform, C++-based SDR receiver with a clean interface, low CPU overhead, and a plugin architecture. It is not built on GNU Radio internally but integrates with the same SoapySDR hardware abstraction layer and is part of the same ecosystem. It is widely regarded as the best general-purpose daily-driver SDR application for Linux in 2026.

- **Best for:** Spectrum monitoring, general receive, remote/network streaming
- **Limitations:** Receive only; no transmit capability

#### OpenWebRX+

OpenWebRX+ is a multi-user SDR receiver with a browser-based interface. Once running on the repeater system, any device on the local network (or the internet) can connect via a web browser to monitor the spectrum and listen to received audio — with no software installation required on the client. It includes built-in decoders for FT8, APRS, ADS-B, and other digital modes.

- **Best for:** Remote monitoring and management of the repeater site over the network
- **Limitations:** Receive only; primarily a monitoring and remote-access tool

#### Software comparison summary

| Application | TX | RX | GNU Radio | Digital modes | Remote access | Linux |
|-------------|----|----|-----------|--------------|---------------|-------|
| GNU Radio 4.0 (GRC) | ✓ | ✓ | Native | Via blocks | Via blocks | ✓ |
| GQRX | ✗ | ✓ | Built on GR | Limited | TCP server | ✓ |
| SDRangel | ✓ | ✓ | Compatible | Extensive built-in | REST API | ✓ |
| QRadioLink + gr-qradiolink | ✓ | ✓ | Built on GR / OOT blocks | Extensive (DMR, dPMR, NXDN, P25, M17, DSSS, GDSS) | ROIP/EchoLink | ✓ |
| SDR++ | ✗ | ✓ | SoapySDR | Via plugins | Network source | ✓ |
| OpenWebRX+ | ✗ | ✓ | Compatible | FT8, APRS, ADS-B | Browser-based | ✓ |

**Recommended combination for a repeater:** Fork and extend [f4exb/sdrangel](https://github.com/f4exb/sdrangel) for TX/RX and digital modes; use GNU Radio 4.0 + [gr-ident](#74-gr-ident--radio-mode-identification) + [gr-linux-crypto](#8-authenticated-remote-control) for flowgraph-centric logic and authenticated control; use **[gr-qradiolink](https://github.com/Supermagnum/gr-qradiolink)** for DMR, dPMR, NXDN, P25, and M17 GNU Radio blocks; run OpenWebRX+ in parallel for browser-based spectrum monitoring. Use QRadioLink application only if ROIP/EchoLink-style linking is required alongside SDRangel.

---

### 7.4 gr-ident — radio mode identification

**[gr-ident](https://github.com/Supermagnum/gr-ident)** specifies a lightweight radio mode identification preamble for GNU Radio systems. When the repeater is configured to use it, the receiver can identify the incoming modulation type (analog or digital, and the specific mode such as narrowband FM versus C4FM) before committing to a demodulator, and automatically switch to the appropriate processing path.

The preamble is a Golay(24,12)-protected field transmitted at the start of each frame. The receiver reads the analog/digital flag and mode ID, routes the signal to the correct demodulator bank, and does not pass unrecognised or mismatched traffic to the audio output. For example, a receiver set for analog FM does not present digital C4FM as noise on the speaker.

The same identification approach applies to **Linht**, an open-source-hardware, Linux-based SDR handheld transceiver: If it also has gr-ident it can discriminate between modes on receive so the operator is not forced to listen to digital C4FM while the radio is configured for analog FM. Conventional analog-only transceivers do not offer this capability.

gr-ident is designed to work alongside **[gr-linux-crypto](https://github.com/Supermagnum/gr-linux-crypto)** (see [Section 8](#8-authenticated-remote-control)). The preamble includes an encrypted/open flag so a Linht or repeater implementation can identify the mode before attempting decryption, and can refuse to demodulate encrypted payloads for which no key is available.

---

### 7.5 ZeroMQ IPC

**[ZeroMQ](https://zeromq.org/)** (ZMQ) is the inter-process communication layer between the radio module hardware path and signal processing on the Linux host. Raw IQ from each band's RFIC is delivered over I2S on the DIN 41612 backplane (via the ECP5 PCIe interface card, up to 32 MHz bit clock at 1 MHz IQ bandwidth) into **`ht-module-daemon`**, which publishes framed RX IQ on per-band PUB sockets. GNU Radio (`gr-ht13g`), SDRangel, and recorders connect as SUB clients. TX IQ and hardware control use separate sockets.

| Plane | Sockets | Purpose |
|-------|---------|---------|
| IQ data | `iq_*` (PUB), `tx_*` (SUB) | Sample streams only; TX IQ does not key the PA by itself |
| Control | `ctrl` (REQ/REP) | Per-module PTT, frequency, squelch, TX timeout, gain, attenuator |
| Telemetry | `status` (PUB) | JSON: RSSI, PLL lock, temperature, SWR, alerts |

**Canonical wire formats, command tables, gr-ident preamble JSON, and LinHT compatibility** are documented in **[docs/zeromq-messages.md](docs/zeromq-messages.md)**.

When [gr-ident](https://github.com/Supermagnum/gr-ident) mode identification is enabled, a detect flowgraph publishes preamble decode JSON (for example `{"mode_id":20,"digital":false,...}`) so the repeater can route to the correct demodulator before audio is output — see [docs/zeromq-messages.md Section 6](docs/zeromq-messages.md#6-gr-ident-integration).

Local ZMQ `ctrl` commands use the same text as signed over-the-air frames in [Section 8](#8-authenticated-remote-control); only the transport differs.

Hardware daemon details: **[docs/RF-modules.md](docs/RF-modules.md)**, [Section 10](docs/RF-modules.md#10-software-interface-zeromq-ipc). Packages: **`libzmq3-dev`**, **`libzmq5`** on Ubuntu 26.04.

---

## 8. Authenticated Remote Control

Remote management of the repeater over the air replaces DTMF entirely. For **local** TX/RX switching, frequency, and gain on the Linux host, applications use the ZeroMQ `ctrl` socket described in [Section 7.5](#75-zeromq-ipc); Section 8 is the signed RF command channel for remote operators. All control commands are cryptographically signed using GnuPG-compatible keys. The repeater authenticates every command in **`repeater-authd`** (Rust) before acting on it and logs every accepted change with a complete audit trail.

**Normative specifications:** [docs/ota-remote-control.md](docs/ota-remote-control.md) (OTA frame format and verification), [docs/repeater-logic.md](docs/repeater-logic.md) (supervisor and PTT policy), [docs/implementation-language.md](docs/implementation-language.md) (Rust daemons).

### 8.1 What can be controlled remotely

| Task | Command (band: `2m`, `70cm`, `23cm`, or `all`) |
|------|---------|
| Adjust RF output power | `SET_PWR 70cm 5` |
| Check all temperatures | `GET_TEMP all` |
| Check battery state and current | `GET_BATTERY` |
| Enable or disable a radio module | `MOD_ENABLE 2m` / `MOD_DISABLE 23cm` |
| Set squelch threshold | `SET_SQUELCH 70cm -120` |
| Set transmit timeout (seconds) | `SET_TX_TIMEOUT 2m 300` |
| Set receive / transmit frequency | `SET_FREQ 2m 145500000` |
| Full status report | `GET_STATUS all` or `GET_STATUS 70cm` |
| Graceful reboot | `REBOOT` (elevated trust required) |

Per-module addressing uses the same band tokens as the ZeroMQ `ctrl` socket ([docs/zeromq-messages.md Section 4](docs/zeromq-messages.md#4-control-plane-ctrl)). A command without a band is rejected unless the command is inherently global (`GET_BATTERY`, `REBOOT`).

### 8.2 How it works — summary

Each command frame contains the target repeater callsign, the sender's callsign, a GNSS-disciplined UTC timestamp, the command text, and a detached GnuPG signature. The repeater verifies the signature against its keyring of trusted operator public keys before taking any action. Commands with invalid signatures, unknown senders, or timestamps outside ±30 seconds of the repeater's GNSS clock are silently discarded and logged as rejected.

The repeater itself has a GnuPG key pair (callsign as the key UID). It signs all outgoing replies and periodic status broadcasts, so operators can verify replies came from the correct repeater.

Because the frames are signed but not encrypted, every receiver on the network can read the content. Only the repeater whose callsign and key match the command target will act on it. All others ignore it. This means control commands propagate naturally across linked repeater networks.

### 8.3 gr-linux-crypto

The authentication system is implemented using **[gr-linux-crypto](https://github.com/Supermagnum/gr-linux-crypto)**, a GNU Radio out-of-tree module providing:

- Linux kernel keyring integration (keys stored in kernel, not in files)
- Nitrokey and hardware security token support (operator private key never leaves the token)
- Brainpool ECC signing and verification as native GNU Radio blocks
- `CallsignKeyStore` API — indexes public keys by amateur radio callsign
- `M17SessionKeyExchange` helpers for signing and frame composition
- Web of Trust key management compatible with existing GnuPG infrastructure
- AES-GCM and ChaCha20-Poly1305 authenticated encryption via kernel crypto API
- Multi-recipient ECIES encryption (up to 25 recipients) using Brainpool curves
- NIST CAVP-validated cryptographic implementations

Operator private keys should be stored on a **Nitrokey** hardware token. When the token is removed, `gr-linux-crypto` immediately clears all cached key material from memory — no residual key remains in the system.

### 8.4 Audit log

Every accepted command is written to `/var/log/repeater/audit.log` in append-only JSON format. Each entry records:

- GNSS-disciplined UTC timestamp
- Sender callsign and key fingerprint
- Command issued
- Previous value → new value (for state-changing commands)
- Signature verification result

This answers definitively: who changed it, when, what it was before, and what it was changed to. Rejected attempts are also logged with the reason (`KEY_NOT_FOUND`, `SIGNATURE_INVALID`, `REPLAY_DETECTED`). Daily log files are signed by the repeater key to produce a tamper-evident chain of custody.

### 8.5 Key management

Operator keys are GnuPG key pairs with the operator's callsign as the key UID (e.g. `LA1ABC`). New operators are added by importing their public key and signing it with the repeater key or an existing trusted operator key — no central authority, no backend service. The Web of Trust model applies: the repeater accepts a key if it is signed by at least one key already in its trusted keyring. Key management uses standard GnuPG tooling (`gpg --import`, `gpg --sign-key`) and the `gr-linux-crypto` `CallsignKeyStore` API.

---

## 9. Power Architecture

### Philosophy: DC UPS topology — no generator

The system uses a DC UPS topology rather than a traditional AC UPS or generator. The load runs from a DC bus at all times. When 230 V AC mains is present, an AC-DC converter simultaneously powers the bus and charges the battery. When mains fails, the battery takes over with zero switching delay — no relay, no inverter, no interruption. Generator backup is deliberately excluded; battery sizing and optional solar input provide the required autonomy.

### 9.1 AC-DC UPS module: Mean Well DRC series

The **Mean Well DRC-100B** (or DRC-240B for more headroom) is an all-in-one DIN-rail mounted unit providing AC-DC conversion, battery charging, and UPS function in a single package.

| Parameter | DRC-100B | DRC-240B |
|-----------|----------|----------|
| AC input | 90–264 VAC (universal, 230 V nominal) | 90–264 VAC |
| DC output voltage | 27.6 V (24 V nominal) | 27.6 V |
| Output current | 3.5 A continuous | 8.7 A continuous |
| Battery charge voltage | 27.6 V float | 27.6 V float |
| Battery charge current | 1.25 A | 2.5 A |
| UPS switchover | Zero — battery and load are on the same DC bus | Zero |
| Alarm signals | AC OK pin, Battery Low pin (TTL open-collector or relay contact) | Same |
| Mounting | DIN rail TS-35/7.5 or TS-35/15 | DIN rail |
| Certifications | UL, TÜV, CE | UL, TÜV, CE |

### 9.2 Battery: LiFePO4

**LiFePO4 (Lithium Iron Phosphate)** is the correct chemistry for a site repeater installation.

Advantages over lead-acid:

- Flat discharge curve — output voltage stays stable until ~90% depth of discharge
- Over 2,000 charge cycles at 80% DoD (versus 300–500 for lead-acid)
- Tolerates partial state of charge — no sulfation, no memory effect
- Operates across a wide temperature range (−20°C to +60°C)
- No off-gassing — safe in enclosed enclosures

**Recommended:** 24 V / 20–40 Ah LiFePO4 pack with integrated BMS (Battery Management System).

| Battery capacity | Energy | Runtime at 60 W avg load | Runtime at 80 W avg load |
|-----------------|--------|--------------------------|--------------------------|
| 20 Ah | 480 Wh | ~8 hours | ~6 hours |
| 30 Ah | 720 Wh | ~12 hours | ~9 hours |
| 40 Ah | 960 Wh | ~16 hours | ~12 hours |

The BMS inside the battery pack provides cell balancing, over-charge protection, over-discharge cutoff, and short-circuit protection. The DRC module's 27.6 V float voltage is compatible with an 8S LiFePO4 pack (8 × 3.2 V nominal = 25.6 V, fully charged at 8 × 3.65 V = 29.2 V — adjust DRC output trim to match).

### 9.3 Power budget estimate

| Component | Typical draw |
|-----------|-------------|
| Milk-V Megrez host + ECP5 interface card (idle–load) | 15–30 W |
| 5 × radio modules (RX only) | ~10 W |
| 5 × radio modules (1 active TX at 5 W RF) | ~15–20 W additional |
| GNSS receiver | ~0.1–0.3 W |
| Backplane, regulators, fans | ~5–10 W |
| **Total typical** | **~50–70 W** |
| **Total peak (all TX)** | **~90 W** |

The DRC-100B at 100 W provides comfortable headroom for typical operation. The DRC-240B is recommended if all five modules may transmit simultaneously or if a larger battery requires faster recharge.

### 9.4 Battery status monitoring in Linux

Battery state is exposed to Linux through two complementary paths.

#### Path 1 — DRC alarm GPIO signals

The DRC module's `AC OK` and `Battery Low` pins connect to GPIO inputs readable by the Linux host — via a USB GPIO adapter, or optional chassis-management GPIO on the ECP5 interface card. A systemd service monitors these signals:

- `AC OK` low → mains has failed, system is on battery
- `Battery Low` low → battery voltage below 22 V (24 V nominal system), initiate graceful shutdown

#### Path 2 — TI BQ27xxx fuel gauge (I²C)

A **TI BQ27427** or **BQ27441** fuel gauge IC on the battery pack connects to the Linux host over **I²C** (USB-I²C adapter or optional I²C on the ECP5 card). The Linux mainline driver `bq27xxx_battery_i2c` exposes the following to userspace via `/sys/class/power_supply/battery/`:

- `capacity` — state of charge in percent
- `voltage_now` — real-time battery terminal voltage
- `current_now` — charge or discharge current
- `time_to_empty_now` — estimated minutes remaining
- `temp` — battery temperature
- `status` — Charging / Discharging / Full / Not charging

Tools like `upower`, monitoring daemons, and SNMP agents read from this standard interface with no custom drivers or proprietary software.

---

## 10. Optional Solar Power

Solar input is an optional supplement to 230 V AC mains. There is no generator. The architecture is additive — the solar charge controller connects to the same 24 V battery bus as the DRC module, and both charge the battery simultaneously or independently depending on availability.

### 10.1 MPPT charge controller

A **Maximum Power Point Tracking (MPPT)** solar charge controller is required for LiFePO4 batteries. MPPT controllers achieve 97–99% tracking efficiency and include CC/CV (Constant Current / Constant Voltage) charging profiles correct for LiFePO4 chemistry.

**Recommended specification:**

| Parameter | Value |
|-----------|-------|
| Battery voltage | 24 V nominal (auto-detect 12/24 V) |
| Charge current | 20–30 A (depending on panel array size) |
| PV input voltage | Up to 100 V open-circuit |
| Battery type | LiFePO4 (dedicated profile or adjustable) |
| Communication | RS485 / Modbus (optional, for monitoring) |
| Mounting | Wall or DIN rail |

Suitable products: Victron SmartSolar MPPT 100/20 or 100/30 (Bluetooth + VE.Direct for monitoring), Bioenno Power SC-122430NE (LiFePO4-specific), or equivalent.

### 10.2 Panel sizing for Norway (latitude ~60–70°N)

Without a generator, battery capacity and panel sizing together determine winter survivability. Solar alone cannot sustain a Norwegian repeater through polar winter — AC mains is the essential primary source, and solar is a valuable summer supplement that reduces mains consumption and extends battery autonomy during grid outages.

| Season | Peak sun hours/day (estimate) | Panel output for coverage at 60 W load |
|--------|-------------------------------|----------------------------------------|
| Summer | 5–6 h | 2 × 100 W panels (~200 W array) |
| Equinox | 3–4 h | 3 × 100 W panels (~300 W array) |
| Winter | <1 h | Solar supplemental only — AC mains essential |

> **Note:** In winter at high northern latitudes, days may have fewer than 2 usable solar hours, and snow cover on panels reduces output further. The system must be designed to operate indefinitely from AC mains alone. Solar provides additional battery reserve and energy cost savings during the other eight months of the year.

### 10.3 Wiring topology

```
[230 V AC mains] ──► [Mean Well DRC-100B/240B] ──┐
                                                   ├──► [24 V DC bus] ──► [Backplane power distribution]
[solar panels] ──► [MPPT charge controller] ──────┘         │
                                                             │
                                               [24 V LiFePO4 battery + BMS]
                                                             │
                                               [BQ27xxx I²C fuel gauge] ──► [Linux host I²C]
                                               [DRC AC OK / Bat Low pins] ─► [Linux host GPIO]
                                               [GNSS receiver] ─────────────► [Megrez USB / UART]
                                               [GNSS 1PPS output] ──────────► [ECP5 or GPIO adapter]
```

The battery bus is always live. The DRC module and MPPT controller both float-charge the battery and power the bus simultaneously. Priority management is automatic — each unit regulates to its output voltage setpoint and the higher-voltage source contributes more current naturally.

---

## 11. Commercial and Licensed Private Network Applications

Although designed for amateur radio use, the hardware and software in this system are directly applicable to licensed commercial and private network deployments. The RFIC frequency ranges, the cryptographic infrastructure, and the open architecture make this a compelling platform for organisations requiring transparent, auditable, and cost-effective radio infrastructure.

### 11.1 Frequency coverage and commercial band overlap

The HT13G-M and HT13G-S RFICs cover ranges that encompass the major VHF and UHF commercial land mobile allocations used worldwide:

| RFIC | Coverage | Commercial allocations included |
|------|----------|----------------------------------|
| HT13G-M VHF chain | 130–175 MHz | VHF high band PMR (150–174 MHz) |
| HT13G-M UHF chain | 400–480 MHz | UHF PMR (450–470 MHz), TETRA UHF |
| HT13G-S | 1200–1300 MHz | L-band data links, TETRA 1.4 GHz |

The hardware does not distinguish between amateur and commercial allocations. A module configured for 144 MHz and a module configured for 460 MHz use identical hardware; only the firmware frequency word differs. For a licensed commercial operator, the same field-replaceable module PCB covers the relevant allocation with no hardware change.

### 11.2 Encryption for licensed commercial use

Encryption of voice and data is legally permitted — and often required — on commercial and private PMR allocations in most jurisdictions. The cryptographic infrastructure already present in this system (see [Section 8.3](#83-gr-linux-crypto)) is fully capable of supporting encrypted operation:

- **AES-256-GCM** authenticated encryption via the Linux kernel crypto API
- **Brainpool P-256/P-384 ECC** for key exchange and digital signatures — chosen specifically to avoid algorithm monoculture and NSA-influenced curve parameters
- **Multi-recipient ECIES** allowing a single transmission to be decrypted by up to 25 independent key holders — useful for fleet or group communications
- **Nitrokey hardware token** support ensuring private keys never exist in software-accessible memory; removing the token immediately clears all cached key material
- **NIST CAVP-validated** cryptographic implementations with 268+ million fuzz-test executions and zero crashes or memory safety violations recorded

The same `gr-linux-crypto` module that handles amateur radio authentication handles commercial encrypted voice and data. No additional cryptographic software is required.

### 11.3 Comparison with proprietary commercial PMR systems

This system provides a fully open-source, open-silicon alternative to proprietary commercial PMR infrastructure:

| | This system | Motorola MOTOTRBO / Hytera DMR / Kenwood NEXEDGE |
|--|-------------|--------------------------------------------------|
| Hardware source | Open design, field-replaceable modules | Proprietary, vendor-specific |
| Firmware | Open source, fully auditable | Closed, vendor-controlled |
| Encryption implementation | Auditable open-source (gr-linux-crypto, kernel crypto API) | Proprietary, unauditable |
| Key management | Standard GnuPG Web of Trust, Nitrokey hardware tokens | Vendor key management systems |
| Vendor lock-in | None — standard interfaces throughout | High — proprietary protocols and accessories |
| Remote management | Cryptographically authenticated, tamper-evident audit log | Vendor management software |
| Cost at scale | Significantly lower — open hardware and software | High — per-unit licensing and support contracts |

For municipalities, utilities, transport operators, emergency services, and other organisations in jurisdictions where **open and independently auditable communications infrastructure** is required or preferred, this architecture offers capabilities unavailable in proprietary systems.

### 11.4 Simulcast capability

The GNSS-disciplined nanosecond timestamps embedded in every ZeroMQ IQ frame provide the foundation for simulcast operation across linked sites — a requirement in many commercial land mobile deployments covering large geographic areas.

The infrastructure already in place:

- All sites share a common GNSS time reference accurate to 5 ns RMS (ZED-F9T) or 30 ns RMS (NEO-M9N)
- Per-module VCTCXO discipline holds each band's carrier to sub-millihertz accuracy
- ZeroMQ IQ frames carry 64-bit nanosecond UTC timestamps from the point of reception
- The `ctrl` socket supports per-module frequency and timing control

What a simulcast implementation would add in software:

- A transmit scheduler in `ht-module-daemon` that holds IQ frames in a buffer and releases them at a specified future UTC timestamp, ensuring all sites transmit the same audio at the same moment regardless of network path delay
- An inter-site delay measurement and compensation coordinator
- A phase calibration procedure for the RF overlap zones

The hardware and transport infrastructure for this is already present. Simulcast is a natural software extension requiring no hardware changes.

### 11.5 Legal and regulatory notes

Operators deploying this system on commercial or private PMR allocations are responsible for ensuring compliance with all applicable regulations in their jurisdiction, including:

- Holding the appropriate radio licence for the frequencies used
- Complying with technical emission standards (bandwidth, power, spurious emissions)
- Complying with any local regulations governing the use of encryption on radio
- Ensuring type approval or equipment authorisation requirements are met where applicable

The open nature of the hardware and software stack facilitates regulatory compliance by making the complete technical specification of the system available for inspection. **This documentation does not constitute legal or regulatory advice.**

---

## 12. System Integration Summary

### Complete bill of materials overview

| Category | Component | Standard / Interface |
|----------|-----------|---------------------|
| Backplane | 3U Eurocard subrack with DIN 41612 backplane | IEC 60297; DIN 41612 Type C + har-bus 64 |
| Power supply | Mean Well DRC-100B or DRC-240B (DIN rail) | 24 V DC bus to backplane |
| Radio module ×3 | 2 m / 70 cm / 23 cm SDR TX/RX | DIN 41612 Eurocard (100 × 160 mm), RP-SMA front panel |
| Expansion slots | Spare (slots D–E) | DIN 41612 Eurocard |
| Compute host | Milk-V Megrez Mini-ITX (ESWIN EIC7700X) | 32 GB LPDDR5 soldered; M.2 NVMe; 2× GbE; Wi-Fi 6 |
| Backplane interface | ECP5-25F PCIe card | PCIe Gen1 ×1 (in Megrez Gen3 ×4 slot); USB fallback |
| Module daemon | `ht-module-daemon` (Rust, libzmq) | ZMQ IPC under `/run/ht-module/` — see [docs/repo-map.md](docs/repo-map.md) |
| Repeater control | `repeater-control` repo: `repeater-supervisord` + `repeater-authd` (Rust) | [docs/runtime/repeater-control.md](docs/runtime/repeater-control.md) |
| Storage | NVMe SSD (240 GB+), M.2 M-Key on Megrez | PCIe 2.0 ×2 |
| GNSS receiver | u-blox NEO-M9N (standard) or ZED-F9T (precision) | USB or UART to Megrez; 1PPS to ECP5 or GPIO adapter |
| GNSS antenna | Active multi-band patch, roof/mast mount | SMA / TNC coaxial |
| Battery | 24 V / 20–40 Ah LiFePO4 with BMS | 24 V DC bus |
| Battery monitor | TI BQ27427 / BQ27441 fuel gauge | I²C → Linux host (USB-I²C or ECP5) |
| AC alarm signals | DRC `AC OK` + `Battery Low` pins | GPIO → Linux host (USB GPIO or ECP5) |
| Solar (optional) | MPPT 24 V / 20–30 A controller + panel array | 24 V DC bus |

### Software stack summary

| Layer | Component |
|-------|-----------|
| OS | Ubuntu 24.04 LTS, Debian, or Fedora on Milk-V Megrez (EIC7700X) |
| SDR framework | GNU Radio 4.0 + VOLK 3.3 (RISC-V vector where supported) |
| AI / NPU | EIC7700X 19.95 TOPS INT8 — signal classification, AI squelch (optional) |
| IQ transport | [ZeroMQ](https://zeromq.org/) — see [docs/zeromq-messages.md](docs/zeromq-messages.md) |
| Mode identification | [gr-ident](https://github.com/Supermagnum/gr-ident) preamble (optional automatic mode switching) |
| Repeater application (fork upstream) | [f4exb/sdrangel](https://github.com/f4exb/sdrangel) — TX/RX, plugins, server/REST |
| Remote monitoring | OpenWebRX+ (browser-based, multi-user) |
| Supplementary SDR tools | GQRX, QRadioLink application (ROIP/linking), SDR++ |
| Digital voice blocks | [gr-qradiolink](https://github.com/Supermagnum/gr-qradiolink) — DMR, dPMR, NXDN, P25, M17, FreeDV, LDPC FEC as GNU Radio OOT blocks |
| GNSS daemon | gpsd (NMEA/UBX parsing, shared memory) |
| Time discipline | chrony (GNSS SHM + PPS → Stratum 1 NTP) |
| Frequency correction | Software PPM in GNU Radio / SDRangel (standard); hardware 10 MHz ref (optional) |
| Remote control | `repeater-authd` (Rust) + gr-linux-crypto (Brainpool, CallsignKeyStore, Nitrokey) |
| Audit log | `/var/log/repeater/audit.log` — append-only JSON, daily repeater-signed rotation |
| Crypto | Linux kernel crypto API + GnuPG userspace + gr-linux-crypto |
| Battery monitoring | `bq27xxx_battery_i2c` → `/sys/class/power_supply/battery/` |
| RAID | Optional mdadm RAID 1 if second NVMe added |
| UPS signalling | systemd service on DRC GPIO alarm pins |
| Inter-site linking | GbE RJ45 (primary); optional fiber — ZeroMQ TCP, ROIP, simulcast, remote control |
| Site management | Dual GbE; optional Wi-Fi 6 / SSH remote access |

### Key standards used

| Standard | Description |
|----------|-------------|
| RISC-V RV64GCH | Host CPU ISA (ESWIN EIC7700X, SiFive P550) |
| IEC 60297 | 3U Eurocard mechanical form factor |
| DIN 41612 / IEC 60603-2 | Backplane signal connector (96-pin Type C) |
| DIN 41612 har-bus 64 | High-current power contacts (+12 V PA rail) |
| NMEA 0183 | GNSS serial data protocol |
| UBX | u-blox binary GNSS protocol |
| RFC 5905 | NTP v4 (chrony implementation) |
| OpenPGP / RFC 4880 | GnuPG key format, Web of Trust, digital signatures |
| IEC 62619 | Battery safety standard for lithium systems |
