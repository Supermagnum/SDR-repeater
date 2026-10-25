# P2.6 step 3 — transistor-level closed loop (interface check)

Details in the header of `run_p26s3.py`. The whole loop at transistor level — VCO (8-bit trimmed bank), LO buffer,
CML ÷3 with the D15 enable, converter, a TSPC ripple ÷32 in place of the MMD, PFD, charge pump, bias generator — with
the D19 loop filter scaled to 10 × the bandwidth so the loop settles within a few µs. Integer-N, VCO 3.456 GHz.

```bash
cd /foss/designs/analog/pll/p26/step3
mkdir -p out
python3 -u run_p26s3.py tstop=2u | tee out/summary_2u.txt   # start-up trial
python3 -u run_p26s3.py | tee out/summary.txt               # 8 us
```

Pass: the divider period equals the reference period (locked), V_tune settles inside 0.25–0.95 V, UP ≈ 3 ns and DN ≈ 0.25 ns per
cycle (D18), no oscillation of the loop or of the bias generator.
