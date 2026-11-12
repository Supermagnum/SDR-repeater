"""cocotb: D24 3→7 thermometer decoder — all 256 VCO_BAND codes."""
import cocotb
from cocotb.triggers import Timer


def expect(code):
    bin_bits = code & 0x1F
    msb = (code >> 5) & 0x7
    therm = 0
    for i in range(7):
        if msb > i:
            therm |= 1 << i
    return bin_bits, therm


@cocotb.test()
async def all_256_codes(dut):
    for code in range(256):
        dut.code.value = code
        await Timer(1, unit="ns")
        exp_bin, exp_th = expect(code)
        got_bin = int(dut.bin.value)
        got_th = int(dut.therm.value)
        assert got_bin == exp_bin, f"code={code}: bin {got_bin:#04x} != {exp_bin:#04x}"
        assert got_th == exp_th, f"code={code}: therm {got_th:#04x} != {exp_th:#04x}"
        weight = got_bin + 32 * bin(got_th).count("1")
        assert weight == code, f"code={code}: weight {weight}"
    dut._log.info("vco_band_dec: all 256 codes OK (weight == code)")
