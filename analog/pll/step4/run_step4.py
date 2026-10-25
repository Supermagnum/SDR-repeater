#!/usr/bin/env python3
"""P2.5 step 4: bias generator, lock-detector window delay cell, V_tune hold switch
(spec/pll-topology.md §12).

Run inside the container from this folder:

    mkdir -p out
    python3 -u run_step4.py | tee out/summary.txt            # bias, start, win, hold (about 15 min)
    python3 -u run_step4.py lin | tee out/summary_lin.txt    # pump linearity with the real bias, about 25 min
    python3 -u run_step4.py win cw=4.2                       # options: cw= MIM side of the delay cell (um),
                                                             #          wi= its charging current in uA

bias   Bias generator, DC [SCH]. V_REF / R_B sets a 10 uA master current (V_REF 0.4 V from the chip reference -
       still an ideal source, the bandgap is a shared block; R_B 40 kOhm, ideal, with +-20 % as a stand-in for
       the poly-resistor tolerance). A rail-to-rail transconductor (the step-2a design, here biased from its
       own outputs) drives the PMOS gate pbias so that the master device puts V_REF across R_B; start-up circuit
       for the zero-current state. All outputs are mirrors of 1 uA unit fingers (PMOS 2 / 2 um, NMOS 1 / 2 um):
         I_cp DAC  PLL_CTRL[5:3]: (code + 1) x 25 uA, segments 25 (always on) + 25 + 50 + 100 uA, PMOS switches
         tails     the four amplifier tails of the charge pump (2 and 10 uA, sources and sinks)
         window    4 uA per delay cell
       I_cp tracks V_REF / R_B; with R_B of the same resistor type as the loop-filter R1, I_cp x R1 (and so the
       loop bandwidth) does not depend on the resistor's absolute value.
start  Start-up with the supply ramped in 0.1 us and in 20 us: master current reaches its value, the start-up
       device turns off.
win    Window delay cell for the two-sided lock detector (rtl/afe/lockdet.sv): a rising edge sets a flip-flop,
       which releases a MIM capacitor charged by 4 uA; an inverter pair is the threshold; the output resets the
       flip-flop (self-timed pulse). One cell on the reference (50 % clock), one on the divider output (2.5 ns
       pulse, as the MMD gives). Delay against corners, capacitor corners, R_B +-20 % and supply. Target 7 ns,
       allowed 5-12 ns (above the 4.7 ns locked UP pulse incl. reset; below T_ref / 2).
hold   V_tune hold switch for band calibration: transmission gates connect the CP output node and the C2 node of
       the loop filter to V_DD / 2 from a 2 x 1 kOhm divider (on only during hold). Loop filter as P2.2 (ideal
       R, C), offset current on. Loop filter precharged to 0 / 0.25 / 0.95 / 1.2 V, then hold: V_tune (C3 node)
       error after the first-trial settling (64 reference cycles, bandcal.sv SETTLE0) and averaged over the
       first 128-cycle count; limit 10 mV (0.4 MHz at the VCO, a tenth of a count). Plus the switch leakage with
       hold off at fast-hot.
lin    The step-2a/3 linearity check (Q(dt) at 1-5 ns, offset pair on) with every ideal current source of the
       pump replaced by the bias generator; compare with step 3 (nominal INL 0.4-2.0 ps, lock point 2.76-3.05 ns).
Results are [SCH].
"""
import importlib.util
import math
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
_spec = importlib.util.spec_from_file_location("pll_step2", os.path.join(REPO, "analog", "pll", "step2", "run_step2.py"))
S2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S2)
S2.OUT = OUT

ARGS = sys.argv[1:]
opt = lambda k, d: next((float(a[len(k) + 1:]) for a in ARGS if a.startswith(k + "=")), d)   # noqa: E731
VREF, RB = 0.4, 40e3            # master current V_REF / R_B = 10 uA
CW = opt("cw", 4.7)             # delay-cell MIM side (um), about 33 fF at 1.5 fF/um^2
WI = int(opt("wi", 4))          # delay-cell charging current (uA, unit fingers)
F_REF = S2.F_REF

