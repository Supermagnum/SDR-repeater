# AFE/LO control block — RTL (P2.5)

Digital parts of the PLL that live in the AFE/LO control block (`spec/analog-digital-interface.md` §5, D3). So far:

| File | Content | Status |
|---|---|---|
| `mmd.sv` | Multi-modulus feedback divider (step 2b): divide-by-4/5 prescaler from two 2/3 cells + program and swallow counters, N = 16–127, new ratio every cycle (latency one cycle) | Functional tests pass (icarus) |

```bash
cd /foss/designs/rtl/afe/cocotb
python3 run_mmd.py                 # icarus; SIM=verilator python3 run_mmd.py
```

Tests (`test_mmd.py`): every ratio 16–127 held constant (all output periods = N); 800 output cycles with a new ratio after every output pulse (400 random in 23–73, crossing the 32 and 64 boundaries, then 400 Σ-Δ-like N0 + (−3 … +4)) — every period equals one applied ratio with a constant latency of one cycle.

Timing for the silicon version: the two prescaler cells run at up to 2.2 GHz (TSPC cell of step 1: ÷3 to 2.9 GHz at the slow corner, 10/10 mismatch samples); the counters run at up to 550 MHz (standard cells). The divide-by-5 control `mc` is a flip-flop output on the prescaler clock and must settle within about two input periods (≈ 0.9 ns at 2.2 GHz) after the prescaler output edge — checked at transistor level / in timing analysis with the AFE block.
