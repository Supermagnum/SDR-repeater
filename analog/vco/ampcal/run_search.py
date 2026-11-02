#!/usr/bin/env python3
"""D22 5-bit amplitude SAR with start-up bypass closed [SCH].

Top (bank 0) and bottom (bank 255); mos×MIM×T matrix. Reports Amp, code, times,
target-not-reached, and Amp≤1.40 V during search.

    python3 -u run_search.py | tee out/summary_search.txt
    python3 -u run_search.py quick   # tt 27 °C only
"""
import os
import re
import sys
import time

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2

A.load_sizing()
S2.OUT = A.OUT

CORNERS = [
    ("mos_tt", "cap_typ"),
    ("mos_ss", "cap_wcs"),
    ("mos_ss", "cap_bcs"),
    ("mos_ff", "cap_wcs"),
    ("mos_ff", "cap_bcs"),
]
TEMPS = (-40, 27, 85)
SETTLE = 200e-9  # with bypass closed; Ron path `[SCH]` 7τ≈11 ns


def prep(sim, bias_code):
    text = open(sim).read()
    text = re.sub(r"iref \(vdd nb\) isource dc=[^\n]+\n", A.dac_snippet(bias_code, "nb"), text)
    text = text.replace("\ncontrol\n", "\n" + A.detector_snippet(True) + "\ncontrol\n")
    # force bypass closed
    text = re.sub(r"vbptie \(vbp 0\) vsource dc=0", "vbptie (vbp 0) vsource dc=1.2", text)
    if "vbptie" not in text:
        text = text.replace("\ncontrol\n", "\nvbptie (vbp 0) vsource dc=1.2\ncontrol\n")
    open(sim, "w").write(text)


def measure(mos, cap, temp, bcode, bias, tag):
    A.set_corner(mos, cap)
    vt = S2.VTUNE_MID if bcode < 128 else 0.3
    stop = 60e-9 + SETTLE
    sim = S2.netlist(
        tag, bcode, vt, itail=A.itail(bias), bypass=True, drive_vbp=False,
        analysis=(
            f"  options temp={temp}\n"
            "  save v(tp) v(tn) v(cmp) v(vhp) v(vhn) v(vhr)\n"
            f"  analysis tr tran stop={stop:.6g} step=5p maxstep=5p"
        ),
    )
    prep(sim, bias)
    t0 = time.time()
    S2.run(sim)
    dt = time.time() - t0
    d = rawread(os.path.join(A.OUT, "tr.raw")).get()
    t = np.real(d["time"])
    m = t >= t[-1] - 10e-9
    v = np.real(d["tp"])[m] - np.real(d["tn"])[m]
    amp = float(v.max() - v.min()) / 2
    a_est = A.a_est_from_holds(
        float(np.real(d["vhp"])[m][-1]),
        float(np.real(d["vhn"])[m][-1]),
        float(np.real(d["vhr"])[m][-1]),
    )
    cmp = float(np.real(d["cmp"])[m][-1])
    high = cmp > 0.6  # Amp above target if comparator trips
    # also use a_est as backup if cmp stuck
    if abs(a_est) > 0.2:
        high = a_est > A.A_TARGET
    return dict(amp=amp, a_est=a_est, high=high, dt=dt)


def sar(mos, cap, temp, band, bcode):
    code = 0
    steps = []
    amp_peak = 0.0
    for bit in range(4, -1, -1):
        trial = code | (1 << bit)
        tag = f"sar_{mos}_{cap}_{temp}_{band}_b{bit}_c{trial}"
        r = measure(mos, cap, temp, bcode, trial, tag)
        amp_peak = max(amp_peak, r["amp"])
        # if Amp too high, clear bit; else keep
        keep = not r["high"]
        if r["amp"] > A.A_HARD:
            keep = False
        if keep:
            code = trial
        steps.append(dict(bit=bit, trial=trial, keep=keep, **r))
    # final measure
    fin = measure(mos, cap, temp, bcode, code, f"sar_{mos}_{cap}_{temp}_{band}_fin_c{code}")
    amp_peak = max(amp_peak, fin["amp"])
    tnr = (code == 31) and (fin["amp"] < A.A_TARGET - A.A_WIN)
    return dict(code=code, final=fin, steps=steps, amp_peak=amp_peak, tnr=tnr,
                t_step=np.mean([s["dt"] for s in steps]), t_tot=sum(s["dt"] for s in steps) + fin["dt"])


def main():
    quick = "quick" in sys.argv
    corners = [("mos_tt", "cap_typ")] if quick else CORNERS
    temps = (27,) if quick else TEMPS
    print("# D22 amplitude SAR search (bypass closed) [SCH]\n")
    print(f"Settle {SETTLE*1e9:.0f} ns/step; target {A.A_TARGET} V ± {A.A_WIN} V; hard {A.A_HARD} V.\n")
    print("| MOS | CAP | T | band | code | Amp | A_est | tnr | Amp_peak | t_step (s) | t_tot (s) | ≤1.40 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for mos, cap in corners:
        for temp in temps:
            for band, bcode in (("top", 0), ("bottom", 255)):
                r = sar(mos, cap, temp, band, bcode)
                ok = r["amp_peak"] <= A.A_HARD + 1e-3
                print(
                    f"| {mos} | {cap} | {temp} | {band} | {r['code']} | {r['final']['amp']:.3f} | "
                    f"{r['final']['a_est']:.3f} | {int(r['tnr'])} | {r['amp_peak']:.3f} | "
                    f"{r['t_step']:.1f} | {r['t_tot']:.1f} | {'PASS' if ok else 'FAIL'} |"
                )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
