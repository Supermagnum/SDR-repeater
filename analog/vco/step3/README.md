# P2.3 step 3 — VCO across bands, corners and temperature

The step-2 VCO (`analog/vco/step2/`, sizes from its `out/range.json`) checked against the requirements in `spec/vco-topology.md` §1. Status: **done 2026-10-20** — all parts pass; results and open points in `spec/vco-topology.md` §9. One pss at the slow corner (4.20 GHz) needed the 8000-point fallback (offsets ≥ 62 kHz accurate).

```bash
cd /foss/designs/analog/vco/step3
mkdir -p out && python3 -u run_step3.py | tee out/summary.txt     # all four parts, about 2-3 h
python3 -u run_step3.py reltol                                     # or one part: reltol range bands worst
```

| Part | What | Pass |
|---|---|---|
| 1. reltol | The validated level 2 oscillator (`analog/pn-validation/`) at reltol 1e-7 and 1e-6: is the looser tolerance step 2 needed accurate enough? | Difference ≤ 0.5 dB |
| 2. range | Code 0 at 1.0 V and code 127 at 0.3 V, MOS corners tt/ss/ff × MIM corners typ/wcs/bcs (5 combinations), −40 / 27 / 85 °C; per-band tail current from step 2 | Top ≥ 4.20 GHz, bottom ≤ 3.12 GHz, oscillates, peak V_GS / V_GD ≤ 1.5 V |
| 3. bands | pss/pnoise at 3.12 / 3.40 / 3.65 / 3.90 / 4.20 GHz, typical, 27 °C | VHF ≤ −108.4 @ 600 kHz and ≤ −116 @ 1 MHz; UHF band (3.20–3.84 GHz) ≤ −115 @ 1 MHz and ≤ −117.9 @ 2 MHz |
| 4. worst | pss/pnoise at the slow MOS corner, 85 °C, 3.12 / 3.65 / 4.20 GHz | Same |

The per-band tail current is not recalibrated at the corners (the conservative case); the real design sets `VCO_BIAS` per band at calibration. Supplies, reference current and the buffer are still ideal.
