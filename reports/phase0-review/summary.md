# Phase 0 review

Date: 2026-10-17. Scope: toolchain pin, LinHT host re-read, and one inductor EM baseline. No schematic, RTL, or layout of this RFIC was started. No fabrication, shuttle, or upstream pull request was opened.

## What was done

- Confirmed this repository had no earlier tool lock.
- Queried the live GitHub, Codeberg, PyPI, Docker Hub, SourceForge, and LinHT pages listed in the session prompt.
- Started `hpretl/iic-osic-tools:2026.10` and read the PDK commit shipped in that image.
- Ran `SG13_Octagon_L2n0` in Palace and openEMS. Numbers and caveats: `reports/phase0-review/em-l2n0.md`.
- Recorded supply, reference, and I2S decisions in `spec/baseline-decisions.md` and `decisions.md`.

## Pins

- Container `hpretl/iic-osic-tools:2026.10`, local image `sha256:306585de35d198e70ea58950f77147c86f56c698726a19afea9f1c83009557be`.
- PDK `a49358cc0b20635fcb53c0940505e3563763fc7a` from that image. It includes RF MOSFET LVS pull request 1246 and is 26 hours before `dev` `89d42ee`. The histories have diverged: 43 commits are only on `dev`, and 48 are only in the image. `89d42ee` is not pinned.
- DRC flag `--minimum_drc`.
- EM workflows `gds2palace` `v0.8.2` and `gds2openEMS` `v0.5.0`. Stack-up XML only from the pinned PDK. cocotb 2.1.0 is in the image. No project venv.
- Rejected: `efabless/cace`, `AliSahafi/Analog_OpenSource_ihp`, QUCS-COPEN. ngspice 47 PSS may be used; phase-noise results stay lower confidence.

## Key result

At 2.4 GHz, Palace reports 1.642 nH and Q 14.2. openEMS reports 1.631 nH and Q 11.8. At 3.5 GHz, Palace reports 1.658 nH and Q 18.8. openEMS reports 1.641 nH and Q 14.9. Inductance agrees to about 1%. Q differs by 20% and 26%. The meshes, the frequency methods, and the stack-up files are not the same, so that Q gap is not a pure solver comparison. Full figures are in `reports/phase0-review/em-l2n0.md`.

The host was rebooted during the first openEMS attempt. systemd-resolved and Docker were already running afterward, so neither was restarted. That first openEMS file used the Palace GDS and is discarded. The numbers above are from the rerun on the openEMS GDS.

## Open risks

- The pinned PDK commit and current `dev` have diverged. A later move to `dev` HEAD needs a new decision.
- Palace port polygons in the v0.8.2 example GDS have zero height. Palace still showed a connected 2-port. openEMS does not accept that GDS with the openEMS stack-up.
- openEMS warned that its timestep is very small. Palace's mesh still contains 5 ill-shaped tetrahedra.
- LinHT Rev C is not validated. Supply, 36 MHz reference, and I2S facts stay provisional. USB-A connector part numbers are not chosen.
- Neither Q value is ready to use as a design target until the meshes are converged.

## Decisions still needed

1. Whether to follow `dev` past `a49358cc` once the image catches up.
2. Whether to spend another EM run on a matched mesh and one shared stack-up before trusting Q.
3. Approval to start Phase 1 RTL. Topology approval is still required before any analog schematic.

## Dual-use table

Evidence for host facts is the public LinHT page and README fetched 2026-10-17, plus Semtech SX1255 datasheet Rev 3.0. No RFIC exists yet. The supply, reference, and I2S rows are decisions for this project, not measured chip performance.

| Requirement | Repeater | LinHT |
|---|---|---|
| Supply rails defined for the RFIC | Decision recorded: backplane rails +12 V PA, +5 V, +3.3 V, +1.8 V from `docs/RF-modules.md` r0.3. Not measured on a board. | Decision recorded: 5 V buck from a 2S pack (`TPS565242DRLR`, charger `BQ25792RQMR`). Ripple and spur tolerance is required. No ripple amplitude has been measured. Rev C is not validated. |
| RX, TX, standby, shutdown current | not yet evaluated | not yet evaluated |
| Both 2 m and 70 cm | not yet evaluated | not met by current LinHT. README: current revisions are UHF only. VHF is not ruled out later. |
| Temperature range in corners | not yet evaluated | not yet evaluated. SX1255 operating range in its datasheet is -40 C to +85 C. That is the host front-end, not this RFIC. |
| IQ interface compatible with the host | Decision recorded: references 32 MHz and 36 MHz; I2S slot 16 or 32 bits, MSB-justified, 16-bit baseline. Integer-boundary map is in `spec/integer-boundary-spurs.md`. Spur levels were not estimated. | Same decision, provisional. SX1255 Rev 3.0 tables use a 36 MHz reference. Mode B serialises internal 32-bit I and Q buses. Pin wiring was not confirmed from KiCad. |
| Package at most 5 x 5 mm for the handheld | not yet evaluated | not yet evaluated |
| USB-A security-dongle slot on a future handheld PCB proposal | not applicable | not yet designed. No part numbers are recorded. See `reports/linht-proposals.md`. |

## Assumptions and items not verified

- LinHT KiCad sources were not downloaded.
- Tapeout submodules inside `IHP-Open-FMD_QNC-Tapeouts` were not checked out.
- No simulation number in this package was copied from a third-party report. The L and Q values were computed here from the Touchstone and Palace port-S files.

Work stops at this gate.
