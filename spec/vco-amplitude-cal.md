# VCO amplitude control (P2.3 open point §9.3)

Status: **D22 accepted 2026-11-02. Step 1 done 2026-11-11** (§10): end-to-end search on the single-ended comparator PASS; **interim A2 retired** for all bands. Calibration sets every band; bottom bands end at code 31 with tnr = 1.

Items 1–2 of `prompts/06-design-next-step.md` are closed (P2.6 accepted 2026-10-31; open points 1–3 closed). Newest status report `reports/status-2026-10-30.md`: no failed re-run; amplitude cal listed as open work, not as an unverified blocking result.

---

## 1. Limits

| Limit | Value | Source |
|---|---|---|
| Steady-state differential Amp (D22) | ≤ **1.40 V** | Owner 2026-11-11 |
| Transient Amp during amplitude search only | ≤ **1.50 V** (≈ 1 µs/step, cal only) | Owner 2026-11-11 |
| Upper: peak V_GS / V_GD of the LV core | ≤ **1.5 V** (process abs. max 1.65 V) | `[DS]` / step-3 gate in `summary_8bit_range.txt` |
| Peak V_GS vs differential amplitude | In the 15 corner cases, **peak V_GS = Amp** (to the reported precision) | `[SCH]` `summary_8bit_range.txt` |
| Lower: tank swing for the P2.4 LO chain | Buffer target **≥ 0.5 V per side** into CML (25 % over the ÷3 minimum 0.40 V at slow / 1.08 V) | `[SCH]` `spec/lo-divider-topology.md` §7 |
| Lower: pessimistic tank (ideal sine) that still divides | ss 125 °C: **< 0.25 V** per side; ss −40 °C needs **≈ 0.34–0.36 V** per side (fails at 0.27–0.29 V with a hot/fast swing substitute) | `[SCH]` §9 |
| Lower: VCO’s own bottom-band swing at 4 mA | Typical ≈ **0.41 V** per side (0.82 V diff.); lowest recorded **0.59 V** diff. (ff / MIM wcs / 85 °C) → **0.295 V** per side | `[SCH]` `summary_8bit_range.txt`, §9 |
| Phase noise vs amplitude | Worst recorded VCO margin **+3.6 dB** at 1 MHz, **ss / 85 °C / 4.20 GHz**, Amp **1.257 V**, I_tail **3.59 mA**; bank-omitted re-check **+3.4 dB** | `[SCH]` `summary_4ma.txt`, `summary_pn_nobank.txt` |
| 4 mA cap (D12) | Tail current **≤ 4.0 mA**; bottom of the range already at the cap | `[SCH]` / `decisions.md` |
| `VCO_BIAS` register | **0x2C**, reset **0x10**; **[4:0]**; **I_tail = 1.52 mA + code × 0.08 mA** (1.52–4.00 mA; D12 at code 31) | D22 / `spec/analog-digital-interface.md` §4 |

Design intent in the schematic scripts: target differential amplitude **A_TARGET = 1.3 V**, then `I_tail = min(4 mA, I0 · 1.3 / Amp)` `[SCH]` (`analog/vco/step2/run_step2.py`).

---

## 2. What a fixed current per band gives today

Per-band I_tail from the A_TARGET rule at typical, then held across corners `[SCH]` (`summary_8bit_range.txt`): top of range **3.41 mA**, bottom **4.00 mA** (at the D12 cap).

| Edge | Amp min … max (15 MOS×CAP×T cases) | Worst low | Worst high |
|---|---|---|---|
| Top (code 0, 3.41 mA) | **1.14 … 1.48 V** | ff / MIM wcs / 85 °C: 1.14 V | ss / MIM bcs / −40 °C: **1.48 V** (peak V_GS 1.48) |
| Bottom (code 255, 4.00 mA) | **0.59 … 1.04 V** | ff / MIM wcs / 85 °C: **0.59 V** | ss / MIM bcs / −40 °C: 1.04 V |

