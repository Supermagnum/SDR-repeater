# Implementation Language Policy

**Status:** Accepted  
**Date:** May 2026  

## Summary

| Component class | Language | Rationale |
|-----------------|----------|-----------|
| Module daemon (`ht-module-daemon`) | **Rust** | Memory safety for 24/7 site service; SPI/I2C/GPIO; ZMQ IQ and `ctrl`; PTT sequencing |
| OTA verify and audit (`repeater-authd`) | **Rust** | Cryptographic verification, replay cache, append-only audit I/O |
| Repeater supervisor (`repeater-supervisord`) | **Rust** | PTT arbitration, repeater state machine, single TX owner |
| GNU Radio flowgraphs and OOT | C++ / Python | Ecosystem standard; `gr-ht13g`, gr-ident, gr-linux-crypto bridges |
| SDRangel device/channel plugins | C++ | Upstream [f4exb/sdrangel](https://github.com/f4exb/sdrangel) convention |
| Kernel I2S/DMA driver (if used) | C | Linux kernel requirement |
| Thin lab scripts (fake IQ, tests) | Python | Optional; not production path |

## Rust scope (normative)

The following **must** be implemented in Rust in production deployments:

1. **`ht-module-daemon`** — RFIC init, DMA/I2S IQ pack/unpack, ZMQ PUB/SUB/REP per [zeromq-messages.md](zeromq-messages.md), hardware PTT order, VCTCXO trim from 1PPS, `status` JSON publisher.
2. **`repeater-authd`** — OpenPGP / Brainpool verification per [ota-remote-control.md](ota-remote-control.md); replay suppression; mapping verified commands to `ctrl` REQ; audit log writes.
3. **`repeater-supervisord`** — Logic in [repeater-logic.md](repeater-logic.md); grants TX lease; forwards allowed PTT to daemon; refuses conflicting `tx_*` consumers.

Rust binaries should run under **systemd** with hardening (`NoNewPrivileges`, `ProtectSystem`, restricted filesystem namespaces) and separate Unix users where practical (`ht-module`, `repeater-auth`).

## GNU Radio and SDRangel

- **GNU Radio** performs demodulation, mode routing (gr-ident), and optional over-the-air **frame extraction** (bytes out of modem).
- **`repeater-authd`** performs trust decisions; flowgraphs must not apply `ctrl` commands without a verified path from authd or local operator policy.
- **SDRangel** may consume ZMQ IQ via a sample-source plugin; PTT and frequency changes go through `ctrl`, not REST alone, unless REST is wired to the same supervisor policy.

## Inter-process boundaries

```
GNU Radio / SDRangel  --IQ-->  ZMQ iq_* / tx_*  <--  ht-module-daemon (Rust)
                                    ^
                                    | ctrl REP
                    repeater-supervisord (Rust) --lease-->
                                    ^
                                    | verified command
                         repeater-authd (Rust) <-- OTA bytes from GR demod
```

## Dependencies (guidance for implementers)

Rust crates (suggested, not mandated by this spec repo): `zeromq`, `serde`/`serde_json`, `nix` or `gpio-cdev`, `spidev`, `tracing`, `thiserror`. For OpenPGP: `sequoia-openpgp` or controlled `gpgme` bindings; align with [gr-linux-crypto](https://github.com/Supermagnum/gr-linux-crypto) key UIDs and Brainpool profiles.

## Runtime repository specs

Per-repo layout, acceptance tests, and upstream API pointers (no source in spec tree):
[docs/runtime/README.md](runtime/README.md).

## Licensing

Rust runtime repositories should use **GPL-3.0-or-later** to match SDRangel and GNU Radio linkage expectations unless counsel advises otherwise. This documentation remains **CC-BY-SA 4.0**.
