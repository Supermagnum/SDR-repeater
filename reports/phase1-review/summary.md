# Phase 1 review

Date: 2026-10-17. This is a resubmission. It is not an approval.

Scope: digital back end, receive and transmit, for one chain. No analog schematic, no fabrication. The matched-mesh inductor study has not been started. Phase 2 has not been started.

The SPI frame is approved. The register map is frozen at this gate. Addresses `0x00` through `0x13` are listed below. The next free address is `0x14`.

Manifest snapshot: `tools/tool-manifest.lock` on this branch. PDK pin `a49358cc`. Container `hpretl/iic-osic-tools:2026.10`. cocotb 2.1.0. Simulators: Icarus Verilog 14.0 and Verilator 5.052. Synthesis and placement: LibreLane classic flow, Yosys 0.70, OpenROAD, OpenSTA, through placement, clock-tree synthesis, and the post-CTS timing resizer. Standard cells: `sg13g2_stdcell`. The clock period stays 27.778 ns.

## Register map

SPI mode 0, 16 bits. Bit 15 is write. Bits 14:8 are the address. Bits 7:0 are the data. MISO returns the current byte during the data half. A write commits when CS rises. SCLK is oversampled by `clk` and stays slower than `clk/4`.

| Addr | Name | Reset | Meaning |
|---|---|---|---|
| 0x00 | CTRL | 0x00 | [1:0] mode: 00 shutdown, 01 standby, 10 RX, 11 TX. [2] duty-cycle enable. [3] 32-bit slots. [4] I2S slave. [7] write-1 clears FIFO flags and does not stick. |
| 0x01 | DUTY_ON | 1 | RX on frames. |
| 0x02 | DUTY_OFF | 0 | Following blank frames. Zero means the on period does not end. |
| 0x03 | RATE | 4 | 0 = 25, 1 = 50, 2 = 100, 3 = 200, 4 = 500 kHz. |
| 0x04 | DC_SHIFT | 4 | DC-loop shift, clipped to 1..7. **Removed 2026-10-18 (host-side calibration): reserved, reads 0.** |
| 0x05 | GAIN_I | 128 | 128 means 1.0. **Removed 2026-10-18 (host-side calibration): reserved, reads 0.** |
| 0x06 | GAIN_Q | 128 | 128 means 1.0. **Removed 2026-10-18 (host-side calibration): reserved, reads 0.** |
| 0x07 | PHASE | 0 | Signed 8-bit Q-into-I cross term. One LSB is 1/128 rad. **Removed 2026-10-18 (host-side calibration): reserved, reads 0.** |
| 0x08 | BLOCK_PD | 0 | [0] decimator, [1] DC, [2] IQ, [3] I2S, [4] TX. A set bit powers that block down. |
| 0x09 | WAKE | 0 | Output frames before `valid_iq`. |
| 0x0A | STATUS | — | Read only. Mode, blank, valid, FIFO flags, `clk_error`, relock busy. |
| 0x0B | CHIP_ID | 0x11 | Read only. Writes are ignored. **0x12 since 2026-10-18.** |
| 0x0C | BAND | 0 | 0 selects divide-by-8. 1 selects divide-by-24. A write starts the digital relock count. |
| 0x0D | DC_CLEAR | 0 | Write bit 0 pulses a one-cycle clear. The bit does not stick. **Removed 2026-10-18 (host-side calibration): reserved, reads 0.** |
| 0x0E | TX_DC_I | 0 | Signed 8-bit TX I offset, sample LSBs, -128..+127. **Removed 2026-10-18 (host-side calibration): reserved, reads 0.** |
| 0x0F | TX_DC_Q | 0 | Signed 8-bit TX Q offset, same units. **Removed 2026-10-18 (host-side calibration): reserved, reads 0.** |
| 0x10 | TX_GAIN_I | 128 | TX I gain. 128 means 1.0. **Removed 2026-10-18 (host-side calibration): reserved, reads 0.** |
| 0x11 | TX_GAIN_Q | 128 | TX Q gain. 128 means 1.0. **Removed 2026-10-18 (host-side calibration): reserved, reads 0.** |
| 0x12 | TX_PHASE | 0 | Signed 8-bit, same scale as `PHASE`. **Removed 2026-10-18 (host-side calibration): reserved, reads 0.** |
| 0x13 | CLK_GATE | 0x1F | Allow bits. [0] CIC, [1] FIR, [2] DC and IQ data enable, [3] I2S, [4] TX. A 0 stops that block. SPI is outside this mask and stays clocked in every mode. |

