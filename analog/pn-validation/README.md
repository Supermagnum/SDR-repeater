# Phase-noise validation (VACASK pnoise)

Purpose: decide whether VACASK's `pnoise` (oscillator mode) can be trusted for the
Phase 2 VCO, before any VCO design depends on it.

**Status: validated, 2026-10-19 — OVERALL PASS.** VACASK fb8cc20, IHP SG13G2 PDK in
`hpretl/iic-osic-tools:2026.10`.

**Flicker region (P2.0): validated 2026-10-20.** Level 3 (exact) worst 0.2 dB at
`pss_minpts` 64 000; Level 4b (SG13G2, real tail, tone injection) worst 0.48 dB. Summary:
`reports/phase2-review/p20-flicker.md`.

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
  requirements (600 kHz, 2 MHz) are inside the validated range. Levels 3 and 4 below
  (P2.0) test the flicker region: **Level 3 passes (0.2 dB, 10 kHz–20 MHz) with
  `pss_minpts` 64 000; Level 4b passes (0.48 dB)** (2026-10-20).
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
| `pss_minpts` (flicker, levels 3–4) | 64000 | 64000 | Rule: `pss_minpts` × lowest offset ≥ 5·10⁸ for ≤ 0.3 dB (16 000 points: 10 kHz 1.9 dB low, 30 kHz converged) |
| `reltol` / `pss_tolscale` | 1e-8 / 1e-6 | 1e-7 / 1e-4 | The tighter Level 1 values did not converge with the transistor models (50 shooting iterations) |
| `maxharm` / `truncharm` | 32 / 16 | 32 / 16 | Conversion-matrix harmonics |
| `in=` | dummy zero-valued `isource` | same | `pnoise` aborts with "Instance '' not found" without an `in` source |
| Environment | `PDK_ROOT=/foss/pdks PDK=ihp-sg13g2` | same | A full path in `PDK` doubles the VACASK model paths |

## Flicker region (levels 3 and 4, P2.0)

In a real VCO, low-frequency (flicker) noise from the tail and the varactor bias reaches
the carrier phase by modulating the oscillation frequency, which gives the −30 dB/decade
region below the flicker corner. Levels 3 and 4 check that `pnoise` translates
low-frequency noise to the carrier correctly.

**Level 3: exact answer known** (`level3_flicker_fm.sim`). The Level 1 oscillator with
0.2 pF of its 2.0678 pF made a linear varactor (0.1 pF/V). Its control node carries only
a pure 1/f noise voltage, S_v = 10⁻¹⁰/f V²/Hz (Verilog-A `flicker_noise`). With
K = f0 · 0.1 pF / (2 · 2.0678 pF) = 84.6 MHz/V,

    L(Δf) = kT / (R C² A² (2πΔf)²) + K² S_v(Δf) / (2 Δf²)

(thermal Level 1 term plus narrow-band FM), with the flicker corner near 1 MHz, so both
regions are tested from 10 kHz to 20 MHz. It is run with `pss_minpts` 16 000 and 64 000,
because the lowest offsets are the most sensitive to it. Pass: the 64 000 run is within
1 dB of the closed form at every offset.

First run (2026-10-20), L(Δf) in dBc/Hz:

| Offset | Closed form | pnoise 16 000 | pnoise 64 000 |
|---|---|---|---|
| 10 kHz | −64.4 | −66.3 (−1.9 dB) | −64.6 (−0.2 dB) |
| 30 kHz | −78.6 | −78.9 (−0.3 dB) | −78.7 (−0.1 dB) |
| 100 kHz – 10 MHz | −94.1 … −144.2 | 0.0 dB | 0.0 dB |
| 20 MHz | −150.4 | −150.2 (+0.2 dB) | +0.2 dB |

So `pnoise` translates 1/f noise to the carrier correctly once the PSS has enough points.
The error depends on the product `pss_minpts` × Δf: 16 000 points are converged
(≤ 0.3 dB) from 30 kHz (product ≥ 4.8·10⁸), and Level 1 showed the same pattern at
100 kHz (1 000 points: −3.9 dB; 4 000: −0.3 dB).

