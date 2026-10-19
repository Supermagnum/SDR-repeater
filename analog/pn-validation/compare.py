#!/usr/bin/env python3
"""Compare VACASK pnoise with the closed form (level 1), transient noise and Leeson.

Run from this folder after run.sh. Needs vacask.rawfile on PYTHONPATH (run.sh sets it).
Pass criteria (README):
  level 1: |pnoise - closed form| <= 1 dB, |tran - closed form| <= 2 dB
  level 2: |pnoise - tran| <= 2 dB; Leeson (F = 1.5..3) is a plausibility band only
"""
import math
import os
import sys

import numpy as np
from scipy.signal import welch

import params as P


def fundamental_amplitude(t, v, npts=4096):
    """Amplitude of the first harmonic of one PSS period (non-uniform time points)."""
    t = np.real(np.asarray(t)); v = np.real(np.asarray(v))
    period = t[-1] - t[0]
    tu = t[0] + np.arange(npts) * period / npts
    vu = np.interp(tu, t, v)
    spec = np.fft.rfft(vu) / npts
    return 2 * abs(spec[1]), 1.0 / period


def pnoise_dbc(onoise, amp):
    """onoise is a one-sided PSD at f0+df; PM noise gives S = (A^2/2) L(df)."""
    return 10 * np.log10(np.real(onoise) / (amp * amp / 2))


def _phase_diff(t, v, settle):
    """Uniformly resampled first difference of the carrier phase.

    The analytic signal is formed from the band 0.75-1.25 f0 only, so harmonics and
    DC (which would turn into fast phase ripple) are removed before the phase is taken.
    """
    t = np.real(np.asarray(t)); v = np.real(np.asarray(v))
    keep = t >= t[0] + settle
    t, v = t[keep], v[keep]
    # Fixed 5 ps grid: adaptive steps can make the median step much smaller and the
    # arrays too large; 5 ps is still >50 points per period at 3.7 GHz.
    dt = max(float(np.median(np.diff(t))), 5e-12)
    tu = np.arange(t[0], t[-1], dt)
    vu = np.interp(tu, t, v)
    del t, v
    spec = np.fft.fft(vu)
    f = np.fft.fftfreq(len(vu), dt)
    pos = f > 0
    f0 = f[pos][np.argmax(np.abs(spec[pos]))]
    band = (f >= 0.75 * f0) & (f <= 1.25 * f0)
    analytic = np.fft.ifft(np.where(band, 2 * spec, 0))
    dphi = np.diff(np.unwrap(np.angle(analytic)))
    # The band filter acts on a non-periodic record: drop the ringing at both ends.
    edge = len(dphi) // 20
    return dphi[edge:len(dphi) - edge], dt


def tran_phase_noise_dbc(t, v, offsets, settle=0.5e-6, rel_bw=0.2):
    """L(df) from a noisy transient: analytic-signal phase, Welch PSD, L = S_phi / 2."""
    dphi, dt = _phase_diff(t, v, settle)
    nper = 2 ** int(math.floor(math.log2(len(dphi) / 4)))
    f, s_d = welch(dphi, fs=1 / dt, nperseg=nper, window="hann", detrend="constant")
    with np.errstate(divide="ignore", invalid="ignore"):
        s_phi = s_d / (2 * np.sin(np.pi * f * dt)) ** 2
    out = []
    for df in offsets:
        m = (f >= df * (1 - rel_bw)) & (f <= df * (1 + rel_bw))
        out.append(10 * math.log10(np.mean(s_phi[m]) / 2) if m.any() else float("nan"))
    return np.array(out), f[1] - f[0]


def tran_fit_at_1mhz(t, v, fa=2e6, fb=20e6, settle=0.5e-6, nseg=16):
    """Fit L(df) = c / df^2 to transient phase noise over [fa, fb]; return L at 1 MHz (dBc/Hz).

    Many short Welch segments and many bins make this far steadier than single bins.
    """
    dphi, dt = _phase_diff(t, v, settle)
    nper = 2 ** int(math.floor(math.log2(len(dphi) / nseg)))
    f, s_d = welch(dphi, fs=1 / dt, nperseg=nper, window="hann", detrend="constant")
    m = (f >= fa) & (f <= fb)
    s_phi = s_d[m] / (2 * np.sin(np.pi * f[m] * dt)) ** 2
    c = np.mean(s_phi * f[m] ** 2) / 2            # L(df) * df^2
    return 10 * math.log10(c / 1e12), int(m.sum())


def model_fit_at_1mhz(off, l_dbc, fa=2e6, fb=20e6):
    """Same normalisation for pnoise/closed-form values: mean of L*df^2 over [fa, fb], at 1 MHz."""
    off = np.asarray(off); m = (off >= fa) & (off <= fb)
    c = np.mean(10 ** (np.asarray(l_dbc)[m] / 10) * off[m] ** 2)
    return 10 * math.log10(c / 1e12)