`BAND` relock is 64 reference clocks, about 2.00 µs at 32 MHz and 1.78 µs at 36 MHz. That is a digital handshake. The analog lock budget remains under 1 ms and is not claimed here.

## I2S clocking

The RFIC is the I2S master by default. The b14/b15 direction change is approved as a proposal. The note is `spec/i2s-clocking.md`. `docs/RF-modules.md` revision 0.3 was not edited.

Recommendation for the repeater backplane: 16-bit slots at 500 kHz, so BCLK stays at or under 16 MHz.

At 32 MHz, 16-bit, 500 kHz, every bit cell is two reference clocks. BCLK is 16 MHz with a 50 percent duty. High and low are each 31.25 ns. The i.MX93 slave table (datasheet Rev. 3, Table 48, 25 MHz) requires a BCLK period of at least 40 ns (S11) and a high and low pulse of 40 to 60 percent of that period (S12). This case meets both.

At 36 MHz, 16-bit, 500 kHz, 24 cells are two reference clocks and 8 cells are three. A two-clock cell is 55.556 ns at 50 percent and meets S11 and S12. A three-clock cell is 83.333 ns with a 67/33 split: high 55.556 ns, low 27.778 ns. The period meets S11. The 33 percent low pulse misses S12. An integer split of three reference clocks cannot land inside 40 to 60 percent. The K3 audio section publishes a fixed 48 kHz I2S rate and does not publish a slave BCLK minimum high or low time, so no K3 pulse-width limit is stated here.

The 32 MHz, 32-bit, 500 kHz case still forwards BCLK as the 32 MHz reference. That exceeds the 16 MHz recommendation and the i.MX93 slave table. The 36 MHz, 32-bit, 500 kHz case still sets `clk_error`. There is no PLL in this block.

## Filter

Two order-4 CIC stages, a 3-tap compensation FIR, and a 31-tap half-band, sharing one multiplier. Symmetric coefficients. The `adc_valid` enable is registered and replicated per integrator. Each integrator is one add per clock.

Raw DC gain is not 1, and it is not the same at every rate. A Q15 `norm` after the half-band brings a constant 1000 to within 4 LSB of 1000 on all ten pairs.

| Reference | Rates | Raw DC gain | Q15 norm |
|---|---|---|---|
| 32 MHz | 25, 50, 100, 200 kHz | 1.6931 | 19354 |
| 32 MHz | 500 kHz | 1.3870 | 23626 |
| 36 MHz | 25, 50, 100, 200 kHz | 2.7120 | 12083 |
| 36 MHz | 500 kHz | 2.2217 | 14749 |

Passband ripple, 0 to 0.40 of the sample rate, worst case 0.189 dB. The test limit is 0.25 dB. Alias attenuation, images 1 through 4, worst case 48.1 dB. The test still requires 45 dB. That 45 dB limit is provisional until the Phase 3 modulator co-design.

## IQ phase

**Historical: these registers were removed on 2026-10-18 and the host applies this correction.** `PHASE` and `TX_PHASE` are signed 8-bit. One LSB is 1/128 rad, about 0.447 degrees. The stored range is -128 to +127, so the largest coefficient is -1 rad (about -57.3 degrees) and +127/128 rad (about +56.8 degrees). The term is Q into I. Two degrees is about 4.5 LSB. That is the correction grid. It is not a claim that an uncalibrated mixer meets 2 degrees.

## Transmit path

I2S input, signed 8-bit DC subtract, the same IQ cross term, a half-band interpolate-by-2, an order-2 CIC interpolator up to the reference, and a 2nd-order 1-bit sigma-delta modulator with feedback into both integrators. Outputs are `dac_bit_i` and `dac_bit_q`.

`tx_image_and_noise` uses a 0.1*fs tone at 500 kHz and 32 MHz. The test requires at least 40 dB of image rejection at `fs - f`, and an out-of-band median from 1 to 8 MHz at least 20 dB below the tone. The measured result is 61.9 dB rejection and a floor 25.8 dB below the tone.

