# PLL topology memo (P2.5): PFD, charge pump, loop filter, feedback divider, Σ-Δ

Status: **topology accepted by the owner 2026-10-21 (D16–D18 as proposed, §4). Step 1 done 2026-10-21 (§7): plain long-channel charge-pump sources with replica matching, complementary MOS loop-filter capacitors, TSPC 2/3 cell; tuning window 0.25–0.95 V. Step 2a (PFD and charge pump, `analog/pll/step2/`) done 2026-10-25 (§8): fully transistor level, no dead zone, INL ≤ 3.6 ps on the locked side except the slow corner at the very top of the window. Step 2b (MMD) and 2c (Σ-Δ, lock detector, band calibration) done 2026-10-25 as RTL (§9–10), all tests pass. Step 3 (Monte Carlo, spur levels, current) prepared: `analog/pll/step3/`.** Numbers are hand estimates `[HAND]` or from the linear PLL model `[MODEL]` (`analog/pll-model/`, P2.2), unless marked. Inputs: `spec/phase2-plan.md` §2 and D3, D5, D6, D7, D11; the VCO (`spec/vco-topology.md` §9); the LO dividers (`spec/lo-divider-topology.md` §9, P2.4 accepted 2026-10-21); the register map (`spec/analog-digital-interface.md` §5).

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

**Tuning window vs charge-pump compliance:** a cascoded current source on 1.2 V keeps its output current within about 1 % from roughly 0.25 to 0.95 V `[HAND]`. The VCO bands were sized for 0.3–1.0 V. ~~Proposal: the band calibration targets 0.35–0.85 V~~ — corrected in §7: one band step is about 6 MHz (bottom) to 20 MHz (top), i.e. 0.45–0.52 V of V_tune at K_VCO 13–39 MHz/V, so with drift margin the pump must cover **about 0.25–0.95 V**.

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

## 7. Step 1 results (2026-10-21)

Source: `analog/pll/step1/` (VACASK, PDK `a49358cc`) `[SCH]`; tt 1.2 V 27 °C, ss 1.08 V 125 °C, ff 1.32 V −40 °C.

**Tuning window needed (correction to §3):** the 7-bit bank spans 2.90–4.41 GHz, so one band step is ≈ 6 MHz at the bottom and ≈ 20 MHz at the top (the step grows with f³); at K_VCO 13.1 / 38.6 MHz/V that is **0.45–0.52 V of V_tune** just to reach from one band to the next. With margin for temperature drift after lock, the charge pump has to work over **≈ 0.25–0.95 V**, close to the VCO design window (0.3–1.0 V). The 0.35–0.85 V of §3 is too narrow.

| Check | Result | Consequence |
|---|---|---|
| **Charge pump, wide-swing cascodes** | Down (NMOS) side within 1 % from 0.35–0.45 V upward; **up (PMOS) side only up to 0.65–0.80 V** (ss 200 µA: 0.40–0.65 V). Raw up/down mismatch 3–20 %. Leakage, switches off, 125 °C: 2–10 nA typical, 23–59 nA fast | **Fails the 0.25–0.95 V window**: two stacked devices plus the switch need too much of 1.2 V. Second run: plain current sources with long channels (L = 2 µm, one V_ov ≈ 0.15 V) and wider switches; the replica-feedback amplifier (D18) then removes the mismatch, and the few-% change of the absolute current only moves the loop gain slightly |
| **MOS capacitors (D17)** | Thin NMOS 10–13 fF/µm² above 0.35 V but falls to 2–7 at 0.1–0.2 V; thin PMOS the mirror image; **NMOS + PMOS in parallel ≈ 7–12.5 fF/µm², spread 1.06–1.43× over 0.35–0.85 V**; thick NMOS only 1.2–4.4 fF/µm² (no better than MIM). Gate leakage at 125 °C for 355 pF: 0.04–3.8 µA (thin), 0.5–2.0 µA for the complementary pair | **C1 and C2 as complementary thin-oxide pairs** (NMOS to ground ∥ PMOS to V_DD), ≈ 0.04 mm² for C2. The leakage is far above the 100 nA I had assumed, but the reference spur it causes is still small: `pll_model.py --presc --ileak 2e-6` → ≤ −116 dBc, 10 µA → ≤ −102 dBc (limits TX −67, RX −84 dBc). It also adds a static phase offset like the D18 offset current; checked in closed loop (P2.6) |
| **MMD 2/3 cell (D16)** | TSPC, size 2: ÷2 to ≥ 3.3 GHz, ÷3 to 2.9 GHz at the slow corner (fails at 3.3); 10 of 10 mismatch samples correct in each mode at 2.2 GHz | **Passes** (2.9 / 2.2 = 1.32×, just above the 1.3× rule); first cell in TSPC as proposed |

