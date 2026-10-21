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

First run (2026-10-21): MOS capacitors — the complementary thin-oxide pair is the choice (≈ 7–12.5 fF/µm², spread ≤ 1.43× over 0.35–0.85 V; leakage 0.5–2 µA for 355 pF at 125 °C, reference spur still ≤ −116 dBc); 2/3 cell passes (÷3 to 2.9 GHz at ss, 10/10 mismatch samples); **cascoded charge pump fails the needed 0.25–0.95 V window** (up side ends at 0.65–0.80 V). Results in `spec/pll-topology.md` §7.

Second run: plain long-channel current sources (`cp2`):

```bash
python3 -u run_step1.py cp2 | tee out/summary_cp2.txt
```

Second run result: plain long-channel sources reach 0.25–0.95 V at typical and fast; at the slow corner (1.08 V) the up side ends at 0.80–0.85 V → step 2 widens the PMOS source and switch and uses the regulated supply. Raw mismatch up to ±30 % (for the replica amplifier). **Step 1 done**; summary in `spec/pll-topology.md` §7.
