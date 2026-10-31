# P2.7 layout notes

Status: **notes only, 2026-10-31.** Layout has not started. Owner: P2.7 may begin with open IHP LVS issues #861, #753 and #512; document a workaround for each and re-check when the PDK pin moves (`decisions.md` 2026-10-31).

## Before the first P2.7 run

Re-run the VACASK schematic results that `reports/status-2026-10-30.md` only checked against committed `out/summary_*.txt` (VCO steps 1–3, LO step 3, PLL steps 1–4 and p26 steps 2–3 as applicable). Do not treat file-backed SCH numbers as fresh until that re-run.

Prerequisites still in flight for a clean layout start: P2.6 open point 2 (bypass — done 2026-10-31) and open point 1 (V_tune monitor). Open point 3 does not block P2.7.

## Open IHP LVS issues — workarounds

| Issue | Problem | Workaround until the pin moves | Re-check |
|---|---|---|---|
| [#861](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/861) | Missing ThickGateOx (44/0) → SVaricap not extracted in KLayout LVS | Do not treat a clean VCO LVS as proof that the varactor is present. Keep a device-level checklist: count of `sg13_hv_svaricap` in schematic vs drawn PCells; optional textual LVS waiver with the open-issue ID until ThickGateOx is in the deck | First VCO LVS on the new pin |
| [#753](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/753) | KLayout LVS does not check `Nx` on SVaricap | Draw the intended finger count; record `nx` in the schematic and in the layout notes. LVS cannot prove finger count — rely on PCell parameters and visual / scripted GDS property check | First multi-finger SVaricap LVS |
| [#512](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/512) | `rfcmim` LVS: multi-port warnings; crash on series/parallel combination | Prefer single `cap_rfcmim` devices or a combination style already proven on this deck; avoid untested series/parallel banks in one LVS cell until fixed. Cap bank and AC-coupling MIMs: one device per schematic instance where practical | First bank / coupling MIM LVS |

Related: maximal DRC for SVaricap at `w=3.74u` (#639 fixed upstream — confirm on this pin during P2.7). See also `reports/pdk-tool-issues-2026-10-30.md`.

## Layout scope (from `spec/phase2-plan.md`)

VCO, dividers and PLL in KLayout/Magic; DRC/LVS; PEX; tapped L2n0 EM; LO routing EM and post-layout pnoise; integer-boundary coupling target raw ≤ −35 dBc (VHF) / −15 dBc (UHF) at the VCO. Every schematic from here: xschem `.sch` with SVG/PDF export; layouts `.gds.gz` with reports and rendered pictures.
