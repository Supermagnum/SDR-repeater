# P2.3 step 2 — first VCO schematic

**8-bit bank (D20, 2026-10-25):** the scripts now build an 8-bit bank by default (same range, LSB about half;
`bits=7` reproduces the P2.3 runs below). Rerun for D20:

```bash
cd /foss/designs/analog/vco/step2
python3 -u run_step2.py range | tee out/summary_8bit.txt     # sizing, range, KVCO, tail currents (~15 min)
python3 -u run_step2.py steps | tee out/summary_steps.txt    # band steps at the carry transitions (~15 min)
cd ../step3 && python3 -u run_step3.py range bands | tee out/summary_8bit.txt   # corners + phase noise (~2 h)
```

Generated VACASK netlist of the whole VCO as decided in `spec/vco-topology.md` (D8–D11, step 1 sizes), typical corner, 27 °C. Status: **done 2026-10-20.** Result with 2 MΩ bias resistors and the buffer node decoupled (code 48, 3.65 GHz, 4.12 mA, 1.18 V differential, reltol 1e-6): **−116.8 dBc/Hz at 600 kHz (+8.4 dB), −122.6 at 1 MHz (+6.6 dB), −129.6 at 2 MHz (+11.7 dB)**. Contributions at 1 MHz: core pair 50 %, inductor 20 %, varactor bias 9 %, bank bias about 10 %, tail 3 %. Corners, temperature and the other bands: step 3.

Earlier: first phase-noise result 2026-10-20 (code 48, 3.65 GHz, 4.12 mA, 1.19 V differential; pss converged at reltol 1e-6, not at 1e-7): **−119.2 dBc/Hz at 1 MHz** (target −116), −113.6 at 600 kHz (limit −108.4 at the VCO), −126.5 at 2 MHz (limit −117.9). Slope about −25 dB/decade from 300 kHz to 2 MHz: a noise source other than the tank adds about 2.4 dB at 1 MHz. `contrib` at 1 MHz: buffer pair 26 %, core pair 22 %, varactor bias resistors 21 %, off MSB bank bias resistors 15 %, inductor 9 %. Next run: bank and varactor bias resistors 2 MΩ (their noise above the R·C corner falls as 1/R), 2 pF on the buffer's common node. Earlier: third run prepared 2026-10-20 (second run: range 2.95–4.41 GHz covers the band; KVCO 13.6–38.6 MHz/V; 1.3 V needs 3.4 mA at the top and 5 mA (capped) at the bottom; pss failed again at both tolerances, so pss now starts from a stored transient).

First run (2026-10-20): the VCO oscillated at all codes but at **3.75–5.96 GHz**. Two sizing errors on my side: the bank was sized for 955 fF of *on*-state capacitance, but it switches only C_on − C_off (about 644 fF); and the fixed capacitance was about 420 fF, well under the 762 fF budget. Swing 1.07–1.59 V differential at 3.5 mA, over the 1.5 V oxide limit at the top code. KVCO 22–76 MHz/V. The pss stabilisation transient failed at reltol 1e-7.

Second run changes: `size()` scales the bank and adds a fixed differential MIM so code 0 / 127 land at 762 / 1717 fF (4.37 / 3.00 GHz with the ± 3 % L margin), in two passes of short transients; varactor 20 fingers (the first run gave 8.7 fF over the 0.7 V window, about 10 fF needed); tail current per band for 1.3 V differential; pss falls back to reltol 1e-6 if 1e-7 fails.

```bash
cd /foss/designs/analog/vco/step2
mkdir -p out && python3 -u run_step2.py | tee out/summary.txt   # range, then pss/pnoise (20-60 min)
python3 run_step2.py range                      # only the transients
python3 run_step2.py pn                         # only pss/pnoise, band code from out/range.json
```

What it reports:
1. **Tuning range and swing:** noiseless 60 ns transients at bank codes 0/32/64/96/127 and tuning voltages 0.3/0.65/1.0 V: frequency, differential amplitude, peak V_GS and V_GD of the core against 1.5 V, minimum tail and drain voltages; whether 3.12–4.20 GHz is covered; KVCO at codes 0/64/127.
2. **Band pick:** the code that puts the VCO at 3.65 GHz at 0.65 V.
3. **Phase noise there:** pss/pnoise (16 000 points), 30 kHz–10 MHz, against −116 dBc/Hz at 1 MHz and the duplex-offset limits at the VCO (−108.4 at 600 kHz, −117.9 at 2 MHz); slope per decade shows the flicker region.

The circuit is in the docstring of `run_step2.py`. Ideal parts still in it: supplies (the LDO), the reference current, the bias-filter R and C, the tail capacitor and the buffer loads. Needs `analog/vco/models/l2n0_lumped.inc` (step 1) and the PDK's VACASK models.

First-run expectations, so a surprise is visible: about 3.5 mA gives roughly 1.1–1.5 V differential; hand estimate −124 to −126 dBc/Hz at 1 MHz. If the range is not covered, the fixed capacitance is larger than budgeted (§2 of the memo); if a peak voltage is above 1.5 V, the tail current is reduced per band.
