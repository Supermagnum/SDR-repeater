#!/usr/bin/env python3
"""P2.4 step 1: divider speed checks before the schematic (spec/lo-divider-topology.md section 5).

Run inside the container from this folder:

    mkdir -p out && python3 -u run_step1.py | tee out/summary.txt     # all checks, about 20-60 min
    python3 -u run_step1.py cml2 cml3 tspc conv                       # or some of them

Checks (transients, typical corner 1.2 V 27 degC and slow corner 1.08 V 125 degC):
  cml2  CML divide-by-2 (master-slave latch pair): highest input frequency that still divides by 2,
        for three tail currents per latch. Needed: >= 1.3 x 4.41 GHz = 5.7 GHz at the slow corner.
  cml3  CML divide-by-3: two CML flip-flops and a single-level CML NOR with a reference input
        (D1 = NOR(Q1, Q2), D2 = Q1). Needed: >= 5.7 GHz at the slow corner.
  tspc  CMOS TSPC flip-flop as a toggle (divide-by-2), three sizes: highest clock frequency.
        Needed (D14): >= 1.3 x 1.47 GHz = 1.9 GHz (VHF Johnson) and >= 1.3 x 2.2 GHz = 2.9 GHz (UHF Johnson).
  conv  CML-to-CMOS converter (NMOS pair with PMOS mirror load, two inverters): output duty cycle and
        delay at 1.47 and 2.2 GHz.
Sources are ideal (Verilog-A sine / smoothed square), supplies ideal. Results are [SCH]; the topology,
not the final sizing, is what this step checks.
"""
import math
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
os.environ.setdefault("PDK_ROOT", "/foss/pdks")
os.environ.setdefault("PDK", "ihp-sg13g2")
sys.path.append("/foss/tools/vacask/lib/vacask/python")

CORNERS = [("tt", "mos_tt", 1.2, 27), ("ss", "mos_ss", 1.08, 125)]
NEED_CML = 1.3 * 4.41e9
NEED_TSPC = {"VHF": 1.3 * 1.47e9, "UHF": 1.3 * 2.2e9}

HEADER = """{title}

include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section={mos}

load "resistor.osdi"
load "capacitor.osdi"

model resistor  resistor
model capacitor capacitor
model vsource   vsource
model isource   isource

embed "clk.va" <<<FILE
`include "constants.vams"
`include "disciplines.vams"
// Differential clock: sine (shape = 0) or smoothed square (shape > 0, tanh sharpness), common mode vcm
module clk(p, n);
    inout p, n;
    electrical p, n;
    analog begin
        V(p) <+ {vcm} + {amp} * ({shape} > 0 ? tanh({shape} * sin(2 * `M_PI * {f:.6e} * $abstime)) : sin(2 * `M_PI * {f:.6e} * $abstime));
        V(n) <+ {vcm} - {amp} * ({shape} > 0 ? tanh({shape} * sin(2 * `M_PI * {f:.6e} * $abstime)) : sin(2 * `M_PI * {f:.6e} * $abstime));
    end
endmodule
>>>FILE
load "clk.va"
model clk clk
"""

SUMMARY = []


def say(s=""):
    print(s)
    SUMMARY.append(s)


def run(name, body, f, stop, corner, vcm, amp, shape=0.0):
    _, mos, vdd, temp = corner
    path = os.path.join(OUT, name + ".sim")
    with open(path, "w") as fh:
        fh.write(HEADER.format(title=f"P2.4 step 1: {name}", mos=mos, vcm=vcm, amp=amp, shape=shape, f=f))
        fh.write(f"vdd (vdd 0) vsource dc={vdd}\nxclk (ckp ckn) clk\n" + body)
        fh.write("\ncontrol\n  abort always\n  options rawfile=\"binary\"\n"
                 f"  options temp={temp}\n"
                 f"  analysis tr tran stop={stop:.4e} step={1/f/50:.4e} maxstep={1/f/50:.4e}\nendc\n")
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(f"vacask {name}.sim failed; end of out/{name}.log: " + open(log).read()[-600:])
    from vacask.rawfile import rawread
    return rawread(os.path.join(OUT, "tr.raw")).get()


