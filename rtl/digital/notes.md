# Digital back end

Phase 1 RTL for one chain. The analog ADC and DAC are outside this block. The SPI frame is approved: mode 0, 16 bits, bit 15 is write, bits 14:8 are the address, bits 7:0 are the data. The register map below is frozen at this gate.

## Clock

The modulator clock is the reference on `clk`: 32 MHz, or 36 MHz when `ref_36` is high. It is not 38.4 MHz. The period used for timing signoff is 27.778 ns. Every sample rate in the rate register divides both references exactly. The ratios, the illegal 36 MHz / 500 kHz / 32-bit-slot case, the 16-bit / 500 kHz recommendation, and the wake times are in `spec/i2s-clocking.md`.

## Decimator

Two order-4 CIC stages, then one time-multiplexed multiplier for the 3-tap compensation FIR and the 31-tap half-band. The half-band uses symmetric coefficients, so each pair of taps is one multiply. The same multiplier serves I and Q. The tightest budget is 32 reference clocks per half-band input (32 MHz, 500 kHz). The schedule finishes in 27 clocks.

Each CIC integrator has its own registered enable, so `adc_valid` is not a single combo enable across the adder chain. The comb runs one stage per clock on the decimated beat. Integrators wrap in 40 bits. Only the final 16-bit result saturates.

Compensation taps, scaled by 2^15: -5006, 32767, -5006.

Half-band taps, same scale: -138, 0, 305, 0, -617, 0, 1128, 0, -1952, 0, 3376, 0, -6450, 0, 20688, 32767, 20688, 0, -6450, 0, 3376, 0, -1952, 0, 1128, 0, -617, 0, 305, 0, -138.

The 45 dB alias limit is provisional until the Phase 3 modulator co-design. The coefficient check still requires it. Computed worst case on these taps: 0.189 dB ripple and 48.1 dB alias attenuation. A full-scale DC input clips at +32767 (the normalized result is 32766 or 32767). It does not wrap negative.

## DC gain

Raw DC gain, before the per-rate normalize, is the product of the two CIC stage gains (`R^4 / 2^shift`, each in [1, 2)) and the FIR sums. It is not the same at every rate:

| Reference | Rates | Raw DC gain | Q15 `norm` |
|---|---|---|---|
| 32 MHz | 25, 50, 100, 200 kHz | 1.6931 | 19354 |
| 32 MHz | 500 kHz | 1.3870 | 23626 |
| 36 MHz | 25, 50, 100, 200 kHz | 2.7120 | 12083 |
| 36 MHz | 500 kHz | 2.2217 | 14749 |

`norm` is applied after the half-band (`>>> 15`). Cocotb checks every pair with a constant 1000 and requires the settled word within 4 LSB of 1000.

## IQ phase

`yI = (gain_i * xI + phase * xQ) / 128`, `yQ = (gain_q * xQ) / 128`, then saturate. Gain 128 is 1.0. `PHASE` is a signed 8-bit register. One LSB is 1/128 rad, about 0.447 degrees. The stored range is -128 to +127, so the largest coefficient is -128/128 = -1 rad (about -57.3 degrees) and +127/128 rad (about +56.8 degrees). It is a Q-into-I cross term, not a full rotation matrix. Two degrees is about 4.5 LSB, so the grid is finer than the 2 degree image target. That does not say an uncalibrated mixer meets 2 degrees. The TX path uses the same width in `TX_PHASE`.

## TX path

I2S input at the sample rate, DC subtract (`TX_DC_*`, signed 8-bit, units of sample LSBs, range -128 to +127), then the same IQ cross term. A half-band interpolates by 2 using the RX coefficients as a polyphase pair (eight symmetric products for the even output, the center tap for the odd output). An order-2 CIC interpolator carries that stream up to the reference. A 2nd-order 1-bit sigma-delta modulator, with feedback into both integrators, drives `dac_bit_i` and `dac_bit_q`.

`tx_image_and_noise` drives a 0.1*fs tone at 500 kHz / 32 MHz and requires at least 40 dB of image rejection at `fs - f`, and an out-of-band median from 1 to 8 MHz at least 20 dB below the tone. The run on this net measured 61.9 dB rejection and a floor 25.8 dB below the tone.

## DC loop across sleep

The accumulator clears only on reset or on `DC_CLEAR`. RX sleep stops new samples. It does not clear the accumulator. The decimator enable follows the block power-down bit, not RX enable, so CIC state is also kept when the ADC valid stops. With state kept, the first valid word after wake is already settled: zero extra frames. After a clear, with shift 1 and a 200 LSB offset, the error is under 20 LSB on the fourth new word.

## Registers

SPI mode 0, 16 bits per CS assertion. Bit 15 is write when 1. Bits 14:8 are the address. Bits 7:0 are the data. MISO returns the current byte during the data half, and a write commits when CS rises. SCLK is oversampled by `clk` and must be slower than `clk/4`.

