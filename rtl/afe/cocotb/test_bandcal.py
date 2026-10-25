"""Band calibration against a VCO model: for targets across the range the result is the highest code whose
frequency is >= target (and the next code is below it); about 29 us per calibration."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge, Timer

from models import f_vco, m_full

F_REF = 36e6


async def vco_clock(dut, p):
    """f2 = f_VCO(band) / (4 P), following the band code."""
    while True:
        half = 4 * p / f_vco(int(dut.band.value)) / 2
        dut.f2.value = 1
        await Timer(round(half * 1e12), unit="ps")
        dut.f2.value = 0
        await Timer(round(half * 1e12), unit="ps")


@cocotb.test()
async def calibrate(dut):
    cocotb.start_soon(Clock(dut.clk, round(1e12 / F_REF), unit="ps").start())
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.f2.value = 0
    await Timer(100, unit="ns")
    dut.rst_n.value = 1
    task = None
    for f_target, p3 in ((3.12e9, 1), (3.40e9, 1), (3.65e9, 0), (3.84e9, 0), (4.20e9, 1), (3.20e9, 0)):
        n = f_target / F_REF
        n_int, n_frac = int(n), int((n - int(n)) * 2 ** 24)
        p = 3 if p3 else 2
        dut.m_full.value = m_full(n_int, n_frac, p3)
        if task:
            task.cancel()
        task = cocotb.start_soon(vco_clock(dut, p))
        await RisingEdge(dut.clk)
        dut.start.value = 1
        await RisingEdge(dut.clk)
        dut.start.value = 0
        t0 = cocotb.utils.get_sim_time("us")
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            if int(dut.done.value):
                break
        await Timer(1, unit="ns")
        dt = cocotb.utils.get_sim_time("us") - t0
        code = int(dut.band.value)
        assert f_vco(code) >= f_target * (1 - 6e-4), f"code {code}: {f_vco(code)/1e9:.4f} < {f_target/1e9}"
        assert code == 127 or f_vco(code + 1) < f_target * (1 + 6e-4), f"code {code} not the highest"
        assert not int(dut.fail.value)
        dut._log.info(f"target {f_target/1e9:.3f} GHz (P {p}): code {code} = {f_vco(code)/1e9:.4f} GHz, "
                      f"next {f_vco(min(code + 1, 127))/1e9:.4f} GHz, {dt:.1f} us")
