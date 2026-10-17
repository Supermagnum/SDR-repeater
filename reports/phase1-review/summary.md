# Phase 1 review

Date: 2026-10-17. Scope: digital back end for one chain. No analog schematic, no layout, no fabrication.

Manifest snapshot: `tools/tool-manifest.lock` on this branch. PDK pin `a49358cc`. cocotb 2.1.0 from the image. Simulator: Icarus Verilog 14.0 in that image.

## What was done

RTL in `rtl/digital/` and cocotb tests in `rtl/cocotb/`. Six tests passed: SPI read/write, decimation by 4, 32-bit I2S slot with zero padding, RX duty-cycle blanking, wake-up then shutdown, and I-gain calibration.

`valid_iq` rises after `WAKE` output frames. That count is the wake-up-to-valid-IQ figure. It is in frames. There is no seconds value, because the sample clock is the host's.

The provisional tank Q is not an input. No Phase 1 result depends on it.

## Results against the digital targets

| Item | Result |
|---|---|
| SPI registers | Pass. Map in `rtl/digital/notes.md`. |
| I2S 16- and 32-bit slots, MSB-justified | Pass in simulation. 16-bit is the reset. |
| Decimation, DC loop, IQ cal | Pass for the boxcar, the first-order loop, and the gain/cross term implemented here. |
| Power-down and RX duty cycle | Pass as control logic. Supply current is not simulated. |
| CACE, DRC, LVS, PEX, EM | Not applicable. No layout and no analog netlist. |
| Optimisation logs | None. No sizing run. |

## Open risks

- LinHT SX1255 pin wiring is still unread. The 32-bit slot matches the datasheet's mode-B width. It does not prove the Rev C board uses that mode.
- Duty-cycle and wake figures are in output frames. A host sample rate is required before they become a time.
- Block power-down bypasses the decimator, DC loop, and IQ cal. It does not estimate current.
- Icarus warned that part-selects inside `always_comb` are not fully supported. The calibration math no longer uses those selects. The tests pass on this Icarus.

## Decisions needed

1. Accept this register map and I2S slave timing, or change the SPI frame and the MSB-justified edge before any host driver is written.
2. Analog topology remains unapproved. Phase 2 stays closed until the matched-mesh inductor comparison is also done.

## Dual-use table

Evidence is this RTL and the cocotb run, plus the LinHT notes already in `reports/linht-proposals.md`. Currents and temperatures were not simulated.

| Requirement | Repeater | LinHT |
|---|---|---|
| Supply rails | Decision from Phase 0 stands. This RTL draws no rail. | Same. 5 V buck is the host rail on paper. Ripple tolerance is not tested. |
| RX, TX, standby, shutdown current | not met. Modes exist. No current. | not met. Same RTL. Battery use needs the current numbers. |
| Both 2 m and 70 cm | not yet evaluated. One chain, band not selected in this RTL. | not met by current LinHT hardware. This chip is the intended VHF path. Dual-watch timing is not in this phase. |
| Duty cycle / thermal | Duty-cycle blanking is in the RTL. Continuous RX is the duty-enable-off case. Dissipation is not estimated. | Same blanking. No junction-temperature rise. |
| Temperature range | not yet evaluated | not yet evaluated |
| IQ interface | Met in RTL: 16-bit baseline, 32-bit slot available, MSB-justified, host is master. | Met in RTL for the 32-bit slot width. Rev C wiring was not confirmed from KiCad, so the board connection stays provisional. |
| Package at most 5 x 5 mm | not yet evaluated | not yet evaluated |
| USB-A security-dongle slot | not applicable | not designed. No part numbers. |

Work stops at this gate.
