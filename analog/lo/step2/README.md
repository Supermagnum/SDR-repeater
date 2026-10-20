# P2.4 step 2 — VCO buffer and divider chains with the VCO

Both divider chains of `spec/lo-divider-topology.md` driven by the simulated P2.3 VCO, with a real VCO buffer.

First run (2026-10-20):
- **Buffer: meets the requirement.** 0.64–0.65 V per side typical, 0.55–0.58 V slow (need ≥ 0.50 / 0.45), common mode 0.61 / 0.54 V; 0.4–0.6 mA.
- **UHF: divides exactly** (VCO / 8 at 3.20 and 3.84 GHz, both corners); currents CML 1.0, converter 0.34, logic 0.1–0.14 mA. **But the 25 % pulses taken straight from NAND + inverter had growing phase errors**: +3.7 / +7.4 / +9.9° typical, up to +31 / +52° with duty 18–35 % at the slow corner, 480 MHz — gate-path delays, not mismatch.
- **VHF: no result** — VACASK stopped at the DC operating point (TSPC nodes float in some clock states).

Second run (2026-10-20), retimed outputs:
- **Typical: phase and duty now right** — UHF errors ≤ 0.8°, duty 24.6–25.7 %; VHF errors ≤ 0.18°, duty 49.4–50.5 %; currents UHF ≈ 2.1 mA, VHF ≈ 3.7 mA (buffer, divider, converter, logic).
- **Slow corner: UHF divided by 10 / 16 instead of 8, VHF at 4.20 GHz gave no output** (VHF at 3.12 GHz fine). Cause: the converter's last 1/2 µm inverter now drives 6 / 12 flip-flop clocks and is too slow at 1.08 V, 125 °C. Buffer swing at slow 3.12 GHz only 0.47 V per side (need 0.45).

Third run: tapered clock driver after the converter (3/6 → 9/18 µm), second buffer inverter 6/12 µm. Run the slow corner first: `python3 -u run_step2.py ss`.

Third run result (slow corner): UHF 3.20 GHz now correct (phase errors ≤ 0.23°, duty 21 % against 25 %); VHF 3.12 GHz correct (≤ 0.06°, duty 49–50 %, buffer only 0.44 V per side); **UHF 3.84 GHz only partly divides and VHF 4.20 GHz gives no output**. Fourth run adds a stage-by-stage frequency and swing check (buffer, CML divider, converter, clock, counter) to find where the chain stops: `python3 -u run_step2.py ss 3.84 4.20`.

Fourth run result (stage check, slow corner): **UHF 3.84 GHz** — buffer, CML ÷2, converter and clock all correct (1.923 GHz, full swing), but the **Johnson counter miscounts** (0.861 GHz instead of 0.481): the minimum-size TSPC flip-flops are too weak once loaded at 1.92 GHz. **VHF 4.20 GHz** — buffer correct (4.21 GHz, 1.0 V differential), but the **CML ÷3 output is wrong** (2.71 GHz, 0.15 V instead of 1.40 GHz): with the same swing that worked in step 1 from ideal complementary sources, the likely difference is skew between the separately buffered ckp and ckn.

Fifth run: TSPC flip-flops size 2 (default); the buffer's outputs coupled in anti-phase (1/2 µm cross-coupled inverters); the clock skew is printed; option `cmlbuf` adds a differential current-steering stage (1 mA) after the inverters for exactly complementary clocks. Run: `python3 -u run_step2.py ss 3.84 4.20`, and if the ÷3 still fails, `python3 -u run_step2.py ss 4.20 cmlbuf`.

Fifth run result: **UHF 3.84 GHz slow corner now correct** (counter right with size-2 flip-flops; phase errors ≤ 0.46°; duty 21 % against 25 %). **VHF 4.20 GHz still fails** in the CML ÷3 (2.37 GHz out, 0.16 V); ckp/ckn skew only −4 … −6 ps, so skew is not the cause; the `cmlbuf` stage did not help either (and cost 1 mA). Sixth run: the stand-alone ÷3 in step 1 (`div3x`) with square instead of sine clock, duty 50 / 45 / 40 %, converter load and 0.65 mA per latch, to isolate the cause; step 2 now also prints the clock duty cycle.

