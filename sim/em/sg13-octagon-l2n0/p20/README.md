# P2.0 — matched-mesh study of SG13_Octagon_L2n0

Phase 2 prerequisite (`spec/phase2-plan.md`, step P2.0; `reports/phase0-review/em-l2n0.md`). Goal: replace the **provisional tank Q** (openEMS 1 µm: 14.9 at 3.5 GHz) with a mesh-converged value, and explain the Phase 0 gap (Palace Q 18.7 vs openEMS 14.9).

Status: **stage 1 done 2026-10-19** (results and analysis: `reports/phase2-review/p20-stage1.md`); stage 2 next.

## Method

The same GDS, stack-up, ports, margins and boundary conditions as the Phase 0 baseline (`../palace_l2n0.py`, `../openems_l2n0_2port.py`); only the mesh changes, one setting per step. It follows the upstream gds2palace mesh-convergence method (`vendor/gds2palace/more_examples/mesh_convergence/AGENTS.md`).

| Step | Solver | Mesh | Why |
|---|---|---|---|
| `pal5` | Palace | 5 µm, order 2 | Phase 0 setting (now with a 2.0–4.5 GHz sweep) |
| `pal3`, `pal2`, `pal1` | Palace | 3 / 2 / 1 µm, order 2 | uniform refinement; upstream found Q needs ~2 µm on a 5 µm-trace spiral |
| `pal2o3` | Palace | 2 µm, order 3 | cross-check: basis order instead of mesh (stage 3) |
| `palamr` | Palace | 5 µm start, 2 AMR passes | cross-check: adaptive refinement (stage 3) |
| `palF3`, `palF2`, `palF1` | Palace | 3 / 2 / 1 µm, **filled metals + via fill-factor correction** | the conductor model that came closest to measurement in the upstream L6n2 study; the surface model read Q 24 % high there (stage 2) |
| `oem2`, `oem1`, `oem07`, `oem05` | openEMS | 2 / 1 / 0.7 / 0.5 µm | uniform refinement; the gds2palace guide notes openEMS needs ~0.5 µm to resolve skin effect (skin depth in Al ≈ 1.4 µm at 3.5 GHz) |

- **Quantities:** L = Im(Zdiff)/ω and Q = Im(Zdiff)/Re(Zdiff), Zdiff = Z11 − Z12 − Z21 + Z22, at 2.4, 3.12, 3.5, 3.65 and 4.2 GHz (`p20_extract.py`, reusing `../extract_lq.py`).
- **Convergence:** a solver is converged when its last refinement step moves both L and Q by < 2 % across 3.1–4.2 GHz (the Phase 0 criterion).
- **Comparison basis:** raw S-parameters (ports included) for both solvers, as in Phase 0.
- **Design values:** the finest converged Palace step, **de-embedded** with `combine_extend_snp.py`. This removes the estimated port series inductance, a geometric correction rather than a calibration, per the gds2palace FAQ.

## Run (inside the container)

The Phase 0 vendor checkouts must exist in `../vendor/` (gds2palace v0.8.2, gds2openEMS v0.5.0), as for `../run_in_container.sh`.

```bash
cd /foss/designs/sim/em/sg13-octagon-l2n0/p20
EM_NPROC=8 ./run_p20.sh stage1      # pal5 pal3 pal2 oem2 oem1 — start here
./run_p20.sh summary                # tables + verdict -> out/p20/summary.md
EM_NPROC=8 ./run_p20.sh stage2      # palF3 palF2 palF1 oem07
EM_NPROC=8 ./run_p20.sh stage3      # optional, heavy: oem05 pal1 pal2o3 palamr
./run_p20.sh pal2 oem1              # or any single steps
```

- Steps run one after another and skip anything already finished (`out/p20/<step>.json`); per-step logs are `out/p20/<step>.log`.
- **Do not run stage 2 blind.** Start with stage 1 and look at the times and memory in the logs. Reference points:
  - The upstream 115 µm spiral needed 2 m 20 s / 5.5 GB at 2 µm and 5 m / 9.7 GB at 1 µm on 16 cores. L2n0 with its 150 µm margin is larger.
  - openEMS at 0.5 µm has roughly 4–8× the cells of 1 µm (1.55 M) and a halved time step, so expect 10–15× the 1 µm run time.
- No repository files are changed by the runs (everything goes to the git-ignored `out/` and `palace_model/`).

## What to send back

`out/p20/summary.md` (or the `./run_p20.sh summary` output), plus the run time line of any step that took unexpectedly long.

## Outcome to expect

- Upstream mesh studies show L settling on coarse meshes and Q needing the finest; there, coarse Palace meshes gave Q 2–6 % low, so Palace Q may still rise a little from 18.7. openEMS Q is expected to rise as 0.7 / 0.5 µm resolve the skin effect. The Phase 0 gap should therefore close mainly from the openEMS side.
- If the two converged solvers still differ by more than about 5 % in Q, that is recorded as solver uncertainty, and the lower value stays the design value.
