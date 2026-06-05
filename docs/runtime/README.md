# Runtime Repository Specifications

**Revision:** 1.0  
**Date:** May 2026  

Normative requirements for **implementation repositories** (source code lives outside this spec tree). Each document is the contract a new git repository must satisfy before it is linked from [repo-map.md](../repo-map.md).

| Repository spec | Language | Primary spec links |
|-----------------|----------|-------------------|
| [ht-module-daemon.md](ht-module-daemon.md) | Rust | [zeromq-messages.md](../zeromq-messages.md), [RF-modules.md](../RF-modules.md) Section 10 |
| [repeater-control.md](repeater-control.md) | Rust | [repeater-logic.md](../repeater-logic.md), [ota-remote-control.md](../ota-remote-control.md) |
| [gr-ht13g.md](gr-ht13g.md) | C++ / Python | [zeromq-messages.md](../zeromq-messages.md) Sections 3–4 |
| [sdrangel-fork.md](sdrangel-fork.md) | C++ | [zeromq-messages.md](../zeromq-messages.md) Section 3, upstream [f4exb/sdrangel](https://github.com/f4exb/sdrangel) |
| [sdr-repeater-flowgraphs.md](sdr-repeater-flowgraphs.md) | GNU Radio 4 | [zeromq-messages.md](../zeromq-messages.md) Section 8, [gr-ident](https://github.com/Supermagnum/gr-ident) |

## Creation order

See [roadmap.md](../roadmap.md). Typical sequence: `ht-module-daemon` stub, `repeater-control`, `gr-ht13g`, `sdr-repeater-flowgraphs`, then `sdrangel` fork plugin.

## When a repo is created

1. Initialise git with license **GPL-3.0-or-later** (runtime) unless counsel advises otherwise.
2. Add a root `README.md` pointing back to this spec repo and the matching `docs/runtime/*.md` file.
3. Update [repo-map.md](../repo-map.md) **URL** column with the real remote.

## Release signing

Published binaries and release tarballs from runtime repositories must ship with SHA-256 checksums and ASCII-armored detached GPG signatures. See [release-integrity.md](../release-integrity.md).

## Out of scope in runtime repos

- Duplicating wire-format tables (link to `zeromq-messages.md` instead).
- OpenRepeater / Supermagnum openrepeater code paths.
- Committed private keys or site-specific `audit.log` samples with real callsigns.
