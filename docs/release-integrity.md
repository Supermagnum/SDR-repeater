# Release Artifact Integrity

**Revision:** 1.0  
**Date:** May 2026  

## Purpose

Provide a **minimal, reproducible** way for operators and developers to confirm that security-sensitive binaries and source archives (Rust daemons, GNU Radio OOT builds, SDRangel fork packages) have **not been altered** after the maintainer signed them. This complements over-the-air command signing in [ota-remote-control.md](ota-remote-control.md); it does not replace it.

Use **GPG detached signatures (ASCII-armored)** plus a **SHA-256 checksum**. Both work on **GitHub** and **Codeberg** release pages.

## What to sign

| Artifact type | Examples |
|---------------|----------|
| Release binaries | `ht-module-daemon`, `repeater-supervisord`, `repeater-authd` static or distro packages |
| Source archives | `.tar.xz` / `.zip` of tagged release trees |
| Firmware or bitstreams | Module images when distributed outside git |

Sign **the file users actually install**, not only a manifest, unless the manifest is the sole deliverable.

## Maintainer steps (publish on each release)

For each release file `file` (binary, archive, or image):

1. **Create SHA-256 checksum**

   `sha256sum file > file.sha256`

2. **Create an ASCII-armored detached GPG signature** of `file` (recommended), or of `file.sha256` if policy prefers signing the checksum only — document which you use on the release notes page.

   `gpg --armor --detach-sign file`

   This produces `file.asc`.

3. **Upload to the release page:** include all of:

   - `file` (original)
   - `file.asc` (detached signature)
   - `file.sha256` (checksum)

   GitHub and Codeberg allow users to download all three assets.

### Signing key

| Item | Guidance |
|------|----------|
| Key UID | Project or maintainer callsign / organisation name consistent with [ota-remote-control.md](ota-remote-control.md) key practices |
| Algorithm | Prefer Brainpool ECC or RSA-4096 where supported; match site policy for OTA keys when possible |
| Publication | Public key on project website, release notes, or `KEYS` / `docs/keys/` in the **runtime** repository that built the artifact |
| Subkeys | Use signing subkey with annual rotation documented in release notes |

## User verification

After downloading `file`, `file.asc`, and `file.sha256`:

1. **Import the project public key** (once per machine), then **verify the detached signature**

   `gpg --verify file.asc file`

   Expect `Good signature` from a trusted key.

2. **Verify the checksum**

   `sha256sum -c file.sha256`

   Expect `file: OK`.

If signature verification fails, **do not install** the artifact. If checksum fails but signature passes, treat the download as corrupted and re-download.

## Which repositories use this

Apply to **runtime** repositories listed in [runtime/README.md](runtime/README.md) and the SDRangel fork — any release that ships binaries or pre-built packages consumed at a repeater site.

| Repository | Typical signed artifacts |
|------------|-------------------------|
| `ht-module-daemon` | Release tarball, static binary |
| `repeater-control` | Release tarball, `repeater-supervisord`, `repeater-authd` binaries |
| `gr-ht13g` | Source tarball; optional installable package |
| `sdrangel` fork | `sdrsrv` build archive or distro package |
| `sdr-repeater-flowgraphs` | Source tarball only (optional) |

This **SDR-repeater** spec repository contains documentation only; signed releases apply when maintainers publish **downstream** build artifacts.

## CI and automation (optional)

Release workflows may run the same commands in CI after the artifact is built, using a protected signing key (token, HSM, or manual approval gate). The spec does not mandate a particular CI platform; GitHub Actions and Codeberg Actions both support uploading the three files to a release.

## Relation to OTA and audit

| Mechanism | Scope |
|-----------|--------|
| Release GPG + SHA-256 | **Distribution integrity** — artifact unchanged since maintainer release |
| [ota-remote-control.md](ota-remote-control.md) | **Operational commands** — who may change repeater settings over the air |
| Audit log | **Runtime history** — accepted/rejected commands at the site |

Operators need both trustworthy **install media** (this document) and trustworthy **command authority** (OTA spec) for a complete security story.

## Related documents

- [ota-remote-control.md](ota-remote-control.md)
- [implementation-language.md](implementation-language.md)
- [runtime/README.md](runtime/README.md)
- [CONTRIBUTING.md](../CONTRIBUTING.md)
