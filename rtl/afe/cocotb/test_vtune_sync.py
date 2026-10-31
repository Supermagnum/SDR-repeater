"""cocotb: vtune_sync 2-FF for PLL_STATUS[4:5]."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, ReadOnly


async def reset(dut):
    dut.rst_n.value = 0
    dut.vtune_lo_a.value = 0
    dut.vtune_hi_a.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


@cocotb.test()
async def sync_delay_and_clear(dut):
    cocotb.start_soon(Clock(dut.clk, 27.778, unit="ns").start())
    await reset(dut)
    assert int(dut.vtune_lo.value) == 0
    assert int(dut.vtune_hi.value) == 0

    await RisingEdge(dut.clk)
    dut.vtune_lo_a.value = 1
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.vtune_lo.value) == 0  # still in first flop
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.vtune_lo.value) == 1
    assert int(dut.vtune_hi.value) == 0

    await RisingEdge(dut.clk)
    dut.vtune_hi_a.value = 1
    dut.vtune_lo_a.value = 0
    await ClockCycles(dut.clk, 2)
    await ReadOnly()
    assert int(dut.vtune_hi.value) == 1
    assert int(dut.vtune_lo.value) == 0

    dut._log.info("vtune_sync: 2-FF delay OK; maps to PLL_STATUS[4:5]")
