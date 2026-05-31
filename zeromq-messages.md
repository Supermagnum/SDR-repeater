# ZeroMQ Message Reference — SDR Repeater

**Revision:** 1.0  
**Date:** May 2026  

This document is the canonical wire-format reference for ZeroMQ on the SDR multiband repeater.
Hardware integration and daemon responsibilities are also summarised in
[RF-modules.md](RF-modules.md) Section 10.

Mode-identification traffic follows **[gr-ident](https://github.com/Supermagnum/gr-ident)** conventions
(documented upstream in
[gr-ident/docs/zeromq-protocol.md](https://github.com/Supermagnum/gr-ident/blob/main/docs/zeromq-protocol.md)).
This file records how those messages integrate with the repeater stack.

---

## Table of Contents

1. [Protocol families](#1-protocol-families)
2. [Repeater native (`ht-module-daemon`)](#2-repeater-native-ht-module-daemon)
3. [IQ data plane](#3-iq-data-plane)
4. [Control plane (`ctrl`)](#4-control-plane-ctrl)
5. [Telemetry (`status`)](#5-telemetry-status)
6. [gr-ident integration](#6-gr-ident-integration)
7. [LinHT compatibility (Linht handheld)](#7-linht-compatibility-linht-handheld)
8. [Repeater flowgraph wiring](#8-repeater-flowgraph-wiring)
9. [Compatibility matrix](#9-compatibility-matrix)
10. [Related documents](#10-related-documents)

---

## 1. Protocol families

Three independent ZeroMQ conventions may coexist on the K3. They use **different sockets,
patterns, and payloads** — do not mix them on the same endpoint.

| Family | Role on repeater | Default transport | Primary spec |
|--------|------------------|-------------------|--------------|
| **Repeater native** | IQ, hardware control, site telemetry | `ipc:///run/ht-module/...` | This document, [Section 2](#2-repeater-native-ht-module-daemon) |
| **gr-ident** | Preamble decode results, lab/distributed PTT, optional distributed IQ | `tcp://127.0.0.1:...` (typical on K3) | [gr-ident zeromq-protocol.md](https://github.com/Supermagnum/gr-ident/blob/main/docs/zeromq-protocol.md) |
| **LinHT** | Linht GUI / M17 baseband proxy (handheld) | `ipc:///tmp/...` | LinHT-utils, [Section 7](#7-linht-compatibility-linht-handheld) |

The repeater **`ht-module-daemon`** implements the native family only. A GNU Radio flowgraph
adds gr-ident blocks (or bridges) when automatic mode identification is enabled.

---

## 2. Repeater native (`ht-module-daemon`)

> **Implementation:** [`ht-module-daemon`](docs/repo-map.md) in **Rust** (not shipped in this spec repo). Companion processes: [`repeater-supervisord`](docs/repeater-logic.md), [`repeater-authd`](docs/ota-remote-control.md).

### 2.1 Data flow

```
RFIC (I2S) -> DMA -> ring buffer
                         |
                         v
              ht-module-daemon (Rust)
              |  pack IQ / unpack TX
              |  GPIO/SPI (PTT, attenuator, VCTCXO)
              v
        ZMQ PUB/SUB/REQ/REP under ipc:///run/ht-module/
                         |
         +---------------+---------------+
         v               v               v
   GNU Radio        SDRangel         recorder
   (gr-ht13g)       (plugin)         (ZMQ SUB)
```

### 2.2 Socket layout

All paths below use the `ipc://` scheme. The daemon **binds** PUB sockets; consumers
**connect** SUB sockets. The daemon **binds** REP on `ctrl`; clients **connect** REQ.

| Endpoint | Pattern | Binder | Direction | Payload |
|----------|---------|--------|-----------|---------|
| `ipc:///run/ht-module/iq_A` | PUB | daemon | RX IQ -> consumers | Binary IQ frame ([Section 3](#3-iq-data-plane)) |
| `ipc:///run/ht-module/iq_B` | PUB | daemon | RX IQ -> consumers | Binary IQ frame |
| `ipc:///run/ht-module/iq_C` | PUB | daemon | RX IQ -> consumers | Binary IQ frame |
| `ipc:///run/ht-module/iq_D` | PUB | daemon | RX IQ -> consumers | Binary IQ frame |
| `ipc:///run/ht-module/tx_A` | SUB | daemon | consumers -> TX IQ | Binary IQ frame |
| `ipc:///run/ht-module/tx_B` | SUB | daemon | consumers -> TX IQ | Binary IQ frame |
| `ipc:///run/ht-module/tx_C` | SUB | daemon | consumers -> TX IQ | Binary IQ frame |
| `ipc:///run/ht-module/tx_D` | SUB | daemon | consumers -> TX IQ | Binary IQ frame |
| `ipc:///run/ht-module/ctrl` | REQ/REP | daemon (REP) | client <-> daemon | ASCII command / reply ([Section 4](#4-control-plane-ctrl)) |
| `ipc:///run/ht-module/status` | PUB | daemon | telemetry -> consumers | UTF-8 JSON ([Section 5](#5-telemetry-status)) |

**Remote IQ:** change `ipc:///run/ht-module/iq_B` to `tcp://0.0.0.0:<port>` on the
daemon and matching connect address on subscribers. Frame layout is unchanged.

Only **populated** slots have sockets; empty slots have no `iq_*` / `tx_*` endpoints.

### 2.3 Daemon responsibilities

- Initialise RFICs over SPI; read module EEPROM and temperature sensors over I2C
- Publish RX IQ from DMA ring buffers; consume TX IQ into SAI DMA
- Execute hardware PTT sequence on `ctrl` commands: RFIC PTT -> T/R switch -> 1 ms delay -> PA enable
- Apply frequency, gain, squelch, TX timeout, and attenuator settings **per module address**
- Discipline VCTCXO trim from GNSS 1PPS
- Publish `status` JSON on a fixed interval and on alerts (PLL unlock, AGC events)

---

## 3. IQ data plane

### 3.1 Rules

- One ZMQ message = one IQ frame (not a continuous byte stream without headers).
- Sample rate: **500 kSa/s** per module (500 kHz IQ bandwidth).
- Sample format: **int16** interleaved **I, Q, I, Q, ...**, little-endian.
- Publishing on `iq_*` does not imply the transmitter is keyed; see [Section 4](#4-control-plane-ctrl).

### 3.2 RX / TX binary frame layout

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 8 | `timestamp_ns` | `uint64` LE | GNSS-disciplined UTC-related time (nanoseconds) |
| 8 | 4 | `module_id` | `uint32` LE | `0` = A, `1` = B, `2` = C, `3` = D |
| 12 | 4 | `sample_count` | `uint32` LE | Number of **complex** samples (pairs) in this message |
| 16 | `sample_count * 4` | `iq[]` | int16[I], int16[Q] ... | Interleaved I/Q |

**Total message size:** `16 + sample_count * 4` bytes.

**Example:** `sample_count = 1024` -> 4112 bytes per message.

### 3.3 `gr-ht13g` conversion

GNU Radio flowgraphs normally use `complex<float>`. The OOT module **`gr-ht13g`** scales
between daemon int16 frames and GR streams:

- `ht13g_source` — SUB on `iq_*`, output `complex float`
- `ht13g_sink` — input `complex float`, PUB to `tx_*`

### 3.4 gr-ident IQ note

gr-ident distributed blocks (`ZmqPushSink` / `ZmqPullSource`) use **raw binary**
`complex<float>` on PUSH/PULL with **no** repeater header. To run gr-ident detection on
repeater IQ, insert a format adapter (int16 framed -> complex float) or a dedicated
detect flowgraph subscribed to `iq_*`.

LinHT baseband (`ipc:///tmp/bsb_rx`) uses **int32** interleaved I/Q, 8192 bytes per
message — not wire-compatible with repeater frames without conversion
(see [Section 7](#7-linht-compatibility-linht-handheld)).

---

## 4. Control plane (`ctrl`)

### 4.1 Transport

| Property | Value |
|----------|-------|
| Socket | REQ (client) / REP (daemon) |
| Address | `ipc:///run/ht-module/ctrl` |
| Request | **Single ZMQ frame**, UTF-8 / ASCII, one command line |
| Reply | **Single ZMQ frame**: `OK` or `ERR <reason>` |

The control plane is **separate** from IQ sockets. Sending IQ to `tx_*` does not key the
transmitter; issue `PTT B on` on `ctrl` as well.

Over-the-air remote control uses the **same command text** inside signed frames
([README.md Section 8](README.md#8-authenticated-remote-control)); only the transport
differs (RF + GnuPG vs local ZMQ).

### 4.2 Module addresses

Each backplane slot has a fixed **module address** (letter). The address identifies the
physical module, not its band. Two modules in slots B and C can both be 70 cm hardware;
commands and IQ sockets still use **`B`** and **`C`** individually.

| Address | Backplane slot |
|---------|----------------|
| `A` | Slot A |
| `B` | Slot B |
| `C` | Slot C |
| `D` | Slot D |
| `all` | Every populated slot (only where noted) |

The module's band (`2m`, `70cm`, `23cm`, …) is read from EEPROM at startup and reported
in `status` JSON. It is **not** used as a command target — band names alone are ambiguous
when more than one module shares a band.

Commands that configure RF parameters **require** a module address. Global commands omit it.

### 4.3 Command reference

Syntax: `COMMAND <module> <arguments...>` unless global.

| Command | Example | Effect |
|---------|---------|--------|
| `SET_SQUELCH` | `SET_SQUELCH B -120` | Squelch threshold (dBm) on module B |
| `SET_SQUELCH` | `SET_SQUELCH C -120` | Squelch on module C (e.g. second 70 cm link) |
| `SET_TX_TIMEOUT` | `SET_TX_TIMEOUT A 300` | Auto PTT off after 300 s on module A |
| `SET_TX_TIMEOUT` | `SET_TX_TIMEOUT B 300` | Auto PTT off on module B |
| `SET_FREQ` | `SET_FREQ D 1252000000` | Centre frequency (Hz) on module D |
| `SET_PWR` | `SET_PWR A 5` | RF output power (watts) on module A |
| `PTT` | `PTT B on` | Key transmitter on module B |
| `PTT` | `PTT B off` | Unkey transmitter on module B |
| `MOD_ENABLE` | `MOD_ENABLE A` | Enable module A |
| `MOD_DISABLE` | `MOD_DISABLE C` | Disable module C |
| `GET_TEMP` | `GET_TEMP all` | Query temperature sensors |
| `GET_STATUS` | `GET_STATUS B` | Status for module B |
| `GET_STATUS` | `GET_STATUS all` | Full status report |
| `GET_BATTERY` | `GET_BATTERY` | Battery state (global) |
| `REBOOT` | `REBOOT` | Graceful reboot (global, elevated trust OTA) |

Squelch and TX timeout are always **per module**; there is no implicit global target.

### 4.4 Example REQ/REP exchange (illustrative)

Reference client logic only; not maintained in this repository.

```python
import zmq

ctx = zmq.Context()
req = ctx.socket(zmq.REQ)
req.connect("ipc:///run/ht-module/ctrl")

req.send_string("SET_SQUELCH B -120")
print(req.recv_string())  # OK

req.send_string("PTT B on")
print(req.recv_string())  # OK

req.send_string("PTT B off")
print(req.recv_string())  # OK
```

---

## 5. Telemetry (`status`)

### 5.1 Transport

| Property | Value |
|----------|-------|
| Socket | PUB (daemon) / SUB (consumers) |
| Address | `ipc:///run/ht-module/status` |
| Payload | One UTF-8 JSON object per message (single frame) |

### 5.2 JSON schema (periodic update)

```json
{
  "module": "B",
  "band": "70cm",
  "timestamp_ns": 1717000000123456789,
  "rssi_dbm": -95.5,
  "agc_gain_db": 12.0,
  "pll_lock": true,
  "temp_c": 42.1,
  "ptt": false,
  "tx_timeout_remaining_s": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `module` | string | Module address: `A`, `B`, `C`, or `D` |
| `band` | string | Band type from module EEPROM: `2m`, `70cm`, `23cm`, … |
| `timestamp_ns` | integer | Same clock domain as IQ frames |
| `rssi_dbm` | number | Estimated RSSI |
| `agc_gain_db` | number | AGC setting |
| `pll_lock` | boolean | Synthesizer locked |
| `temp_c` | number | Module temperature |
| `ptt` | boolean | Transmitter keyed |
| `tx_timeout_remaining_s` | integer | Seconds until auto PTT off (0 if inactive) |

### 5.3 Alert messages

On PLL unlock or AGC threshold crossing, the daemon may publish:

```json
{
  "module": "A",
  "band": "2m",
  "timestamp_ns": 1717000000999999999,
  "alert": "pll_unlock"
}
```

Allowed `alert` values: `pll_unlock`, `pll_lock`, `agc_high`, `agc_low`.

---

## 6. gr-ident integration

gr-ident adds **mode identification** before demodulation. On the repeater, a detect
flowgraph consumes IQ (from `iq_*` or an internal GR source), publishes decode results
on a gr-ident PUB socket, and a **mode router** switches demodulators — compatible with
[gr-linux-crypto](https://github.com/Supermagnum/gr-linux-crypto) when the encrypted
flag is set.

Upstream reference:
[gr-ident/docs/zeromq-protocol.md](https://github.com/Supermagnum/gr-ident/blob/main/docs/zeromq-protocol.md).

### 6.1 Preamble decode results (PUB / SUB)

Used after Golay preamble decode on the receive path.

| Parameter | Default (gr-ident) | Repeater suggestion |
|-----------|-------------------|---------------------|
| Socket | PUB | PUB on detect flowgraph |
| Endpoint | `tcp://127.0.0.1:5560` | `tcp://127.0.0.1:5560` or `ipc:///run/ht-module/grident` |
| Topic (frame 0) | `grident` | `grident`, `grident.A` … `grident.D`, or `grident.70cm` when unambiguous |
| Body (frame 1) | UTF-8 JSON | Same |

**JSON body schema:**

```json
{
  "mode_id": 20,
  "digital": false,
  "encrypted": false,
  "metadata_present": false
}
```

| Field | Meaning |
|-------|---------|
| `mode_id` | 9-bit mode ID (0-511); see [gr-ident README](https://github.com/Supermagnum/gr-ident/blob/main/README.md#mode-id-table) |
| `digital` | Bit 11: route to digital demod bank |
| `encrypted` | Bit 10: payload needs gr-linux-crypto before demod |
| `metadata_present` | Bit 9: secondary metadata codeword follows on air |

**Subscriber actions (repeater mode router):**

1. Parse JSON from ZMQ multipart `[topic, body]`.
2. If `encrypted == true`, obtain keys via gr-linux-crypto before payload FEC.
3. Map `mode_id` to demodulator (e.g. `20` -> NFM 12.5 kHz analog; `104` -> C4FM; experimental IDs in
   [experimental-mode-registry.md](https://github.com/Supermagnum/gr-ident/blob/main/docs/experimental-mode-registry.md)).
4. If mode is unknown or analog/digital mismatch, do not pass noise to audio.

**Example subscriber:**

```python
import json
import zmq

ctx = zmq.Context()
sub = ctx.socket(zmq.SUB)
sub.connect("tcp://127.0.0.1:5560")
sub.setsockopt_string(zmq.SUBSCRIBE, "grident")

topic, payload = sub.recv_multipart()
result = json.loads(payload.decode())

if result["encrypted"]:
    # gr-linux-crypto key retrieval before demod
    pass

if result["mode_id"] == 20 and not result["digital"]:
    route = "nfm_125_analog"
elif result["mode_id"] == 104 and result["digital"]:
    route = "c4fm"
else:
    route = "unknown"
```

Sync sequences and air-interface profiles for detection are defined in
[gr-ident/docs/sync-sequences.md](https://github.com/Supermagnum/gr-ident/blob/main/docs/sync-sequences.md)
and the gr-ident modulation registry — not repeated here.

### 6.2 TX / PTT control (`profile=grident`)

For lab or TCP-based co-process flowgraphs (not the hardware daemon `ctrl` socket).

| Parameter | Value |
|----------|-------|
| Socket | SUB (receiver) / PUB (sender) |
| Endpoint | `tcp://127.0.0.1:5561` |
| Topic | `grident.tx` (multipart frame 0) |
| Body | UTF-8 JSON or plain text (frame 1) |

**Accepted body payloads (TX on):** `PTT_ON`, `TX`, `KEYDOWN`, `1`, `ON`, `SOT`, `{"ptt": true}`

**Accepted body payloads (TX off):** `PTT_OFF`, `RX`, `KEYUP`, `0`, `OFF`, `EOT`, `{"ptt": false}`

On the repeater, **hardware PTT** should still use `ctrl` (`PTT B on`). Use gr-ident
PTT to gate `PreambleOnPtt` inside GNU Radio when inserting mode-ident bursts on key-down.

### 6.3 Distributed IQ (PUSH / PULL)

Optional split-process development path; not used by `ht-module-daemon`.

| Parameter | PUSH (sender) | PULL (receiver) |
|----------|---------------|-----------------|
| Endpoint | `tcp://127.0.0.1:5555` | `tcp://127.0.0.1:5555` |
| Payload | Raw `sizeof(T) * N` bytes, no header | Same |

Supported types in gr-ident include `std::complex<float>`. Connect a PUSH bridge from
`ht13g_source` output only if you add framing — native repeater IQ uses [Section 3](#3-iq-data-plane).

### 6.4 Worked example: mode 20 (NFM) on repeater 70 cm

1. `ht-module-daemon` publishes IQ on `ipc:///run/ht-module/iq_B` (module B, 70 cm in a typical install).
2. Detect flowgraph: `ht13g_source` -> CPFSK/Golay detect -> `PreambleResultZmqPub` on `tcp://*:5560`.
3. Mode router receives `{"mode_id":20,"digital":false,"encrypted":false,"metadata_present":false}`.
4. Router enables NFM 12.5 kHz demod on the same IQ stream; ignores C4FM if `digital` were true on a mismatch.

### 6.5 Worked example: mode 300 (Sleipnir, experimental)

Registry:
[experimental-mode-registry.md](https://github.com/Supermagnum/gr-ident/blob/main/docs/experimental-mode-registry.md)
— mode ID **300**, digital, demod via gr-sleipnir after preamble.

Typical ZMQ body:

```json
{"mode_id":300,"digital":true,"encrypted":false,"metadata_present":false}
```

CPFSK detect profile for mode 300 may require a future gr-ident registry entry; the ZMQ
JSON is still valid for routing once the preamble is decoded.

---

## 7. LinHT compatibility (Linht handheld)

**Linht** uses the LinHT/M17 ZeroMQ paths under `/tmp/`. The repeater uses `/run/ht-module/`.
They are **not** the same endpoints; a bridge process is required for shared tooling.

| Endpoint | Pattern | Payload | Repeater compatible |
|----------|---------|---------|---------------------|
| `ipc:///tmp/ptt_msg` | PUB/SUB | LinHT PMT `SOT`/`EOT` ([gr-ident doc](https://github.com/Supermagnum/gr-ident/blob/main/docs/zeromq-protocol.md#linht-pmt-string-wire-format)) | PTT only, via `ZmqTxControlSub profile=linht` |
| `ipc:///tmp/bsb_rx` | PUB/SUB | int32 I/Q, 8192 B/msg | No — adapter to repeater frame or `complex<float>` |
| `ipc:///tmp/bsb_tx` | SUB/PUB | int32 I/Q, 8192 B/msg | No |
| `ipc:///tmp/fg_aux_data_in` | PUB/SUB | PMT (SOT/EOT, SMS, ...) | PTT/aux only; gr-ident does not parse SMS |
| `ipc:///tmp/fg_aux_data_out` | PUB/SUB | M17 decoded PMT | No — not gr-ident JSON |

gr-ident **PTT** parsing accepts LinHT PMT when `profile=linht`. Repeater hardware PTT
remains on `ipc:///run/ht-module/ctrl`.

---

## 8. Repeater flowgraph wiring

### 8.1 Single-band FM repeater with gr-ident

```
iq_B (ZMQ SUB; module B, typically 70 cm) -> ht13g_source -> detect chain -> PreambleResultZmqPub (tcp://*:5560)
                              \-> mode router SUB (grident) -> NFM / C4FM / ... demods
tx_B <- ht13g_sink <- modulator <- audio
ctrl REQ: SET_FREQ B ..., SET_SQUELCH B ..., PTT B on/off
```

### 8.2 Cross-band repeat (module A -> module B)

Example: 2 m in slot A, 70 cm in slot B.

```
iq_A -> demod -> re-encode -> tx_B
ctrl: PTT A off/on as needed; PTT B on only during TX burst
Per-module T/R timing handled in daemon
```

### 8.3 Process summary

| Process | Sockets used |
|---------|----------------|
| `ht-module-daemon` (Rust) | Binds `iq_*`, `status`, `ctrl` REP; connects `tx_*` SUB |
| `repeater-supervisord` (Rust) | REQ `ctrl` (lease holder); policy per [docs/repeater-logic.md](docs/repeater-logic.md) |
| `repeater-authd` (Rust) | OTA bytes in; verified commands to supervisor/`ctrl` per [docs/ota-remote-control.md](docs/ota-remote-control.md) |
| GNU Radio repeater | SUB `iq_*`, PUB `tx_*` (with lease), optional SUB `grident` |
| gr-ident detect (optional) | SUB IQ, PUB `tcp://127.0.0.1:5560` |
| OpenWebRX+ / recorder | SUB `iq_*` only |

---

## 9. Compatibility matrix

| Channel | Repeater native | gr-ident | LinHT |
|---------|-----------------|----------|-------|
| RX IQ | int16 framed, `iq_*` | PUSH/PULL `complex<float>` or adapted | int32 8192 B, `bsb_rx` |
| TX IQ | int16 framed, `tx_*` | PUSH/PULL | int32, `bsb_tx` |
| Hardware PTT | `ctrl` ASCII | — | — |
| GR preamble gating | — | `grident.tx` or LinHT PMT | `ptt_msg`, `fg_aux_data_in` |
| Mode ID to router | — | JSON `tcp://127.0.0.1:5560` | — |
| Site telemetry | JSON `status` | — | — |

---

## 10. Related documents

| Document | Content |
|----------|---------|
| [README.md](README.md) | System overview; [Section 7.5](README.md#75-zeromq-ipc) summary |
| [RF-modules.md](RF-modules.md) | RFIC, backplane, daemon context (Section 10) |
| [docs/repo-map.md](docs/repo-map.md) | Where runtime code lives |
| [docs/runtime/README.md](docs/runtime/README.md) | Per-repository implementation specs |
| [docs/repeater-logic.md](docs/repeater-logic.md) | Supervisor and PTT lease |
| [docs/ota-remote-control.md](docs/ota-remote-control.md) | Signed OTA frames |
| [docs/implementation-language.md](docs/implementation-language.md) | Rust policy |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to change specs |
| [gr-ident README](https://github.com/Supermagnum/gr-ident/blob/main/README.md) | Preamble specification, mode ID table |
| [gr-ident zeromq-protocol.md](https://github.com/Supermagnum/gr-ident/blob/main/docs/zeromq-protocol.md) | Full gr-ident and LinHT wire formats |
| [gr-ident sync-sequences.md](https://github.com/Supermagnum/gr-ident/blob/main/docs/sync-sequences.md) | Normative sync bit patterns |
| [gr-ident experimental-mode-registry.md](https://github.com/Supermagnum/gr-ident/blob/main/docs/experimental-mode-registry.md) | Mode IDs 300-498 |

---

## License

This document is part of the SDR-repeater project documentation. gr-ident upstream
files are licensed per the gr-ident repository (AGPL-3.0).