def freq(t, v, frac=0.5):
    """Frequency from rising zero crossings over the last part of the record."""
    t, v = np.real(t), np.real(v)
    m = t >= t[-1] * (1 - frac)
    t, v = t[m], v[m] - np.mean(v[m])
    s = np.sign(v)
    i = np.where((s[:-1] < 0) & (s[1:] >= 0))[0]
    if len(i) < 3:
        return 0.0, 0.0
    tz = t[i] - v[i] * (t[i + 1] - t[i]) / (v[i + 1] - v[i])
    return (len(tz) - 1) / (tz[-1] - tz[0]), (v.max() - v.min()) / 2


# ------------------------------------------------------------------ CML cells
VARIANT = dict(k=1.0, tailless=False)   # latch-pair width ratio; clock pair sources to ground (no tail source)


def cml_latch(name, dp, dn, ckp, ckn, qp, qn, i, rl, w):
    """CML D-latch: tracks D while ckp is high. Outputs are the drains (qn = drain of the dp device).
    VARIANT['k'] scales the regenerative pair; VARIANT['tailless'] grounds the clock pair (no tail source)."""
    k, tl = VARIANT["k"], VARIANT["tailless"]
    t = "0" if tl else f"t{name}"
    return (f"rl{name}p (vdd {qp}) resistor r={rl:.1f}\nrl{name}n (vdd {qn}) resistor r={rl:.1f}\n"
            f"m{name}1 ({qn} {dp} s1{name} 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
            f"m{name}2 ({qp} {dn} s1{name} 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
            f"m{name}3 ({qn} {qp} s2{name} 0) sg13_lv_nmos w={w*k:.2f}u l=0.13u\n"
            f"m{name}4 ({qp} {qn} s2{name} 0) sg13_lv_nmos w={w*k:.2f}u l=0.13u\n"
            f"m{name}5 (s1{name} {ckp} {t} 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
            f"m{name}6 (s2{name} {ckn} {t} 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
            + ("" if tl else f"i{name} (t{name} 0) isource dc={i:.4e}\n"))


def cml_dff(name, dp, dn, qp, qn, i, rl, w):
    """Master tracks while ckp is high, slave while ckn is high: output changes on the falling ckp edge."""
    return (cml_latch(name + "m", dp, dn, "ckp", "ckn", f"m{name}p", f"m{name}n", i, rl, w) +
            cml_latch(name + "s", f"m{name}p", f"m{name}n", "ckn", "ckp", qp, qn, i, rl, w))


def kick(node):
    return f'ik{node} (0 {node}) isource type="pulse" val0=0 val1=200u delay=20p rise=10p fall=10p width=50p\n'


def cml_params(i, vdd):
    swing = 0.4                                   # single-ended swing I * RL
    return i, swing / i, max(1.0, 10.0 * i / 1e-3)   # current, load, width (10 um per mA)


def search(build, freqs, corner, n_div, vcm, amp, shape=0.0, out=("qp", "qn"), single=False, probe=None):
    """Run every frequency. Returns (f_max, pattern, probe_min): f_max is the top of the first unbroken run of
    correct divisions (output = input / N within 1 % and a real swing); pattern marks each frequency
    (e.g. '1+ 2+ 3- ...', GHz); probe_min is the lowest voltage seen on node `probe` (headroom check).

    First run (2026-10-20): the sweep stopped at the first failure, and nearly every case reported 0 GHz,
    so it now runs all frequencies and shows where it fails.
    """
    marks, runs, pmin = [], [], None
    for f in freqs:
        stop = (n_div * 40 + 20) / f
        try:
            d = run(build(f), build.body(f), f, stop, corner, vcm, amp, shape)
        except RuntimeError as e:
            marks.append(f"{f/1e9:g}!")
            runs.append(False)
            continue
        v = np.real(d[out[0]]) - (np.real(d[out[1]]) if not single else corner[2] / 2)
        fo, a = freq(d["time"], v)
        ok = abs(fo * n_div / f - 1) < 0.01 and a > (0.15 if not single else 0.35 * corner[2])
        marks.append(f"{f/1e9:g}{'+' if ok else '-'}")
        runs.append(ok)
        if probe and pmin is None:
            pmin = float(np.min(np.real(d[probe])))
    fmax, started = 0.0, False
    for f, ok in zip(freqs, runs):
        if ok:
            fmax, started = f, True
        elif started:
            break
    return fmax, " ".join(marks), pmin


class Build:
    """Callable that names a netlist and holds the body generator."""
    def __init__(self, tag, body):
        self.tag, self.body = tag, body

    def __call__(self, f):
        return f"{self.tag}_{f/1e9:.2f}g"