- **4 mA already reached** from about mid-band downward (step-2 table: codes 128 / 192 / 255 → 4.0 mA; code 0 → 3.4 mA) `[SCH]` `summary_8bit.txt`.
- **Temperature drift with a one-time setting** (same I_tail, tt / typ, −40 → 85 °C) `[SCH]`: top **1.42 → 1.25 V** (−0.17 V); bottom **0.94 → 0.73 V** (−0.21 V). Roughly **−1.3 to −1.7 mV/°C** `[HAND]` from those two points. After lock, a fixed `VCO_BIAS` does not track die temperature.
- Supply pushing moves amplitude with V_CT: tt 3.65 GHz Amp **1.136 → 1.196 V** for V_CT 1.05 → 1.15 V; ss85 4.20 GHz **1.216 → 1.295 V** `[SCH]` `summary_supply_push.txt`.
- Bottom-band **0.59 V** diff. ≈ **0.30 V** per side: above the ss-125 °C divider floor, near the ss −40 °C need if the cold slow corner saw a hot-fast swing; with the VCO’s own cold swing the chain passes `[SCH]` §9. Headroom is thin; raising Amp would need more than 4 mA (blocked by D12) or a higher-Q / lower-loss tank.

---

## 3. Options

### A — Per-band table (now)

| | |
|---|---|
| **Hardware** | Existing 5-bit `VCO_BIAS` DAC only. Host (or AFE ROM) writes one code per `VCO_BAND` / RF band. |
| **Holds against** | Frequency dependence of swing at **one** process/temperature (today: typical 27 °C). |
| **Cost / risk** | No new analogue area. Does **not** hold process or temperature: top Amp to **1.48 V** at cold/ss/bcs; bottom to **0.59 V** at hot/ff/wcs `[SCH]`. No detector PN. No wake-time cost. No tank loading. |
| **D9 filter / bypass** | Bias written before or with band; start-up bypass already settles the 1 MΩ / 50 pF tail filter in **1.00 µs** `[SCH]` (`spec/analog-digital-interface.md` §6). |
| **Wake / D20 / V_tune** | No change to 83–120 µs model wake `[MODEL]` (`spec/pll-topology.md` §13). Band cal unchanged. V_tune-monitor re-runs: host may rewrite `VCO_BIAS` with the new band; no extra search. |

### A2 — Per-band table, top bands derated for 1.5 V margin

Same as A, but top-band codes reduced so cold/ss peak V_GS stays ≤ **≈ 1.40 V** (100 mV margin) `[HAND]`.

| | |
|---|---|
| **Hardware** | Same DAC. Table built from the 15-case matrix (derate where Amp_top > 1.40 V). |
| **Holds against** | Upper reliability limit at cold corners, at the cost of less Amp (and some PN) at the top on typical/hot dice. |
| **Cost / risk** | Still no process/temp tracking after programming. Bottom edge unchanged (already at 4 mA). Derating top by ~0.08 V from 1.48 → 1.40 is ~5 % Amp → ~**0.4 dB** PN if Leeson-limited `[HAND]` — small vs +4 dB top-band margin at typical. |
| **Wake / ordering** | Same as A. |

### B — Per-corner table (process + temperature)

| | |
|---|---|
| **Hardware** | Same DAC. Needs a **process ID** (fuse / wafer sort bin) and a **temperature** input (on-chip sensor or host). Host or on-chip LUT: `VCO_BIAS(band, corner_bin, T)`. |
| **Holds against** | The 15 SCH corners if the binning matches; in-field T if the sensor is used. |
| **Cost / risk** | No detector PN / tank C. Large **host and test** cost; fuse map; sensor accuracy. Mismatch inside a bin still open. Not self-contained in the RFIC. |
| **Wake** | Table lookup only; wake unchanged. Re-run on V_tune flag: re-index table. |

### C — Peak detector + comparator + digital search over `VCO_BIAS`

