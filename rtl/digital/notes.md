# Digital back end

Phase 1 RTL for one chain. The analog ADC and DAC are outside this block. The SPI frame is approved: mode 0, 16 bits, bit 15 is write, bits 14:8 are the address, bits 7:0 are the data. The register map is not frozen. `CTRL[3]` is reserved.

## Clock

The modulator clock is the reference on `clk`: 32 MHz, or 36 MHz when `ref_36` is high. It is not 38.4 MHz. The period used for timing signoff is 27.778 ns. Every sample rate in the rate register divides both references exactly. The ratios, the illegal 36 MHz / 500 kHz / 32-bit-slot case, the 16-bit / 500 kHz recommendation, and the wake times are in `spec/i2s-clocking.md`.

## Decimator

Two order-4 CIC stages, then one time-multiplexed multiplier for the 3-tap compensation FIR and the 31-tap half-band. The half-band uses symmetric coefficients, so each pair of taps is one multiply. The same multiplier serves I and Q. The tightest budget is 32 reference clocks per half-band input (32 MHz, 500 kHz). The schedule finishes in 27 clocks.

Each CIC integrator has its own registered enable, so `adc_valid` is not a single combo enable across the adder chain. The comb runs one stage per clock on the decimated beat. Integrators wrap in 40 bits. Only the final 16-bit result saturates.

Compensation taps, scaled by 2^15: -5006, 32767, -5006.

Half-band taps, same scale: -138, 0, 305, 0, -617, 0, 1128, 0, -1952, 0, 3376, 0, -6450, 0, 20688, 32767, 20688, 0, -6450, 0, 3376, 0, -1952, 0, 1128, 0, -617, 0, 305, 0, -138.

The 45 dB alias limit is provisional until the Phase 3 modulator co-design. The coefficient check still requires it. Computed worst case on these taps: 0.189 dB ripple and 48.1 dB alias attenuation. A full-scale DC input clips at +32767 (the normalized result is 32766 or 32767). It does not wrap negative.

## DC gain

A constant +1 bitstream is the DC stimulus. The 8-tap front end sums to 50. `norm` is chosen so the settled word is near code 64 (the integer truncate of a unity-gain Q15 scale is 0 on this small pre-norm value).

| Reference | Rates | Q15 `norm` | Settled code |
|---|---|---|---|
| 32 MHz | 25, 50, 100, 200 kHz | 25267 | 64 |
| 32 MHz | 500 kHz | 31301 | 64 |
| 36 MHz | 25, 50, 100, 200 kHz | 15768 | 63 |
| 36 MHz | 500 kHz | 19600 | 64 |

## IQ phase

DC and IQ correction are not done on the chip since 2026-10-18 (area decision (a), see `decisions.md`). The host applies them to the I2S words. RX: remove the DC estimate `d` (a first-order loop, `d += (x - d) / 2^k`), then `yI = gI*xI + p*xQ`, `yQ = gQ*xQ`. TX: apply the inverse before sending. The removed registers used gain 128 = 1.0 and a phase LSB of 1/128 rad (about 0.45 degrees, finer than the 2 degree image target); that grid is a sensible host-side default.

## TX path

I2S input at the sample rate, already DC- and IQ-corrected by the host (since 2026-10-18). A half-band interpolates by 2 using the RX coefficients as a polyphase pair (eight symmetric products for the even output, the center tap for the odd output). An order-2 CIC interpolator carries that stream up to the reference. A 2nd-order 1-bit sigma-delta modulator, with feedback into both integrators, drives `dac_bit_i` and `dac_bit_q`.

`tx_image_and_noise` drives a 0.1*fs tone at 500 kHz / 32 MHz and requires at least 40 dB of image rejection at `fs - f`. The 1 to 8 MHz median floor, 20 dB below the tone, is a provisional check of this modulator model. Phase 4 has to derive that limit from the emission mask, including the analogue reconstruction filter and the modulator order. The expected mask is at least 60 to 70 dB below the carrier near the carrier. This run measured 59.6 dB image rejection and a floor 25.7 dB below the tone (tone 53.5 dB, image -6.1 dB, floor 27.8 dB).

## DC loop across sleep

The accumulator clears only on reset or on `DC_CLEAR`. RX sleep stops new samples. It does not clear the accumulator. The decimator enable follows the block power-down bit, not RX enable, so CIC state is also kept when the ADC valid stops. With state kept, the first valid word after wake is already settled: zero extra frames. After a clear, with shift 1 and a 200 LSB offset, the error is under 20 LSB on the fourth new word.

## Registers

SPI mode 0, 16 bits per CS assertion. Bit 15 is write when 1. Bits 14:8 are the address. Bits 7:0 are the data. MISO returns the byte captured at the 8th SCLK edge. The write commits on the 16th rising SCLK while CS is still low. The register file is clocked by SCLK, so the reference may be stopped. `clk_req` is high when the mode is not shutdown. A write that selects standby, RX, or TX raises it with the reference stopped.

