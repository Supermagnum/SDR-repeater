# P2.5 step 4 — bias generator, window delay cell, V_tune hold switch

Details in the header of `run_step4.py`; design in `spec/pll-topology.md` §12.

```bash
cd /foss/designs/analog/pll/step4
mkdir -p out
python3 -u run_step4.py | tee out/summary.txt            # bias, start, win, hold
python3 -u run_step4.py lin | tee out/summary_lin.txt    # pump linearity with the real bias (about 25 min)
```

| Part | What | Pass |
|---|---|---|
| `bias` | DC: master current, I_cp DAC (8 codes), tails; corners, supply ±10 %, R_B ±20 % | Mirror ratios within a few %; I_cp ∝ V_REF / R_B |
| `start` | Supply ramp 0.1 µs and 20 µs | Master current settles; start-up device off |
| `win` | Delay cells on the reference and the divider output over corners, MIM corners, R_B ±20 %, supply | 5–12 ns (target 7) |
| `hold` | Loop filter precharged to 0–1.2 V, then hold; switch leakage at fast-hot | Mean V_tune error over the first count ≤ 10 mV |
| `lin` | Step-3 linearity check with all pump current sources from the bias generator | INL and lock point as in step 3 |

The RTL side (two-sided lock detector, first-trial settling of the calibration) is tested with `rtl/afe/cocotb/run_afe.py`.
