# PLL topology memo (P2.5): PFD, charge pump, loop filter, feedback divider, Σ-Δ

Status: **topology accepted by the owner 2026-10-21 (D16–D18 as proposed, §4). Step 1 (device and block checks, `analog/pll/step1/`) prepared.** Numbers are hand estimates `[HAND]` or from the linear PLL model `[MODEL]` (`analog/pll-model/`, P2.2), unless marked. Inputs: `spec/phase2-plan.md` §2 and D3, D5, D6, D7, D11; the VCO (`spec/vco-topology.md` §9); the LO dividers (`spec/lo-divider-topology.md` §9, P2.4 accepted 2026-10-21); the register map (`spec/analog-digital-interface.md` §5).

---

## 1. Requirements

| Item | Value | Source |
|---|---|---|
| Reference / PFD | 32 or 36 MHz (TCXO, pin strap `ref_36`); no reference divider | Plan §2.2 |
| Feedback ratio | f_VCO / f_ref = 86.7 … 131.25 in use (N_INT 86–131, 24-bit fraction); calibration sweeps the VCO over 2.90–4.41 GHz (80–138) | Register map §5.2 |
| Σ-Δ | MASH 1-1-1, 24 bits, dither; modulus excursion −3 … +4 | D3, plan §2.2 |
| Loop | Type II, 150 kHz bandwidth, 55° phase margin, 3rd-order passive filter plus one pole | D5, P2.2 |
| Loop filter (P2.2) | C1 39 pF, C2 355 pF, R1 9.5 kΩ, R3 34 kΩ, C3 3.9 pF (≈ 400 pF), for I_cp · K_VCO ≈ 50 µA · 40 MHz/V | P2.2 |
| K_VCO | 13–39 MHz/V across the 7-bit bank (P2.3); I_cp set per band to keep I_cp · K_VCO constant: about 50–155 µA, inside `PLL_CTRL` [5:3] = 25–200 µA | D8, register map |
| Tuning window | 0.3–1.0 V on the 1.2 V domain (AC-coupled varactor) | D11, P2.3 |
| Phase noise | In-band PFD/CP figure of merit ≤ −218 dBc/Hz (model input); duplex limits −136 dBc/Hz at RF met with margin when the VCO meets its target | P2.2 |
| Spurs | Integer-boundary (fractional) spur raw at the VCO ≤ −35 dBc (VHF) / −20 dBc (UHF) to meet −95 dBc on the hit channels; reference spur ≤ −67 dBc (TX), leakage ≤ 100 nA gives −151 dBc | P2.2, `spec/derived-limits.md` §9 |
| Lock | ≤ 150 µs wake incl. band calibration; linear lock 125 µs from a 2 MHz residual | P2.2 |
| Current | PLL share of the LO budget about 1.5 mA `[HAND]`; with the dividers measured (P2.4) the margin to D7 is about 0.35 mA, so **≤ 1.8 mA** | D7 reading 2026-10-21 |

## 2. Proposed topology

```
 XTB ─► ref buffer ─► PFD (tri-state, reset delay) ─► CP (I_cp 25–200 µA, offset current) ─► loop filter ─► V_tune (VCO)
                       ▲                                                                       C1 ∥ (R1+C2), R3-C3
                       │ div_clk                                                                        
   VCO ─► LO buffer ─► CML ÷2 (UHF) / ÷3 (VHF) ─► converter ─► x_clk ─┬─► LO chain (P2.4)
                                                                       └─► MMD (2/3-cell chain, CMOS) ─► div_clk
                                                                              ▲ div_n (8 bits)
                                                         Σ-Δ MASH 1-1-1 (AFE/LO block, clocked by div_clk)
```

