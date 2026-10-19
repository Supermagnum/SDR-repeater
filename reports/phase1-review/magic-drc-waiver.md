# Magic DRC waiver — run phase1f

Magic reports 7815 errors (Magic notes the count should be divided by 3-4).
All 7815 boxes lie inside the RM_IHPSG13_1P_64x16_c2 footprint (x 100-337 um, y 100-165 um).

Rules: NW.d SRAM exception, Cnt.c and Cnt.c SRAM exception (bit-cell device rules
inside IHP's foundry macro), and subcell abut/overlap (top-level vias landing on the
macro's Metal4 power pins).

KLayout DRC (IHP reference deck): 0 errors. LVS: pass. Antenna: pass.

Waived: foundry-supplied macro internals and pin-connection hierarchy artefacts.
To confirm with IHP's full KLayout deck on runs/phase1f/final GDS before any tapeout.

## Update — run phase1g (2026-10-18)
NW.d (4 errors at the corners of the SRAM keep-out region, IHP full deck) fixed by
FP_MACRO_VERTICAL_HALO = 13.78 um (one row): row cuts now fall on ground boundaries.
IHP full KLayout DRC (maximum rule set, --antenna, --no_density): 0 errors.
LVS: 0 differences. Antenna: 0 violations. Setup WS +1.20 ns, hold WS +0.05 ns, TNS 0.
Magic: 7816 errors, all inside the RM_IHPSG13_1P_64x16_c2 footprint, waived as above.
Density not checked at block level; required at chip level with fill.

## Update — run phase1i (2026-10-18), new reference layout
Includes SPI mode 0, Philips I2S, clk-domain reset synchroniser, output scale 16384,
per-clock I/O constraints, post-GRT design repair (SRAM A_DOUT max-cap fixed).
IHP full KLayout DRC (maximum rule set, --antenna, --no_density): 0 errors.
LVS 0, antenna 0, max-cap 0, routing DRC 0. Setup WS +0.80 ns, hold WS +0.10 ns, TNS 0.
Cell area 0.708 mm2. Magic: 7817 errors, all inside the SRAM footprint, waived as above.

## phase1j and phase1k (2026-10-19)

- `phase1j`: 7 818 Magic findings, all inside the SRAM footprint (100, 100)–(336.80, 164.36) µm, 0 outside.
- `phase1k` (reference): 7 815 Magic findings, all inside the SRAM footprint, 0 outside. IHP full KLayout deck (maximum rule set, antenna on, density off): 0 violations.
- Checked by script: every Magic box compared against the macro bounding box from the LEF `SIZE` and the placement at (100, 100). The waiver is unchanged.
