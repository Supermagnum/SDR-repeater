"""Band + amplitude calibration (D20/D22) against VCO frequency and amplitude models."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge, Timer

from models import amp_high_bit, amp_vco, f_vco8 as f_vco, m_full

F_REF = 36e6


async def vco_clock(dut, p):
    acc = 0.0
    while True:
        half = p / f_vco(int(dut.band.value)) / 2 * 1e12 + acc
        h = round(half)
        acc = half - h
        dut.f1.value = 1 - int(dut.f1.value)
        await Timer(h, unit="ps")


async def amp_driver(dut):
    """Drive amp_high from the amplitude model whenever vco_bias or band changes."""
    while True:
        await RisingEdge(dut.clk)
        if int(dut.rst_n.value) == 0:
            continue
        bias = int(dut.vco_bias.value)
        band = int(dut.band.value)
        dut.amp_high.value = 1 if amp_high_bit(bias, band) else 0


@cocotb.test()
async def calibrate_with_amp(dut):
    cocotb.start_soon(Clock(dut.clk, round(1e12 / F_REF), unit="ps").start())
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.f1.value = 0
    dut.amp_high.value = 0
    dut.amp_manual.value = 0
    await Timer(100, unit="ns")
    dut.rst_n.value = 1
    cocotb.start_soon(amp_driver(dut))
    task = None
    for f_target, p3 in ((3.12e9, 1), (3.65e9, 0), (4.20e9, 1)):
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
        await RisingEdge(dut.clk)
        dt = cocotb.utils.get_sim_time("us") - t0
        code = int(dut.band.value)
        bias = int(dut.vco_bias.value)
        tnr = int(dut.target_nr.value)
        tol = 2 / (128 * n / p) * f_target
        d = abs(f_vco(code) - f_target)
        for nb in (code - 1, code + 1):
            if 0 <= nb <= 255:
                assert d <= abs(f_vco(nb) - f_target) + tol
        amp = amp_vco(bias, code)
        # Model: top reaches ≥1.25; lower bands may stop at code 31 with target_nr
        if amp >= 1.15:
            assert not tnr or bias == 31
        else:
            assert tnr and bias == 31, f"amp {amp:.3f} bias {bias} tnr {tnr} band {code}"
        assert 45.0 < dt < 60.0, f"cal took {dt:.1f} us (expect ~49)"
        dut._log.info(
            f"target {f_target/1e9:.4f} GHz: band {code} bias {bias} amp≈{amp:.3f} V "
            f"tnr={tnr} in {dt:.1f} us"
        )


@cocotb.test()
async def manual_skips_amp(dut):
    cocotb.start_soon(Clock(dut.clk, round(1e12 / F_REF), unit="ps").start())
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.f1.value = 0
    dut.amp_high.value = 0
    dut.amp_manual.value = 1
    await Timer(100, unit="ns")
    dut.rst_n.value = 1
    dut.m_full.value = m_full(100, 0, 0)
    cocotb.start_soon(vco_clock(dut, 2))
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
    dt = cocotb.utils.get_sim_time("us") - t0
    # Band-only ≈ 38.8 µs; with amp would be ~49 µs
    assert 30.0 < dt < 45.0, f"manual cal {dt:.1f} us"
    dut._log.info(f"manual band-only {dt:.1f} us")
