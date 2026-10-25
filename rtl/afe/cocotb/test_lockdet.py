"""Lock detector: UP pulses of 3.5 ns (+-1 ns wander) inside a 6.5 ns window -> lock after 64 cycles; an
out-of-window phase error for 4 cycles clears it; DN-side errors too."""
import random

import cocotb
from cocotb.triggers import Timer

T = 27.78
W = 6.5


async def cycle(dut, up_ns, dn_ns):
    """One reference cycle: UP for up_ns and DN for dn_ns from the reference edge; clk_s at +W."""
    dut.up.value = 1 if up_ns > 0 else 0
    dut.dn.value = 1 if dn_ns > 0 else 0
    events = sorted([(up_ns, "up"), (dn_ns, "dn"), (W, "clk")])
    t = 0.0
    for at, what in events:
        if at > t:
            await Timer(round((at - t) * 1000), unit="ps")
            t = at
        if what == "up" and up_ns > 0:
            dut.up.value = 0
        elif what == "dn" and dn_ns > 0:
            dut.dn.value = 0
        elif what == "clk":
            dut.clk_s.value = 1
    await Timer(round(T / 2 * 1000), unit="ps")
    dut.clk_s.value = 0
    await Timer(round((T - t - T / 2) * 1000), unit="ps")


@cocotb.test()
async def lock_and_unlock(dut):
    random.seed(3)
    dut.clk_s.value = 0
    dut.up.value = 0
    dut.dn.value = 0
    dut.en.value = 1
    dut.rst_n.value = 0
    await Timer(10, unit="ns")
    dut.rst_n.value = 1
    k = 0
    while not int(dut.lock.value):
        await cycle(dut, 3.5 + random.uniform(-1, 1), 0.3)
        k += 1
        assert k < 100
    assert 64 <= k <= 68, f"lock after {k} cycles"
    for _ in range(200):
        await cycle(dut, 3.5 + random.uniform(-1, 1), 0.3)
        assert int(dut.lock.value)
    for j in range(8):                          # phase error beyond the window
        await cycle(dut, 9.0, 0.3)
        if not int(dut.lock.value):
            break
    assert not int(dut.lock.value) and j <= 6, "lock not cleared"
    k = 0
    while not int(dut.lock.value):
        await cycle(dut, 3.0, 0.3)
        k += 1
        assert k < 100
    for j in range(8):                          # DN-side error
        await cycle(dut, 0.3, 8.0)
        if not int(dut.lock.value):
            break
    assert not int(dut.lock.value)
    dut._log.info("lock after 64 good cycles, held with +-1 ns wander, cleared by UP or DN errors")
