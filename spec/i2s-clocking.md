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

## Recommendation for the repeater backplane

Use 16-bit slots at 500 kHz. That keeps BCLK at or under 16 MHz on both references.

| Reference | Slots | M | B | Cell lengths | BCLK high / low |
|---|---|---|---|---|---|
| 32 MHz | 16-bit | 64 | 32 | every cell is 2 clocks | 31.25 ns / 31.25 ns (50 percent), period 62.5 ns, BCLK = 16 MHz |
| 36 MHz | 16-bit | 72 | 32 | 24 cells of 2 clocks, 8 cells of 3 | 2-clock cell: 27.778 ns / 27.778 ns. 3-clock cell: high 55.556 ns, low 27.778 ns (67 / 33 percent) |

32-bit slots at 500 kHz on a 32 MHz reference forward the reference as BCLK (32 MHz). That is above 16 MHz, so it is not the repeater-backplane choice. It remains a legal mode. 36 MHz with 32-bit slots at 500 kHz stays illegal.

## Host slave timing

i.MX 93, industrial datasheet Rev. 3, 12/2023, Table 48, "Slave mode SAI timing (25 MHz)":

- S11, SAI_BCLK cycle time, minimum 40 ns. The published slave table stops at 25 MHz.
- S12, SAI_BCLK pulse width high and low, 40 to 60 percent of the BCLK period.
- S13 / S14, frame-sync setup / hold, 3 ns / 2 ns.
- S17 / S18, RXD setup / hold, 3 ns / 2 ns.

The 50 MHz table in that datasheet is master mode. It is not used as the slave limit here.

32 MHz, 16-bit, 500 kHz meets S11 (62.5 ns > 40 ns) and S12 (50 percent).

36 MHz, 16-bit, 500 kHz: the 2-clock cells are 55.556 ns and 50 percent, which meets S11 and S12. The 3-clock cells are 83.333 ns, so S11 is met, but the high/low split is 67 / 33 percent of that cell. S12 is 40 to 60 percent of the period. Those cells do not meet S12. An integer split of three reference clocks cannot land inside 40 to 60 percent. The absolute low pulse is 27.778 ns, which is longer than 40 percent of the 40 ns minimum cycle (16 ns), but the datasheet states the limit as a fraction of the period.

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

`LRCLK` toggles once per frame, so its rate is the sample rate exactly.

A 16-bit slot uses 32 bit cells in the frame. A 32-bit slot uses 64. Cell length is `floor(M / B)` or one more, spread across the frame. The sample rate stays exact when the cells differ by one reference clock. That difference is bit-period jitter, not a sample-rate error.

A symmetric BCLK needs at least two reference clocks per bit. One case is shorter than that and is still legal, because every cell is exactly one reference clock and BCLK is the reference itself: 32 MHz, 500 kHz, 32-bit slots (M = 64, B = 64).

One case is illegal. 36 MHz, 500 kHz, 32-bit slots has M = 72 and B = 64, so some cells would be a single reference clock and the others would be two. A 32 MHz bit clock is not an integer divide of 36 MHz. The master sets `clk_error` and holds the clocks low. There is no PLL in this block to make that clock.

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

Clearing the DC accumulator (`DC_CLEAR`) drops that state. With `DC_SHIFT = 1` and a 200 LSB input offset, the next new word is 100 LSB and the error is under 20 LSB on the fourth new word. At 25 kHz those four words are 160 us. At 500 kHz they are 8 us. The same count applies on both references.
