# Runtime Repository: `repeater-control` (supervisor + authentication)

**Revision:** 1.0  
**Date:** May 2026  
**Language:** Rust  
**License:** GPL-3.0-or-later  

## Purpose

Hosts two production binaries (single repository recommended):

| Binary | Spec |
|--------|------|
| `repeater-supervisord` | [repeater-logic.md](../repeater-logic.md) |
| `repeater-authd` | [ota-remote-control.md](../ota-remote-control.md) |

Alternative: separate git repos `repeater-supervisord` and `repeater-authd` sharing a Rust workspace crate `repeater-control-common`.

## Normative specifications

| Binary | Document |
|--------|----------|
| `repeater-supervisord` | [repeater-logic.md](../repeater-logic.md) — TX lease, per-band FSM, cross-band policy |
| `repeater-authd` | [ota-remote-control.md](../ota-remote-control.md) — canonical payload, OTA frame, audit log |
| Shared `ctrl` vocabulary | [zeromq-messages.md Section 4](../../zeromq-messages.md#4-control-plane-ctrl) |
| Crypto alignment | [gr-linux-crypto](https://github.com/Supermagnum/gr-linux-crypto) — `CallsignKeyStore`, Brainpool profiles, Nitrokey operator workflow |

## Repository layout (expected)

| Path | Contents |
|------|----------|
| `crates/supervisor/` | `repeater-supervisord` binary |
| `crates/authd/` | `repeater-authd` binary |
| `crates/common/` | Shared ZMQ client to `ctrl`, config types, callsign parsing |
| `config/supervisor.toml` | Hang time, attack delay, lease TTL, band enables |
| `config/authd.toml` | Repeater callsign, trusted keyring path, elevation fingerprints |
| `config/policy.toml` | `local_ctrl_trust` default false |
| `systemd/repeater-supervisord.service` | |
| `systemd/repeater-authd.service` | After `ht-module-daemon` |

## `repeater-supervisord`

### Responsibilities

| Area | Behaviour |
|------|-----------|
| TX lease | At most one lease per band; see [repeater-logic.md Section 3](../repeater-logic.md#3-tx-lease-model) |
| State machine | Per-band `IDLE` … `DISABLED` per [Section 4](../repeater-logic.md#4-per-band-state-machine) |
| `ctrl` proxy | Only lease holder’s PTT commands forwarded to `ipc:///run/ht-module/ctrl` |
| COR integration | Optional ZMQ SUB on COR events from flowgraph, or poll `status` |
| ID / courtesy | Schedule `PLAY_ID` triggers to flowgraph message port (document IPC name in flowgraphs spec) |

### Suggested internal modules

| Module | Functions (names indicative) |
|--------|------------------------------|
| `lease_table` | `grant_lease`, `renew_lease`, `release_lease`, `holder_for_band` |
| `fsm` | `on_cor_active`, `on_cor_idle`, `transition`, `force_idle` |
| `ctrl_client` | Wrap ZMQ REQ to daemon — mirror semantics of zeromq REQ/REP |
| `config` | Load hang/attack/timeout overrides; extension commands until in zeromq-messages |

### IPC (implementer-defined, document in repo README)

| Endpoint | Pattern | Purpose |
|----------|---------|---------|
| `ipc:///run/repeater/supervisor` | REQ/REP | `LEASE PTT`, `RELEASE PTT`, `GET_STATE` |
| Optional PUB | `ipc:///run/repeater/supervisor_events` | FSM transitions for flowgraphs |

### Upstream references

| Project | Study |
|---------|--------|
| LinHT-utils | PTT timing discipline in `tests/zmq_proxy/main.c` (not endpoint-compatible) |
| SvxLink | Repeater controller concepts only — no code reuse required |

## `repeater-authd`

### Responsibilities

| Step | Reference |
|------|-----------|
| Receive OTA bytes | SUB or Unix datagram from GNU Radio sink — endpoint in flowgraphs spec |
| Parse frame | [ota-remote-control.md Section 6](../ota-remote-control.md#6-ota-wire-frame-logical) |
| Verify OpenPGP | Detached signature over canonical payload |
| Replay cache | Per-sender `TS` monotonicity and ±30 s window |
| Audit | Append JSON lines to `/var/log/repeater/audit.log` |
| Forward command | REQ to supervisor or `ctrl` per command class |

### Suggested internal modules

| Module | Functions (names indicative) |
|--------|------------------------------|
| `ota_parser` | `parse_frame`, `validate_magic`, `extract_payload` |
| `canonical` | `parse_canonical_lines`, `validate_callsign`, `extract_cmd` |
| `verify` | `verify_detached_signature`, `lookup_trust`, `check_elevation` |
| `replay` | `accept_timestamp`, `reject_reason` |
| `audit` | `log_accepted`, `log_rejected`, `rotate_daily` |
| `inject` | `forward_to_supervisor` |

### gr-linux-crypto alignment

| gr-linux-crypto concept | authd use |
|-------------------------|-----------|
| `CallsignKeyStore` | Index trusted operator keys by `FROM` callsign |
| Brainpool signing | Match verification policy in ota-remote-control Section 5 |
| Nitrokey | Operator-side only; authd never holds operator private keys |

GNU Radio may use gr-linux-crypto blocks for lab loopback; production trust decision stays in `repeater-authd`.

### IPC

| Endpoint | Pattern | Purpose |
|----------|---------|---------|
| `ipc:///run/repeater/ota_rx` | SUB or Unix dgram | Raw OTA frames from demod |
| `ipc:///run/ht-module/ctrl` | REQ | Only after supervisor approval for PTT-class commands |

## Interaction diagram

```
Flowgraph OTA sink -> repeater-authd -> repeater-supervisord -> ht-module-daemon (ctrl)
Flowgraph COR/lease  -> repeater-supervisord ----------------^
```

## systemd

| Unit | User | Requires |
|------|------|----------|
| `repeater-supervisord.service` | `repeater` | `ht-module-daemon.service` |
| `repeater-authd.service` | `repeater` | `repeater-supervisord.service` (ordering for policy) |

## Acceptance tests

| Test | Pass criterion |
|------|----------------|
| Lease | Second client denied lease on same band |
| OTA valid | Signed `SET_SQUELCH` changes daemon state; audit `ACCEPTED` |
| OTA replay | Duplicate `TS` → `REPLAY_DETECTED`, no `ctrl` |
| OTA wrong REPT | Frame ignored, no hardware change |
| PTT without lease | Daemon returns `ERR no_lease` |

## Deliverables by phase

| Phase | Milestone |
|-------|-----------|
| A | Supervisor stub + authd verify against loopback file-fed OTA frames |
| B | Live OTA from flowgraph; daily signed audit rotation |

## Release integrity

Security-sensitive binaries (`repeater-authd`, `repeater-supervisord`): sign all release artifacts per [release-integrity.md](../release-integrity.md).

## Related runtime specs

- [ht-module-daemon.md](ht-module-daemon.md)  
- [sdr-repeater-flowgraphs.md](sdr-repeater-flowgraphs.md) — OTA and COR publishers  
