# P2.6 step 2 — noise from the circuits

Details in the header of `run_p26s2.py`; results go to `spec/pll-topology.md` §13.

```bash
cd /foss/designs/analog/pll/p26/step2
mkdir -p out
python3 -u run_p26s2.py cp | tee out/summary_cp.txt          # charge pump + bias generator, small-signal noise (~10 min)
python3 -u run_p26s2.py lo tstop=1u | tee out/summary_lo1.txt  # LO-chain floor, short trial (~1 h)
python3 -u run_p26s2.py lo | tee out/summary_lo.txt          # 3 us transient noise (a few h); add 'ss' for the slow corner
python3 -u run_p26s2.py total | tee out/summary_total.txt    # total phase noise from out/cp_noise.json, out/lo_noise.json
```

| Part | Method | Replaces |
|---|---|---|
| `cp` | Noise analysis of the pump in its three locked states (off, UP, UP+DN), duty-weighted; FoM and 1/f corner | P2.2 FoM −218 dBc/Hz, corner 20 kHz [PROP] |
| `lo` | Transient noise of the P2.4 chains (validated method), output time-interval error → L(f) | P2.4 hand estimate −157 / −161 dBc/Hz |
| `total` | P2.2 model, D19 loop, simulated VCO per band, the two results above | P2.2 [PROP] inputs |
