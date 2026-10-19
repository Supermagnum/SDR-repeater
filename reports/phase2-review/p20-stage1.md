# P2.0 stage 1 — matched-mesh study of SG13_Octagon_L2n0

Provenance: [EM]. Run 2026-10-19 in `hpretl/iic-osic-tools:2026.10`, PDK `a49358cc`, same GDS (sha256 `c8769e26…`) and stack-up (sha256 `5d452943…`) as Phase 0. Scripts: `sim/em/sg13-octagon-l2n0/p20/`. 8 MPI processes / threads.

## Results (raw S-parameters, ports included)

| Step | Model | Cell | Time | L @ 3.65 GHz | Q @ 2.4 | Q @ 3.12 | Q @ 3.5 | Q @ 3.65 | Q @ 4.2 |
|---|---|---|---|---|---|---|---|---|---|
| pal5 | Palace, surface conductors | 5 µm | 3.4 min | 1.6665 nH | 14.18 | 17.21 | 18.73 | 19.09 | 21.01 |
| pal3 | Palace, surface | 3 µm | 6.7 min | 1.6707 nH | 14.47 | 17.61 | 19.20 | 19.57 | 21.57 |
| pal2 | Palace, surface | 2 µm | 9.2 min | 1.6721 nH | 14.55 | 17.73 | 19.33 | 19.70 | 21.73 |
| oem2 | openEMS | 2 µm (0.37 M cells) | 7.6 min | 1.6343 nH | 11.40 | 13.32 | 14.27 | 14.60 | 15.71 |
| oem1 | openEMS | 1 µm (1.55 M cells) | 26.8 min | 1.6432 nH | 11.82 | 13.90 | 14.91 | 15.26 | 16.44 |

Palace pal2, de-embedded (port series inductance removed): L 1.6696 nH, Q 19.67 at 3.65 GHz; the port correction is < 0.2 %.

## Convergence

- **Palace (surface model): converged.** 3 → 2 µm moves L by ≤ 0.09 % and Q by ≤ 0.73 % (limit 2 %); 5 → 3 µm moved Q by 2.0–2.7 %. Q rises with refinement, as in the upstream inductor study.
- **openEMS: not converged.** 2 → 1 µm moves Q by +3.7 … +4.7 %. Extrapolating the two points to zero cell size gives Q ≈ 15.5 (error ∝ h²) to 15.9 (error ∝ h) at 3.65 GHz.
- **L agrees within 2 %** between the solvers at every frequency (openEMS lower, plausibly the nearby PEC box walls).
- **Q still differs by 23–32 %**, Palace higher. More openEMS refinement can close only about 2–4 % of that.

## Why the solvers differ: the conductor model

The pinned gds2palace v0.8.2 includes a measured-vs-simulated study of IHP's L6n2 inductor (`vendor/gds2palace/more_examples/measured_vs_simulated/more_accurate_models_L6n2_v2/`). Its measured and simulated Touchstone files were evaluated here with the same L/Q definition, at this project's frequencies:

| L6n2 model (upstream files) | Q @ 3.5 GHz | vs measured |
|---|---|---|
| **Measured** (de-embedded) | **14.92** | — |
| Surface conductors, via arrays merged, no correction (= this study's Palace setup) | 18.50 | **+24 %** |
| Surface conductors, merged vias with fill-factor correction | 17.21 | +15 % |
| Filled-metal volume mesh + correction, 2 µm | 13.64 | −9 % |
| Filled metals + correction + conformal passivation, 1 µm | 14.05 | −6 % |

So the Palace setup used in Phase 0 and in stage 1 (surface-impedance conductors, merged vias without the fill-factor correction) reads Q about 24 % high on a measured IHP inductor at these frequencies. openEMS meshes the metal volume, as the filled-metal Palace model does.

Applying the L6n2 ratio (14.92 / 18.50 = 0.806) to the converged L2n0 Palace result gives **Q ≈ 15.6 at 3.5 GHz and ≈ 15.9 at 3.65 GHz**. That matches the extrapolated openEMS value (15.5–15.9). This is indicative only: L6n2 is a different coil (6.2 nH, 8 µm traces, more via crossings).

## Conclusion for now

- **Best estimate of the L2n0 tank Q at 3.5–3.65 GHz: about 15.5–16**; L = 1.67 nH (Palace) / 1.64 nH (openEMS).
- **The provisional design Q of 14.9 stays** until stage 2, and is about 5 % conservative.
- For the VCO this is good news: the validated pnoise test case (`analog/pn-validation/`) used Q 15.8, so the −124 dBc/Hz at 1 MHz starting point holds.

## Stage 2 (changed after these results)

The surface-model refinement steps (`pal1`, order 3, AMR) would only refine a model that is known to read high, so they move to an optional stage 3. Stage 2 now runs:
- `palF3`, `palF2`, `palF1`: Palace with **filled metals and the via fill-factor correction**, on the pinned-PDK stack-up. The conformal-passivation stack-up from the upstream study is not used: it is not from the PDK, and its substrate ground is on a different layer from this GDS.
- `oem07`: openEMS at 0.7 µm, about 1 h expected.

Expected outcome: Palace (filled) and openEMS converge to within about 5 %, near Q ≈ 15–16. If they do, the converged value replaces the provisional 14.9.
