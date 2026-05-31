# Over-the-Air Remote Control

**Revision:** 1.0  
**Date:** May 2026  
**Status:** Normative specification (implementation in `repeater-authd`, Rust)

Companion to [README.md Section 8](../README.md#8-authenticated-remote-control) and [zeromq-messages.md Section 4](../zeromq-messages.md#4-control-plane-ctrl).

## 1. Purpose

Replace legacy DTMF remote control with **cryptographically signed** command frames. Any receiver can read frame contents (not encrypted by default); only the repeater whose callsign matches the target field and whose keyring trusts the sender may execute the command.

Local operators use the same command text on `ipc:///run/ht-module/ctrl` without a signature. Remote operators use RF transport plus verification in **`repeater-authd`**.

## 2. Components

| Process | Language | Role |
|---------|----------|------|
| `repeater-authd` | Rust | Verify signatures, replay check, audit log, inject to `ctrl` |
| GNU Radio demod | C++/Python | Deliver raw **OTA frame bytes** to authd (Unix socket or ZMQ) |
| `ht-module-daemon` | Rust | Execute validated `ctrl` commands on hardware |
| `repeater-supervisord` | Rust | Policy gate for PTT and `REBOOT` (see [repeater-logic.md](repeater-logic.md)) |

## 3. Command vocabulary

Command text is **identical** to [zeromq-messages.md Section 4.3](../zeromq-messages.md#43-command-reference). Examples:

- `SET_SQUELCH B -120`
- `PTT B on`
- `GET_STATUS all`
- `REBOOT` (elevated; see Section 7)

Maximum command line length: **256 UTF-8 bytes** (excluding trailing newline in canonical form).

## 4. Canonical payload (signed body)

Before OpenPGP signing, the sender builds a **canonical UTF-8 string** (Unix line endings `\n` only):

```
REPT=<target_callsign>
FROM=<sender_callsign>
TS=<utc_unix_ns>
CMD=<command line>
```

Rules:

- `target_callsign` and `sender_callsign`: uppercase amateur callsign, no SSID in baseline spec (extensions may add `CALL-ssid` in a future revision).
- `utc_unix_ns`: unsigned integer, nanoseconds since Unix epoch, from a clock synchronised within **30 s** of the repeater GNSS clock.
- `CMD`: single line, no embedded `\n`.
- Fields are fixed order; extra fields are forbidden in v1.

**Example:**

```
REPT=LA1XYZ
FROM=LA1ABC
TS=1717000000123456789
CMD=SET_SQUELCH B -120
```

## 5. OpenPGP signature

| Property | Value |
|----------|-------|
| Format | OpenPGP v4 detached signature over the canonical payload bytes (UTF-8) |
| Hash | SHA-256 or stronger (sender key preference) |
| Public-key algorithm | Brainpool ECC or RSA-4096 per site policy; **Brainpool preferred** to align with [gr-linux-crypto](https://github.com/Supermagnum/gr-linux-crypto) |
| Key UID | Sender callsign (e.g. `LA1ABC`) |
| Private key storage | Nitrokey or kernel keyring via gr-linux-crypto operator workflow |

Verification uses the repeater's **trusted keyring** (Web of Trust). Unknown or untrusted keys yield `KEY_NOT_FOUND` in the audit log.

## 6. OTA wire frame (logical)

Demodulator delivers one binary blob per received command frame:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 | `magic` | `0x52 0x43` (`RC`) |
| 2 | 1 | `version` | `0x01` |
| 3 | 2 | `payload_len` | `uint16` LE, length of canonical payload |
| 5 | `payload_len` | `payload` | Canonical string (Section 4) |
| 5+N | 2 | `sig_len` | `uint16` LE, detached signature length |
| 7+N | `sig_len` | `signature` | OpenPGP detached signature bytes |

Maximum frame size: **4096 bytes** (reject larger at authd).

**RF encapsulation** (which modem, baud, FEC) is a deployment profile — not fixed in v1. The repeater site document must state the active profile (e.g. narrowband FM data channel at 1200 baud, or digital mode pipe). authd only sees bytes after the demod chain.

## 7. Verification algorithm (`repeater-authd`)

1. Parse frame; reject on bad `magic`, `version`, or oversize.
2. Parse canonical payload; validate callsign charset and `CMD` syntax.
3. Verify `REPT` equals this repeater's configured callsign (case-insensitive compare, store uppercase).
4. Verify detached OpenPGP signature over `payload` with sender key from `FROM`.
5. **Replay check:** for each `FROM` key, reject if `TS` is not strictly greater than the last accepted `TS` for that sender, or if `|TS - repeater_now_ns| > 30 s`.
6. **Trust policy:** accept if key is in trusted keyring (signed by repeater or trusted operator per README Section 8.5).
7. **Elevation:** `REBOOT` and `MOD_DISABLE all` require key marked `elevated` in local policy file (TOML/JSON list of fingerprints) in addition to WoT.
8. On success: append audit record; send `CMD` line to `repeater-supervisord` or directly to `ctrl` per command class.
9. On failure: append rejected audit record; do not touch hardware.

## 8. Replies and status broadcasts

The repeater may transmit **signed status** using the same canonical format with `CMD=STATUS_JSON` and a JSON body in a fifth field extension in v1.1; baseline v1 uses separate periodic beacons:

```
REPT=<target>
FROM=<repeater_callsign>
TS=<utc_unix_ns>
CMD=STATUS
BODY=<utf-8 json minified>
```

`BODY` is not part of the four-line canonical form in Section 4; v1.1 will unify schema. Until then, status over RF is optional and site-defined.

## 9. Audit log

Path: `/var/log/repeater/audit.log`

Each line: one JSON object, append-only.

**Accepted example:**

```json
{
  "utc_ns": 1717000000999999999,
  "sender": "LA1ABC",
  "sender_fpr": "ABCD1234...",
  "target": "LA1XYZ",
  "cmd": "SET_SQUELCH B -120",
  "prev": "-130",
  "new": "-120",
  "result": "ACCEPTED",
  "transport": "ota"
}
```

**Rejected example:**

```json
{
  "utc_ns": 1717000000888888888,
  "sender": "LA1ABC",
  "target": "LA1XYZ",
  "cmd": "PTT B on",
  "result": "REJECTED",
  "reason": "REPLAY_DETECTED",
  "transport": "ota"
}
```

Daily rotation: new file `audit.log.YYYYMMDD`; previous file signed with repeater OpenPGP key (detached `.sig`).

## 10. Integration with GNU Radio

1. Flowgraph outputs **OTA frame bytes** on a dedicated sink (e.g. ZMQ PUB `ipc:///run/repeater/ota_rx` or Unix datagram socket).
2. `repeater-authd` SUBscribes, verifies, and REQ/REP to `ipc:///run/ht-module/ctrl` only after supervisor approval for PTT-related commands.
3. gr-linux-crypto blocks may be used **inside GR** for lab tests; production path should still centralise policy in authd.

## 11. Local control bypass

Connections to `ctrl` from `127.0.0.1` or group `ht-module` Unix peer credentials may bypass OTA signatures **only if** site policy `local_ctrl_trust = unix_peer` is enabled. Default for production sites: **disabled**; all control via authd or physical front-panel service menu.

## 12. Release artifact integrity

Distribution of `repeater-authd`, `ht-module-daemon`, and other installable builds is covered separately: [release-integrity.md](release-integrity.md) (SHA-256 + detached GPG on GitHub/Codeberg releases). OTA frame signing and release signing use the same Web of Trust keyring practices where practical.

## 13. Related documents

- [repeater-logic.md](repeater-logic.md) — PTT and supervisor interaction
- [implementation-language.md](implementation-language.md) — Rust components
- [zeromq-messages.md](../zeromq-messages.md) — `ctrl` command reference
