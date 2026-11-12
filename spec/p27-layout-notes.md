# P2.7 layout notes

Status: **D23 Option A accepted; VCO island ≤ 0.30 mm² (amended 2026-11-12).** **D24 segmented bank recorded.** **P2.7.2c PASS.** **P2.7.2 lin gate accepted (−102.9 dBc).** **P2.7.2a3 Q gate accepted.** **P2.7.2b STOP:** core+tank GDS drawn; DRC/LVS **FAIL** (tn|tp merge; M1.b/M2.b/V1.a).

---

## Inventory — blocks P2.7 must lay out

Device counts are from representative VACASK decks (MOS / MIM / svaricap / resistor instance tags) `[SCH]`; multifinger `ng` still counts as one instance. Exact LVS device counts come after xschem capture.

### Analogue (layout in P2.7)

| Block | Source (deck / script) | Devices (approx.) | Decisions |
|---|---|---|---|
| VCO core (NMOS XC) + tail + RC filter + tail C | `analog/vco/step2/run_step2.py`, `step3/run_step3.py` | Mid-band pick sim: ~14 MOS + 20 MIM + 2 svaricap + ~25 R (bank+var+bias); full with bypasses higher | D1 NMOS, D9 tail, D12 ≤ 4 mA |
| 8-bit bank + trim + switch + plate bias R + bank bypass | same; sizes in `step2/out/range.json` | 8× (2 MIM + 1 switch + 2 R + bypasses) | D8→D20 8-bit |
| AC-coupled varactor + bias R + var bypass | same (`sg13_hv_svaricap_fx`) | 2 svaricap + 2 coupling MIM + 2 R | D11 |
| Start-up bypasses `vbp` / `vbp_tail` | `run_step2.py` `bias_bypass_switches` | LV NMOS across rbf / rba* / rbb* / rvp/rvn | P2.6 op.2; D22 |
| Tapped L2n0 | EM GDS `sim/em/sg13-octagon-l2n0/tapped/`; lumped `analog/vco/models/l2n0_lumped.inc` | Custom TM inductor + CT | P2.0 / tapped EM |
| D22 amp-cal: V_DS-matched OTA DAC, peak det, SE cmp | `analog/vco/ampcal/` (`run_dac.py`, `run_detector.py`, `run_search.py`, `amp_common.py`) | Ampcal top sim ~61 MOS + 20 MIM + 2 var + ~34 R | D22, D12 |
| LO buffer | `analog/lo/step2/`, `step3/run_step3.py` | Part of LO chain | D12–D15 |
| CML ÷2 (UHF) / ÷3 (VHF) + enable | same | LO UHF sim ~120 MOS + ~50 R (full chain) | D13–D15 |
| CML→CMOS converter + TSPC counters / Johnson + retiming | same | included above | D14 |
| PFD + CP (replica, dummy, offset) | `analog/pll/step2/run_step2.py` | Linearity deck ~137 MOS | D16, D18 |
| Bias generator + I_cp DAC | `analog/pll/step4/run_step4.py` | Bias sim ~108 MOS | D18, step 4 |
| Window delay cells | `analog/pll/step4/` | in step-4 decks | lockdet window |
| V_tune hold switch + 2×1 kΩ divider | `analog/pll/step4/` | NMOS/PMOS TG | D20 hold |
| V_tune monitor comparators | `analog/pll/vtune_mon/` | ~18 MOS + ~10 R | D20 |
| Loop filter D19 | values in `spec/pll-topology.md` §13; device checks step 1 | C1 30.8 pF, C2 465 pF MOS; C3 3.1 pF MIM; R1 22.9 kΩ; R3 108 kΩ → ≈ **0.062 mm²** MOS | D17, D19 |
| VR_ANA1 LDO + 10 Ω + Cg 100 pF | `analog/vco/ldo/run_d21_vrana1.py` | LDO sim ~7 MOS + 1 MIM + ~8 R; Cg ≈ **0.0125 mm²** MOS | D10→D21 |

### Digital — stay in signed-off / AFE blocks (not re-laid as analogue)

