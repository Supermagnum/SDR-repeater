#!/usr/bin/env python3
"""Level 4b: deterministic check of low-frequency upconversion in the SG13G2 oscillator.

Replaces the level 4 transient-noise reference, which is impractical: with noise on, every
transistor transient (level 2 included) averages a 14 fs time step, so 80 us would take
22-37 h and about 140 GB; with noise off the same circuit runs at about 1.2 ps.

Method (all on the level 4 circuit, real MOS tail, injection at the tail bias node nb):
  1. pnoise (pss_minpts 16000) without and with an extra noise current into nb. The
     difference is the output sideband PSD caused by a current at nb: onoise_inj(df) =
     |H(df)|^2 S_i(df). The injected current must be band-limited (S_i = 9/f^2 A^2/Hz):
     a white source also has power near 2 f0 +- df, which the tail mixes into the same
     sideband (first run: 2.6-2.9 dB high at every tone). The white prediction is still
     printed for comparison.
  2. A noiseless transient with three small sine currents into nb (300 kHz, 1 MHz, 3 MHz),
     each sized for an upper sideband of about -50 dBc predicted from step 1.
     Linearity: a tone of amplitude Ia carries power Ia^2/2, so the predicted upper sideband
     is  USB/carrier = L_inj(fm) * (Ia^2/2) / S_i.
  3. The transient's upper sidebands at f0 + fm are measured with a flat-top window on the
     differential output (40 us after 2 us settling, 25 kHz bins).
Pass: measured and predicted upper sidebands agree within 1 dB at each tone.

This tests exactly what the flicker region depends on (the periodic transfer from a
low-frequency current to the carrier sidebands) with the real transistors; Level 3 already
tested the same path exactly against a closed form. It does not test the device flicker
noise magnitude, which is PDK model data.

Run inside the container from this folder:  ./run.sh inject   (about 20-40 min)
"""
import math
import os
import re
import subprocess
import sys

import numpy as np
from scipy.signal.windows import flattop

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "inject")
S_I = 1e-12                       # A^2/Hz, injected white noise current (pnoise only)
K_FN = 9.0                        # A^2: band-limited injection S_i(f) = K_FN / f^2 (1e-12 at 3 MHz)


def S_I_FN(f):
    return K_FN / (f * f)
TONES = [3e5, 1e6, 3e6]           # Hz
USB_TARGET = -50.0                # dBc, predicted upper sideband per tone
T_SETTLE, T_REC = 2e-6, 40e-6     # s
LIMIT = 1.0                       # dB

VA_NOISE = '''embed "injnoise.va" <<<FILE
`include "constants.vams"
`include "disciplines.vams"
module injnoise(A, B);
    inout A, B;
    electrical A, B;
    analog begin
        I(A, B) <+ 0;
        I(A, B) <+ %s;
    end
endmodule
>>>FILE
load "injnoise.va"
model injnoise injnoise
'''

VA_TONE = '''embed "injtone.va" <<<FILE
`include "constants.vams"
`include "disciplines.vams"
module injtone(A, B);
    inout A, B;
    electrical A, B;
    analog begin
        I(A, B) <+ %s;
    end
endmodule
>>>FILE
load "injtone.va"
model injtone injtone
'''


