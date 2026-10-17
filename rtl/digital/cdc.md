# Clock-domain crossing

The reference clock is `clk`. It is 32 MHz or 36 MHz, selected by the `ref_36` pin. The decimator, DC loop, IQ calibration, power control, SPI oversampling, and the I2S master all use this clock.

## Master mode

Master mode is the reset default (`CTRL[4] = 0`). `BCLK` and `LRCLK` are outputs. They are divided from `clk`, so the master shifter and the decimator are in the same clock domain. There is no synchronizer on the IQ sample in this mode. `dout` changes on the rising edge of `BCLK`. The host samples on the falling edge.

## Slave mode

Slave mode (`CTRL[4] = 1`) tri-states the clock outputs and takes `bclk_i` and `lrclk_i` from the host. Those clocks are not divided from `clk`. They may be asynchronous and they may drift.

IQ samples cross in `sample_fifo`, depth 8. The write clock is `clk`. The read clock is `bclk_i`. Both pointers are gray-coded and synchronized by two flip-flops. A write into a full FIFO sets `overflow`. A read from an empty FIFO sets `underflow`. Both flags stick. `CTRL[7]` is a write-1 clear. The clear request is held until the BCLK domain has seen it, so a one-cycle pulse on the reference is not lost when BCLK is slow or stopped. After BCLK starts again the flags drop. A read that still finds the FIFO empty sets `underflow` again.

The slave shifter prefetches one word at the start of Left and transmits it on the next frame. The first frame after enable is zeros. That is one frame of latency, on top of the FIFO.

The TX capture path in slave mode does not pulse `dac_valid`. TX IQ from a slave host is captured in the BCLK domain and is not yet timed into the reference domain. Master mode does pulse `dac_valid` at the end of a frame.
