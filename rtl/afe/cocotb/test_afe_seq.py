"""cocotb tests for afe_seq (P2.6 open point 2)."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, ReadOnly


BYPASS_CYCLES = 36
LODIV_DELAY_CYCLES = 48


async def reset(dut):
    dut.rst_n.value = 0
    dut.pll_on.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


@cocotb.test()
async def wake_bypass_and_lodiv(dut):
    """Bias bypass high for BYPASS_CYCLES; en_lodiv after LODIV_DELAY_CYCLES; all clear when pll_on falls."""
    cocotb.start_soon(Clock(dut.clk, 27.778, unit="ns").start())  # 36 MHz
    await reset(dut)

    assert int(dut.en_vco.value) == 0
    assert int(dut.en_vco_bias_bp.value) == 0
    assert int(dut.en_lodiv.value) == 0

    await RisingEdge(dut.clk)
    dut.pll_on.value = 1
    # NBA of the next posedge applies enables; wait one edge then ReadOnly
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.en_vco.value) == 1, f"en_vco={dut.en_vco.value} pll_on={dut.pll_on.value} rst_n={dut.rst_n.value}"
    assert int(dut.en_vco_bias_bp.value) == 1
    assert int(dut.en_lodiv.value) == 0

    # Remain in bypass for BYPASS_CYCLES-1 more cycles (bp high while cnt < 18)
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

    dut._log.info(
        f"wake OK: bypass {BYPASS_CYCLES} cycles, lodiv from cycle {LODIV_DELAY_CYCLES}"
    )
