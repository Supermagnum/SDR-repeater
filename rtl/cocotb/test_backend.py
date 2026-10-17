import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge


async def reset(dut):
    dut.sclk.value = 0
    dut.cs_n.value = 1
    dut.mosi.value = 0
    dut.bclk.value = 0
    dut.lrclk.value = 0
    dut.din.value = 0
    dut.adc_valid.value = 0
    dut.adc_i.value = 0
    dut.adc_q.value = 0
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def spi_xfer(dut, addr, data, write):
    frame = ((1 if write else 0) << 15) | ((addr & 0x7F) << 8) | (data & 0xFF)
    miso_bits = []
    dut.cs_n.value = 0
    await RisingEdge(dut.clk)
    for bit in range(15, -1, -1):
        dut.mosi.value = (frame >> bit) & 1
        await RisingEdge(dut.clk)
        dut.sclk.value = 1
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        if bit < 8:
            miso_bits.append(int(dut.miso.value))
        dut.sclk.value = 0
        await RisingEdge(dut.clk)
    dut.cs_n.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    value = 0
    for bit in miso_bits:
        value = (value << 1) | bit
    return value


def to_signed(raw):
    raw &= 0xFFFF
    return raw - 0x10000 if raw & 0x8000 else raw


async def push_adc(dut, i_val, q_val):
    dut.adc_i.value = i_val & 0xFFFF
    dut.adc_q.value = q_val & 0xFFFF
    dut.adc_valid.value = 1
    await RisingEdge(dut.clk)
    dut.adc_valid.value = 0
    await RisingEdge(dut.clk)


async def i2s_slot(dut, right, sample, slot_32):
    bits = []
    width = 32 if slot_32 else 16
    word = (sample & 0xFFFF) << (16 if slot_32 else 0)
    dut.lrclk.value = 1 if right else 0
    for n in range(width):
        dut.din.value = (word >> (31 - n)) & 1 if slot_32 else (word >> (15 - n)) & 1
        dut.bclk.value = 0
        await RisingEdge(dut.clk)
        dut.bclk.value = 1
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        bits.append(int(dut.dout.value))
        dut.bclk.value = 0
        await RisingEdge(dut.clk)
    value = 0
    for bit in bits[:16]:
        value = (value << 1) | bit
    return to_signed(value)


@cocotb.test()
async def spi_roundtrip(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    await spi_xfer(dut, 0x05, 90, write=True)
    readback = await spi_xfer(dut, 0x05, 0, write=False)
    assert readback == 90, readback
    status = await spi_xfer(dut, 0x0A, 0, write=False)
    assert (status & 0x3) == 0, status


@cocotb.test()
async def decim_and_passthrough(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    # RX, wake 0, decimation 4, DC loop powered down.
    await spi_xfer(dut, 0x08, 0x02, write=True)
    await spi_xfer(dut, 0x03, 0x02, write=True)
    await spi_xfer(dut, 0x00, 0x02, write=True)
    await push_adc(dut, 100, -40)
    await push_adc(dut, 100, -40)
    await push_adc(dut, 100, -40)
    await push_adc(dut, 100, -40)
    for _ in range(4):
        await RisingEdge(dut.clk)
    assert int(dut.valid_iq.value) == 1
    got_i = await i2s_slot(dut, right=0, sample=0, slot_32=False)
    got_q = await i2s_slot(dut, right=1, sample=0, slot_32=False)
    assert got_i == 100, got_i
    assert got_q == -40, got_q


@cocotb.test()
async def slot_width_32(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    # RX, 32-bit slots, block the DC loop so the sample is not pulled down.
    await spi_xfer(dut, 0x08, 0x02, write=True)
    await spi_xfer(dut, 0x00, 0x0A, write=True)
    await push_adc(dut, 0x1234, 0x00AB)
    for _ in range(3):
        await RisingEdge(dut.clk)
    bits = []
    dut.lrclk.value = 0
    for n in range(32):
        dut.bclk.value = 0
        await RisingEdge(dut.clk)
        dut.bclk.value = 1
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        bits.append(int(dut.dout.value))
        dut.bclk.value = 0
        await RisingEdge(dut.clk)
    assert bits[:16] == [(0x1234 >> (15 - n)) & 1 for n in range(16)], bits[:16]
    assert bits[16:] == [0] * 16, bits[16:]


@cocotb.test()
async def duty_cycle_blanks(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    await spi_xfer(dut, 0x08, 0x02, write=True)
    await spi_xfer(dut, 0x01, 1, write=True)
    await spi_xfer(dut, 0x02, 1, write=True)
    await spi_xfer(dut, 0x00, 0x06, write=True)
    await push_adc(dut, 50, 60)
    for _ in range(2):
        await RisingEdge(dut.clk)
    first = await i2s_slot(dut, right=0, sample=0, slot_32=False)
    await i2s_slot(dut, right=1, sample=0, slot_32=False)
    assert first == 50, first
    await push_adc(dut, 50, 60)
    for _ in range(2):
        await RisingEdge(dut.clk)
    second = await i2s_slot(dut, right=0, sample=0, slot_32=False)
    assert second == 0, second
    assert int(dut.valid_iq.value) == 0


@cocotb.test()
async def wake_and_shutdown(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    await spi_xfer(dut, 0x08, 0x02, write=True)
    await spi_xfer(dut, 0x09, 1, write=True)
    await spi_xfer(dut, 0x00, 0x02, write=True)
    await push_adc(dut, 70, 80)
    for _ in range(8):
        await RisingEdge(dut.clk)
    assert int(dut.valid_iq.value) == 0
    during = await i2s_slot(dut, right=0, sample=0, slot_32=False)
    await i2s_slot(dut, right=1, sample=0, slot_32=False)
    assert during == 0, during
    await push_adc(dut, 70, 80)
    for _ in range(8):
        await RisingEdge(dut.clk)
    assert int(dut.valid_iq.value) == 1
    after = await i2s_slot(dut, right=0, sample=0, slot_32=False)
    assert after == 70, after
    await spi_xfer(dut, 0x00, 0x00, write=True)
    await push_adc(dut, 70, 80)
    for _ in range(2):
        await RisingEdge(dut.clk)
    assert int(dut.valid_iq.value) == 0


@cocotb.test()
async def iq_cal_gain(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    await spi_xfer(dut, 0x08, 0x02, write=True)
    await spi_xfer(dut, 0x05, 64, write=True)
    await spi_xfer(dut, 0x00, 0x02, write=True)
    await push_adc(dut, 200, 40)
    for _ in range(3):
        await RisingEdge(dut.clk)
    got_i = await i2s_slot(dut, right=0, sample=0, slot_32=False)
    got_q = await i2s_slot(dut, right=1, sample=0, slot_32=False)
    assert got_i == 100, got_i
    assert got_q == 40, got_q
