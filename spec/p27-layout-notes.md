# P2.7 layout notes

Status: **plan written 2026-11-11; floorplan memo awaiting owner (proposed D23, `spec/p27-floorplan.md`).** No schematic capture and no layout in the planning run. **Tapped L2n0 EM done** 2026-11-01. Owner: P2.7 may begin with open IHP LVS issues #861, #753 and #512; document a workaround for each and re-check when the PDK pin moves (`decisions.md` 2026-10-31).

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

### P2.7.0 — Plan + floorplan (this run) ✅
**Inputs:** closed P2.3–P2.6; notes above.  
**Outputs:** this file; `spec/p27-floorplan.md`; `phase2-plan.md` §3 update.  
**Pass:** owner accepts floorplan (D23). **No layout.**

### P2.7.1 — xschem capture: VCO + amp-cal + LDO
**Inputs:** `analog/vco/step2|step3`, `ampcal/`, `ldo/`; tapped L2n0 symbol.  
**Outputs:** `xschem` trees under `analog/vco/sch/` (names TBD); SVG/PDF; equivalence `out/summary_xsch_vco.txt`.  
**Pass:** netlist match to simulated decks (core, bank, var, bypasses, D22, LDO); symbol pins match D21/D22 interface.  
**Re-run:** none (capture only).

### P2.7.2 — Layout: VCO (inductor + core + bank + var + bypasses + amp-cal)
**Inputs:** P2.7.1; floorplan D23; tapped GDS.  
**Outputs:** `vco*.gds.gz`; DRC/LVS reports; rendered PNG/SVG; checklist for #861/#753/#512.  
**Pass:** DRC clean (incl. maximal SVaricap `w=3.74u`); LVS clean **or** waived with written #861/#753/#512 notes; device count checklist signed.  
**Re-run:** none until PEX.

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
