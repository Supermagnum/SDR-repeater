# Phase 2 plan — LO and synthesizer

Status: **draft for human review, 2026-10-19. Owner decisions D1–D7 accepted 2026-10-19, D8–D10 (VCO topology, `spec/vco-topology.md`) 2026-10-20; P2.0 done; P2.2 first run done (`analog/pll-model/`).** Nothing in this plan has been designed or simulated yet. It turns `spec/rf-frontend.md` §5 and `spec/derived-limits.md` §9 into budgets, work steps and the decisions the owner has to make before circuit work starts. Topologies are proposals; per the agent rules they are chosen by a human.

---

## 1. What Phase 2 delivers

The local oscillator for the single HT13G-M chain:

- VCO, **3.12–4.20 GHz** (one range for both bands).
- Dividers: **÷8** for 400–480 MHz, **÷24** for 130–175 MHz, with quadrature outputs, and 8 phases on VHF if the harmonic-reject mixer is confirmed (§4).
- Fractional-N PLL: phase-frequency detector and charge pump, loop filter, multi-modulus feedback divider, Σ-Δ modulator, coarse band calibration.
- Reference input from XTB at 32 or 36 MHz.

Output of the phase: reviewed schematics, post-layout simulations with EM-extracted inductors, and a system model that ties them to the limits. **No fabrication** (`docs/HANDOFF.md`).

---

## 2. Budgets

### 2.1 Phase noise

RF requirement (25 W, attenuator baseline): ≤ −136 dBc/Hz at the duplex offset; 5 W: ≤ −129 dBc/Hz. Division lowers phase noise by 20·log10(N) and does not change the offset frequency.