HEADER4 = S2.HEADER.replace('include "cornerMOSlv.lib" section={mos}\n',
                            'include "cornerMOSlv.lib" section={mos}\ninclude "cornerCAP.lib" section={cap}\n') + """
embed "step4va.va" <<<FILE
`include "constants.vams"
`include "disciplines.vams"
module pulse2(p);
    inout p;
    electrical p;
    parameter real f = 36e6;
    parameter real td = 0;
    parameter real w = 2.5e-9;
    parameter real vh = 1.2;
    // high from td to td + w every period (the MMD output is one prescaler cycle wide)
    analog V(p) <+ vh * 0.25 * (1 + tanh(8 * sin(2 * `M_PI * f * ($abstime - td))))
                          * (1 - tanh(8 * sin(2 * `M_PI * f * ($abstime - td - w))));
endmodule
module tsw(p, n);
    inout p, n;
    electrical p, n;
    parameter real t0 = 0.5e-6;
    parameter real ron = 10;
    parameter real roff = 1e12;
    // closed before t0, open after (precharge of the loop filter)
    analog I(p, n) <+ V(p, n) * (1 / roff + (1 / ron - 1 / roff) * 0.5 * (1 - tanh(($abstime - t0) / 2e-9)));
endmodule
>>>FILE
load "step4va.va"
"""

BIAS_CORNERS = [("tt", "mos_tt", 1.20, 27, 1.0), ("tt 1.08 V", "mos_tt", 1.08, 27, 1.0),
                ("tt 1.32 V", "mos_tt", 1.32, 27, 1.0), ("ss", "mos_ss", 1.08, 125, 1.0),
                ("ff", "mos_ff", 1.32, -40, 1.0), ("ff hot", "mos_ff", 1.32, 125, 1.0),
                ("tt R −20 %", "mos_tt", 1.20, 27, 0.8), ("tt R +20 %", "mos_tt", 1.20, 27, 1.2)]


def pm(k):
    return f"sg13_lv_pmos w={2 * k:g}u l=2u ng={k}"


def nm(k):
    return f"sg13_lv_nmos w={k:g}u l=2u ng={k}"


def biasgen(rs=1.0):
    """Master current V_REF / R_B through PMOS mb0; the transconductor regulates vx = V_REF via pbias."""
    return (f"vref (vref 0) vsource dc={VREF}\n"
            f"mb0 (vx pbias vdd vdd) {pm(10)}\n"
            "vimb (vx vx2) vsource dc=0\n"
            f"rb (vx2 0) resistor r={RB * rs:.1f}\n"
            # non-inverting from vx to pbias: vx high -> pbias up -> less current (negative feedback). Its
            # tails (2 uA) become mirrors of the generator itself (use_bias), hence the start-up circuit.
            + S2.rr_ota("bg", "vx", "vref", "pbias", 2e-6)
            # NMOS reference for the sinks
            + f"mnf (nbias pbias vdd vdd) {pm(10)}\n"
            f"mnd (nbias nbias 0 0) {nm(10)}\n"
            # start-up: with no current nbias = 0, xsun is pulled up by the weak msu1 and msu3 pulls pbias down;
            # once current flows, msu2 holds xsun low and msu3 is off.
            # First run: msu1 0.5/10 um (about 1 uA) against msu2 1/2 um (1 uA): xsun stayed up at tt and ff,
            # msu3 kept sinking 7-13 uA from pbias and the regulation lost (master 16-25 uA). Now msu1 about
            # 0.1 uA and msu2 able to sink several uA.
            "msu1 (xsun 0 vdd vdd) sg13_lv_pmos w=0.15u l=20u\n"
            "msu2 (xsun nbias 0 0) sg13_lv_nmos w=4u l=1u\n"
            "msu3 (pbias xsun xsu3 0) sg13_lv_nmos w=1u l=0.5u\nvsu (xsu3 0) vsource dc=0\n")


def dac(code, out, tag=""):
    """I_cp DAC: (code + 1) x 25 uA, PMOS unit mirrors with series PMOS switches (gate 0 = on)."""
    s = ""
    for j, (m, bit) in enumerate(((1, None), (1, 0), (2, 1), (4, 2))):
        on = bit is None or (code >> bit) & 1
        s += (f"mdac{tag}{j} (xd{tag}{j} pbias vdd vdd) {pm(25 * m)}\n"
              f"msw{tag}{j} (xo{tag} {'0' if on else 'vdd'} xd{tag}{j} vdd) sg13_lv_pmos w={2 * m:g}u l=0.13u\n")
    return s + f"vidac{tag} (xo{tag} {out}) vsource dc=0\n"


