"""MMD tests (P2.5 step 2b): every ratio 16-127 at a fixed setting, then a new ratio every output cycle as the
Sigma-Delta modulator will give it. Reference model: the output period in input cycles equals the ratio that
was applied for that cycle (with a fixed latency of whole output cycles, found from the data)."""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

PERIOD_NS = 1.0


async def setup(dut, n):
    dut.n.value = n
    dut.rst_n.value = 0
    cocotb.start_soon(Clock(dut.fin, PERIOD_NS, unit="ns").start())
    await Timer(5, unit="ns")
    dut.rst_n.value = 1


async def periods(dut, count, on_edge=None):
    """Input-cycle counts between successive rising edges of div_out."""
    out, cyc, last = [], 0, None
    fin_edge = RisingEdge(dut.fin)
    prev = int(dut.div_out.value)
    while len(out) < count:
        await fin_edge
        cyc += 1
        cur = int(dut.div_out.value)
        if cur and not prev:
            if last is not None:
                out.append(cyc - last)
            last = cyc
            if on_edge:
                on_edge(len(out))
        prev = cur
    return out


@cocotb.test()
async def every_ratio(dut):
    """Each ratio 16-127, fixed: all output periods equal N."""
    cocotb.start_soon(Clock(dut.fin, PERIOD_NS, unit="ns").start())
    bad = []
    for n in range(16, 128):
        dut.n.value = n
        dut.rst_n.value = 0
        await Timer(3, unit="ns")
        dut.rst_n.value = 1
        p = await periods(dut, 6)
        if any(x != n for x in p[2:]):
            bad.append((n, p))
    assert not bad, f"wrong periods: {bad[:5]}"
    dut._log.info("every ratio 16-127 correct")


@cocotb.test()
async def ratio_every_cycle(dut):
    """A new ratio after every output pulse (Sigma-Delta-like: 23-73 and N0 + (-3 .. +4)); each output period
    must equal one applied ratio, with a constant latency."""
    random.seed(7)
    seq = []
    for _ in range(400):
        seq.append(random.randint(23, 73))
    n0 = 48
    seq += [n0 + random.randint(-3, 4) for _ in range(400)]
    applied = []
    dut.n.value = seq[0]
    dut.rst_n.value = 0
    cocotb.start_soon(Clock(dut.fin, PERIOD_NS, unit="ns").start())
    await Timer(3, unit="ns")
    dut.rst_n.value = 1

    def new_ratio(k):
        v = seq[min(k, len(seq) - 1)]
        applied.append(v)
        dut.n.value = v

    p = await periods(dut, len(seq) - 4, new_ratio)
    best = None
    for lat in range(0, 4):
        ok = sum(1 for i in range(10, len(p)) if i - lat >= 0 and p[i] == applied[i - lat])
        if best is None or ok > best[1]:
            best = (lat, ok)
    lat, ok = best
    n = len(p) - 10
    bad = [(i, p[i], applied[i - lat]) for i in range(10, len(p)) if p[i] != applied[i - lat]]
    first = sum(1 for b in bad if b[0] < 400)
    dut._log.info(f"wrong: {first} in the first 400 (23-73), {len(bad) - first} after (45-52); first: {bad[:12]}")
    assert ok == n, f"latency {lat}: {n - ok} of {n} periods wrong"
    dut._log.info(f"{n} periods with a new ratio each cycle all correct (latency {lat} output cycles)")
