# Digital back end

Phase 1 RTL for one chain. The analog ADC and DAC are outside this block. The register map and the SPI frame are proposed. They are not frozen.

## Clock

The modulator clock is the reference on `clk`: 32 MHz, or 36 MHz when `ref_36` is high. It is not 38.4 MHz. Every sample rate in the rate register divides both references exactly. The ratios, the illegal 36 MHz / 500 kHz / 32-bit-slot case, and the wake times are in `spec/i2s-clocking.md`.

## Decimator

Two order-4 CIC stages, a 3-tap compensation FIR, and a 31-tap half-band that decimates by 2. The half-band input rate is exactly twice the output sample rate. CIC ratios and shifts are in `rate_table.sv`. Integrators wrap in 40 bits. Only the 16-bit result saturates.

Compensation taps, scaled by 2^15: -5006, 32767, -5006.

Half-band taps, same scale: -138, 0, 305, 0, -617, 0, 1128, 0, -1952, 0, 3376, 0, -6450, 0, 20688, 32767, 20688, 0, -6450, 0, 3376, 0, -1952, 0, 1128, 0, -617, 0, 305, 0, -138.

Pass limits checked by `filter_response_limits`: passband ripple at most 0.25 dB from 0 to 0.40 of the sample rate, and alias attenuation at least 45 dB for the first four images. The computed worst case is 0.189 dB and 48.1 dB. A full-scale DC input clips at +32767. It does not wrap negative.

## IQ phase

`yI = (gain_i * xI + phase * xQ) / 128`, `yQ = (gain_q * xQ) / 128`, then saturate. Gain 128 is 1.0. `phase` is a signed byte. One LSB is 1/128 rad, about 0.45 degrees. Two degrees is about 4.5 LSB, so the correction grid is finer than the 2 degree image target. That does not say an uncalibrated mixer meets 2 degrees.

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
| 0x08 | BLOCK_PD | 0 | [0] decimator, [1] DC loop, [2] IQ cal, [3] I2S. A set bit powers that block down. Filters bypass. I2S dout stays 0. |
| 0x09 | WAKE | 0 | Output frames to wait after entering RX or TX before `valid_iq` rises. |
| 0x0A | STATUS | — | Read only. [1:0] mode, [2] blank, [3] valid_iq, [4] FIFO overflow, [5] FIFO underflow, [6] clk_error, [7] relock busy. |
| 0x0B | CHIP_ID | 0x11 | Read only. Writes are ignored. |
| 0x0C | BAND | 0 | [0] = 0 selects divide-by-8 (70 cm). [0] = 1 selects divide-by-24 (2 m). A write starts the digital relock interval. |
| 0x0D | DC_CLEAR | 0 | Write [0] = 1 pulses a one-cycle clear of the DC accumulator. The bit does not stick. |

`BAND` relock is a digital handshake of 64 reference clocks, about 2.00 us at 32 MHz and 1.78 us at 36 MHz. It is not an analog PLL lock. The analog lock budget remains under 1 ms and is not claimed here.

## I2S

MSB-justified. LRCLK 0 is I (left) and LRCLK 1 is Q (right). Data changes when BCLK rises. The host samples on the fall. A 32-bit slot carries the 16-bit sample in the upper half and zeros in the lower half.

The RFIC is the master unless `CTRL[4]` is set. Clocking, the proposed b14/b15 direction change, and the CDC are in `spec/i2s-clocking.md` and `cdc.md`.

## Power

Shutdown and standby keep SPI alive and force IQ to zero. Configuration bits are kept. RX and TX wait `WAKE` output frames, then raise `valid_iq`. That wait is the wake-up-to-valid-IQ figure. Times are in `spec/i2s-clocking.md`. Duty-cycled RX then alternates `DUTY_ON` and `DUTY_OFF` frames.

## Tank Q

This RTL does not use the provisional tank Q.