**Second run (`cp2`): plain current sources, L = 2 µm** (NMOS 15 µm, PMOS 60 µm per 25 µA), switches NMOS 8 / PMOS 16 µm:

| Corner | Up side usable to | Down side | Raw mismatch over 0.25–0.95 V | Leakage, 125 °C |
|---|---|---|---|---|
| tt 1.2 V | 1.00 V | to 0.25 V (mismatch at 0.25 V only +1…+3 %) | +3 … −15 % | 2.5–14 nA net |
| ff 1.32 V | 1.05 V | to 0.25 V | +3 … −21 % | up to 90 nA net |
| ss 1.08 V | **0.80–0.85 V** | to 0.25 V | +3 … −32 % (the up side leaves saturation above 0.85 V) | — |

The "compliance" column of the run (5 % of the value at 0.6 V) mostly measures the current's slope with output voltage (channel-length modulation), not loss of saturation; that slope is what the replica amplifier removes. **Conclusion:**
- Plain long-channel sources reach 0.25–0.95 V at typical and fast; only the slow corner at 1.08 V ends at 0.80–0.85 V on the up side. Step 2 makes the PMOS source twice as wide (V_ov ≈ 0.1 V) and its switch 24 µm, and runs the pump from the regulated analogue supply (`VR_ANA1`, a few % tolerance rather than −10 %).
- The replica amplifier must correct up to about ±30 % mismatch to ≤ 1 % → loop gain ≥ 30–40 dB, output range covering the PMOS gate over the window.
- Leakage (pump plus MOS capacitors) totals a few µA at 125 °C; reference spur ≤ −102 dBc even at 10 µA (§7 table above).

**Changes to §2 from step 1:** charge pump with plain long-channel (L = 2 µm) sources instead of cascodes, plus the replica amplifier and offset current (D18 unchanged); C1 and C2 as complementary thin-oxide MOS pairs (D17 unchanged: MOS for C1/C2); tuning window 0.25–0.95 V (calibration aims at the middle, about 0.6 V); MMD first cell in TSPC confirmed.

**Step 2 (next), in three parts:** (a) PFD with reset delay, charge pump with replica amplifier, dummy branch and offset current, loop filter — dead zone, up/down match across 0.25–0.95 V in transient, ripple; (b) the full MMD (6 cells with range extension) — every modulus 23–73, speed at slow corner; (c) Σ-Δ MASH 1-1-1, lock detector and calibration as RTL with a Python reference model.

## 8. Step 2a — PFD and charge pump (2026-10-22)

Source: `analog/pll/step2/` `[SCH]`; tt / ss / ff, V_tune 0.25 / 0.6 / 0.95 V, I_cp 100 µA, 36 MHz. Transistor-level PFD and pump; the replica amplifier and the dummy-node follower are still behavioural (Verilog-A).

**Circuit as simulated:**
- **PFD:** two static master-slave flip-flops (D = 1, transmission gates, NOR reset); reset = AND(UP, DN) through NAND + 2 inverters + NAND with a power-on reset; UP and DN buffered by two inverters each.
- **Charge pump:** long-channel sources (L = 2 µm; NMOS 15 µm and PMOS 120 µm per 25 µA); current steering to the output or to a dummy node at V_tune. Each switch pair is driven by an inverter and a matched always-on transmission gate. Replica branch with an amplifier on the PMOS gate, Miller-compensated (2 pF) with the replica stage.
- **Offset current (D18):** NMOS sink from the pump bias, 0.2 × the unit width.

| Result | tt | ss (1.08 V, 125 °C) | ff (1.32 V, −40 °C) |
|---|---|---|---|
| Dead zone | none (±3 ps resolved) | none | none |
| Reset pulse | 285 ps | 451 ps | 188 ps |
| Static match (DC check, tt) | within 0.1 % at 0.25–0.95 V | — | — |
| Replica node − V_tune | −2 mV | −2 mV | −1 … +20 mV |
| Offset at dt = 0, no offset current | −20 … +54 ps | +33 … +75 ps | −50 … +30 ps |
| Pump gain (both sides, no offset current) | 1.11–1.24 | 1.12–1.21 | 1.10–1.27 |
| **INL on the locked side** (with offset current, dt 1–5 ns) | **≤ 0.4 ps** | **≤ 1.0 ps** | **≤ 0.2 ps** |
| Lock point (UP lead) | 3.2–3.6 ns | 3.6–4.0 ns | 2.9–3.2 ns |
| Offset current | 11–15 µA | 13–16 µA | 10–14 µA |

