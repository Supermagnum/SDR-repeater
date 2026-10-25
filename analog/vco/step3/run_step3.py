#!/usr/bin/env python3
"""P2.3 step 3: the step-2 VCO across bands, PDK corners and temperature (spec/vco-topology.md section 7).

Run inside the container from this folder (needs ../step2/out/range.json from step 2):

    python3 -u run_step3.py | tee out/summary.txt     # everything, about 2-3 h
    python3 -u run_step3.py reltol                     # 1. pss tolerance check on the validated level 2 (minutes)
    python3 -u run_step3.py range                      # 2. tuning range and swing at corners (transients, ~30 min)
    python3 -u run_step3.py bands                      # 3. phase noise in 5 bands, typical, 27 degC (~75 min)
    python3 -u run_step3.py worst                      # 4. phase noise at the slow corner, 85 degC, 3 bands (~45 min)

Same circuit and sizing as step 2 (imported from ../step2/run_step2.py, sizes from range.json): 2 MOhm bank
and varactor bias, buffer common node decoupled. Tail current per band from the step-2 rule (about 1.3 V
differential at typical, capped at 5 mA); at corners the same per-band current is kept (no recalibration),
which is the conservative case for swing and start-up. Results are [SCH].
"""
import json
import math
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step2"))
import run_step2 as S2  # noqa: E402

S2.OUT = OUT
BANDS = [3.12e9, 3.40e9, 3.65e9, 3.90e9, 4.20e9]
CORNERS = [("mos_tt", "cap_typ"), ("mos_ss", "cap_wcs"), ("mos_ss", "cap_bcs"),
           ("mos_ff", "cap_wcs"), ("mos_ff", "cap_bcs")]
TEMPS = [-40, 27, 85]
LIMITS = {"VHF": {6e5: -108.4, 1e6: -116.0}, "UHF": {1e6: -115.0, 2e6: -117.9}}
OFFS = [1e5, 3e5, 6e5, 1e6, 2e6, 1e7]


def set_corner(mos="mos_tt", cap="cap_typ"):
    S2.HEADER = re.sub(r'include "cornerMOSlv.lib" section=\w+', f'include "cornerMOSlv.lib" section={mos}', S2.HEADER)
    S2.HEADER = re.sub(r'include "cornerMOShv.lib" section=\w+', f'include "cornerMOShv.lib" section={mos}', S2.HEADER)
    S2.HEADER = re.sub(r'include "cornerCAP.lib" section=\w+', f'include "cornerCAP.lib" section={cap}', S2.HEADER)


def load_sizing():
    rj = os.path.join(REPO, "analog", "vco", "step2", "out", "range.json")
    if not os.path.exists(rj):
        sys.exit("analog/vco/step2/out/range.json missing: run step 2 'range' first")
    r = json.load(open(rj))
    S2.LSB_FF, S2.C_FIX_FF, S2.NFING = r["lsb"], r["cfix"], r["nfing"]
    S2.NBITS = r.get("nbits", 7)          # 8 since D20; range.json files from P2.3 have no entry (7 bits)
    S2.CMAX = (1 << S2.NBITS) - 1
    meas = {tuple(float(x) for x in k.split(",")): v for k, v in r["meas"].items()}
    return r, meas


def itail_for(f, meas):
    """Per-band tail current: the step-2 rule (1.3 V at typical, capped at S2.I_MAX = 4 mA, D12), interpolated."""
    pts = sorted((v["f"], min(S2.I_MAX, S2.ITAIL * S2.A_TARGET / v["amp"])) for (c, vt), v in meas.items()
                 if abs(vt - S2.VTUNE_MID) < 1e-6)
    fs, cur = zip(*pts)
    return float(np.interp(f, fs, cur))


def tran(code, vt, tag, itail, temp):
    sim = S2.netlist(f"s3_tr_{tag}", code, vt, itail=itail, analysis=
                     f"  options temp={temp}\n  save v(tp) v(tn) v(tail)\n"
                     "  analysis tr tran stop=60n step=5p maxstep=5p")
    S2.run(sim)
    return S2.measure(os.path.join(OUT, "tr.raw"))


def code_for(f, temp, tag):
    """Bank code for frequency f at V_tune mid: fit 1/f^2 against code from the end codes, verify."""
    cm = S2.CMAX
    m0 = tran(0, S2.VTUNE_MID, f"{tag}_c0", 3.5e-3, temp)
    m1 = tran(cm, S2.VTUNE_MID, f"{tag}_c{cm}", 3.5e-3, temp)
    y0, y1 = 1 / m0["f"] ** 2, 1 / m1["f"] ** 2
    return int(round(min(cm, max(0, (1 / f ** 2 - y0) / (y1 - y0) * cm))))


