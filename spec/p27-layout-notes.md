# P2.7 layout notes

Status: **notes, 2026-11-01.** Layout of VCO/dividers/PLL has not started. **Tapped L2n0 EM done** (see below). Owner: P2.7 may begin with open IHP LVS issues #861, #753 and #512; document a workaround for each and re-check when the PDK pin moves (`decisions.md` 2026-10-31).

## Before the first P2.7 run

VACASK SCH re-run done 2026-10-31 (`reports/sch-rerun-2026-10-31.md`): VCO range pass; LO UHF tt pass; PLL 2 µs smoke pass; UHF LO floor −150.1 dBc/Hz (full ÷2+Johnson) pass.

**VCO pnoise:** off-state **bank** bypass MOS break VACASK PSS (`summary_pss_bypass_parts.txt`; tail/var OK). Bank-omitted PN accepted to start layout: tt 3.65 −122.7 / ss85 4.20 −119.4 dBc/Hz @ 1 MHz (`summary_pn_nobank.txt`). Linear off-state equivalent abandoned (PSS still fails). Off-switch noise bound vs bank bias R **closed 2026-11-01** (`summary_bound_bank_switch.txt`): owner gate = positive margin everywhere and worst point (ss85 4.20) moves < 0.5 dB. tt +0.59 dB worst-case bound (margin +6.1 dB); ss85 Δ +0.006 dB. Draft VACASK issue (not posted): `reports/upstream-issues/vacask-pss-off-nmos-tank.md`; minimal repro `analog/vco/step3/repro_pss_bank_bypass.py`.

**Post-layout VCO phase noise:** use the **bank-omitted** extracted netlist (omit off-state bank bypass MOS from the PEX deck the same way as SCH) **plus** the closed `[SCH]+[HAND]` switch-noise bound, until VACASK PSS converges with those devices. Do not rely on a linear R/C/leakage stand-in. **Layout order:** VCO, dividers and PLL may start.

P2.6 open points 2 (bypass), 1 (V_tune monitor, option B), and 3 (UHF LO floor) closed 2026-10-31.

## Open IHP LVS issues — workarounds

| Issue | Problem | Workaround until the pin moves | Re-check |
|---|---|---|---|
| [#861](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/861) | Missing ThickGateOx (44/0) → SVaricap not extracted in KLayout LVS | Do not treat a clean VCO LVS as proof that the varactor is present. Keep a device-level checklist: count of `sg13_hv_svaricap` in schematic vs drawn PCells; optional textual LVS waiver with the open-issue ID until ThickGateOx is in the deck | First VCO LVS on the new pin |
| [#753](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/753) | KLayout LVS does not check `Nx` on SVaricap | Draw the intended finger count; record `nx` in the schematic and in the layout notes. LVS cannot prove finger count — rely on PCell parameters and visual / scripted GDS property check | First multi-finger SVaricap LVS |
| [#512](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/512) | `rfcmim` LVS: multi-port warnings; crash on series/parallel combination | Prefer single `cap_rfcmim` devices or a combination style already proven on this deck; avoid untested series/parallel banks in one LVS cell until fixed. Cap bank and AC-coupling MIMs: one device per schematic instance where practical | First bank / coupling MIM LVS |

Related: maximal DRC for SVaricap at `w=3.74u` (#639 fixed upstream — confirm on this pin during P2.7). See also `reports/pdk-tool-issues-2026-10-30.md`.

## VR_ANA1 / LO supply (D21, 2026-11-01)

Pin 3 is the filtered VCO+LO+CP rail (LDO → 10 Ω → pad → 100 nF). Board C filters LDO noise at duplex offsets; **bond inductance isolates the board cap at divider frequencies** (175 MHz–2 GHz |Z_pad| ≈ 1–90 Ω).

**Local on-chip decoupling (required in layout):**
- Place MIM / MOS bypass at the **VCO centre-tap** and at each **CML / TSPC divider supply** tap so GHz switching currents close on-chip, not through the bond.
- Target: discrete supply-push spurs at divider frequencies **≤ −80 dBc** at the VCO (1 mA into |Z|~few Ω is already near that; keep local C so |Z| stays low).
- Do not rely on the VR_ANA1 100 nF for GHz bounce.

LDO compensation closed 2026-11-01: Rz=500 Ω + **Cg=100 pF** to gnd (Miller-to-mid removed). Transient HOLD; PM ≥ 60° with R=10/bond/100 nF and with C missing; S_v(pad)≈3.0 nV/√Hz @ 10 mA after the fix (prior 9.5 nV unmarked until HOLD). `analog/vco/ldo/out/summary_ldo_verify.txt`.

**Cg area budget (layout):** 100 pF → **≈ 0.0125 mm²** as thin-oxide MOS (≈ 8 fF/µm²; ~112 µm square) or **≈ 0.067 mm²** as MIM (1.5 fF/µm²; ~258 µm square). Prefer MOS for the error-amp gate cap unless a later noise/linearity check forces MIM. On-chip LDO Cout remains a small MIM (~100 fF class); the board 100 nF is off-chip.

## Tapped L2n0 EM ✅ (2026-11-01) [EM]

CT via at outer-turn bottom midpoint; short TM1 stub to CT port; clear of underpass and P/N. Pre-EM: three distinct TM1 nets; R(P–CT) ≈ R(N–CT) ≈ R(P–N)/2 within 2 % (`tapped/review/net_r_check.txt`). Palace 3-port:

| f (GHz) | L (nH) | Q | \|V_CT / V_diff\| |
|---|---|---|---|
| 3.1 | 1.685 | 14.13 | ≤ 0.0036 |
| 3.5 | 1.690 | 15.15 | ≤ 0.0036 |
| 4.2 | 1.703 | 16.66 | ≤ 0.0036 |

All within 2 % of untapped baseline. **[HAND]** 1.4 % lower Q at 4.2 GHz → ≈ 0.1 dB PN at ss 85 °C; remaining margin ≈ +3.5 dB. Details: `spec/provisional-tank-q.md`, `tapped/review/em_summary.md`.

## Layout scope (from `spec/phase2-plan.md`)

VCO, dividers and PLL in KLayout/Magic; DRC/LVS; PEX; ~~tapped L2n0 EM~~ **done**; LO routing EM and post-layout pnoise; integer-boundary coupling target raw ≤ −35 dBc (VHF) / −15 dBc (UHF) at the VCO. Every schematic from here: xschem `.sch` with SVG/PDF export; layouts `.gds.gz` with reports and rendered pictures.