def check_cml(n_div):
    label = "÷2" if n_div == 2 else "÷3"
    say(f"## CML {label}: highest input frequency [SCH]")
    say("")
    say(f"Differential sine clock, 0.3 V amplitude per side (×0.9 at the slow corner), common mode V_DD − 0.5 V "
        "(below the data level, for headroom in the two-level stack; the real clock comes level-shifted from the VCO buffer). "
        f"Load RL = 0.4 V / I_latch, widths 10 µm per mA, L = 0.13 µm. Needed: ≥ {NEED_CML/1e9:.2f} GHz at the slow corner.")
    say("")
    say("| Corner | I per latch (mA) | Clock CM (V) | Total current (mA) | f_max (GHz) | Margin vs 4.41 GHz | "
        "Tail node min (V) | Pattern (GHz: + divides, - fails, ! error) |")
    say("|---|---|---|---|---|---|---|---|")
    freqs = [x * 1e9 for x in (1, 2, 3, 4, 5, 6, 7, 8, 10, 12)]
    for corner in CORNERS:
        for i, dv in [(i, dv) for i in (0.3e-3, 0.5e-3, 0.8e-3) for dv in (0.40, 0.55)]:
            i_, rl, w = cml_params(i, corner[2])
            vcm = corner[2] - dv       # clock common mode below the data level (two-level stack headroom)
            if n_div == 2:
                body = lambda f, i_=i_, rl=rl, w=w: cml_dff("a", "qn", "qp", "qp", "qn", i_, rl, w) + kick("qp")   # noqa: E731
                latches, extra = 2, 0
            else:
                # D1 = NOR(Q1, Q2) from a single-level gate with a reference; D2 = Q1
                def body(f, i_=i_, rl=rl, w=w):
                    vref = corner[2] - 0.2
                    gate = (f"rgp (vdd orp) resistor r={rl:.1f}\nrgn (vdd orn) resistor r={rl:.1f}\n"
                            f"mga (orn q1p tg 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
                            f"mgb (orn q2p tg 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
                            f"mgr (orp vref tg 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
                            f"ig (tg 0) isource dc={i_:.4e}\nvref (vref 0) vsource dc={vref:.3f}\n")
                    # orn = NOR (low when either input high), orp = OR
                    return (gate + cml_dff("a", "orn", "orp", "q1p", "q1n", i_, rl, w) +
                            cml_dff("b", "q1p", "q1n", "q2p", "q2n", i_, rl, w) + kick("q1p"))
                latches, extra = 4, 1
            b = Build(f"cml{n_div}_{corner[0]}_i{i*1e3:.1f}_cm{vcm:.2f}", body)
            fmax, pat, pmin = search(b, freqs, corner, n_div, vcm, 0.3 * corner[2] / 1.2,
                                     out=("q2p", "q2n") if n_div == 3 else ("qp", "qn"), probe="tam")
            tot = (latches + extra) * i
            say(f"| {corner[0]} ({corner[2]} V, {corner[3]} °C) | {i*1e3:.1f} | {vcm:.2f} | "
                f"{tot*1e3:.1f} | {fmax/1e9:.1f}{'+' if fmax >= freqs[-1] else ''} | "
                f"{fmax/4.41e9:.2f}× {'OK' if fmax >= NEED_CML else '**short**'} | "
                f"{pmin if pmin is None else round(pmin, 2)} | {pat} |")
    say("")


# ------------------------------------------------------------------ TSPC
def tspc_toggle(s):
    """Positive-edge TSPC flip-flop (inverting: output = NOT D after the edge), output fed back to D: divide by 2.
    First run: the clock gates were on a node 'ck' that nothing drove (the source drives 'ckp'); fixed."""
    wn, wp = 0.5 * s, 1.0 * s
    return (f"mp1 (x1 q vdd vdd) sg13_lv_pmos w={wp:.2f}u l=0.13u\n"
            f"mp2 (a ckp x1 vdd) sg13_lv_pmos w={wp:.2f}u l=0.13u\n"
            f"mn1 (a q 0 0) sg13_lv_nmos w={wn:.2f}u l=0.13u\n"
            f"mp3 (b ckp vdd vdd) sg13_lv_pmos w={wp:.2f}u l=0.13u\n"
            f"mn2 (b a x2 0) sg13_lv_nmos w={wn:.2f}u l=0.13u\n"
            f"mn3 (x2 ckp 0 0) sg13_lv_nmos w={wn:.2f}u l=0.13u\n"
            f"mp4 (q b vdd vdd) sg13_lv_pmos w={wp:.2f}u l=0.13u\n"
            f"mn4 (q ckp x3 0) sg13_lv_nmos w={wn:.2f}u l=0.13u\n"
            f"mn5 (x3 b 0 0) sg13_lv_nmos w={wn:.2f}u l=0.13u\n"
            f"cl (q 0) capacitor c={5e-15 * s:.3e}\n")


