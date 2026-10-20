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


# Level 3: level 1 with a varactor driven by a pure 1/f noise voltage (flicker -> FM path)
L3_CV0 = 0.2e-12              # F, varactor at V(ctl) = 0 (fixed part L1_C - L3_CV0)
L3_KC = 0.1e-12               # F/V, varactor slope
L3_KF = 1e-10                 # V^2, S_v(f) = L3_KF / f at the control node
OFFSETS_FLICKER = [1e4, 3e4, 1e5, 3e5, 6e5, 1e6, 2e6, 5e6, 1e7, 2e7]


def kvco_level3(f0):
    """Tuning gain in Hz/V: df0/dVctl = -f0 * KC / (2 C). The sign does not matter."""
    return f0 * L3_KC / (2 * L1_C)


def flicker_fm_closed_form_dbc(df, amp, f0):
    """Level 3 exact answer: thermal (level 1) plus FM by the 1/f control voltage.

    Frequency-noise PSD S_f = K^2 S_v(df); phase PSD S_phi = S_f / df^2; L = S_phi / 2.
    """
    k = kvco_level3(f0)
    l_th = 10 ** (lc_closed_form_dbc(df, amp) / 10)
    l_fl = k * k * L3_KF / df / (2 * df * df)
    return 10 * math.log10(l_th + l_fl)
