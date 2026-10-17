# SG13_Octagon_L2n0 regression

Provenance: [EM], except the name explanation, which is [LIT] from the gds2palace user guide. Date: 2026-10-17. Container `hpretl/iic-osic-tools:2026.10`. PDK commit `a49358cc0b20635fcb53c0940505e3563763fc7a`.

Definition, same for both solvers: `Z = 50*(I+S)*inv(I-S)`, `Zdiff = Z11-Z12-Z21+Z22`, `L = Im(Zdiff)/omega`, `Q = Im(Zdiff)/Re(Zdiff)`. Port de-embedding is not applied. That step is part of the matched-mesh comparison required before Phase 2.

## Shared inputs

Both solvers used one GDS and one stack-up file.

- GDS: `gds2openEMS` `v0.5.0` `L_2n0_twoport.gds`, sha256 `c8769e266a15f3209b1a8bf563a0af6fea8f572352646b182048078b4f48f659`. Port rectangles are 4 um tall. Substrate ground is layer 210.
- Stack-up, both runs: `/foss/pdks/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2/workflow/SG13G2_200um.xml`, sha256 `5d4529432b38d7996814f5096af2173d96e8ad5ff84c73ebb57904f1faf03bdf`.

The pinned PDK also ships `libs.tech/palace/workflow/SG13G2_200um.xml`, sha256 `2615d4d75d6d81e0314b42ecdedf754b9e856d826bf829cb7e14081d8fb1b044`. That file is not used. It is a different stack: air is 200 um rather than 300 um, substrate ground is a conductor on layer 250 rather than a via on layer 210, it adds a backside ground, and the MIM layers differ. The shared GDS ground layer matches the openEMS file, so that file is the one both solvers read.

## Results

| Solver | 2.4 GHz L | 2.4 GHz Q | 2.4 GHz R | 3.5 GHz L | 3.5 GHz Q | 3.5 GHz R |
|---|---|---|---|---|---|---|
| Palace | 1.6479349397451104 nH | 14.178858276240124 | 1.7526286642605555 ohm | 1.6643533396207333 nH | 18.73515364547795 | 1.9536024238555 ohm |
| openEMS | 1.6312015365634183 nH | 11.822375191490515 | 2.0806258698257807 ohm | 1.6410333779018373 nH | 14.909053105443727 | 2.4205567298574806 ohm |

Palace minus openEMS, relative to openEMS: L is +1.03% at 2.4 GHz and +1.42% at 3.5 GHz. Q is +19.9% at 2.4 GHz and +25.7% at 3.5 GHz.

openEMS used a 1 um Cartesian mesh, 1.54778e6 cells, and a 0 to 6 GHz transient stopped at -50 dB. Palace used a 5 um tetrahedral mesh, order 2, two discrete frequencies, and no adaptive passes. The meshes are not matched. Matched-mesh refinement, until L and Q each move by less than 2% between steps, is required before Phase 2 and is not a Phase 1 blocker.

## Why this is not 2.0 nH

The gds2palace user guide calls this cell "the 2nH inductor already known from IHP openEMS workflow". The name `L2n0` is that 2.0 nH class name. The pinned PDK has no ngspice compact model for this cell. The workflow trees have measured-versus-simulated data for `L6n2`, not for `L2n0`.

The extracted differential inductance is 1.63 nH (openEMS) and 1.65 nH (Palace) at 2.4 GHz, and it stays within 0.02 nH up to 3.5 GHz. The result is not a 2.0 nH inductor that has rolled off between those two frequencies. The ports are still inside `Zdiff`. De-embedding removes port inductance, so it would not move a 1.64 nH result up to the 2.0 nH name. The comparison against a compact model and against IHP measured data remains open because neither source is in this PDK commit for this cell.

## Provisional tank Q

Until the matched-mesh comparison is done, the design value is the lower Q, from openEMS: 11.8 at 2.4 GHz and 14.9 at 3.5 GHz. Any later number that uses this Q is marked provisional. The Phase 1 digital back end does not use it.

## Earlier runs, not the baseline

- Palace on the v0.8.2 GDS and the Palace workflow XML: `baseline/palace_mismatched_stack_lq.json`. Different stack-up and zero-height ports.
- openEMS on that same Palace GDS: `|S21|` about -67 dB. `baseline/openems_on_palace_gds.s2p`. Not an inductor measurement.