**What it means:**
- With the offset current the pump works on the UP side only, where it is linear to ≤ 1 ps over a 4 ns range. The Σ-Δ moves the divider edge by about ±1 ns, which is 0.05 % of nonlinearity at most. The offset and the two-sided gain mismatch no longer matter.
- The offset current is about 10–16 % of I_cp (intended about 8 %), because the narrow sink does not mirror the wide diode exactly. A lock point of 2.9–4.0 ns leaves ample margin over ±1 ns. It can be trimmed to about 0.15 × in the final sizing; the in-band pump noise rises by about 1 dB at this offset (§4, D18).
- The 15 % difference between the UP slope and the DC up current, and the offset at dt = 0, come from switching transients. They are harmless on one side, and are kept as known behaviour.

**Transistor-level amplifiers (2026-10-25, runs 9–12).**
- **Replica amplifier and dummy-node buffer** are rail-to-rail-input *symmetric* transconductors: an NMOS pair and a PMOS pair, each pair's currents mirrored to the output, so the output range does not depend on the input common mode. A simple version (output at the pair drains) lost the NMOS pair's headroom at 0.95 V.
  - Replica amplifier: 2 µA tails, Miller 5 pF.
  - Buffer: 10 µA tails, mirror gain 3, 10 pF on the dummy node.
  - Their bias currents are still ideal references; that is the bias-generator block, still to come.
- **Offset current pair:** with the offset current the dummy node receives −I_off on average when locked. A matching PMOS source into the dummy node cancels it, so the buffer only handles the difference.
- **Unit fingers:** every mirror and current-source device is built from gate fingers of one width per type (NMOS 1.5 µm, PMOS 6 µm), and ratios are finger counts. Single wide fingers of very different width did not keep their ratio: the offset source came out 2–3× too strong and saturated the buffer.

| Result (transistor amplifiers) | tt | ss (1.08 V, 125 °C) | ff (1.32 V, −40 °C) |
|---|---|---|---|
| Replica node − V_tune (DC) | −2 … +4 mV | — | — |
| Offset sink / source into dummy | 9.5–11.8 / 9.7–10.8 µA | 9.6–11.4 / 9.7–12.7 µA | 9.6–12.1 / 9.7–11.4 µA |
| **INL, locked side, dt 1–5 ns** | **0.4–2.4 ps** | **0.8–1.9 ps** at 0.25 / 0.6 V; **19 ps at 0.95 V** | **0.2–3.6 ps** |
| Lock point | 2.75–3.05 ns | 2.70–2.76 ns (1.53 ns at 0.95 V) | 2.77–2.94 ns |
| Dummy node − V_tune (transient) | −42 … +11 mV | −28 … +8 mV (+25 … +51 at 0.95 V) | −29 … +14 mV |

**The one weak case: slow corner, 1.08 V supply, V_tune 0.95 V.** The up source has too little voltage left there (step 1: up side to 0.80–0.85 V at ss), so its current depends on the switching state: slope 1.51 and INL 19 ps (0.97 % of the ±1 ns range). In use this case is unlikely:
- the calibration centres V_tune near 0.6 V and the drift after lock is about ±0.1–0.2 V;
- the pump runs from the regulated `VR_ANA1` (a few % tolerance, not −10 %).

It is recorded as the window limit at the slow corner (about 0.85 V), not fixed here. Closed-loop spurs including it are checked in P2.6.

**Step 2a done.** Next: 2b — the multi-modulus divider (6 divide-by-2/3 cells with range extension, every ratio 23–73, speed at the slow corner); then 2c — Σ-Δ, lock detector and calibration as RTL; then the bias generator for the amplifiers.

## 9. Step 2b — multi-modulus divider (2026-10-25)

Source: `rtl/afe/mmd.sv`, tests `rtl/afe/cocotb/` (cocotb, icarus) `[RTL]`.

