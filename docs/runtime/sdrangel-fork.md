# Runtime Repository: SDRangel fork (organisation TBD)

**Revision:** 1.0  
**Date:** May 2026  
**Language:** C++ (Qt5)  
**Upstream:** [f4exb/sdrangel](https://github.com/f4exb/sdrangel) — **fork, do not reimplement TX/RX stack**  
**License:** GPL-3.0 (inherit upstream)  

## Purpose

Maintained fork of SDRangel for repeater site operation: headless `sdrsrv`, digital mode channel plugins, and a **custom sample source plugin** that consumes repeater ZMQ IQ from `ht-module-daemon`. TX/RX and mode decoding stay in SDRangel; hardware PTT and frequency commits go through `ctrl` + `repeater-supervisord` per [repeater-logic.md](../repeater-logic.md).

## Normative specifications

| Topic | Document |
|-------|----------|
| IQ frame layout | [zeromq-messages.md Section 3](../zeromq-messages.md#3-iq-data-plane) |
| Do not key PA from IQ alone | [zeromq-messages.md Section 4](../zeromq-messages.md#4-control-plane-ctrl) |
| System role of SDRangel | [README.md Section 7.3](../../README.md#73-user-friendly-frontends-gnu-radio-based-or-gnu-radio-compatible) |

## Fork policy

| Rule | Detail |
|------|--------|
| Track upstream | Regular merge from `f4exb/sdrangel` `master` |
| Repeater changes | Prefer plugin + preset + REST glue in fork; upstream generic fixes go upstream via PR |
| Naming | Suggest remote `github.com/<org>/sdrangel-repeater` or similar; record URL in [repo-map.md](../repo-map.md) |
| Builds | Match upstream CMake presets; add plugin via `plugins/samplesource/CMakeLists.txt` registration |

## Required fork deliverables

### 1. Sample source plugin: `samplesource/htzmq/` (name indicative)

New plugin directory parallel to existing sample sources (e.g. `remoteinput`, `localinput`, `fileinput`).

| Upstream pattern to follow | Location in f4exb/sdrangel |
|----------------------------|----------------------------|
| Plugin registration | `plugins/samplesource/<plugin>/` — `PluginInterface` implementation |
| Sample source factory | Class implementing `SampleSourcePluginInterface` — method `createSampleSourcePlugin` |
| Device instance | Subclass of `DeviceSampleSource` (see `sdrbase/devices/samplesource.h` or equivalent device sample source header) |
| Settings UI (GUI build) | Qt form under plugin folder; optional in server-only builds |
| Serialization | `*Settings::serialize` / `deserialize` for preset restore |

| Plugin class (indicative) | Responsibility |
|---------------------------|----------------|
| `HTZMQPlugin` | Register plugin metadata, version, id |
| `HTZMQInput` extends `DeviceSampleSource` | `start()`, `stop()`, pull samples into SDRangel DSP chain |
| `HTZMQWorker` or internal thread | ZMQ SUB connect to `ipc:///run/ht-module/iq_*`; parse repeater frame header |
| `HTZMQSettings` | Endpoints per band, `sample_rate`, `band_id`, scale int16→`Sample` type SDRangel uses |

| DeviceSampleSource method | Repeater use |
|---------------------------|--------------|
| `start` | Connect ZMQ SUB; subscribe topic if used |
| `stop` | Disconnect, join worker |
| `getSampleRate` | Return 500000 for repeater profile |
| `setDeviceCenterFrequency` | Forward to `ctrl` `SET_FREQ` via sidecar client, not fake tuning inside plugin only |

**Reference plugins to read in upstream tree:**

| Plugin | Why |
|--------|-----|
| `plugins/samplesource/remoteinput/` | Network IQ ingest pattern |
| `plugins/samplesource/fileinput/` | Timed sample push |
| `plugins/samplesource/localinput/` | Local device abstraction |

### 2. TX path policy

| Layer | Responsibility |
|-------|----------------|
| SDRangel channel TX chain | Modulation, audio, digital modes |
| Repeater ZMQ | Optional future `htzmq` sink plugin or continue using GNU Radio `ht13g_sink` for TX IQ |
| PTT | **Never** auto-key from sample source; invoke `ctrl` through supervisor |

If TX IQ via SDRangel is required later, add `plugins/samplesink/htzmq/` mirroring frame pack in [zeromq-messages Section 3](../zeromq-messages.md#3-iq-data-plane) — Phase B optional.

### 3. Headless server profile

| Target | Upstream reference |
|--------|-------------------|
| `sdrsrv` binary | `sdrsrv/` or `appsrv/` tree — server build without GUI |
| REST control | `swagger/` API — `MainSettings`, device set APIs |
| Remote web UI | [f4exb/sdrangelcli](https://github.com/f4exb/sdrangelcli) optional |

| Integration rule | Detail |
|------------------|--------|
| REST frequency change | Must call repeater `ctrl` or supervisor, not only SDRangel internal offset |
| Presets | Ship `settings/repeater-70cm.json` (name indicative) per band |

Study upstream class `MainCore` (or `DSPEngine`) for how device sets bind sample sources — exact header path in `sdrbase/maincore.h`.

### 4. Repeater channel presets

| Preset | Channels (indicative upstream plugin ids) |
|--------|---------------------------------------------|
| `repeater-70cm-fm` | NFM demod / FM mod channel plugins |
| `repeater-70cm-dmr` | DSD demod family if licensed/build flags allow |
| `repeater-m17` | `modemm17` plugin tree under `modemm17/` |

Document preset filenames in fork `README.md`; no preset blobs required in SDR-repeater spec repo.

### 5. Sidecar `ctrl` client (fork or separate tiny Rust binary)

| Option | Note |
|--------|------|
| Rust helper in `ht-module-daemon` repo | Reused by SDRangel via subprocess — discouraged |
| C++ `HTZMQCtrlClient` in plugin | REQ/REP to `ipc:///run/ht-module/ctrl` for `SET_FREQ`, lease-aware `PTT` |

Prefer REQ/REP client shared library linked only by `htzmq` plugin and documented in fork README.

## CMake / build flags

| Flag | Purpose |
|------|---------|
| `ENABLE_CHANNELSM17` | Match upstream defaults for M17 |
| New `ENABLE_SAMPLESOURCE_HTZMQ` | Gate repeater plugin |

Register in top-level `plugins/samplesource/CMakeLists.txt` same pattern as sibling plugins.

## RISC-V

Upstream reports BPI-F3 (SpacemiT K1) success. Repeater fork must CI-build `sdrsrv` for `riscv64` when K3 images are available.

## Acceptance criteria

| Test | Pass |
|------|------|
| Plugin loads in `sdrsrv` | Device set shows HTZMQ source |
| IQ | Waterfall/spectrum moves with Phase A stub daemon |
| PTT | Keying only after supervisor lease + `ctrl` |
| Upstream merge | Clean merge from `f4exb/sdrangel` within one release cycle |

## Deliverables by phase

| Phase | Milestone |
|-------|-----------|
| A | `htzmq` sample source; one band; `sdrsrv` preset |
| B | Multi device set (2m/70cm/23cm); REST documented with `ctrl` sidecar |
| C | Optional TX sink plugin |

## Related runtime specs

- [ht-module-daemon.md](ht-module-daemon.md)  
- [sdr-repeater-flowgraphs.md](sdr-repeater-flowgraphs.md) — may run in parallel on same ZMQ PUB  
- [repeater-control.md](repeater-control.md)  

## Ancillary upstream projects

| Project | Use |
|---------|-----|
| [f4exb/sdrangelcli](https://github.com/f4exb/sdrangelcli) | Web UI for headless instance |
| SDRangel-Docker | Optional packaging only |
