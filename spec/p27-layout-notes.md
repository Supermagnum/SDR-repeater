# P2.7 layout notes

Status: **D23 ≤ 0.38 mm² final.** **tail_block join PASS** (0.0950 mm² [GDS]). **Island outline 0.3906 > 0.38** — finding (die-level gate at P2.7.2c). **P2.7.2b varactor join PASS** (M1.b = SVaricap PCell waived); strip area 0.0066 > 0.0062 (width OK; under full pocket 0.0187). **D22:** hold_caps + det_sf_pair PASS; cmp_se LVS/netgen PASS, DRC M2.b open; bias/join Found, not done.

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

#### P2.7.2b (2026-11-12) — first routed sub-block (core + tank) **PASS** (re-spin 2)
**Outputs:** `analog/vco/layout/p272b/` — first-attempt `build_core_tank.py` /
`run_drc_lvs.py`; re-spin `build_pair.py`, `build_assemble.py`, runners;
`compare_fab_lvs_gds.py`; `out/vco_xc_pair.gds.gz`, `out/vco_core_tank{,_b,_c,_d}.gds.gz`,
PNG/SVG, DRC/LVS/netgen logs, `summary_assemble_*_PASS.txt`, `summary_rc_tank.txt`,
`summary_fab_lvs_gds_diff.txt`.
- **First attempt:** DRC/LVS FAIL; `tn|tp` merge; W=64. Causes: PCell psub GR; MIM∩CT;
  gnd×drain; gate jog×drain; S/D column polarity wrong (even=D not S).
- **Re-spin (bottom-up):**
  - **Pair cell `vco_xc_pair`:** DRC PASS (density none); KLayout LVS PASS; netgen PASS.
    even M1 cols = drain, odd = source [LVS]; M2 join for S/D (no M1 across array);
    end dummies W=4×2 → W=8 combined; gates poly-strapped (bank_unit). Two W=32 devices;
    tn, tp, tail, gnd separate.
  - **Stage a (L2n0 + CT):** DRC PASS; KLayout LVS PASS; netgen PASS. Area 0.093 mm².
    Inductor: fab GDS keeps `l2n0_em` spiral; LVS uses pin-only `l2n0` (spiral vias on
    133/134 DC-short LA–CT–LB in the LVS stack).
  - **Stage b (fixed MIM + rfx) — re-spin 1 FAIL:** MINUS|TIE|gnd; root cause found in
    re-spin 2: `rfcmim` PCell has a **solid M1 shield** over the full bbox (= TIE/gnd via
    Cont/Activ). Any M5→M1 via on MINUS shorts fx to TIE [PDK geometry].
  - **Re-spin 2 (2026-11-12):** keep schematic `rfcmim` (not cmim). Route MINUS→fx on
    **M2** (via_stack M5→M2), drop M2→M1 only south of the shield; TIE outboard to gnd;
    rhigh top=fx, bottom=gnd + ptap. PLUS Y = origin+8 (pin centre). Stages **b, c, d:**
    DRC PASS (density none); KLayout LVS PASS; netgen “Circuits match uniquely”
    (property noise: extract A/P/ps vs sch; `ct` disconnected — same as stage a) [TOOL].
    Netgen rewrite: `rfcmim`→`cap_rfcmim`, C/R→X for 3-terminal devices [PDK].
  - **Assembled area (stage d):** **0.1102 mm² ≈ 36.7 %** of ≤ 0.30 mm² [GDS].
- **Inductor LVS:** PDK deck recognises inductor2/3 with IND markers; L2n0 EM has none →
  pin-only LVS GDS. `compare_fab_lvs_gds.py` PASS: fab vs LVS differ only by `l2n0_em` [TOOL].
- **ng:** not in extract; layout `ng=8`, W=32 matches sch; finger count checked in
  `build_pair.py` [LAYOUT] (decision accepted).
- **EM dens [HAND]:** `SG13G2_os_process_spec.pdf` strings — no mA/µm table [DS miss].
  HAND limits M1–M5 ≈ 1.0 mA/µm, TM1 ≈ 5; tank 4 µm → J=1.0; CT 8 µm → 0.50 at 4 mA.
