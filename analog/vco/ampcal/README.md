# D22 amp cal — step 1c (V_DS-matched DAC, tail-only bypass, SE cmp)

See `spec/vco-amplitude-cal.md` §8 (1b) and §9 (1c).

Each script writes under its own `out/<name>/` subdirectory (avoids rawfile races).

```bash
cd /foss/designs/analog/vco/ampcal
python3 -u run_dac.py        | tee out/dac/summary_dac.txt
python3 -u run_headroom.py   | tee out/headroom/summary_headroom.txt
python3 -u run_bottom.py     | tee out/bottom/summary_bottom.txt
python3 -u run_cmp_mc.py     | tee out/cmp/summary_cmp_mc.txt
python3 -u run_search.py     | tee out/sar/summary_search.txt     # or: quick
python3 -u run_pn_det.py     | tee out/pn/summary_pn_det.txt
```

Shared constants / netlist fragments: `amp_common.py`.

RTL: `rtl/afe/afe_seq.sv` (`en_vco_bias_bp` wake all; `en_vco_tail_bp` wake|cal), `bandcal.sv`.
Wake: `analog/pll/p26/wake_timing.py` — amp settle still 1.00 µs/bit (RTL margin over SCH 0.20 µs); wake 109–130 µs ≤ 150 µs.
