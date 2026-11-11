# VCO topology memo (P2.3)

Status: **topology accepted (D8–D11). P2.3 open items closed.** **P2.7.1b (2026-11-11):** range shift vs 25-Oct `range.json` caused by off-state **bank** (and var) start-up bypass C; re-baselined. 15-corner coverage of 3.12–4.20 GHz **PASS** (worst top margin 39 MHz); band steps **FAIL** (1.06 V at MSB carry) — fix before P2.7.2 layout. See §9.

---

## 1. Requirements

| Item | Value | Source |
|---|---|---|
| Range | 3.12–4.20 GHz (VHF ÷24: 130–175 MHz; UHF ÷8 uses 3.20–3.84 GHz) | `spec/rf-frontend.md` §5 |
| Phase noise at 1 MHz | VHF ≤ −116, UHF ≤ −115 dBc/Hz (at the 600 kHz / 2 MHz duplex offsets: ≤ −108.4 / −117.9) | `spec/phase2-plan.md` §2.1 |
| Current | VCO 2–4 mA of the ≤ 10 mA LO budget (D7) | §2.4 |
| Structure | One VCO, switched-capacitor bank (D2: 5–6 bits), NMOS cross-coupled core first, HBT core as comparison (D1) | §5 |
| Tank | L2n0, L 1.69 nH ± 3 %, Q 14.2 / 15.3 / 16.9 at 3.12 / 3.5 / 4.2 GHz (untapped P2.0); centre-tapped [EM] L 1.685 / 1.690 / 1.703 nH, Q 14.13 / 15.15 / 16.66 at 3.1 / 3.5 / 4.2 GHz, within 2 %, \|V_CT/V_diff\| ≤ 0.0036 | P2.0 / P2.7 tapped |
| Temperature, corners | −40 to +85 °C, PDK corners | `spec/rf-frontend.md` §6 |
| Settling | Band calibration + lock inside 150 µs | §5 |

## 2. Tank budget

Design range 3.00–4.37 GHz (band edges ± 4 % for capacitor spread, parasitic uncertainty and temperature), on top of the ± 3 % L uncertainty:

- Differential tank capacitance needed: **1 717 fF** at the low edge (L − 3 %) down to **762 fF** at the high edge (L + 3 %). Ratio 2.25; the bank and varactor must switch 955 fF.
- **Everything fixed must fit in 762 fF differential** at the high edge: core transistors, inductor self-capacitance, the bank's off-capacitance, the varactor minimum, the buffer input and routing. Rough split `[HAND]`: core ≈ 40, inductor ≈ 45, bank off-state ≈ 320 (for an on/off ratio of 4), varactor ≈ 20, buffer ≈ 15, routing ≈ 25 fF → ≈ 465 fF, leaving ≈ 300 fF margin. **The bank's on/off ratio at an acceptable Q is the main tuning-range risk.**
- Bank Q: each switched unit needs Q ≥ about 80 at 4.2 GHz so the bank costs ≤ 15 % of tank Q (assumed in the estimates below). This sets the switch size and therefore the off-capacitance; step 1 measures the trade-off.

## 3. Proposed topology

```
                VDD_VCO (dedicated LDO, about 1.0–1.2 V, from VR_ANA1)
                          │
                    ┌─────┴─────┐  L2n0 (centre tap to VDD_VCO)
                    │           │
          tank+ ────┤           ├──── tank−    → CML buffer → ÷2 (CML) → dividers (P2.4)
                    │           │
    7-bit cap bank ═╪═══════════╪═  MIM + NMOS switch per bit, differential
    varactor pair  ═╪═══════════╪═  sg13_hv_svaricap, well = Vtune (loop filter)
                    │           │
                M1 ─┴─┐     ┌───┴─ M2      NMOS LV cross-coupled pair (D1)
                      └──┬──┘
                         │ tail node ── C_tail (5–10 pF MIM): shunts tail noise near 2 f0
                         │
                        Mt   NMOS tail, long L (≥ 2 µm), current DAC 4–5 bits (amplitude per band)
                         │
                bias ── RC low-pass (pole ≤ 10 kHz) ── reference current
```