- **RC report (routing changed) [HAND]:** C_add/side ≈ 15–30 fF; Rs pair→L ≈ 0.2–0.4 Ω;
  no spare-bank flag. See `out/summary_rc_tank.txt`.
- **Next:** was D24 bank (done below).

#### P2.7.2b D24 bank (2026-11-12) — **PASS** (stages a–d)
**Outputs:** `analog/vco/layout/p272b_bank/` — `build_cells.py`, `run_drc_lvs.py`,
`cell_sizes.json`; `out/bank_cell_b{0..4}.gds.gz`, `bank_cell_u*.gds.gz`,
`vco_bank.gds.gz`, PNG/SVG, DRC/LVS/netgen per stage, `summary_rc_bank.txt`.
- **Architecture [SCH]:** 5 binary + 7 thermo (32 LSB); bypass
  W=max(0.15, 5·2^(k−7)) µm; 3→7 decoder in AFE RTL → bank pins g0–g11 / bb*.
- **Centroid order:** thermo [0,1,2,D,3,4,5,6] in 2×4; binary row south.
- **Stage a–d (first pass):** DRC/LVS/netgen PASS; area 0.1509 mm²; ng_req=123
  clamped to ng_lay=100 [TOOL].
- **Bank fix (2026-11-12) — PASS:**
  - Area forecast [HAND/TOOL]: remaining blocks ≈ 0.028 mm² vs 0.038 free →
    **fits** (no D23). See `out/summary_area_forecast.txt`.
  - Finger: sch + step2 + layout **ng=100** at W=308.58 (not split); poly-count
    script PASS (`out/summary_finger_check.txt`).
  - Band range [SCH]: least-margin corners still cover (top +130 MHz, bottom
    +76 MHz) — `step3/out/summary_bank_ng100_range.txt`.
  - Dummy in slot D: unit cell, all pins → gnd on M3 east corridor (vias outside
    cell); sch `xbdum*` / `msdum` in `vco_bank.sch`. DRC + KLayout LVS + netgen
    PASS on `bank_cell_dummy` and `vco_bank` (density waived; property noise).
  - Denser pack: gap_x=2, gap_y=5.5, corridor=4; pitch 134.5×90.8 µm; area
    **0.1514 mm²**; with core 0.1102 → **0.2616 mm²** [GDS].
- **RC [SCH/HAND]:** boundary step 8.58 fF ≈ 0.69 LSB (P2.7.3 flag); wiring
  ~20–40 fF/side. See `out/summary_rc_bank.txt`.
- **Next:** was tail / DAC / OTA — blocked on D9 (below).

#### P2.7.2b D9 / tail gate (2026-11-12) — **FINDING** (no layout)
- Area: ideal `cbf` 50 pF as MIM → island ≈ 0.316 mm² > 0.30 [PDK/TOOL]. Thin-ox
  `moscap_n` 5×30/30 µm fits (~0.279) but VCO ΔL **+0.516 dB @ 100 kHz** vs ideal
  (pass < 0.2 dB) [SCH]. Schematic unchanged; no tail GDS.
- Outputs: `analog/vco/layout/p272b_tail/out/summary_area_d9.txt`,
  `summary_d9_mos_vs_mim.txt`, `summary_d9_finding.txt`; `decisions.md` finding;
  floorplan §8 optional raise to 0.34 mm².
- **Next:** owner decision on D9 options A–D; then resume tail / DAC / OTA.

#### P2.7.2b DAC array — routing plan (2026-11-13) [PDK / HAND]

Recorded before redraw (`decisions.md` “P2.7.2b DAC array”). Compact 0.0064 mm² kept as
area target class; LVS shorts fixed by opening pitch within ≤ 0.015 mm² and one direction
per metal.

**PDK channel (SG13G2 tech defaults) [PDK]:**
| Rule | Value |
|---|---|
| M1 width / space | 0.16 / 0.18 µm |
| Mn (M2/M3) width / space | 0.20 / 0.21 µm |
| Via1 width / space | 0.19 / 0.22 µm |
| Track used | width 0.40 µm, pitch 0.90 µm (0.40 + 0.50 margin) |