| Block | Where it lives | Interface into P2.7 analogue |
|---|---|---|
| SPI / I2S / chip digital | `rtl/digital/`, layout **phase1l** (339 617 µm²) | Already signed off |
| MMD (pulse-swallow) | RTL `rtl/afe/mmd.sv` → **AFE/LO control** (D3), not phase1l | `div_clk` from CML first stage (D16); `run` / hold |
| Σ-Δ MASH 1-1-1 | `rtl/afe/sdm.sv` → AFE/LO | N to MMD |
| Band cal + amp SAR | `rtl/afe/bandcal.sv` → AFE/LO | `VCO_BAND`, `VCO_BIAS`, hold, cal_busy |
| Lock detector | `rtl/afe/lockdet.sv` → AFE/LO | UP/DN sample; window delay analogue |
| Sequencer | `rtl/afe/afe_seq.sv` → AFE/LO | `en_vco`, `en_lodiv`, `en_vco_bias_bp`, `en_vco_tail_bp`, … |
| V_tune flag sync | `rtl/afe/vtune_sync.sv` | From analogue monitors → `PLL_STATUS`[4:5] |

Crossing signals (see `spec/analog-digital-interface.md` §5–6): `VCO_BAND[7:0]`, `VCO_BIAS[7:0]`, `PLL_CTRL`, `en_*`, `hold`, `band_sel`, `div_clk` / LO CMOS clocks, `pll_lock`, V_tune monitor bits, I_cp code, MMD modulus controls.

---

## Before the first layout sub-step (carried forward)

VACASK SCH re-run done 2026-10-31 (`reports/sch-rerun-2026-10-31.md`): VCO range pass; LO UHF tt pass; PLL 2 µs smoke pass; UHF LO floor −150.1 dBc/Hz (full ÷2+Johnson) pass.

**VCO pnoise:** off-state **bank** bypass MOS break VACASK PSS (`summary_pss_bypass_parts.txt`; tail/var OK). Bank-omitted PN accepted to start layout: tt 3.65 −122.7 / ss85 4.20 −119.4 dBc/Hz @ 1 MHz (`summary_pn_nobank.txt`). Off-switch noise bound **closed 2026-11-01** (`summary_bound_bank_switch.txt`): tt +0.59 dB (margin +6.1 dB); ss85 Δ +0.006 dB. Detector PN bound `[HAND]` ≈ 0 dB powered down (D22); CML load `[HAND]` ≤ +0.3 dB on top of buffer +0.14 dB (`summary_real_load.txt`).

**Post-layout VCO phase noise:** bank-omitted PEX + the three `[HAND]`/`[SCH]` bounds (bank switch, detector, CML), until VACASK PSS converges with those devices.

P2.3 closed 2026-11-11 (real LO load; D1 keep NMOS).

---

## Open IHP LVS issues — workarounds