| | |
|---|---|
| **Hardware** | RF peak (or envelope) detector on the tank or buffer input; comparator vs a reference; small FSM in the AFE block searches `VCO_BIAS[4:0]` (binary or linear), then **holds** the code. Optional: disable detector after lock. |
| **Holds against** | Process, temperature at calibration time, and supply (within the search). Drift after hold still follows T and V_CT unless re-run. |
| **Phase noise** | Detector/amplifier noise couples if the detector stays attached and biased during RX/TX. Mitigate: AC couple with small C, high series R, or power down after search `[HAND]` — not simulated here. |
| **Tank loading** | Extra C and possible nonlinear conductance. Budget against the 762 fF high-edge cap (`spec/vco-topology.md` §2); keep detector C ≪ buffer tap (buffer already ~100 fF/side) `[HAND]`. |
| **D9 filter / bypass** | Each DAC step must settle through 1 MΩ / 50 pF (**τ ≈ 50 µs**) unless `en_vco_bias_bp` is pulsed for each trial (same switch as wake, ≥ 6–7 τ of the **bypassed** path ≈ 11 ns) `[SCH]`. Proposal: pulse bypass ~0.2–0.5 µs per step, then open and sample. |
| **Wake budget** | Model wake today **83–120 µs** of **≤ 150 µs** `[MODEL]`. Headroom **≈ 30–67 µs**. A 5-bit binary search (5 trials) with ~1–2 µs settle each fits in **≈ 10 µs**; linear search worst 32 steps needs care. Must not push total wake over 150 µs. |
| **Ordering with D20** | **D22:** run the amplitude search **with** band calibration; **start-up bypass stays closed for the whole search**, then open and hold the code. Re-run on every band cal (wake, band change, V_tune-monitor). |
| **V_tune-monitor re-runs** | On `PLL_STATUS[4:5]`, re-run band cal **and** amplitude search (D22). |

### D — Continuous analogue amplitude loop

| | |
|---|---|
| **Hardware** | Peak detector + error amp into the tail bias (around or instead of the DAC), always closed. |
| **Holds against** | Continuous T and supply. |
| **Cost / risk** | Detector and loop noise become a **phase-noise** path (AM→PM on the tank; bias-node noise like an unfiltered tail). Conflicts with D9’s intentional slow bias filter unless the loop is very slow (then it barely beats a held search). Start-up and bypass interaction is messy. Highest analogue risk. |
| **Wake** | Loop must settle inside wake; a slow loop eats the 30–67 µs headroom. |

---

## 4. D22 — accepted 2026-11-02

Option **C** accepted (`decisions.md`), with the owner’s DAC offset and bottom-band flag. Rationale from the memo still holds: corner Amp spread under a fixed per-band current; avoid continuous loop noise (D) and host fuse maps (B).

| Item | Accepted |
|---|---|
| **Topology** | Peak detector + comparator **on the tank**; digital search over `VCO_BIAS`; **start-up bypass closed during the search**; code **held** in operation. Detector may be powered down after hold (step 1). |
| **When it runs** | With **every** band calibration: wake, band change, and V_tune-monitor flag. |
| **Target amplitude** | **1.25 V ± 0.10 V** differential. Hard upper limit **1.40 V**. |
| **DAC** | `VCO_BIAS[4:0]`: **I_tail = 1.52 mA + code × 0.08 mA** → **1.52–4.00 mA**; D12 cap at **code 31**. (Not code/31 × 4 mA.) |
| **Bottom bands** | If 4 mA still below target: end at code 31 and set **"target not reached"** — **expected, not a fault**; D12 unchanged. |
| **Register map** | Keep **0x2C** `[4:0]` as the DAC (host override when cal disabled / interim A2). Add status for busy / target-not-reached / clamp-high as needed when C is designed (`AMP_CTRL` sketch in the pre-acceptance proposal remains a starting point). |
| **Interim until C is designed** | **Option A2**: per-band table, top bands derated for margin to 1.5 V. Host writes `VCO_BIAS` with the band. |
| **Step-1 plan** | (1) Detector on the tank: topology and C_load budget. (2) Comparator reference for 1.25 V. (3) FSM with bypass **held closed** for the whole search; wake total vs 150 µs `[MODEL]`. (4) SCH Amp vs code (offset DAC) at tt and ss85 top/bottom. (5) pnoise detector off after hold vs on — gate ≤ 0.5 dB on worst margin. (6) Ordering with D20; re-run path on V_tune-monitor. Stop for review before detector layout. |

