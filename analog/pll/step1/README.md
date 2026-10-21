# P2.5 step 1 — PLL device and block checks

The checks of `spec/pll-topology.md` §5 in one script (charge-pump current sources, loop-filter MOS capacitors, the feedback divider's first 2/3 cell). The PFD dead-zone check needs the PFD and the pump switches together and is done with the step-2 schematic. Details in the header of `run_step1.py`.

```bash
cd /foss/designs/analog/pll/step1
mkdir -p out && python3 -u run_step1.py | tee out/summary.txt     # all checks
python3 -u run_step1.py cp                                         # or some of: cp cap mmd
```

| Check | What | Pass |
|---|---|---|
| `cp` | Wide-swing cascode current sources, 25 / 100 / 200 µA, output 0.15–1.05 V, tt / ss / ff; leakage at 125 °C | Current within 1 % over the tuning window 0.35–0.85 V; raw up/down mismatch (sets the replica-amplifier gain); leakage ≪ 100 nA |
| `cap` | Thin NMOS, thin PMOS, both in parallel, thick NMOS as capacitors: fF/µm² against 0.1–1.1 V; gate leakage at 125 °C | Density and its spread over 0.35–0.85 V (loop gain), leakage for 355 pF ≪ 100 nA |
| `mmd` | Divide-by-2/3 cell (two TSPC flip-flops + AOI21), ÷2 and ÷3, 1.0–3.3 GHz, tt / ss; 10 mismatch samples at ss / 2.2 GHz | ≥ 2.9 GHz (1.3 × 2.2 GHz) at the slow corner; all samples correct |
