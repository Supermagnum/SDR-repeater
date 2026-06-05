# Repeater Logic and Supervision

**Revision:** 1.0  
**Date:** May 2026  
**Status:** Normative specification (implementation in `repeater-supervisord`, Rust)

Defines behaviour between demodulators, **`repeater-supervisord`**, **`ht-module-daemon`**, and ZMQ consumers. Wire formats remain in [zeromq-messages.md](zeromq-messages.md).

## 1. Goals

- One **TX owner** per band at a time (no duplicate PTT from GNU Radio and SDRangel).
- Deterministic **hang time**, **timeout**, and **ID** behaviour.
- Clear split: **signal processing** (GNU Radio / SDRangel) vs **hardware policy** (Rust daemons).

## 2. Processes and ownership

| Concern | Owner |
|---------|--------|
| RX IQ publish, TX IQ consume, SPI/PTT hardware | `ht-module-daemon` |
| Squelch threshold, AGC readout, PLL alerts | `ht-module-daemon` + `status` JSON |
| COR / VOX / digital squelch (optional) | GNU Radio or SDRangel channel |
| "Should we transmit now?" | `repeater-supervisord` |
| OTA command trust | `repeater-authd` |
| Demod / remod / cross-band audio | GNU Radio flowgraph and/or SDRangel |

## 3. TX lease model

Before any process may key a band:

1. Client requests lease: `LEASE PTT <band> <client_id> <ttl_ms>` on `ipc:///run/repeater/supervisor` (REQ/REP, spec mirror of `ctrl`; implementers define exact socket in runtime repo).
2. Supervisor grants at most **one active lease per band**.
3. Only the lease holder may send `PTT <band> on` to `ctrl` (daemon rejects others with `ERR no_lease`).
4. Lease expires after `ttl_ms` or explicit `RELEASE PTT <band> <client_id>`.
5. **Default TTL:** 500 ms; renewed by holder while TX audio is active (heartbeat every 200 ms).

**Priority (higher wins on conflict):**

1. `REBOOT` / emergency `MOD_DISABLE` (authd, elevated)
2. Manual `ctrl` from trusted local peer (if enabled)
3. OTA verified command (authd)
4. Repeater supervisor auto-repeat path (COR-driven)
5. SDRangel REST (only if wired to supervisor; never direct to daemon in production)

## 4. Per-band state machine

States: `IDLE`, `RX_ACTIVE`, `TX_ARMED`, `TX_ON`, `TX_HANG`, `DISABLED`.

```
                    MOD_DISABLE
        +--------------------------------------+
        v                                      |
     DISABLED <---------------- MOD_ENABLE ----+
        |
        v
      IDLE ----(COR open / squelch broken)----> RX_ACTIVE
        ^                                            |
        |                                            | (COR closed + hang expired)
        |                                            v
        +-------- TX_HANG <---- TX_ON <---- TX_ARMED
                      ^            |            ^
                      |            |            |
                      +------------+------------+
                           (timeout / PTT off)
```

| Transition | Condition | Actions |
|------------|-----------|---------|
| IDLE -> RX_ACTIVE | COR active or digital carrier detected | Publish `status.ptt=false`; optional gr-ident detect |
| RX_ACTIVE -> TX_ARMED | COR still active; repeat enabled; lease granted | Allocate lease; modulator may buffer |
| TX_ARMED -> TX_ON | Hang delay elapsed (default **300 ms**); `PTT band on` OK | Daemon keys PA sequence |
| TX_ON -> TX_HANG | COR dropped or max TX time reached | `PTT band off`; start hang timer |
| TX_HANG -> IDLE | Hang time elapsed (default **800 ms**) | Release lease |
| * -> DISABLED | `MOD_DISABLE` | Force `PTT off`; reject new leases |

**Parameters** (per module, stored in daemon, set via `ctrl`):

| Parameter | Default | `ctrl` command |
|-----------|---------|----------------|
| Hang time | 800 ms | `SET_HANG B 800` (extension; until implemented use supervisor config file) |
| Attack delay | 300 ms | `SET_ATTACK B 300` (extension) |
| TX timeout | 300 s | `SET_TX_TIMEOUT B 300` |
| Squelch | site-specific | `SET_SQUELCH B -120` |

Document extension commands in zeromq-messages when implemented; until then supervisor reads TOML.

## 5. Cross-band repeat

Example: module A (2 m) RX -> module B (70 cm) TX.

- Two modules, **two independent** state machines.
- RX module stays in `RX_ACTIVE` or `IDLE`; TX module follows `TX_ARMED`/`TX_ON` when audio is present on cross-band bus.
- Supervisor ensures **never** both modules key the same PA path (not applicable on separate modules).
- `ctrl`: `PTT A off` always during module B TX unless full-duplex cross-band profile enabled in site config.

## 6. Identification and courtesy tone

| Event | Behaviour |
|-------|-----------|
| Every 10 minutes (configurable) | Supervisor triggers `PLAY_ID` on audio injection path (GNU Radio or WAV via ZMQ sidechain) |
| After TX_HANG | Optional courtesy tone (configurable length 100–500 ms) |
| During foreign `REPT` OTA | No ID; audit only |

ID audio is **not** sent on `tx_*` IQ unless the flowgraph explicitly maps it; preferred path: GR message port or ALSA sidechain on bench only.

## 7. Interaction with gr-ident

When gr-ident preamble is enabled:

1. On COR rise, detect chain may emit preamble on TX (gr-ident `PTT` / `PreambleOnPtt` profile).
2. Mode router selects demod from `grident` JSON ([zeromq-messages.md Section 6](zeromq-messages.md#6-gr-ident-integration)).
3. Encrypted preamble with no key: remain in `RX_ACTIVE`, no audio to speaker chain; no repeat.

## 8. `tx_*` ZMQ rules

- Publishing IQ to `tx_*` **without** lease and `PTT on` is allowed for buffering but daemon **must not** key PA.
- Daemon drops TX IQ frames if PLL unlocked or `DISABLED`.
- Multiple SUB publishers to same `tx_*`: **forbidden**; only one connected PUB per band (ZMQ convention: last connect wins — supervisor enforces single publisher via lease).

## 9. Failure modes

| Failure | Response |
|---------|----------|
| PLL unlock (`status.alert`) | Force `PTT off`; state -> IDLE |
| Daemon restart | Supervisor releases all leases; consumers reconnect SUB |
| authd down | OTA ignored; local `ctrl` per site policy |
| GR flowgraph stall | TX timeout fires -> `PTT off` |

## 10. Related documents

- [ota-remote-control.md](ota-remote-control.md)
- [implementation-language.md](implementation-language.md)
- [zeromq-messages.md](zeromq-messages.md) Section 8 (flowgraph examples)
