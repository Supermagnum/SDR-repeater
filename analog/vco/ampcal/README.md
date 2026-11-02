# D22 step 1 — VCO amplitude detector, DAC, search

See `spec/vco-amplitude-cal.md` §6–7.

```bash
cd /foss/designs/analog/vco/ampcal
python3 -u run_dac.py        | tee out/summary_dac.txt
python3 -u run_detector.py   | tee out/summary_detector.txt
python3 -u run_search.py     | tee out/summary_search.txt   # or: quick
python3 -u run_pn_det.py     | tee out/summary_pn_det.txt
```

RTL: `rtl/afe/bandcal.sv`, `afe_seq.sv`; cocotb in `rtl/afe/cocotb/` (`ONLY=bandcal` / `afe_seq`).
