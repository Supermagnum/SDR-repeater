"""cocotb tests for afe_seq (P2.6 open point 2 + D22 cal_busy)."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, ReadOnly


BYPASS_CYCLES = 36
LODIV_DELAY_CYCLES = 48


async def reset(dut):
    dut.rst_n.value = 0
    dut.pll_on.value = 0
    dut.cal_busy.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


@cocotb.test()
async def wake_bypass_and_lodiv(dut):
    cocotb.start_soon(Clock(dut.clk, 27.778, unit="ns").start())
    await reset(dut)

    assert int(dut.en_vco.value) == 0
    assert int(dut.en_vco_bias_bp.value) == 0
    assert int(dut.en_lodiv.value) == 0

    await RisingEdge(dut.clk)
    dut.pll_on.value = 1
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.en_vco.value) == 1
    assert int(dut.en_vco_bias_bp.value) == 1
    assert int(dut.en_lodiv.value) == 0

    for _ in range(BYPASS_CYCLES - 1):
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert int(dut.en_vco_bias_bp.value) == 1

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.en_vco_bias_bp.value) == 0
    assert int(dut.en_lodiv.value) == 0

    while int(dut.en_lodiv.value) == 0:
        await RisingEdge(dut.clk)
        await ReadOnly()
    assert int(dut.en_vco.value) == 1
    assert int(dut.en_vco_bias_bp.value) == 0

    await RisingEdge(dut.clk)
    dut.pll_on.value = 0
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.en_vco.value) == 0
    assert int(dut.en_vco_bias_bp.value) == 0
    assert int(dut.en_lodiv.value) == 0

    dut._log.info(f"wake OK: bypass {BYPASS_CYCLES} cycles, lodiv from cycle {LODIV_DELAY_CYCLES}")


@cocotb.test()
async def cal_busy_holds_bypass(dut):
    """D22: cal_busy keeps bypass closed and lodiv off until cal ends."""
    cocotb.start_soon(Clock(dut.clk, 27.778, unit="ns").start())
    await reset(dut)
    await RisingEdge(dut.clk)
    dut.pll_on.value = 1
    dut.cal_busy.value = 1
    for _ in range(BYPASS_CYCLES + LODIV_DELAY_CYCLES + 10):
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert int(dut.en_vco_bias_bp.value) == 1
        assert int(dut.en_lodiv.value) == 0
    await RisingEdge(dut.clk)
    dut.cal_busy.value = 0
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.en_vco_bias_bp.value) == 0
    assert int(dut.en_lodiv.value) == 1
    dut._log.info("cal_busy holds bypass OK")