**Layer directions (strict):**
| Layer | Direction | Nets |
|---|---|---|
| M1 | local only | unit straps, pins, NW tap |
| M2 | horizontal only | vdd spine; xraw spine; pbias track; one track per code (`base`, b0..b4, `D`) above the array |
| M3 | vertical only | drops from each pin’s **lane X** up/down to its M2 track |

**Why lane X:** unit `code` pins share the same X in a column. A raw M3 riser at pin X
merges every bit in that column. Each cell jogs on M2 inside a right-hand **lane
channel** to a per-bit lane X (lanes stay inside the cell pitch so neighbours do not
overlap), then M3 rises only on that lane.

**Pitch / area forecast [HAND] → measured [GDS]:**
- Unit bbox 5.20 × 6.17 µm (no per-cell GR) [GDS].
- Lane channel = 7 × 0.90 = 6.30 µm.
- `pitch_x` = 12.50 µm; `pitch_y` = 8.17 µm [GDS].
- Full array (all codes) bbox area **0.0068 mm²** ≤ 0.015 [GDS].

**Build order (LVS after each) — DONE 2026-11-13 [TOOL]:**
(a) vdd + pbias + xraw, all codes on `code_gnd` — DRC/LVS/netgen PASS;
(b) b0 → b4 → D one bit at a time — each step PASS;
(c) full `all` — DRC clean (density waived), KLayout LVS PASS, netgen PASS;
    55 nets match schematic (51× xd + vdd/pbias/xraw/code_*).

**Fixes recorded during prove:**
- Via centre = via_stack origin (not −0.2 offset) so bus vias land on M2 tracks.
- xraw M2 spine below outer GR (abb.bottom−4); pin M1 on GR shorted xraw→vdd [LVS].
- NW fill under array so PMOS bulks merge to GR→vdd (else 51 floating bulks) [LVS].
- Array unit instances: no m1pin/m1txt (unit pin texts became top ports) [LVS].
- No second Via1 on unit xraw pin (V1.b vs unit via) [DRC].
Centroid order and edge dummy kept.

#### P2.7.2b OTA / d9_rc / cbf (2026-11-13) — cells PASS; join STOP
**Outputs:** `analog/vco/layout/p272b_tail/` — `ota_vds`, `d9_rc`, `cbf`, `tail_block`
GDS.gz / PNG / SVG / DRC / KLayout LVS / netgen; `check_fingers.py`; this note;
`decisions.md` “d9_rc / cbf done; join + island gate”.

**KLayout LVS vs netgen disagreement (d9_rc WIP, cause recorded) [TOOL]:**
- Prove script uses `--ignore_top_ports_mismatch`. When the bypass gate Cont missed the
  poly strap (0.10 µm gap) and gnd pin M1 did not touch the ptap, extract had ports
  `nb,nbf` only, gate `$8`, bulk on `nb`. KLayout still reported PASS (ignored missing
  ports). Netgen compared full circuits (4 nets vs 3) and failed pin matching.
- Rule kept: cell fails until both pass and the cause is recorded. After the Cont/gnd
  fixes both PASS. Same flags remain on the prove script for consistency with bank/core.

**Netgen audit (accepted cells) [TOOL]:**
| cell | netgen |
|---|---|
| dac_unit, dac_array, tail_mt, ota_vds, d9_rc, cbf | Circuits match uniquely |

**d9_rc PASS:** 0.0039 mm²; ports nb, nbf, en_vco_bias_bp, gnd; mbp ng=4 [GDS/TOOL].
**cbf (rfcmim 16×) rejected for area** (`decisions.md` 2026-11-14): 0.0574 mm²;
breakdown MIM 0.0333 + ring/shield 0.0185 + empty 0.0056 ≈ +72 % over MIM [GDS].

