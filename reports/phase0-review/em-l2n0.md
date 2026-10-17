# SG13_Octagon_L2n0 regression

Provenance: [EM]. Date: 2026-10-17. Container `hpretl/iic-osic-tools:2026.10`. These numbers are a baseline for later reruns. They are not a specification limit.

Definition, same for both solvers: `Z = 50*(I+S)*inv(I-S)`, `Zdiff = Z11-Z12-Z21+Z22`, `L = Im(Zdiff)/omega`, `Q = Im(Zdiff)/Re(Zdiff)`. No port de-embedding. `gds2palace` `combine_snp` was not used.

## Results

| Solver | 2.4 GHz L | 2.4 GHz Q | 2.4 GHz R | 3.5 GHz L | 3.5 GHz Q | 3.5 GHz R |
|---|---|---|---|---|---|---|
| Palace | 1.6422238313709743 nH | 14.205402121580939 | 1.7432911609356552 ohm | 1.6581223246803751 nH | 18.78960680171629 | 1.9406480818136629 ohm |
| openEMS | 1.6312015365634183 nH | 11.822375191490515 | 2.0806258698257807 ohm | 1.6410333779018373 nH | 14.909053105443727 | 2.4205567298574806 ohm |

Palace minus openEMS, relative to openEMS: L is +0.68% at 2.4 GHz and +1.04% at 3.5 GHz. Q is +20% at 2.4 GHz and +26% at 3.5 GHz. The extra Q comes from a lower series resistance in the Palace result.

Transmission on the valid runs is similar. Palace `|S21|` is -0.445 dB at 2.4 GHz and -0.704 dB at 3.5 GHz. openEMS `|S21|` is -0.468 dB and -0.736 dB at those frequencies.

## What was solved

- Palace: `gds2palace` tag `v0.8.2` (`ed063dc9`; the package version string inside that tag is still `0.8.1`). GDS `vendor/gds2palace/workflow/L_2n0_twoport.gds`, sha256 `59f560741001e2e61e817d28087796b350340ce73cfe6893c6bfd606b31c356f`. Stack-up `/foss/pdks/ihp-sg13g2/libs.tech/palace/workflow/SG13G2_200um.xml`, sha256 `2615d4d75d6d81e0314b42ecdedf754b9e856d826bf829cb7e14081d8fb1b044`. Two discrete frequencies, 2.4 GHz and 3.5 GHz. Refined cell size 5 um, 10 cells per wavelength, mesh size max 70, order 2, 8 MPI ranks, 247094 unknowns, 0 adaptive iterations, about 126 s. Mesh about 7689 nodes and 61403 tetrahedra. gmsh left 5 ill-shaped tetrahedra. Port layers 201 and 202 in this GDS are zero-height polygons. The reader warned that it could not repair them. `|S21|` is still about -0.4 dB, so the ports did connect.
- openEMS: `gds2openEMS` tag `v0.5.0` (`99d8bd18`). GDS `vendor/gds2openEMS/workflow/L_2n0_twoport.gds`, sha256 `c8769e266a15f3209b1a8bf563a0af6fea8f572352646b182048078b4f48f659`. Stack-up `/foss/pdks/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2/workflow/SG13G2_200um.xml`, sha256 `5d4529432b38d7996814f5096af2173d96e8ad5ff84c73ebb57904f1faf03bdf`. Transient 0 to 6 GHz, 61 frequency bins, energy stop -50 dB, refined cell size 1 um, 20 cells per wavelength, 8 threads. Mesh 249 x 222 x 28 = 1.54778e6 cells. Solve time 800 s and 847 s for the two excitations. openEMS warned that the timestep is very small.

Inductor metal bounding boxes on layers 126 and 134 match between the two GDS files. The files differ in the ports and the substrate ground: the Palace GDS has zero-height ports and ground on layer 250; the openEMS GDS has 4 um port rectangles and ground on layer 210. Each stack-up file expects its own ground layer. Air thickness is 200 um in the Palace file and 300 um in the openEMS file. Substrate thickness is 180 um in both. MIM stack definitions differ. Metal conductivities match.

## Discarded openEMS run

The first openEMS run used the Palace GDS with the openEMS stack-up. Port polygons had zero area, and layer 250 is not the openEMS substrate-ground layer. `|S21|` was -67.3 dB at 2.4 GHz and -68.1 dB at 3.5 GHz. The differential formula then returned about -820 nH and -632 nH. That file is kept as `baseline/openems_on_palace_gds.s2p`. It is not an inductor measurement.

## What the disagreement is

L agrees to about 1%. Q does not. The two runs are not the same mesh, not the same frequency method, and not the same stack-up file. The Q gap is therefore not a pure solver delta. A later mesh-convergence check is required before either Q is used as a design number.
