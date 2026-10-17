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
- PDK `a49358cc0b20635fcb53c0940505e3563763fc7a` from that image. Confirmed in the image: `rfmos_extraction.lvs` extracts `rfnmos`, and `rfmos_model_mapping.lvs` is absent, so the RF MOSFET LVS change is present. `dev` is not followed. The pin is reconsidered only at a phase review gate.
- DRC flag `--minimum_drc`.
- EM workflows `gds2palace` `v0.8.2` and `gds2openEMS` `v0.5.0`. Stack-up XML only from the pinned PDK. cocotb 2.1.0 is in the image. No project venv.
- Rejected: `efabless/cace`, `AliSahafi/Analog_OpenSource_ihp`, QUCS-COPEN. ngspice 47 PSS may be used; phase-noise results stay lower confidence.

## Key result

Both solvers now read the same pinned-PDK stack-up, sha256 `5d4529432b38d7996814f5096af2173d96e8ad5ff84c73ebb57904f1faf03bdf`, and the same port geometry. At 2.4 GHz, Palace reports 1.648 nH and Q 14.2. openEMS reports 1.631 nH and Q 11.8. At 3.5 GHz, Palace reports 1.664 nH and Q 18.7. openEMS reports 1.641 nH and Q 14.9. Inductance agrees to about 1.4%. Q still differs by about 20% and 26%. The meshes are not matched. The provisional tank Q is the openEMS pair. Full figures are in `reports/phase0-review/em-l2n0.md`.

The host was rebooted during the first openEMS attempt. systemd-resolved and Docker were already running afterward, so neither was restarted. That first openEMS file used the Palace GDS and is discarded. The numbers above are from the rerun on the openEMS GDS.

## Open risks

- `dev` is not followed. The pin stays at `a49358cc` until a later phase review gate.
- The v0.8.2 example GDS has zero-height ports. The shared baseline uses the openEMS GDS instead.
- openEMS warned that its timestep is very small. The shared-stack Palace mesh reported no ill-shaped tetrahedra. The meshes are still not refined to the 2% step.
- LinHT Rev C is not validated. Supply, 36 MHz reference, and I2S facts stay provisional. USB-A connector part numbers are not chosen.
- Provisional tank Q is the openEMS result. It is not a converged design target.

## Decisions still needed

1. Matched-mesh comparison before Phase 2: same stack-up (done), same ports (done), port de-embedding, refine until L and Q each change by less than 2% between steps, then compare with a compact model and with IHP measured data if a later PDK or a cited measurement provides either. This PDK commit has neither for `L2n0`.
2. Analog topology, before any schematic.

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
