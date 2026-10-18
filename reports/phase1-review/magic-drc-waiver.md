# Magic DRC waiver — run phase1f

Magic reports 7815 errors (Magic notes the count should be divided by 3-4).
All 7815 boxes lie inside the RM_IHPSG13_1P_64x16_c2 footprint (x 100-337 um, y 100-165 um).

Rules: NW.d SRAM exception, Cnt.c and Cnt.c SRAM exception (bit-cell device rules
inside IHP's foundry macro), and subcell abut/overlap (top-level vias landing on the
macro's Metal4 power pins).

KLayout DRC (IHP reference deck): 0 errors. LVS: pass. Antenna: pass.

Waived: foundry-supplied macro internals and pin-connection hierarchy artefacts.
To confirm with IHP's full KLayout deck on runs/phase1f/final GDS before any tapeout.
