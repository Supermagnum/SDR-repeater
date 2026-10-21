# P2.4 step 3 — LO chains across corners, Monte Carlo

The final step-2 chain (`analog/lo/step2/`) driven by an ideal tank source with the lowest VCO swing at each frequency (0.27 V per side at 3.12 GHz to 0.52 V at 4.20 GHz), so every corner sees a pessimistic clock and a run takes minutes. Details in the header of `run_step3.py`.

```bash
cd /foss/designs/analog/lo/step3
mkdir -p out
python3 -u run_step3.py corners | tee out/summary_corners.txt    # 7 corners x 4 cases (28 runs)
python3 -u run_step3.py mc | tee out/summary_mc.txt              # tt and ss, both bands, 25 samples each (100 runs)
python3 -u run_step3.py mc n=5 uhf tt                            # quick trial first
```

| Part | What | Pass |
|---|---|---|
| `corners` | tt 1.2 V 27 °C; ss 1.08 V 125 / −40 °C; ff 1.32 V −40 / 125 °C; sf, fs 1.2 V 27 °C — UHF 3.20 / 3.84 GHz, VHF 3.12 / 4.20 GHz | Divides everywhere; systematic phase errors and duty; chain current per corner (D7 budget) |
| `mc` | PDK mismatch (V_T, beta, W, L) on every LO transistor; tt and ss; top frequency of each band | Phase-error sigma per output; UHF image rejection from the quadrature error; all samples divide |

First run (2026-10-21):
- **Corners:** all cases correct at tt, ff, sf, fs and at the top of each band at ss / ss-cold. Systematic errors ≤ 0.53° (UHF), ≤ 0.12° (VHF); duty 23.3–25.6 % (UHF), 47.8–50.9 % (VHF). **Fails at the bottom of the bands at the slow corner** with the pessimistic tank swing (UHF 3.20 GHz ss −40 °C; VHF 3.12 GHz ss 125 and −40 °C) — the buffer output looks right (0.56–0.57 V per side), the stage is not known yet. **VHF ff 125 °C: no DC operating point.** Chain current up to 3.47 mA (UHF) and 5.25 mA (VHF, ff −40 °C).
- **Monte Carlo:** typical fine — all samples divide; phase sigma 0.50° UHF (quadrature error → 37.4 dB raw image rejection at 3 sigma), 0.16° VHF. **Slow corner: 9 of 25 UHF and 3 of 25 VHF samples do not divide**; the rest give sigma 1.07° (UHF, 30.6 dB) and 0.28° (VHF).

Second run: supplies ramp from 0 (operating point), the first wrong stage and the clock duty / skew are printed for every failing case and sample, and `swing` finds the minimum tank swing at the bottom of each band at the slow corner:

```bash
python3 -u run_step3.py swing | tee out/summary_swing.txt          # 2 bands x 2 corners x 5 swings (20 runs)
python3 -u run_step3.py corners ff-hot vhf | tee out/summary_ffhot.txt
python3 -u run_step3.py mc ss n=12 | tee out/summary_mc_ss12.txt   # failing samples with their stage
```

The divider noise floor (target ≤ −150 dBc/Hz at the LO output) is the next part of step 3, after these two.