---

## 5. Not in this memo

- Real CML buffer load on the VCO (separate P2.3 item; `summary_pn_real_buf_cml.txt` PSS fails).
- HBT core comparison (D1).

---

## 6. Step 1 — plan (2026-11-02)

Work directory: `analog/vco/ampcal/`. Results `[SCH]` / `[RTL]` / `[MODEL]` in `out/summary_*.txt`.

1. **Detector choice.** Compare a source-follower peak hold (AC-coupled from the tank, ≤ 10 fF total) against a replica biased at V_CT, versus a MOS/diode rectifier into a hold cap. Pick one; state the reason. Reference for 1.25 V from the PLL bias generator (V_REF = 0.4 V, `spec/pll-topology.md` §12) with a resistor ratio. Comparator: continuous-time; offset Monte Carlo with the PDK mismatch used in P2.4/P2.5.
2. **Detector accuracy.** Drive or use the real VCO tank; report detector estimate vs true differential Amp over mos_tt/ss/ff × MIM typ/wcs/bcs × −40/27/85 °C, top (code 0) and bottom (code 255) bands. Gate: error ≤ **±0.10 V** at the 1.25 V target.
3. **DAC.** Replace the ideal `iref` with a 5-bit binary DAC: **I_tail = 1.52 mA + code × 0.08 mA** (mirror 1:8 as today). DC sweep codes 0–31 at tt/ss/ff; check monotonicity and absolute current.
4. **Search transient.** Five-bit SAR with **bypass closed** the whole time; top and bottom bands; same corner set. Report final Amp, code, time/step and total, “target not reached” at bottom; Amp ≤ **1.40 V** throughout.
5. **RTL.** Amplitude search in `bandcal.sv` / `afe_seq.sv`: mid-code amp SAR → band SAR → one amp touch-up; bypass held while cal busy. cocotb vs a VCO amplitude model. Register `VCO_BIAS`: [4:0] DAC, [7] manual, [5] target-not-reached.
6. **Wake.** Update `wake_timing.py` and `spec/pll-topology.md` §13; total ≤ 150 µs.
7. **PN.** Bank-omitted pnoise with detector attached (powered down after hold vs left on) at tt 3.65 and ss85 4.20 if PSS converges; else `[HAND]` bound.

---

## 7. Step 1 results (2026-11-02)

Sources: `analog/vco/ampcal/out/summary_*.txt`, `rtl/afe/bandcal.sv`, `afe_seq.sv`, `wake_timing.py`.

### Detector choice
**Source-follower peak hold + replica at V_CT**, AC-coupled **4 fF/side (8 fF ≤ 10 fF)**. Reason: coupling C sets tank load; replica cancels V_GS/CM; rectifier-on-tank rejected for nonlinear RF current `[HAND]`.

### Detector accuracy `[SCH]` — **MISS**
All 30 corner×band cases: |A_est − Amp| ≈ 0.56–1.19 V (A_est ≈ 0.03–0.23 V). Gate ±0.10 V at 1.25 V **not met**. Peak-hold / estimate path needs redesign (charge time, diode, or estimator). True tank Amp in the same runs still looks sane (top ≈ 1.05–1.34 V, bottom ≈ 0.59–1.04 V).

### Comparator offset
Stand-alone MC OP did not trip; **[HAND]** from PDK σV_T: 3σ ≈ 12 mV at Amp/2 → ≈ **23 mV** on Amp ≪ 0.10 V. **PASS** on paper.

### DAC `[SCH]`
| Check | Result |
|---|---|
| Ideal I_tail = 1.52 + code×0.08 mA through VCO mirror, tt/ss/ff, codes 0–31 | **PASS** (mono; |err| ≤ 4.5 %) |
| Transistor PMOS binary DAC | **FAIL** DNL (bit-weight trim needed); VCO decks use the ideal source until trimmed |

