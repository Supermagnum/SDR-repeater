"""Band calibration (8 bits, counter on f / P, nearest-code rule; P2.6 step 1, D20) against a VCO model: for
targets across the range the result is the code whose frequency is closest to the target (within the counting
resolution); 38.8 us per calibration."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge, Timer

from models import f_vco8 as f_vco, m_full

F_REF = 36e6


async def vco_clock(dut, p):
    """f1 = f_VCO(band) / P, following the band code. Half periods in whole ps with the rounding error carried
    over, so the mean frequency is exact (plain rounding to 1 ps is up to 0.2 % off at 1.9 GHz)."""
    acc = 0.0
    while True:
        half = p / f_vco(int(dut.band.value)) / 2 * 1e12 + acc
        h = round(half)
        acc = half - h
        dut.f1.value = 1 - int(dut.f1.value)
        await Timer(h, unit="ps")


@cocotb.test()
async def calibrate(dut):
    cocotb.start_soon(Clock(dut.clk, round(1e12 / F_REF), unit="ps").start())
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.f1.value = 0
    await Timer(100, unit="ns")
    dut.rst_n.value = 1
    task = None
    for f_target, p3 in ((3.12e9, 1), (3.40e9, 1), (3.65e9, 0), (3.84e9, 0), (4.20e9, 1), (3.20e9, 0),
                         (3.4567e9, 1), (3.7311e9, 0)):
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
        # nearest code: no neighbour is closer to the target than the chosen code, within the counting
        # resolution (two counts of K * M = 128 * N / P, 3700-6400)
        tol = 2 / (128 * n / p) * f_target
        d = abs(f_vco(code) - f_target)
        for nb in (code - 1, code + 1):
            if 0 <= nb <= 255:
                assert d <= abs(f_vco(nb) - f_target) + tol, f"code {code} ({f_vco(code)/1e9:.5f}) not the nearest ({nb})"
        assert not int(dut.fail.value)
        dut._log.info(f"target {f_target/1e9:.4f} GHz (P {p}): code {code} = {f_vco(code)/1e9:.4f} GHz "
                      f"(neighbours {f_vco(max(code - 1, 0))/1e9:.4f} / {f_vco(min(code + 1, 255))/1e9:.4f}), {dt:.1f} us")