def use_bias(text):
    """Replace the ideal current sources of the pump and of the transconductors by bias-generator outputs."""
    out = []
    for ln in text.splitlines():
        m = re.match(r"^iref \(vdd nb\) isource dc=(\S+)$", ln)
        if m:
            code = round(float(m.group(1)) / 25e-6) - 1
            assert 0 <= code <= 7, ln
            out.append(dac(code, "nb").rstrip())
            continue
        m = re.match(r"^iref(\w+)n \(vdd (\w+)\) isource dc=(\S+)$", ln)
        if m:
            k = round(float(m.group(3)) / 1e-6)
            out.append(f"mt{m.group(1)}n ({m.group(2)} pbias vdd vdd) {pm(k)}")
            continue
        m = re.match(r"^iref(\w+)p \((\w+) 0\) isource dc=(\S+)$", ln)
        if m:
            k = round(float(m.group(3)) / 1e-6)
            out.append(f"mt{m.group(1)}p ({m.group(2)} nbias 0 0) {nm(k)}")
            continue
        out.append(ln)
    return "\n".join(out) + "\n"


def tails_load():
    """The four tail outputs into the devices they feed in the pump (probed)."""
    s = ""
    for i, k in ((1, 2), (2, 10)):
        s += (f"mtl{i} (xtl{i} pbias vdd vdd) {pm(k)}\nvtl{i} (xtl{i} tl{i}) vsource dc=0\n"
              f"mtl{i}d (tl{i} tl{i} 0 0) sg13_lv_nmos w=2u l=1u\n")
    for i, k in ((3, 2), (4, 10)):
        s += (f"mtl{i} (xtl{i} nbias 0 0) {nm(k)}\nvtl{i} (tl{i} xtl{i}) vsource dc=0\n"
              f"mtl{i}d (tl{i} tl{i} vdd vdd) sg13_lv_pmos w=4u l=1u\n")
    return s


def sim(name, mos, temp, body, analysis, raw, cap="cap_typ"):
    from vacask.rawfile import rawread
    with open(os.path.join(OUT, name + ".sim"), "w") as fh:
        fh.write(HEADER4.format(title=f"P2.5 step 4: {name}", mos=mos, cap=cap))
        fh.write(body)
        fh.write(f"\ncontrol\n  abort always\n  options rawfile=\"binary\"\n  options temp={temp}\n  {analysis}\nendc\n")
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(f"vacask {name}.sim failed; end of out/{name}.log: " + open(log).read()[-500:])
    return rawread(os.path.join(OUT, raw)).get()


def rises(t, v, th, falling=False):
    if falling:
        v = -v
        th = -th
    i = np.where((v[:-1] < th) & (v[1:] >= th))[0]
    return t[i] + (th - v[i]) * (t[i + 1] - t[i]) / (v[i + 1] - v[i])


