# P2.0 stage 2 — filled-metal Palace and openEMS 0.7 µm (SG13_Octagon_L2n0)

Provenance: [EM]. Run 2026-10-19/20 in `hpretl/iic-osic-tools:2026.10`, PDK `a49358cc`, same GDS and stack-up as Phase 0 and stage 1. Scripts: `sim/em/sg13-octagon-l2n0/p20/` (`./run_p20.sh stage2`). 8 MPI processes / threads. Stage 1: `p20-stage1.md`.

## Results (raw S-parameters, ports included)

| Step | Model | Cell | Time | L @ 3.65 GHz | Q @ 2.4 | Q @ 3.12 | Q @ 3.5 | Q @ 3.65 | Q @ 4.2 |
|---|---|---|---|---|---|---|---|---|---|
| palF3 | Palace, filled metals + via fill-factor correction | 3 µm | 8.0 min | 1.6907 nH | 11.93 | 14.00 | 15.00 | 15.23 | 16.45 |
| palF2 | Palace, filled + correction | 2 µm | 11.7 min | 1.6920 nH | 12.01 | 14.13 | 15.16 | 15.40 | 16.67 |
| palF1 | Palace, filled + correction | 1 µm | 26.7 min | 1.6924 nH | 12.08 | 14.25 | 15.31 | 15.56 | 16.89 |
| oem1 | openEMS (stage 1) | 1 µm | 26.8 min | 1.6432 nH | 11.82 | 13.90 | 14.91 | 15.26 | 16.44 |
| oem07 | openEMS | 0.7 µm | **2 h 55 min** | 1.6437 nH | 12.06 | 14.30 | 15.42 | 15.81 | 17.14 |
| pal2 | Palace, surface conductors (stage 1, for reference) | 2 µm | 9.2 min | 1.6721 nH | 14.55 | 17.73 | 19.33 | 19.70 | 21.73 |

## Convergence

- **Palace, filled metals: converged** by the Phase 0 criterion. 2 → 1 µm moves L by ≤ 0.04 % and Q by ≤ 1.31 % (limit 2 %). The Q steps do not shrink (3 → 2 µm +1.08 %, 2 → 1 µm +1.02 % at 3.5 GHz), which is what first-order convergence in cell size looks like over equal 1 µm steps; extrapolated to zero cell size, Q ≈ 15.5 at 3.5 GHz and 15.7 at 3.65 GHz (+1 %).
- **openEMS: not converged.** 1 → 0.7 µm moves Q by +2.0 … +4.3 % (L by 0.03 %). The step is nearly as large as the 2 → 1 µm step (ratio 0.8 at 3.5 GHz, where first-order convergence would give 0.3), so the run is not yet in its asymptotic range and cannot be extrapolated reliably. Q is still rising; finer meshes would move it up, not down.
- **L converged in both solvers** (≤ 0.04 % per step).

## Solver comparison at the finest meshes

| f (GHz) | L Palace F1 | L openEMS 0.7 | ΔL | Q Palace F1 | Q openEMS 0.7 | ΔQ |
|---|---|---|---|---|---|---|
| 2.40 | 1.6804 | 1.6315 | +3.0 % | 12.08 | 12.06 | +0.2 % |
| 3.12 | 1.6857 | 1.6366 | +3.0 % | 14.25 | 14.30 | −0.3 % |
| 3.50 | 1.6909 | 1.6415 | +3.0 % | 15.31 | 15.42 | −0.7 % |
| 3.65 | 1.6924 | 1.6437 | +3.0 % | 15.56 | 15.81 | −1.6 % |
| 4.20 | 1.7033 | 1.6536 | +3.0 % | 16.89 | 17.14 | −1.5 % |

- **Q agrees within 1.6 %** across 2.4–4.2 GHz once both solvers mesh the conductor volume. The Phase 0 gap (Palace 18.7 vs openEMS 14.9, +26 %) was the conductor model (surface-impedance sheets, vias merged without fill-factor correction), as stage 1 concluded from the upstream L6n2 measurement, plus about 3 % of unresolved openEMS mesh.
- **L differs by a constant 3.0 %**, Palace higher, at every frequency and every mesh. A constant offset that does not move with mesh is a geometry or boundary difference, not discretisation: candidates are the openEMS PEC box walls (image currents lower L) and the different port models. It is larger than the 2 % Phase 0 agreement figure, so it is carried as an L uncertainty rather than resolved here.
- The upstream L6n2 study has the filled-metal model reading 6–9 % **below** measurement. If that carried over, the real L2n0 Q would be 16–17 at 3.5 GHz. Indicative only (different coil, and the best upstream variant used a non-PDK conformal-passivation stack-up).

## Proposed design values

The finest converged Palace step, de-embedded (port series inductance removed), as defined in the P2.0 README. Both extrapolations and the openEMS trend lie above it, so it is a conservative value, not a central one.

| f (GHz) | L (nH) | Q | R (Ω) |
|---|---|---|---|
| 2.40 | 1.678 | 12.1 | 2.10 |
| 3.12 | 1.683 | 14.2 | 2.30 |
| 3.50 | 1.688 | 15.3 | 2.43 |
| 3.65 | 1.690 | 15.5 | 2.46 |
| 4.20 | 1.701 | 16.9 | 2.66 |

- **L uncertainty ±3 %** (1.64–1.70 nH): the solver offset above. For the VCO that is ±1.5 % in frequency (about ±55 MHz at 3.65 GHz); the P2.3 capacitor bank must cover 3.12–4.20 GHz over this range as well as over the PDK corners.
- **Effect on the phase-noise plan:** Q 15.3 instead of the provisional 14.9 at 3.5 GHz is +0.2 dB better. Against the validated pnoise case (Q 15.8, −124 dBc/Hz at 1 MHz) it is 0.3 dB worse at 3.5 GHz and 0.9 dB worse at the 3.12 GHz band edge (Q 14.2). The margin to the −116 dBc/Hz target stays about 7 dB before real-VCO penalties; the risk "real tank Q below 12" in `spec/phase2-plan.md` §6 does not apply in the VCO band (Q ≥ 14.2 from 3.12 GHz).
- The 2.4 GHz value (12.1) is listed for continuity with Phase 0 only; 2.4 GHz is outside the VCO range.

## Stage 3: not needed

Stage 3 (`oem05`, `pal1`, `pal2o3`, `palamr`) would refine the openEMS trend and the surface model. It is not needed for the decision:
- The surface model is known to read high, so `pal1`, `pal2o3` and `palamr` would refine a model that is not used.
- `oem05` would take an estimated 8–15 h (`oem07` took 6.6× the 1 µm run) and can only raise the openEMS Q, which would not lower the conservative design value.

It stays available for a reviewer who wants the openEMS asymptote.

## Still open in P2.0

- Owner acceptance of the EM result (the P2.0 gate).
- The pnoise check of the flicker region (`analog/pn-validation/`), the other half of P2.0.
- The 3 % L offset between solvers, recorded as uncertainty.
