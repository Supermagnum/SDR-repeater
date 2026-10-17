# Tool manifest

Checked: 2026-10-17. Previous lock: none. The container, the image PDK commit, and the EM workflow tags below were accepted on 2026-10-17. Analog topology is not approved.

Every row was read from a live repository API, Docker Hub, PyPI, Codeberg, or a project page on this date. `hpretl/iic-osic-tools:2026.10` runs on this host. Host `PATH` still has no `ngspice`, `klayout`, `xschem`, or `xyce` outside that image.

| Tool | Canonical URL | Version / commit used | Release or commit date | Status | Notes |
|---|---|---|---|---|---|
| IIC-OSIC-TOOLS | https://github.com/iic-jku/IIC-OSIC-TOOLS | tag `2026.10`; Docker Hub `hpretl/iic-osic-tools:2026.10` | release 2026-10-15; image 2026-10-15 | OK | Default branch `main` pushed 2026-10-17. Not archived. GitHub project is a fork of `efabless/foss-asic-tools`. AMS template requires tag `2026.09` or later, so `2026.10` is the newest tag that template accepts. `2026.10` adds EZ130 cells, OpenCDC, an OpenVAF `mb-experimental` build for VACASK `absdelay`, and a KLayout-PEX bump with FEM plugins. |
| IHP-Open-PDK | https://github.com/IHP-GmbH/IHP-Open-PDK | pinned `a49358cc0b20635fcb53c0940505e3563763fc7a` from image `2026.10` | image commit 2026-10-15 | pinned, do not follow `dev` | The image commit contains the RF MOSFET LVS decks (`rfmos_extraction.lvs` extracts `rfnmos`; `rfmos_model_mapping.lvs` is absent). `dev` is not followed. The pin is reconsidered only at a phase review gate. |
| AMS chip template | https://github.com/iic-jku/ihp-sg13g2-ams-chip-template | tag `2026.09`, commit `4a283cd07d3b68ca1e82830cade4816a89ccd222` | tag published 2026-10-14 | OK | Not archived. README requires IIC-OSIC-TOOLS `2026.09` or later. Also documents VACASK and CACE. `make all` builds a tapeout-ready GDS; this project must not run any submit or upload target. |
| LibreLane full-chip template | https://github.com/IHP-GmbH/ihp-sg13-librelane-template | `main` `23c62045bb212175c20d8186a7ab308e15fba98c` | 2026-10-16 | updated | The name `ihp-sg13g2-librelane-template` redirects here. No GitHub release. README says it supports both `ihp-sg13g2` and `ihp-sg13cmos5l`, and its Nix shell tracks LibreLane `dev`. |
| LibreLane | https://github.com/librelane/librelane | release `3.0.16` | 2026-10-06 | OK | Not archived. Successor of OpenLane, stated in the repository description. `ihp-sg13g2` is not bundled; release docs point at `IHP-Open-PDK` `ihp-sg13g2/libs.tech/librelane`. Default branch pushed 2026-10-08. Newer dev tags `3.1.0.dev1` through `3.1.0.dev3` exist and are not proposed. |
| CACE | https://github.com/fossi-foundation/cace | PyPI `cace` 2.13.0; git `dedb5e0d` | PyPI upload 2026-09-23; commit 2026-09-24 | OK | Canonical org is now FOSSi Foundation. PyPI homepage matches that repository. No GitHub release objects. `efabless/cace` last commit 2025-02-07 and is rejected. |
| Xschem | https://github.com/StefanSchippers/xschem | container pin `d76e6cc74fdfa5de573a8ba14124ef00c611a9b6`; latest tag `3.4.7` | pin 2026-10-13; tag 2025-05-14 | OK | Not archived. `master` moved again on 2026-10-17 (`6bbc0e36`). PDK `dev` changelog says xschem scripts were updated toward 3.4.8RC. Follow the container pin, not floating `master`. |
| KLayout | https://github.com/KLayout/klayout | `v0.30.12` | 2026-08-26 | OK | Not archived. `master` pushed 2026-10-16, after the release. Container pins the release. |
| KLayout-PEX | https://github.com/iic-jku/klayout-pex | `v0.6.10` | 2026-10-16 | OK | Not archived. Project site still says early stage and not for production sign-off. Open SG13G2 issues: non-MAGIC engines can emit empty LVSDB layers (issue 158, 2026-04-28); 2.5D HBT netlists omit the `X` subcircuit prefix (issue 151). |
| ngspice | https://ngspice.sourceforge.io/ | `ngspice-47` | 2026-08-11 | OK | Container pins the SourceForge mirror tag. Release notes list an update to experimental PSS, plus small-signal noise for code models. They do not add PNOISE. PSS on current master remains experimental and autonomous-only. |
| Xyce | https://github.com/Xyce/Xyce | `Release-7.10.0` | 2025-07-21 | OK | Not archived. `master` pushed 2026-10-05, after the release. No newer release. Container pins 7.10.0. |
| openEMS | https://github.com/thliebig/openEMS-Project | `v0.37.0` (`974294ba`) | 2026-10-09 | OK | Not archived. This is the container pin. |
| openEMS SG13G2 workflow | https://github.com/VolkerMuehlhaus/gds2openEMS | `v0.5.0` (`99d8bd18`) | tag 2026-09-28 | pinned for EM | Image PDK submodule is still `e29417aa` (2025-05-23). The regression used the tag, and stack-up XML only from the pinned PDK. |
| gds2palace | https://github.com/VolkerMuehlhaus/gds2palace_ihp_sg13g2 | `v0.8.2` (`ed063dc9`) | tag 2026-10-12 | pinned for EM | Package `__version__` inside that tag still says `0.8.1`. Image PDK submodule is `a904bc08`, not this tag. Stack-up XML came from the pinned PDK. `combine_snp` de-embedding was not used. |
| Palace | https://github.com/awslabs/palace | container pin `1fa13c9d` (after `v0.18.1`) | pin 2026-10-14; release `v0.18.1` on 2026-09-21 | OK | Not archived. `main` pushed 2026-10-16. |
| Analog OpenSource IHP add-on | https://github.com/AliSahafi/Analog_OpenSource_ihp | `main` `2d87abbb` | 2026-08-18 | deprecated for this flow | Not archived, but the README still builds on `hpretl/iic-osic-tools:2026.07`. Not verified against `2026.10`. Official container already contains openEMS, Palace, and KLayout-PEX. Do not adopt. |
| cocotb | https://github.com/cocotb/cocotb | `2.1.0` in the image | 2026-08-30 | OK | Not archived. Installed at `/usr/local/lib/python3.12/dist-packages/cocotb`. Absent from `_build/tool_metadata.yml`. No project venv. |
| VACASK | https://codeberg.org/arpadbuermen/VACASK | container pin `fb8cc205`; latest release `_0.3.4` | release 2026-09-13; `main` commit 2026-10-15 | OK | Not archived. AMS template uses it through the Spectre netlist path. Included because the current AMS README requires it alongside ngspice. |
| IHP-Open-DesignLib | https://github.com/IHP-GmbH/IHP-Open-FMD_QNC-Tapeouts | `main` `242e511a` | 2026-10-15 | updated | `IHP-GmbH/IHP-Open-DesignLib` now resolves to this repository. Not archived. No GitHub releases. Designs are monthly submodules and were not expanded. |
| gdsfactory IHP | https://github.com/gdsfactory/IHP | `main` `8f023c77` | 2026-10-16 | not adopted | Not archived. Parametric SG13G2 cells, including RF MOS, HBT, and spiral inductors. Reported only. |
| LinHT hardware (read only) | https://linux-radio.eu/ and https://github.com/M17-Project/LinHT-hw | `main` `72336d64`; release tag `revC` | README commit 2026-10-16; tag 2026-09-17 | OK as reference | Not cloned. See `reports/linht-proposals.md`. |

