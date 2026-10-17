# Baseline decisions after Phase 0

Human decisions of 2026-10-17. LinHT hardware facts remain provisional until Rev C is validated.

## Supplies

The single-cell 3.0-4.2 V assumption is withdrawn.

- Repeater: regulated backplane rails. `docs/RF-modules.md` r0.3 names +12 V for the external PA, +5 V, +3.3 V, and +1.8 V. Those names are the host rails, not a finished RFIC pinout.
- LinHT: the public README describes a 2S pack, a BQ25792 charger, and a TPS565242 5 V buck. The RFIC is fed from regulated rails on that board, not from the cells.
- The RFIC specification must include tolerance to buck-regulator ripple and to the spurs of those regulators. No ripple amplitude has been measured.

## Reference and I2S

- The PLL must lock from either a 32 MHz or a 36 MHz reference.
- Integer-boundary locations for both references are in `spec/integer-boundary-spurs.md` ([HAND]).
- I2S slot width is configurable, 16 or 32 bits per channel, MSB-justified. 16-bit data is the baseline. The 32-bit slot exists so a LinHT-style SX1255 mode B port can be matched. The SX1255 wiring on Rev C was not confirmed from KiCad.

## DRC

KLayout DRC invocations in this project use `--minimum_drc`. `--precheck_drc` is not used.

## Phase noise

ngspice 47 experimental PSS may be used. Every phase-noise number is labelled lower confidence. QUCS-COPEN is not used.
