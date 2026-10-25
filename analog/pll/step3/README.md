# P2.5 step 3 — charge-pump Monte Carlo, fractional spurs, PLL current

Details in the header of `run_step3.py` and `pll_behav.py`.

```bash
cd /foss/designs/analog/pll/step3
mkdir -p out
python3 -u run_step3.py mc n=3 tt | tee out/summary_mc3.txt     # quick trial (tt, 3 V_tune, 3 samples)
python3 -u run_step3.py mc | tee out/summary_mc.txt             # full: 4 cases x (1 + 10) curves x 5 points, about 4 h
python3 -u run_step3.py spur | tee out/summary_spur.txt         # minutes, from out/mc_*.json
python3 -u run_step3.py current | tee out/summary_cur.txt
```

| Part | What | Pass |
|---|---|---|
| `mc` | PDK mismatch on every transistor of PFD, pump and amplifiers; Q(dt) at 1–5 ns of UP lead with the offset pair; tt at 0.25 / 0.6 / 0.95 V, ss at 0.6 V | INL a few ps at most; lock point well above the Σ-Δ wander (≈ 1.2–4.4 ns around it) |
| `spur` | Cycle-by-cycle PLL model with the real MASH 1-1-1 sequence (bit-exact to `rtl/afe/sdm.sv`), the P2.2 loop and each measured Q(dt) curve; spur at the boundary offset (600 kHz VHF, 2 MHz UHF) | ≤ −95 dBc at RF |
| `current` | PFD + pump + amplifiers from the runs, other PLL blocks estimated | ≤ 1.8 mA |

Self-check of the PLL model (`python3 pll_behav.py`, run when writing it): with a linear pump nothing rises above the Σ-Δ noise in one bin (VHF −127 / floor −134 dBc, UHF −122 / −132 dBc at RF); a synthetic 1 ps INL gives VHF −126 dBc, 10 ps gives −117 dBc — so the −95 dBc limit leaves room for tens of ps. The divider-edge timing in the model stays within 1.2–4.4 ns (VHF) and 1.7–3.8 ns (UHF) of UP lead, inside the measured 1–5 ns, so the pump stays on one side as D18 intends.