1. **Reference buffer:** self-biased CMOS inverter, AC-coupled from the XTB pin (clipped-sine TCXO), then a sharpening inverter. Its noise is in-band and multiplied by N, so it gets its own quiet supply branch.
2. **PFD:** the usual tri-state phase-frequency detector (two resettable flip-flops, AND reset) with a **reset delay of about 150–250 ps**, so both charge-pump switches turn fully on every cycle (no dead zone).
3. **Charge pump:** current-steering with a dummy branch whose node is held at V_tune by a unity-gain amplifier (no charge sharing when the switches turn), cascoded current sources, and a replica-feedback amplifier that matches the up and down currents across the tuning window. **Offset (bleed) current** of about 5–10 % of I_cp (D18), so the PFD always works on one side of zero and the up/down mismatch stays linear — the common way to keep a fractional-N charge pump from folding Σ-Δ noise into spurs. I_cp 25–200 µA in 25 µA steps (`PLL_CTRL` [5:3]).
4. **Loop filter:** the P2.2 values. Capacitor type is D17.
5. **Feedback divider (D16):** the multi-modulus divider takes its clock from the **LO chain's first CML stage** (÷2 on UHF, ÷3 on VHF, `x_clk` after the converter), not from the VCO directly. The MMD then runs at ≤ 2.2 GHz (UHF) / ≤ 1.47 GHz (VHF) in CMOS, and no extra 4.4 GHz stage is needed. MMD ratio = N / P: UHF 40–69, VHF 27–46 over the calibration sweep, **37–73 / 23–50** with the Σ-Δ excursion. Structure: chain of **6 divide-by-2/3 cells with range extension** (16–127), the first cell or two in TSPC (checked with mismatch at the slow corner), the rest static CMOS; the modulus `div_n` is reloaded once per output cycle and `div_clk` is retimed.
6. **Σ-Δ modulator:** MASH 1-1-1, 24-bit accumulators, LSB dither, clocked by `div_clk` (D3: in the AFE/LO control block). The prescaler P multiplies its quantisation step at the VCO by P (see §3). Written as RTL in this step, verified against a Python model.
7. **Lock detector and band calibration:** digital, in the AFE/LO block: lock = PFD up/down pulses shorter than a window for 64 reference cycles; calibration = counter on `div_clk` against `clk`, binary search over the 7-bit bank (`spec/analog-digital-interface.md` §7 item 4).

**Alternatives considered:**
- *Separate CML prescaler at the VCO* (dual-modulus 4/5 or 2/3 at 4.4 GHz): independent of the LO chain, Σ-Δ step not enlarged; but about 1–1.5 mA more (a third 4.4 GHz CML block), which breaks D7. Kept as the fallback.
- *Divide the reference instead of a higher PFD:* lower PFD raises the in-band CP noise by 20·log; excluded in P2.2.
- *Sampling or subsampling PLL:* lower in-band noise, but a new architecture with no fractional-N reference design in this PDK; not needed for the limits.

## 3. Estimates

**Σ-Δ noise with the shared prescaler** `[MODEL]` (`pll_model.py --presc`, new option): the quantisation noise at the VCO rises by 20·log10(P): +6 dB UHF, +9.5 dB VHF.

| Case | Σ-Δ share at the duplex offset (RF) | Total (RF) | Limit |
|---|---|---|---|
| VHF, 600 kHz, no prescaler | −170.5 … −173.1 dBc/Hz | −137.2 … −137.3 | −136 |
| VHF, 600 kHz, ÷3 prescaler | −161.0 … −163.6 | −137.1 … −137.3 | −136 |
| UHF, 2 MHz, ÷2 prescaler | −158.2 … −160.7 | −139.4 … −139.5 | −136 |
| With the simulated VCO (−120 dBc/Hz at 1 MHz, K_VCO 39 MHz/V), prescaler | VHF −161, UHF −158 | VHF −140.4 … −140.8, UHF −143.1 … −143.2 | −136 |

The Σ-Δ share stays at least 17 dB below the total; the totals do not change. Spurs, lock time and loop filter are unchanged (the prescaler does not change the loop).

**Current** `[HAND]`:

