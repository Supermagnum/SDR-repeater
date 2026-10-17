# I2S clocking (proposed)

This note is a proposed change to the repeater backplane in `docs/RF-modules.md` revision 0.3. That file is not edited here.

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
