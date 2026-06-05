# Implementation Roadmap

**Revision:** 1.1  
**Date:** May 2026  

This document orders work for developers and RF engineers. **No implementation code lives in this repository** — see [repo-map.md](repo-map.md).

## Phase A — Contract and bench (no custom silicon)

**Goal:** Prove ZMQ contracts and repeater logic on commodity hardware.

| Milestone | Deliverable | Owner skill |
|-----------|-------------|-------------|
| A1 | `ht-module-daemon` stub: PUB fake IQ, REP `ctrl`, PUB `status` (Rust) | Software |
| A2 | `repeater-supervisord` lease + state machine per [repeater-logic.md](repeater-logic.md) | Software |
| A3 | `repeater-authd` verify + audit per [ota-remote-control.md](ota-remote-control.md) | Software |
| A4 | GNU Radio 4 flowgraph: ZMQ SUB -> NFM demod -> optional cross-band (external repo) | Software |
| A5 | Reference RF bridge: adapt [LinHT-utils zmq_proxy](https://github.com/M17-Project/LinHT-utils) or SX1255 + GPIO PTT | RF + software |
| A6 | Fork [f4exb/sdrangel](https://github.com/f4exb/sdrangel): ZMQ sample source plugin spec implemented | Software |

**Exit criteria:** One band (70 cm recommended) repeats analog FM with PTT via `ctrl`; OTA command changes squelch on bench loopback; audit log entries written.

## Phase B — Production module integration

**Goal:** Real HT13G-M / HT13G-S modules over I2S.

| Milestone | Deliverable | Owner skill |
|-----------|-------------|-------------|
| B1 | Kernel SAI/DMA driver or validated ALSA-DMA path | Software / kernel |
| B2 | `ht-module-daemon` production: SPI, EEPROM, PTT sequence per [RF-modules.md](RF-modules.md) Section 10 | Software + RF |
| B3 | `gr-ht13g` OOT: `ht13g_source` / `ht13g_sink` (C++/Python) | Software |
| B4 | Three-band `status` and per-band `ctrl` | Software |
| B5 | chrony + 1PPS VCTCXO trim closed loop | RF + software |

**Exit criteria:** All installed bands publish IQ at 500 kSa/s; TX timeout and PLL unlock tested on hardware.

## Phase C — Site operations

| Milestone | Deliverable |
|-----------|-------------|
| C1 | OpenWebRX+ parallel monitoring |
| C2 | gr-ident + gr-linux-crypto on-air profiles documented per site |
| C3 | mdadm, DRC GPIO, fuel gauge integration (README Sections 9–10) |
| C4 | Optional SvxLink / AllStar audio bridge (adjunct, not core stack) |

## Phase D — Custom RFIC (parallel track)

Per [RF-modules.md](RF-modules.md) Section 11 (MPW). Does not block Phase A software.

| Milestone | Deliverable |
|-----------|-------------|
| D1 | Phase 1 MPW VHF RX validation |
| D2 | Integrated HT13G-M silicon on module PCB |

## Repository creation order

1. `ht-module-daemon` (Rust) — [runtime/ht-module-daemon.md](runtime/ht-module-daemon.md)
2. `repeater-control` (Rust) — [runtime/repeater-control.md](runtime/repeater-control.md)
3. `gr-ht13g` — [runtime/gr-ht13g.md](runtime/gr-ht13g.md)
4. `sdr-repeater-flowgraphs` — [runtime/sdr-repeater-flowgraphs.md](runtime/sdr-repeater-flowgraphs.md)
5. `sdrangel` fork — [runtime/sdrangel-fork.md](runtime/sdrangel-fork.md)

Names are suggestions; record actual URLs in [repo-map.md](repo-map.md) when created.

## Out of scope for Phase A–B

- OpenRepeater / Supermagnum openrepeater (deprecated for this project)
- Pi-Star images as primary stack (OpenDVM/MMDVMHost are alternate **digital hotspot** products only)
- Implementation code commits in **this** spec repository
