# SDR Multiband Repeater System Design

**Revision:** 1.1  
**Date:** May 2026  
**Architecture:** Open Silicon · Linux · Modular OpenVPX  

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Radio Modules](#2-radio-modules)
3. [Backplane Architecture](#3-backplane-architecture)
4. [Compute Module](#4-compute-module)
5. [Storage](#5-storage)
6. [GNSS Timing and Frequency Reference](#6-gnss-timing-and-frequency-reference)
7. [Software Stack](#7-software-stack)
8. [Authenticated Remote Control](#8-authenticated-remote-control)
9. [Power Architecture](#9-power-architecture)
10. [Optional Solar Power](#10-optional-solar-power)
11. [System Integration Summary](#11-system-integration-summary)

---

## 1. System Overview

This document describes a modular, Linux-based, software-defined radio (SDR) repeater system capable of simultaneous operation across the 2 metre, 70 cm, and 23 cm amateur radio bands. The system is designed around open standards throughout: open silicon CPU, open backplane standards, and open-source software. It runs from 230 V AC mains with seamless battery backup, and optionally from solar power. No generator is used or required.

### Design principles

- All hardware uses open or openly-documented standards (RISC-V ISA, OpenVPX/VITA 65, VITA 46, VITA 67)
- All software is free and open source (Linux, GNU Radio ecosystem)
- Pluggable modular architecture — radio modules are field-replaceable
- Single DC bus throughout — no AC/DC inversion on the load side
- Battery backup is zero-switchover (DC UPS topology)
- Power sources: 230 V AC mains + optional solar — no generator
- Temperature and battery state monitored in Linux userspace via standard kernel interfaces
- System time disciplined by GNSS (GPS/GLONASS/Galileo/BeiDou) — no internet dependency
- Optional GNSS-disciplined frequency reference for SDR oscillator correction

---

## 2. Radio Modules

The system supports up to four pluggable radio modules on the backplane. Three bands are defined; the fourth slot is spare or expansion.

### Module specifications

| Module | Band | Frequency Range | IQ Bandwidth | TX Power | Antenna |
|--------|------|-----------------|--------------|----------|---------|
| 2 metre | VHF | 144–146 MHz | 500 kHz | 5 W | RP-SMA (front panel) |
| 70 cm | UHF | 432–438 MHz | 500 kHz | 5 W | RP-SMA (front panel) |
| 23 cm | UHF/SHF | 1240–1258 MHz | 500 kHz | 5 W | RP-SMA (front panel) |
| Expansion | — | User-defined | — | — | RP-SMA (front panel) |

### Module interface

Each module connects to the backplane via:

- **Edge connector:** VITA 46 high-speed serial connector (Eurocard edgecard)
- **Data bus:** PCIe Gen 3 or 1/10 GbE over VITA 46 fabric — sufficient for 500 kHz IQ streams from all four modules simultaneously
- **Power:** +12 V, +5 V, +3.3 V from backplane VITA 62 power rails
- **Temperature monitoring:** I²C on the VITA 46 J0 utility plane (per-slot sensor readable by the chassis manager and Linux `hwmon`)
- **RF antenna port:** RP-SMA on the module front panel for the antenna connection. IQ data is transported digitally over the VITA 46 data bus; the RP-SMA is the antenna interface only, not a backplane RF path.

> **Note on VITA 67:** VITA 67 RF backplane connectors (SMPM/SMPS blind-mate coaxial) are available as an option if RF signals ever need to be routed through the backplane rather than digitised at the module. At 144–1258 MHz with 500 kHz IQ bandwidth, digital transport over VITA 46 is the preferred and simpler approach, making front-panel RP-SMA the natural choice.

---

## 3. Backplane Architecture

### Standard: 3U OpenVPX (VITA 65)

The backplane follows the VITA 65 OpenVPX standard, the dominant open modular standard for SDR and embedded computing systems. It uses Eurocard edgecard connectors (VITA 46) as required.

Key characteristics:

- **Form factor:** 3U (Eurocard height), pluggable card architecture
- **Edge connector:** VITA 46 multi-gigabit serial connector — the edgecard interface for all modules
- **Slot count:** 5 slots minimum — 4 × payload (radio modules) + 1 × VITA 62 power supply
- **Data fabric:** PCIe Gen 3 or Ethernet switch topology connecting all payload slots
- **Utility plane (J0):** I²C / SMBus for temperature monitoring, chassis management, and per-slot health signals
- **Power distribution:** VITA 62 pluggable PSU — provides +24 V bus, with per-slot regulation to +12 V, +5 V, +3.3 V

### Recommended chassis: Pixus Technologies 3U OpenVPX Cube

The Pixus 3U OpenVPX Cube chassis is only 42 HP (8.4 inches) wide and accommodates four to five OpenVPX boards in the 3U form factor with a compact power supply. Various VITA 65 backplane profiles are available with options for VITA 66 or 67 interfaces, and pluggable VITA 62 or fixed ATX power supply units are supported.

### Backplane standards reference

| Standard | Role |
|----------|------|
| VITA 46 | Base VPX connector and signalling |
| VITA 65 (OpenVPX) | System-level interoperability profiles |
| VITA 62 | Power supply form factor and rails |
| VITA 67 | Optional RF coaxial backplane connectors (SMPM/SMPS) |

---

## 4. Compute Module

### CPU: SpacemiT K3 (RISC-V, RVA23)

The main compute module is based on the **SpacemiT Key Stone K3** SoC, an 8-core RVA23-compliant RISC-V processor. This is the recommended single-chip solution — no separate security coprocessor is needed because the K3 provides hardware cryptographic acceleration consumed directly by the Linux kernel and GnuPG in userspace.

#### Processor specifications

| Parameter | Value |
|-----------|-------|
| CPU cores | 8 × X100 RISC-V (RVA23 compliant) |
| Clock speed | Up to 2.4 GHz |
| AI cores | 8 × A100 (60 TOPS, RVV 1.0 up to 1024-bit) |
| Memory | Up to 32 GB LPDDR5-6400 |
| Linux kernel | Mainline support from kernel 7.0 |
| OS support | Ubuntu 26.04 LTS (RVA23 required), Bianbu 3.0 (Ubuntu-based), Fedora, Deepin 25 |

#### Hardware cryptography

The K3 SoC provides hardware-accelerated cryptographic primitives exposed to the Linux kernel's crypto API (`/proc/crypto`):

- AES (128/256-bit, CBC/GCM/CTR)
- SHA-256 / SHA-512
- RSA
- SM2, SM3, SM4 (Chinese national standards)
- Hardware TRNG

These are consumed transparently by GnuPG, OpenSSL, dm-crypt/LUKS, and the kernel keyring — no separate secure element or coprocessor is needed. GPG keys live in kernel keyring and user keyring as standard Linux practice.

#### I/O peripherals (K3 Pico-ITX board)

| Interface | Detail |
|-----------|--------|
| USB | 2 × USB 3.2 Gen1 Type-C + 4 × USB 2.0 (system installation, peripherals) |
| Wired LAN | 1 × GbE RJ45 + 1 × 10GbE SFP+ |
| Wireless | Wi-Fi 6 + Bluetooth 5.2 (onboard) |
| Temperature | EC controller on I²C/UART/GPIO expansion (FPC connector) |
| Battery status | I²C via EC-IO connector — see Section 8 |
| Storage | 1 × M.2 M-Key 2280 (PCIe Gen3 ×4) + 1 × M.2 B-Key 2242/3052 (PCIe Gen3 ×2 + USB) |
| Debug | UART, JTAG, serial console header |

#### Available board variants (same K3 SoC, same design)

| Vendor | Product name | Notes |
|--------|-------------|-------|
| SpacemiT / Sipeed | K3 Pico-ITX | Reference design, $299–$399 |
| Milk-V | Jupiter 2 | Same board in chassis, $300–$575 |
| Banana Pi | BPI-SM10 (K3-CoM260) | SoM form factor for carrier board integration |

For integration into the OpenVPX backplane, the **K3-CoM260 SoM** (260-pin SO-DIMM, compatible with Jetson Orin Nano/NX carrier boards) is the cleanest path, enabling a custom 3U VPX carrier board design.

---

## 5. Storage

### Configuration: 2 × 240 GB NVMe SSD in Linux software RAID 1 (mirror)

Both M.2 slots on the K3 board are populated with 240 GB M.2 NVMe SSDs:

- **Slot 1:** M.2 M-Key 2280, PCIe Gen3 ×4 (full bandwidth when slot 2 is empty)
- **Slot 2:** M.2 B-Key 2242/3052, PCIe Gen3 ×2 (bandwidth shared with slot 1 when both populated)

When both slots are in use, the M-Key slot runs at PCIe Gen3 ×2. For a mirrored pair this is entirely acceptable — RAID 1 reads from one drive and writes to both; sustained throughput around 1.5–2 GB/s per slot is far more than any GNU Radio or repeater workload requires.

#### RAID setup

```bash
mdadm --create /dev/md0 --level=1 --raid-devices=2 /dev/nvme0n1 /dev/nvme1n1
```

The kernel `mdadm` RAID 1 array appears as `/dev/md0` and is treated as a single block device. Status is readable via:

```bash
cat /proc/mdstat
mdadm --detail /dev/md0
```

Systemd monitors the array and alerts on drive failure. The mirrored configuration ensures the repeater keeps running if one SSD fails, with the faulty drive replaceable after halting the array.

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

# Enable PPS discipline (1PPS GPIO wired to K3 EC-IO GPIO pin)
# Add to /boot/firmware/config.txt or device tree:
# dtoverlay=pps-gpio,gpiopin=<pin>
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

**Ubuntu 26.04 LTS** (or Bianbu 3.0, its Ubuntu-based derivative pre-installed on K3 hardware). Ubuntu 26.04 requires RVA23 compliance, which the K3 satisfies — it is one of the first RISC-V platforms to qualify.

### 7.2 GNU Radio 4.0

GNU Radio 4.0 reached Release Candidate 1 in March 2026. The core architecture is stable, the execution model is well-defined, and the API is no longer expected to undergo major breaking changes. It is the signal processing foundation of the repeater — handling IQ data ingestion from modules, filtering, demodulation, repeater logic (CTCSS/DCS detection, squelch, crossband linking), and re-modulation.

**VOLK 3.3.0** (February 2026) added specific RISC-V vector optimisations. The K3's X100 cores support RVV 1.0 up to 1024-bit wide vector operations, which VOLK uses for SIMD-accelerated kernels — filters, FFTs, correlators — without any manual tuning.

GNU Radio is the most powerful and flexible option but has a steep learning curve due to its flowgraph / block-programming paradigm. For operators who prefer a more direct interface, the following GNU Radio-based frontends are available.

---

### 7.3 User-friendly frontends (GNU Radio-based or GNU Radio-compatible)

These applications sit on top of GNU Radio or share its ecosystem, offering conventional point-and-click interfaces instead of flowgraph programming.

#### GQRX

GQRX is a software-defined radio receiver built on top of GNU Radio and the Qt graphical toolkit. It provides a simple, familiar receiver interface — waterfall display, tuning dial, demodulator selector, audio output, bookmark manager, and TCP remote control. It is the most widely used GNU Radio-based frontend on Linux, reliable and lightweight. It does not support transmit.

- **Best for:** Monitoring, receive-only operations, scripting via its TCP control interface
- **Limitations:** No digital voice decoding built in; no transmit; limited plugin ecosystem

#### SDRangel

SDRangel is a Qt5/OpenGL SDR frontend that supports both receive and transmit simultaneously across multiple SDR devices. It includes a large built-in decoder suite covering DMR, D-Star, NXDN, YSF, FT8, APRS, AIS, ADS-B, and many others. It can run TX and RX on separate SDR devices concurrently, making it well-suited to a repeater role where simultaneous receive and transmit is required. The interface is dense but highly capable.

- **Best for:** Digital voice repeater operation, multi-mode monitoring, TX/RX simultaneous use
- **Limitations:** Steep learning curve; resource-intensive on lower-end hardware
- **RISC-V status:** Confirmed running on Banana Pi BPI-F3 (SpacemiT K1, RISC-V)

#### QRadioLink

QRadioLink is a multimode SDR transceiver application built directly on top of GNU Radio, specifically designed for Linux and repeater/VOIP bridging use cases. It supports radio-over-IP (ROIP) bridging using Internet protocols, making it useful for linking the repeater to EchoLink, AllStar, or similar networks. It supports analog and digital modes and uses a Qt5 UI.

- **Best for:** Repeater linking, radio-over-IP, GNU Radio-backed transceiver operation
- **Limitations:** Smaller community than GQRX or SDRangel; less polished UI

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
| QRadioLink | ✓ | ✓ | Built on GR | Analog + digital | ROIP/EchoLink | ✓ |
| SDR++ | ✗ | ✓ | SoapySDR | Via plugins | Network source | ✓ |
| OpenWebRX+ | ✗ | ✓ | Compatible | FT8, APRS, ADS-B | Browser-based | ✓ |

**Recommended combination for a repeater:** SDRangel for TX/RX repeater logic and digital modes, with OpenWebRX+ running in parallel for remote site monitoring over the network.

---

## 8. Authenticated Remote Control

Remote management of the repeater over the air replaces DTMF entirely. All control commands are cryptographically signed using GnuPG-compatible keys. The repeater authenticates every command before acting on it and logs every accepted change with a complete audit trail. Full technical specification, GNU Radio flowgraph integration, and operator workflows are described in the companion document **SDR Repeater — RF Module and RFIC Specification**, Section 11.

### 9.1 What can be controlled remotely

| Task | Command |
|------|---------|
| Adjust RF output power | `SET_PWR band watts` |
| Check all temperatures | `GET_TEMP` |
| Check battery state and current | `GET_BATTERY` |
| Enable or disable a radio module | `MOD_ENABLE` / `MOD_DISABLE` |
| Set squelch threshold | `SET_SQUELCH band dBm` |
| Set receive / transmit frequency | `SET_FREQ band Hz` |
| Full status report | `GET_STATUS` |
| Graceful reboot | `REBOOT` (elevated trust required) |

### 9.2 How it works — summary

Each command frame contains the target repeater callsign, the sender's callsign, a GNSS-disciplined UTC timestamp, the command text, and a detached GnuPG signature. The repeater verifies the signature against its keyring of trusted operator public keys before taking any action. Commands with invalid signatures, unknown senders, or timestamps outside ±30 seconds of the repeater's GNSS clock are silently discarded and logged as rejected.

The repeater itself has a GnuPG key pair (callsign as the key UID). It signs all outgoing replies and periodic status broadcasts, so operators can verify replies came from the correct repeater.

Because the frames are signed but not encrypted, every receiver on the network can read the content. Only the repeater whose callsign and key match the command target will act on it. All others ignore it. This means control commands propagate naturally across linked repeater networks.

### 9.3 gr-linux-crypto

The authentication system is implemented using **[gr-linux-crypto](https://github.com/Supermagnum/gr-linux-crypto)**, a GNU Radio out-of-tree module providing:

- Linux kernel keyring integration (keys stored in kernel, not in files)
- Nitrokey and hardware security token support (operator private key never leaves the token)
- Brainpool ECC signing and verification as native GNU Radio blocks
- `CallsignKeyStore` API — indexes public keys by amateur radio callsign
- `M17SessionKeyExchange` helpers for signing and frame composition
- Web of Trust key management compatible with existing GnuPG infrastructure

Operator private keys should be stored on a **Nitrokey** hardware token. When the token is removed, `gr-linux-crypto` immediately clears all cached key material from memory — no residual key remains in the system.

### 9.4 Audit log

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
| SpacemiT K3 SBC (idle–load) | 10–20 W |
| 4 × radio modules (RX only) | ~8 W |
| 4 × radio modules (1 active TX at 5 W RF) | ~15–20 W additional |
| GNSS receiver | ~0.1–0.3 W |
| Backplane, regulators, fans | ~5–10 W |
| **Total typical** | **~40–60 W** |
| **Total peak (all TX)** | **~80 W** |

The DRC-100B at 100 W provides comfortable headroom for typical operation. The DRC-240B is recommended if all four modules may transmit simultaneously or if a larger battery requires faster recharge.

### 9.4 Battery status monitoring in Linux

Battery state is exposed to Linux through two complementary paths.

#### Path 1 — DRC alarm GPIO signals

The DRC module's `AC OK` and `Battery Low` pins connect to two GPIO inputs on the K3's EC-IO FPC connector. A systemd service monitors these signals:

- `AC OK` low → mains has failed, system is on battery
- `Battery Low` low → battery voltage below 22 V (24 V nominal system), initiate graceful shutdown

#### Path 2 — TI BQ27xxx fuel gauge (I²C)

A **TI BQ27427** or **BQ27441** fuel gauge IC wires to the K3's I²C bus (available on the EC-IO connector). The Linux mainline driver `bq27xxx_battery_i2c` exposes the following to userspace via `/sys/class/power_supply/battery/`:

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
                                                   ├──► [24 V DC bus] ──► [OpenVPX VITA 62 PSU]
[Solar panels] ──► [MPPT charge controller] ──────┘         │
                                                             │
                                               [24 V LiFePO4 battery + BMS]
                                                             │
                                               [BQ27xxx I²C fuel gauge] ──► [K3 EC-IO I²C]
                                               [DRC AC OK / Bat Low pins] ─► [K3 EC-IO GPIO]
                                               [GNSS receiver] ─────────────► [K3 USB / UART]
                                               [GNSS 1PPS output] ──────────► [K3 EC-IO GPIO]
```

The battery bus is always live. The DRC module and MPPT controller both float-charge the battery and power the bus simultaneously. Priority management is automatic — each unit regulates to its output voltage setpoint and the higher-voltage source contributes more current naturally.

---

## 11. System Integration Summary

### Complete bill of materials overview

| Category | Component | Standard / Interface |
|----------|-----------|---------------------|
| Backplane | Pixus 3U OpenVPX Cube, 5-slot | VITA 65, VITA 46 edgecard |
| Power supply slot | Mean Well DRC-100B or DRC-240B (DIN rail) | VITA 62 to OpenVPX |
| Radio module ×3 | 2 m / 70 cm / 23 cm SDR TX/RX | VITA 46 edgecard, RP-SMA front panel |
| Expansion slot | Spare (4th module or switch card) | VITA 46 edgecard |
| Compute | SpacemiT K3 Pico-ITX or K3-CoM260 SoM | PCIe Gen3, GbE RJ45, USB 3.2 |
| Storage | 2 × 240 GB M.2 NVMe SSD, mdadm RAID 1 | M-Key + B-Key on K3 board |
| GNSS receiver | u-blox NEO-M9N (standard) or ZED-F9T (precision) | USB or UART to K3; 1PPS to GPIO |
| GNSS antenna | Active multi-band patch, roof/mast mount | SMA / TNC coaxial |
| Battery | 24 V / 20–40 Ah LiFePO4 with BMS | 24 V DC bus |
| Battery monitor | TI BQ27427 / BQ27441 fuel gauge | I²C → K3 EC-IO |
| AC alarm signals | DRC `AC OK` + `Battery Low` pins | GPIO → K3 EC-IO |
| Solar (optional) | MPPT 24 V / 20–30 A controller + panel array | 24 V DC bus |

### Software stack summary

| Layer | Component |
|-------|-----------|
| OS | Ubuntu 26.04 LTS (RISC-V RVA23) |
| SDR framework | GNU Radio 4.0 + VOLK 3.3 (RISC-V vector optimised) |
| Repeater frontend | SDRangel (TX/RX, digital modes) |
| Remote monitoring | OpenWebRX+ (browser-based, multi-user) |
| Supplementary SDR tools | GQRX, QRadioLink (ROIP/linking), SDR++ |
| GNSS daemon | gpsd (NMEA/UBX parsing, shared memory) |
| Time discipline | chrony (GNSS SHM + PPS → Stratum 1 NTP) |
| Frequency correction | Software PPM in GNU Radio / SDRangel (standard); hardware 10 MHz ref (optional) |
| Remote control | gr-linux-crypto (Brainpool signing/verification, CallsignKeyStore, Nitrokey integration) |
| Audit log | `/var/log/repeater/audit.log` — append-only JSON, daily repeater-signed rotation |
| Crypto | Linux kernel crypto API (K3 hardware AES/SHA/RSA) + GnuPG userspace + gr-linux-crypto |
| Battery monitoring | `bq27xxx_battery_i2c` → `/sys/class/power_supply/battery/` |
| RAID | mdadm RAID 1 on two NVMe SSDs |
| UPS signalling | systemd service on DRC GPIO alarm pins |

### Key standards used

| Standard | Description |
|----------|-------------|
| RISC-V RVA23 | Open CPU instruction set architecture |
| VITA 46 | VPX base connector and signalling |
| VITA 65 (OpenVPX) | Backplane and module interoperability profiles |
| VITA 62 | Power supply interface for VPX chassis |
| VITA 67 | Optional RF coaxial backplane connectors |
| NMEA 0183 | GNSS serial data protocol |
| UBX | u-blox binary GNSS protocol |
| RFC 5905 | NTP v4 (chrony implementation) |
| OpenPGP / RFC 4880 | GnuPG key format, Web of Trust, digital signatures |
| IEC 62619 | Battery safety standard for lithium systems |
| IPC-2141 | PCB design reference for edgecard connectors |

---