**Structure changed from §2 item 5.** The full Vaucher chain of six 2/3 cells with range extension was built first and fails with a new ratio every cycle (about a third of the periods wrong).
- The last active cell makes its decision for the next cycle before the first cell has decided the current one.
- Where that falls relative to the output pulse moves with N and with the chain length, which changes inside the operating range (23–73 crosses 32 and 64).
- The cells therefore mixed program bits of two ratios. Per-cell retiming variants did not remove this.

**Now a pulse-swallow divider**, the classic structure for fractional-N:
- **Prescaler:** divide-by-4/5 built from two step-1 2/3 cells. The second cell's bit is fixed at 0, so its early decision is harmless.
- **Counters:** a 5-bit program counter and a 2-bit swallow counter on the prescaler output (≤ 550 MHz, standard cells).
- **Ratio:** N = 4 · n[6:2] + n[1:0]; the prescaler divides by 5 for the first n[1:0] of the n[6:2] cycles.
- **Range:** any N from 16 to 127.
- **Loading:** the whole ratio is loaded at one instant per cycle, so every cycle uses exactly one ratio.

| Test | Result |
|---|---|
| Every ratio 16–127, constant | all periods = N |
| New ratio every cycle: 400 random in 23–73 (crossing 32 and 64), 400 Σ-Δ-like N0 + (−3 … +4) | **all 786 periods correct**, latency one cycle |

Consequences:
- The fast part is two 2/3 cells at ≤ 2.2 GHz. Step 1's cell passes to 2.9 GHz at the slow corner, with 10/10 mismatch samples correct.
- The divide-by-5 control is a flip-flop on the prescaler clock and must settle within about 0.9 ns after the prescaler edge (at 2.2 GHz). That is checked in the AFE block's timing.
- Current: the two TSPC cells ≈ 0.2–0.3 mA at 2.2 GHz; the counters < 0.1 mA. That fits the §3 estimate.

**Next:** 2c — the Σ-Δ modulator (MASH 1-1-1, 24 bits, dither), lock detector and band calibration as RTL against a Python reference model.

## 10. Step 2c — Σ-Δ, lock detector, band calibration (2026-10-25)

Source: `rtl/afe/sdm.sv`, `lockdet.sv`, `bandcal.sv`, tests and Python reference models in `rtl/afe/cocotb/` `[RTL]`.

| Block | Function | Result |
|---|---|---|
| Σ-Δ | MASH 1-1-1, 24-bit, LSB dither (LFSR x²³ + x¹⁸ + 1). On a load, {N_INT, N_FRAC} is divided by P = 2 / 3 (D16) with a 32-cycle restoring divider; the error is ≤ 2⁻²⁴ in M, < 0.3 Hz at RF. div_n = M_int + y, y in −3 … +4. Integer-N mode (`PLL_CTRL[1]` = 0) | Bit-exact against the Python model for 7 settings × 2000 cycles; mean within 2·10⁻³ of M; range correct |
| Lock detector | UP / DN sampled at reference + window (≈ 6.5 ns, from an analogue delay cell, to cover the 2.9–4 ns locked UP pulse plus ±1 ns Σ-Δ wander); 64 good cycles → lock, 4 bad → unlock. **Made two-sided in step 4 (§12):** sampling DN at the reference edge only saw an early divider when it led by more than T_ref − t_w ≈ 21 ns | Lock after 64 cycles; held with ±1 ns wander; cleared by UP or DN errors within 4–6 cycles |
| Band calibration | Successive approximation over the 7-bit bank with V_tune held (hold output). For each trial: 16 cycles settling, then the prescaler output (f_VCO / 4P, ≤ 550 MHz) counted for 128 reference cycles against K·M/4. Ends on the highest code whose frequency is ≥ target | Six targets 3.12–4.20 GHz on a VCO model: correct within the counting resolution (0.06 % at P = 2, 0.08–0.11 % at P = 3 — corrected in step 4; a band step is 0.2–0.5 %); **29.2 µs** per calibration (30.5 µs since step 4, §12) |

**Notes:**
- The calibration counts the prescaler output, not the MMD output. That gives about 1600 counts per step instead of about 128, so 128 reference cycles per step are enough.
- The total of 29 µs calibration plus 125 µs lock is 154 µs (155.5 µs with the step-4 first-trial settling), at the 150 µs wake budget. If needed: K = 64 (15 µs, resolution 0.12 %, still below a band step), or a faster loop after the calibration.
- Still to come: the window delay cell, the hold switch on V_tune, and the bias generator. The four RTL blocks are integrated into the AFE/LO control block at Phase 5.