#### P2.7.2b compact cmim cbf + join (2026-11-14)
**cmim PN/swing gate PASS [SCH]:** 7× side 69.007 µm (Cmax 8 pF → side_max 73.03 µm
[PDK]); ΔL −0.011 / 0.000 dB @ 100 kHz / 1 MHz; swing +0.02 % vs ideal
(`out/summary_cmim_vs_ideal.txt`). Parallel 7× tiles (PSS on single size not required).
**cbf layout PASS [TOOL/GDS]:** 7× cmim, pitch 70.14 µm (M5 abut, same-net gnd), one
ptap GR; PLUS=nbf (TM1), MINUS=gnd (M5); area **0.0431 mm²**; DRC clean (density
waived); KLayout LVS PASS; netgen PASS (`w=l=68.94u m=7` extract-rounded). Sch /
vacask re-netlisted to 7× `cap_cmim` [SCH].
**tail_block join PASS [TOOL] (2026-11-14):** see join section below. Join bbox
**0.2352 mm²** [GDS].
**Island sum [GDS]:** 0.1102+0.1514+0.0073+0.0058+0.0017+0.0039+0.0431 = **0.3234 mm²**
(laid-out cells only). Forecast varactor+D22+top ≈ **0.017 mm²** [HAND] → **≈ 0.340 mm²**,
at the ≤ 0.34 limit (not 0.0166 headroom). ≤ 0.36 not opened yet.

#### P2.7.2b join layer-usage map + routing plan (2026-11-14) [GDS]
Source: `analog/vco/layout/p272b_tail/out/summary_join_layer_map.json`.

| Cell | Metals/vias present (area order) | Free over cell bbox |
|---|---|---|
| dac_array | M1, M2, M3 (heavy); Via3/Via4 | M4, M5, TM1 (go around or jump on M4+) |
| tail_mt | M1 full; M2 south strip only; Via4 | M3+ over device body; avoid south M2 band |
| ota_vds | M1, M2; Via4 | M3+ |
| d9_rc | M1, M2 (tall); Via4 | M3+ |
| cbf | M1 (GR); M5 + TM1 plates; tiny M2–M4 in via stacks | **No** signal over plates — route **around** bbox |

**Rule:** never run inter-cell straps on a layer a child already uses inside that
child’s bbox. Pin escape: short M1 to via → up to the free layer → corridor → down.

**Channels [HAND]:** west (x < all cells), east (x > all cells), south (y < all),
sky north of cbf / along d9 top. Power stays on **M2 in corridors only** (power-only
already kept gnd≠vdd). Signals on **M3 in corridors**; any hop **over dac** uses
**M4** (dac owns M3). cbf nbf stays TM1 at the pin, via down to M3/M4 only at the
east/south edge outside the plate array.

**Prove order:** power → tail → filter(nbf) → nb → xraw → bypass → codes; DRC+LVS
after each; stop at first port merge.

#### P2.7.2b tail_block join PASS (2026-11-14) [GDS/TOOL]
Incremental join with layer-map corridors (`build_cells.py` `--nets`).
**Causes fixed [LVS/DRC]:**
- `gnd|tail`: M1 ox=−2 and M2 south through `tail_mt` hit drain finger / drain M2
  bar → via at pin, M2 west in rail gap then corridor.
- `gnd|nb|vdd` / M1.b: M1 jogs through ota/d9 → via at pins / M2–M3 on real metal only.
- `nb|xraw`: M3 at out_via Y crossed xref pad → nb south corridor first.
- Floating xraw / +1 net: vias placed on empty metal → vias on real M1/M2 strips.
- `d1≡vdd` (even at power+tail): M2 vdd strap through ota hit d1 ring at y≈23.3 →
  ota vdd on **M3 over cell** to east corridor.
- Codes: pbias north jog crossed code bus; stub–pin M1 gap → M1.b.
**Pass [TOOL]:** DRC clean (density waived); KLayout LVS PASS; netgen “Circuits match
uniquely” (69 nets); ports 17 top-level only (no child pin texts); property noise =
missing as/ad/ps/pd/area/b (same class as child proves). Tail port present.
**Area:** join bbox **0.2352 mm²** [GDS]; island cells **0.3234** + forecast **0.017**
→ **≈ 0.340 / 0.34** [GDS/HAND] under **cell-sum** accounting (superseded for the
island gate by the footprint method below).
Artifacts: `analog/vco/layout/p272b_tail/out/tail_block.gds.gz`,
`summary_join_step_full.txt`, `summary_join_layer_map.*`.

