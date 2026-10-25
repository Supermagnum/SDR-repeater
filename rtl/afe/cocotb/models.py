"""Python reference models for the AFE/LO RTL (P2.5 step 2c)."""


def m_full(n_int, n_frac, p3):
    """M = {N_INT, N_FRAC} / P as 7.24 fixed point (integer division, as the RTL)."""
    return ((n_int << 24) | n_frac) // (3 if p3 else 2)


def sdm(m, cycles, dither=True, mash=True):
    """Bit-exact MASH 1-1-1 sequence of div_n for a constant M (accumulators and LFSR from reset values)."""
    a1 = a2 = a3 = 0
    c2d = c3d = c3dd = 0
    lfsr = 0x5A5A5
    mint, mfrac = m >> 24, m & 0xFFFFFF
    out = []
    for _ in range(cycles):
        d = (lfsr & 1) if dither else 0
        s1 = a1 + mfrac + d
        s2 = a2 + (s1 & 0xFFFFFF)
        s3 = a3 + (s2 & 0xFFFFFF)
        c1, c2, c3 = s1 >> 24, s2 >> 24, s3 >> 24
        y = c1 + c2 - c2d + c3 - 2 * c3d + c3dd
        out.append(mint + y if mash else mint)
        a1, a2, a3 = s1 & 0xFFFFFF, s2 & 0xFFFFFF, s3 & 0xFFFFFF
        c3dd, c3d, c2d = c3d, c3, c2
        lfsr = (((lfsr & 1) ^ ((lfsr >> 5) & 1)) << 22) | (lfsr >> 1)
    return out


def f_vco(code):
    """VCO model for the calibration test: 4.41 GHz at code 0 to 2.90 GHz at code 127, C linear in code."""
    return 4.41e9 / (1 + code * ((4.41 / 2.90) ** 2 - 1) / 127) ** 0.5


def f_vco8(code):
    """8-bit bank (D20): the same 2.90-4.41 GHz range in 256 codes."""
    return f_vco(code * 127 / 255)
