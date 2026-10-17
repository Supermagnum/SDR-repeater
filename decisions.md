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

Not approved: any analog topology, any phase advance past this review, any push.