#### P2.7.2b island footprint reconciliation + D23 finding (2026-11-14) [GDS/HAND]
**Method:** island = sum of placed block footprints + forecast (not cell area sums).
Prior join bbox **0.2352** → owner chose reshape (not raise to 0.52).

#### P2.7.2b reshape + island stop (2026-11-14) [GDS/TOOL]
**Cells PASS:** `d9_rc` serpentine b=16 (R 962880→998699 [PDK]); `tail_mt` 2×2 of
120u/4u ng=24; `cbf` 3×3 cmim; DRC/LVS/netgen (+ fingers) each [TOOL].
**Floorplan [HAND]:** dac|ota|d9 south; mt; cbf. Place-only join **0.0805 mm²** [GDS].

| Block | Footprint (mm²) | Source |
|---|---|---|
| core + tank | **0.1102** | [GDS] |
| bank | **0.1514** | [GDS] |
| tail place-only | **0.0805** | [GDS] |
| forecast var+D22+top | **≈ 0.017** | [HAND] |
| **Island sum** | **≈ 0.359** | at ≤ 0.36 |
| with power corridors | join ≈ 0.091 → island ≈ **0.370** | **> 0.36** |

**Join:** power+tail intermediate ports clean; filter merges `nbf|gnd|vdd` — full join
not finished. **Stop for owner** (`out/summary_reshape_stop.txt`). Varactor not started.

#### P2.7.2b filter merge fix + full join + island outline (2026-11-14) [GDS/TOOL]
**Filter-node merge cause [PDK/LVS]:** cmim stack is M5 bottom plate (gnd) / TopVia1 /
TopMetal1 top plate (nbf). Prior join routed nbf on M2/via over the cbf block and its
ring, shorting nbf|gnd; ota vdd M2 at y≈21 crossed d9 nbf; dac vdd via landed in M2
rails → pbias|vdd. Fix: nbf escapes on TM1 north / M3 east only (no filter metal on
M5 or below over cbf); ota vdd via alley on M2; dac vdd on M1 north of M2 rails then
via. Recorded in join build (`build_cells.py`) and prove logs.

**Full join PASS [TOOL]:** DRC clean (density waived); KLayout LVS PASS; netgen
“Circuits match uniquely” (69 nets); 17 top ports; no child pin texts. Spice rhigh
must carry extract props `l=21.285u ps=0.18u b=16 m=1` [TOOL] (PCell Calculate=l;
omitting `ps`/`b` fails KLayout LVS while netgen still matches). Footprint
**0.0950 mm²** [GDS] (`out/tail_block.gds.gz`, `summary_prove_join_full_lfix.txt`).

**Island outline GDS [GDS]:** `vco_island_outline` places core+tank, bank, tail_block
(blocks only; no inter-block routing) with reserved pocket for varactor / D22 / top
corridors. Compact pack: bank south; core|tail north (gap=0).

| Item | Area (mm²) | Source |
|---|---|---|
| core + tank | **0.1102** | [GDS] |
| bank | **0.1514** | [GDS] |
| tail_block join | **0.0950** | [GDS] |
| reserved pocket | **0.0187** (target 0.017) | [HAND/GDS] |
| cell-sum + forecast | **0.3737** | ≤ 0.38 |
| **island outline bbox** | **0.3906** | **> 0.38** [GDS] |

**Stop:** outline overrun **+0.0106 mm²** vs D23 final ≤ 0.38. Per decisions: finding
with numbers, not a further raise. Die-level gate at P2.7.2c (`decisions.md`
2026-11-14 island outline finding).
Artifacts: `out/vco_island_outline.gds.gz`, `summary_island_outline.txt`.

#### P2.7.2b varactor + bias (2026-11-14 / join 2026-11-16) [GDS/TOOL/SCH]
**d9_rc geometry [SCH/TOOL]:** xschem / netlists carry rhigh `w=0.5u l=21.285u b=16`
(extract). R check: prior reshape **998.7 kΩ** [PDK] stands (GDS unchanged);
extract-L CbResCalc 1.030 MΩ is a different path. Filter pole ≈ 3.19 kHz at prior R
[SCH/PDK]. KLayout LVS + netgen uniquely; no l/b delta. Summary:
`p272b_tail/out/summary_d9_r_resim.txt`.

