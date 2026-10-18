import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer


RATES_KHZ = [25, 50, 100, 200, 500]
# (ref_mhz, rate_index) -> (frame clocks, r1, r2, sh1, sh2)
TABLE = {
    (32, 0): (1280, 4, 10, 16, 8, 13),
    (32, 1): (640, 4, 8, 10, 7, 10),
    (32, 2): (320, 4, 5, 8, 4, 9),
    (32, 3): (160, 4, 4, 5, 3, 6),
    (32, 4): (64, 4, 2, 4, 0, 4),
    (36, 0): (1440, 4, 12, 15, 9, 13),
    (36, 1): (720, 4, 9, 10, 7, 11),
    (36, 2): (360, 4, 5, 9, 4, 10),
    (36, 3): (180, 2, 5, 9, 4, 10),
    (36, 4): (72, 4, 3, 3, 0, 4),
}
FRONT = np.array([1, 4, 8, 12, 12, 8, 4, 1], dtype=float)
# A full-scale 1-bit input (all ones) lands at FS on the output word.
FS = 16384
FS_TOL = 64
HB = np.array([-138, 0, 305, 0, -617, 0, 1128, 0, -1952, 0, 3376, 0,
               -6450, 0, 20688, 32767, 20688, 0, -6450, 0, 3376, 0,
               -1952, 0, 1128, 0, -617, 0, 305, 0, -138], dtype=float)
CF = np.array([-5006, 32767, -5006], dtype=float)
# The 45 dB alias number is provisional until the Phase 3 modulator
# co-design. The coefficient set clears it; the limit is not frozen.
RIPPLE_LIMIT_DB = 0.25
ALIAS_LIMIT_DB = 45.0


async def start(dut, ref_36=0):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.ref_36.value = ref_36
    dut.sclk.value = 0
    dut.cs_n.value = 1
    dut.mosi.value = 0
    dut.bclk_i.value = 0
    dut.lrclk_i.value = 0
    dut.din.value = 0
    dut.adc_valid.value = 0
    dut.adc_bit_i.value = 0
    dut.adc_bit_q.value = 0
    dut.adc_i.value = 0
    dut.adc_q.value = 0
    # Start high, then fall: some simulators (Verilator) start signals at 0
    # and only run an async-reset branch on a real falling edge.
    dut.rst_n.value = 1
    await Timer(1, unit="ns")
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
        if bit < 8:
            # Mode 0: sample MISO at the SCLK rising edge, as a real host does.
            miso_bits.append(int(dut.miso.value))
        dut.sclk.value = 1
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        dut.sclk.value = 0
        await RisingEdge(dut.clk)
    dut.cs_n.value = 1
    # Raise CS first, then pulse SCLK: changing both at once is a race
    # (gate level sees the edge before CS), and real hosts never do it.
    await RisingEdge(dut.clk)
    dut.sclk.value = 1
    await RisingEdge(dut.clk)
    dut.sclk.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    value = 0
    for bit in miso_bits:
        value = (value << 1) | bit
    return value


def cic_mag(freq, fs_in, ratio, order=4):
    freq = np.asarray(freq, dtype=float)
    out = np.empty_like(freq)
    small = np.abs(freq) < 1.0
    out[small] = float(ratio ** order)
    s = ~small
    out[s] = np.abs(np.sin(np.pi * freq[s] * ratio / fs_in) / np.sin(np.pi * freq[s] / fs_in)) ** order
    return out


def fir_mag(coeff, freq, fs):
    w = 2 * np.pi * np.asarray(freq, dtype=float) / fs
    k = np.arange(len(coeff))
    return np.abs(np.exp(-1j * np.outer(w, k)) @ coeff)


def chain_mag(freq, fref, fs, r0, r1, r2):
    freq = np.asarray(freq, dtype=float)
    hcic = fir_mag(FRONT, freq, fref)
    hcic = hcic * cic_mag(freq, fref / r0, r1) * cic_mag(freq, fref / r0 / r1, r2)
    folded = np.abs(freq) % (2 * fs)
    folded = np.minimum(folded, 2 * fs - folded)
    return hcic * fir_mag(CF, folded, 2 * fs) * fir_mag(HB, folded, 2 * fs)


