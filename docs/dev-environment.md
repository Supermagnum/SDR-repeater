# Developer Environment

**Revision:** 1.0  
**Date:** May 2026  

Setup guide for implementers working on **runtime repositories** linked from [repo-map.md](repo-map.md). Per-repo requirements are in [runtime/](runtime/README.md). This spec repo itself requires only a markdown editor and git.

## Target platform

| Item | Value |
|------|--------|
| OS | Ubuntu 26.04 LTS (RISC-V RVA23) or x86_64 for cross-development |
| CPU | SpacemiT K3 (production) or PC (Phase A bench) |
| GNU Radio | 4.0 RC or stable when available |
| SDRangel upstream | [f4exb/sdrangel](https://github.com/f4exb/sdrangel) `master` |

## Packages (Ubuntu 26.04)

Install on the development host or K3:

```bash
sudo apt update
sudo apt install -y \
  build-essential cmake pkg-config git \
  libzmq3-dev libzmq5 \
  gpsd chrony \
  gpg sequoia-chameleon-gnupg || true
```

Add GNU Radio 4.0, VOLK, and SDRangel build dependencies per upstream install guides when building those trees.

## Rust toolchain

Production daemons use **Rust** ([implementation-language.md](implementation-language.md)):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup default stable
```

Suggested components for runtime repos: `clippy`, `rustfmt`. Cross-compile to `riscv64gc-unknown-linux-gnu` when building on x86 for K3 deploy.

## Runtime directories

Created by systemd or installer scripts (not committed here):

| Path | Mode | Purpose |
|------|------|---------|
| `/run/ht-module/` | `0750` root:`ht-module` | ZMQ IPC sockets |
| `/run/repeater/` | `0750` root:`repeater` | Supervisor and OTA IPC |
| `/var/log/repeater/` | `0750` root:`repeater` | Audit logs |

## ZMQ smoke test (manual)

With a Phase A daemon binary (external repo):

1. Confirm socket `ipc:///run/ht-module/ctrl` answers `GET_STATUS all` with `OK` or structured reply per [zeromq-messages.md](../zeromq-messages.md).
2. SUB to `ipc:///run/ht-module/iq_70cm` and verify frame size `16 + sample_count * 4`.
3. SUB to `ipc:///run/ht-module/status` and parse JSON schema Section 5.

No test scripts are maintained in this repository.

## GNU Radio

- Flowgraphs live in **`sdr-repeater-flowgraphs`** (to be created) — see [runtime/sdr-repeater-flowgraphs.md](runtime/sdr-repeater-flowgraphs.md).
- Use `gr-zeromq` or `gr-ht13g` for IQ; gr-ident for preamble per [zeromq-messages.md Section 6](../zeromq-messages.md#6-gr-ident-integration).
- Point `ctrl` at the daemon; do not bypass supervisor in production tests without documenting `local_ctrl_trust`.

## SDRangel fork

- See [runtime/sdrangel-fork.md](runtime/sdrangel-fork.md).
- Build server flavour for headless repeater (`sdrsrv`).
- Plugin: ZMQ IQ sample source reading repeater frame layout Section 3.
- REST API changes go upstream or in fork README; PTT still via `ctrl` + supervisor.

## Security keys

- Generate operator keys with standard `gpg` or gr-linux-crypto workflows; **never** commit private keys.
- Repeater public key distributed to operators for reply verification.

## References

- [roadmap.md](roadmap.md)
- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [adr/001-iq-transport-i2s-zmq.md](adr/001-iq-transport-i2s-zmq.md)
