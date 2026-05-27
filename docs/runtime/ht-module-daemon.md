# Runtime Repository: `ht-module-daemon`

**Revision:** 1.0  
**Date:** May 2026  
**Language:** Rust  
**License:** GPL-3.0-or-later  

## Purpose

Long-running site service on the SpacemiT K3 that owns RF module hardware (SPI, I2C, GPIO, I2S/DMA), publishes RX IQ, consumes TX IQ, and serves the `ctrl` / `status` ZeroMQ planes defined in [zeromq-messages.md](../../zeromq-messages.md).

## Normative specifications (read-only links)

| Topic | Document |
|-------|----------|
| ZMQ sockets, IQ frame layout, `ctrl` commands | [zeromq-messages.md](../../zeromq-messages.md) Sections 2–5 |
| RFIC init, PTT order, EEPROM, I2S | [RF-modules.md](../../RF-modules.md) Sections 9–10 |
| IQ transport decision (I2S, not PCIe DMA) | [adr/001-iq-transport-i2s-zmq.md](../adr/001-iq-transport-i2s-zmq.md) |
| PTT policy (lease before keying) | [repeater-logic.md](../repeater-logic.md) — daemon enforces `ERR no_lease` when supervisor enabled |
| Bench reference bridge | [M17-Project/LinHT-utils](https://github.com/M17-Project/LinHT-utils) — study `tests/zmq_proxy/main.c` for ALSA↔ZMQ and PTT timing only; repeater endpoints use `/run/ht-module/` |

## Repository layout (expected)

| Path | Contents |
|------|----------|
| `Cargo.toml` | Workspace root; binary `ht-module-daemon` |
| `src/main.rs` | Process entry, signal handling, config load |
| `src/zmq/` | PUB `iq_*`, SUB `tx_*`, REP `ctrl`, PUB `status` |
| `src/iq/` | Frame pack/unpack per zeromq-messages Section 3 |
| `src/rfic/` | SPI register access, per-band state |
| `src/ptt/` | Hardware PTT sequence |
| `src/eeprom/` | Module identification and calibration load |
| `src/gnss/` | 1PPS GPIO, VCTCXO trim loop |
| `src/backends/` | Phase A stub, Phase B I2S/DMA, optional LinHT/SX1255 bench backend |
| `config/` | Example TOML: bands, socket paths, backend selector |
| `systemd/ht-module-daemon.service` | Unit file template |
| `README.md` | Build, run, link to this spec |

Optional: ship `repeater-supervisord` and `repeater-authd` in a sibling crate — see [repeater-control.md](repeater-control.md).

## Binaries

| Binary | Role |
|--------|------|
| `ht-module-daemon` | Production daemon |
| `ht-module-fake-iq` (optional) | Phase A: synthetic IQ publisher for contract tests without RF |

## Internal modules and responsibilities

### ZMQ plane (`src/zmq/`)

| Responsibility | Behaviour |
|----------------|-----------|
| Bind PUB | `ipc:///run/ht-module/iq_2m`, `iq_70cm`, `iq_23cm` |
| Bind REP | `ipc:///run/ht-module/ctrl` — one command per REQ/REP round-trip |
| Connect SUB | `tx_2m`, `tx_70cm`, `tx_23cm` — single logical publisher per band enforced at policy layer |
| Bind PUB | `ipc:///run/ht-module/status` — periodic JSON plus alert events |

Reference: ZeroMQ guide REQ/REP semantics; match reply strings `OK` and `ERR <reason>` from [zeromq-messages.md Section 4](../../zeromq-messages.md#4-control-plane-ctrl).

### IQ framing (`src/iq/`)

| Field | Source |
|-------|--------|
| `timestamp_ns` | CLOCK_REALTIME adjusted by chrony, or monotonic mapping documented in README |
| `band_id` | 0 / 1 / 2 per band |
| `sample_count` | Derived from DMA buffer fill |
| `iq[]` | int16 interleaved from SAI capture |

Reject malformed frames on TX SUB (wrong length, band mismatch).

### RFIC and SPI (`src/rfic/`)

| Task | RF-modules reference |
|------|---------------------|
| Reset and enumerate modules | Section 10.5, SPI Section 9.2 |
| Frequency program | `SET_FREQ` via PLL registers |
| Attenuator / gain | `SET_PWR`, AGC status for `status` JSON |
| IRQ handling | PLL unlock, AGC alerts → `status` alert JSON |

Phase B: mirror behaviours described for OpenHT-DB `ht13g-spi` CLI (not public); treat RF-modules register map as authoritative when available.

### PTT hardware (`src/ptt/`)

Enforce order from [RF-modules.md Section 10.5](../../RF-modules.md#105-ht-module-daemon-functions):

1. RFIC PTT assert  
2. T/R switch  
3. 1 ms delay  
4. PA enable  

Reverse order on unkey. Reject `PTT` if `repeater-supervisord` lease check fails when integration enabled.

### EEPROM (`src/eeprom/`)

Read layout [RF-modules.md Section 9.4](../../RF-modules.md) utility EEPROM map; populate calibration and module ID at startup.

### GNSS discipline (`src/gnss/`)

| Input | Action |
|-------|--------|
| 1PPS GPIO edge | Timestamp sample for VCTCXO trim |
| chrony-synchronised clock | IQ `timestamp_ns` domain |

### Backends (`src/backends/`)

| Backend ID | Phase | Description |
|------------|-------|-------------|
| `stub` | A | Timer-driven fake IQ; no SPI |
| `linht_proxy` | A | Optional wrapper around adapted LinHT zmq_proxy patterns |
| `sx1255` | A | Commodity 70 cm lab path per roadmap A5 |
| `i2s_dma` | B | Production SAI/DMA from kernel |

## Configuration

| Key (TOML) | Meaning |
|------------|---------|
| `backend` | `stub` \| `linht_proxy` \| `sx1255` \| `i2s_dma` |
| `bands.enabled` | List: `2m`, `70cm`, `23cm` |
| `zmq.ipc_prefix` | Default `/run/ht-module` |
| `status.interval_ms` | Default 1000 |
| `ptt.require_lease` | Default true in production |
| `supervisor.ctrl_check` | Optional REQ to supervisor before honouring PTT |

## systemd

| Unit | User | After |
|------|------|-------|
| `ht-module-daemon.service` | `ht-module` | `network.target`; creates `/run/ht-module` via `RuntimeDirectory` |

Hardening per [implementation-language.md](../implementation-language.md): `NoNewPrivileges`, `ProtectSystem=strict`, limited `ReadWritePaths`.

## Dependencies (crate-level guidance)

| Area | Suggested crates |
|------|------------------|
| ZMQ | `zmq` |
| JSON status | `serde`, `serde_json` |
| SPI | `spidev` |
| GPIO / 1PPS | `gpio-cdev` or `nix` |
| Logging | `tracing`, `tracing-subscriber` |
| Config | `toml` + `clap` |

## Acceptance tests (no code in spec repo)

| Test | Pass criterion |
|------|----------------|
| ZMQ IQ SUB | Frame size `16 + 4 * sample_count` for known `sample_count` |
| `ctrl` | `GET_STATUS all` returns `OK`; invalid band returns `ERR` |
| PTT | `PTT 70cm on` only after supervisor lease when enabled |
| PLL fault | Injected unlock forces `ptt: false` in `status` |
| Restart | Consumers reconnect; no stale PUB path |

## Deliverables by phase

| Phase | Milestone |
|-------|-----------|
| A | `stub` backend; all sockets live; RF-modules PTT sequence simulated or GPIO on bench |
| B | `i2s_dma` backend; three bands; EEPROM and VCTCXO loop |

## Release integrity

Tagged releases: publish `file`, `file.sha256`, and `file.asc` per [release-integrity.md](../release-integrity.md).

## Related runtime specs

- [repeater-control.md](repeater-control.md) — auth and supervisor  
- [gr-ht13g.md](gr-ht13g.md) — GNU Radio consumer  
- [sdrangel-fork.md](sdrangel-fork.md) — parallel consumer  