@cocotb.test()
async def spi_reset_and_registers(dut):
    await start(dut)
    expect_reset = {
        0x00: 0x00,
        0x01: 1,
        0x02: 0,
        0x03: 4,
        0x04: 4,
        0x05: 128,
        0x06: 128,
        0x07: 0,
        0x08: 0,
        0x09: 0,
        0x0B: 0x11,
        0x0C: 0,
        0x0D: 0,
        0x0E: 0,
        0x0F: 0,
        0x10: 128,
        0x11: 128,
        0x12: 0,
        0x13: 0x1F,
    }
    for addr, exp in expect_reset.items():
        got = await spi_xfer(dut, addr, 0, write=False)
        assert got == exp, (addr, got, exp)
    writes = {
        0x01: 3, 0x02: 5, 0x03: 2, 0x04: 6, 0x05: 90, 0x06: 100,
        0x07: 0xE0, 0x08: 0x0F, 0x09: 4, 0x0C: 1,
        0x0E: 0x05, 0x10: 140, 0x12: 0x10, 0x13: 0x1F,
    }
    for addr, data in writes.items():
        await spi_xfer(dut, addr, data, write=True)
    for addr, data in writes.items():
        got = await spi_xfer(dut, addr, 0, write=False)
        if addr == 0x0C:
            data = 1
        assert got == data, (addr, got, data)
    # CTRL bit 7 is a clear strobe and does not stick. Bit 4 is slave.
    await spi_xfer(dut, 0x00, 0x96, write=True)
    ctrl = await spi_xfer(dut, 0x00, 0, write=False)
    assert ctrl == 0x16, ctrl
    # Chip ID is not writable.
    await spi_xfer(dut, 0x0B, 0xFF, write=True)
    assert await spi_xfer(dut, 0x0B, 0, write=False) == 0x11
    # Standby keeps the other registers.
    await spi_xfer(dut, 0x00, 0x01, write=True)
    assert await spi_xfer(dut, 0x05, 0, write=False) == 90
    assert await spi_xfer(dut, 0x0C, 0, write=False) == 1


@cocotb.test()
async def phase_cross_term(dut):
    await start(dut)
    # Bypass CIC and DC. phase = 32/128 rad per full-scale Q into I.
    await spi_xfer(dut, 0x08, 0x03, write=True)
    await spi_xfer(dut, 0x07, 32, write=True)
    await spi_xfer(dut, 0x00, 0x02, write=True)
    for _ in range(12):
        await RisingEdge(dut.clk)
    dut.adc_i.value = 0
    dut.adc_q.value = 400
    dut.adc_valid.value = 1
    await RisingEdge(dut.clk)
    dut.adc_valid.value = 0
    for _ in range(6):
        await RisingEdge(dut.clk)
    assert int(dut.i_hold.value.to_signed()) == 100
    assert int(dut.q_hold.value.to_signed()) == 400
    # 2 degrees is 0.0349 rad. One phase LSB is 1/128 rad, about 0.45 degrees,
    # so the cross-term can place the residual under 2 degrees.


@cocotb.test()
async def master_frame_lengths(dut):
    await start(dut)
    await spi_xfer(dut, 0x08, 0x07, write=True)
    for ref, pin in ((32, 0), (36, 1)):
        dut.ref_36.value = pin
        for rate in range(5):
            await spi_xfer(dut, 0x03, rate, write=True)
            await spi_xfer(dut, 0x00, 0x02, write=True)
            for _ in range(8):
                await RisingEdge(dut.clk)
            m = TABLE[(ref, rate)][0]
            illegal = ref == 36 and rate == 4
            status = await spi_xfer(dut, 0x0A, 0, write=False)
            assert bool(status & 0x40) == illegal, (ref, rate, status)
            if illegal:
                continue
            prev = int(dut.lrclk_o.value)
            rises = 0
            period = 0
            highs = 0
            lows = 0
            for _ in range(m * 3):
                await RisingEdge(dut.clk)
                now = int(dut.lrclk_o.value)
                b = int(dut.bclk_o.value)
                if rises == 1:
                    period += 1
                    if b:
                        highs += 1
                    else:
                        lows += 1
                if prev == 0 and now == 1:
                    rises += 1
                    if rises == 2:
                        break
                prev = now
            assert period == m, (ref, rate, period, m)
            # 50 percent of the active bit cells, plus idle lows at the
            # end of a frame that is longer than the slots.
            assert highs > 0 and abs(highs - lows) <= m, (ref, rate, highs, lows)


