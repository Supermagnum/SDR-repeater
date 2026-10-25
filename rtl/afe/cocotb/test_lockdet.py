"""Lock detector (two-sided, P2.5 step 4) driven by a PFD model: per reference cycle a phase error e (ns,
positive = divider late). The PFD raises UP at the reference edge and DN at the divider edge and clears both
the reset width R after the later of the two; clk_su rises at reference + W, clk_sd at divider + W.
Checks: lock after 64 cycles at the locked point 2.9 +- 1.6 ns; held; cleared within 6 cycles by a late
(+9 ns) or an early (-9 ns) divider; no lock while the phase walks by 0.25 ns per cycle (a frequency error of
about 0.9 %); lock with the window at both ends of its allowed range (5 and 12 ns)."""
import random

import cocotb
from cocotb.triggers import Timer

T = 27.78
R = 0.25


async def play(dut, errs, w):
    """Drive len(errs) reference cycles; returns the lock output after each cycle."""
    ev = []
    for k, e in enumerate(errs):
        t_ref, t_div = k * T, k * T + e
        ev += [(t_ref, "up", 1), (t_div, "dn", 1), (max(t_ref, t_div) + R, "up", 0), (max(t_ref, t_div) + R, "dn", 0),
               (t_ref + w, "clk_su", 1), (t_ref + w + 1.0, "clk_su", 0),
               (t_div + w, "clk_sd", 1), (t_div + w + 1.0, "clk_sd", 0), ((k + 1) * T - 0.01, "sample", 0)]
    ev.sort(key=lambda x: (x[0], x[1] != "up" and x[1] != "dn"))
    out, t = [], ev[0][0]
    for at, sig, v in ev:
        if round((at - t) * 1000) > 0:
            await Timer(round((at - t) * 1000), unit="ps")
            t = at
        if sig == "sample":
            out.append(int(dut.lock.value))
        else:
            getattr(dut, sig).value = v
    return out


async def reset(dut):
    for s in ("clk_su", "clk_sd", "up", "dn"):
        getattr(dut, s).value = 0
    dut.en.value = 1
    dut.rst_n.value = 0
    await Timer(10, unit="ns")
    dut.rst_n.value = 1
    await Timer(30, unit="ns")


def locked(n, rng):
    return [2.9 + rng.uniform(-1.6, 1.6) for _ in range(n)]


@cocotb.test()
async def lock_and_unlock(dut):
    rng = random.Random(3)
    await reset(dut)
    o = await play(dut, locked(100, rng), 7.0)
    k = o.index(1) + 1
    assert 64 <= k <= 68 and all(o[k - 1:]), f"lock after {k} cycles"
    for e, side in ((9.0, "late"), (-9.0, "early")):
        o = await play(dut, [e] * 8, 7.0)
        assert 0 in o[:6], f"{side} divider: lock not cleared within 6 cycles ({o})"
        o = await play(dut, locked(80, rng), 7.0)
        assert o[-1] == 1, f"no relock after the {side} error"
    dut._log.info("lock after 64 cycles; cleared by a late and by an early divider; relocks")


@cocotb.test()
async def walk_no_lock(dut):
    await reset(dut)
    e, errs = 0.0, []
    for _ in range(400):
        errs.append((e + T / 2) % T - T / 2)
        e += 0.25
    o = await play(dut, errs, 7.0)
    assert not any(o), "locked while the phase walked by 0.25 ns per cycle"
    dut._log.info("no lock with the phase walking 0.25 ns per cycle")


@cocotb.test()
async def window_range(dut):
    rng = random.Random(5)
    for w in (5.0, 12.0):
        await reset(dut)
        o = await play(dut, locked(90, rng), w)
        assert o[-1] == 1 and o.index(1) + 1 <= 68, f"window {w} ns: no lock"
        o = await play(dut, [w + 2.0] * 8 + [-(w + 2.0)] * 0, w)
        assert 0 in o[:6], f"window {w} ns: late error not seen"
    dut._log.info("lock and unlock with the window at 5 and at 12 ns")