def check_tspc():
    say("## TSPC flip-flop as a toggle: highest clock frequency [SCH]")
    say("")
    say("Rail-to-rail clock (smoothed square, about 20 ps edges), load 5 fF per size unit (next stage). Sizes: NMOS "
        "0.5 µm and PMOS 1 µm per unit, L = 0.13 µm. Needed (D14): VHF ≥ 1.9 GHz, UHF ≥ 2.9 GHz at the slow corner.")
    say("")
    say("| Corner | Size | f_max (GHz) | VHF (1.47 GHz) | UHF (2.2 GHz) | Pattern |")
    say("|---|---|---|---|---|---|")
    freqs = [x * 1e9 for x in (0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8)]
    for corner in CORNERS:
        for s in (1, 2, 4):
            body = lambda f, s=s: tspc_toggle(s)                 # noqa: E731
            b = Build(f"tspc_{corner[0]}_s{s}", body)
            vdd = corner[2]
            fmax, pat, _ = search(b, freqs, corner, 2, vdd / 2, vdd / 2, shape=6.0, out=("q", "q"), single=True)
            say(f"| {corner[0]} ({vdd} V, {corner[3]} °C) | {s} | {fmax/1e9:.1f} | "
                f"{fmax/1.47e9:.2f}× {'OK' if fmax >= NEED_TSPC['VHF'] else '**short**'} | "
                f"{fmax/2.2e9:.2f}× {'OK' if fmax >= NEED_TSPC['UHF'] else '**short**'} | {pat} |")
    say("")
    say("The clock source drives `ckp` only (`ckn` unused); a real TSPC chain needs a single-phase clock from the "
        "CML-to-CMOS converter.")
    say("")


# ------------------------------------------------------------------ converter
def check_conv():
    say("## CML-to-CMOS converter: duty cycle and delay [SCH]")
    say("")
    say("NMOS pair 4/0.13 µm, PMOS mirror 4/0.13 µm, tail 0.3 mA, then two inverters (1/0.5 µm and 2/1 µm), "
        "load 10 fF. Input: 0.3 V per side around 0.9 V (×0.9 at the slow corner).")
    say("")
    say("| Corner | f (GHz) | Output duty (%) | Low / high level (V) |")
    say("|---|---|---|---|")
    for corner in CORNERS:
        vdd = corner[2]
        for f in (1.47e9, 2.2e9):
            body = ("mp1 (o1 o1 vdd vdd) sg13_lv_pmos w=4u l=0.13u\nmp2 (o2 o1 vdd vdd) sg13_lv_pmos w=4u l=0.13u\n"
                    "mn1 (o1 ckn tc 0) sg13_lv_nmos w=4u l=0.13u\nmn2 (o2 ckp tc 0) sg13_lv_nmos w=4u l=0.13u\n"
                    "it (tc 0) isource dc=0.3m\n"
                    "mi1p (x o2 vdd vdd) sg13_lv_pmos w=1u l=0.13u\nmi1n (x o2 0 0) sg13_lv_nmos w=0.5u l=0.13u\n"
                    "mi2p (y x vdd vdd) sg13_lv_pmos w=2u l=0.13u\nmi2n (y x 0 0) sg13_lv_nmos w=1u l=0.13u\n"
                    "cy (y 0) capacitor c=10f\n")
            name = f"conv_{corner[0]}_{f/1e9:.2f}g"
            try:
                d = run(name, body, f, 30 / f, corner, vdd - 0.3, 0.3 * vdd / 1.2)
            except RuntimeError as e:
                say(f"| {corner[0]} | {f/1e9:.2f} | failed: {str(e)[:80]} |")
                continue
            t, y = np.real(d["time"]), np.real(d["y"])
            m = t >= t[-1] * 0.5
            t, y = t[m], y[m]
            tu = np.linspace(t[0], t[-1], 20000)
            yu = np.interp(tu, t, y)
            duty = 100 * np.mean(yu > vdd / 2)
            say(f"| {corner[0]} ({vdd} V, {corner[3]} °C) | {f/1e9:.2f} | {duty:.1f} | {yu.min():.2f} / {yu.max():.2f} |")
    say("")


