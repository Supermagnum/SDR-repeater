# P2.6 step 1 — behavioural closed loop with the circuit data

`closed_loop.py` (numpy, scipy; runs anywhere, no simulator; details in its header, results in `spec/pll-topology.md` §13):

```bash
cd analog/pll/p26/step1
mkdir -p out
python3 closed_loop.py | tee out/summary.txt          # corrected 60 kHz loop filter (about 1 min)
python3 closed_loop.py built | tee out/summary_built.txt   # the P2.5 filter as built (about 42 kHz, 35 deg)
python3 closed_loop.py land                           # calibration landing sweep only
python3 closed_loop.py bw=75e3                        # another bandwidth for the corrected design
```

It models the band calibration (`rtl/afe/bandcal.sv`, and variants: 8-bit bank, counter at f / P, 'nearest' rule), the
release of the V_tune hold, acquisition with a tri-state PFD and the measured pump compliance, the loop filter
(exact), the VCO tuning (P2.3), the divider with the bit-exact Σ-Δ sequence, and the two-sided lock detector.
