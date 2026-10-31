# V_tune window monitor (P2.6 open point 1 / D20) — closed

Two continuous-time comparators flag when `V_tune` leaves ≈ 0.28–0.775 V (option B). Outputs feed `PLL_STATUS`[4:5] after `rtl/afe/vtune_sync.sv`.

```bash
cd /foss/designs/analog/pll/vtune_mon
mkdir -p out
python3 -u run_vtune_mon.py | tee out/summary.txt
python3 -u run_margins.py n=30 | tee out/summary_margins.txt
```

- Lo: PMOS pair at 0.28 V. Hi: NMOS pair after ÷2; **V_hi = 0.775 V** so ss hi_rise+3σ ≤ 0.82 V; ff may trip below ff cal top (accepted).
- Normal hysteresis (~45 mV). Host rules: `spec/analog-digital-interface.md` §6.
- Results: `out/summary.txt`, `out/summary_margins.txt` `[SCH]`. Finding that chose B: `out/finding_vhi.txt`.