### Search `[SCH]` (tt / typ / 27 °C, bypass closed; settle 200 ns/step)
| band | code | Amp | tnr | Amp_peak ≤ 1.40 |
|---|---|---|---|---|
| top | 31 | 1.150 | 1 | PASS |
| bottom | 31 | 0.579 | 1 | PASS |

Bottom tnr expected. Top tnr with Amp 1.15 V: search cannot reach 1.25 V in this deck (detector load / short transient / bias) — **uncertain**, full corner matrix not run (blocked on detector). Step time ~0.2 µs electrical; wall ~20–110 s/step.

### RTL `[RTL]`
`bandcal`: amp SAR → band SAR → amp touch-up; `afe_seq.cal_busy` holds bypass. cocotb: amp+band ≈ **49.1 µs**; manual band-only 38.8 µs; afe_seq cal_busy test PASS.

### Wake `[MODEL]`
Amp cal +10.0 µs → wake **109–130 µs ≤ 150 µs** (`wake_timing.py`, `spec/pll-topology.md` §13). **PASS**.

### Detector PN
PSS with detector did not converge. **[HAND]**: powered down after hold → ΔL(1 MHz) ≈ **0 dB**; if left on < 0.05 dB.

### Register map
`VCO_BIAS`: [4:0] DAC, [5] target-not-reached, [7] manual (`spec/analog-digital-interface.md` §4).

---

## 8. Step 1b results (2026-11-02)

Sources: `analog/vco/ampcal/out/summary_diagnose.txt`, `summary_detector.txt`, `summary_dac.txt`, `summary_cmp_mc.txt`, `summary_search*.txt`.

### 8.1 Diagnosis of step-1 under-read `[SCH]`

tt / typ / 27 °C, top (bias 20) and bottom (bias 31):

| | top | bottom |
|---|---|---|
| Amp (true) | 1.282 V | 0.847 V |
| A_est (vhp+vhn−2·vhr) | 0.027 V | 0.000 V |
| vhp / vhn / vhr | 0.505 / 0.502 / 0.490 | ≈ 0.49 |
| sfp min/max | 0.123 / 0.910 | 0.227 / 0.764 |
| AC atten (gp/tp) | 0.744 | 0.743 |
| diode conduction fraction | 0.253 | 0.144 |

**Root cause: conduction-angle / diode-Vth loss not cancelled by the DC replica.** Hold ≈ sfp_max − Vth ≈ 0.51 V; replica hold floats at sfr (diode off, Vgs ≈ 0), so A_est ≈ Amp_sf − 2·Vth ≈ 0. Secondary: AC atten ≈ 0.74. Not bias-vs-hold-cap (no bleed on hold), not a formula mix-up, not a netlist error.

### 8.2 Redesign — differential max detector

- Two NMOS (W=0.5 µm L=0.13 µm) gates on tp/tn, shared source = hold; replica pair same size/bias, gates at CT.
- I_det = 4 µA, C_hold = 400 fF; settle ≪ 1 µs. Tank gate load ≈ 2×Cgg ≪ 10 fF `[HAND]`.
- A_est = 2·(V_hold − V_rep + V_LOSS); V_LOSS = **0.22 V** fixed design-time (tt/27 top: Vsense=0.419, Amp/2=0.642) `[SCH]`.
- Comparator threshold V_th = Amp_target/2 − V_LOSS = 0.405 V from the Amp/2 node.

### 8.3 Detector accuracy `[SCH]` — **PASS at Amp ≈ 1.25 V**

30 cases (mos_tt/ss/ff × MIM typ/wcs/bcs × −40/27/85 °C × top/bottom):

- Near-target (Amp 1.15–1.35 V): **10/10** with |err| ≤ 0.022 V (mean 0.011 V). Gate ±0.10 V: **PASS**.
- All 30: 23/30 within ±0.10 V. The 7 misses are bottom-band low-Amp cases (Amp ≲ 0.67 V) where fixed V_LOSS overestimates; outside the cal target.

### 8.4 Comparator offset MC `[SCH]` — **PASS**