| Issue | Problem | Workaround until the pin moves | Re-check |
|---|---|---|---|
| [#861](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/861) | Missing ThickGateOx (44/0) → SVaricap not extracted in KLayout LVS | Do not treat a clean VCO LVS as proof that the varactor is present. Keep a device-level checklist: count of `sg13_hv_svaricap` in schematic vs drawn PCells; optional textual LVS waiver with the open-issue ID until ThickGateOx is in the deck | First VCO LVS on the new pin |
| [#753](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/753) | KLayout LVS does not check `Nx` on SVaricap | Draw the intended finger count; record `nx` in the schematic and in the layout notes. LVS cannot prove finger count — rely on PCell parameters and visual / scripted GDS property check | First multi-finger SVaricap LVS |
| [#512](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/512) | `rfcmim` LVS: multi-port warnings; crash on series/parallel combination | Prefer single `cap_rfcmim` devices or a combination style already proven on this deck; avoid untested series/parallel banks in one LVS cell until fixed. Cap bank and AC-coupling MIMs: one device per schematic instance where practical | First bank / coupling MIM LVS |

Related: maximal DRC for SVaricap at `w=3.74u` (#639 fixed upstream — confirm on this pin during P2.7). See also `reports/pdk-tool-issues-2026-10-30.md`.

---

## VR_ANA1 / LO supply (D21, 2026-11-01)

Pin 3 is the filtered VCO+LO+CP rail (LDO → 10 Ω → pad → 100 nF). Board C filters LDO noise at duplex offsets; **bond inductance isolates the board cap at divider frequencies** (175 MHz–2 GHz |Z_pad| ≈ 1–90 Ω).

**Local on-chip decoupling (required in layout):**
- Place MIM / MOS bypass at the **VCO centre-tap** and at each **CML / TSPC divider supply** tap so GHz switching currents close on-chip, not through the bond.
- Target: discrete supply-push spurs at divider frequencies **≤ −80 dBc** at the VCO (1 mA into |Z|~few Ω is already near that; keep local C so |Z| stays low).
- Do not rely on the VR_ANA1 100 nF for GHz bounce.

LDO compensation closed 2026-11-01: Rz=500 Ω + **Cg=100 pF** to gnd. Transient HOLD; PM ≥ 60°; S_v(pad)≈3.0 nV/√Hz @ 10 mA. `analog/vco/ldo/out/summary_ldo_verify.txt`.

**Cg area budget (layout):** 100 pF → **≈ 0.0125 mm²** as thin-oxide MOS (≈ 8 fF/µm²) or **≈ 0.067 mm²** as MIM (1.5 fF/µm²). Prefer MOS. On-chip LDO Cout remains a small MIM (~100 fF class); the board 100 nF is off-chip.

---

## Tapped L2n0 EM ✅ (2026-11-01) [EM]

CT via at outer-turn bottom midpoint. Palace 3-port: L 1.685 / 1.690 / 1.703 nH, Q 14.13 / 15.15 / 16.66 at 3.1 / 3.5 / 4.2 GHz; \|V_CT/V_diff\| ≤ 0.0036; within 2 % of untapped. **[HAND]** 1.4 % lower Q at 4.2 GHz → ≈ 0.1 dB PN. Details: `spec/provisional-tank-q.md`, `sim/em/sg13-octagon-l2n0/tapped/review/em_summary.md`.

---

## Plan — numbered sub-steps (one prompt-06 run each)

Dependency order. Every analogue block: **xschem `.sch` + SVG/PDF**, then layout **`.gds.gz`**, KLayout DRC, netgen LVS (with #861/#753/#512 workarounds), PEX where listed, KLayout PNG/SVG, `out/summary_*.txt`. Netlist equivalence: generated VACASK deck from xschem must match the simulated deck (device types, connectivity, key parameters) before layout.

### P2.7.0 — Plan + floorplan ✅
**Inputs:** closed P2.3–P2.6; notes above.  
**Outputs:** this file; `spec/p27-floorplan.md`; `phase2-plan.md` §3 update.  
**Pass:** D23 Option A recorded 2026-11-11. **No layout.**

### P2.7.1 — xschem capture: VCO + amp-cal + LDO ✅
**Outputs:** `analog/vco/sch/`; SVG/PDF; `out/summary_xsch_vco.txt`. Whole-die tally in `p27-floorplan.md` §8.  
**Pass:** capture accepted (`decisions.md` P2.7.1 results). Range miss deferred to 1b.

### P2.7.1b — Range shift cause + re-baseline (done 2026-11-11, finding)
**Outputs:** `sch/out/summary_p271b.txt`, `summary_range_shift.txt`; `step2/out/range.json` + `range_2026-10-25.json`; `summary_range.txt`, `summary_steps.txt`; `step3/out/summary_8bit_range.txt`; D22 `ampcal/out/summary_search_rebaseline.txt`; landing `sch/out/summary_land_rebaseline.txt`.  
**Pass / finding:**
- Cause: off-state **bank** (+ var) bypass C (−18 MHz at code 0 vs nobp). PDK pinned.
- Re-baseline done. 15-corner **3.12–4.20 covered**; oxide ≤ 1.46 V; worst top margin **39 MHz**.
- Band steps **FAIL** (1.06 V at 127→128). Held for 1c.

### P2.7.1c — Binary bank bypass + re-trim (done 2026-11-11; accepted in `decisions.md`)
**Outputs:** `sch/out/summary_p271c.txt`; `step2/run_step2.py` + `run_wake_bank_bypass.py`; `sch/vco_bank.sch` + exports; `range.json`; `summary_steps.txt`; `step3/out/summary_8bit_range.txt`, `summary_spot_steps.txt`; D22 `ampcal/out/summary_search_p271c.txt`; landing `summary_land_p271c.txt`.  
**Pass / finding:**
- Bank bypass W = max(0.15 µm, 5 µm × 2^(k−7)); wake ≥ 3800 τ in 1 µs — PASS.
- tt carries 0.97–1.02×; steps ≤ 0.296 V — **accepted** (inside D20 0.23–0.30 V).
- 15-corner PASS (top margin 140 MHz, bottom 77 MHz); D22 PASS.
- ss85 127→128 ratio 1.52 held for the P2.7.2 D20 landing gate.

### P2.7.2 — Layout: VCO (inductor + core + bank + var + bypasses + amp-cal)
**Status: FINDING (placement d4284fc). Split a/b/c. P2.7.2a recorded; P2.7.2a2 stop (bank_unit + Q).**

#### P2.7.2 layout (2026-11-12) — placement FINDING
**Outputs:** `analog/vco/layout/` — `build_vco_layout.py`, `out/vco_top.gds.gz`,
`summary_layout_build.txt`, `summary_drc_lvs.txt`, `summary_drc_waivers.txt`,
PNG/SVG (top/core/bank/inductor), KLayout LVS extract + logs.
- Outline **0.4457 mm²** [SCH layout]. Placement-only — **not** accepted for PEX
  (`decisions.md`). Density fill waived at block level; TV2.a **not** waived
  (fix via arrays in 2a). Cnt.b / M1.b / M5.b → routed respin.

#### P2.7.2a (2026-11-12) — LVS flow, hierarchy, inductor vias, area
**Outputs:** `analog/vco/sch/` hierarchical `vco_top.sch` + `out/summary_hier_equiv.txt`;
`analog/vco/layout/p272a/` proof cells + `out/summary_lvs_proof.txt`,
`out/summary_area_plan.txt`; tapped inductor via-array GDS + net/R check.
- **Hierarchy:** `vco_top.sch` instantiates l2n0, vco_core, vco_bank, vco_var,
  vco_tail_dac, ampcal_det. Equivalence vs flat: bank/core/var/L match; explained
  diffs = D22 tail vs step2 stand-in, ampcal present, no CML buffer [SCH].
- **LVS flow (a):** PDK netgen + KLayout. **dac_unit** MOS flow accepted; **bank_unit**
  FAIL. Inductor TV2.a arrays DRC-clean; EM ΔL PASS / ΔQ −3.3…−3.8 % (one run).
- **Area:** compact **0.22–0.28 mm²** [HAND] vs old D23 0.15–0.20 → **D23 amended**
  to VCO island **≤ 0.30 mm²** (`decisions.md` 2026-11-12 — P2.7.2a result). Tank not
  redesigned. Die tally §8 updated; still fits ≈ 2.5 × 2.5 mm with pad ring.

#### P2.7.2a2 (2026-11-12) — proof cells clean, Q confirm, area tally
**Outputs:** `analog/vco/layout/p272a/build_lvs_proof_cells.py`, `run_lvs_proof.py`,
`out/summary_lvs_proof.txt`; `spec/p27-floorplan.md` §8; this note; `phase2-plan` §3.
- **dac_unit PASS:** DRC clean (density waived); KLayout LVS PASS; netgen “Circuits
  match uniquely.” Extract: 2× PMOS W/L match, bulk=vdd. Gate Cont on upward poly pad
  above real Activ top; xraw exits sideways below pad band [SCH layout].
- **bank_unit FAIL (a2):** DRC non-density M1.b / M2.a / TM1.*; extract merged `bb|g`.
  Causes recorded for a3 (Cont-on-L=0.13, M1 across S/D, finger W clamp).
- **Inductor Q:** mesh1 not finished in a2; ΔQ −3.3…−3.8 % unconfirmed then.
- **Area:** §8 re-totalled; die ≈ 3.6–3.7 mm² fits 2.5 × 2.5 mm + pad ring.

#### P2.7.2a3 (2026-11-12) — bank_unit clean + inductor Q gate
**Outputs:** `build_lvs_proof_cells.py` (a3 rewrite), `out/summary_lvs_proof.txt`,
`out/q_gate/summary_q_gate.txt`, `sim/em/.../em_summary_p272a2_mesh1.md`; this note;
`phase2-plan` §3; `decisions.md` a3 result.
- **bank_unit PASS:** DRC non-density none (density waived); KLayout LVS PASS; netgen
  “Circuits match uniquely.” Extract: NMOS W=10.32 (ng=2), 2×0.15 bypass, 2×rhigh,
  2×cmim; pins bb/g/gnd/tn/tp/vbp separate [SCH layout]. Fixes: ng=2 + poly gate strap;
  Cont off Activ; M2 side-spur outer join; 1×1 via_stack; rhigh/MIM on outboard M2;
  TM1 ≥ 1.70 µm (TM1.a).
- **Inductor Q gate:** mesh1 finished [EM]: L≈1.69 nH; Q 13.70/14.74/16.31 at
  3.1/3.5/4.2 GHz; ΔQ −3.54/−3.63/−3.49 % vs tapped (worst −3.63 % ≥ 2 %). No wider-via
  EM this run. Swing ff/cap_wcs/85 °C I_tail=4 mA: **0.6435 V** ≥ 0.54 → PASS [SCH].
  Worst-corner VACASK PSS/pnoise **did not converge** (several settings) [SCH tool].
  Leeson ΔL from ΔQ ≈ 0.32 dB [HAND]; prior ss85 4.20 margin +3.6 dB → est. **+3.28 dB**
  [HAND]. Formal SCH PN gate left for owner decision.
- **P2.7.2a finished**; Q gate accepted in `decisions.md` (2026-11-12 — P2.7.2a3 result,
  inductor Q gate). Next was **P2.7.2b**.

#### P2.7.2b (2026-11-12) — first routed sub-block (core + tank) STOP
**Outputs:** `analog/vco/layout/p272b/` — `build_core_tank.py`, `run_drc_lvs.py`,
`out/vco_core_tank.gds.gz`, PNG/SVG, DRC/LVS/netgen logs, `summary_drc_lvs.txt`,
`summary_rc_tank.txt`, `summary_build.txt`.
- **Cell:** via-fixed `L_2n0_tapped` + XC pair (W=32 ng=8, mirrored) + 2× rfcmim 16×16 +
  rfx + CT≡vdd TM1 strap; ports tp/tn/tail/ct/vdd/gnd. Keep-out 30 µm [HAND]. Area
  **0.107 mm² ≈ 36 %** of ≤ 0.30 mm² island [SCH layout].
- **EM dens [HAND]:** TM1 tank 4 µm → J=1.0 mA/µm; CT 8 µm → 0.50 (open PDK has no EM
  table; HAND limit TM1 ≈ 5 mA/µm).
- **Pass criteria: FAIL.** DRC non-density M1.b / M2.b / V1.a (density waived). KLayout
  LVS FAIL; netgen FAIL. Extract: `gnd` and `tail` separate; **`tn|tp` still merged**;
  pair seen as one W=64 device. Root causes hit this run: PCell psub GR M1 shorting S/D;
  MIM TM1 overlapping CT; gnd rail crossing drain M1; gate M1 jog crossing drain spur.
  End dummies deferred (bridged gnd→tank).
- **RC report only [HAND]:** C_add/side ≈ 15–25 fF; Rs pair→L ≈ 0.2 Ω; no spare-bank flag
  vs §2. Formal PEX deferred to P2.7.3 after LVS-clean.
- **Next:** re-spin core+tank routing until DRC+LVS+properties PASS, **or** owner accepts
  partial and continues to D24 bank sub-block with this as FINDING.

#### P2.7.2 lin (2026-11-12) — gate **accepted** (`decisions.md`)
ss 0.897 V VHF spur **−102.9 dBc** [MODEL] accepted (7.9 dB inside −95); margin
target −105 retired. Post-layout re-check target ≤ −100 dBc at that point.

#### Prior gates (reference)
- P2.7.2c PASS (VR_ANA1 pads). P2.7.2b D24 landing failed before pad re-run.
- Binary-bank P2.7.2 gate (2026-11-11) superseded by D24 + 2c.

### P2.7.3 — PEX + post-layout VCO range / steps / PN bounds
**Inputs:** P2.7.2 PEX.  
**Outputs:** `out/summary_pex_vco_range.txt`, `summary_pex_vco_pn.txt`.  
**Pass:**
- Range covers **3.12–4.20 GHz** at corners (same ends method as `summary_8bit_range` / real-load); band steps even at carries.
- PN: bank-omitted PEX pnoise + bank-switch bound (≤ +0.59 dB tt) + detector `[HAND]` + CML `[HAND]` ≤ +0.5 dB → still meet **−116 / −115 dBc/Hz @ 1 MHz** and duplex totals; ss85 worst margin stays **> 0** (today ≈ +3.3 dB SCH).
**Re-run:** noiseless range grid; bank-omitted PSS/pnoise at tt 3.65 and ss85 4.20.

### P2.7.4 — xschem + layout: LO buffer, CML ÷2/÷3, converter, TSPC/Johnson
**Inputs:** `analog/lo/step3/`; floorplan.  
**Outputs:** sch + gds.gz + DRC/LVS + renders; `out/summary_xsch_lo.txt`.  
**Pass:** equivalence to LO decks; DRC/LVS clean; D15 enable pins present.  
**Re-run after PEX (same or next run if short):** corner divide (tt/ss/ff, −40/27/85); phase error ≤ 0.46° (P2.4); LO current with VCO inside D7 ≤ 10 mA typ.

### P2.7.5 — xschem + layout: PFD, CP, bias, hold, window delay, V_tune monitors, loop filter
**Inputs:** `analog/pll/step2|step4`, `vtune_mon/`; D19 values.  
**Outputs:** sch + gds.gz + DRC/LVS; LF MOS area ≈ 0.062 mm².  
**Pass:** equivalence; DRC/LVS; monitors thresholds ≈ 0.30 / 0.90 V per D20 design.  
**Re-run (PEX):** CP match / leakage vs step-2/3 limits; hold τ and leakage; monitor offset MC summary vs existing.

### P2.7.6 — EM: LO routing (VCO–buffer–divider)
**Inputs:** placed metals from P2.7.2–4.  
**Outputs:** openEMS or Palace S-params (same stack pin as tapped L2n0); `out/summary_lo_route_em.txt`.  
**Pass:** insertion / imbalance do not break CML ≥ 0.5 V/side at ss; document Δ vs schematic C load.  
**Re-run:** LO corner smoke with EM-fitted parasitics if Δ material.

### P2.7.7 — Integer-boundary coupling check
**Inputs:** full synth metals; CP and digital aggressors.  
**Outputs:** `out/summary_ib_coupling.txt` — method: EM or extracted capacitive/ inductive transfer from aggressor nets (CP UP/DN, div CMOS edges, AFE clocks) to tank / V_tune; convert to raw spur dBc at VCO `[HAND]`/`[EM]`.  
**Pass:** raw ≤ **−35 dBc** (VHF) / **−15 dBc** (UHF) at VCO before the loop (`pll-topology` §13 step 4).  
**If fail:** finding + spacing/shield proposal; stop for owner.

### P2.7.8 — Top assembly: synthesizer + AFE abutment; DRC/LVS/PEX
**Inputs:** all block GDS; AFE digital LEF/GDS from D3 place (or abstract).  
**Outputs:** `synth_top.gds.gz`; top DRC/LVS; PEX; renders.  
**Pass:** top DRC/LVS (with documented waivers); supply splits per D21; local GHz caps present.

### P2.7.9 — Post-layout system checks
**Inputs:** top PEX / behavioural wrappers.  
**Outputs:** `out/summary_pex_pll_smoke.txt`, `summary_pex_uhf_floor.txt`, `summary_pex_duplex_pn.txt`.  
**Pass:**
- PLL closed-loop smoke locks (as P2.6 step 3 polarity/levels);
- UHF LO floor ≤ **−150 dBc/Hz** (same method as `run_uhf_floor.py`, or documented successor);
- Duplex PN totals still ≥ **−136 dBc/Hz** with PEX VCO + bounds + LO floor.
**Re-run:** p26s3-style smoke; UHF floor; model PN with updated VCO/LO numbers.

### P2.7.10 — Phase 2 review gate package
**Inputs:** all summaries, GDS, sch exports, EM, decisions.  
**Outputs:** `reports/phase2-review/p27-result-review.md` (one-page owner summary + links).  
**Pass:** owner accepts Phase 2; unlocks Phases 3–5 topology memos.

---

## Layout scope (from `spec/phase2-plan.md`)

VCO, dividers and PLL in KLayout (Magic optional); DRC/LVS; PEX; tapped L2n0 EM **done**; LO routing EM; integer-boundary coupling target; top synth assembly; Phase 2 gate. Every schematic: xschem `.sch` with SVG/PDF; layouts `.gds.gz` with reports and rendered pictures.
