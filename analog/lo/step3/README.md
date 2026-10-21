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

Second run result (2026-10-21):
- **VHF ÷3 has a second stable mode:** it divides by 2 instead of 3 (2.10 GHz out at 4.20 GHz, 0.05–0.17 V) at ff / 125 °C without mismatch, and in 8 of 12 slow-corner Monte Carlo samples — although it is enabled after the clock is up (D15). With the supply ramp the start-up differs from the first run (22 of 25 then), so the ÷3's mode depends on its start-up state: not robust.
- **UHF:** 5 of 12 slow-corner samples fail in the TSPC Johnson counter at 1.92 GHz (buffer, CML ÷2 and converter correct).
- **Bottom of the band (`swing`):** minimum tank swing per side 0.29 V (VHF, ss 125 °C; UHF passes at 0.25 V) and 0.33 V at ss −40 °C (both bands); below that the buffer's duty cycle drifts to 58–69 %. The VCO gives about 0.32 V at 85 °C and 0.43 V at −40 °C: the cold case has margin, **125 °C is marginal**.
- VHF ff 125 °C now has an operating point (supply ramp); 3.12 GHz correct.

Third run: design options (`i=`, `sw=`, `k=`, `sz=`, `bufac`, `nokick`, see the script header) to find the fixes:

```bash
cd /foss/designs/analog/lo/step3
for o in "k=1.5" "i=0.65" "sw=0.5" "nokick"; do
  python3 -u run_step3.py corners ff-hot vhf $o | tee "out/summary_ffhot_${o}.txt"
done
for o in "k=1.5" "i=0.65" "sw=0.5"; do
  python3 -u run_step3.py mc ss vhf n=8 $o | tee "out/summary_mc_vhf_${o}.txt"
done
python3 -u run_step3.py mc ss uhf n=8 sz=3 | tee out/summary_mc_uhf_sz3.txt
python3 -u run_step3.py swing bufac | tee out/summary_swing_bufac.txt
```

The divider noise floor (target ≤ −150 dBc/Hz at the LO output) is the next part of step 3, after these two.
