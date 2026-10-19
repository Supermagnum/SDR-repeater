"""Shared circuit constants for the phase-noise validation (keep in sync with the .sim files)."""
import math

K = 1.380649e-23
T = 300.15                    # VACASK default 27 degC

# Level 1: ideal single-node LC tank, noisy R, noiseless tanh negative conductance
L1_L = 1e-9                   # H
L1_C = 2.0678e-12             # F  -> f0 = 3.500 GHz
L1_R = 330.0                  # ohm, Q = R/(w0 L) = 15.0
L1_GM = 2.0 / L1_R            # small-signal negative conductance, loop gain 2
L1_VL = 0.2                   # V, tanh limiting voltage

# Level 2: SG13G2 cross-coupled NMOS, ideal inductors with series loss, ideal tail
L2_L = 1e-9                   # H per side
L2_RS = 1.466                 # ohm series per side (Q = 15 at 3.5 GHz)
L2_C = 1.8e-12                # F per side to ground (devices add the rest)
L2_ITAIL = 2e-3               # A
L2_VDD = 1.2                  # V

OFFSETS = [1e5, 3e5, 6e5, 1e6, 2e6, 5e6, 1e7, 2e7]


def f0_level1():
    return 1.0 / (2 * math.pi * math.sqrt(L1_L * L1_C))


def lc_closed_form_dbc(df, amp, r=L1_R, c=L1_C):
    """Exact phase noise of an LC tank whose only noise is its parallel resistor.

    L(df) = kT / (R C^2 A^2 (2 pi df)^2); identical to Leeson with F = 1.
    """
    w = 2 * math.pi * df
    return 10 * math.log10(K * T / (r * c * c * amp * amp * w * w))


def leeson_dbc(df, f0, q, psig, f_noise):
    """Leeson without the flicker corner: (2 F k T / Psig) (f0 / (2 Q df))^2."""
    return 10 * math.log10(2 * f_noise * K * T / psig * (f0 / (2 * q * df)) ** 2)
