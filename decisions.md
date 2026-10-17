# Decisions

Human decisions for the SG13G2 VHF/UHF RFIC. An entry is added only after a person approves it.

## 2026-10-17 — Phase 0 review

Approved:

- Container `hpretl/iic-osic-tools:2026.10`.
- PDK commit `a49358cc0b20635fcb53c0940505e3563763fc7a`, the commit named in that image. It contains the RF MOSFET LVS change (pull request 1246, merge `f7bca326`) and is 26 hours before `dev` `89d42ee`. `89d42ee` is not pinned. The two commits have diverged: 43 commits are only on `dev`, and 48 commits are only in the image, mostly the `sg13g2_stdcell_hv` library.
- KLayout DRC flag `--minimum_drc`.
- EM workflows `gds2palace` `v0.8.2` (`ed063dc9`) and `gds2openEMS` `v0.5.0` (`99d8bd18`). Stack-up XML is taken from the pinned PDK commit.
- CACE `fossi-foundation/cace` 2.13.0.
- cocotb 2.1.0 from the image. No project venv.
- Rejections: `efabless/cace`, `AliSahafi/Analog_OpenSource_ihp`, QUCS-COPEN.
- ngspice 47 experimental PSS is allowed. Phase-noise results stay lower confidence.
- Supply assumption replaced by regulated host rails, with buck ripple and spur tolerance required. See `spec/baseline-decisions.md`.
- PLL references 32 MHz and 36 MHz. Spur map: `spec/integer-boundary-spurs.md`.
- I2S slot width 16 or 32 bits, MSB-justified, 16-bit baseline.
- LinHT facts stay provisional. USB-A part numbers wait.

Recorded after those approvals, not a new topology decision: `SG13_Octagon_L2n0` L and Q at 2.4 GHz and 3.5 GHz are in `reports/phase0-review/em-l2n0.md`. That file is a regression baseline. It is not a pass or fail against a specification.

Not approved at that point: any analog topology, and any push.

## 2026-10-17 — Phase 0 EM review

Approved:

- Stay on PDK `a49358cc`. Do not follow `dev`. Reconsider the PDK pin only at a phase review gate.
- The image commit does contain the RF MOSFET LVS change. `rfmos_extraction.lvs` extracts `rfnmos`. `rfmos_model_mapping.lvs` is not in the image.
- Both EM solvers use the pinned-PDK openEMS stack-up `SG13G2_200um.xml`, sha256 `5d452943`. The Palace workflow XML in the same commit is a different stack and is not used. Hashes are in `reports/phase0-review/em-l2n0.md`.
- Matched mesh, shared port de-embedding, and a comparison to a compact model or IHP measured data are required before Phase 2. They are not a Phase 1 blocker. No compact model and no `L2n0` measured file were found in this PDK commit.
- Provisional tank Q is the openEMS value: 11.8 at 2.4 GHz and 14.9 at 3.5 GHz. See `spec/provisional-tank-q.md`.
- Phase 1 digital back end may start. Analog topology is still not approved.

## 2026-10-17 — Phase 1 review, not approved

The first Phase 1 submission was not approved. The resubmission is on `phase1/digital` and is waiting for review. It is not an approval and it is not a topology decision.

Recorded in `reports/phase1-review/summary.md`, still open:

- The register map and the SPI frame are proposed, not frozen.
- The RFIC is the I2S master by default. Slave mode keeps an asynchronous FIFO. The b14/b15 direction change is only a proposed note in `spec/i2s-clocking.md`.
- LinHT IQ is provisional until the Rev C wiring is read.
- Pre-place timing at 36 MHz does not meet the slow or typical corner.
- The matched-mesh inductor study is still required before Phase 2. It has not been started. Phase 2 has not been started.
