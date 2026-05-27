# Contributing to SDR Repeater

This repository holds **system design and wire-format specifications** only. Application source code (daemons, GNU Radio OOT modules, SDRangel plugins) lives in separate repositories listed in [docs/repo-map.md](docs/repo-map.md).

## What belongs here

- Architecture and integration updates in `README.md`
- RF module and backplane specification in `RF-modules.md`
- ZeroMQ wire formats in `zeromq-messages.md`
- Developer specs under `docs/` (repeater logic, OTA control, ADRs, roadmap)
- Runtime repository contracts under `docs/runtime/` (what each external git repo must implement)

## What does not belong here

- Implementation source code (no Rust/C++/Python modules in this repo)
- Generated binaries, keys, or credentials
- Vendor-specific calibration blobs unless redistributable under project licenses

## Implementation language

Security-sensitive and hardware-adjacent runtime components are specified for **Rust**. See [docs/implementation-language.md](docs/implementation-language.md).

Signal processing may use **GNU Radio 4.0** (C++/Python flowgraphs) and **SDRangel** (C++ plugins) as documented in the README.

## Before you open a change

1. Read [docs/repo-map.md](docs/repo-map.md) so the edit targets the correct repository.
2. If you change ZMQ layouts or `ctrl` commands, update **both** [zeromq-messages.md](zeromq-messages.md) and any affected `docs/*.md` in the same pull request.
3. If you change IQ transport assumptions, check [docs/adr/001-iq-transport-i2s-zmq.md](docs/adr/001-iq-transport-i2s-zmq.md).

## Release artifacts (runtime repositories)

Binaries and release archives published from runtime repos should include **SHA-256 checksums** and **ASCII-armored detached GPG signatures** on GitHub or Codeberg releases. Procedure and user verification steps: [docs/release-integrity.md](docs/release-integrity.md).

## Pull request expectations

- One logical topic per PR (spec fix, new ADR, OTA field addition).
- Use complete sentences in commit messages; reference issue numbers when applicable.
- Do not commit operator private keys, Nitrokey dumps, or production `audit.log` excerpts with real callsigns unless anonymised.

## Code repositories (external)

Implementation work is tracked in runtime repos once created; this spec repo links to them from [docs/repo-map.md](docs/repo-map.md). Propose new repo names in an issue before duplicating functionality.

## Questions

Open a GitHub issue with labels `spec`, `hardware`, `zmq`, `ota`, or `sdrangel` as appropriate. For RFIC tapeout and PCB, tag `hardware`. For command-line and socket contracts, tag `zmq`.