Sixth run result (`div3x`, step 1): the stand-alone ÷3 divides correctly at slow corner at 3.12, 4.21 and 4.41 GHz with a 0.47 V clock **for every variant** (sine, square at 50 / 45 / 40 % duty, converter load, 0.65 mA per latch; 0.31–0.33 V out). Clock shape, duty cycle, load and current are not the cause. Remaining difference: in the chain the ÷3 is on while the VCO starts up, so it free-runs first (2.37 GHz, 0.16 V — its self-oscillation) and apparently stays there. Seventh run: `div3s` in step 1 (clock ramped up over 5 / 20 ns with the divider on, also to 0.6 / 0.75 V; and the divider enabled only after the clock is up), and option `en=<ns>` here to enable the CML divider late in the full chain: `python3 -u run_step2.py vhf ss 4.20 en=35`.

Seventh run result: **confirmed.** `div3s`: with the divider on during a clock ramp (5 or 20 ns, also a step after 5 ns off) the ÷3 fails at 4.41 GHz (2.2–3.1 GHz out, 0.14–0.17 V, its free-running state), and more final swing (0.6 / 0.75 V) does not pull it out; enabled after the ramp it divides at all three frequencies. Full chain, VHF slow 4.20 GHz with the divider enabled at 35 ns: **all 8 phases correct**, phase errors ≤ 0.12°, duty 48.7–49.6 %, currents buffer 0.77, CML 2.51, converter 0.63, logic 0.30 mA. Owner decision **D15**: the sequencer enables the LO dividers only after the VCO has full swing (and again after a band change or a failed lock). Eighth run: `en=35` is now the default (both chains); `en=off` gives the old behaviour; option `pq=<x>` widens the output PMOS of the UHF retiming flip-flops to check the 21 % duty (the TSPC output rises one gate later than it falls). Run all 8: `python3 -u run_step2.py | tee out/summary.txt`, then `python3 -u run_step2.py uhf ss pq=2 | tee out/summary_uhf_ss_pq2.txt`.

Earlier, second run setup: every phase output is **retimed by a TSPC flip-flop on the same clock** (UHF: the NAND outputs; VHF: all 8 phases, true from complement and complement from true), so all outputs leave through identical paths; 1 GΩ leaks on the TSPC nodes for the operating point.

```bash
cd /foss/designs/analog/lo/step2
mkdir -p out && python3 -u run_step2.py | tee out/summary.txt     # 8 transients, about 1-2 h
python3 -u run_step2.py vhf                                        # or one band: uhf / vhf
```

| Part | Circuit |
|---|---|
| VCO | The P2.3 netlist (`analog/vco/step2/run_step2.py`, sizes from its `out/range.json`), stand-in buffer removed; code and tail current per band as in VCO step 3 (≤ 4 mA, D12) |
| Buffer | Per side: 100 fF from the tank, self-biased CMOS inverter (50 kΩ feedback), second inverter; weak cross-coupled inverters for anti-phase. Rail-to-rail around V_DD/2 — meets the step-1 need of ≥ 0.5 V per side near V_DD − 0.55 V |
| UHF | CML ÷2 → CML-to-CMOS → TSPC Johnson ÷4 → NAND → retiming TSPC → four 25 % pulses I+, Q+, I−, Q− (D13) |
| VHF | CML ÷3 → CML-to-CMOS → TSPC Johnson ÷8 → retiming TSPC × 8 → 8 phases at 45° (D4) |

Runs: UHF at 3.20 and 3.84 GHz, VHF at 3.12 and 4.20 GHz (VCO), each at typical (1.2 V, 27 °C) and slow (mos_ss, 1.08 V, 125 °C). Reported per run: VCO frequency, buffer swing and common mode, current per supply (buffer, CML divider, converter, CMOS logic), and per output its frequency (against VCO / 8 or / 24), duty cycle (25 % / 50 %) and phase error against 90° / 45° spacing.

The phase errors here are systematic (layout-free, no mismatch); random mismatch follows in step 3 (Monte Carlo). All outputs are retimed, so their remaining systematic error comes from TSPC rise/fall asymmetry and loading.