| Addr | Name | Reset | Meaning |
|---|---|---|---|
| 0x00 | CTRL | 0x00 | [1:0] mode: 00 shutdown, 01 standby, 10 RX, 11 TX. [2] RX duty-cycle enable. [3] reserved, forced to 0. [4] I2S slave when 1. Reset is master. [7] write-1 clears FIFO flags and does not stick. [6:5] reserved. |
| 0x01 | DUTY_ON | 1 | Output frames with IQ present in one RX on-period. Zero with a non-zero DUTY_OFF blanks after the first frame. |
| 0x02 | DUTY_OFF | 0 | Following frames forced to zero. Zero means the on-period does not end. |
| 0x03 | RATE | 4 | [2:0] sample rate: 0 = 25, 1 = 50, 2 = 100, 3 = 200, 4 = 500 kHz. |
| 0x04 | — | 0 | Reserved. Was `DC_SHIFT` until 2026-10-18; DC and IQ correction are done by the host. Reads 0, writes ignored. |
| 0x05 | — | 0 | Reserved. Was `GAIN_I` until 2026-10-18; DC and IQ correction are done by the host. Reads 0, writes ignored. |
| 0x06 | — | 0 | Reserved. Was `GAIN_Q` until 2026-10-18; DC and IQ correction are done by the host. Reads 0, writes ignored. |
| 0x07 | — | 0 | Reserved. Was `PHASE` until 2026-10-18; DC and IQ correction are done by the host. Reads 0, writes ignored. |
| 0x08 | BLOCK_PD | 0 | [0] decimator, [1] DC loop, [2] IQ cal, [3] I2S, [4] TX chain. A set bit powers that block down. Filters bypass. I2S dout stays 0. |
| 0x09 | WAKE | 0 | Output frames to wait after entering RX or TX before `valid_iq` rises. |
| 0x0A | STATUS | — | Read only. [1:0] mode, [2] blank, [3] valid_iq, [4] FIFO overflow, [5] FIFO underflow, [6] clk_error, [7] relock busy. |
| 0x0B | CHIP_ID | 0x12 | Read only. Writes are ignored. 0x11 before the calibration registers were removed (2026-10-18). |
| 0x0C | BAND | 0 | [0] = 0 selects divide-by-8 (70 cm). [0] = 1 selects divide-by-24 (2 m). A write starts the digital relock interval. |
| 0x0D | — | 0 | Reserved. Was `DC_CLEAR` until 2026-10-18; DC and IQ correction are done by the host. Reads 0, writes ignored. |
| 0x0E | — | 0 | Reserved. Was `TX_DC_I` until 2026-10-18; DC and IQ correction are done by the host. Reads 0, writes ignored. |
| 0x0F | — | 0 | Reserved. Was `TX_DC_Q` until 2026-10-18; DC and IQ correction are done by the host. Reads 0, writes ignored. |
| 0x10 | — | 0 | Reserved. Was `TX_GAIN_I` until 2026-10-18; DC and IQ correction are done by the host. Reads 0, writes ignored. |
| 0x11 | — | 0 | Reserved. Was `TX_GAIN_Q` until 2026-10-18; DC and IQ correction are done by the host. Reads 0, writes ignored. |
| 0x12 | — | 0 | Reserved. Was `TX_PHASE` until 2026-10-18; DC and IQ correction are done by the host. Reads 0, writes ignored. |
| 0x13 | CLK_GATE | 0x1F | Clock allow. [0] CIC, [1] FIR (shares the RX clock with the CIC, so either bit stops that clock), [2] DC and IQ data enable, [3] I2S, [4] TX. A 0 stops that block even in RX or TX. SPI is not in this mask. It stays clocked in every mode, including shutdown. |

`BAND` relock is a digital handshake of 64 reference clocks, about 2.00 us at 32 MHz and 1.78 us at 36 MHz. It is not an analog PLL lock. The analog lock budget remains under 1 ms and is not claimed here.

## I2S

MSB-justified. LRCLK 0 is I (left) and LRCLK 1 is Q (right). Data changes when BCLK rises. The host samples on the fall. The slot width comes from the rate table. The first 16 bits of the slot are the sample. Wider slots send zeros after that. `CTRL[3]` does not select the slot.

The RFIC is the master unless `CTRL[4]` is set. Clocking, the proposed b14/b15 direction change, and the CDC are in `spec/i2s-clocking.md` and `cdc.md`.

## Power

Shutdown stops the reference. SPI stays on SCLK. A write that leaves shutdown raises `clk_req`, which is the wake for the reference. RX and TX wait `WAKE` output frames, then raise `valid_iq`. Times are in `spec/i2s-clocking.md`. Duty-cycled RX blanks with a clock enable on the root RX gate. I2S stays on the run gate so the frame count advances.

Three root gates (run, RX, TX) use the behavioral latch-and-AND. `sg13g2_lgcp_1` and `sg13g2_slgcp_1` stay `dont_use`. Blocks inside a gate use clock enables, not more gated clocks.

## Tank Q

This RTL does not use the provisional tank Q.
