#!/usr/bin/env python3
"""Flicker-region validation of VACASK pnoise (levels 3 and 4). Run from out/ after run.sh.

Level 3 (exact): pnoise vs closed form, thermal + 1/f FM through a varactor, 10 kHz-20 MHz.
         pnoise is run with pss_minpts 16000 (pn3) and 64000 (pn3h). Pass: the 64000 run is
         within 1 dB of the closed form at every offset. The 16000 run is reported per offset
         as converged where it agrees with 64000 within 0.3 dB. First run (2026-10-20):
         16000 points are 1.9 dB low at 10 kHz and converged from 30 kHz; at 100 kHz Level 1
         showed the same pattern with 1000-4000 points. The error depends on pss_minpts x df.
Level 4 (SG13G2, real MOS tail): L(df) = a/df^3 + b/df^2 fitted to pnoise and, if run, to
         transient noise (50 kHz-20 MHz). Pass: the two fits agree within 1.5 dB at 600 kHz
         (duplex offset) and 1 MHz, and within 2.5 dB at 100 kHz. Synthetic check of the
         transient method (80 us, 2 segments, 6 seeds, corner 300 kHz): bias < 0.05 dB,
         scatter (1 sigma) 0.9 / 0.37 / 0.25 dB at 100 kHz / 600 kHz / 1 MHz.
"""
import math
import os
import sys

import numpy as np
from scipy.signal import welch

import params as P
from compare import _phase_diff, fundamental_amplitude, pnoise_dbc, table

CHECK_AT = {1e5: 2.5, 6e5: 1.5, 1e6: 1.5}   # offset: limit (dB)


def fit_flicker_thermal(df, s, w=None):
    """Least-squares fit of S(df) = a/df^3 + b/df^2 in linear power.

    Written as y = S df^2 = a/df + b (linear in a, b), reweighted by 1/model^2 so every
    offset has the same relative weight (unbiased for averaged periodogram bins).
    """
    df = np.asarray(df, float); y = np.asarray(s, float) * df ** 2
    x = 1.0 / df
    w = np.ones_like(y) if w is None else np.asarray(w, float)
    a = b = 0.0
    for _ in range(5):
        A = np.vstack([x, np.ones_like(x)]).T * np.sqrt(w)[:, None]
        a, b = np.linalg.lstsq(A, y * np.sqrt(w), rcond=None)[0]
        model = np.maximum(a * x + b, 1e-300)
        w = 1.0 / model ** 2
    return a, b


def model_dbc(a, b, df):
    return 10 * math.log10(a / df ** 3 + b / df ** 2)


def tran_spectrum(t, v, fa=5e4, fb=2e7, nseg=2, settle=0.5e-6):
    """Transient phase noise L(df) per Welch bin (linear, 1/Hz) in [fa, fb]."""
    dphi, dt = _phase_diff(t, v, settle)
    nper = len(dphi) // nseg          # no power-of-two rounding: keeps the resolution
    f, s_d = welch(dphi, fs=1 / dt, nperseg=nper, noverlap=nper // 2, window="hann",
                   detrend="linear")
    m = (f >= fa) & (f <= fb)
    s_phi = s_d[m] / (2 * np.sin(np.pi * f[m] * dt)) ** 2
    return f[m], s_phi / 2, f[1] - f[0]


def level3(rawread):
    pss = rawread("pn3.pss.raw").get()
    a1, f0 = fundamental_amplitude(pss["time"], pss["t"])
    pn = rawread("pn3.raw").get()
    off = np.real(pn["frequency"])
    lpn = pnoise_dbc(pn["onoise"], a1)
    lcf = np.array([P.flicker_fm_closed_form_dbc(d, a1, f0) for d in off])
    lth = np.array([P.lc_closed_form_dbc(d, a1) for d in off])
    print(f"Level 3: f0 = {f0/1e9:.4f} GHz, A1 = {a1:.4f} V, K = {P.kvco_level3(f0)/1e6:.2f} MHz/V, "
          f"S_v = {P.L3_KF:.0e}/f V^2/Hz")
    cols = ["thermal only", "closed form", "pnoise", "pn - cf"]
    rows = [(d, [lth[i], lcf[i], lpn[i], lpn[i] - lcf[i]]) for i, d in enumerate(off)]
    ok = True
    if os.path.exists("pn3h.raw"):
        pnh = rawread("pn3h.raw").get()
        lpnh = pnoise_dbc(pnh["onoise"], a1)
        cols.append("4x pts - pn")
        for i, r in enumerate(rows):
            r[1].append(lpnh[i] - lpn[i])
    table("Level 3, L(df) in dBc/Hz", rows, cols)
    e = np.max(np.abs(lpn - lcf))
    print(f"  pss_minpts 16000: max |pnoise - closed form| = {e:.2f} dB")
    if not os.path.exists("pn3h.raw"):
        print("  64000-point run missing: level 3 judged on the 16000 run")
        ok = e <= 1
        print(f"  {'PASS' if ok else 'FAIL'} (<= 1 dB)")
        return ok
    eh = np.max(np.abs(lpnh - lcf))
    ok = eh <= 1
    print(f"  pss_minpts 64000: max |pnoise - closed form| = {eh:.2f} dB  {'PASS' if ok else 'FAIL'} (<= 1 dB)")
    conv = np.abs(lpnh - lpn) <= 0.3
    good = off[conv]
    if conv.all():
        print("  16000 points converged (<= 0.3 dB vs 64000) at every offset")
    else:
        bad = ", ".join(f"{d/1e3:.0f} kHz" for d in off[~conv])
        print(f"  16000 points NOT converged at {bad}; converged from "
              f"{good[good > off[~conv].max()].min()/1e3:.0f} kHz (product pss_minpts x df >= "
              f"{16000 * good[good > off[~conv].max()].min():.1e})")
    return ok