@cocotb.test()
async def filter_response_limits(dut):
    # Numeric response of the coefficients and ratios used by the RTL.
    await start(dut)
    worst_rip = 0.0
    worst_alias = 999.0
    for (ref, rate), (m, r0, r1, r2, _s1, _s2) in TABLE.items():
        fs = RATES_KHZ[rate] * 1e3
        fref = ref * 1e6
        f = np.linspace(0, 0.40 * fs, 200)
        h = chain_mag(f, fref, fs, r0, r1, r2)
        h = h / h[0]
        rip = 20 * np.log10(h.max() / h.min())
        fp = np.linspace(0.02 * fs, 0.40 * fs, 40)
        num = chain_mag(fp, fref, fs, r0, r1, r2)
        den = np.max(np.stack([chain_mag(k * fs - fp, fref, fs, r0, r1, r2) for k in (1, 2, 3, 4)]), axis=0)
        alias = 20 * np.log10(np.min(num) / np.max(den))
        assert rip <= RIPPLE_LIMIT_DB, (ref, rate, rip)
        assert alias >= ALIAS_LIMIT_DB, (ref, rate, alias)
        worst_rip = max(worst_rip, rip)
        worst_alias = min(worst_alias, alias)
        assert r0 * r1 * r2 * 2 == m
    cocotb.log.info("worst ripple %.3f dB, worst alias %.1f dB", worst_rip, worst_alias)


@cocotb.test()
async def filter_dc_and_overflow(dut):
    await start(dut)
    await spi_xfer(dut, 0x08, 0x06, write=True)
    await spi_xfer(dut, 0x03, 4, write=True)
    await spi_xfer(dut, 0x00, 0x02, write=True)
    dut.adc_bit_i.value = 1
    dut.adc_bit_q.value = 1
    dut.adc_valid.value = 1
    seen = []
    for _ in range(64 * 80):
        await RisingEdge(dut.clk)
        if int(dut.cal_v.value):
            seen.append(int(dut.cal_i.value.to_signed()))
    dut.adc_valid.value = 0
    assert len(seen) >= 8, len(seen)
    # Constant +1 through the normalized chain is code 64 at this rate.
    assert abs(seen[-1] - FS) <= FS_TOL, seen[-1]
    dut.adc_bit_i.value = 0
    dut.adc_bit_q.value = 0
    dut.adc_valid.value = 1
    full = []
    for _ in range(64 * 80):
        await RisingEdge(dut.clk)
        if int(dut.cal_v.value):
            full.append(int(dut.cal_i.value.to_signed()))
    assert abs(full[-1] + FS) <= FS_TOL, full[-1]