| Block | Current |
|---|---|
| Reference buffer (36 MHz) | 0.1–0.2 mA |
| PFD (36 MHz) | < 0.05 mA |
| Charge pump: I_cp (average far below, short pulses) + offset current + two amplifiers | 0.2–0.4 mA |
| MMD, CMOS at ≤ 2.2 GHz (C·V²·f) | 0.3–0.5 mA |
| Σ-Δ, lock detector, calibration (digital, 36 MHz) | 0.1–0.2 mA |
| **PLL total** | **≈ 0.8–1.3 mA** (≤ 1.8 mA allowed) |
| A separate CML prescaler (not proposed) would add | 1–1.5 mA |

**Tuning window vs charge-pump compliance:** a cascoded current source on 1.2 V keeps its output current within about 1 % from roughly 0.25 to 0.95 V `[HAND]`. The VCO bands were sized for 0.3–1.0 V. Proposal: the band calibration targets 0.35–0.85 V (margin for temperature drift after lock); the 7-bit bank overlaps enough for that (P2.3: K_VCO 13–39 MHz/V, band step about 10–30 MHz) — checked in step 1.

**Loop-filter area** `[HAND]`: about 400 pF → about 0.05 mm² as thin-oxide MOS capacitors (≈ 8 fF/µm²) or 0.27 mm² as MIM (≈ 1.5 fF/µm²).

## 4. Decisions (accepted as proposed, 2026-10-21)

| # | Decision | Proposal | Reason |
|---|---|---|---|
| **D16** | Where the feedback divider takes its clock | **From the LO chain's first CML stage** (÷2 UHF / ÷3 VHF), MMD in CMOS | Saves a third 4.4 GHz CML block (1–1.5 mA; D7 has only ≈ 0.35 mA left). Cost: Σ-Δ quantisation noise +6 / +9.5 dB, still ≥ 17 dB below the total; the band's first divider stage must run whenever the PLL runs (also in "fast-wake" standby, `PLL_CTRL` [0]); band calibration counts MMD output cycles × P. Fallback: own CML prescaler |
| **D17** | Loop-filter capacitors | **MOS capacitors for C1 and C2, MIM for C3**; about 0.06 mm² | All-MIM would take about 0.27 mm². MOS gate leakage (estimated tens of nA for 355 pF) only reaches the reference spur, which has > 80 dB of margin at 100 nA; their voltage dependence changes the loop gain slightly over the 0.35–0.85 V window (checked in step 1) |
| **D18** | Charge-pump linearisation | **Offset (bleed) current about 5–10 % of I_cp**, plus replica-feedback up/down matching | The usual fix for fractional-N spur folding: the raw boundary-spur budget at VHF is −35 dBc, which an unlinearised pump with a few % mismatch can exceed. Cost: a small fixed phase offset and slightly more in-band CP noise (≈ 1 dB) |

Interface consequences (if accepted): the MMD range and `div_n` width stay as in the register map (8 bits covers 23–73); the calibration and the `N_INT` / `N_FRAC` to MMD conversion divide by P = 2 or 3 (digital, AFE block); `FILT`, `PLL_CTRL` unchanged.

## 5. Step 1 — device and block checks before the schematic

Small VACASK runs at typical and slow corner (1.08 V, 125 °C), fast where it matters:
1. **Charge pump:** up/down current match and output compliance against V_tune 0.2–1.0 V, at 25 / 100 / 200 µA; leakage with the pump off.
2. **Loop-filter MOS capacitor:** density, voltage dependence 0.3–1.0 V and gate leakage at 125 °C from the PDK models (thin-oxide and thick-oxide options).
3. **MMD first 2/3 cell:** maximum frequency at the slow corner with mismatch (the P2.4 lesson: TSPC margin at 2 GHz shrinks with mismatch and slow clock edges).
4. **PFD:** reset pulse width and dead zone across corners.

## 6. After the review

| Step | Work | Gate |
|---|---|---|
| 1 | Device and block checks (§5) | Result review: confirms or changes §2 |
| 2 | Schematics: reference buffer, PFD, CP, loop filter, MMD; Σ-Δ, lock detector and calibration as RTL with a Python reference model | — |
| 3 | Corners and Monte Carlo: CP mismatch and leakage, MMD speed, PFD dead zone → raw spur level S0 and reference spur fed back to the P2.2 model; current | Result review against §1; then P2.6 (closed loop) |
