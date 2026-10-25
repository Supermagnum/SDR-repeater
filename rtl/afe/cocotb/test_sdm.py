"""Sigma-Delta tests: divide-by-P exact, div_n bit-exact against the Python model, mean equal to M, range."""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge, Timer

from models import m_full, sdm

CASES = [(100, 0x000000, 0), (100, 0x123456, 0), (120, 0xFFFFFF, 0), (86, 0x8A3D71, 1),
         (131, 0x400000, 1), (97, 0x000001, 1), (110, 0x555555, 1)]


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 27.78, unit="ns").start())
    dut.rst_n.value = 0
    dut.load.value = 0
    dut.en_mash.value = 1
    dut.en_dither.value = 1
    await Timer(60, unit="ns")
    dut.rst_n.value = 1


async def load(dut, n_int, n_frac, p3):
    await RisingEdge(dut.clk)
    dut.n_int.value, dut.n_frac.value, dut.p3.value, dut.load.value = n_int, n_frac, p3, 1
    await RisingEdge(dut.clk)
    dut.load.value = 0
    while True:                      # wait until the division is done
        await RisingEdge(dut.clk)
        await ReadOnly()
        if not int(dut.busy.value):
            break


@cocotb.test()
async def bit_exact(dut):
    await start(dut)
    for n_int, n_frac, p3 in CASES:
        await load(dut, n_int, n_frac, p3)
        m = m_full(n_int, n_frac, p3)
        assert int(dut.m_full.value) == m, f"M wrong for {n_int},{n_frac:#x},P={3 if p3 else 2}"
        got = []
        for _ in range(2000):
            await RisingEdge(dut.clk)
            await ReadOnly()
            got.append(int(dut.div_n.value))
        ref = sdm(m, 2001)
        lag = next(k for k in range(4) if got[10:200] == ref[10 - k:200 - k])
        assert got[10:] == ref[10 - lag:2000 - lag], "sequence differs from the model"
        mean = sum(got[100:]) / len(got[100:])
        exp = m / 2 ** 24
        assert abs(mean - exp) < 2e-3, f"mean {mean} vs {exp}"
        assert min(got) >= (m >> 24) - 3 and max(got) <= (m >> 24) + 4
        dut._log.info(f"N {n_int}+{n_frac / 2**24:.6f}, P {3 if p3 else 2}: M {exp:.7f}, mean {mean:.5f}, "
                      f"div_n {min(got)}..{max(got)}, bit-exact (lag {lag})")


@cocotb.test()
async def integer_mode(dut):
    await start(dut)
    dut.en_mash.value = 0
    await load(dut, 100, 0x123456, 0)
    for _ in range(50):
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert int(dut.div_n.value) == m_full(100, 0x123456, 0) >> 24
    dut._log.info("integer-N mode: constant M_int")