def table(title, rows, cols):
    print(f"\n{title}")
    print("  offset    " + "".join(f"{c:>14s}" for c in cols))
    for df, vals in rows:
        print(f"  {df/1e6:6.2f} MHz" + "".join(f"{x:14.1f}" for x in vals))


def main():
    from vacask.rawfile import rawread
    ok = True

    # Level 1
    pss = rawread("pn1.pss.raw").get()
    a1, f0 = fundamental_amplitude(pss["time"], pss["t"])
    pn = rawread("pn1.raw").get()
    off = np.real(pn["frequency"])
    lpn = pnoise_dbc(pn["onoise"], a1)
    lcf = np.array([P.lc_closed_form_dbc(d, a1) for d in off])
    print(f"Level 1: f0 = {f0/1e9:.4f} GHz (ideal {P.f0_level1()/1e9:.4f}), A1 = {a1:.4f} V")
    cols, rows = ["closed form", "pnoise", "pn - cf"], []
    have_tran = os.path.exists("tn1.raw")
    if have_tran:
        tr = rawread("tn1.raw").get()
        ltr, res = tran_phase_noise_dbc(tr["time"], tr["t"], off)
        cols += ["tran", "tran - cf"]
        print(f"  transient-noise resolution {res/1e3:.0f} kHz")
    for i, d in enumerate(off):
        r = [lcf[i], lpn[i], lpn[i] - lcf[i]]
        if have_tran:
            r += [ltr[i], ltr[i] - lcf[i]]
        rows.append((d, r))
    table("Level 1, L(df) in dBc/Hz", rows, cols)
    e1 = np.max(np.abs(lpn - lcf))
    print(f"  max |pnoise - closed form| = {e1:.2f} dB  {'PASS' if e1 <= 1 else 'FAIL'} (<= 1 dB)")
    ok &= e1 <= 1
    if have_tran:
        lfit, nb = tran_fit_at_1mhz(tr["time"], tr["t"])
        lcf1 = P.lc_closed_form_dbc(1e6, a1)
        e1t = abs(lfit - lcf1)
        print(f"  1/df^2 fit of transient noise (2-20 MHz, {nb} bins), at 1 MHz: {lfit:.2f} dBc/Hz"
              f" vs closed form {lcf1:.2f}: diff {lfit - lcf1:+.2f} dB  {'PASS' if e1t <= 1 else 'FAIL'} (<= 1 dB)")
        ok &= e1t <= 1

    # Level 2 (optional: only if it was run)
    if os.path.exists("pn2.raw"):
        pss = rawread("pn2.pss.raw").get()
        a2, f2 = fundamental_amplitude(pss["time"], np.real(pss["vp"]) - np.real(pss["vm"]))
        pn = rawread("pn2.raw").get()
        off2 = np.real(pn["frequency"])
        lpn2 = pnoise_dbc(pn["onoise"], a2)
        w0 = 2 * math.pi * f2
        rp_side = (w0 * P.L2_L) ** 2 / P.L2_RS
        q = rp_side / (w0 * P.L2_L)
        psig = a2 ** 2 / 2 / (2 * rp_side)            # differential amplitude into 2 Rp
        lo = [P.leeson_dbc(d, f2, q, psig, 1.5) for d in off2]
        hi = [P.leeson_dbc(d, f2, q, psig, 3.0) for d in off2]
        print(f"\nLevel 2: f0 = {f2/1e9:.4f} GHz, differential A1 = {a2:.4f} V, tank Q = {q:.1f}")
        cols, rows = ["Leeson F=1.5", "Leeson F=3", "pnoise"], []
        have_tran2 = os.path.exists("tn2.raw")
        if have_tran2:
            tr = rawread("tn2.raw").get()
            ltr2, _ = tran_phase_noise_dbc(tr["time"], np.real(tr["vp"]) - np.real(tr["vm"]), off2)
            cols += ["tran", "pn - tran"]
        for i, d in enumerate(off2):
            r = [lo[i], hi[i], lpn2[i]]
            if have_tran2:
                r += [ltr2[i], lpn2[i] - ltr2[i]]
            rows.append((d, r))
        table("Level 2, L(df) in dBc/Hz", rows, cols)
        if have_tran2:
            lfit2, nb = tran_fit_at_1mhz(tr["time"], np.real(tr["vp"]) - np.real(tr["vm"]))
            lpnfit = model_fit_at_1mhz(off2, lpn2)
            e2 = abs(lpnfit - lfit2)
            print(f"  1/df^2 level at 1 MHz (fit 2-20 MHz): pnoise {lpnfit:.2f}, transient {lfit2:.2f} ({nb} bins):"
                  f" diff {lpnfit - lfit2:+.2f} dB  {'PASS' if e2 <= 1.5 else 'FAIL'} (<= 1.5 dB)")
            ok &= e2 <= 1.5
        inband = np.mean((lpn2 >= np.array(lo) - 3) & (lpn2 <= np.array(hi) + 3))   # F=1.5 is the lower edge
        print(f"  pnoise within Leeson band +-3 dB at {inband*100:.0f} % of offsets (plausibility only)")

    print("\nOVERALL", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
