# P2.4 step 1 — divider speed checks

The device checks of `spec/lo-divider-topology.md` §5 in one script.

Status 2026-10-20, second run:
- **TSPC (D14): passes.** f_max 6–7 GHz typical, 4.0 GHz at the slow corner: 2.7× margin for the VHF Johnson clock (1.47 GHz) and 1.8× for UHF (2.2 GHz), both above the 1.3× of D14. CMOS flip-flops stay.
- **Converter: passes.** Duty 50–51 % typical, 45–46 % slow corner, full CMOS levels.
- **CML ÷2 / ÷3: fine at typical** (÷2 2–12+ GHz, ÷3 2–8 GHz), **but at the slow corner they fail below about 4–5 GHz** while dividing up to 10 / 7 GHz, and the tail node of the ideal current source goes below 0 V (no headroom at 1.08 V). The ÷3 then misses its 3.12–4.20 GHz operating range. Third run (`cmlx`): larger clock swing, stronger latch pair, tail-less latch, on the operating window only.

Third run result: **a 0.5 V-per-side clock fixes both dividers at the slow corner** (÷2 divides 2–8 GHz, ÷3 2–6.5 GHz; 1.0 / 2.5 mA). A stronger latch pair adds nothing; the tail-less latch fails at the slow corner (current-starved). With 0.27 V per side the dividers fail below 5 GHz at the slow corner. Fourth run (`amp`): minimum clock swing for the whole window — slow corner 0.35 V (÷2) / 0.40 V (÷3), typical and fast 0.30 V. **Step 1 done**; results and the buffer requirement (≥ 0.5 V per side) in `spec/lo-divider-topology.md` §7.

```bash
cd /foss/designs/analog/lo/step1
mkdir -p out && python3 -u run_step1.py | tee out/summary.txt     # all checks
python3 -u run_step1.py amp                                        # or some of: cml2 cml3 tspc conv cmlx amp
```

| Check | Circuit | Pass (slow corner: mos_ss, 1.08 V, 125 °C) |
|---|---|---|
| `cml2` | CML ÷2 (master-slave latch pair), 0.3 / 0.5 / 0.8 mA per latch | Divides correctly up to ≥ 5.7 GHz (1.3 × 4.41 GHz) |
| `cml3` | CML ÷3: two CML flip-flops and a single-level NOR with a reference input | Same, ≥ 5.7 GHz |
| `tspc` | CMOS TSPC flip-flop as a toggle, 3 sizes (D14) | ≥ 1.9 GHz (VHF Johnson ÷8 clock) and ≥ 2.9 GHz (UHF Johnson ÷4 clock) |
| `conv` | CML-to-CMOS converter (NMOS pair, PMOS mirror, two inverters) | Duty cycle near 50 % and full CMOS levels at 1.47 and 2.2 GHz |

Every frequency is run; `f_max` is the top of the first unbroken run of correct divisions (output = input / N within 1 % and a real swing), and the pattern column shows each frequency. First run (2026-10-20): almost every case reported 0 GHz — the TSPC clock was on an undriven node (fixed), and the CML cases are now also run at two clock common modes with the tail-node voltage shown (headroom at 1.08 V). Converter first run: duty 50–51 % (typical), 45–46 % (slow corner), full CMOS levels.

Results: `out/summary.md` (send it back); netlists and logs in `out/`.
