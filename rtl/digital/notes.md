# Digital back end

Phase 1 RTL for one chain. The analog ADC and DAC are outside this block. The host is the SPI and I2S master.

## Registers

SPI mode 0, 16 bits per CS assertion. Bit 15 is write when 1. Bits 14:8 are the address. Bits 7:0 are the data. MISO returns the current byte during the data half, and a write commits when CS rises.

| Addr | Name | Reset | Meaning |
|---|---|---|---|
| 0x00 | CTRL | 0x00 | [1:0] mode: 00 shutdown, 01 standby, 10 RX, 11 TX. [2] RX duty-cycle enable. [3] I2S slot is 32 bits when 1, else 16. |
| 0x01 | DUTY_ON | 1 | Output frames with IQ present in one RX on-period. |
| 0x02 | DUTY_OFF | 0 | Following frames forced to zero. |
| 0x03 | DECIM | 0 | [1:0] selects boxcar length 1, 2, 4, or 8. |
| 0x04 | DC_SHIFT | 4 | DC-loop shift, clipped to 1..7. |
| 0x05 | GAIN_I | 128 | I gain. 128 means 1.0. |
| 0x06 | GAIN_Q | 128 | Q gain. 128 means 1.0. |
| 0x07 | PHASE | 0 | Signed I-from-Q cross term, same scale as the gains. |
| 0x08 | BLOCK_PD | 0 | [0] decimator, [1] DC loop, [2] IQ cal, [3] I2S. A set bit powers that block down. Filters bypass. I2S dout stays 0. |
| 0x09 | WAKE | 0 | Output frames to wait after entering RX or TX before `valid_iq` rises. |
| 0x0A | STATUS | — | Read only. [1:0] mode, [2] blank, [3] valid_iq. |

## I2S

MSB-justified. lrclk 0 is I (left) and lrclk 1 is Q (right). The bclk rise on which lrclk changes carries the MSB. A 32-bit slot carries the 16-bit sample in the upper half and zeros in the lower half. Sample rate follows the host. The repeater baseline is 16-bit slots. The 32-bit slot is the LinHT SX1255 mode-B width.

## Power

Shutdown and standby keep the SPI alive and force IQ to zero. RX and TX wait `WAKE` output frames, then raise `valid_iq`. That wait is the wake-up-to-valid-IQ figure, in frames. Duty-cycled RX then alternates `DUTY_ON` and `DUTY_OFF` frames. No supply current is computed here.

## Tank Q

This RTL does not use the provisional tank Q.