## 11. Step 3 — Monte Carlo, fractional spurs, current (2026-10-25)

Source: `analog/pll/step3/` (`run_step3.py`, `pll_behav.py`); run outputs `out/summary_mc.txt`, `summary_spur.txt`, `summary_cur.txt`.

**Monte Carlo** `[SCH]`: the step-2a PFD, charge pump, both amplifiers and the offset pair, with PDK mismatch on every transistor (σ(V_T) 3.9 / 2.2 mV·µm, σ(β) 0.5 / 0.33 %·µm, σ(W) 4 nm, σ(L) 2 nm). Ten samples per case plus the nominal run, Q(dt) at 1–5 ns of UP lead, I_cp 100 µA, 36 MHz.

| Corner | V_tune | INL nominal (ps) | INL mean / max (ps) | Lock point mean / min / max (ns) | Slope mean / σ | Offset current mean / σ (µA) | Supply (mA) |
|---|---|---|---|---|---|---|---|
| tt | 0.25 | 0.6 | 0.6 / 0.6 | 2.76 / 2.69 / 2.84 | 0.946 / 0.005 | 9.6 / 0.1 | 0.39 |
| tt | 0.6 | 0.4 | 0.4 / 0.5 | 2.76 / 2.70 / 2.83 | 1.059 / 0.005 | 10.9 / 0.1 | 0.43 |
| tt | 0.95 | 2.0 | 2.2 / 3.9 | 3.05 / 2.96 / 3.13 | 1.031 / 0.006 | 11.8 / 0.2 | 0.41 |
| ss | 0.6 | 0.7 | 0.7 / 0.7 | 2.75 / 2.68 / 2.83 | 1.021 / 0.004 | 10.7 / 0.1 | 0.41 |

Mismatch barely changes the linearity: the replica loop absorbs up/down mismatch, and the long-channel sources and unit-finger mirrors keep the offset current within 1–2 %. The lock point moves by at most ±0.09 ns, far inside the 1.2–4.4 ns that the Σ-Δ sequence spans around it, so the pump always works on one side (D18). The slope (loop gain) varies by ≤ 0.6 %. Not in the Monte Carlo: ff (nominal passes, step 2a) and ss at 0.95 V (outside the slow-corner window limit, §8).

**Fractional spur at the boundary offset** `[MODEL]`: a cycle-by-cycle phase-domain PLL (`pll_behav.py`) with the real MASH 1-1-1 sequence (bit-exact to `rtl/afe/sdm.sv`), the P2.2 loop filter solved exactly between charge packets, and each measured Q(dt) curve's deviation from a straight line applied to every cycle. The channel is placed so that the fractional spur falls on the duplex offset (600 kHz VHF, 2 MHz UHF). Limit at RF −95 dBc (25 W duplex).

| Curve | VHF spur (dBc at RF) | UHF spur (dBc at RF) |
|---|---|---|
| Linear pump (reference) | −126.7 (Σ-Δ floor −134.0) | −121.6 (floor −132.0) |
| Nominal, all four cases | −125.4 … −124.4 | −121.6 |
| Worst-INL sample, tt 0.95 V (3.9 ps) | −117.4 | −121.6 |
| **Worst** | **−117.4** (22 dB margin) | **−121.6** (27 dB margin) |

- The UHF value is the same as with a linear pump: it is a residual of the model at that fractional word, and the pump's contribution stays below it (UHF has 10 dB less division credit than VHF, but its divider edge spans only 1.7–3.8 ns, where the curves are straightest).
- The model takes the INL as a timing deviation (independent of I_cp to first order) and runs at the P2.2 design point (50 µA · 40 MHz/V); the curves were measured at 100 µA.
- This replaces the raw boundary-spur input S0 of the P2.2 model (budget −35 dBc at VHF) with a computed result.

**Current** `[SCH]` + `[HAND]`:

| Block | mA | Source |
|---|---|---|
| Reference buffer (36 MHz) | 0.15 | hand |
| PFD, charge pump, replica amplifier, dummy buffer, offset pair | 0.43 | schematic, worst case |
| Amplifier bias generator | 0.03 | hand |
| MMD prescaler (two TSPC 2/3 cells ≤ 2.2 GHz) | 0.25 | hand, from P2.4 TSPC |
| MMD counters (≤ 550 MHz) | 0.05 | hand |
| Σ-Δ, lock detector, calibration | 0.10 | hand (≈ 1500 gates) |
| **PLL total** | **1.01** | budget ≤ 1.8 mA (D7) |

