import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from test_backend import spi_xfer


# One mode per run. The clock period matches the 36 MHz reference so a VCD
# from this run can be read by OpenSTA against a 27.778 ns clock.
CYCLES = 1280


async def boot(dut):
    # 27.78 ns is 36.00 MHz within 0.01 percent. The cell models are
    # compiled at 10 ps, which cannot represent 27.777... ns.
    cocotb.start_soon(Clock(dut.clk, 27.78, unit="ns").start())
    dut.ref_36.value = 1
    dut.sclk.value = 0
    dut.cs_n.value = 1
    dut.mosi.value = 0
    dut.bclk_i.value = 0
    dut.lrclk_i.value = 0
    dut.din.value = 0
    dut.adc_valid.value = 0
    dut.adc_i.value = 0
    dut.adc_q.value = 0
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


@cocotb.test()
async def power_mode(dut):
    mode = os.environ.get("PWR_MODE", "shutdown")
    await boot(dut)
    if mode == "shutdown":
        await spi_xfer(dut, 0x00, 0x00, write=True)
    elif mode == "standby":
        await spi_xfer(dut, 0x00, 0x01, write=True)
    elif mode == "rx":
        await spi_xfer(dut, 0x03, 4, write=True)
        await spi_xfer(dut, 0x00, 0x02, write=True)
        dut.adc_valid.value = 1
        dut.adc_i.value = 1000
        dut.adc_q.value = 500
    elif mode == "tx":
        await spi_xfer(dut, 0x03, 4, write=True)
        await spi_xfer(dut, 0x00, 0x03, write=True)
    elif mode == "duty10":
        await spi_xfer(dut, 0x03, 4, write=True)
        await spi_xfer(dut, 0x01, 1, write=True)
        await spi_xfer(dut, 0x02, 9, write=True)
        await spi_xfer(dut, 0x00, 0x06, write=True)
        dut.adc_valid.value = 1
        dut.adc_i.value = 1000
        dut.adc_q.value = 500
    else:
        raise AssertionError(mode)
    toggle = 0
    for _ in range(CYCLES):
        await RisingEdge(dut.clk)
        if mode == "tx":
            dut.din.value = toggle & 1
            toggle += 1
