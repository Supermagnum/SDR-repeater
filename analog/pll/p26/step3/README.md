# P2.6 step 3 — transistor-level closed loop (interface check)

Details in the header of `run_p26s3.py`. The whole loop at transistor level — VCO (8-bit trimmed bank), LO buffer,
CML ÷3 with the D15 enable, converter, a TSPC ripple ÷32 in place of the MMD, PFD, charge pump, bias generator — with
the D19 loop filter scaled to 10 × the bandwidth so the loop settles within a few µs. Integer-N, VCO 3.456 GHz.

```bash
cd /foss/designs/analog/pll/p26/step3
mkdir -p out
python3 -u run_p26s3.py tstop=2u | tee out/summary_2u.txt     # start-up / bypass trial
python3 -u run_p26s3.py s=5 tstop=20u | tee out/summary_s5.txt  # full lock (hours)
```

Bias bypass follows `afe_seq` / `wake_timing.py` (closed 1.00 µs @ 36 MHz, then MOS switches open); `en_lodiv` at 1.33 µs. Not the old behavioural `tsw` at 200 ns. Canonical lock result: `out/summary_s5.txt` (2026-10-31, sequencer-driven MOS bypass).

Pass: the divider period equals the reference period (locked), V_tune settles inside 0.25–0.95 V, UP ≈ 3 ns and DN ≈ 0.25 ns per
cycle (D18), no oscillation of the loop or of the bias generator.
