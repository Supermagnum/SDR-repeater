# PDK and tool issues affecting HT13G-M

Date: 2026-10-30. Prompt 02. No design, PDK pin or container pin was changed.

## Pins checked

| Item | Value in this repo / image |
|---|---|
| Container | `hpretl/iic-osic-tools:2026.10` |
| PDK | `/foss/pdks/ihp-sg13g2/COMMIT` = `a49358cc0b20635fcb53c0940505e3563763fc7a` |
| VACASK | `fb8cc20` |
| OpenVAF-Reloaded | `osdi_0.5_20260820-26-gdd05b5e-dirty` (OSDI 0.5) |
| ngspice | 47 |
| KLayout | 0.30.12 |
| Magic | 8.3.685 |
| netgen | 1.5.324 |
| LibreLane | 3.1.0.dev3 |
| OpenROAD | 26Q4-407-geb14e40b7 |
| Yosys | 0.70 |

Sources: container binaries and `/foss/pdks/ihp-sg13g2/COMMIT`. Issue trackers searched: [IHP-GmbH/IHP-Open-PDK](https://github.com/IHP-GmbH/IHP-Open-PDK/issues), [iic-jku/IIC-OSIC-TOOLS](https://github.com/iic-jku/IIC-OSIC-TOOLS/issues). VACASK’s own tracker on Codeberg was not searched in this session (GitHub search has no usable VACASK upstream repo under that name). LibreLane / OpenROAD issue search returned no accessible hits from this account for the hold / ICG keywords used.

Device classes this design uses (schematic and digital): LV/HV MOS (PSP), `sg13_hv_svaricap`, `cap_rfcmim`, EM inductor stack (openEMS / Palace), `npn13G2` (comparison only so far), resistors, stdcells / IO, corners and Monte Carlo, KLayout DRC/LVS (P2.7), LibreLane digital flow. Seal ring and metal filler are not yet laid out.

## Issue table

| Source | Issue (link) | Affects | Status | Our handling | Results to re-check |
|---|---|---|---|---|---|
| IHP-Open-PDK + VACASK conversion in the image | Local: VACASK `sg13g2_svaricaphv_mod.lib` keeps `v(2,4)` in the well resistance (coefficients `rwellvw` / `rwellwvw` / `rwellnxvw` are 0). VACASK does not elaborate the expression. Same form exists in the ngspice model (`v(2, 4)`). Not filed upstream. | Every VACASK run that instantiates `sg13_hv_svaricap` (VCO steps 1–3, P2.6 closed loop) | **affects us, worked around** | `analog/vco/step1/run_step1.py` `svaricap_fixed()` writes `out/svaricap_fx.lib` (`sg13_hv_svaricap_fx`), documented in `analog/vco/step1/README.md` and `spec/vco-topology.md` §8. Draft upstream text: `reports/upstream-issues/ihp-svaricap-vacask-v24.md`. | Any VCO / PLL result that used the patched model stays valid only while the coefficients stay 0. Re-run VCO C–V / Q and band pnoise if the model expression changes. |
| IHP-Open-PDK | [#1098](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/1098) (closed 2026-08-24) ngspice transient of `sg13_hv_svaricap` above ~52.47 °C with positive well bias (`dsubw` `vj=0.1` without TLEVC). Fix [#1102](https://github.com/IHP-GmbH/IHP-Open-PDK/pull/1102) (`vj` → 0.3357). | ngspice cross-checks of the varactor at 85 / 125 °C | **fixed in pin `a49358cc`** | Pin has `vj=0.3357` in both ngspice and VACASK `dsubw` model cards. No local patch for this. | None for the pin. If an older image without #1102 is used, high-temp ngspice varactor transients are unverified. |
| IHP-Open-PDK | [#639](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/639) (closed 2026-08-27) SVaricap PCell `w='3.74u'` NW.e DRC on maximal ruleset. Fixed in PR #819. | Layout of the AC-coupled varactor (we use `w=3.74u`) | **fixed upstream after the original report; present in pin** | Use the PCell as documented; confirm NW.e on maximal DRC in P2.7. | P2.7 VCO varactor DRC (maximal). |
| IHP-Open-PDK | [#861](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/861) (open) Missing ThickGateOx (44/0) → SVaricap not extracted in KLayout LVS | P2.7 LVS of the VCO | **affects us, not handled** | No layout yet. Do not treat a clean LVS as proof until this is fixed or waived with a documented deck pin. | First SVaricap LVS when P2.7 starts. |
| IHP-Open-PDK | [#753](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/753) (open) KLayout LVS does not check `Nx` on SVaricap | VCO uses multiple fingers (`nx`) | **affects us, not handled** | Same as #861: open for P2.7. | First multi-finger SVaricap LVS. |
| IHP-Open-PDK | [#512](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/512) (open) `rfcmim` LVS: multi-port warnings; crash on series/parallel combination | Cap bank and AC-coupling MIMs (`cap_rfcmim`) | **affects us, not handled** | No layout yet. Prefer single devices or a proven combination style when LVS starts. | First bank / coupling MIM LVS. |
| IHP-Open-PDK | [#754](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/754) (open) RF MOSFET xschem name vs KLayout PCell name (`sg13_lv_rf_*` vs `rfnmos` / `rfpmos`) | Only if RF MOSFETs are used in schematic+layout | **does not affect us** (today) | Phase 2 uses `sg13_lv_nmos` / HV devices and HBTs for the LO. Revisit if RF MOSFETs enter the LNA/mixer. | — |
| IHP-Open-PDK | [#1112](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/1112) (open) HBT local mismatch: fixed 10 % area sigma, not Pelgrom | Any Monte Carlo that relies on HBT local matching | **affects us, not handled** if HBT mismatch MC is used | HBT was a comparison path; LO core is NMOS. Do not claim Pelgrom HBT matching from the PDK MC decks. | Any future HBT mismatch MC. |
| IHP-Open-PDK | [#780](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/780) (open) Magic `npn13G2` PCell DRC vs KLayout | Only if Magic is used to lay out HBTs | **does not affect us** (today) | Layout path for P2.7 is KLayout-first in the plan. Avoid Magic PCell for `npn13G2` until fixed. | — |
| IHP-Open-PDK | [#1287](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/1287) (open) Inductor LVS extraction (centre-tap / space). Filed against SG13CMOS5L deck | Custom EM coils, not the SG13G2 std inductor flow we use for L2n0 | **does not affect us** (today) | Tank inductor is EM GDS + lumped fit, not the CMOS5L LVS inductor path. Revisit if SG13G2 inductor LVS is required for a PCell coil. | — |
| IHP-Open-PDK | [#895](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/895) (open) GFil.i DRC on large inductor PCell | Std inductor PCell | **does not affect us** (today) | We use the shared L2n0 GDS / custom mesh, not that PCell for the tank Q decision. | — |
| IHP-Open-PDK | [#314](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/314) / [#806](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/806) s2p inductor + ngspice | Only if s2p is dropped into ngspice | **does not affect us** | VCO uses a lumped VACASK fit from EM (`analog/vco/step1`), not s2p in the pnoise deck. | — |
| IHP-Open-PDK / local method | Palace stack-up XML in the same PDK commit differs from the openEMS `SG13G2_200um.xml` | EM Q / L | **affects us, worked around** | Decision: both solvers use the pinned openEMS stack (`decisions.md`, `reports/phase0-review/em-l2n0.md`). Palace workflow XML is not used. | Matched-mesh EM already accepted for Q; re-check only if the stack pin changes. |
| IHP-Open-PDK | [#1047](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/1047) (open, labeled invalid / wontfix) Long sim times and “timestep too small” vs other PDKs | Transient noise / stiff LO chain | **affects us, not handled** as a method limit | Matches P2.6 step 2: UHF ÷2 / Johnson noisy transient fails at 50 / 20 / 10 GHz noise BW; VHF converges. No upstream fix to adopt. Floor taken as estimate ≈ −150 dBc/Hz (`spec/pll-topology.md` §13). | UHF LO floor (P2.6 open point 3) until a working method exists. |
| IHP-Open-PDK | [#921](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/921) (open) IO pad diode → ngspice “timestep too small” | Chip-level ngspice with IO pads | **affects us, not handled** (later) | No pad-level transient yet. | First full-chip ngspice with IO. |
| IHP-Open-PDK | [#810](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/810) (open) Pin-order mismatch stdcell `.spice` / `.cdl` / `.lef` | Analog simulation of LibreLane GDS extracted by Magic | **affects us, not handled** (later) | Digital gate sim today uses liberty Verilog cell models, not Magic-extracted spice of the stdcell LEF. | Any post-layout stdcell spice that mixes those views. |
| IHP-Open-PDK | [#804](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/804) / [#805](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/805) (closed) Channel thermal / flicker bookkeeping | PSP noise | **does not affect us** | Closed as user error / documentation; not a model defect for our use. | — |
| IHP-Open-PDK | [#13](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/13) (closed) Missing ngspice varicap models | Historical | **does not affect us** | Models exist in the pin. | — |
| IHP-Open-PDK | [#414](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/414) / [#891](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/891) (closed) SVaricap LVS | Older LVS bugs | **fixed upstream** | Superseded by open #861 / #753 for current work. | — |
| PDK liberty / LibreLane | `sg13g2_lgcp_1` / `sg13g2_slgcp_1` `dont_use` and listed in `synth_exclude.cells` / `pnr_exclude.cells` | Digital clock gating | **affects us, worked around** | Deliberate: behavioral latch+AND root gates (`rtl/digital/clk_gate.sv`, `rtl/digital/notes.md`). Owner rule: do not lift `dont_use`. | Hold-buffer area after any future ICG policy change. |
| IIC-OSIC-TOOLS | [#375](https://github.com/iic-jku/IIC-OSIC-TOOLS/issues/375) (closed 2026-10-07) OpenVAF OSDI 0.4 → `absdelay` silently zero in 2026.09 | Ideal t-lines / absdelay models | **fixed in container 2026.10** | Image ships OpenVAF-Reloaded OSDI 0.5. Design does not rely on `absdelay` for the LO. | None on 2026.10. |
| Local method (VACASK) | Driven pss/pnoise on TSPC / dynamic CMOS (P2.4 step 3) | Divider noise floor | **affects us, worked around** (method) | Declared unusable; hand estimate then VHF transient noise in P2.6. No matching closed upstream fix found. | UHF LO floor (same as #1047 row). |
| Local method (VACASK) | Full VCO pss at `reltol` 1e-7 does not converge; 1e-6 matches validated level-2 within 0.00 dB | VCO pnoise | **affects us, worked around** | Settings in `analog/pn-validation/README.md` and `analog/vco/step2/run_step2.py`. | Re-validate if VACASK pss defaults change. |
| Local method (VACASK) | First-trial “timestep too small” / DC OP failures on LO noisy transient | P2.6 step 2 | **affects us, worked around** (procedure) | Noiseless warm-up from power-on, then noisy transient; documented in `spec/pll-topology.md` §13. | UHF still fails after that procedure. |

## Results to re-check (unverified until prompt 01 re-runs them)

These are the rows whose status is “affects us, not handled” or that depend on a workaround that could drift:

1. **UHF LO-chain noise floor** (P2.6 open point 3) — estimate ≈ −150 dBc/Hz; transient noise does not converge.
2. **First KLayout LVS of `sg13_hv_svaricap`** — blocked or unreliable while #861 / #753 are open.
3. **First KLayout LVS of parallel/series `cap_rfcmim` banks** — #512.
4. **Maximal DRC of SVaricap at `w=3.74u`** — confirm #639 fix on this deck in P2.7.
5. **Any HBT local-mismatch Monte Carlo** — #1112.
6. **Full-chip ngspice with IO pads** — #921.
7. **Magic-extracted stdcell spice mixed with PDK `.spice`** — #810.
8. **VCO / PLL VACASK results that use `sg13_hv_svaricap_fx`** — re-run if the upstream well-resistance expression or VACASK expression rules change (draft issue not yet submitted).

## Updating the pin (proposal only — not done)

Do not move `a49358cc` or `2026.10` without an owner decision at a phase gate.

| Candidate | Why | What would change | Sims to re-run |
|---|---|---|---|
| Newer IHP `dev` after LVS fixes for #861 / #753 / #512 | Needed before trusting P2.7 LVS | LVS decks / PCells | Device LVS unit tests; then VCO/MIM LVS |
| Keep 2026.10 | Already has OSDI 0.5 (#375) and OpenVAF that matches VACASK | — | — |
| Drop `v(2,4)` upstream in the ngspice/VACASK svaricap wrapper | Removes the local `_fx` patch | Identical C–V if coefficients stay 0 | VCO step 1 C–V/Q smoke; one band pnoise |

No pin change is proposed for #1098 (already in the pin) or for #1047 (no fix).

## Method limits vs tool bugs (P2.6 open point 3)

| Observation | Matches a known issue? | Closes open point 3? |
|---|---|---|
| Unusable pss/pnoise on TSPC | No filed VACASK issue found in this pass; pattern is local | No |
| VCO pss needs `reltol` 1e-6 | Local; validated against level 2 | N/A (workaround accepted) |
| UHF noisy transient fails; VHF works | Same class as #1047 (stiff / timestep), but that issue is wontfix | No |
| Early “timestep too small” / DC OP | Procedure fixed for VHF | UHF remains open |

Open point 3 stays open: UHF LO floor is still an estimate.

## Local workarounds — upstream status

| Workaround | Documented in repo? | Reported upstream? |
|---|---|---|
| `sg13_hv_svaricap_fx` (drop zero-coeff `v(2,4)`) | Yes (`step1/README.md`, `vco-topology.md`) | **No** — draft in `reports/upstream-issues/ihp-svaricap-vacask-v24.md` |
| openEMS stack for both EM solvers | Yes (`decisions.md`, EM report) | N/A (local choice of which XML to use) |
| Behavioral ICG instead of `lgcp`/`slgcp` | Yes (`rtl/digital/notes.md`) | N/A (`dont_use` is intentional PDK policy) |
| Looser VCO `reltol` / noisy-transient warm-up | Yes (pn-validation, pll-topology §13) | No matching fix to cite |

## Sources for this report

- GitHub issue API / search on IHP-Open-PDK and IIC-OSIC-TOOLS (2026-10-30).
- Container inspection of PDK COMMIT, liberty `dont_use`, exclude cells, svaricap libs.
- Repo docs: `decisions.md`, `spec/vco-topology.md`, `spec/pll-topology.md`, `spec/lo-divider-topology.md`, `analog/vco/step1/README.md`, `analog/pn-validation/README.md`.
