# P2.0 — pnoise in the flicker region

Provenance: [SCH] simulation. Run 2026-10-20 in `hpretl/iic-osic-tools:2026.10`, VACASK fb8cc20, IHP SG13G2 PDK `a49358cc`. Scripts and method: `analog/pn-validation/` (README, levels 3, 4 and 4b). Thermal region: validated 2026-10-19 (levels 1–2).

**Result: VACASK `pnoise` handles the flicker region correctly.** It can be used for the P2.3 VCO from 30 kHz offset upwards at `pss_minpts` 16 000 (lower offsets need more points, rule below).

## Level 3 — exact answer (ideal oscillator, 1/f noise through a varactor)

Low-frequency noise reaches the carrier phase by frequency modulation. Here a pure 1/f voltage drives a linear varactor in the ideal Level 1 tank, so L(Δf) = thermal term + K²·S_v(Δf)/(2Δf²) exactly (K = 84.6 MHz/V, flicker corner about 1 MHz).

| Offset | Closed form (dBc/Hz) | pnoise, 16 000 points | pnoise, 64 000 points |
|---|---|---|---|
| 10 kHz | −64.4 | −1.9 dB | −0.2 dB |
| 30 kHz | −78.6 | −0.3 dB | −0.1 dB |
| 100 kHz – 10 MHz | −94.1 … −144.2 | 0.0 dB | 0.0 dB |
| 20 MHz | −150.4 | +0.2 dB | +0.2 dB |

- **Pass** (limit 1 dB): worst 0.2 dB from 10 kHz to 20 MHz at 64 000 points.
- **Setting rule:** the error depends on `pss_minpts` × Δf; ≤ 0.3 dB needs `pss_minpts` × lowest offset ≥ about 5·10⁸ (16 000 points from 30 kHz; Level 1 showed the same at 100 kHz with 1 000–4 000 points). The 64 000-point runs take much longer on transistor circuits, so P2.3 uses 16 000 points and offsets ≥ 30 kHz.

## Level 4 — SG13G2 oscillator with a real MOS tail

Level 2 with the ideal tail replaced by an `sg13_lv_nmos` 1:4 mirror (L = 0.5 µm, no bias filtering). `pnoise`: f0 3.690 GHz, differential amplitude 0.96 V, 1/Δf² level −122.9 dBc/Hz at 1 MHz, **flicker corner about 615 kHz** (8.5 dB above the 1/Δf² line at 100 kHz).

**Transient-noise reference: not practical.** With `zoh` noise on, every transistor transient (this circuit and the validated Level 2 alike) averages a 14 fs time step, against 1.16 ps with noise off; the noise bandwidth (20 / 50 GHz) and `noisefmin` (10 / 50 kHz) make no difference, and `sde` mode aborts. An 80 µs reference would take 22–37 h and about 140 GB; the first attempt was stopped at 24 µs (8.7 h, 33 GB).

## Level 4b — deterministic injection (replaces the transient-noise reference)

Same Level 4 circuit. `pnoise` with and without a band-limited (1/f²) noise current into the tail bias node gives the transfer from a current at that node to the output sideband. A noiseless transient (normal time step, about 20 min) injects three small sine currents into the same node; the measured upper sidebands are compared with the prediction.

| Tone | Current | Predicted USB | Measured USB | Difference | Measured LSB |
|---|---|---|---|---|---|
| 300 kHz | 36.9 nA | −52.29 dBc | −52.77 dBc | −0.48 dB | −52.52 dBc |
| 1 MHz | 125.0 nA | −52.41 dBc | −52.60 dBc | −0.19 dB | −51.81 dBc |
| 3 MHz | 395.3 nA | −52.79 dBc | −52.89 dBc | −0.11 dB | −50.58 dBc |

- **Pass** (limit 1 dB): worst 0.48 dB. This checks, with the real transistors, the periodic transfer from a low-frequency current to the carrier sidebands, which is what the flicker region depends on. The flicker magnitude of the devices is PDK model data and is not checked by any of these methods.
- The first prediction used a white injected current and read 2.3–2.8 dB high at every tone. A white source also has power near 2 f0 ± Δf, which the tail mixes into the same sideband; a low-frequency tone has none. The difference shows that in this circuit tail-node noise near 2 f0 (and other harmonics) adds 70–90 % on top of the sideband power from the same noise density at low frequency, i.e. 41–47 % of the total for white noise.
- Upper and lower sidebands differ by up to 2.3 dB (at 3 MHz): the tail modulation produces amplitude as well as phase modulation. `pnoise` reports the upper sideband, which is what is compared here.

## Consequences for P2.3 (VCO)

- Use `pnoise` at `pss_minpts` 16 000 with offsets ≥ 30 kHz (all the requirements: 600 kHz and 2 MHz duplex offsets, 1 MHz VCO target).
- **Tail and bias filtering are design items, not options.** With an unfiltered tail mirror the flicker corner (615 kHz) sits on the 600 kHz duplex offset and costs about 3 dB there; tail noise near 2 f0 is a second, comparable path. Expect a low-pass on the tail and varactor bias and a tail filter at 2 f0 (or a tail-less / HBT topology) in the topology memo.
- Transient noise is not a usable reference for transistor circuits at these run lengths; deterministic injection (Level 4b) is the method for checking `pnoise` on new circuits.