**Against §1:** boundary spur met with ≥ 22 dB margin; no dead zone; current 1.0 mA of 1.8 mA; calibration plus lock at the 150 µs wake budget (§10). **Still open, for P2.5 step 4 or P2.6:** the amplifier bias generator (amplifier biases are still ideal), the lock-detector window delay cell, the V_tune hold switch; the reference spur at 36 MHz from the offset current and loop-filter leakage (step 1 leakage model ≤ −102 dBc) and the divider noise floor in closed loop (P2.6).

## 12. Step 4 — bias generator, window delay cell, hold switch (2026-10-25)

P2.5 result review: accepted by the owner 2026-10-25, with step 4 for the three blocks that were still ideal or missing. Source: `analog/pll/step4/run_step4.py`, `rtl/afe/lockdet.sv`, `rtl/afe/bandcal.sv`.

**Bias generator.** V_REF / R_B = 0.4 V / 40 kΩ = 10 µA master current. A rail-to-rail transconductor (the step-2a design) drives the master PMOS gate so that V_REF sits across R_B; it is biased from the generator's own outputs, so a start-up circuit (weak pull-up, sensing NMOS, pull-down on the PMOS gate) removes the zero-current state. All outputs are mirrors of 1 µA unit fingers (PMOS 2/2 µm, NMOS 1/2 µm):

| Output | Value | Use |
|---|---|---|
| I_cp DAC, `PLL_CTRL`[5:3] | (code + 1) × 25 µA: segments 25 (always on) + 25 + 50 + 100 µA, PMOS series switches | Charge-pump reference (NMOS diode `nb`) |
| Amplifier tails | 2 µA (replica amplifier), 10 µA (dummy buffer), sources and sinks | Step-2a transconductors |
| Window cells | 4 µA each | Delay cells below |

I_cp follows V_REF / R_B. With R_B of the same resistor type as the loop-filter R1, the product I_cp · R1, and so the loop bandwidth, does not depend on the resistor's absolute value. V_REF (0.4 V) comes from the chip reference (shared block, not yet designed; an ideal source until then). In the final pump the source segments switch with the code too, so the current density stays as in step 2a.

**Window delay cell, and the lock detector made two-sided.** A rising edge sets a flip-flop, which releases a MIM capacitor (≈ 33 fF) charged by 4 µA; an inverter pair is the threshold, and its output resets the flip-flop (self-timed strobe, so the 2.5 ns MMD output pulse is enough). Delay ≈ C · V_th / I + gate delays: target 7 ns, allowed 5–12 ns (above the 4.7 ns locked UP pulse including reset; below T_ref / 2). Two identical cells: reference + t_w samples UP (divider late by more than t_w), divider + t_w samples DN (divider early by more than t_w). The step-2c detector sampled both at the reference strobe only, and a DN pulse ends at the reference edge, so an early divider was seen only beyond T_ref − t_w ≈ 21 ns; with a frequency error below about 1.2 % it could report lock. Two-sided, a phase walk of 0.25 ns per cycle (≈ 0.9 % frequency error) no longer locks (`test_lockdet.py`, three tests pass).

**V_tune hold switch.** During band calibration, transmission gates (NMOS 10 µm, PMOS 20 µm) connect the charge-pump node and the C2 node of the loop filter to V_DD / 2 from a 2 × 1 kΩ divider that is on only during hold (≈ 0.6 mA for ≈ 30 µs per calibration). Holding the C2 node directly avoids the R1·C2 = 3.4 µs time constant; the expected time constant is ≈ 0.4 µs. The first calibration trial now settles for 64 reference cycles (`bandcal.sv` SETTLE0) so that the loop filter can come from anywhere in 0–1.2 V; later trials only change the bank (16 cycles). Calibration 30.5 µs instead of 29.2 µs. Limit: V_tune within 10 mV on average over the first count (0.4 MHz at the VCO, a tenth of a count).

**Correction (counting resolution):** one count is 4 / (K·M) — 0.06 % at P = 2 (≈ 1600 counts) but 0.08–0.11 % at P = 3 (920–1250 counts), not ≤ 0.06 % everywhere. The decision is exact to about two counts (gate ± one prescaler cycle, truncated target); still below a band step (0.2–0.5 %). The calibration test now uses that tolerance.

Results: pending (`run_step4.py`: `bias`, `start`, `win`, `hold`, `lin`).
