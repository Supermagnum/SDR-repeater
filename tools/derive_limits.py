#!/usr/bin/env python3
"""Derive the RX/TX limits at the repeater duplex offsets (spec/derived-limits.md).

Part 1 (RX) uses the ideal frequency response of the decimation chain:
bit_front -> CIC1 -> CIC2 -> comp FIR -> half-band. It reports how much the
chain attenuates a duplex-offset blocker band before it lands on the wanted
channel. The wanted channel is assumed to be at DC (zero-IF).
Part 2 (TX) simulates a generic 2nd-order 1-bit sigma-delta at the core clock
and reports the noise at the duplex offsets. Replace this with a bitstream
captured from tx_image_and_noise when it becomes available.

Usage:
  python3 tools/derive_limits.py [--no-tx] [--hb=c0,c1,...] [--no-hb]
The half-band taps from fir_seq.sv are built in. --hb= overrides them (use the '='
form, because the first tap is negative). --no-hb leaves the half-band out.
"""
import argparse
import numpy as np

BF = np.array([1, 4, 8, 12, 12, 8, 4, 1], float)
COMP = np.array([-5006, 32767, -5006], float)
_HB_HALF = [-138, 0, 305, 0, -617, 0, 1128, 0, -1952, 0, 3376, 0, -6450, 0, 20688]  # fir_seq.sv hb_c
HB_RTL = np.array(_HB_HALF + [32767] + _HB_HALF[::-1], float)
PAIRS = {  # name: (clk, frame_clks, r0, r1, r2) -- from rate_table.sv
    "32M r0": (32e6, 1280, 4, 10, 16), "32M r1": (32e6, 640, 4, 8, 10),
    "32M r2": (32e6, 320, 4, 5, 8), "32M r3": (32e6, 160, 4, 4, 5),
    "32M r4": (32e6, 64, 4, 2, 4),
    "36M r0": (36e6, 1440, 4, 12, 15), "36M r1": (36e6, 720, 4, 9, 10),
    "36M r2": (36e6, 360, 4, 5, 9), "36M r3": (36e6, 180, 2, 5, 9),
    "36M r4": (36e6, 72, 4, 3, 3),
}
OFFSETS = (0.6e6, 2.0e6)   # Norwegian list: 2 m -600 kHz (112), 70 cm -2 MHz (104)
CH_HALF = 5.5e3            # occupied half-bandwidth of a 12.5 kHz FM channel


def fir(f, fs, taps):
    k = np.arange(len(taps))
    return np.abs(np.exp(-2j * np.pi * np.outer(f, k) / fs) @ taps) / abs(taps.sum())


def cic4(f, fs, r):
    x = np.pi * f / fs
    den = r * np.sin(x)
    with np.errstate(invalid="ignore", divide="ignore"):
        h = np.where(np.abs(den) < 1e-15, 1.0, np.sin(r * x) / den)
    return np.abs(h) ** 4


def chain(f, p, hb):
    clk, frame, r0, r1, r2 = p
    f1 = clk / r0
    f2 = f1 / r1
    f3 = f2 / r2                      # = 2 * fout
    h = fir(f, clk, BF) * cic4(f, f1, r1) * cic4(f, f2, r2) * fir(f, f3, COMP)
    if hb is not None:
        h = h * fir(f, f3, hb)
    return h


def rx_table(hb):
    d = np.linspace(-CH_HALF, CH_HALF, 401)
    print("RX: attenuation of a duplex-offset blocker band relative to the wanted channel")
    print(f"{'pair':7s} {'fout':>6s}  " + "  ".join(
        f"[{o/1e6:.1f} MHz] lands   avg  worst" for o in OFFSETS))
    for name, p in PAIRS.items():
        fo = p[0] / p[1]
        ref = np.mean(chain(d, p, hb) ** 2)
        cols = []
        for off in OFFSETS:
            land = ((-off + fo / 2) % fo) - fo / 2
            h2 = chain(off + d, p, hb) ** 2
            on = abs(land) < CH_HALF
            tag = "on-ch" if on else f"{land/1e3:+.0f}k"
            cols.append(f"{tag:>17s} {10*np.log10(ref/h2.mean()):5.0f} {10*np.log10(ref/h2.max()):6.0f}")
        print(f"{name:7s} {fo/1e3:5.0f}k  " + "  ".join(cols))
    print("'on-ch' = blocker aliases onto the wanted channel; otherwise it lands at the"
          " listed offset, where host-side channel filtering removes it.\n")


def tx_noise(fs=32e6, amp=0.5, n=1 << 21):
    k = np.arange(n)
    f0 = fs * round(5e3 / fs * n) / n
    x = amp * np.cos(2 * np.pi * f0 * k / fs)
    y = np.empty(n)
    i1 = i2 = yp = 0.0
    for j in range(n):
        i1 += x[j] - yp
        i2 += i1 - yp
        yp = 1.0 if i2 >= 0 else -1.0
        y[j] = yp
    w = np.blackman(n)
    p = np.abs(np.fft.rfft(y * w)) ** 2 / (np.sum(w ** 2) * fs) * 2
    f = np.fft.rfftfreq(n, 1 / fs)
    car = np.sum(p[np.abs(f - f0) < 200]) * fs / n
    print("TX: generic 2nd-order 1-bit sigma-delta at 32 MHz, -6 dBFS tone")
    for off in OFFSETS:
        m = np.abs(f - (f0 + off)) < 20e3
        print(f"  {off/1e6:.1f} MHz offset: {10*np.log10(p[m].mean()/car):6.1f} dBc/Hz")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hb", help="comma-separated half-band taps (use --hb=...)")
    ap.add_argument("--no-hb", action="store_true")
    ap.add_argument("--no-tx", action="store_true")
    a = ap.parse_args()
    hb = None if a.no_hb else (np.array([float(v) for v in a.hb.split(",")]) if a.hb else HB_RTL)
    rx_table(hb)
    if not a.no_tx:
        tx_noise()
