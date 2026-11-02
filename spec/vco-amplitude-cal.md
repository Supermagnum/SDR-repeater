# VCO amplitude control (P2.3 open point §9.3)

Status: **D22 accepted by the owner 2026-11-02** (`decisions.md`). Option C with the DAC offset and “target not reached” rule below. Interim: A2 until C is designed. No circuit designed in the memo run.

Items 1–2 of `prompts/06-design-next-step.md` are closed (P2.6 accepted 2026-10-31; open points 1–3 closed). Newest status report `reports/status-2026-10-30.md`: no failed re-run; amplitude cal listed as open work, not as an unverified blocking result.

---

## 1. Limits

| Limit | Value | Source |
|---|---|---|
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
