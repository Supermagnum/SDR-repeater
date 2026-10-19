# Phase-noise validation (VACASK pnoise)

Purpose: decide whether VACASK's `pnoise` (oscillator mode) can be trusted for the
Phase 2 VCO, before any VCO design depends on it.

**Status: validated, 2026-10-19 — OVERALL PASS.** VACASK fb8cc20, IHP SG13G2 PDK in
`hpretl/iic-osic-tools:2026.10`.

## Result

| Check | Result | Limit |
|---|---|---|
| Level 1: pnoise vs exact closed form, 100 kHz–20 MHz | worst **0.19 dB** (0.0 dB from 100 kHz to 5 MHz) | ≤ 1 dB |
| Level 1: transient noise vs closed form (1/Δf² fit, 2–20 MHz, at 1 MHz) | −123.65 vs −124.60 dBc/Hz, **+0.96 dB** | ≤ 1 dB |
| Level 2: pnoise vs transient noise (same fit, at 1 MHz) | −123.96 vs −124.46 dBc/Hz, **+0.50 dB** | ≤ 1.5 dB |
| Level 2: pnoise inside the Leeson band (F = 1.5–3) ± 3 dB | 100 % of offsets | plausibility |

Level 1 oscillates at 3.4996 GHz with A₁ = 0.463 V. Level 2 (SG13G2) oscillates at
3.6874 GHz with a differential A₁ = 0.914 V and tank Q = 15.8; its pnoise is
−124.0 dBc/Hz at 1 MHz with a clean −20 dB/decade slope from 100 kHz to 20 MHz,
an effective noise factor of about 2.2 (3.4 dB), the textbook value for a
cross-coupled NMOS pair.

Conclusion: VACASK `pnoise` gives correct phase noise for LC oscillators in the
thermal (−20 dB/decade) region, with SG13G2 devices, at the settings below. It can be
used for the Phase 2 VCO in place of hand estimates. HANDOFF §9 ("no PNOISE") is
superseded.

## Limits of this validation

- Only the thermal region was tested. The flicker (−30 dB/decade) region close to the
  carrier was not; Level 2 shows no flicker rise down to 100 kHz. The duplex-offset
  requirements (600 kHz, 2 MHz) are inside the validated range.
- Level 2 uses an ideal inductor and an ideal, noiseless tail current. A real VCO adds
  tail noise, varactor/capacitor-bank loss and inductor loss from EM; those are design
  questions, not simulator questions.
- The transient-noise estimate is statistical: 10 µs gives 6 bins in the fit range,
  about ±1 dB. A 40 µs run would give four times the bins.

## Method

**Level 1: ideal oscillator, exact answer known.** Single-node LC tank (1 nH,
2.0678 pF, 330 Ω, f0 = 3.5 GHz, Q = 15) kept oscillating by a noiseless tanh
negative conductance. The tank resistor is the only noise source, so

    L(Δf) = kT / (R · C² · A² · (2πΔf)²)        (Leeson with F = 1)

with A the fundamental amplitude from the PSS.

**Level 2: SG13G2 devices.** Cross-coupled `sg13_lv_nmos` pair (PSP103, W = 20 µm,
L = 0.13 µm, ng = 4), ideal 1 nH inductors with 1.466 Ω series loss, 1.8 pF per side,
ideal noiseless 2 mA tail, 1.2 V.

**Independent reference.** VACASK transient noise (`noisemode="zoh"`). The waveform is
resampled onto a fixed 5 ps grid, the analytic signal is formed from the band
0.75–1.25 f0 only (harmonics would otherwise appear as phase ripple), the ends are
trimmed (filter ringing), and the phase difference — flat spectrum, no window
leakage — goes through Welch and is divided back exactly; L = Sφ/2. The result is a
fit of the 1/Δf² law over 2–20 MHz, quoted at 1 MHz. Checked on synthetic signals with
known phase noise, harmonics and DC offset: within 0.6 dB.
(`hbnoise` cannot be used: harmonic balance has no oscillator mode in VACASK.)

**Conversion.** `onoise` is a one-sided voltage PSD at f0 + Δf, so
L(Δf) = onoise / (A₁²/2). AM noise is negligible at these offsets.

## Settings that matter

| Setting | Level 1 | Level 2 | Why |
|---|---|---|---|
| `pss_minpts` | 16000 | 8000 | At the default 1000 the 100 kHz point was 3.9 dB low; 4000 gave 0.3 dB, 16000 gave 0.0 dB |
| `reltol` / `pss_tolscale` | 1e-8 / 1e-6 | 1e-7 / 1e-4 | The tighter Level 1 values did not converge with the transistor models (50 shooting iterations) |
| `maxharm` / `truncharm` | 32 / 16 | 32 / 16 | Conversion-matrix harmonics |
| `in=` | dummy zero-valued `isource` | same | `pnoise` aborts with "Instance '' not found" without an `in` source |
| Environment | `PDK_ROOT=/foss/pdks PDK=ihp-sg13g2` | same | A full path in `PDK` doubles the VACASK model paths |

## Run (inside the container)

```bash
cd /foss/designs/analog/pn-validation
./run.sh            # level 1 pnoise, seconds
./run.sh l2         # + level 2 pnoise, about 1-2 min
./run.sh tran       # + transient-noise references, 5-20 min
```
Results: `out/compare.txt`; logs: `out/*.log`.
