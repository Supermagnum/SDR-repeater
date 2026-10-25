# AFE/LO control block — RTL (P2.5)

Digital parts of the PLL that live in the AFE/LO control block (`spec/analog-digital-interface.md` §5, D3). So far:

| File | Content | Status |
|---|---|---|
| `mmd.sv` | Multi-modulus feedback divider (step 2b): divide-by-4/5 prescaler from two 2/3 cells + program and swallow counters, N = 16–127, new ratio every cycle (latency one cycle) | Tests pass (icarus) |
| `sdm.sv` | Σ-Δ modulator (step 2c): MASH 1-1-1, 24 bits, LSB dither; divides {N_INT, N_FRAC} by P = 2 / 3 (D16) with a 32-cycle divider; integer-N mode | Bit-exact against `models.py`; tests pass |
| `lockdet.sv` | Lock detector (step 2c): UP / DN sampled at the reference + window (≈ 6.5 ns, analogue delay); 64 good cycles → lock, 4 bad → unlock | Tests pass |
| `bandcal.sv` | Band calibration (step 2c): successive approximation over the 7-bit bank, counts the prescaler output for 128 reference cycles per step against K·M/4; 29 µs | Tests pass against a VCO model |

```bash
cd /foss/designs/rtl/afe/cocotb
python3 run_afe.py                 # all four; ONLY=sdm python3 run_afe.py for one; SIM=verilator possible
```

Σ-Δ tests (`test_sdm.py`): seven settings (UHF and VHF, fractions 0 … 0.99999994, P = 2 and 3) — M exact, div_n bit-exact against the Python model for 2000 cycles, mean within 2·10⁻³ of M (500 ppm of one step), range M_int − 3 … + 4; integer-N mode constant. Lock detector (`test_lockdet.py`): lock after 64 cycles with 3.5 ± 1 ns UP pulses, held for 200 cycles, cleared within 4–6 cycles by a 9 ns UP or 8 ns DN error. Calibration (`test_bandcal.py`): six targets 3.12–4.20 GHz on a VCO model (4.41 GHz at code 0 to 2.90 GHz at code 127): the result is the highest code at or above the target within the counting resolution (≤ 0.06 %), 29.2 µs each.

Tests (`test_mmd.py`): every ratio 16–127 held constant (all output periods = N); 800 output cycles with a new ratio after every output pulse (400 random in 23–73, crossing the 32 and 64 boundaries, then 400 Σ-Δ-like N0 + (−3 … +4)) — every period equals one applied ratio with a constant latency of one cycle.

Timing for the silicon version: the two prescaler cells run at up to 2.2 GHz (TSPC cell of step 1: ÷3 to 2.9 GHz at the slow corner, 10/10 mismatch samples); the counters run at up to 550 MHz (standard cells). The divide-by-5 control `mc` is a flip-flop output on the prescaler clock and must settle within about two input periods (≈ 0.9 ns at 2.2 GHz) after the prescaler output edge — checked at transistor level / in timing analysis with the AFE block.