def vacask(sim):
    log = sim.replace(".sim", ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", sim], stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        print(open(log).read()[-2000:])
        sys.exit(f"vacask {sim} failed (exit {r.returncode}), see out/inject/{log}")


def insert_after_loads(text, block):
    i = text.index('load "inductor.osdi"\n') + len('load "inductor.osdi"\n')
    return text[:i] + "\n" + block + text[i:]


def pnoise_netlist(base, name, inject):
    t = base.replace("pss_minpts=64000", "pss_minpts=16000")
    t = re.sub(r"analysis pn4 pnoise", f"analysis {name} pnoise", t)
    t = re.sub(r"values=\[[^\]]*\]", "values=[" + ", ".join(f"{f:.0f}.0" for f in TONES) + "]", t)
    if inject:
        src = (f'white_noise({S_I:g}, "inj")' if inject == "white"
               else f'flicker_noise({K_FN:g}, 2.0, "inj")')
        t = insert_after_loads(t, VA_NOISE % src)
        t = t.replace("// Start-up kick", "ninj (0 nb) injnoise\n// Start-up kick")
    return t


def tone_netlist(base, amps):
    expr = " + ".join(f"{a:.6e} * sin(2 * `M_PI * {f:.0f}.0 * $abstime)" for f, a in zip(TONES, amps))
    t = insert_after_loads(base, VA_TONE % expr)
    t = t.replace("// Start-up kick", "xinj (0 nb) injtone\n// Start-up kick")
    stop = (T_SETTLE + T_REC) * 1e6 + 0.1
    t = re.sub(r"analysis tn4 tran stop=80\.5u .*", f"analysis tone tran stop={stop:.1f}u step=5p maxstep=5p "
               'ic="ss" icmode="uic"', t)
    t = t.replace("transient-noise reference (slow: 1-3 h)", "deterministic tone injection at nb (level 4b)")
    return t


def onoise(rawread, name):
    d = rawread(name + ".raw").get()
    return np.real(d["frequency"]), np.real(d["onoise"])


def predicted_gain(rawread, a, name):
    """g(fm) = sideband power / carrier power per A^2 of tone power at nb (1/A^2)."""
    f, on_r = onoise(rawread, "pn4r")
    _, on_x = onoise(rawread, name)
    excess = on_x / on_r
    if np.any(excess < 10):
        sys.exit(f"{name}: injected noise only {10*np.log10(excess.min()):.1f} dB above the circuit noise")
    s_i = np.array([S_I_FN(fm) if name == "pn4b" else S_I for fm in f])
    return f, (on_x - on_r) / (a * a / 2) / s_i, excess


def main():
    sys.path.insert(0, HERE)
    from vacask.rawfile import rawread
    from compare import fundamental_amplitude
    os.makedirs(OUT, exist_ok=True)
    os.chdir(OUT)
    base_pn = open(os.path.join(HERE, "level4_sg13_tail.sim")).read()
    base_tr = open(os.path.join(HERE, "level4_tran.sim")).read()

    # 1. pnoise: reference, white injection (pn4i) and band-limited 1/f^2 injection (pn4b)
    for name, inj in (("pn4r", None), ("pn4i", "white"), ("pn4b", "lowpass")):
        open(name + ".sim", "w").write(pnoise_netlist(base_pn, name, inj))
        print(f"== vacask {name}.sim")
        vacask(name + ".sim")
    pss = rawread("pn4b.pss.raw").get()
    a, f0 = fundamental_amplitude(pss["time"], np.real(pss["vp"]) - np.real(pss["vm"]))
    f, g_w, ex_w = predicted_gain(rawread, a, "pn4i")
    _, g_b, ex_b = predicted_gain(rawread, a, "pn4b")
    print(f"pnoise: f0 {f0/1e9:.4f} GHz, A1 {a:.4f} V; injected noise above the circuit's own: "
          f"white {10*np.log10(ex_w.min()):.0f} dB, 1/f^2 {10*np.log10(ex_b.min()):.0f} dB (minimum)")

    # 2. noiseless transient with the tones (reused if it already exists)
    if os.path.exists("tone.raw") and os.path.exists("tone.sim"):
        expr = open("tone.sim").read()
        amps = {float(fm): float(ia) for ia, fm in
                re.findall(r"([0-9.]+e[+-][0-9]+) \* sin\(2 \* `M_PI \* ([0-9.]+) \* \$abstime\)", expr)}
        amps = [amps[fm] for fm in TONES]
        print("== reusing tone.sim / tone.raw from the previous run")
    else:
        amps = [math.sqrt(2 * 10 ** (USB_TARGET / 10) / gb) for gb in g_b]
        open("tone.sim", "w").write(tone_netlist(base_tr, amps))
        print("== vacask tone.sim (noiseless transient, about 15-30 min)")
        vacask("tone.sim")

    # 3. measure the sidebands
    d = rawread("tone.raw").get()
    t = np.real(d["time"]); v = np.real(d["vp"]) - np.real(d["vm"])
    dt = 5e-12
    tu = np.arange(T_SETTLE, T_SETTLE + T_REC, dt)
    vu = np.interp(tu, t, v)
    del t, v, d
    w = flattop(len(vu), sym=False)
    spec = np.abs(np.fft.rfft(vu * w))
    fr = np.fft.rfftfreq(len(vu), dt)
    df = fr[1]
    kc = int(np.argmax(spec * (fr > 0.5 * f0)))
    carrier = spec[kc]
    fc = fr[kc]
    print(f"transient: carrier {fc/1e9:.4f} GHz, resolution {df/1e3:.0f} kHz")
    print("  tone    amplitude   pred. (white inj.)   pred. (1/f^2 inj.)   measured USB   measured LSB"
          "   USB - pred. (1/f^2)")
    ok = True
    for fm, ia, gw, gb in zip(TONES, amps, g_w, g_b):
        def side(sign):
            k = int(round((fc + sign * fm - fr[0]) / df))
            return 20 * math.log10(spec[k - 3:k + 4].max() / carrier)
        usb, lsb = side(+1), side(-1)
        pw, pb = 10 * math.log10(gw * ia * ia / 2), 10 * math.log10(gb * ia * ia / 2)
        diff = usb - pb
        good = abs(diff) <= LIMIT
        ok &= good
        print(f"  {fm/1e6:4.2f} MHz {ia*1e9:8.2f} nA   {pw:12.2f} dBc   {pb:14.2f} dBc   {usb:9.2f} dBc   "
              f"{lsb:9.2f} dBc   {diff:+8.2f} dB  {'PASS' if good else 'FAIL'}")
    print("\nThe white-noise prediction also counts nb noise near 2 f0 +- fm (and other harmonics), which the")
    print("tail mixes into the same sideband; a low-frequency tone has none. The 1/f^2 source is band-limited.")
    print(f"\nLEVEL 4b {'PASS' if ok else 'FAIL'} (|measured - predicted with 1/f^2 injection| <= {LIMIT} dB at each tone)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
