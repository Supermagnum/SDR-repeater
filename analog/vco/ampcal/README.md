# D22 step 1b — differential-max detector, unit-cell DAC, corner search

See `spec/vco-amplitude-cal.md` §8.

Each script writes under its own `out/<name>/` subdirectory (avoids rawfile races).

```bash
cd /foss/designs/analog/vco/ampcal
python3 -u run_diagnose.py   | tee out/summary_diagnose.txt
python3 -u run_dac.py        | tee out/summary_dac.txt
python3 -u run_detector.py   | tee out/summary_detector.txt   # or: quick
python3 -u run_cmp_mc.py     | tee out/summary_cmp_mc.txt
python3 -u run_search.py     | tee out/summary_search.txt     # or: quick
```

Shared constants / netlist fragments: `amp_common.py`.

RTL (step 1, unchanged this run): `rtl/afe/bandcal.sv`, `afe_seq.sv`.
Wake (unchanged): `analog/pll/p26/wake_timing.py` — amp settle still 1.00 µs/bit (RTL margin over SCH 0.20 µs).
