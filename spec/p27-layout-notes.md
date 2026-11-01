# P2.7 layout notes

Status: **notes only, 2026-10-31.** Layout has not started. Owner: P2.7 may begin with open IHP LVS issues #861, #753 and #512; document a workaround for each and re-check when the PDK pin moves (`decisions.md` 2026-10-31).

## Before the first P2.7 run

VACASK SCH re-run done 2026-10-31 (`reports/sch-rerun-2026-10-31.md`): VCO range pass; LO UHF tt pass; PLL 2 µs smoke pass; UHF LO floor −150.1 dBc/Hz (full ÷2+Johnson) pass.

**VCO pnoise:** off-state **bank** bypass MOS break VACASK PSS (`summary_pss_bypass_parts.txt`; tail/var OK). Bank-omitted PN accepted to start layout: tt 3.65 −122.7 / ss85 4.20 −119.4 dBc/Hz @ 1 MHz (`summary_pn_nobank.txt`). Linear off-state equivalent abandoned (PSS still fails). Off-switch noise bound vs bank bias R (`run_bound_bank_switch.py`, `[SCH]+[HAND]`): tt 3.65 **FAIL** Δ = +0.591 dB (ff/125 °C I_leak); ss85 4.20 PASS Δ = +0.006 dB — **STOP** vs ≤0.5 dB. Draft VACASK issue (not posted): `reports/upstream-issues/vacask-pss-off-nmos-tank.md`; minimal repro `analog/vco/step3/repro_pss_bank_bypass.py`.

**Post-layout VCO phase noise:** use the **bank-omitted** extracted netlist (omit off-state bank bypass MOS from the PEX deck the same way as SCH) **plus** the `[SCH]+[HAND]` switch-noise bound above, until VACASK PSS converges with those devices. The bound does **not** yet clear the ≤0.5 dB gate at tt (see `summary_bound_bank_switch.txt`); owner decision needed before treating PEX PN as closed. Do not rely on a linear R/C/leakage stand-in. **Layout order:** VCO, dividers and PLL may start on bank-omitted SCH PN; PEX PN method open.

P2.6 open points 2 (bypass), 1 (V_tune monitor, option B), and 3 (UHF LO floor) closed 2026-10-31.

## Open IHP LVS issues — workarounds

| Issue | Problem | Workaround until the pin moves | Re-check |
|---|---|---|---|
| [#861](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/861) | Missing ThickGateOx (44/0) → SVaricap not extracted in KLayout LVS | Do not treat a clean VCO LVS as proof that the varactor is present. Keep a device-level checklist: count of `sg13_hv_svaricap` in schematic vs drawn PCells; optional textual LVS waiver with the open-issue ID until ThickGateOx is in the deck | First VCO LVS on the new pin |
| [#753](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/753) | KLayout LVS does not check `Nx` on SVaricap | Draw the intended finger count; record `nx` in the schematic and in the layout notes. LVS cannot prove finger count — rely on PCell parameters and visual / scripted GDS property check | First multi-finger SVaricap LVS |
| [#512](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/512) | `rfcmim` LVS: multi-port warnings; crash on series/parallel combination | Prefer single `cap_rfcmim` devices or a combination style already proven on this deck; avoid untested series/parallel banks in one LVS cell until fixed. Cap bank and AC-coupling MIMs: one device per schematic instance where practical | First bank / coupling MIM LVS |

Related: maximal DRC for SVaricap at `w=3.74u` (#639 fixed upstream — confirm on this pin during P2.7). See also `reports/pdk-tool-issues-2026-10-30.md`.

## Layout scope (from `spec/phase2-plan.md`)

VCO, dividers and PLL in KLayout/Magic; DRC/LVS; PEX; tapped L2n0 EM; LO routing EM and post-layout pnoise; integer-boundary coupling target raw ≤ −35 dBc (VHF) / −15 dBc (UHF) at the VCO. Every schematic from here: xschem `.sch` with SVG/PDF export; layouts `.gds.gz` with reports and rendered pictures.