N=40, trip on co−co2 = 0. σ = 3.89 mV at Amp/2 → Amp 3σ ≈ **23 mV** ≪ 0.10 V. (Single-ended cmp OP previously failed to trip; this run uses the diff-load zero.)

### 8.5 Unit-cell VCO_BIAS DAC `[SCH]`

P2.5-style: 10 µA master; offset 19 + bits 1/2/4/8/16 with `w=2·m`, `ng=m`; series PMOS switches L=0.13 µm (gate 0 = on). Into VCO 1:8 mirror → I_tail ≈ 1.52 mA + code×0.08 mA.

| Check | Result |
|---|---|
| Mono tt/ss/ff codes 0–31 | **PASS** |
| |DNL| ≤ 0.5 LSB | **PASS** (tt 0.35, ss …, ff 0.23 LSB) |
| INL | 1.7–2.3 LSB (Early / Vds compression at high codes) |
| |I_tail − ideal| at code 31 | −13 % (tt) … −18 % (ss) — absolute scale short of 4.0 mA |
| Mismatch MC N=20 full sweeps | mono PASS; worst |DNL| 0.39 LSB **PASS** |

VCO decks use this transistor DAC (not the ideal source). Cascode deferred.

### 8.6 Full corner search `[SCH]`

Tail **bypass only** closed during search. Bank/var bypass AC-grounds MIM/varactor plates and collapses Amp (tt code 20: 1.25 V → 0.94 V) — must stay open. SCH settle 0.20 µs/step (total 1.20 µs for 5 bits + final); RTL wake still budgets 1.00 µs/bit.

30 corner×band cases (`out/summary_search.txt`):

- **Amp ≤ 1.40 V throughout: PASS** (worst peak 1.351 V, ff/wcs/−40 top).
- **Top band:** final Amp 1.197–1.248 V; codes 12–31. Hot corners often end at code 31 with Amp still inside 1.25±0.10 (DAC absolute scale short of 4 mA).
- **Bottom band:** all end code 31, tnr=1, Amp 0.478–0.982 V — expected (D12 / DAC scale).
- tt/27 top: code **19**, Amp **1.243 V**, tnr=0. **Step-1 top tnr at 1.15 V was a detector artefact.**

### 8.7 Wake `[MODEL]`

No change. Amp cal remains +10.0 µs; wake **109–130 µs ≤ 150 µs** (`wake_timing.py`). SCH settle 0.20 µs fits inside the 1.00 µs RTL bit time.

---

## 9. Step 1c results (2026-11-11) — DAC scale, tail-only bypass, SE cmp

Sources: `analog/vco/ampcal/out/{dac,bottom,sar,cmp,pn,headroom}/`, `rtl/afe/{afe_seq,bandcal}.sv`, `wake_timing.py`.

### 9.1 DAC full-scale root cause and fix `[SCH]`

**Cause:** code 31 delivered 3.26–3.65 mA (INL ≈ 2 LSB) because the NMOS 1:8 mirror ran with **V(tail) ≈ 0.44–0.49 V** while the diode reference sat at V_GS — Early / V_DS mismatch. A cascode on the tail mirror was **rejected** (no headroom at V_tail ≈ 0.47 V).

**Fix:** **V_DS-matched reference** — OTA servos `nbf` so V(xref) ≈ V(tail_f); wide mr/mt (60 µm/12, 480 µm/96); I_master = 10.5 µA so units deliver ~10 µA into the low-V_DS node. Keeps `rbf`/`cbf`/`mbp_rbf` for D9 + bypass.

| Check | Result |
|---|---|
| code 31 = 4.0 mA ± 3 %, never > 4.0+3 %, tt/ss/ff × −40/27/85 | **PASS** (worst ss/85 −2.92 %; ff/−40 +2.77 %) |
| \|INL\| ≤ 1 LSB @ 27 °C | **PASS** (tt 0.23, ss 0.43, ff 0.13 LSB) |
| Mono + MC N=20 | **PASS** (worst \|DNL\| MC 0.46 LSB); ss major-carry \|DNL\| 0.84 NOTE |
| Headroom Amp / V(tail) @ code 20 | old 1.309 V / 0.461 V → new 1.374 V / 0.440 V — tail **lower**, Amp up `[SCH]` |