**Level 4: SG13G2 with a real tail** (`level4_sg13_tail.sim`). Level 2 with the ideal tail
replaced by an `sg13_lv_nmos` 1:4 mirror (L = 0.5 µm, no bias filter capacitor), so the
devices supply flicker noise and the tail current is modulated by the oscillation. There
is no closed form. The reference is VACASK transient noise, which also generates flicker
noise (`noisefmin` = 10 kHz), over 80 µs (`level4_tran.sim`). Both are reduced to
L(Δf) = a/Δf³ + b/Δf² by a least-squares fit over 50 kHz–20 MHz. Pass: the fits agree within
1.5 dB at 600 kHz and 1 MHz and within 2.5 dB at 100 kHz. Those limits come from a
synthetic check of the transient method with known phase noise (80 µs, corner 300 kHz,
6 seeds): bias < 0.05 dB, scatter 0.9 / 0.37 / 0.25 dB (1σ) at 100 kHz / 600 kHz / 1 MHz.
Level 4 is judged only if `pnoise` shows a flicker region (≥ 3 dB above the 1/Δf² line at
100 kHz); otherwise it validates nothing new and the mirror is changed. Level 4 now runs
`pnoise` with 64 000 points.

First `pnoise` result (2026-10-20, 16 000 points): f0 3.690 GHz, differential A1 0.96 V,
1/Δf² level −122.9 dBc/Hz at 1 MHz, **flicker corner about 615 kHz**, 8.5 dB above the
1/Δf² line at 100 kHz. With an unfiltered tail mirror the corner sits on the 600 kHz duplex
offset, adding about 3 dB there. Design note for P2.3: filter the tail bias (and the
varactor bias) or the duplex-offset budget loses those 3 dB. Level 4b confirms the
transfer behind it (worst 0.48 dB).

What this does not cover: the device flicker parameters themselves (that is the PDK
model), and the transient flicker generator is an approximation (Voss-McCartney sum).
Level 3 does not depend on either.

## Run (inside the container)

```bash
cd /foss/designs/analog/pn-validation
./run.sh               # level 1 pnoise, seconds
./run.sh l2            # + level 2 pnoise, about 1-2 min
./run.sh tran          # + transient-noise references, 5-20 min
./run.sh flicker       # level 3 (+ 4x pss_minpts check) and level 4 pnoise, minutes
./run.sh flicker-tran  # + level 4 transient noise, 80 us, about 1-3 h
```
Results: `out/compare.txt`, `out/compare_flicker.txt`; logs: `out/*.log`.

**Level 4 transient cost (2026-10-20).** The first 80 µs run in `zoh` mode averaged a 17 fs
time step (1.38·10⁹ points in 23.9 µs, 8.7 h), projecting 29 h and 111 GB; it was stopped.
`./tran_diag.sh` times 0.5 µs trials (`zoh`, `sde`, `zoh` at 20 GHz noise bandwidth) and
projects the full run; `./tran_diag.sh l1sde` checks `sde` against the Level 1 closed form
before it is used. `rawprogress.py out/<name>.raw` shows the progress of a running transient.

Cause (`./tran_diag.sh cause`, 0.5 µs trials): with noise off, Level 4 averages a 1.16 ps
step (80 µs ≈ 0.6 h); with `zoh` noise on, Level 4 and also the validated Level 2 average
14 fs, independent of the noise bandwidth (20 / 50 GHz) and of `noisefmin` (10 / 50 kHz);
`sde` aborts (timestep too small). So transient noise on transistor circuits costs about
80× in steps, and an 80 µs reference is 22–37 h and about 140 GB. (The Level 2 10.5 µs
reference above would take about 3 h at that rate, not the 5–20 min stated.)

**Level 4b replaces the Level 4 transient-noise reference** (`level4_inject.py`,
`./run.sh inject`). On the same Level 4 circuit:
1. `pnoise` (16 000 points) without and with an extra noise current into the tail bias node
   gives the transfer from a current at that node to the output sideband. The injected
   current must be **band-limited** (1/f², 9/f² A²/Hz): a white source also has power near
   2 f0 ± Δf, which the tail mixes into the same sideband, and a low-frequency tone has none.
   The first run used a white source and read 2.6–2.9 dB high at all three tones, the
   classic tail-noise path at 2 f0; both predictions are printed.
2. A noiseless transient with three small sine currents into the same node (300 kHz, 1 MHz,
   3 MHz), each sized for a −50 dBc upper sideband (first run, white prediction); the
   transient is reused when `out/inject/tone.raw` exists.
3. The transient's upper sidebands are measured (flat-top window, 40 µs, 25 kHz bins).
Pass: within 1 dB of the prediction at each tone. This checks the periodic transfer from a
low-frequency current to the carrier sidebands, which is what the flicker region depends
on, with the real transistors and without random noise. The device flicker magnitude is PDK
model data and is not checked by either method.

First run 2026-10-20: **PASS**, −0.48 / −0.19 / −0.11 dB at 300 kHz / 1 MHz / 3 MHz.
Start with `./run.sh flicker`: if level 3 fails, the transient run is not worth starting.