@cocotb.test()
async def dc_retained_across_sleep(dut):
    await start(dut)
    await spi_xfer(dut, 0x08, 0x05, write=True)  # bypass CIC and IQ cal
    await spi_xfer(dut, 0x04, 1, write=True)
    await spi_xfer(dut, 0x00, 0x02, write=True)
    dut.adc_i.value = 200
    dut.adc_q.value = -80
    async def frames(n):
        got = 0
        while got < n:
            dut.adc_valid.value = 1
            await RisingEdge(dut.clk)
            dut.adc_valid.value = 0
            await RisingEdge(dut.clk)
            if int(dut.sample_valid.value):
                got += 1
        return int(dut.i_hold.value.to_signed())
    await frames(30)
    settled = int(dut.i_hold.value.to_signed())
    assert abs(settled) < 20, settled
    await spi_xfer(dut, 0x00, 0x01, write=True)  # standby
    for _ in range(10):
        await RisingEdge(dut.clk)
    await spi_xfer(dut, 0x00, 0x02, write=True)
    first = await frames(1)
    assert abs(first) < 20, first
    await spi_xfer(dut, 0x0D, 1, write=True)
    # shift=1 halves the residual each frame. The first frame after a
    # clear jumps back toward the raw offset. Later frames reconverge.
    samples = []
    for _ in range(8):
        dut.adc_valid.value = 1
        await RisingEdge(dut.clk)
        dut.adc_valid.value = 0
        for _w in range(6):
            await RisingEdge(dut.clk)
            if int(dut.cal_v.value):
                samples.append(int(dut.i_hold.value.to_signed()))
    assert len(samples) >= 2, samples
    # samples[0] is the word already in the pipeline when clear was written.
    assert abs(samples[1] - 100) < 30, samples
    reconverged = next((i for i, y in enumerate(samples) if i > 0 and abs(y) < 20), None)
    assert reconverged is not None, samples
    cocotb.log.info("DC clear: first=%s frames to |y|<20: %s", samples[0], reconverged)


@cocotb.test()
async def wake_duty_and_power(dut):
    await start(dut)
    await spi_xfer(dut, 0x08, 0x07, write=True)
    await spi_xfer(dut, 0x09, 0, write=True)
    await spi_xfer(dut, 0x01, 1, write=True)
    await spi_xfer(dut, 0x02, 1, write=True)
    await spi_xfer(dut, 0x00, 0x06, write=True)  # RX, duty, wake 0
    dut.adc_i.value = 50
    dut.adc_q.value = 60
    dut.adc_valid.value = 1
    blanks = 0
    valids = 0
    # Two-frame duty period is 128 reference clocks at 500 kHz.
    for _ in range(64 * 6):
        await RisingEdge(dut.clk)
        if int(dut.cal_v.value):
            if int(dut.sample_valid.value):
                valids += 1
            else:
                blanks += 1
    assert blanks >= 64, blanks
    assert valids >= 64, valids
    await spi_xfer(dut, 0x00, 0x00, write=True)
    await RisingEdge(dut.clk)
    assert int(dut.valid_iq.value) == 0
    assert await spi_xfer(dut, 0x03, 0, write=False) == 4
    await spi_xfer(dut, 0x09, 0, write=True)
    await spi_xfer(dut, 0x02, 0, write=True)
    await spi_xfer(dut, 0x00, 0x06, write=True)
    on_count = 0
    dut.adc_valid.value = 1
    for _ in range(64 * 3):
        await RisingEdge(dut.clk)
        if int(dut.cal_v.value) and int(dut.sample_valid.value):
            on_count += 1
    assert on_count >= 64, on_count
    await spi_xfer(dut, 0x01, 0, write=True)
    await spi_xfer(dut, 0x02, 2, write=True)
    await spi_xfer(dut, 0x00, 0x01, write=True)
    await spi_xfer(dut, 0x00, 0x06, write=True)
    off_after = 0
    blank_after = 0
    for _ in range(64 * 4):
        await RisingEdge(dut.clk)
        if int(dut.cal_v.value):
            if int(dut.sample_valid.value):
                off_after += 1
            else:
                blank_after += 1
    assert off_after >= 1 and blank_after >= 1, (off_after, blank_after)


@cocotb.test()
async def band_relock(dut):
    await start(dut)
    await spi_xfer(dut, 0x0C, 1, write=True)
    status = await spi_xfer(dut, 0x0A, 0, write=False)
    assert status & 0x80, status
    assert await spi_xfer(dut, 0x0C, 0, write=False) == 1
    for _ in range(70):
        await RisingEdge(dut.clk)
    status = await spi_xfer(dut, 0x0A, 0, write=False)
    assert (status & 0x80) == 0, status


