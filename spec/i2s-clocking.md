# I2S clocking (proposed)

This note is a proposed change to the repeater backplane in `docs/RF-modules.md` revision 0.3. That file is not edited here. The master-mode default and the b14/b15 direction change are approved as a proposal. They are not a change to the board document.

## Default: the RFIC is the I2S master

`BCLK` and `LRCLK` are derived from the RFIC reference. The host SAI is the slave. Reset state is master mode.

Proposed direction change on J_BACKPLANE:

| Pin | Signal | r0.3 direction | Proposed direction |
|---|---|---|---|
| b14 | I2S_BCLK | In, from K3 SAI | Out, from the RFIC, when the RFIC is master |
| b15 | I2S_LRCLK | In, from K3 SAI | Out, from the RFIC, when the RFIC is master |
| c9 | I2S_DOUT | Out | Out (unchanged) |
| c10 | I2S_DIN | In | In (unchanged) |

Slave mode remains available (`CTRL[4] = 1`). In that mode b14 and b15 would be inputs again, and the words cross an asynchronous FIFO. Overflow and underflow are sticky status bits. A board that wires the host as master has to strap slave mode before the clocks are used. The default strap is master.

LinHT Rev C wiring has not been read from the board files. Which mode that host needs stays provisional. See the Phase 1 review.

## Bit cells

Every bit cell is an even number of reference clocks, so BCLK is high for half the cell and low for half the cell. The cell length is 2 clocks at 32 MHz (BCLK = 16 MHz) and 4 clocks at 36 MHz (BCLK = 9 MHz). The slot width is the widest integer from 16 to 32 such that two slots fit in the frame. The 16-bit sample is MSB-justified. Extra slot bits are zero.

The old case that forwarded the 32 MHz reference as BCLK (32 MHz, 500 kHz, 32-bit slots, one clock per bit) is not generated.

| Reference | Rate | M | Cell | Slot | BCLK | High = low | S11 | S12 | <= 16 MHz |
|---|---|---|---|---|---|---|---|---|---|
| 32 MHz | 25 kHz | 1280 | 2 | 32 | 16 MHz | 31.25 ns | yes (62.5 ns) | yes (50 percent) | yes |
| 32 MHz | 50 kHz | 640 | 2 | 32 | 16 MHz | 31.25 ns | yes | yes | yes |
| 32 MHz | 100 kHz | 320 | 2 | 32 | 16 MHz | 31.25 ns | yes | yes | yes |
| 32 MHz | 200 kHz | 160 | 2 | 32 | 16 MHz | 31.25 ns | yes | yes | yes |
| 32 MHz | 500 kHz | 64 | 2 | 16 | 16 MHz | 31.25 ns | yes | yes | yes |
| 36 MHz | 25 kHz | 1440 | 4 | 32 | 9 MHz | 55.556 ns | yes (111.1 ns) | yes (50 percent) | yes |
| 36 MHz | 50 kHz | 720 | 4 | 32 | 9 MHz | 55.556 ns | yes | yes | yes |
| 36 MHz | 100 kHz | 360 | 4 | 32 | 9 MHz | 55.556 ns | yes | yes | yes |
| 36 MHz | 200 kHz | 180 | 4 | 22 | 9 MHz | 55.556 ns | yes | yes | yes |
| 36 MHz | 500 kHz | 72 | - | - | - | - | - | - | flagged |

36 MHz at 500 kHz has a 72-clock frame. A 16-bit slot at a 4-clock cell needs 128 clocks. A 2-clock cell would make BCLK 18 MHz, which meets S11 (55.6 ns) and S12 (50 percent) and misses the 16 MHz repeater cap. The master sets `clk_error` and holds BCLK and LRCLK low. There is no PLL in this block.

`CTRL[3]` used to select a 32-bit slot. It is reserved and reads as 0. The register map is not frozen.

## Host slave timing

i.MX 93, industrial datasheet Rev. 3, 12/2023, Table 48, "Slave mode SAI timing (25 MHz)":

- S11, SAI_BCLK cycle time, minimum 40 ns. The published slave table stops at 25 MHz.
- S12, SAI_BCLK pulse width high and low, 40 to 60 percent of the BCLK period.
- S13 / S14, frame-sync setup / hold, 3 ns / 2 ns.
- S17 / S18, RXD setup / hold, 3 ns / 2 ns.

The 50 MHz table in that datasheet is master mode. It is not used as the slave limit here.

32 MHz, every rate in the table above, meets S11 (62.5 ns) and S12 (50 percent).

36 MHz, every rate except 500 kHz, meets S11 (111.1 ns) and S12 (50 percent). 500 kHz is the flagged row.

SpacemiT Key Stone K3, public datasheet: the audio block is listed as standard I2S, fixed 48 kHz, 16-bit, stereo, with sysclk of 64/128/256 times fs. That datasheet does not publish a slave BCLK minimum high time or low time. No K3 pulse-width limit is claimed here. The 48 kHz feature line does not describe this IQ rate.

## Exact sample rates

The modulator clock is the reference. It is not 38.4 MHz. Every output rate below divides both 32 MHz and 36 MHz with no remainder. The frame length M is `reference / sample_rate` in reference clocks.

| Sample rate | 32 MHz, M | 36 MHz, M |
|---|---|---|
| 25 kHz | 1280 | 1440 |
| 50 kHz | 640 | 720 |
| 100 kHz | 320 | 360 |
| 200 kHz | 160 | 180 |
| 500 kHz | 64 | 72 |

`LRCLK` period is M reference clocks, so the sample rate is exact. The 200 kHz / 36 MHz frame has 4 idle clocks after the two 22-bit slots (176 clocks). Those clocks hold BCLK low. They do not change the frame length.

A pair that cannot meet both the even-cell rule and the 16 MHz cap is 36 MHz at 500 kHz. The master sets `clk_error` and holds the clocks low. There is no PLL in this block.

## Wake-up to valid IQ

`WAKE` is a count of output frames. Because the sample rate is exact, the time does not depend on which reference is fitted.

| Sample rate | Time of one frame | Time of N wake frames |
|---|---|---|
| 25 kHz | 40 us | N * 40 us |
| 50 kHz | 20 us | N * 20 us |
| 100 kHz | 10 us | N * 10 us |
| 200 kHz | 5 us | N * 5 us |
| 500 kHz | 2 us | N * 2 us |

With the DC state kept across RX sleep, the first valid frame after wake is already the settled word. No extra frames are added. `WAKE` itself is still spent blanked, so the time above is the programmed wait, the same on both references.

DC removal moved to the host on 2026-10-18 (area decision (a)). The chip no longer has `DC_CLEAR` or `DC_SHIFT`; its output word is the half-band (or decimator) output.
