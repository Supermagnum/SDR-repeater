# VCO topology memo (P2.3)

Status: **topology accepted by the owner, 2026-10-20 (D8–D10 as proposed, `decisions.md`). Step 1 device checks done 2026-10-20 (§8); D11 accepted 2026-10-20 (AC-coupled varactor). Steps 2–3 (schematic, bands, corners, temperature) done 2026-10-20: all bands and corners meet the phase-noise targets, worst margin +3.6 dB (§9). Result review 2026-10-20: 5 % more switched capacitance accepted and rerun (§9, final numbers); the other open points of §9 stay open. P2.3 schematic phase done. Rerun with the 4 mA cap (D12) 2026-10-20: bottom band only 0.3–0.7 dB worse, worst margin unchanged at +3.6 dB (§9).** Numbers here are hand estimates `[HAND]` from `analog/vco/tank_budget.py` and the P2.2 model (`analog/pll-model/`), on the accepted EM tank values (`spec/provisional-tank-q.md`) and the P2.0 phase-noise validation (`reports/phase2-review/p20-flicker.md`).

---

## 1. Requirements

| Item | Value | Source |
|---|---|---|
| Range | 3.12–4.20 GHz (VHF ÷24: 130–175 MHz; UHF ÷8 uses 3.20–3.84 GHz) | `spec/rf-frontend.md` §5 |
| Phase noise at 1 MHz | VHF ≤ −116, UHF ≤ −115 dBc/Hz (at the 600 kHz / 2 MHz duplex offsets: ≤ −108.4 / −117.9) | `spec/phase2-plan.md` §2.1 |
| Current | VCO 2–4 mA of the ≤ 10 mA LO budget (D7) | §2.4 |
| Structure | One VCO, switched-capacitor bank (D2: 5–6 bits), NMOS cross-coupled core first, HBT core as comparison (D1) | §5 |
| Tank | L2n0, L 1.69 nH ± 3 %, Q 14.2 / 15.3 / 16.9 at 3.12 / 3.5 / 4.2 GHz | P2.0 |
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
3. **Amplitude per band:** the tail current is a 4–5-bit DAC, set per band so the swing stays at the reliability limit (about 2.5 mA at 4.2 GHz, 3.9 mA at 3.12 GHz, `[HAND]`). A peak detector for a closed amplitude loop is an option for P2.3; it adds a block to the AFE/LO control.
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
- **Second run (with the trim):** trims 0.971 (bit 1) … 0.933 (bit 7), i.e. the larger cells 3–7 % smaller than plain binary; after re-sizing LSB 6.07 fF, fixed 202 fF. Range 2.914–4.414 GHz, KVCO 13.1–38.8 MHz/V, swing and tail currents unchanged. **Band steps even:** every carry within 0.94–1.07 × the neighbouring steps, steps 3.3 MHz (bottom) to 11.2 MHz (top), **0.24–0.29 V of V_tune** everywhere (7 bits: 0.45–0.59 V), as assumed in the P2.6 closed-loop model. Corner range check with the trimmed bank: `run_step3.py range`.

Source: `analog/vco/step2/`, `analog/vco/step3/` (VACASK, PDK `a49358cc`) `[SCH]`. Ideal still: supplies (LDO), reference current, bias-filter R and C, tail capacitor, buffer (a stand-in for the CML buffer of P2.4).

**Circuit as simulated:** L2n0 lumped model, centre tap at 1.1 V; LV NMOS pair 32/0.13 µm; tail LV NMOS 160/4 µm, mirror 1:8, bias RC 1 MΩ / 50 pF, tail capacitor 8 pF; 7-bit bank, on-state LSB 11.5 fF after the review (10.9 fF before; sized automatically: the bank switches C_on − C_off, and the fixed capacitance without a fixed capacitor was only about 420 fF), about 100 µm of switch per 60 fF, plus a 204 fF fixed MIM (224 fF before the review); varactor 20 fingers AC-coupled through MIMs of about 5×, gates at 0.3 V; **2 MΩ** bank and varactor bias resistors.

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
3. **Amplitude per corner:** at fast MOS / 85 °C the bottom-band swing falls to 0.69 V with the typical current (0.59 V with the 4 mA cap and the MIM worst case). The P2.4 chain divides correctly at the slow corner, 125 °C, bottom band (buffer 0.43 V per side, `spec/lo-divider-topology.md` §8); the fast-corner low-swing case is checked in P2.4 step 3. An amplitude calibration (peak detector setting `VCO_BIAS`) or a per-corner table is needed; it is not yet simulated.
4. **Not yet simulated:** supply pushing (the LDO noise budget), the real CML buffer and divider load (P2.4), the HBT comparison (D1), a tapped L2n0 layout with EM (before P2.7).
