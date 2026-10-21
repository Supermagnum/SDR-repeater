# P2.5 step 2 — PLL schematics

Step 2 has three parts (`spec/pll-topology.md` §7): (a) PFD and charge pump, (b) the multi-modulus divider, (c) Σ-Δ, lock detector and calibration as RTL.

## Part a: PFD and charge pump (`run_step2.py`)

Transistor-level PFD (static master-slave flip-flops with asynchronous reset, reset delay NAND + 5 inverters) and charge pump (long-channel sources, current steering into a dummy node held at V_tune, replica branch with a Miller-compensated amplifier that matches up and down at V_tune). The amplifier and the dummy-node follower are behavioural for now. The output is held at V_tune by an ideal source; its averaged current gives the net charge per reference cycle against the REF–DIV phase offset.

```bash
cd /foss/designs/analog/pll/step2
mkdir -p out && python3 -u run_step2.py | tee out/summary_a.txt     # 3 corners x 3 V_tune x 9 offsets (81 runs)
python3 -u run_step2.py tt                                          # one corner first, as a trial
python3 -u run_step2.py icp=200                                     # other pump current (µA, default 100)
```

| Result | Pass |
|---|---|
| Q / I_cp against dt | linear, slope (pump gain) 1 ± 5 % over 0.25–0.95 V |
| Offset at dt = 0 | small (residual mismatch × reset pulse); ≪ the D18 offset current's effect |
| Dead zone | ±3 ps still gives the right sign |
| Reset pulse | 100–300 ps at every corner (both switches fully on) |
| Replica error | vr within a few mV of V_tune |

First run (typical, 2026-10-21): no dead zone (±3 ps resolved), but **offset +131 / +143 ps at dt = 0** (V_tune 0.6 / 0.95 V), gain 1.14–1.16, reset pulse 606–643 ps (too long), replica 16–20 mV off; at 0.25 V the replica loop ran to the rail (+937 mV) and the result is void. Causes and second-run fixes:
- the output switch and the dummy switch of each pair were driven one inverter delay apart, so the source floated on every UP edge and dumped its charge into the output → each pair now driven by an inverter and a matched always-on transmission gate (complementary, equal delay);
- the behavioural transconductor could drive the PMOS gate outside the supply → clamped 60 dB voltage amplifier;
- reset delay chain shortened (NAND + 3 inverters, no load capacitors).