def check_cmlx():
    """Slow-corner rescue for the CML dividers (second run, 2026-10-20).

    The second run showed the CML ÷2 / ÷3 dividing up to 10 / 7 GHz at the slow corner but failing BELOW
    4-5 GHz, inside the operating range (÷3: 3.12-4.20 GHz VCO), with the ideal tail node pulled below 0 V
    (no headroom at 1.08 V). This check tries the usual remedies on the operating window itself.
    """
    say("## CML ÷2 / ÷3 at the operating frequencies: variants [SCH]")
    say("")
    say("Window that must divide: ÷2 2.9–5.0 GHz (UHF 3.2–3.84 GHz × margin), ÷3 2.9–5.7 GHz (VHF 3.12–4.41 GHz "
        "× 1.3). 0.5 mA per latch nominal, widths 10 µm per mA. Current is the measured average supply current.")
    say("")
    say("| Corner | Divider | Variant | Supply current (mA) | Window | Pattern (GHz) |")
    say("|---|---|---|---|---|---|")
    freqs = [x * 1e9 for x in (2.0, 2.5, 2.9, 3.2, 3.5, 3.84, 4.2, 4.41, 5.0, 5.7, 6.5, 8.0)]
    windows = {2: (2.9e9, 5.0e9), 3: (2.9e9, 5.7e9)}
    variants = [("base, 0.27 V clock", 0.27, 1.0, False, 0.55),
                ("0.5 V clock", 0.5, 1.0, False, 0.55),
                ("0.5 V clock, latch pair 2×", 0.5, 2.0, False, 0.55),
                ("tail-less, 0.5 V clock, latch pair 2×", 0.5, 2.0, True, None)]
    for corner in CORNERS[::-1]:
        vdd = corner[2]
        for n_div in (2, 3):
            for label, amp, k, tl, dv in variants:
                VARIANT.update(k=k, tailless=tl)
                i_, rl, w = cml_params(0.5e-3, vdd)
                vcm = 0.45 if tl else vdd - dv
                if n_div == 2:
                    body = lambda f, i_=i_, rl=rl, w=w: cml_dff("a", "qn", "qp", "qp", "qn", i_, rl, w) + kick("qp")  # noqa: E731
                    out = ("qp", "qn")
                else:
                    def body(f, i_=i_, rl=rl, w=w, vdd=vdd):
                        gate = (f"rgp (vdd orp) resistor r={rl:.1f}\nrgn (vdd orn) resistor r={rl:.1f}\n"
                                f"mga (orn q1p tg 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
                                f"mgb (orn q2p tg 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
                                f"mgr (orp vref tg 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
                                f"ig (tg 0) isource dc={i_:.4e}\nvref (vref 0) vsource dc={vdd - 0.2:.3f}\n")
                        return (gate + cml_dff("a", "orn", "orp", "q1p", "q1n", i_, rl, w) +
                                cml_dff("b", "q1p", "q1n", "q2p", "q2n", i_, rl, w) + kick("q1p"))
                    out = ("q2p", "q2n")
                tag = f"cmlx{n_div}_{corner[0]}_{label.split(',')[0].replace(' ', '').replace('.', 'p')}_k{k:g}{'_tl' if tl else ''}_a{amp}"
                marks, oks, cur = [], [], []
                for f in freqs:
                    try:
                        d = run(f"{tag}_{f/1e9:.2f}g", body(f), f, (n_div * 40 + 20) / f, corner, vcm, amp * vdd / 1.2)
                    except RuntimeError:
                        marks.append(f"{f/1e9:g}!")
                        oks.append(False)
                        continue
                    fo, a = freq(d["time"], np.real(d[out[0]]) - np.real(d[out[1]]))
                    ok = abs(fo * n_div / f - 1) < 0.01 and a > 0.15
                    oks.append(ok)
                    marks.append(f"{f/1e9:g}{'+' if ok else '-'}")
                    t = np.real(d["time"])
                    cur.append(float(np.mean(np.abs(np.real(d["vdd:flow(br)"])[t >= t[-1] / 2]))))
                lo, hi = windows[n_div]
                win = all(ok for f, ok in zip(freqs, oks) if lo - 1 <= f <= hi + 1)
                say(f"| {corner[0]} ({vdd} V, {corner[3]} °C) | ÷{n_div} | {label} | "
                    f"{(np.mean(cur) * 1e3 if cur else float('nan')):.1f} | {'**OK**' if win else 'fails'} | {' '.join(marks)} |")
    VARIANT.update(k=1.0, tailless=False)
    say("")


