# Repository Map

**Revision:** 1.1  
**Date:** May 2026  

Where specification ends and implementation repositories begin. Update this table when new repos are created.

## This repository (spec only)

| Repository | Role |
|------------|------|
| **SDR-repeater** (this tree) | System design, RF spec, ZMQ wire formats, developer docs — **no runtime code** |

## Specification documents (in-tree)

| Document | Contents |
|----------|----------|
| [README.md](../README.md) | System architecture |
| [RF-modules.md](../RF-modules.md) | RFIC, PCB, backplane, daemon responsibilities |
| [zeromq-messages.md](../zeromq-messages.md) | ZMQ endpoints and payloads |
| [docs/repeater-logic.md](repeater-logic.md) | Supervisor state machine, TX lease |
| [docs/ota-remote-control.md](ota-remote-control.md) | Signed OTA frames, audit log |
| [docs/implementation-language.md](implementation-language.md) | Rust vs GR vs SDRangel |
| [docs/adr/001-iq-transport-i2s-zmq.md](adr/001-iq-transport-i2s-zmq.md) | I2S + ZMQ production IQ path |
| [docs/runtime/](runtime/README.md) | Per-repo implementation contracts (no source here) |
| [docs/release-integrity.md](release-integrity.md) | SHA-256 + GPG detached signatures for release artifacts |

## Runtime repositories (to be created by implementers)

| Suggested name | Language | Status | Runtime spec |
|----------------|----------|--------|--------------|
| `ht-module-daemon` | **Rust** | Not created | [runtime/ht-module-daemon.md](runtime/ht-module-daemon.md) |
| `repeater-control` | **Rust** | Not created | [runtime/repeater-control.md](runtime/repeater-control.md) (`repeater-supervisord` + `repeater-authd`) |
| `gr-ht13g` | C++ / Python | Not created | [runtime/gr-ht13g.md](runtime/gr-ht13g.md) |
| `sdr-repeater-flowgraphs` | GNU Radio | Not created | [runtime/sdr-repeater-flowgraphs.md](runtime/sdr-repeater-flowgraphs.md) |
| `sdrangel` fork (org TBD) | C++ | Not created | [runtime/sdrangel-fork.md](runtime/sdrangel-fork.md) |

Record actual GitHub/Codeberg URLs in the **URL** column when repos exist:

| Suggested name | URL |
|----------------|-----|
| `ht-module-daemon` | *(pending)* |
| `repeater-control` | *(pending — supervisord + authd binaries)* |
| `gr-ht13g` | *(pending)* |
| `sdr-repeater-flowgraphs` | *(pending)* |
| `sdrangel` fork | *(pending)* |

## External dependencies (existing upstream)

| Project | Use |
|---------|-----|
| [f4exb/sdrangel](https://github.com/f4exb/sdrangel) | Fork base for TX/RX application |
| [Supermagnum/gr-ident](https://github.com/Supermagnum/gr-ident) | Mode identification |
| [Supermagnum/radio-modulation-validator](https://github.com/Supermagnum/radio-modulation-validator) | Validate GNU Radio OOT modulator blocks (IQ classification) |
| [Supermagnum/gr-linux-crypto](https://github.com/Supermagnum/gr-linux-crypto) | Signing alignment, operator keys |
| [M17-Project/LinHT-utils](https://github.com/M17-Project/LinHT-utils) | Reference ZMQ/ALSA bridge (`tests/zmq_proxy`) |
| GNU Radio 4.0 + gr-zeromq | Flowgraph IPC |

## Explicitly not used

| Project | Reason |
|---------|--------|
| Supermagnum/openrepeater | Unmaintained for this architecture |
| OpenRepeater (legacy BBB stack) | Superseded by SvxLink / SDR-native path per project decision |

## Optional adjuncts (not core)

| Project | Use |
|---------|-----|
| [sm0svx/svxlink](https://github.com/sm0svx/svxlink) | EchoLink / classic repeater linking |
| [AllStarLink/ASL3](https://github.com/AllStarLink/ASL3) | Asterisk linking |
| [g4klx/MMDVMHost](https://github.com/g4klx/MMDVMHost) | Digital hotspot hardware only |