# ---------------------------------------------------------------------------------------------------- bias
def check_bias():
    print("## Bias generator, DC [SCH]\n")
    print(f"Master current V_REF / R_B = {VREF} V / {RB/1e3:.0f} kΩ = {VREF/RB*1e6:.0f} µA. I_cp from the DAC into the "
          "pump's NMOS diode (sized per code as in step 2a); tails into the devices they feed. 'Ratio' = output / "
          "(nominal ratio × measured master) − 1 (mirror accuracy); 'abs.' = output / nominal − 1 (includes R_B).\n")
    print("| Case | Master (µA) | vx − V_REF (mV) | pbias / nbias (V) | I_cp code 0 / 3 / 7 (µA) | I_cp ratio error, "
          "worst of 8 codes | I_cp abs. error at code 3 | Tails 2 / 10 µA src, 2 / 10 µA sink (µA) | Tail ratio error, worst | "
          "Start-up device (nA) |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for lab, mos, vdd, temp, rs in BIAS_CORNERS:
        body = f"vdd (vdd 0) vsource dc={vdd}\n" + biasgen(rs) + tails_load()
        for c in range(8):
            wn = 15 * (c + 1)
            body += dac(c, f"nbl{c}", f"c{c}") + f"mnbl{c} (nbl{c} nbl{c} 0 0) sg13_lv_nmos w={wn:g}u l=2u ng={S2.fn(wn, 1.5)}\n"
        try:
            d = sim("bias_" + re.sub(r"[^A-Za-z0-9]+", "_", lab.replace("−", "m").replace("+", "p")), mos, temp,
                    use_bias(body), "analysis op1 op", "op1.raw")
        except RuntimeError as e:
            print(f"| {lab} | error: {str(e)[-120:]!r} |")
            continue
        g = lambda k: float(np.real(d[k])[0])   # noqa: E731
        im = abs(g("vimb:flow(br)"))
        icp = [abs(g(f"vidacc{c}:flow(br)")) for c in range(8)]
        rerr = max(abs(icp[c] / ((c + 1) * 2.5 * im) - 1) for c in range(8))
        tl = [abs(g(f"vtl{i}:flow(br)")) for i in range(1, 5)]
        terr = max(abs(tl[i] / (k / 10 * im) - 1) for i, k in enumerate((2, 10, 2, 10)))
        print(f"| {lab} | {im*1e6:.2f} | {(g('vx') - VREF)*1e3:+.1f} | {g('pbias'):.3f} / {g('nbias'):.3f} | "
              f"{icp[0]*1e6:.1f} / {icp[3]*1e6:.1f} / {icp[7]*1e6:.1f} | {rerr*100:.1f} % | {(icp[3]/100e-6 - 1)*100:+.1f} % | "
              + " / ".join(f"{x*1e6:.2f}" for x in tl) + f" | {terr*100:.1f} % | {abs(g('vsu:flow(br)'))*1e9:.1f} |")
    print()


# --------------------------------------------------------------------------------------------------- start
def check_start():
    print("## Start-up with a supply ramp [SCH]\n")
    print("Supply 0 → V_DD in t_ramp (from 10 ns); bias generator with the I_cp DAC (code 3) and the tails as loads. "
          "Settled = master current within 2 % of its final value from then on.\n")
    print("| Corner | t_ramp | Master at the end (µA) | Settled after the ramp ends (µs) | Start-up device at the end (nA) |")
    print("|---|---|---|---|---|")
    for lab, mos, vdd, temp, _ in [c for c in BIAS_CORNERS if c[0] in ("tt", "ss", "ff")]:
        for tr in (0.1e-6, 20e-6):
            body = (f'vdd (vdd 0) vsource type="pulse" val0=0 val1={vdd} delay=10n rise={tr:.3e} fall=1n width=1\n'
                    + biasgen() + tails_load() + dac(3, "nbl", "s") + "mnbl (nbl nbl 0 0) sg13_lv_nmos w=60u l=2u ng=40\n")
            stop = 10e-9 + tr + 5e-6
            try:
                d = sim(f"start_{lab}_{tr*1e6:g}", mos, temp, use_bias(body),
                        f"analysis tr tran stop={stop:.4e} step={stop/4000:.3e} maxstep={min(5e-9, tr/50):.3e}", "tr.raw")
            except RuntimeError as e:
                print(f"| {lab} | {tr*1e6:g} µs | error: {str(e)[-120:]!r} |")
                continue
            t = np.real(d["time"])
            im = np.abs(np.real(d["vimb:flow(br)"]))
            fin = im[-1]
            bad = np.where(np.abs(im - fin) > 0.02 * fin)[0]
            ts = (t[bad[-1]] - 10e-9 - tr) * 1e6 if len(bad) else 0.0
            print(f"| {lab} | {tr*1e6:g} µs | {fin*1e6:.2f} | {max(ts, 0):.2f} | {abs(np.real(d['vsu:flow(br)'])[-1])*1e9:.1f} |")
    print()


# ----------------------------------------------------------------------------------------------------- win
def mono(n, inp, strobe):
    """Window delay cell: input buffer, flip-flop set by the rising edge, MIM ramp, threshold, self reset."""
    i1, ib, q, qb, rp, c1, d1, rs = (f"x{n}{s}" for s in ("i1", "in", "q", "qb", "rp", "c1", "d1", "rs"))
    return (S2.inv(f"{n}b1", inp, i1, 1, 2) + S2.inv(f"{n}b2", i1, ib, 2, 4)
            + S2.dff_r(f"{n}f", ib, rs, q) + S2.inv(f"{n}qi", q, qb, 1, 2)
            + f"m{n}rs ({rp} {qb} 0 0) sg13_lv_nmos w=1u l=0.13u\n"           # ramp held at 0 while q = 0
            + f"m{n}ch ({rp} pbias vdd vdd) {pm(WI)}\n"                         # charging current
            + f"x{n}c ({rp} 0 0) cap_rfcmim w={CW:g}u l={CW:g}u\n"
            + S2.inv(f"{n}c1", rp, c1, 0.5, 1) + S2.inv(f"{n}c2", c1, strobe, 1, 2)
            + S2.inv(f"{n}d1", strobe, d1) + S2.inv(f"{n}d2", d1, rs))         # strobe resets the flip-flop


WIN_CASES = [("tt", "mos_tt", 1.20, 27, "cap_typ", 1.0), ("tt 1.08 V", "mos_tt", 1.08, 27, "cap_typ", 1.0),
             ("tt 1.32 V", "mos_tt", 1.32, 27, "cap_typ", 1.0), ("tt R −20 %", "mos_tt", 1.20, 27, "cap_typ", 0.8),
             ("tt R +20 %", "mos_tt", 1.20, 27, "cap_typ", 1.2), ("ss", "mos_ss", 1.08, 125, "cap_typ", 1.0),
             ("ff", "mos_ff", 1.32, -40, "cap_typ", 1.0),
             ("slowest: ss, C wcs, R +20 %", "mos_ss", 1.08, 125, "cap_wcs", 1.2),
             ("ss, C bcs, R −20 %", "mos_ss", 1.08, 125, "cap_bcs", 0.8),
             ("ff, C wcs, R +20 %", "mos_ff", 1.32, -40, "cap_wcs", 1.2),
             ("fastest: ff, C bcs, R −20 %", "mos_ff", 1.32, -40, "cap_bcs", 0.8)]


def check_win():
    print(f"## Window delay cell [SCH] (MIM {CW:g} × {CW:g} µm, {WI} µA)\n")
    print("Delay from the buffered input edge to the strobe edge (V_DD / 2), mean of the last 6 cycles; reference = "
          "50 % clock, divider = 2.5 ns pulse. Allowed 5–12 ns, target 7 ns. C wcs / bcs: MIM corners; R ±20 %: R_B "
          "(sets the charging current).\n")
    print("| Case | Delay, reference (ns) | Delay, divider (ns) | Strobe pulse (ps) | Pass |")
    print("|---|---|---|---|---|")
    worst = [1e9, 0]
    for lab, mos, vdd, temp, cap, rs in WIN_CASES:
        body = (f"vdd (vdd 0) vsource dc={vdd}\n"
                f"model sqref sqclk f={F_REF:.6e} td=2e-9 vh={vdd}\nxref (refc) sqref\n"
                f"model pdiv pulse2 f={F_REF:.6e} td=5e-9 w=2.5e-9 vh={vdd}\nxdiv (divc) pdiv\n"
                + biasgen(rs) + mono("wr", "refc", "su") + mono("wd", "divc", "sd"))
        name = "win_" + re.sub(r"[^A-Za-z0-9]+", "_", lab.replace("−", "m").replace("+", "p"))
        try:
            d = sim(name, mos, temp, use_bias(body), f"analysis tr tran stop={12 / F_REF:.4e} step=10p maxstep=10p",
                    "tr.raw", cap=cap)
        except RuntimeError as e:
            print(f"| {lab} | error: {str(e)[-120:]!r} |")
            continue
        t = np.real(d["time"])
        res = []
        for inp, st in (("xwrin", "su"), ("xwdin", "sd")):
            ti = rises(t, np.real(d[inp]), vdd / 2)
            ts = rises(t, np.real(d[st]), vdd / 2)
            tf = rises(t, np.real(d[st]), vdd / 2, falling=True)
            dl = []
            for x in ts[-6:]:
                prev = ti[ti < x]
                if len(prev):
                    dl.append(x - prev[-1])
            pw = [f[0] - x for x in ts[-6:] for f in [tf[tf > x]] if len(f)]
            res.append((np.mean(dl) if dl else float("nan"), np.mean(pw) if pw else float("nan")))
        ok = all(5e-9 <= r[0] <= 12e-9 for r in res)
        worst = [min(worst[0], *(r[0] for r in res)), max(worst[1], *(r[0] for r in res))]
        print(f"| {lab} | {res[0][0]*1e9:.2f} | {res[1][0]*1e9:.2f} | {min(res[0][1], res[1][1])*1e12:.0f} | "
              f"{'yes' if ok else '**NO**'} |")
    print(f"\nRange over all cases: {worst[0]*1e9:.2f}–{worst[1]*1e9:.2f} ns (allowed 5–12 ns).\n")


# ---------------------------------------------------------------------------------------------------- hold
# Loop filter: D19 (P2.6 step 1, 60 kHz / 55 deg). The first runs used the P2.2 values C1 39 pF, C2 355 pF,
# R1 9.5 kOhm, R3 34 kOhm, C3 3.9 pF (sized with a 2 pi error); option 'lf22' brings them back.
LF = (dict(C1=39e-12, C2=355e-12, R1=9.5e3, R3=34e3, C3=3.9e-12) if "lf22" in ARGS
      else dict(C1=30.8e-12, C2=465.2e-12, R1=22.9e3, R3=107.8e3, C3=3.08e-12))


def hold_net(vdd, v0=None, t0=0.5e-6, held=True, vfix=None):
    """Loop filter (n1 = CP output, n2 = C2 node, n3 = V_tune at the VCO) with the hold switches and divider."""
    # first run: the supply source was missing (divider top switch and inverter unpowered, V_tune held at 0)
    s = f"vdd (vdd 0) vsource dc={vdd}\n"
    s += (f"c1 (n1 0) capacitor c={LF['C1']:.4e}\nr1 (n1 n2) resistor r={LF['R1']:.1f}\n"
         f"c2 (n2 0) capacitor c={LF['C2']:.4e}\nr3 (n1 n3) resistor r={LF['R3']:.1f}\n"
         f"c3 (n3 0) capacitor c={LF['C3']:.4e}\n" if vfix is None else "")
    if vfix is not None:      # DC leakage check: both switched nodes held, current probed
        s += f"vn1 (n1 0) vsource dc={vfix}\nvn2 (n2 0) vsource dc={vfix}\n"
    else:
        s += "ioff (n1 0) isource dc=1e-5\n"                              # D18 offset sink, on during hold
    if v0 is not None:
        s += (f"vpre (pre 0) vsource dc={v0}\nmodel tswp tsw t0={t0:.3e} ron=10 roff=1e12\n"
              "xp1 (n1 pre) tswp\nxp2 (n2 pre) tswp\nxp3 (n3 pre) tswp\n")
        s += f'vh (hold 0) vsource type="pulse" val0=0 val1={vdd} delay={t0:.3e} rise=1n fall=1n width=1\n'
    else:
        s += f"vh (hold 0) vsource dc={vdd if held else 0}\n"
    s += S2.inv("hi", "hold", "holdb", 1, 2)
    # divider V_DD / 2, on only while holding
    s += ("mdt (xdt holdb vdd vdd) sg13_lv_pmos w=10u l=0.13u\nrd1 (xdt vmid) resistor r=1000\n"
          "rd2 (vmid xdb) resistor r=1000\nmdb (xdb hold 0 0) sg13_lv_nmos w=5u l=0.13u\n")
    s += S2.tg("h1", "n1", "vmid", "hold", "holdb", 10, 20) + S2.tg("h2", "n2", "vmid", "hold", "holdb", 10, 20)
    return s


def check_hold():
    print("## V_tune hold switch [SCH]\n")
    print("Loop filter precharged to V0, hold from t0. V_tune = C3 node (VCO side). Error against its final value; "
          "first trial: settle 64 reference cycles (1.78 µs), then count 128 cycles (3.56 µs); for comparison the "
          "step-2c timing (settle 16 cycles = 0.44 µs). Limit: mean error over the first count ≤ 10 mV.\n")
    print("| Corner | V0 (V) | V_tune held (V) | Error at 0.44 / 1.78 µs (mV) | Mean error over the count, settle 16 / 64 "
          "cycles (mV) | Time constant (µs) | Pass (64) |")
    print("|---|---|---|---|---|---|---|")
    T = 1 / F_REF
    t0 = 0.5e-6
    for lab, mos, vdd, temp, _ in [c for c in BIAS_CORNERS if c[0] in ("tt", "ss", "ff")]:
        for v0 in (0.0, 0.25, 0.95, vdd):
            stop = t0 + 64 * T + 128 * T + 0.5e-6
            try:
                d = sim(f"hold_{lab}_{v0:.2f}", mos, temp, hold_net(vdd, v0, t0),
                        f"analysis tr tran stop={stop:.4e} step=2n maxstep=5n", "tr.raw")
            except RuntimeError as e:
                print(f"| {lab} | {v0} | error: {str(e)[-120:]!r} |")
                continue
            t = np.real(d["time"]) - t0
            v = np.real(d["n3"])
            vf = v[-1]
            e = lambda tt: abs(np.interp(tt, t, v) - vf) * 1e3   # noqa: E731
            def mean_err(ts):
                m = (t >= ts) & (t <= ts + 128 * T)
                return np.trapezoid(np.abs(v[m] - vf), t[m]) / (t[m][-1] - t[m][0]) * 1e3
            m16, m64 = mean_err(16 * T), mean_err(64 * T)
            # time constant from the 1/e point of the step
            dv0 = v[np.searchsorted(t, 0)] - vf
            idx = np.where((t > 0) & (np.abs(v - vf) < abs(dv0) / math.e))[0]
            tau = t[idx[0]] * 1e6 if len(idx) and abs(dv0) > 1e-3 else float("nan")
            print(f"| {lab} | {v0:.2f} | {vf:.3f} | {e(16*T):.1f} / {e(64*T):.1f} | {m16:.1f} / {m64:.1f} | "
                  f"{tau:.2f} | {'yes' if m64 <= 10 else '**NO**'} |")
    print("\nSwitch leakage with hold off (both switched nodes held at V, divider off), into the loop filter:\n")
    print("| Corner | 0.25 V (nA) | 0.6 V (nA) | 0.95 V (nA) |")
    print("|---|---|---|---|")
    for lab, mos, vdd, temp in (("ff hot", "mos_ff", 1.32, 125), ("tt", "mos_tt", 1.20, 27), ("ss", "mos_ss", 1.08, 125)):
        row = []
        for vf in (0.25, 0.6, 0.95):
            try:
                d = sim(f"leak_{lab.replace(' ', '_')}_{vf}", mos, temp, hold_net(vdd, held=False, vfix=vf),
                        "analysis op1 op", "op1.raw")
                row.append(f"{(abs(np.real(d['vn1:flow(br)'])[0]) + abs(np.real(d['vn2:flow(br)'])[0]))*1e9:.1f}")
            except RuntimeError:
                row.append("error")
        print(f"| {lab} | " + " | ".join(row) + " |")
    print()


# ----------------------------------------------------------------------------------------------------- lin
def check_lin():
    print("## Pump linearity with the bias generator [SCH]\n")
    print("Step-3 check (offset pair on, I_cp code 3 = 100 µA) with the DAC, the four amplifier tails and the "
          "master current from the bias generator instead of ideal sources. Step 3 nominal: INL 0.6 / 0.4 / 2.0 / "
          "0.7 ps, lock point 2.76 / 2.76 / 3.05 / 2.75 ns.\n")
    print("| Corner | V_tune | INL (ps) | Lock point (ns) | Slope | Offset current (µA) | nb min / mean / max (V) | "
          "Supply (mA) |")
    print("|---|---|---|---|---|---|---|---|")
    dts = [1e-9, 2e-9, 3e-9, 4e-9, 5e-9]
    for cname, vt in (("tt", 0.25), ("tt", 0.6), ("tt", 0.95), ("ss", 0.6), ("ff", 0.6)):
        corner = next(c for c in S2.CORNERS if c[0] == cname)
        qs, st = [], None
        try:
            for dt in dts:
                q, _, _, _, st = S2.run(f"lin4_{cname}_{vt:.2f}_{dt*1e9:.0f}", corner, vt, dt, S2.ICP, ioff=True,
                                        post=lambda x: use_bias(x + biasgen()))
                qs.append(q / S2.ICP)
        except RuntimeError as e:
            print(f"| {cname} | {vt} | error: {str(e)[-120:]!r} |")
            continue
        da, qa = np.array(dts), np.array(qs)
        k, c = np.polyfit(da, qa, 1)
        inl = np.max(np.abs(qa - (k * da + c)))
        print(f"| {cname} | {vt} | {inl*1e12:.1f} | {-c/k*1e9:.2f} | {k:.3f} | {st['ioff']*1e6:.1f} | "
              + " / ".join(f"{x:.3f}" for x in st["nb"]) + f" | {st['ivdd']*1e3:.2f} |")
    print()


def main():
    os.makedirs(OUT, exist_ok=True)
    modes = [m for m in ("bias", "start", "win", "hold", "lin") if m in ARGS] or ["bias", "start", "win", "hold"]
    print("# P2.5 step 4 — bias generator, window delay cell, hold switch\n")
    for m in modes:
        globals()[f"check_{m}"]()


if __name__ == "__main__":
    main()
