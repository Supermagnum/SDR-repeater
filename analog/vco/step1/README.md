# P2.3 step 1 — device checks before the VCO schematic

The five checks in `spec/vco-topology.md` §6, in one script.

Status: **done 2026-10-20** (results in `spec/vco-topology.md` §8). First run: limits done (1.5 V differential at a 1.1 V centre tap); inductor model **PASS** (worst 0.71 % in L and Q, Cp ≈ 30 fF); tail noise: HV NMOS lowest flicker (corner 0.5 MHz against 1.3 MHz LV NMOS and 3.2 MHz LV PMOS at 80/2 µm); bank cell: switches up to 32 µm too lossy (Q_on ≤ 28 at 4.2 GHz); varactor failed on a parameter name. Second run:
- **Bank:** with 200 kΩ bias resistors (20 kΩ made the off state lossy: Q_off 6–50 against 46–311) and 96–128 µm of switch per 60 fF cell, the whole 7-bit bank keeps 0.89–0.91 of tank Q at the low edge and 0.97 at the high edge, with +104 to +226 fF left in the 762 fF budget. Proposed: about 100 µm per 60 fF, 200 kΩ.
- **Tail:** at the real tail voltage (0.35 V) the HV NMOS keeps only 74 % of its current (headroom), the LV NMOS 85 %. LV NMOS 160/4 µm: flicker corner 0.14–0.32 MHz, at 600 kHz within 1.5× of the white floor. Proposed tail: LV NMOS of at least 160/4 µm.
- **Varactor:** the PDK's VACASK conversion does not elaborate (`v(2,4)` in the well resistance). Third run uses a local copy with those zero-coefficient terms removed.

```bash
cd /foss/designs/analog/vco/step1
python3 run_step1.py                 # all checks, a few minutes
python3 run_step1.py bank flicker    # or some of: limits var bank flicker ind
```

Results: `out/summary.md` (send this back); netlists and logs in `out/`. Check 5 also writes the inductor model `analog/vco/models/l2n0_lumped.inc`, which P2.3 uses and which should be committed.

| # | Check | Method | Decides |
|---|---|---|---|
| 1 | LV MOS voltage limits | SG13G2 process specification Rev. 1.2: LV `VGS ≤ 1.65 V @ 125 °C`, BVDSS ≥ 2.0 V `[DS]` | Swing and VCO supply (D10) |
| 2 | `sg13_hv_svaricap` | AC, differential C and Q at 3.0–4.37 GHz against tuning voltage, 1 and 2 fingers | Varactor size, tuning window, KVCO |
| 3 | Bank unit cell | AC, two `cap_rfcmim` (9 × 9 µm) and an LV NMOS switch (2–32 µm), on and off | C_on/C_off at Q ≥ 80 → whether the 762 fF fixed-capacitance budget holds |
| 4 | Tail-device noise | Noise analysis, drain-current PSD of LV NMOS, LV PMOS, HV NMOS (80/2 µm) at 3 mA | Tail device (D9) |
| 5 | Inductor model | Fit of a lumped differential model to the de-embedded P2.0 EM data (palF1), then an AC check in VACASK | Model for pss/pnoise; pass if L and Q within 1 % |

Notes:
- Check 1 is already known from the PDK document: with 10 % oxide margin, a centre-tap voltage of about 1.1 V allows about 1.5 V differential swing, more than the memo's 1.0 V assumption.
- The EM inductor (`L_2n0_twoport.gds`) has **no centre tap**. The lumped model places the tap at the electrical midpoint of a symmetric split. A tapped layout needs its own EM run before layout (P2.7).
- Checks 2–5 use the typical corner at 27 °C. Corners and temperature follow in step 3.
- Check 5 needs the P2.0 output under `sim/em/sg13-octagon-l2n0/p20/` (`out/p20/palF1.json` and the de-embedded `.s2p` in `palace_model/`). Without them it is skipped.

Third run (varactor, local copy): per finger 3.7 → 2.1 fF differential over V_G − V_W = +1.2 … −1.2 V, steepest about 1.4 fF/V near −0.3 V, Q 110–190 at 4.2 GHz. About 12 fingers give the 10 fF the 7-bit bank needs over a 0.7 V window. The bias point is decision D11 (`spec/vco-topology.md` §8).
