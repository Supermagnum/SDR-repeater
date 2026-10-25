#!/usr/bin/env python3
"""P2.5 step 3: fractional spur from the charge-pump nonlinearity, in a cycle-by-cycle PLL model.

The linear P2.2 model takes the raw boundary spur S0 as an input (budget: S0 <= -35 dBc at VHF). Here the spur
is computed instead: a discrete-time phase-domain PLL, one step per reference cycle, with
  - the real divider sequence: Sigma-Delta MASH 1-1-1 (bit-exact model of rtl/afe/sdm.sv, models.py) on
    M = N / P (D16), the VCO counted in P x div_n cycles per reference cycle;
  - the charge pump as measured: Q = I_cp * (dt + inl(dt)) - I_off * T_ref, where inl(dt) is the deviation
    of the transistor-level Q(dt) curve from a straight line (step 2a / step 3 Monte Carlo, dt 1-5 ns);
  - the P2.2 loop filter (C1 || (R1 + C2), R3-C3) solved exactly between charge packets, VCO gain K_VCO.
The VCO phase error is sampled once per cycle; its spectrum gives the spur at the boundary-channel offset
(the duplex offset: 600 kHz VHF, 2 MHz UHF), referred to RF by -20 log10(D). Limit at RF: -95 dBc.

    python3 pll_behav.py                      # self-check: linear pump (no spur) and a synthetic INL
    (run_step3.py spur calls spur() with the measured curves)
"""
import math
import os
import sys

import numpy as np
from scipy.linalg import expm

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "rtl", "afe", "cocotb"))
sys.path.insert(0, os.path.join(REPO, "analog", "pll-model"))
import models  # noqa: E402
import pll_model  # noqa: E402

F_REF = 36e6
BANDS = {"VHF": dict(D=24, P=3, dup=0.6e6), "UHF": dict(D=8, P=2, dup=2.0e6)}
LIM_RF = -95.0
LOOP_BW = 60e3


def spur(band, inl=None, f_vco_approx=3.6e9, icp=50e-6, kvco=40e6, off_frac=0.1, cycles=1 << 16, warm=4000):
    """Spur (dBc at RF) at the boundary offset for one band. inl: callable dt[s] -> deviation[s] or None."""
    b = BANDS[band]
    T = 1 / F_REF
    P, D = b["P"], b["D"]
    # channel: VCO a little above an integer multiple of P x f_ref, so that frac(M) x f_ref = duplex offset
    m_int = int(f_vco_approx / F_REF / P)
    frac_m = b["dup"] / F_REF
    m_full = int(round((m_int + frac_m) * 2 ** 24))
    n_seq = models.sdm(m_full, cycles + warm + 10)
    n_fb = P * (m_full / 2 ** 24)
    # P2.6 step 1: loop filter of the corrected design (D19 proposal, 60 kHz, 55 deg actual; design_loop fixed)
    lf = pll_model.design_loop(LOOP_BW, 62.0, kvco, icp, n_fb)
    c1, c2, r1, r3, c3 = lf["C1"], lf["C2"], lf["R1"], lf["R3"], lf["C3"]
    i_off = off_frac * icp
    # state x = [v1, v2, v3, 1]; offset current as a constant input into node 1
    A = np.array([[-1 / (r1 * c1) - 1 / (r3 * c1), 1 / (r1 * c1), 1 / (r3 * c1), -i_off / c1],
                  [1 / (r1 * c2), -1 / (r1 * c2), 0, 0],
                  [1 / (r3 * c3), 0, -1 / (r3 * c3), 0],
                  [0, 0, 0, 0]])
    # exact propagation over T and the integral of v3 over T (augmented exponential)
    Ab = np.zeros((8, 8))
    Ab[:4, :4] = A
    Ab[:4, 4:] = np.eye(4)
    E = expm(Ab * T)
    Phi, Gam = E[:4, :4], E[:4, 4:]          # x(T) = Phi x(0); int_0^T x dt = Gam x(0)
    f_target = n_fb * F_REF                  # VCO frequency the loop must reach
    v0 = 0.6
    f_free = f_target                        # VCO frequency at v3 = v0 (the loop only corrects drift)
    x = np.array([v0, v0, v0, 1.0])
    dt0 = i_off * T / icp
    phi = -dt0 * f_target                    # VCO phase (cycles) relative to the first divider target
    target = 0.0
    err = np.zeros(cycles)
    g = (lambda d: d + inl(d)) if inl else (lambda d: d)
    for k in range(cycles + warm):
        f_now = f_free + kvco * (x[2] - v0)
        dt = (target - phi) / f_now          # divider edge after the reference edge -> UP
        q = icp * g(dt)
        x = x.copy()
        x[0] += q / c1
        xi = Gam @ x
        x = Phi @ x
        phi += f_free * T + kvco * (xi[2] - v0 * T)
        target += P * n_seq[k]
        if k >= warm:
            # VCO phase error against the ideal ramp at f_target (radians)
            err[k - warm] = 2 * math.pi * (phi - (k + 1) * f_target * T)
    err = err - np.polyval(np.polyfit(np.arange(cycles), err, 1), np.arange(cycles))
    w = np.hanning(cycles)
    X = np.fft.rfft(err * w)
    fr = np.fft.rfftfreq(cycles, T)
    amp = 2 * np.abs(X) / w.sum()                        # phase amplitude (rad) per bin
    k_sp = int(round(b["dup"] / (fr[1] - fr[0])))
    a_sp = amp[max(1, k_sp - 3):k_sp + 4].max()
    spur_vco = 20 * math.log10(a_sp / 2 + 1e-30)
    floor = 20 * math.log10(np.median(amp[k_sp // 2:k_sp * 2]) / 2 + 1e-30)
    return dict(band=band, spur_rf=spur_vco - 20 * math.log10(D), floor_rf=floor - 20 * math.log10(D),
                dt_mean=float(dt0), bins=fr[1] - fr[0])


def inl_from_curve(dts, qs):
    """Deviation of a measured Q(dt) (both in seconds) from its straight-line fit, as a callable."""
    dts, qs = np.asarray(dts), np.asarray(qs)
    k, c = np.polyfit(dts, qs, 1)
    dev = (qs - (k * dts + c)) / k
    return lambda d: float(np.interp(d, dts, dev))


if __name__ == "__main__":
    for band in BANDS:
        r0 = spur(band)
        r1 = spur(band, lambda d: 1e-12 * math.sin(2 * math.pi * (d - 1e-9) / 4e-9))     # 1 ps INL
        r2 = spur(band, lambda d: 1e-11 * math.sin(2 * math.pi * (d - 1e-9) / 4e-9))     # 10 ps INL
        print(f"{band}: linear pump: spur {r0['spur_rf']:.1f} dBc (floor {r0['floor_rf']:.1f}); "
              f"1 ps INL: {r1['spur_rf']:.1f}; 10 ps INL: {r2['spur_rf']:.1f} dBc at RF (limit {LIM_RF})")
