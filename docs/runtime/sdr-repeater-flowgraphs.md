# Runtime Repository: `sdr-repeater-flowgraphs`

**Revision:** 1.0  
**Date:** May 2026  
**Language:** GNU Radio 4 flowgraphs (`.grc` and/or YAML flowgraph), optional Python runners  
**License:** GPL-3.0-or-later  

## Purpose

Version-controlled GNU Radio 4 flowgraphs for repeater signal paths: analog FM repeat, gr-ident mode routing, OTA control byte delivery to `repeater-authd`, and cross-band examples from [zeromq-messages.md Section 8](../zeromq-messages.md#8-repeater-flowgraph-wiring). **No daemon or kernel code** — depends on [gr-ht13g](gr-ht13g.md), [ht-module-daemon](ht-module-daemon.md), and [repeater-control](repeater-control.md).

## Normative specifications

| Topic | Document |
|-------|----------|
| Wiring diagrams | [zeromq-messages.md Section 8](../zeromq-messages.md#8-repeater-flowgraph-wiring) |
| gr-ident ZMQ | [gr-ident docs/zeromq-protocol.md](https://github.com/Supermagnum/gr-ident/blob/main/docs/zeromq-protocol.md) |
| OTA bytes to authd | [ota-remote-control.md](../ota-remote-control.md) |
| Lease before PTT | [repeater-logic.md](../repeater-logic.md) |

## Repository layout (expected)

| Path | Contents |
|------|----------|
| `flowgraphs/70cm_fm_repeater.grc` | Phase A single-band analog repeat |
| `flowgraphs/70cm_fm_repeater_ident.grc` | gr-ident mode router |
| `flowgraphs/crossband_2m_70cm.grc` | 2 m RX → 70 cm TX |
| `flowgraphs/ota_loopback.grc` | Lab: emit OTA frames to `ipc:///run/repeater/ota_rx` |
| `flowgraphs/README.md` | Per-graph prerequisites and run order |
| `scripts/run_graph.sh` | Optional launcher — document only, implementation in runtime repo |
| `config/graph.toml` | Endpoints, callsigns, module addresses |
| `README.md` | Depends: GNU Radio 4, gr-ht13g, gr-ident, gr-linux-crypto |

## Dependency repositories (must be installed)

| Module | Repository |
|--------|------------|
| `gr-ht13g` | [gr-ht13g.md](gr-ht13g.md) — `ht13g_source`, `ht13g_sink`, `ht13g_ctrl` |
| `gr-ident` | [Supermagnum/gr-ident](https://github.com/Supermagnum/gr-ident) |
| `gr-linux-crypto` | [Supermagnum/gr-linux-crypto](https://github.com/Supermagnum/gr-linux-crypto) — lab signing |
| `gr-zeromq` | GNU Radio upstream — only if not using gr-ht13g for a path |

## Flowgraph catalogue

### `70cm_fm_repeater` (Phase A exit graph)

| Stage | Block (indicative) | Notes |
|-------|-------------------|-------|
| IQ in | `ht13g_source` | endpoint `ipc:///run/ht-module/iq_B` (module B; typically 70 cm) |
| Channel filter | `fir_filter_fff` or `freq_xlating_fir_filter` | 12.5 kHz NFM chain |
| Demod | `analog.fm_demod_cf` | Audio stream |
| Squelch / COR | `analog.simple_squelch_cc` or custom power detector | Drives supervisor COR messages or internal repeat gate |
| Resample / mod | `analog.fm_mod_cf` | TX audio |
| IQ out | `ht13g_sink` | endpoint `ipc:///run/ht-module/tx_B` |
| PTT | `ht13g_ctrl` or message to supervisor | Lease acquired before key-down |

**GNU Radio API references:** `gr::analog::fm_demod_cf`, `gr::analog::fm_mod_cf`, `gr::blocks::multiply_const_cc` for AGC.

### `70cm_fm_repeater_ident`

Extends FM repeater:

| Stage | Block (upstream gr-ident) | ZMQ |
|-------|---------------------------|-----|
| Detect | CPFSK/Golay chain per gr-ident README | — |
| Publish decode | `PreambleResultZmqPub` | PUB `tcp://127.0.0.1:5560` topic `grident` |
| Mode router | Custom `gr::block` or Python hub SUB `grident` | Switches demod branch |
| Preamble on key | `PreambleOnPtt`, `ZmqTxControlSub` | See gr-ident zeromq-protocol |

Demod branches (indicative): NFM (`mode_id` 20), C4FM path when `digital` true — registry in gr-ident docs.

### `crossband_2m_70cm`

| Leg | Blocks |
|-----|--------|
| RX | `ht13g_source` on `iq_A` → demod → audio |
| TX | audio → mod → `ht13g_sink` on `tx_B` |
| PTT | Supervisor coordinates `PTT A off` / `PTT B on` per [repeater-logic Section 5](../repeater-logic.md#5-cross-band-repeat) |

### `ota_loopback`

| Stage | Role |
|-------|------|
| File or message source | Payload bytes matching [ota-remote-control Section 6](../ota-remote-control.md#6-ota-wire-frame-logical) |
| Sink | Publish to `ipc:///run/repeater/ota_rx` for `repeater-authd` SUB |
| Optional signed path | gr-linux-crypto signing blocks for operator key tests |

Production over-the-air profile (baud, mode) is **site config** in graph README, not fixed here.

## Message and IPC endpoints (document in each graph README)

| Endpoint | Producer | Consumer |
|----------|----------|----------|
| `ipc:///run/ht-module/iq_*` | ht-module-daemon | `ht13g_source` |
| `ipc:///run/ht-module/tx_*` | `ht13g_sink` | ht-module-daemon |
| `ipc:///run/repeater/supervisor` | flowgraph lease client | repeater-supervisord |
| `ipc:///run/repeater/ota_rx` | OTA sink block | repeater-authd |
| `tcp://127.0.0.1:5560` | `PreambleResultZmqPub` | mode router SUB |

## Operating procedure (document in repo README)

| Step | Service |
|------|---------|
| 1 | `ht-module-daemon` (stub or hardware backend) |
| 2 | `repeater-supervisord` |
| 3 | `repeater-authd` if OTA testing |
| 4 | `gnuradio-companion` or `grcc` / flowgraph runner for selected `.grc` |
| 5 | Optional `sdrsrv` in parallel — separate IQ consumer |

## COR → supervisor bridge

Flowgraph should document one integration choice:

| Option | Mechanism |
|--------|-----------|
| A | Periodic message to `ipc:///run/repeater/supervisor` with COR state |
| B | Poll `status` JSON via external helper — not recommended inside GR real-time path |

Indicative supervisor API messages: `COR B active`, `COR B idle` — exact strings defined in `repeater-control` runtime README and mirrored in supervisor spec.

## Testing matrix

| Graph | Preconditions | Expected outcome |
|-------|---------------|------------------|
| `70cm_fm_repeater` | stub IQ + COS from file | Audio repeated; PTT cycles via supervisor |
| `70cm_fm_repeater_ident` | gr-ident preamble injected | Router selects NFM vs digital branch |
| `ota_loopback` | authd running | Audit `ACCEPTED` for valid signed frame |
| `crossband_2m_70cm` | two band stubs | TX only on 70 cm during 2 m activity |

## Deliverables by phase

| Phase | Graphs |
|-------|--------|
| A | `70cm_fm_repeater`, `ota_loopback` |
| B | `70cm_fm_repeater_ident`, `crossband_2m_70cm`, per-site OTA profile README |

## Related runtime specs

- [gr-ht13g.md](gr-ht13g.md)  
- [ht-module-daemon.md](ht-module-daemon.md)  
- [repeater-control.md](repeater-control.md)  
- [sdrangel-fork.md](sdrangel-fork.md) — optional parallel, not a substitute for repeat DSP  