| Addr | Name | Reset | Meaning |
|---|---|---|---|
| 0x00 | CTRL | 0x00 | [1:0] mode: 00 shutdown, 01 standby, 10 RX, 11 TX. [2] RX duty-cycle enable. [3] 32-bit I2S slot when 1, else 16. [4] I2S slave when 1. Reset is master. [7] write-1 clears FIFO flags and does not stick. [6:5] reserved. |
| 0x01 | DUTY_ON | 1 | Output frames with IQ present in one RX on-period. Zero with a non-zero DUTY_OFF blanks after the first frame. |
| 0x02 | DUTY_OFF | 0 | Following frames forced to zero. Zero means the on-period does not end. |
| 0x03 | RATE | 4 | [2:0] sample rate: 0 = 25, 1 = 50, 2 = 100, 3 = 200, 4 = 500 kHz. |
| 0x04 | DC_SHIFT | 4 | DC-loop shift, clipped to 1..7. |
| 0x05 | GAIN_I | 128 | I gain. 128 means 1.0. |
| 0x06 | GAIN_Q | 128 | Q gain. 128 means 1.0. |
| 0x07 | PHASE | 0 | Signed I-from-Q cross term. One LSB is 1/128 rad. |
| 0x08 | BLOCK_PD | 0 | [0] decimator, [1] DC loop, [2] IQ cal, [3] I2S, [4] TX chain. A set bit powers that block down. Filters bypass. I2S dout stays 0. |
| 0x09 | WAKE | 0 | Output frames to wait after entering RX or TX before `valid_iq` rises. |
| 0x0A | STATUS | — | Read only. [1:0] mode, [2] blank, [3] valid_iq, [4] FIFO overflow, [5] FIFO underflow, [6] clk_error, [7] relock busy. |
| 0x0B | CHIP_ID | 0x11 | Read only. Writes are ignored. |
| 0x0C | BAND | 0 | [0] = 0 selects divide-by-8 (70 cm). [0] = 1 selects divide-by-24 (2 m). A write starts the digital relock interval. |
| 0x0D | DC_CLEAR | 0 | Write [0] = 1 pulses a one-cycle clear of the DC accumulator. The bit does not stick. |
| 0x0E | TX_DC_I | 0 | Signed 8-bit TX I DC offset, in sample LSBs. Range -128 to +127. |
| 0x0F | TX_DC_Q | 0 | Signed 8-bit TX Q DC offset, same units. |
| 0x10 | TX_GAIN_I | 128 | TX I gain. 128 means 1.0. |
| 0x11 | TX_GAIN_Q | 128 | TX Q gain. 128 means 1.0. |
| 0x12 | TX_PHASE | 0 | Signed 8-bit TX Q-into-I cross term. One LSB is 1/128 rad. Range -128 to +127. |
| 0x13 | CLK_GATE | 0x1F | Clock allow. [0] CIC, [1] FIR (shares the RX clock with the CIC, so either bit stops that clock), [2] DC and IQ data enable, [3] I2S, [4] TX. A 0 stops that block even in RX or TX. SPI is not in this mask. It stays clocked in every mode, including shutdown. |

`BAND` relock is a digital handshake of 64 reference clocks, about 2.00 us at 32 MHz and 1.78 us at 36 MHz. It is not an analog PLL lock. The analog lock budget remains under 1 ms and is not claimed here.

## I2S

MSB-justified. LRCLK 0 is I (left) and LRCLK 1 is Q (right). Data changes when BCLK rises. The host samples on the fall. A 32-bit slot carries the 16-bit sample in the upper half and zeros in the lower half.

The RFIC is the master unless `CTRL[4]` is set. Clocking, the proposed b14/b15 direction change, and the CDC are in `spec/i2s-clocking.md` and `cdc.md`.

## Power

Shutdown and standby keep SPI alive and force IQ to zero. Configuration bits are kept. RX and TX wait `WAKE` output frames, then raise `valid_iq`. That wait is the wake-up-to-valid-IQ figure. Times are in `spec/i2s-clocking.md`. Duty-cycled RX then alternates `DUTY_ON` and `DUTY_OFF` frames. During a duty-off frame the RX clock gate stops the CIC and the FIR. Bypass (`BLOCK_PD[0]`) keeps that clock running. I2S keeps running so the frame count advances.

Clock gates are the latch-and-AND structure of `sg13g2_lgcp_1` (GATE high, latch open while CLK is low). The library cell and `sg13g2_slgcp_1` are marked `dont_use` and are listed in the PDK `synth_exclude.cells` and `pnr_exclude.cells`, so this flow cannot place the cell. `clk_gate.sv` is the same function, mapped to a latch and an AND.

## Tank Q

This RTL does not use the provisional tank Q.