### 9.2 Bottom band @ code 31 vs LO min `[SCH]`

15 VCO corner×temp cases. LO min 0.54 V (ss/−40: 0.66 V) — `lo-divider-topology.md` §9.

- Amp 0.862–1.105 V; **worst margin +0.293 V** (ss/wcs/−40: Amp 0.953 vs 0.66). **PASS** vs LO.

### 9.3 Tail-only bypass during search `[RTL]` `[SCH]`

- `en_vco_bias_bp`: wake all-resistor bypass, **36 cycles only** (unchanged).
- `en_vco_tail_bp`: wake **or** `cal_busy` — tail filter only.
- Deck: `vbp` → bank/var; `vbp_tail` → `mbp_rbf`. Spec §6 + cocotb updated (2/2 PASS).

### 9.4 Full corner search `[SCH]`

30 cases, real V_DS-matched DAC, tail-only bypass (`out/sar/summary_search.txt`):

- **Top:** final Amp 1.202–1.270 V; codes 9–19; all tnr=0.
- **Bottom:** all code 31, tnr=1; Amp 0.852–1.089 V.
- tt/27 top: code **14**, Amp **1.251 V** (was 19 / 1.243 with short DAC).
- **Amp ≤ 1.40 throughout: FAIL** on 4 top cases (peak during SAR transient): tt/85 1.437; ss/wcs/85 1.448; ff/wcs/27 1.402; ff/bcs/85 1.416. Final Amp still inside 1.25±0.10. Settle 0.20 µs/step, 1.20 µs total `[SCH]`.

### 9.5 Comparator SE node `[SCH]`

First-stage `co` swings only ±70 mV around 1 V — inverter never tripped. **Second OTA** (vip=`co2`, vin=`co`) → `cmp`. MC N=40: SE and co−co2 Amp 3σ = **16 mV** ≪ 0.10 V **PASS**. Search SCH still uses `vsense > V_th`.

### 9.6 Detector PN `[SCH]` / `[HAND]`

Bank-omitted PSS at tt 3.65 and ss85 4.20 with detector off: **PSS aborted** both. `[HAND]` bound ΔL @ 1 MHz ≈ **0 dB** (powered down); gate ≤ 0.5 dB **PASS by [HAND]**.

### 9.7 Wake `[MODEL]`

Unchanged: **109–130 µs ≤ 150 µs**.

---

## 10. Step 1d — end-to-end on SE comparator; D22 step 1 closed (2026-11-11)

Sources: `analog/vco/ampcal/out/summary_search.txt` (1d), `amp_common.py` (CMP_HIGH=0.85 V).

**Path:** detector → second-stage SE `cmp` → digital SAR (`v(cmp) > 0.85`) → V_DS-matched DAC → VCO; `en_vco_tail_bp` closed during search.

### 30-case corner search `[SCH]` — **PASS**

| Gate | Result |
|---|---|
| Steady Amp ≤ 1.40 V | **PASS** (final Amp 0.852–1.292 V) |
| Transient peak ≤ 1.50 V | **PASS** (worst peak 1.447 V, ss/wcs/85 top) |
| Top tnr=0, Amp in 1.25±0.10 | **PASS** (codes 10–20; tt/27 code **14**, Amp **1.250 V**) |
| Bottom code 31, tnr=1 | **PASS** (expected; Amp above LO min) |
| Elec time | 1.20 µs / search (0.20 µs × 6); RTL still 10.0 µs amp |

**vs step 1c:** 12/15 top bands +1 LSB (bottom unchanged). Cause: SE `cmp` trips slightly later than `vsense > V_th` (1c MC mean SE offset ≈ +5.8 mV; CMP_HIGH=0.85 leaves a soft region near the Amp/2 trip) — search keeps one more bit. Final Amp still inside the window.

**D22 step 1 is done. Interim A2 is retired for all bands.** The on-chip calibration sets every band; bottom bands end at code 31 with tnr = 1.

