# PLL system model (Phase 2, step P2.2)

Linear model of the HT13G-M synthesizer (`spec/phase2-plan.md`), used to set the loop parameters and the VCO target before circuit work. **Every input is a proposal `[PROP]`, not a circuit result.** Status: first run, 2026-10-19.

```bash
python3 analog/pll-model/pll_model.py              # default case (150 kHz loop)
python3 analog/pll-model/pll_model.py --bw 125e3   # other loop bandwidth
python3 analog/pll-model/pll_model.py --help       # all inputs
```

## Model

- **Loop:** type-II charge-pump PLL, fPFD = reference (32 or 36 MHz), 3rd-order passive filter (C1 ∥ (R1 + C2)) plus an extra RC pole at 8 × bandwidth, designed for the given bandwidth and 55° phase margin.
- **Noise sources** referred to the VCO, divided to RF by 24 (VHF) or 8 (UHF):
  - VCO: L(1 MHz) with −20 dB/decade and a 1/f³ corner;
  - PFD/charge pump: figure of merit −218 dBc/Hz plus a 1/f corner;
  - reference (TCXO) profile;
  - loop-filter resistors R1 and R3 (thermal);
  - MASH 1-1-1 quantisation noise.
- **Spurs:**
  - Integer-boundary spur: a raw level S0 at the VCO, attenuated by the loop at the duplex offset and by 20·log10(N).
  - Reference spur: from charge-pump leakage (fundamental of the leakage-compensation pulses through the loop filter, narrow-band FM).
- **Lock:** linear step response of the frequency error, 1/(1 + G(s)), from a 2 MHz VCO residual (after the coarse band calibration) to 10 Hz at RF.

Inputs (defaults, all `[PROP]`):

| Input | Value |
|---|---|
| VCO L(1 MHz), 1/f³ corner | −116 dBc/Hz (plan target), 200 kHz |
| Kvco per capacitor-bank band | 40 MHz/V |
| Charge-pump current | 50 µA |
| PFD/CP figure of merit, 1/f corner | −218 dBc/Hz, 20 kHz |
| TCXO L(f), 100 Hz … 10 MHz | −110, −135, −150, −155, −158, −160 dBc/Hz |
| MASH order | 3, 24-bit |
| Raw boundary spur S0 | −45 dBc |
| Charge-pump leakage | 1 nA |

## Results (default run, 150 kHz loop)

All 8 corners of the frequency plan (32 / 36 MHz × VHF / UHF × band edges) pass:

| Check | Result | Limit |
|---|---|---|
| Phase noise at 600 kHz, VHF (RF) | −137.2 … −137.3 dBc/Hz (VCO −137.7, R −146 … −148, CP −161 … −164, Σ-Δ −170 … −173) | ≤ −136 |
| Phase noise at 2 MHz, UHF (RF) | −139.4 … −139.5 dBc/Hz (VCO −139.7, Σ-Δ −164 … −167) | ≤ −136 |
| Boundary spur at the duplex offset (hit channels) | −105.5 dBc VHF, −120.0 dBc UHF | ≤ −95 dBc |
| Largest raw boundary spur S0 that still passes | **−35 dBc (VHF)**, −20 dBc (UHF) | design target for the charge pump / Σ-Δ |
| Reference spur from 1 nA leakage | ≤ −182 dBc (−151 dBc at 100 nA) | ≤ −67 dBc |
| Frequency resolution at RF | ≤ 0.24 Hz | ≤ 10 Hz |
| Linear lock time, 2 MHz → 10 Hz at RF | **125 µs** | ≤ 150 µs (plus band calibration) |
| Loop filter (N ≈ 114) | C1 39 pF, C2 355 pF, R1 9.5 kΩ, R3 34 kΩ, C3 3.9 pF; **≈ 400 pF in total** | on chip |

Sensitivity:
- **Loop bandwidth:** 100 kHz locks in 187 µs (fails 150 µs), 125 kHz in 150 µs (no margin), 150 kHz in 125 µs. → use **150 kHz** (top of the D5 range).
- **VCO noise is the binding term at VHF:** L(1 MHz) = −115 dBc/Hz still passes (−136.3), −114 fails (−135.4). The VCO target of **≤ −116 dBc/Hz at 1 MHz** in the plan stands, with no slack below −115.
- **Loop-filter area:** ≈ 400 pF is about 0.05 mm² as MOS capacitors or 0.27 mm² as MIM (densities `[PROP]`). The charge-pump current sets it: halving Icp halves the capacitance and raises the charge-pump noise share.

## What this model does not cover

- Non-linear effects: charge-pump mismatch folding Σ-Δ noise into the band, PFD dead zone, cycle slips. They set the real S0; the model only gives the budget (S0 ≤ −35 dBc at VHF).
- Coupling paths for the reference spur (supply, substrate, PFD reset pulse). The leakage figure is the textbook mechanism only.
- Coarse band-calibration time, which adds to the 125 µs.
- Flicker noise of the VCO beyond a single corner frequency.

These move to P2.5 / P2.6 (transistor-level charge pump and closed-loop simulation).