def level4(rawread):
    pss = rawread("pn4.pss.raw").get()
    a4, f4 = fundamental_amplitude(pss["time"], np.real(pss["vp"]) - np.real(pss["vm"]))
    pn = rawread("pn4.raw").get()
    off = np.real(pn["frequency"])
    lpn = pnoise_dbc(pn["onoise"], a4)
    m = off >= 5e4
    ap, bp = fit_flicker_thermal(off[m], 10 ** (lpn[m] / 10))
    corner_p = ap / bp if bp > 0 else float("nan")
    print(f"\nLevel 4: f0 = {f4/1e9:.4f} GHz, differential A1 = {a4:.4f} V")
    print(f"  pnoise fit a/df^3 + b/df^2 (50 kHz-20 MHz): 1/f^2 level at 1 MHz "
          f"{10*math.log10(bp/1e12):.2f} dBc/Hz, flicker corner {corner_p/1e3:.0f} kHz")
    cols, rows = ["pnoise", "pnoise fit"], []
    have_tran = os.path.exists("tn4.raw")
    if have_tran:
        tr = rawread("tn4.raw").get()
        f, lt, res = tran_spectrum(tr["time"], np.real(tr["vp"]) - np.real(tr["vm"]))
        at, bt = fit_flicker_thermal(f, lt)
        corner_t = at / bt if bt > 0 else float("nan")
        print(f"  transient fit ({len(f)} bins, {res/1e3:.0f} kHz resolution): 1/f^2 level at 1 MHz "
              f"{10*math.log10(bt/1e12):.2f} dBc/Hz, flicker corner {corner_t/1e3:.0f} kHz")
        cols += ["tran fit", "pn - tran"]
    for i, d in enumerate(off):
        r = [lpn[i], model_dbc(ap, bp, d)]
        if have_tran:
            r += [model_dbc(at, bt, d), model_dbc(ap, bp, d) - model_dbc(at, bt, d)]
        rows.append((d, r))
    table("Level 4, L(df) in dBc/Hz", rows, cols)
    rise = lpn[off == 1e5][0] - (10 * math.log10(bp / 1e10)) if (off == 1e5).any() else float("nan")
    print(f"  pnoise at 100 kHz is {rise:+.1f} dB above the 1/f^2 line"
          f" ({'flicker region visible' if rise > 3 else 'NO clear flicker region: level 4 cannot validate it'})")
    ok = rise > 3
    if have_tran:
        for d, lim in CHECK_AT.items():
            e = abs(model_dbc(ap, bp, d) - model_dbc(at, bt, d))
            print(f"  fits at {d/1e3:.0f} kHz differ by {e:.2f} dB  {'PASS' if e <= lim else 'FAIL'} (<= {lim} dB)")
            ok &= e <= lim
    else:
        print("  transient reference not run (./run.sh flicker-tran): level 4 not judged")
        ok = None
    return ok


def main():
    from vacask.rawfile import rawread
    ok3 = level3(rawread)
    ok4 = level4(rawread) if os.path.exists("pn4.raw") else None
    print("\nLEVEL 3", "PASS" if ok3 else "FAIL")
    print("LEVEL 4", "not judged" if ok4 is None else ("PASS" if ok4 else "FAIL"))
    return 0 if ok3 and ok4 is not False else 1


if __name__ == "__main__":
    sys.exit(main())