def div_body(n_div, i_, rl, w, vdd):
    """Netlist body of the CML ÷2 or ÷3 (ideal tails, latch pair 1×), and its output nodes."""
    if n_div == 2:
        return cml_dff("a", "qn", "qp", "qp", "qn", i_, rl, w) + kick("qp"), ("qp", "qn")
    gate = (f"rgp (vdd orp) resistor r={rl:.1f}\nrgn (vdd orn) resistor r={rl:.1f}\n"
            f"mga (orn q1p tg 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
            f"mgb (orn q2p tg 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
            f"mgr (orp vref tg 0) sg13_lv_nmos w={w:.2f}u l=0.13u\n"
            f"ig (tg 0) isource dc={i_:.4e}\nvref (vref 0) vsource dc={vdd - 0.2:.3f}\n")
    return (gate + cml_dff("a", "orn", "orp", "q1p", "q1n", i_, rl, w) +
            cml_dff("b", "q1p", "q1n", "q2p", "q2n", i_, rl, w) + kick("q1p")), ("q2p", "q2n")


def check_amp():
    """Minimum clock swing (third run, 2026-10-20: 0.27 V per side fails at the slow corner below 5 GHz,
    0.5 V per side passes the whole window). This sets the requirement for the VCO buffer."""
    say("## CML ÷2 / ÷3: minimum clock swing over the operating window [SCH]")
    say("")
    say("0.5 mA per latch, latch pair 1×, ideal tails, clock common mode V_DD − 0.55 V. Swing per side as listed "
        "(scaled by V_DD / 1.2 V). Window: ÷2 2.9–5.0 GHz, ÷3 2.9–5.7 GHz. Fast corner added: mos_ff, 1.32 V, −40 °C.")
    say("")
    corners = CORNERS + [("ff", "mos_ff", 1.32, -40)]
    freqs = [x * 1e9 for x in (2.9, 3.2, 3.5, 3.84, 4.2, 4.41, 5.0, 5.7)]
    windows = {2: 5.0e9, 3: 5.7e9}
    amps = (0.3, 0.35, 0.4, 0.45, 0.5, 0.6)
    say("| Corner | Divider | " + " | ".join(f"{a:g} V" for a in amps) + " | Minimum swing |")
    say("|---|---|" + "---|" * len(amps) + "---|")
    for corner in corners:
        vdd = corner[2]
        for n_div in (2, 3):
            i_, rl, w = cml_params(0.5e-3, vdd)
            cells, minimum = [], None
            for a in amps:
                fails = []
                for f in freqs:
                    if f > windows[n_div] + 1:
                        continue
                    body, out = div_body(n_div, i_, rl, w, vdd)
                    try:
                        d = run(f"amp{n_div}_{corner[0]}_a{a}_{f/1e9:.2f}g", body, f, (n_div * 40 + 20) / f,
                                corner, vdd - 0.55, a * vdd / 1.2)
                        fo, amp = freq(d["time"], np.real(d[out[0]]) - np.real(d[out[1]]))
                        ok = abs(fo * n_div / f - 1) < 0.01 and amp > 0.15
                    except RuntimeError:
                        ok = False
                    if not ok:
                        fails.append(f"{f/1e9:g}")
                cells.append("OK" if not fails else "fails " + ",".join(fails))
                if not fails and minimum is None:
                    minimum = a
            say(f"| {corner[0]} ({vdd} V, {corner[3]} °C) | ÷{n_div} | " + " | ".join(cells) +
                f" | {'**' + format(minimum, 'g') + ' V**' if minimum else '> 0.6 V'} |")
    say("")


CHECKS = {"cml2": lambda: check_cml(2), "cml3": lambda: check_cml(3), "tspc": check_tspc, "conv": check_conv,
          "cmlx": check_cmlx, "amp": check_amp}


def main():
    os.makedirs(OUT, exist_ok=True)
    say("# P2.4 step 1 — divider speed checks")
    say("")
    for k in sys.argv[1:] or list(CHECKS):
        try:
            CHECKS[k]()
        except Exception as e:                                   # noqa: BLE001
            say(f"**Check '{k}' failed:** {e}")
            say("")
    with open(os.path.join(OUT, "summary.md"), "w") as fh:
        fh.write("\n".join(SUMMARY) + "\n")


if __name__ == "__main__":
    main()
