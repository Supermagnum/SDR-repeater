# D22 amp cal — step 1 done (SE-cmp end-to-end)

See `spec/vco-amplitude-cal.md` §8–§10. Interim A2 retired 2026-11-11.

Each script writes under its own `out/<name>/` subdirectory (avoids rawfile races).
Copy `out/<name>/summary_*.txt` to `out/summary_*.txt` for git (gitignore allows that pattern).

```bash
cd /foss/designs/analog/vco/ampcal
python3 -u run_search.py     | tee out/sar/summary_search.txt     # or: quick
python3 -u run_dac.py        | tee out/dac/summary_dac.txt
python3 -u run_cmp_mc.py     | tee out/cmp/summary_cmp_mc.txt
python3 -u run_bottom.py     | tee out/bottom/summary_bottom.txt
python3 -u run_pn_det.py     | tee out/pn/summary_pn_det.txt
```

Decision path (step 1d): `v(cmp) > CMP_HIGH` (0.85 V). Steady ≤ 1.40 V; search transient ≤ 1.50 V.
RTL: `afe_seq` `en_vco_bias_bp` / `en_vco_tail_bp`; `bandcal.sv`. Wake 109–130 µs ≤ 150 µs.