@cocotb.test()
async def slave_fifo_drift(dut):
    await start(dut)
    await spi_xfer(dut, 0x08, 0x07, write=True)
    # Slave, RX. Filters bypassed, so each adc_valid is one FIFO write.
    await spi_xfer(dut, 0x00, 0x12, write=True)
    dut.adc_i.value = 7
    dut.adc_q.value = 9
    for _ in range(12):
        dut.adc_valid.value = 1
        await RisingEdge(dut.clk)
        dut.adc_valid.value = 0
        await RisingEdge(dut.clk)
    status = await spi_xfer(dut, 0x0A, 0, write=False)
    assert status & 0x10, status  # overflow
    # Slow then empty reads on an unrelated BCLK.
    for _ in range(20):
        dut.lrclk_i.value = 0
        dut.bclk_i.value = 1
        await Timer(4, unit="ns")
        dut.bclk_i.value = 0
        await Timer(4, unit="ns")
        dut.lrclk_i.value = 1
        for _b in range(16):
            dut.bclk_i.value = 1
            await Timer(4, unit="ns")
            dut.bclk_i.value = 0
            await Timer(4, unit="ns")
    await RisingEdge(dut.clk)
    status = await spi_xfer(dut, 0x0A, 0, write=False)
    assert status & 0x20, status  # underflow
    # Leave RX so further BCLK edges do not take another empty word.
    await spi_xfer(dut, 0x00, 0x80, write=True)
    for _ in range(8):
        dut.bclk_i.value = 1
        await Timer(20, unit="ns")
        dut.bclk_i.value = 0
        await Timer(20, unit="ns")
    status = await spi_xfer(dut, 0x0A, 0, write=False)
    assert (status & 0x30) == 0, status


def raw_dc_gain(r1, sh1, r2, sh2):
    cic = (r1 ** 4) / (2 ** sh1) * (r2 ** 4) / (2 ** sh2)
    return 50.0 * cic * float(np.sum(CF)) / 32768.0 * float(np.sum(HB)) / 32768.0


@cocotb.test()
async def filter_dc_all_rates(dut):
    # Every reference/rate pair, after `norm`, settles at the input.
    gains = []
    for (ref, rate), (m, r0, r1, r2, sh1, sh2) in TABLE.items():
        raw = raw_dc_gain(r1, sh1, r2, sh2)
        gains.append(raw)
        await start(dut, ref_36=1 if ref == 36 else 0)
        await spi_xfer(dut, 0x08, 0x06, write=True)
        await spi_xfer(dut, 0x03, rate, write=True)
        await spi_xfer(dut, 0x00, 0x02, write=True)
        dut.adc_bit_i.value = 1
        dut.adc_bit_q.value = 1
        dut.adc_valid.value = 1
        seen = []
        for _ in range(m * 48):
            await RisingEdge(dut.clk)
            if int(dut.cal_v.value):
                seen.append(int(dut.cal_i.value.to_signed()))
        assert len(seen) >= 8, (ref, rate, len(seen))
        assert abs(seen[-1] - FS) <= FS_TOL, (ref, rate, raw, seen[-1])
    # The un-normalized gains are not the same. 32 MHz / 500 kHz is the low one.
    assert max(gains) / min(gains) > 1.5, gains
    cocotb.log.info("raw DC gains %s", ["%.4f" % g for g in gains])