**SVaricap LVS [TOOL]:** this PDK pin extracts `sg13_hv_svaricap` (ThickGateOx present);
netgen lists the device. #861 workaround not needed for recognition; #753 Nx still
unchecked by LVS — scripted Nx=10+10. M1.b on bare SVaricap PCell waived for
sv_pair / vco_var (density + this rule).

**Sub-cells** (`analog/vco/layout/p272b_var/`):

| cell | DRC (dens. + SVaricap M1.b waived) | KLayout | netgen | note |
|---|---|---|---|---|
| sv_pair | M1.b (PCell) | PASS | PASS | ports G1/G2/W |
| mim_couple | PASS | PASS | PASS | stacked for strip width |
| bias_r | PASS | PASS | PASS | 2M folded; l=42.095u |
| bypass_pair | PASS | PASS | PASS | ng=2 |
| vco_var join | M1.b (PCell) | PASS | PASS | M3/M4 spines; M1 gnd bus |

**Join routing [TOOL]:** M4 horizontals at per-net Y slots + M3 spines; gnd on M1
east bus. LVS spice exports G1/G2 (SVaricap-named nets) so netgen pin-matches.

**W = vt mapping [TOOL]:** extract/netgen port **W** is the SVaricap **well** pin
(schematic **vt** / V_tune). It is a net name, not the device width property.
Netgen property compare on `sg13_hv_svaricap` is incomplete (#753-class). Real
**w / l / Nx** are compared by script `p272b_var/check_svaricap_dims.py` →
`summary_svaricap_dims.txt` (intent `w=3.74u l=0.3u Nx=10` [SCH]).

**SVaricap M1.b — Phase 5 open item:** bare SVaricap PCell violates **M1.b** on
this PDK pin (`a49358cc`); waived at block level for sv_pair / vco_var only.
**Before any tape-out:** clear by a PDK fix or a documented foundry waiver.
No dedicated IHP issue for M1.b today; related closed [#639](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/639)
was NW.e (not M1.b). Do not file upstream unasked. Track with #753 / #861 class
workarounds in `reports/pdk-tool-issues-2026-10-30.md`.

**Footprint [GDS]:** hierarchical join **0.0066 mm²**, width **41.3 µm** — strip
area over by **0.0004 mm²** vs 0.0062 (accepted 2026-11-16); width YES; under full
pocket **0.0187 mm²**.
**C per side [PDK]:** rfcmim ≈ **684 fF**; SVaricap C(V) not PEX’d.
Artifacts: `p272b_var/out/*.gds.gz`, `summary_cap_footprint.txt`, `summary_build.txt`,
`summary_p272b_var_stop.txt`, `summary_svaricap_dims.txt`.

#### P2.7.2b D22 detector (2026-11-16) — in progress [GDS/TOOL]
`analog/vco/layout/p272b_det/`. Bottom-up:

| cell | DRC (dens. waived) | KLayout | netgen | note |
|---|---|---|---|---|
| hold_caps | PASS | PASS | PASS | 2× cmim 400 fF; w=16.27 µm [extract]; **0.0012 mm²** |
| det_sf_pair | PASS | PASS | PASS | 4× 0.5/0.13 ABBA + dummies; ct on M3; **0.0007 mm²** |
| cmp_se | M2.b×1 | PASS | PASS | rhigh l=6.96 µm [extract]; **0.0023 mm²** |
| bias_pd / ampcal_det | — | — | — | Found, not done |

**Tank load [HAND/PDK]:** one 0.5/0.13 gate per side → Cgg ≈ 0.5–1 fF ≪ 10 fF; no PEX.
**Forecast:** D22 ≈0.0013 [HAND] is already met by hold_caps alone; cmp_se exceeds it.
Remaining pocket after vco_var: **0.0121 mm²** [GDS]. Artifacts: `p272b_det/out/`,
`summary_p272b_det_stop.txt`, `summary_finger_check.txt`.

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