| | VHF (÷24) | UHF (÷8) |
|---|---|---|
| Duplex offset | 600 kHz | 2 MHz |
| Division credit | 27.6 dB | 18.1 dB |
| Allowed at the VCO, at the offset | −108.4 dBc/Hz | −117.9 dBc/Hz |
| Same, referred to 1 MHz (−20 dB/decade) | −112.8 dBc/Hz | −111.9 dBc/Hz |
| **VCO target at 1 MHz** (3 dB for the PLL's own contributions) | **≤ −116 dBc/Hz** | **≤ −115 dBc/Hz** |

Feasibility: the validated SG13G2 test oscillator (ideal 1 nH inductor, tank Q 15.8, noiseless tail, about 2.4 mW) gave **−124 dBc/Hz at 1 MHz** at 3.69 GHz (`analog/pn-validation/`). The EM tank Q (P2.0) is 15.3 at 3.5 GHz and 14.2 at the 3.12 GHz band edge (`spec/provisional-tank-q.md`), 0.3–0.9 dB worse than the test case. A real VCO adds tail noise, varactor and capacitor-bank loss and wide-range penalties; 8 dB of margin over the target is a reasonable starting point but not a result. In figure-of-merit terms the target needs FoM ≥ 177 dB at 10 mW or ≥ 180 dB at 5 mW, which ordinary LC VCOs reach.

Not yet covered: the **flicker region** below about 100 kHz (not validated in VACASK) — it sets in-channel noise, not the duplex limit.

### 2.2 Loop

| Item | Proposal | Reason |
|---|---|---|
| PFD frequency | = reference, 32 or 36 MHz | No reference divider; lowest in-band noise |
| Feedback divider N | ≈ 87–131 (3.12–4.20 GHz / 32–36 MHz) | |
| Loop bandwidth | **150 kHz** (P2.2: 100 kHz locks in 187 µs, 125 kHz in 150 µs, 150 kHz in 125 µs) | Settles in tens of µs (≤ 150 µs wake, ≤ 0.5 ms TX/RX turnaround); well below the 600 kHz / 2 MHz offsets, so the loop filter attenuates Σ-Δ noise and spurs there |
| Σ-Δ modulator | MASH 1-1-1 with dither, ≥ 24-bit | Resolution ≈ fPFD / 2²⁴ / div ≤ 0.24 Hz at RF (requirement ≤ 10 Hz, < 1 Hz preferred) |
| In-band noise | PFD/CP figure of merit ≈ −218 dBc/Hz (conservative) → ≈ −102 dBc/Hz at the VCO, ≈ −130 (VHF) / −120 (UHF) dBc/Hz at RF | Inside the loop only; not at the duplex offsets |
| Loop filter | 3rd or 4th order passive | Attenuation of MASH noise and fractional spurs at 600 kHz / 2 MHz; set by the model in step P2.2 |

### 2.3 Spurs (`spec/derived-limits.md` §9)

- Duplex offset: ≤ −95 dBc (25 W), RX and TX.
- **Integer-boundary channels:** on some 12.5 kHz channels the fractional spur offset equals the duplex offset (VHF: carrier 25 kHz from a boundary; UHF: 250 kHz). With the host's 32/36 MHz choice, 2 channels on 2 m and 5 on 70 cm remain (list in §9). There the spur must be ≤ −95 dBc after the 20·log10(N) division credit and the loop-filter attenuation at the offset. The model in P2.2 decides whether that holds or whether those channels need host-side avoidance.
- Reference spur at ±32 / ±36 MHz: TX ≤ −67 dBc design target; the loop filter gives far more than needed, charge-pump leakage is the risk.

### 2.4 Power

RX ≤ 25 mA and TX ≤ 60 mA for the whole chip (§6 of `spec/rf-frontend.md`). Proposed LO share: **≤ 10 mA** (VCO 2–4 mA, dividers and LO buffers 4–5 mA, PLL 1–2 mA).

---

## 3. Steps and review gates

| Step | Work | Output | Gate |
|---|---|---|---|
| **P2.0** (EM stages 1–2 done: `reports/phase2-review/p20-stage1.md`, `p20-stage2.md`; Q 15.3 at 3.5 GHz accepted 2026-10-20; flicker check done: `reports/phase2-review/p20-flicker.md`) | Prerequisites: matched-mesh, de-embedded inductor study (Phase 0 follow-up); pnoise check of the flicker region | Tank Q to replace the provisional 14.9; flicker method | Owner accepts the EM result |
| **P2.1** | Owner decisions D1–D7 (§5) | Entries in `decisions.md` | — |
| **P2.2** ✅ first run | System model in Python: linear PLL phase-noise model (VCO, PFD/CP, Σ-Δ, loop filter), spur map including the boundary channels, lock-time transient | `analog/pll-model/` with a check script like `vhf_lpf_check.py`; loop parameters (Icp, filter values, KVCO per band, number of bands) | Human review of the budget |
| **P2.3** ✅ schematic (2026-10-20: 2.90–4.41 GHz, all bands, corners and −40/27/85 °C meet §2.1, worst margin +3.6 dB at 1 MHz; result review done, `spec/vco-topology.md` §9; open points there) | VCO: topology memo, schematic, capacitor bank, varactor; VACASK `pnoise` across bands, PDK corners and −40 to +85 °C, with the EM inductor model | Schematic, pnoise table vs §2.1 | Human topology review before schematic; result review after |
| **P2.4** ✅ (topology accepted 2026-10-20; step 1 done: TSPC confirmed, CML ÷2 / ÷3 need ≥ 0.5 V-per-side clock at the slow corner; `spec/lo-divider-topology.md` §7; step 2 done, all 8 cases divide with D15, phase errors ≤ 0.46°, §8; step 3 done 2026-10-21: four fixes, all corners and 100/100 Monte Carlo samples divide, noise floor ≈ −157 / −161 dBc/Hz by hand estimate (simulation in P2.6), §9; accepted by the owner 2026-10-21) | Dividers and phase generation (÷2/÷3 prescaler stages, quadrature, 8-phase for VHF) | Transient across corners: maximum frequency, duty cycle, I/Q phase error (→ image rejection), 8-phase error (→ harmonic rejection) | Human review |
| **P2.5** (topology accepted 2026-10-21, D16–D18, `spec/pll-topology.md`; step 1 done 2026-10-21: long-channel charge pump, complementary MOS loop-filter caps, TSPC 2/3 cell, tuning window 0.25–0.95 V; step 2a core done 2026-10-22: no dead zone, INL ≤ 1 ps with the offset current) | PFD, charge pump, loop filter, multi-modulus divider, Σ-Δ modulator (digital, in the AFE/LO control block: `spec/analog-digital-interface.md` §5) | Schematics; CP mismatch and leakage → spur estimate fed back to P2.2 | Human review |
| **P2.6** | PLL closed loop: behavioural top with transistor-level VCO and divider | Lock time, frequency error, phase noise vs offset, spurs on boundary channels | Compare with P2.2 |
| **P2.7** | Layout of VCO and dividers, PEX, EM on the tank and LO routing; post-layout pnoise | `[PEX-RC]` / `[EM]` tagged results | Phase 2 review gate |

Tools: VACASK (`pss`/`pnoise`, settings in `analog/pn-validation/README.md`), ngspice for cross-checks, openEMS for the inductor, KLayout/Magic/netgen for layout, Python for the system model. All in `hpretl/iic-osic-tools:2026.10`; no new tools needed for P2.2–P2.6.

---

## 4. Architecture proposals (for the decisions in §5)

- **VCO core.** Three candidates: NMOS cross-coupled (the validated test case), complementary CMOS (lower current for the same swing), SiGe HBT cross-coupled or Colpitts (lower flicker noise, larger swing). Proposal: start with the NMOS core because the simulation method is proven on it, and keep an HBT variant as the comparison in P2.3.
- **Tuning range.** 29.6 % in one VCO needs a switched-capacitor bank (about 5–6 bits) plus a small varactor; KVCO stays low per band, which helps noise and spurs. The alternative is two VCO cores, which doubles the inductor area.
- **Dividers and phases.**
  - UHF: ÷8 as ÷2 → ÷2 → ÷2, quadrature from the last stage.
  - VHF: ÷3 (with 50 % duty) → 8-phase Johnson counter (÷8) = ÷24, giving the 8 phases a harmonic-reject mixer needs for ≥ 60 dB 3 × LO rejection (`spec/rf-frontend.md` §3).
  - The first stages run at up to 4.2 GHz: current-mode logic is likely needed there; CMOS after the first ÷2.
- **Σ-Δ modulator location.** The digital back end is full (`phase1l`: 339 617 of 340 000 µm²). A MASH 1-1-1 with 24-bit accumulators is several thousand µm². It needs its own small digital block next to the PLL, or a higher area target for the back end.
- **Band calibration.** A coarse capacitor-bank search at each band change, counted against the reference, inside the 150 µs wake budget.

---

## 5. Owner decisions (D1–D7 accepted as proposed 2026-10-19; D8–D15 2026-10-20; D16–D18 2026-10-21)

| # | Decision | Decided |
|---|---|---|
| D1 | VCO core type | NMOS cross-coupled first, HBT as comparison |
| D2 | One wide-range VCO or two cores | One VCO with a 5–6-bit capacitor bank (bank size changed to 7 bits by D8) |
| D3 | Where the Σ-Δ modulator lives | Separate small digital PLL block; the back end stays at 0.34 mm² |
| D4 | VHF LO phases | 8-phase (÷3 then 8-phase ÷8) for the harmonic-reject mixer |
| D5 | Loop bandwidth | 100–150 kHz; P2.2 picks **150 kHz** for lock time |
| D6 | Integer-boundary channels on the duplex offset | Meet the spur limit in the PLL; host avoidance only if P2.2 shows it cannot |
| D7 | LO current budget | ≤ 10 mA of the RX 25 mA |
| D8 | Capacitor-bank size (2026-10-20) | **7 bits** (KVCO 14–47 MHz/V; keeps the ≈ 400 pF loop filter, `spec/vco-topology.md` §5) |
| D9 | VCO tail (2026-10-20) | NMOS tail, RC-filtered bias (pole ≤ 10 kHz), tail capacitor 5–10 pF; class-C as a P2.3 variant |
| D10 | VCO supply (2026-10-20) | Dedicated LDO, voltage set by the LV device limits (about 1.1 V after step 1) |
| D11 | Varactor bias (2026-10-20) | AC-coupled `sg13_hv_svaricap` (coupling MIMs about 5×, gates biased through ≥ 200 kΩ), so the charge pump and loop filter stay on 1.2 V devices |
| D12 | LO current (2026-10-20) | LO budget stays ≤ 10 mA (D7); the VCO tail current is capped at **4 mA** (`VCO_BIAS`), about 2 dB less phase-noise margin at the bottom of the band |
| D13 | UHF LO waveform (2026-10-20) | Four phases at **25 % duty** from a Johnson ÷4 after a CML ÷2 (`spec/lo-divider-topology.md`) |
| D14 | Divider flip-flops after the first stage (2026-10-20) | **CMOS true single-phase clock (TSPC)**; CML only if step 1 shows < 1.3× speed margin at slow corner / 1.08 V / 125 °C |
| D15 | Divider start-up (2026-10-20) | **Sequenced enable:** `en_lodiv` about 1 µs after `en_vco`, re-pulsed after a band change or a failed lock (a CML divider on during VCO start-up can stay free-running at the slow corner) |
| D16 | PLL feedback-divider clock (2026-10-21) | From the LO chain's first CML stage (÷2 UHF / ÷3 VHF); MMD in CMOS; own CML prescaler is the fallback |
| D17 | Loop-filter capacitors (2026-10-21) | MOS capacitors for C1 and C2, MIM for C3 (≈ 0.06 mm²) |
| D18 | Charge-pump linearisation (2026-10-21) | Offset current ≈ 5–10 % of I_cp plus replica-feedback up/down matching |

---

## 6. Risks

| Risk | Effect | Mitigation |
|---|---|---|
| Real tank Q below the EM value (15.3 at 3.5 GHz) | VCO noise up | EM study done (P2.0, conservative value); bigger margin from higher swing or the HBT core |
| Inductor L ±3 % (solver offset) | VCO band shifts ±1.5 % | Capacitor bank covers 3.12–4.20 GHz over 1.64–1.70 nH (P2.3) |
| 29.6 % tuning range | Q of the capacitor bank, band gaps | Simulated (P2.3): covered at all corners; after the review (+5 % bank) the least margin is 73 MHz at the bottom edge (MIM best case) |
| First divider at 4.2 GHz across corners | Lost lock at slow corner | Checked (P2.4 step 1): CML ÷2 / ÷3 divide over the whole window at slow 1.08 V 125 °C if the clock swing is ≥ 0.4 V per side; the VCO buffer is designed for ≥ 0.5 V. Step 2: a divider on during VCO start-up can stay free-running → sequenced enable (D15). Step 3: ÷3 ÷2-mode at ff/125 °C and with mismatch fixed by stronger latch regeneration; UHF converter duty fixed; all corners and Monte Carlo pass |
| Flicker and 2 f0 tail noise | Unfiltered tail mirror: flicker corner 615 kHz, about 3 dB at the 600 kHz duplex offset; tail noise near 2 f0 a second path (P2.0, `reports/phase2-review/p20-flicker.md`) | Tail and varactor-bias low-pass and a 2 f0 tail filter (or tail-less / HBT core) in the P2.3 topology memo; `pnoise` is validated for this region |
| Σ-Δ area | Back end full | D3 |
| Charge-pump leakage and mismatch | Reference and fractional spurs | P2.5 spur estimate, fed into P2.2 |