@cocotb.test()
async def tx_image_and_noise(dut):
    # 500 kHz, 32 MHz, 16-bit slots. BCLK is 16 MHz with a 2-clock cell.
    # A Philips I2S host: DIN changes on the BCLK falling edge, cells are
    # counted from the LRCLK falling edge, and I bit e sits in cell e+1.
    # Tone at 0.1*fs on I, Q silent.
    await start(dut, ref_36=0)
    await spi_xfer(dut, 0x03, 4, write=True)
    await spi_xfer(dut, 0x00, 0x03, write=True)
    fs = 500_000.0
    f_tone = 0.1 * fs
    bits = []
    sample_n = 0
    word = int(round(8000 * np.sin(2 * np.pi * f_tone / fs * sample_n))) & 0xFFFF
    cell = None
    prev_b = int(dut.bclk_o.value)
    prev_lr = int(dut.lrclk_o.value)
    for _ in range(64 * 160):
        # Observe and drive on clk's falling edge: the I2S master runs on a
        # gated clock that settles after clk's rising edge in RTL simulation.
        await FallingEdge(dut.clk)
        b_now = int(dut.bclk_o.value)
        lr = int(dut.lrclk_o.value)
        if prev_b == 1 and b_now == 0:
            # BCLK falling edge: the host changes DIN here.
            if prev_lr == 1 and lr == 0:
                cell = 0
            elif cell is not None:
                cell += 1
            e = None if cell is None else cell - 1
            if e is not None and 0 <= e < 16:
                dut.din.value = (word >> (15 - e)) & 1
                if e == 15:
                    sample_n += 1
                    word = int(round(8000 * np.sin(2 * np.pi * f_tone / fs * sample_n))) & 0xFFFF
            else:
                dut.din.value = 0
        prev_b = b_now
        prev_lr = lr
        if int(dut.dac_bit_valid.value):
            bits.append(1.0 if int(dut.dac_bit_i.value) else -1.0)
    assert len(bits) > 4096, len(bits)
    bits = np.array(bits[2500:], dtype=float)
    w = np.hanning(len(bits))
    spec = np.abs(np.fft.rfft(bits * w))
    freqs = np.fft.rfftfreq(len(bits), 1.0 / 32e6)
    mag = 20.0 * np.log10(spec + 1e-15)
    df = float(freqs[1] - freqs[0])

    def peak(f0):
        m = np.abs(freqs - f0) < (2.0 * df + 1.0)
        return float(mag[m].max())

    tone = peak(f_tone)
    image = peak(fs - f_tone)
    oob = (freqs > 1.0e6) & (freqs < 8.0e6)
    floor = float(np.median(mag[oob]))
    cocotb.log.info(
        "TX tone %.1f dB, image %.1f dB, rej %.1f dB, oob floor %.1f dB",
        tone, image, tone - image, floor,
    )
    # The 1-8 MHz floor limit is provisional. Phase 4 has to derive it
    # from the emission mask, including the analogue reconstruction
    # filter and the modulator order. The expected mask is 60-70 dB
    # below the carrier near the carrier. 20 dB is only this model's
    # shaped-noise check.
    assert tone - image >= 40.0, (tone, image)
    assert tone - floor >= 20.0, (tone, floor)


@cocotb.test()
async def rx_chain_ports(dut):
    # Port-level RX check so the same test can run on the gate netlist.
    # DC and IQ are bypassed. The decimator output is the I2S left word.
    await start(dut)
    await spi_xfer(dut, 0x08, 0x06, write=True)
    await spi_xfer(dut, 0x03, 4, write=True)
    await spi_xfer(dut, 0x00, 0x02, write=True)
    dut.adc_bit_i.value = 1
    dut.adc_bit_q.value = 1
    dut.adc_valid.value = 1
    saw = 0
    for _ in range(64 * 50):
        await RisingEdge(dut.clk)
        if int(dut.valid_iq.value):
            saw += 1
    assert saw >= 8, saw
    prev_lr = int(dut.lrclk_o.value)
    while True:
        await RisingEdge(dut.clk)
        lr = int(dut.lrclk_o.value)
        if prev_lr == 1 and lr == 0:
            break
        prev_lr = lr
    # Philips I2S: sample DOUT on BCLK rising edges, as a host does.
    # The first rising edge after LRCLK falls (cell 0) carries the previous
    # right-channel bit; the left MSB is in the next cell.
    word = 0
    bits = 0
    rises = 0
    prev_b = int(dut.bclk_o.value)
    for _ in range(200):
        await RisingEdge(dut.clk)
        b = int(dut.bclk_o.value)
        if prev_b == 0 and b == 1:
            rises += 1
            if rises >= 2 and bits < 16:
                word = ((word << 1) | int(dut.dout.value)) & 0xFFFF
                bits += 1
        prev_b = b
    if word & 0x8000:
        word -= 65536
    assert bits == 16, bits
    assert abs(word - FS) <= FS_TOL, word