def pnoise(code, vt, f0, itail, temp, tag):
    from vacask.rawfile import rawread
    from compare import fundamental_amplitude
    vals = ", ".join(f"{x:.0f}" for x in OFFS)
    for opts, npts in (("reltol=1e-6 pss_tolscale=1e-3", 16000), ("reltol=1e-6 pss_tolscale=1e-3", 8000)):
        sim = S2.netlist(f"s3_pn_{tag}", code, vt, itail=itail, analysis=
                         f"  options temp={temp} {opts} pss_minpts={npts}\n"
                         '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
                         f'  analysis pn pnoise oscillator=1 tper={1/f0:.6e} tstab=0 ic="ss" icmode="uic" '
                         f'maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] outharm=1 values=[{vals}] writepss=1',
                         extra="iin (0 tp) isource dc=0\n")
        try:
            S2.run(sim)
            break
        except RuntimeError as e:
            print(f"  pss failed ({opts}, {npts}): {[x for x in str(e).splitlines() if x.strip()][-2:]}")
    else:
        return None
    pss = rawread(os.path.join(OUT, "pn.pss.raw")).get()
    a, fp = fundamental_amplitude(pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
    pn = rawread(os.path.join(OUT, "pn.raw")).get()
    off = np.real(pn["frequency"])
    l = 10 * np.log10(np.real(pn["onoise"]) / (a * a / 2))
    return dict(f=fp, amp=a, L={float(o): float(x) for o, x in zip(off, l)})


def pn_table(title, rows):
    print(f"\n{title}\n")
    print("| Band | f (GHz) | Code | I_tail (mA) | Amplitude (V) | " +
          " | ".join(f"L @ {o/1e6:g} MHz" for o in OFFS) + " | Worst margin |")
    print("|---|---|---|---|---|" + "---|" * len(OFFS) + "---|")
    for tag, code, itail, r in rows:
        if r is None:
            print(f"| {tag} | — | {code} | {itail*1e3:.2f} | pss failed |")
            continue
        margins = []
        for band, lim in LIMITS.items():
            lo, hi = (3.12e9, 4.20e9) if band == "VHF" else (3.20e9, 3.84e9)
            if lo - 30e6 <= r["f"] <= hi + 30e6:
                margins += [(lim[o] - r["L"][o], band, o) for o in lim]
        worst = min(margins) if margins else None
        w = f"{worst[0]:+.1f} dB ({worst[1]} {worst[2]/1e6:g} MHz)" if worst else "—"
        print(f"| {tag} | {r['f']/1e9:.3f} | {code} | {itail*1e3:.2f} | {r['amp']:.3f} | " +
              " | ".join(f"{r['L'][o]:.1f}" for o in OFFS) + f" | {w} |")


def do_reltol():
    print("## 1. pss tolerance check on the validated level 2 (analog/pn-validation)\n")
    print("Step 2 converged only at reltol 1e-6 / pss_tolscale 1e-3; the method was validated at 1e-7 / 1e-4.")
    src = os.path.join(REPO, "analog", "pn-validation", "level2_sg13.sim")
    from vacask.rawfile import rawread
    from compare import fundamental_amplitude
    res = {}
    for tag, opts in (("tight", "reltol=1e-7 pss_tolscale=1e-4"), ("loose", "reltol=1e-6 pss_tolscale=1e-3")):
        text = open(src).read()
        text = re.sub(r"options reltol=\S+ pss_tolscale=\S+", f"options {opts}", text)
        text = text.replace("analysis pn2 pnoise", f"analysis l2{tag} pnoise")
        name = f"l2_{tag}.sim"
        open(os.path.join(OUT, name), "w").write(text)
        S2.run(os.path.join(OUT, name))
        pss = rawread(os.path.join(OUT, f"l2{tag}.pss.raw")).get()
        a, _ = fundamental_amplitude(pss["time"], np.real(pss["vp"]) - np.real(pss["vm"]))
        pn = rawread(os.path.join(OUT, f"l2{tag}.raw")).get()
        res[tag] = (np.real(pn["frequency"]), 10 * np.log10(np.real(pn["onoise"]) / (a * a / 2)))
    off, lt = res["tight"]
    _, ll = res["loose"]
    print("\n| Offset | reltol 1e-7 | reltol 1e-6 | Difference |")
    print("|---|---|---|---|")
    for o, a, b in zip(off, lt, ll):
        print(f"| {o/1e3:.0f} kHz | {a:.2f} | {b:.2f} | {b-a:+.2f} dB |")
    print(f"\nWorst difference {np.max(np.abs(ll-lt)):.2f} dB.\n")


def do_range(meas):
    print("## 2. Tuning range and swing at corners (60 ns transients)\n")
    i_top, i_bot = itail_for(4.4e9, meas), itail_for(2.95e9, meas)
    print(f"Top: code 0 at 1.0 V, I_tail {i_top*1e3:.2f} mA. Bottom: code {S2.CMAX} at 0.3 V, I_tail {i_bot*1e3:.2f} mA. "
          f"Needed: top >= 4.20 GHz, bottom <= 3.12 GHz; peak V_GS / V_GD <= {S2.V_OX} V.\n")
    print("| MOS | CAP | T (degC) | f top (GHz) | f bottom (GHz) | Covers | Amp top / bottom (V) | Peak V_GS | Peak V_GD |")
    print("|---|---|---|---|---|---|---|---|---|")
    for mos, cap in CORNERS:
        set_corner(mos, cap)
        for t in TEMPS:
            try:
                a = tran(0, 1.0, f"{mos}_{cap}_{t}_top", i_top, t)
                b = tran(S2.CMAX, 0.3, f"{mos}_{cap}_{t}_bot", i_bot, t)
            except RuntimeError as e:
                print(f"| {mos} | {cap} | {t} | failed: {str(e).splitlines()[0]} |")
                continue
            if not a or not b:
                print(f"| {mos} | {cap} | {t} | no oscillation ({'top' if not a else 'bottom'}) |")
                continue
            ok = a["f"] >= 4.20e9 and b["f"] <= 3.12e9
            vgs, vgd = max(a["vgs"], b["vgs"]), max(a["vgd"], b["vgd"])
            fl = lambda x: f"**{x:.2f}**" if x > S2.V_OX else f"{x:.2f}"            # noqa: E731
            print(f"| {mos} | {cap} | {t} | {a['f']/1e9:.3f} | {b['f']/1e9:.3f} | {'yes' if ok else '**NO**'} | "
                  f"{a['amp']:.2f} / {b['amp']:.2f} | {fl(vgs)} | {fl(vgd)} |")
    set_corner()
    print()


def do_bands(meas, mos="mos_tt", cap="cap_typ", temp=27, bands=BANDS, title=None):
    set_corner(mos, cap)
    rows = []
    for f in bands:
        tag = f"{mos}_{cap}_{temp}_{f/1e9:.2f}"
        code = code_for(f, temp, tag)
        itail = itail_for(f, meas)
        m = tran(code, S2.VTUNE_MID, f"{tag}_pick", itail, temp)
        print(f"  {tag}: code {code} -> {m['f']/1e9:.4f} GHz, {m['amp']:.3f} V at {itail*1e3:.2f} mA; pnoise ...")
        r = pnoise(code, S2.VTUNE_MID, m["f"], itail, temp, tag)
        rows.append((f"{f/1e9:.2f} GHz", code, itail, r))
    pn_table(title or f"## Phase noise, {mos} / {cap}, {temp} degC (dBc/Hz)", rows)
    set_corner()


def main():
    os.makedirs(OUT, exist_ok=True)
    what = [a for a in sys.argv[1:] if "=" not in a] or ["reltol", "range", "bands", "worst"]
    r, meas = load_sizing()
    print(f"# P2.3 step 3\n\nSizing from step 2 ({S2.NBITS}-bit bank): LSB {S2.LSB_FF:.2f} fF, fixed {S2.C_FIX_FF:.0f} fF, "
          f"varactor {S2.NFING} fingers, bias resistors {S2.R_BIAS/1e6:g} MOhm.\n")
    if "reltol" in what:
        do_reltol()
    if "range" in what:
        do_range(meas)
    if "bands" in what:
        print("## 3. Phase noise across the band (typical, 27 degC)\n")
        do_bands(meas, title="Typical, 27 degC (dBc/Hz); limits VHF -108.4 @ 0.6 MHz, -116 @ 1 MHz; "
                             "UHF -115 @ 1 MHz, -117.9 @ 2 MHz")
    if "worst" in what:
        print("\n## 4. Phase noise at the slow corner, 85 degC\n")
        do_bands(meas, "mos_ss", "cap_typ", 85, [3.12e9, 3.65e9, 4.20e9],
                 title="mos_ss / cap_typ, 85 degC (dBc/Hz)")


if __name__ == "__main__":
    main()
