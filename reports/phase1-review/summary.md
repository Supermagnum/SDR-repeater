# Phase 1 review

Date: 2026-10-17. This is a resubmission. It is not an approval.

Scope: digital back end for one chain. No analog schematic, no layout, no fabrication. The matched-mesh inductor study has not been started. Phase 2 has not been started.

The register map and the SPI frame are proposed. They are not frozen.

Manifest snapshot: `tools/tool-manifest.lock` on this branch. PDK pin `a49358cc`. Container `hpretl/iic-osic-tools:2026.10`. cocotb 2.1.0. Simulator: Icarus Verilog 14.0. Synthesis: LibreLane classic flow, Yosys, OpenSTA, stopped after pre-place timing. Standard cells: `sg13g2_stdcell`.

## What changed since the first submission

The boxcar decimator is gone. The chain is two order-4 CIC stages, a 3-tap compensation FIR, and a 31-tap half-band. The modulator clock is the 32 MHz or 36 MHz reference. It is not 38.4 MHz. Every listed sample rate divides both references exactly. The table is in `spec/i2s-clocking.md`.

The RFIC is the I2S master by default. `BCLK` and `LRCLK` are divided from the reference. Slave mode remains, with an 8-deep asynchronous FIFO and sticky overflow and underflow flags. The clock-domain note is `rtl/digital/cdc.md`. A proposed backplane change for pins b14 and b15 is in `spec/i2s-clocking.md`. `docs/RF-modules.md` revision 0.3 was not edited.

IQ calibration includes the signed cross term. One phase LSB is 1/128 rad, about 0.45 degrees. Two degrees is about 4.5 LSB. That is the correction grid. It is not a claim that an uncalibrated mixer meets 2 degrees.

The DC accumulator and the CIC state are kept across RX sleep. `DC_CLEAR` is the explicit clear.

`BAND` selects divide-by-8 or divide-by-24 and starts a digital relock count of 64 reference clocks. That is not an analog PLL lock. `CHIP_ID` reads `0x11`. Writes to it are ignored.

The provisional tank Q is not an input.

## Numeric filter result

Limits used by `filter_response_limits`: passband ripple at most 0.25 dB from 0 to 0.40 of the sample rate, and alias attenuation at least 45 dB for images 1 through 4. Computed worst case over all ten reference and rate pairs: ripple 0.189 dB, alias attenuation 48.1 dB. Both pass.

A constant 1000 through the 32 MHz, 500 kHz chain settles at 1386 or 1387. Full-scale positive input clips at +32767 and does not wrap negative.

## Wake-up to valid IQ

`WAKE` is a count of output frames. The sample rate is exact, so the time is the same on both references.

| Sample rate | One frame | N wake frames |
|---|---|---|
| 25 kHz | 40 us | N * 40 us |
| 50 kHz | 20 us | N * 20 us |
| 100 kHz | 10 us | N * 10 us |
| 200 kHz | 5 us | N * 5 us |
| 500 kHz | 2 us | N * 2 us |

With the DC state kept, the first valid word after standby is already settled. Extra settle frames: 0. After `DC_CLEAR`, with shift 1 and a 200 LSB offset, the first new word is 100 LSB and the error is under 20 LSB on the fourth new word. At 25 kHz that is 160 us. At 500 kHz it is 8 us. The same frame count applies on both references.

## Clock cases

All ten reference and rate pairs, and both slot widths, were checked in cocotb. `LRCLK` period equals M reference clocks except the one illegal combination.

Illegal: 36 MHz, 500 kHz, 32-bit slots. M is 72 and the frame needs 64 bit cells, so some cells would be one reference clock. `clk_error` is set and the clocks stay low. A 32 MHz bit clock is not an integer divide of 36 MHz. There is no PLL in this block.

Legal special case: 32 MHz, 500 kHz, 32-bit slots. Every cell is one reference clock, and `BCLK` is the reference.

## Synthesis

LibreLane classic flow on `ihp-sg13g2`, clock period 27.778 ns (36 MHz), stopped at pre-place static timing. No clock tree and no placed wires.

| Item | Value |
|---|---|
| Cell area | 518670 µm² (0.519 mm²) |
| Flip-flops | 3300 `sg13g2_dfrbpq_1` |
| Setup, slow 1.08 V 125 C | WNS -19.75 ns, TNS -10749 ns |
| Setup, typical 1.20 V 25 C | WNS -5.21 ns |
| Setup, fast 1.32 V -40 C | WNS +3.35 ns |
| Hold, slow | WNS +0.058 ns |
| Hold, typical | WNS -0.044 ns, 5 paths |
| Hold, fast | WNS -0.109 ns |