@cocotb.test()
async def rx_tone_rtl(dut):
    """Real tones through the RTL RX chain: passband gain and alias rejection."""
    await start(dut)
    await spi_xfer(dut, 0x08, 0x06, write=True)   # bypass DC loop and IQ cal
    await spi_xfer(dut, 0x03, 4, write=True)      # 500 kHz
    await spi_xfer(dut, 0x00, 0x02, write=True)   # RX
    fref, fs, n = 32e6, 500e3, 512
    k_sig, k_alias = 41, 97
    a_sig, a_int = 0.2, 0.3
    f_sig = k_sig * fs / n                 # ~40 kHz, in band
    f_int = fs - k_alias * fs / n          # ~405 kHz, folds to bin 97
    skip = 96
    clocks = int((n + skip + 8) * fref / fs)
    t = np.arange(clocks) / fref
    x = a_sig * np.sin(2 * np.pi * f_sig * t) + a_int * np.sin(2 * np.pi * f_int * t)
    # 2nd-order 1-bit modulator (Boser-Wooley, 0.5 gains)
    bits = np.empty(clocks, dtype=int)
    i1 = i2 = 0.0
    for idx, xv in enumerate(x):
        y = 1.0 if i2 >= 0 else -1.0
        i1 += 0.5 * (xv - y)
        i2 += 0.5 * (i1 - y)
        bits[idx] = 1 if y > 0 else 0
    out = []
    dut.adc_valid.value = 1
    for b in bits:
        dut.adc_bit_i.value = int(b)
        dut.adc_bit_q.value = int(b)
        await RisingEdge(dut.clk)
        if int(dut.cal_v.value):
            out.append(int(dut.cal_i.value.to_signed()))
    dut.adc_valid.value = 0
    assert len(out) >= n + skip, len(out)
    seg = np.array(out[skip:skip + n], dtype=float)
    spec = np.abs(np.fft.rfft(seg - seg.mean())) * 2 / n
    gain_db = 20 * np.log10(spec[k_sig] / (a_sig * FS))
    rej_db = 20 * np.log10((spec[k_sig] / a_sig) / (spec[k_alias] / a_int))
    cocotb.log.info(
        "RX tone %.2f codes, gain %.2f dB vs full scale, alias rejection %.1f dB, peak %d",
        spec[k_sig], gain_db, rej_db, int(np.max(np.abs(seg))))
    assert abs(gain_db) <= 1.0, gain_db
    assert rej_db >= ALIAS_LIMIT_DB, rej_db


@cocotb.test()
async def i2s_slave_philips(dut):
    """Slave mode: a host drives Philips I2S from its own clock; check both words."""
    await start(dut)
    await spi_xfer(dut, 0x08, 0x06, write=True)    # bypass DC loop and IQ cal
    await spi_xfer(dut, 0x03, 4, write=True)       # 500 kHz
    await spi_xfer(dut, 0x00, 0x12, write=True)    # RX, I2S slave
    dut.adc_bit_i.value = 1                        # I = +full scale
    dut.adc_bit_q.value = 0                        # Q = -full scale
    dut.adc_valid.value = 1
    for _ in range(64 * 50):
        await RisingEdge(dut.clk)
    half = 31.2                                    # host BCLK ~16.03 MHz, not locked to clk
    samples = []
    for frame in range(24):
        for cell in range(32):
            dut.bclk_i.value = 0                   # falling edge: host changes LRCLK and DIN
            dut.lrclk_i.value = 0 if cell < 16 else 1
            dut.din.value = 0
            await Timer(half, unit="ns")
            samples.append(int(dut.dout.value))    # host samples at the rising edge
            dut.bclk_i.value = 1
            await Timer(half, unit="ns")
    dut.adc_valid.value = 0

    def word(bits):
        w = 0
        for b in bits:
            w = (w << 1) | b
        return w - 65536 if w & 0x8000 else w

    f = 20 * 32
    left = word(samples[f + 1:f + 17])
    right = word(samples[f + 17:f + 33])
    cocotb.log.info("slave left %d right %d", left, right)
    assert abs(left - FS) <= FS_TOL, left
    assert abs(right + FS) <= FS_TOL, right