## PDK `dev` versus release `v0.3.0`

`dev` CHANGELOG section "Unreleased - 2026-09-01", read from `dev` on 2026-10-17, is absent from the `v0.3.0` changelog. Items that change SG13G2 analog and RF work:

- New KLayout PyCells: `cap_cmomf`, `cap_mom`, `cap_cmomi`, MOSCAP, RF MOSFET PyCells, `NoFillerStack`, `ptap1`.
- Device-model edits: `svaricap` `vj` for 125 C transient, `rhigh` statistical parameters aligned to the process spec, `rsil` `b` parameter removed, `rfcmim` `m` multiplier.
- LVS: RF MOS devices stay as extracted `rf*` classes (`#1246`). Parallel RF and plain fingers no longer merge, and some layouts that previously matched can now fail LVS. Inductor metal stack is configurable. Metal resistors map to an `R` prefix.
- DRC: `--precheck_drc` is deprecated and renamed to `--minimum_drc` (`#1261`). The old flag still runs, with a warning.
- EM: AWS Palace `gds2palace` submodule added; Palace submodule bumped for a scikit-rf 2.0 fix (`#1040`). The openEMS tree's previous examples now live under `obsolete/`.
- SG13CMOS5L, a reduced-metal CMOS-only variant, is in the same tree. The AMS template warns that a wrong `PDK` value silently mixes technologies.

`main` is behind `dev`. A release tag has not absorbed this changelog.

## Phase-noise tooling

- ngspice 47: transient noise and experimental autonomous PSS. Release notes do not document PNOISE. The 2022 maintainer statement that PNOISE is unsupported was not contradicted by the ngspice-47 news page.
- Xyce 7.10.0 is the available harmonic-balance engine. This check did not run Xyce and does not claim a PNOISE feature.
- QUCS-COPEN is described in arXiv:2603.07828 (submitted 2026-03-08) as a working title. No maintained public repository was found. Do not use it until a human approves a located source.
- Qucs-S `26.1.1` is in the container and is a schematic front end, not a substitute PNOISE engine.

## Other SG13G2 work found, not adopted

- `gdsfactory/IHP`: RF layout generators. Active on 2026-10-16.
- arXiv:2607.08852: open-source 2.4 GHz fractional-N LC PLL in SG13G2. Literature only. Its reported phase-noise number is not a result of this project.
- `2AMLogic/sg13g2-lna`, `sg13g2-vco`, `sg13g2-pll`, `sg13g2-sat-rx`: public agent-built blocks updated 2026-10-17. Not reviewed and not a source of numbers for this project.
- `nySe08/radar-chip-24ghz`: 24 GHz, outside the VHF/UHF scope.
- No separate official IHP pre-submission uploader was found. The PDK DRC flag `--minimum_drc` is a rule-deck mode, not a shuttle client. Shuttle, MPW, Tiny Tapeout, and wafer.space clients are out of scope.

## Prior-art gap

`IHP-Open-FMD_QNC-Tapeouts` stores each tapeout as a submodule. Those submodules were not checked out. A statement that IHP has no SG13G2 LNA, mixer, VCO, divider, or sigma-delta below 6 GHz would be unsupported.
