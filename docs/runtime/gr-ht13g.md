# Runtime Repository: `gr-ht13g`

**Revision:** 1.0  
**Date:** May 2026  
**Language:** C++ (GNU Radio OOT), optional Python bindings  
**License:** GPL-3.0-or-later  

## Purpose

GNU Radio 4 out-of-tree module that connects flowgraphs to the repeater native ZMQ plane: int16 framed IQ on `iq_*` / `tx_*`, and optional `ctrl` REQ helper. Specified in [zeromq-messages.md](../../zeromq-messages.md) Sections 3–4 and 8.

## Normative specifications

| Topic | Document |
|-------|----------|
| IQ frame layout | [zeromq-messages.md Section 3](../../zeromq-messages.md#3-iq-data-plane) |
| `ctrl` commands | [zeromq-messages.md Section 4](../../zeromq-messages.md#4-control-plane-ctrl) |
| Flowgraph examples | [zeromq-messages.md Section 8](../../zeromq-messages.md#8-repeater-flowgraph-wiring) |
| PTT / lease | [repeater-logic.md](../repeater-logic.md) — flowgraphs must hold lease before `ht13g_ctrl` sends `PTT` |
| gr-ident adapter note | [zeromq-messages.md Section 3.4](../../zeromq-messages.md#34-gr-ident-iq-note) |

## Repository layout (expected)

| Path | Contents |
|------|----------|
| `CMakeLists.txt` | OOT build against GNU Radio 4 |
| `include/gnuradio/ht13g/` | Public headers |
| `lib/ht13g_source_impl.cc` | RX ZMQ SUB → `gr_complex` stream |
| `lib/ht13g_sink_impl.cc` | `gr_complex` → ZMQ PUB to `tx_*` |
| `lib/ht13g_ctrl.cc` | Optional message or sync block for `ctrl` REQ |
| `python/ht13g/bindings/` | PyBind11 if Python entry points required |
| `grc/` | Companion `.block.yml` for GNU Radio Companion |
| `examples/` | Pointer filenames only — graph descriptions in [sdr-repeater-flowgraphs](sdr-repeater-flowgraphs.md) repo |
| `README.md` | Install, depend on `libzmq`, link to spec |

## Blocks to implement

### `ht13g_source`

| Property | Value |
|----------|-------|
| GR base class | `gr::sync_block` or `gr::block` with `general_work` |
| Input ports | None |
| Output | `out` — `gr_complex` (one stream) |
| Parameters | `endpoint` (string), `band_id` (int), `sample_rate` (default 500000) |

| Method / function (indicative) | Role |
|------------------------------|------|
| `work` / `general_work` | Pull ZMQ message, parse header, emit `sample_count` output items |
| `parse_frame` | Validate length vs `sample_count`; map `band_id` |
| `int16_to_complex` | Scale int16 to float (gain configurable message) |

**Reference implementations to study (upstream GNU Radio):**

| Upstream | Path / symbol |
|----------|----------------|
| gr-zeromq SUB source | `gr::zeromq::sub_msg_source` — message framing patterns |
| VOLK | `volk_16i_s32f_convert_32f` or project-specific scale |

Connect SUB to `ipc:///run/ht-module/iq_B` (etc.) per module address.

### `ht13g_sink`

| Property | Value |
|----------|-------|
| GR base class | `gr::sync_block` |
| Input | `in` — `gr_complex` |
| Output ports | None |
| Parameters | `endpoint`, `band_id`, `sample_rate` |

| Method (indicative) | Role |
|---------------------|------|
| `work` | Accumulate samples; pack int16 frame with `timestamp_ns` |
| `publish_frame` | ZMQ PUB one message per frame policy (match daemon chunk size) |

**Reference:** `gr::zeromq::pub_msg_sink` for PUB discipline.

Sink does **not** key PTT; companion `ht13g_ctrl` or supervisor drives `PTT on`.

### `ht13g_ctrl` (optional block)

| Property | Value |
|----------|-------|
| Type | `gr::block` with message ports or Python-only helper |
| Role | REQ/REP to `ipc:///run/ht-module/ctrl` |

| Message / API (indicative) | Maps to |
|----------------------------|---------|
| `set_freq` | `SET_FREQ <band> <Hz>` |
| `ptt_on` / `ptt_off` | `PTT <band> on\|off` — only if supervisor lease held |
| `set_squelch` | `SET_SQUELCH <band> <dBm>` |

Prefer thin wrapper: one REQ per command, block until `OK` or log `ERR`.

## Build dependencies

| Dependency | Minimum |
|------------|---------|
| GNU Radio | 4.0 |
| libzmq | 4.x |
| CMake | 3.16+ |
| VOLK | 3.x (optional optimisation) |

## GRC integration

| Block name | GRC file |
|------------|----------|
| HT13G Source | `grc/ht13g_ht13g_source.block.yml` |
| HT13G Sink | `grc/ht13g_ht13g_sink.block.yml` |
| HT13G Ctrl | `grc/ht13g_ht13g_ctrl.block.yml` |

Parameters exposed: endpoint, module address dropdown (`A` / `B` / `C` / `D`), sample rate.

## Interaction with gr-ident

| Approach | Blocks |
|----------|--------|
| Native repeater IQ | `ht13g_source` → detect chain |
| gr-ident distributed IQ | Separate adapter block (not in gr-ht13g): int16 framed → `complex<float>` PUSH — see [zeromq-messages Section 6.3](../../zeromq-messages.md#63-distributed-iq-push--pull) |

gr-ident blocks to reference by name from upstream:

| gr-ident block (upstream) | Role |
|---------------------------|------|
| `PreambleResultZmqPub` | Publish decode JSON |
| `ZmqTxControlSub` | PTT gating for preamble insert |
| `PreambleOnPtt` | Key-down burst policy |

## Interaction with gr-linux-crypto

Use gr-linux-crypto in **flowgraphs** for modem-side signing tests. Production OTA verification remains in `repeater-authd` per [repeater-control.md](repeater-control.md).

## Acceptance criteria

| Test | Pass |
|------|------|
| Source connected to Phase A stub daemon | Continuous `complex` stream at 500 kSa/s equivalent |
| Sink | Daemon receives valid frame length for configured `sample_count` |
| Ctrl | `SET_FREQ B 433000000` returns OK at daemon |
| Lease | `ptt_on` without lease fails at supervisor, not silent TX |

## Deliverables by phase

| Phase | Deliverable |
|-------|-------------|
| A | `ht13g_source` + `ht13g_sink` for one band |
| B | Three endpoints; `ht13g_ctrl`; GRC blocks |

## Related runtime specs

- [ht-module-daemon.md](ht-module-daemon.md)  
- [sdr-repeater-flowgraphs.md](sdr-repeater-flowgraphs.md)  
- [sdrangel-fork.md](sdrangel-fork.md) — parallel IQ consumer, no gr-ht13g dependency  