## Clock gating

`sg13g2_lgcp_1` and `sg13g2_slgcp_1` are in the library and are marked `dont_use`. Both are listed in the PDK `synth_exclude.cells` and `pnr_exclude.cells`, so this flow cannot place them. `clk_gate.sv` is the same latch-and-AND function. Synthesis maps it to `sg13g2_dllrq_1` plus an AND. Three gates: RX datapath, I2S master, and TX. SPI, the power controller, and the I2S slave stay on the free-running clock so the host can program the chip and the duty counter can leave the blank phase.

## Placed area

Target: at most 0.25 mm² for the full digital block. The placed result is above that.

| Item | Area |
|---|---|
| Synthesized cell area | 543062 µm² (0.543 mm²) |
| of which sequential | 239740 µm², 4892 flip-flops and 3 latches |
| Core after floorplan | 984022 µm² (0.984 mm²) |
| Die | 1029300 µm² (1.029 mm²) |
| Instances after the post-CTS hold repair | 701910 µm² (0.702 mm²) inside the same core |

The floorplan utilization target was 55 percent. The cell area itself is already above 0.25 mm², so a tighter floorplan does not meet the target. The clock period was not lengthened.

## Timing

Post-CTS, typical corner 1.20 V 25 °C, from the flow STA on the clock-tree database, before the hold-buffer resizer:

| Check | Result |
|---|---|
| Setup worst slack | +5.860 ns |
| Setup WNS / TNS | 0 / 0 |
| Hold WNS | -0.065 ns |
| Hold TNS | -0.688 ns, 31 paths |

The same post-CTS database, retimed with the slow and fast liberties and placement parasitics:

| Corner | Setup slack | Hold slack |
|---|---|---|
| slow 1.08 V 125 °C | +4.648 ns, TNS 0 | +0.040 ns, TNS 0 |
| fast 1.32 V -40 °C | +6.638 ns, TNS 0 | -0.127 ns, TNS -207.6 ns |

The liberty set has no 85 °C file and no 100 °C file. The corners on disk are -40 °C, 25 °C, and 125 °C. Proposed signoff junction temperature: 100 °C, at the top of the 85–100 °C range. No slack number is reported at 100 °C, because that liberty does not exist. The 125 °C row above is the slow corner that does exist. Setup meets 27.778 ns at 125 °C on this database. Hold at the fast corner does not.

The resizer then inserted 7229 hold buffers (143209 µm²). The flow was stopped at that step, so those buffers are in the area and are not in the slack table above.

## Power

OpenSTA on the synthesized netlist, typical liberty, clock period 27.78 ns. Activity is a VCD from a gate-level cocotb run of each mode (1280 reference clocks after the SPI writes). 116507 pin activities were annotated in each run. This netlist has no clock tree, so the clock-buffer power of the placed design is absent.

| Mode | Total |
|---|---|
| Shutdown | 1.01 mW |
| Standby | 1.01 mW |
| RX | 33.1 mW |
| TX | 10.5 mW |
| RX duty cycle, on 1 frame / off 9 | 7.17 mW |

Leakage is about 6.1 µW in every mode. Shutdown and standby match because the datapath clocks are gated in both and SPI plus the I2S slave stay clocked. The duty-cycled run is higher than one tenth of the RX number because the I2S master stays clocked during the off frames and the VCD includes the SPI programming.

## Verification

Cocotb on the RTL: 12 tests, 12 passed, on both Icarus Verilog 14.0 and Verilator 5.052. Gate-level Icarus on the Yosys netlist plus `sg13g2_stdcell.v`: `spi_reset_and_registers`, `master_frame_lengths`, and `rx_chain_ports` (constant 1000, DC and IQ bypassed, left I2S word within 4 LSB of 1000). Icarus prints `sorry` for specify `ifnone` paths in the cell models. Those simulations still passed.

## Still open

LinHT IQ wiring stays provisional until the Rev C board is read. The 45 dB alias limit stays provisional pending the Phase 3 modulator co-design. The matched-mesh inductor study may run in parallel and has not been started. Phase 2 has not been started and still needs approval. This document is the review gate. It is not an approval.