1. **Core: NMOS LV cross-coupled pair** (D1), because the simulation method is validated on exactly this circuit. Swing about 1.0 V differential (0.5 V per side): the peak gate–source, drain–source and gate–drain voltages must stay inside the LV device limits, which step 1 confirms from the PDK documentation. The VCO supply is set from that, not the other way round.
2. **Tail: NMOS current source with two filters**, the two noise paths P2.0 measured:
   - an RC low-pass on the tail bias (pole ≤ 10 kHz, MOS capacitor about 50 pF) against the reference mirror's flicker noise, which put the corner at 615 kHz without it;
   - a capacitor at the tail node (5–10 pF) against the tail transistor's noise near 2 f0, which added 70–90 % on top in P2.0. A resonant 2 f0 tail filter (Hegazi) would do better but needs a second inductor and cannot follow a 30 % tuning range, so it is not proposed.
   - The tail transistor's own flicker is reduced by area (long L); NMOS against PMOS flicker in SG13G2 is checked in step 1.
3. **Amplitude (D22):** 5-bit `VCO_BIAS` DAC, **I_tail = 1.52 mA + code × 0.08 mA** (≤ 4 mA, D12). Peak detector + SE comparator on the tank; digital search with band cal (`en_vco_tail_bp` closed during search), then hold. Target 1.25 V ± 0.10 V; steady ≤ 1.40 V, search transient ≤ 1.50 V. **Step 1 done 2026-11-11; interim A2 retired** (`spec/vco-amplitude-cal.md` §10).
4. **Capacitor bank: 7 bits, binary, differential MIM + NMOS switch** (proposed change from D2's 5–6 bits, §5 D8).
5. **Varactor: `sg13_hv_svaricap`** (accumulation-mode, thick oxide, PDK device), gates on the tank, well on the tuning line. Small: about 10 fF swing with 7 bits. Its C–V curve and Q set the usable tuning window, assumed 0.6 V here; a wider window lowers KVCO further.
6. **Supply: a dedicated LDO for the VCO.** Frequency pushing turns supply noise into phase noise exactly like tail noise; the LDO's own noise is budgeted in step 3.
7. **Buffer:** a differential CML buffer between the tank and the first ÷2, so divider kick-back and the load change between ÷8 and ÷24 do not pull the tank. Its input capacitance is in the 762 fF budget.

**Variant for comparison (D1): SiGe HBT cross-coupled core** (`npn13G2`), larger swing (≈ 1.6 V differential), low flicker. It is about 5 dB better on paper but needs 4–6 mA at the low edge (above the 4 mA VCO share of D7) and a higher supply. It is simulated in P2.3 as the comparison, not as the baseline.

**Not proposed:**
- Complementary (NMOS + PMOS) core: half the current for the same swing, but the PMOS pair adds capacitance that the 762 fF budget cannot spare at 30 % tuning range.
- Two VCO cores: rejected in D2 (twice the inductor area).

## 4. Estimates

Leeson, tank Q × 0.85 for bank and varactor loss, current-limited swing (`analog/vco/tank_budget.py`) `[HAND]`:

| Core | 3.12 GHz | 3.65 GHz | 4.20 GHz | Current |
|---|---|---|---|---|
| A: NMOS, 1.0 V swing, F = 3 | −124.8 | −123.1 | −121.7 dBc/Hz | 3.9 / 3.1 / 2.5 mA |
| A′: same, F = 4 (residual tail and bias noise) | −123.5 | −121.9 | −120.4 dBc/Hz | same |
| C: HBT, 1.6 V swing, F = 2.5 | −129.7 | −128.0 | −126.5 dBc/Hz | 6.3 / 4.9 / 3.9 mA |

Against the ≤ −116 / −115 dBc/Hz targets, core A has about 4–9 dB of margin before the losses this estimate leaves out (varactor AM-to-PM, supply pushing, buffer loading, corners). The worst case is the high edge: phase noise scales with (f0 / Q)², and f0 rises faster than Q across the range.

## 5. Decisions (accepted as proposed, 2026-10-20)

| # | Decision | Proposal | Reason |
|---|---|---|---|
| **D8** | Capacitor-bank size (changes D2) | **7 bits** instead of 6 | P2.2 rerun: the band step grows as f³ across the range, so a 6-bit bank needs KVCO 29–94 MHz/V. At 94 MHz/V the loop-filter resistor noise fails the VHF duplex limit (−135.3 dBc/Hz against −136) unless the charge-pump current rises to 50 µA, which needs about 950 pF of loop filter (2.4×; ≈ 0.12 mm² instead of ≈ 0.05 mm² as MOS capacitors). 7 bits needs 14–47 MHz/V; at 48 MHz/V with 42 µA the model passes with the original ≈ 400 pF. Cost: one more calibration step and one more register bit (`VCO_BAND` [6:0]; [7] stays manual) |
| **D9** | Tail treatment | **NMOS tail + RC-filtered bias + tail capacitor** (§3 item 2) | Removes both noise paths measured in P2.0 with standard parts; class-C biasing (gates biased below threshold through coupling capacitors, large tail capacitor) is evaluated as a variant in P2.3, not chosen now |
| **D10** | VCO supply | **Dedicated LDO**, voltage set by the LV device limits (about 1.0–1.2 V) | Supply pushing; isolation from the dividers and the digital blocks |

Interface consequences (applied to `spec/analog-digital-interface.md` on 2026-10-20): `VCO_BAND` becomes 7 bits; a new register for the VCO tail-current DAC (proposed 0x2C, `VCO_BIAS` [4:0]), written per band by the host or by the calibration; the charge-pump current code in `PLL_CTRL` [5:3] (25–200 µA) is also set per band to keep the loop bandwidth constant while KVCO varies about 3× across the range.

## 6. Step 1 — device checks before the schematic

All in VACASK on the pinned PDK, each a small testbench:

1. **LV NMOS voltage limits** from the PDK documentation, and the resulting swing and VCO supply.
2. **`sg13_hv_svaricap`:** C–V and Q at 3–4.4 GHz against tuning voltage; sets the varactor size and the tuning window.
3. **Bank unit cell** (MIM + NMOS switch): on/off capacitance ratio against Q for a few switch widths; decides whether the 762 fF budget holds.
4. **Flicker of NMOS against PMOS** current sources of equal area (tail choice).
5. **Inductor model:** a lumped broadband model fitted to the de-embedded EM data (2.0–4.5 GHz), so pss/pnoise can use it; checked against the EM L and Q within 1 %.

## 7. P2.3 after the review

| Step | Work | Gate |
|---|---|---|
| 1 | Device checks (§6) | Result review: confirms or changes §2–3 |
| 2 | Core schematic with the EM inductor model; bank, varactor, tail, buffer | — |
| 3 | `pnoise` (16 000 points, offsets ≥ 30 kHz) across bands, PDK corners, −40/27/85 °C; tuning range and KVCO per band; supply pushing; HBT comparison | Result review against §1 |

Simulation settings and method: `analog/pn-validation/README.md`. Offsets below 30 kHz need `pss_minpts` × offset ≥ 5·10⁸.

## 8. Step 1 results (2026-10-20) and what they change

Source: `analog/vco/step1/` (`run_step1.py`, results in its README). Typical corner, 27 °C.

| Item | Result | Change to §2–3 |
|---|---|---|
| Swing `[DS]` | LV `VGS ≤ 1.65 V @ 125 °C` (process spec). With 10 % margin and drain headroom over a 0.35 V tail node: **1.5 V differential at a 1.1 V centre tap** | D10 LDO at about 1.1 V. Swing is current-limited at the low edge (about 1.05 V at 4 mA) and voltage-limited at the high edge (1.5 V at 3.3 mA) |
| Bank cell `[SCH]` | 2 × `cap_rfcmim` 9 × 9 µm + LV NMOS switch, bottom plates to the switch. **About 100 µm of switch per 60 fF, 200 kΩ bias resistors**: whole 7-bit bank keeps 0.89 (all on, 3.12 GHz) / 0.97 (all off, 4.2 GHz) of tank Q; 391 fF off-state capacitance, **+226 fF** left in the 762 fF budget. 20 kΩ bias resistors made the off state lossy (Q_off 6–50) | Bias resistors ≥ 200 kΩ |
| Tail `[SCH]` | At the real 0.35 V tail voltage the HV NMOS keeps 74 % of its current (no headroom), LV NMOS 85 %. **LV NMOS 160/4 µm**: flicker corner 0.14–0.32 MHz, at 600 kHz within 1.5× of the white floor; LV PMOS worst (3.2 MHz corner at 80/2 µm) | Tail: LV NMOS ≥ 160/4 µm |
| Inductor `[EM]→[SCH]` | Lumped model `analog/vco/models/l2n0_lumped.inc`, L and Q within 0.71 % of EM (3.0–4.37 GHz); self-capacitance 30 fF. The EM layout has **no centre tap**; the model assumes one at the electrical midpoint | Tapped layout needs EM before P2.7 |
| Varactor `[SCH]` | Per finger (3.74 × 0.3 µm per side): 3.7 → 2.1 fF differential from V_G − V_W = +1.2 to −1.2 V; steepest about 1.4 fF/V near **V_G − V_W ≈ −0.3 V**; Q 110–190 at 4.2 GHz. Needed: about 10 fF over the tuning window → **about 12 fingers** (two instances, `nx` = 6) for a 0.7 V window | See D11 |

Phase noise with these numbers (Leeson, bank loss as measured, F = 3–4, 4 mA at the low edge): about −124 to −126 dBc/Hz at 1 MHz across the range, 8–10 dB under the targets `[HAND]`.

**D11 — varactor bias: option A accepted by the owner, 2026-10-20.** With the varactor gates at the tank DC (1.1 V), its steep region sits at a tuning voltage of about 1.4 V, above what a charge pump on the 1.2 V domain can deliver. Two common ways:

| Option | How | Cost |
|---|---|---|
| **A (proposed): AC-coupled varactor** | Varactor gates connected to the tank through MIM capacitors (about 5× the varactor capacitance), gates DC-biased to about 0 V through large resistors, so the steep region falls at a tuning voltage of about 0.3–1.0 V; charge pump and loop filter stay on 1.2 V LV devices | Coupling MIMs and bias resistors (their noise reaches the varactor, so ≥ 100 kΩ, checked in step 3); about 30 % less varactor swing through the coupling capacitors (so about 17 fingers instead of 12) |
| B: high-voltage charge pump | Charge pump and loop filter on the 2.7–3.6 V supply with HV devices; tuning window about 1 V or more | The ≈ 400 pF loop filter needs HV capacitors (lower density than LV MOS caps, or MIM at 1.5 fF/µm²): roughly 2× the filter area; KVCO halves, which helps noise |

Note on the PDK: the VACASK conversion of `sg13_hv_svaricap` does not elaborate (`v(2,4)` in its well resistance); step 1 uses a local copy with those zero-coefficient terms removed. To be reported upstream.

## 9. Steps 2–3 results (2026-10-20): first schematic, bands, corners

**D20 (2026-10-25, P2.6 step 1): the bank becomes 8 bits** (same 2.90–4.41 GHz range, LSB about 5.8 fF on-state) so that one band step is 0.23–0.30 V of V_tune instead of 0.45–0.59 V (`spec/pll-topology.md` §13). The step-2/3 scripts build 8 bits by default (`bits=7` gives the results below); first rerun 2026-10-25 `[SCH]`:
- Sizing: LSB 5.71 fF (on-state), fixed 203 fF. Range 2.910–4.408 GHz typical; at all 15 corner / temperature cases 2.77–3.05 GHz bottom and 4.34–4.55 GHz top (covers); peak V_GS / V_GD ≤ 1.48 V; KVCO 13.1–38.6 MHz/V; tail current per band as before (3.4–4.0 mA).
- Phase noise in five bands, typical: −124.4 / −123.4 / −122.7 / −121.5 / −119.9 dBc/Hz at 1 MHz (3.12–4.20 GHz), worst margin +3.9 dB — the same as with 7 bits to within 0.1 dB.
- **Band steps not uniform:** at the carries the step grows towards the MSB — 3→4: 1.07 ×, 63→64: 1.38 ×, **127→128: about 2.8 × a normal step (0.72 V of V_tune)**, 191→192: 1.45 × (ratios against the local mean, which includes the carry itself). Small cells switch relatively less capacitance (perimeter and switch parasitics in the off state do not scale with the cell), so a plain binary weighting is not enough. Fix: each bit trimmed in size so the step at its carry equals the single-LSB steps beside it (`trim()` in `run_step2.py`, bottom-up, two passes, then re-sizing for the range); systematic, so it holds over corners to first order.
- **Second run (with the trim):** trims 0.971 (bit 1) … 0.933 (bit 7), i.e. the larger cells 3–7 % smaller than plain binary; after re-sizing LSB 6.07 fF, fixed 202 fF. Range 2.914–4.414 GHz, KVCO 13.1–38.8 MHz/V, swing and tail currents unchanged. **Band steps even:** every carry within 0.94–1.07 × the neighbouring steps, steps 3.3 MHz (bottom) to 11.2 MHz (top), **0.24–0.29 V of V_tune** everywhere (7 bits: 0.45–0.59 V), as assumed in the P2.6 closed-loop model. Corner range with the trimmed bank: all 15 cases cover; bottom 2.77–3.05 GHz (least margin 3.054 GHz, MIM best case, 66 MHz below 3.12 GHz), top 4.35–4.55 GHz; peak V_GS / V_GD ≤ 1.48 V — the same as before the trim. **D20 bank done.**

Source: `analog/vco/step2/`, `analog/vco/step3/` (VACASK, PDK `a49358cc`) `[SCH]`. Ideal still: supplies (LDO — noise budget from pushing, § open point 4), reference current, bias-filter R and C, tail capacitor. Stand-in buffer replaced for PN by the P2.4 LO buffer (CML ÷N on the tank still breaks PSS).

**Circuit as simulated:** L2n0 lumped model, centre tap at 1.1 V; LV NMOS pair 32/0.13 µm; tail LV NMOS 160/4 µm, mirror 1:8, bias RC 1 MΩ / 50 pF, tail capacitor 8 pF; 7-bit bank, on-state LSB 11.5 fF after the review (10.9 fF before; sized automatically: the bank switches C_on − C_off, and the fixed capacitance without a fixed capacitor was only about 420 fF), about 100 µm of switch per 60 fF, plus a 204 fF fixed MIM (224 fF before the review); varactor 20 fingers AC-coupled through MIMs of about 5×, gates at 0.3 V; **2 MΩ** bank and varactor bias resistors.

**Start-up bias bypass (P2.6 open point 2, 2026-10-31):** LV NMOS across `rbf` (20 µm / 0.13 µm, ng=4) and across every `rba*`/`rbb*` and `rvp`/`rvn` (5 µm / 0.13 µm, ng=2 — smaller on tank nodes), gate `vbp` / digital `en_vco_bias_bp`. Closed ≥ 0.4 µs at wake by `afe_seq` (36 ref cycles = 1.00 µs at 36 MHz). Stand-alone VCO range/pnoise runs keep `vbp` tied low. See `spec/analog-digital-interface.md` §6.

**SCH re-run 2026-10-31:** range pass (`summary_range_rerun.txt`). PSS abort root cause: off-state **bank** bypass NMOS on the tank bottom plates (`summary_pss_bypass_parts.txt`; tail and varactor bypasses OK). Bank-omitted PN accepted for layout start: tt 3.65 GHz −122.7 dBc/Hz @ 1 MHz (+6.7 dB); ss 85 °C 4.20 GHz −119.4 (+3.4 dB) (`summary_pn_nobank.txt`). Linear bank equivalent abandoned. Switch-noise bound vs bank bias R **closed 2026-11-01** (`summary_bound_bank_switch.txt`): tt +0.59 dB worst-case bound (margin +6.1 dB); ss85 Δ +0.006 dB; owner gate (positive margin everywhere; worst-point move < 0.5 dB).

**Bypass on-resistance `[SCH]`** (V_GS = 1.2 V, V_DS = 50 mV): tail switch Ron ≈ 29–34 Ω (tt/ss, −40/27 °C); bank/varactor switch Ron ≈ 124–143 Ω. With C_tail = 50 pF, τ ≈ 1.5–1.6 ns and 7 τ ≈ 11 ns — the 1 µs closed window is ≈ 90 × 7 τ even at ss / −40 °C. Bank MSB (~1.5 pF) is faster (7 τ ≈ 1.4 ns). Ron ≪ R_bias (1 MΩ / 2 MΩ), so the bypass is a true short for start-up.

| Result | Value |
|---|---|
| Range, typical 27 °C | **2.90–4.41 GHz** after the review (2.95–4.41 before) |
| Range at 5 corner combinations × −40 / 27 / 85 °C | Covered everywhere: top 4.34–4.55 GHz, bottom 2.77–3.05 GHz. Least margin at the bottom: MIM best-case corner, 3.036–3.047 GHz, 73–84 MHz below 3.12 GHz (32–45 MHz before the review), enough for the ± 3 % inductance uncertainty (about ± 47 MHz) |
| KVCO | 13.1–38.6 MHz/V (D8 target 14–47) |
| Peak V_GS / V_GD | ≤ 1.48 V at all corners (limit 1.5 V with margin, 1.65 V in the process specification) |
| Tail current for about 1.3 V | 3.4–3.6 mA at the top; **capped at 4 mA** (D12) from about 3.65 GHz down (5 mA before D12) |
| Swing at the bottom (4 mA) | 0.92 V differential typical; lowest 0.59 V (fast MOS, MIM worst case, 85 °C) and 0.64 V (slow, 85 °C) |
| pss tolerance | reltol 1e-6 gives the same result as 1e-7 on the validated level 2 (0.00 dB); 1e-7 does not converge on the full VCO |

Phase noise, typical, 27 °C (dBc/Hz), with the 4 mA cap (D12, rerun 2026-10-20; codes 97 / 67 / 45 / 28 / 11). In brackets: before D12 (5 mA cap).

| VCO | I_tail | 600 kHz | 1 MHz | 2 MHz | Worst margin |
|---|---|---|---|---|---|
| 3.12 GHz | 4.0 mA (5.0) | −119.1 | −124.4 (−124.7) | −130.9 | +8.4 dB (VHF 1 MHz) (+8.7) |
| 3.40 GHz | 4.0 mA (4.8) | −117.8 | −123.4 (−123.5) | −130.2 | +7.4 dB (+7.5) |
| 3.65 GHz | 3.96 mA (4.3) | −116.6 | −122.3 (−122.7) | −129.1 | +6.3 dB (+6.7) |
| 3.90 GHz | 3.87 mA | −115.6 | −121.6 | −128.6 | +5.6 dB |
| 4.20 GHz | 3.59 mA | −113.7 | −120.0 | −127.3 | **+4.0 dB** |

Slow MOS corner, 85 °C, 4 mA cap: 3.12 / 3.65 / 4.20 GHz at 1 MHz −122.8 / −122.0 / −119.6 dBc/Hz (before D12 −123.5 / −122.1 / −119.6), worst margin **+3.6 dB** unchanged (4.20 GHz, VHF 1 MHz). The 4 mA cap costs 0.3–0.7 dB at the bottom, less than the 2 dB estimated. The UHF limits (3.20–3.84 GHz) have at least 8 dB margin. Noise contributions at 3.65 GHz, 1 MHz: core pair 50 %, inductor 20 %, varactor bias 9 %, bank bias about 10 %, tail 3 % (at 200 kΩ the bias resistors were 36 % and the stand-in buffer 26 %).

**Open points for the result review:**
1. **Current at the bottom of the band:** 5 mA is above the 4 mA VCO share of D7. At 4 mA the swing at 3.12 GHz falls to about 0.82 V and the phase noise by roughly 2 dB, still about 6 dB inside the limit. Proposal: cap `VCO_BIAS` at 4 mA. **Decided 2026-10-20 (D12, with P2.4): capped at 4 mA**; rerun done (`analog/vco/step3/out/summary_4ma.txt`): range and corners unchanged, phase noise 0.3–0.7 dB worse at the bottom, bottom margin +6.8 dB at slow 85 °C.
2. **Bottom-edge margin (accepted and done 2026-10-20: now 73–84 MHz):** with the MIM best-case corner the bottom edge sits 32 MHz below 3.12 GHz. Combined with the ± 3 % inductance uncertainty it could miss by about 10 MHz. Proposal: about 5 % more switched capacitance (design range down to about 2.9 GHz); the top edge keeps ≥ 4.3 GHz at the worst MIM corner.
3. **Amplitude per corner:** **D22 accepted 2026-11-02; step 1 closed 2026-11-11** (`spec/vco-amplitude-cal.md` §10): SE-cmp end-to-end search PASS (steady ≤1.40 / transient ≤1.50); **interim A2 retired**. Bottom bands code 31 / tnr=1 expected.
4. **Supply pushing / LDO budget `[SCH]+[HAND]` (2026-11-01):** K_push ≈ −30 / −50 MHz/V → S_v ≤ ~11 nV/√Hz @ 1 MHz (`summary_supply_push.txt`). First D10 LDO SCH: ~86 nV/√Hz bare (**miss**). **D21 (owner):** VR_ANA1 = LDO → 10 Ω → pad → 100 nF; VCO+LO+CP from pad; RX→VR_ANA2; pad worst-case ≥1.08 V; no option (1). Prior S_v≈9.5 nV/√Hz **UNVERIFIED** (OP did not hold). Fixed LDO (Rz=500 + Cg=100 p to gnd): HOLD; PM ≥ 60° with/without 100 nF; S_v(pad)≈**3.0 nV/√Hz** @ 10 mA (**PASS**). `summary_ldo_verify.txt`. **Real P2.4 LO buffer:** −122.6 / −119.3 (Δ +0.14 / +0.08 dB). Buffer + CML ÷N: PSS aborts.
5. **Centre-tapped L2n0 `[EM]` (2026-11-01):** done. L 1.685 / 1.690 / 1.703 nH, Q 14.13 / 15.15 / 16.66 at 3.1 / 3.5 / 4.2 GHz; all within 2 % of untapped; \|V_CT / V_diff\| ≤ 0.0036 (`spec/provisional-tank-q.md`, `tapped/review/em_summary.md`). **[HAND]** 1.4 % lower Q at 4.2 GHz → ≈ 0.1 dB worse PN at ss 85 °C; remaining margin ≈ +3.5 dB (was +3.6).
6. **Real LO buffer + CML load — closed 2026-11-11** (`analog/vco/step3/out/summary_real_load.txt`, landing `analog/pll/p26/step1/out/summary_land_scaled.txt`):
   - Full real load (P2.4 buffer + CML ÷2/÷3 + converter), D22 bias: max |Δf| vs same-Vtune stand-in **0.285 %** `[SCH]`; worst bottom 3.057 GHz (ss/bcs/−40) → **63.3 MHz** margin to 3.12 GHz (was 66 MHz / 3.054 GHz); carries 63→64 / 127→128 / 191→192 even (4.5–8.5 MHz) `[SCH]`.
   - Shift > 0.2 % → closed-loop landing with **scaled behavioural bank** (+0.285 %), not transistor bank `[MODEL]`: D20 8-bit / f/4P / nearest outside-% unchanged within 0.1 pt; V_tune stays in 0.25–0.95 V (ss 0.25–0.85 V).
   - Divider pulling: |Δf| ≤ 55 ppm, |ΔAmp| ≤ 0.0001 V (tt 3.65 / ss85 4.20) `[SCH]`. Kick-back (coherent |Δ|mag) f0/2 and f0/3 ≤ **−107 dBc**; sidebands ≤ −95 dBc `[SCH]`. Buffer reverse isolation **67.8 dB** `[SCH]`.
   - PSS with CML: still aborts (tolerances + longer warm + lower maxharm + CML always-on; no separate autonomous-shooting option in VACASK) `[SCH]`.
   - **[HAND] PN bound:** buffer SCH +0.14 dB + CML ≤ +0.3 dB → total real-load ΔL(1 MHz) ≤ **+0.5 dB** gate (limit met). Open point closed.
7. **HBT core comparison (D1) — closed 2026-11-11** (`analog/vco/step3/out/summary_hbt_compare.txt`): comparison only; **keep NMOS**.
   - Model: `npn13G2` op/tran PASS; PSS converges but L ~35 dB optimistic vs Leeson — **HBT PSS L untrusted** `[SCH]`/`[HAND]`. BVCEO 1.4/1.6 V, BVCBO 3.8/4.8 V, BVEBO 1.0/1.6 V `[DS]`. Flicker params present in VBIC.
   - Same tank / 8-bit bank / D21 1.2 V / D12 4 mA / nx=8: Amp ≈ **0.99 V** (NMOS 1.16 V) `[SCH]`; VCE peaks OK at that Amp; paper 1.6 V swing would exceed BVCEO min and needs ≈ 1.8–2.5 V CT (D21 unchanged → not proposed).
   - Fair Leeson (Q=15, F_HBT=2.5 / F_NMOS=3): ΔL(1 MHz) ≈ **+0.1…+0.6 dB** (HBT not better) `[HAND]`. NMOS SCH duplex −122.6 / −119.3 still the design numbers.
   - Range: top **4.10 GHz < 4.20 GHz** (HBT Cje); bottom 2.91 GHz OK; KVCO ≈ 21 MHz/V; start-up ≈ 1 ns `[SCH]`. Core area smaller (`[HAND]`) — not the cost driver.
   - **Conclusion:** paper ≈ 5 dB win not realised under D21/D12; band top misses; no switch.

### P2.7.1b (2026-11-11) — range shift cause, re-baseline, coverage finding

**Cause of miss vs `range_2026-10-25.json`:** off-state start-up **bank** bypass NMOS C on the tank plates (≈ −15 MHz at code 0), plus var bypass (≈ −3 MHz). Tail bypass ≈ 0. Sum of parts matches the full-bypass shift. Not PDK/tool (pinned `a49358cc`); not xschem. D22 det/DAC are ampcal-only. Details: `analog/vco/sch/out/summary_range_shift.txt`, `summary_p271b.txt` `[SCH]`.

**Re-baseline:** new `analog/vco/step2/out/range.json` (LSB 7.25 fF, cfix 190 fF, trims ≈ 0.87–0.93); archive kept as `range_2026-10-25.json`. tt span 2.796–4.302 GHz.

**Coverage [SCH]** (`step3/out/summary_8bit_range.txt`): all **15** MOS/CAP/T cases cover 3.12–4.20 GHz; peak V_GS/V_GD ≤ 1.46 V. Worst top margin **39 MHz** (mos_ss / cap_wcs / −40 °C, f_top 4.239 GHz). Worst bottom margin **186 MHz** (f_bot 2.934 GHz).

**Band steps [SCH]** (`step2/out/summary_steps.txt`): **FAIL** — 127→128 is **1.060 V** of V_tune (need 0.24–0.29 V). Off-state bypass C breaks the prior trim. **Do not start P2.7.2 layout until steps are fixed.**

**Proposal:** re-trim / re-size with bypass C in the model; or shrink / move bank bypass so off-C does not dominate MSB carries; or keep RF-plate bypass off if wake RC still meets 0.4 µs.

**D22 search** tt/27: PASS (top code 16, Amp 1.261; bottom 31). **D20 landing [MODEL]** with new ends: 8-bit / f/4P / nearest still ~0 % outside.
