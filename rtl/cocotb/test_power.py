import os

import cocotb
from cocotb.triggers import RisingEdge, Timer

from test_backend import spi_xfer


# One mode per run. The clock period matches the 36 MHz reference so a VCD
# from this run can be read by OpenSTA against a 27.778 ns clock.
CYCLES = 1280
_clk_run = True


async def refclk(dut):
    # 27.78 ns is 36.00 MHz within 0.01 percent.
    while _clk_run:
        dut.clk.value = 0
        await Timer(13.89, unit="ns")
        if not _clk_run:
            break
        dut.clk.value = 1
        await Timer(13.89, unit="ns")
    dut.clk.value = 0


async def boot(dut):
    global _clk_run
    _clk_run = True
    cocotb.start_soon(refclk(dut))
    dut.ref_36.value = 1
    dut.sclk.value = 0
    dut.cs_n.value = 1
    dut.mosi.value = 0
    dut.bclk_i.value = 0
    dut.lrclk_i.value = 0
    dut.din.value = 0
    dut.adc_valid.value = 0
    dut.adc_bit_i.value = 0
    dut.adc_bit_q.value = 0
    dut.adc_i.value = 0
    dut.adc_q.value = 0
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


@cocotb.test()
async def power_mode(dut):
    global _clk_run
    mode = os.environ.get("PWR_MODE", "shutdown")
    await boot(dut)
    if mode == "shutdown":
        await spi_xfer(dut, 0x00, 0x00, write=True)
        # Reference stopped. SPI is idle. This is the shutdown case.
        _clk_run = False
        await Timer(CYCLES * 27.78, unit="ns")
        return
    if mode == "standby":
        await spi_xfer(dut, 0x00, 0x01, write=True)
    elif mode == "rx":
        await spi_xfer(dut, 0x03, 4, write=True)
        await spi_xfer(dut, 0x00, 0x02, write=True)
        dut.adc_valid.value = 1
        dut.adc_bit_i.value = 1
        dut.adc_bit_q.value = 1
    elif mode == "tx":
        await spi_xfer(dut, 0x03, 4, write=True)
        await spi_xfer(dut, 0x00, 0x03, write=True)
    elif mode == "duty10":
        await spi_xfer(dut, 0x03, 4, write=True)
        await spi_xfer(dut, 0x01, 1, write=True)
        await spi_xfer(dut, 0x02, 9, write=True)
        await spi_xfer(dut, 0x00, 0x06, write=True)
        dut.adc_valid.value = 1
        dut.adc_bit_i.value = 1
        dut.adc_bit_q.value = 1
    else:
        raise AssertionError(mode)
    toggle = 0
    for _ in range(CYCLES):
        await RisingEdge(dut.clk)
        if mode == "tx":
            dut.din.value = toggle & 1
            toggle += 1