The typical failing path starts at `adc_valid` and crosses a gate with fanout 541 before it reaches a flip-flop. This is a pre-place result. It is not a signoff. The 36 MHz constraint is not met in the slow or typical corner before placement and buffer insertion.

Power is one OpenSTA estimate under its default activity. It is not a per-mode simulation. The netlist does not gate `clk`, so the same clock-running estimate applies in shutdown, standby, RX, and TX whenever the reference is running. Stopping the reference outside the chip would leave leakage.

| Corner | Total | Leakage |
|---|---|---|
| typical 1.20 V 25 C | 7.06 mW | 6.07 µW |
| slow 1.08 V 125 C | 5.56 mW | 26.4 µW |

Clock-pin power in that report is about zero because there is no clock tree.

## Lint

`verilator --lint-only -Wall` on the RTL, top `digital_backend`, exits 0.

The same lint on the gate netlist plus `sg13g2_stdcell.v` exits with 82 warnings, all in the PDK cell models (`specify` blocks, UDP filenames, undriven notifier nets). Re-run with those PDK warnings waived (`SPECIFYIGN`, `DECLFILENAME`, `BLKSEQ`, `UNUSEDSIGNAL`, `UNDRIVEN`, `INITIALDLY`, `WIDTHTRUNC`) exits 0. No warning was reported in the netlist itself under that waiver.

Icarus prints a "sorry" that a constant select in `cic4` makes the combinational process sensitive to all bits of the sample. The cocotb suite still passes.

## Cocotb coverage

Nine tests, nine passes, Icarus, cocotb 2.1.0.

| Test | What it covers |
|---|---|
| `spi_reset_and_registers` | Reset value of every implemented register, writes, chip-id write ignored, CTRL bit 7 does not stick, standby keeps GAIN_I, band bit sticks |
| `phase_cross_term` | phase = 32, I = 0, Q = 400 gives I = 100 and Q = 400 |
| `master_frame_lengths` | Both references, all five rates, both slot widths. Frame length equals M. The illegal 36 MHz / 500 kHz / 32-bit case sets `clk_error` |
| `filter_response_limits` | Ripple and alias limits on all ten reference and rate pairs |
| `filter_dc_and_overflow` | RTL DC word and full-scale clip |
| `dc_retained_across_sleep` | Settled word survives standby. Clear then reconverges |
| `wake_duty_and_power` | Wake blanking, shutdown clears `valid_iq` and keeps RATE, `DUTY_OFF = 0` stays on, `DUTY_ON = 0` blanks after the first frame |
| `band_relock` | Band write sets relock busy, then clears after the count |
| `slave_fifo_drift` | Host BCLK is not divided from `clk`. Overflow, then underflow, then the flag clear once BCLK has run |

## Dual-use table

Currents and temperatures were not measured. The power column above is a default-activity estimate, not a mode current.

| Requirement | Repeater | LinHT |
|---|---|---|
| Supply rails | Phase 0 decision stands. This RTL draws no rail. | Same. The 5 V buck note stays provisional. Ripple is not tested. |
| RX, TX, standby, shutdown current | not met. Modes exist. The OpenSTA number is not a mode current. | not met. Same RTL. |
| Both 2 m and 70 cm | Band register selects divide-by-8 or divide-by-24 and a digital relock flag. The analog divider is not in this phase. | not met by current LinHT hardware. |
| Duty cycle / thermal | Blanking and the on/off edge cases are in the RTL. Dissipation is not a junction-temperature rise. | Same. |
| Temperature range | not yet evaluated | not yet evaluated |
| IQ interface | Master by default, 16-bit baseline, 32-bit slot available, MSB-justified. Proposed b14/b15 direction change is not yet in the backplane document. | provisional. Rev C wiring has not been read. The 32-bit slot matches the SX1255 mode-B width on paper and does not prove the board uses it. |
| Package at most 5 x 5 mm | not yet evaluated. Cell area above is the digital block only, before placement. | not yet evaluated |
| USB-A security-dongle slot | not applicable | not designed. No part numbers. |

## Still open

1. Approve or change the proposed register map and SPI frame.
2. Approve or change the proposed b14/b15 direction (RFIC master by default).
3. The 36 MHz constraint is not met pre-place. A later pass has to cut the high-fanout input path or the clock period has to move.
4. After this review is approved, the next required work is the matched-mesh EM study from the Phase 0 EM review. Phase 2 does not start before that, and does not start without approval.

Work stops at this gate.
