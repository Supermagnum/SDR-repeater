#!/usr/bin/env python3
"""P2.5 step 2a: PFD + charge pump (spec/pll-topology.md §2, §7).

Run inside the container from this folder:

    mkdir -p out && python3 -u run_step2.py | tee out/summary.txt    # 3 corners x 3 V_tune x 9 phase offsets
    python3 -u run_step2.py tt                                        # one corner: tt / ss / ff
    python3 -u run_step2.py icp=200                                   # charge-pump current in uA (default 100)

Circuit (transistor level unless noted):
  clocks  REF and DIV: ideal 36 MHz near-squares (DIV delayed by dt), each sharpened by two inverters
  PFD     two static master-slave D flip-flops (D = 1, transmission gates, NOR-based asynchronous reset), reset
          = AND(UP, DN) through a delay chain (NAND + 3 inverters, about 150-250 ps) so both pump switches turn
          fully on every cycle (no dead zone)
  CP      long-channel current sources (L = 2 um; NMOS 15 um and PMOS 120 um per 25 uA - PMOS twice as wide as
          in step 1 for headroom), current steering: each source goes to the output (UP / DN) or to a dummy node
          held at V_tune by a unity-gain buffer (no charge sharing); a replica branch (both switches on) and an
          amplifier set the PMOS gate so that replica up = replica down at V_tune (D18). The two amplifiers are
          behavioural (Verilog-A: 100 V/V transconductor, 10 uS, output clamped to the supply,
          Miller-compensated with the replica stage; ideal follower); their transistor-level design follows once the pump works.
  output  held by an ideal source at V_tune (0.25 / 0.6 / 0.95 V); its current, averaged over 10 reference
          cycles, gives the net charge per cycle Q(dt).
Results per case: Q/I_cp against dt (ideal: equal to dt), the offset at dt = 0 (residual up/down mismatch x the
reset pulse), the slope (pump gain) and the smallest |dt| that still gives the right sign (dead zone).
The offset current of D18 is left out here (it only adds a constant). Results are [SCH].
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.environ.setdefault("PDK_ROOT", "/foss/pdks")
os.environ.setdefault("PDK", "ihp-sg13g2")
sys.path.append("/foss/tools/vacask/lib/vacask/python")

CORNERS = [("tt", "mos_tt", 1.20, 27), ("ss", "mos_ss", 1.08, 125), ("ff", "mos_ff", 1.32, -40)]
F_REF = 36e6
DTS = [-200e-12, -50e-12, -10e-12, -3e-12, 0.0, 3e-12, 10e-12, 50e-12, 200e-12]
VTS = [0.25, 0.6, 0.95]
ICP = next((float(a[4:]) for a in sys.argv[1:] if a.startswith("icp=")), 100.0) * 1e-6

HEADER = """{title}

include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section={mos}

load "resistor.osdi"
load "capacitor.osdi"

model resistor  resistor
model capacitor capacitor
model vsource   vsource
model isource   isource

embed "pllva.va" <<<FILE
`include "constants.vams"
`include "disciplines.vams"
module sqclk(p);
    inout p;
    electrical p;
    parameter real f = 36e6;
    parameter real td = 0;
    parameter real vh = 1.2;
    analog V(p) <+ 0.5 * vh * (1 + tanh(8 * sin(2 * `M_PI * f * ($abstime - td))));
endmodule
module ota(p, n, o);
    inout p, n, o;
    electrical p, n, o;
    parameter real a = 100;
    parameter real vh = 1.2;
    parameter real rout = 1e7;
    // voltage gain a, output clamped to 0 ... vh, output resistance rout (transconductance a / rout)
    analog I(o) <+ (V(o) - 0.5 * vh * (1 + tanh(2 * a * (V(p) - V(n)) / vh))) / rout;
endmodule
module follower(i, o);
    inout i, o;
    electrical i, o;
    analog V(o) <+ V(i);
endmodule
>>>FILE
load "pllva.va"
model follower follower
"""


def inv(n, a, y, wn=0.5, wp=1.0):
    return (f"x{n}p ({y} {a} vdd vdd) sg13_lv_pmos w={wp:g}u l=0.13u\n"
            f"x{n}n ({y} {a} 0 0) sg13_lv_nmos w={wn:g}u l=0.13u\n")


def tg(n, a, b, cn, cp, wn=1.0, wp=2.0):
    """Transmission gate between a and b, on when cn = 1 (NMOS gate) and cp = 0 (PMOS gate)."""
    return (f"x{n}n ({a} {cn} {b} 0) sg13_lv_nmos w={wn:g}u l=0.13u\n"
            f"x{n}p ({a} {cp} {b} vdd) sg13_lv_pmos w={wp:g}u l=0.13u\n")


def nor2(n, a, b, y):
    return (f"x{n}pa (x_{n}m {a} vdd vdd) sg13_lv_pmos w=2u l=0.13u\n"
            f"x{n}pb ({y} {b} x_{n}m vdd) sg13_lv_pmos w=2u l=0.13u\n"
            f"x{n}na ({y} {a} 0 0) sg13_lv_nmos w=0.5u l=0.13u\n"
            f"x{n}nb ({y} {b} 0 0) sg13_lv_nmos w=0.5u l=0.13u\n")


def nand2(n, a, b, y):
    return (f"x{n}pa ({y} {a} vdd vdd) sg13_lv_pmos w=1u l=0.13u\n"
            f"x{n}pb ({y} {b} vdd vdd) sg13_lv_pmos w=1u l=0.13u\n"
            f"x{n}na ({y} {a} x_{n}m 0) sg13_lv_nmos w=1u l=0.13u\n"
            f"x{n}nb (x_{n}m {b} 0 0) sg13_lv_nmos w=1u l=0.13u\n")


def dff_r(n, ck, r, q):
    """Positive-edge D flip-flop with D = 1 and active-high asynchronous reset (static, master-slave).
    Master value v: x = ck ? v : 1; v = NOR(NOT x, r). Slave: y = ck ? v : q; q = NOR(NOT y, r)."""
    c, cb = f"x_{n}c", f"x_{n}cb"
    x, xb, v, y, yb = (f"x_{n}{s}" for s in ("x", "xb", "v", "y", "yb"))
    return (inv(f"{n}c1", ck, cb) + inv(f"{n}c2", cb, c)
            + tg(f"{n}t1", "vdd", x, cb, c)            # clock low: D (= 1) into the master
            + tg(f"{n}t2", v, x, c, cb)                # clock high: master holds
            + inv(f"{n}i1", x, xb) + nor2(f"{n}n1", xb, r, v)
            + tg(f"{n}t3", v, y, c, cb)                # clock high: slave follows the master
            + tg(f"{n}t4", q, y, cb, c)                # clock low: slave holds
            + inv(f"{n}i2", y, yb) + nor2(f"{n}n2", yb, r, q))


def pfd(vdd):
    s = (inv("rb1", "ref0", "ref1", 1, 2) + inv("rb2", "ref1", "ref", 2, 4)
         + inv("db1", "div0", "div1", 1, 2) + inv("db2", "div1", "div", 2, 4))
    s += dff_r("fu", "ref", "rst", "up") + dff_r("fd", "div", "rst", "dn")
    s += nand2("ra", "up", "dn", "x_r0")
    # Second run: NAND + 5 inverters with 5 fF loads gave a 610-640 ps reset pulse (target 150-250 ps).
    # Eighth run: the last inverter became a NAND with a power-on reset (porb low for the first 1.5 ns), so
    # rst = AND(UP, DN) OR por: the flip-flops start from a defined state. Seventh run: at the slow corner
    # some runs had DN stuck high for the whole simulation (the static latches started from the operating
    # point in an undefined state); the chip's PFD gets the same reset from the sequencer (en_pll).
    s += inv("rd0", "x_r0", "x_r1") + inv("rd1", "x_r1", "x_r2") + nand2("rd2", "x_r2", "porb", "rst")
    s += f'vpor (porb 0) vsource type="pulse" val0=0 val1={vdd} delay=1.5n rise=0.1n fall=0.1n width=1\n'
    return s


def charge_pump(icp):
    u = icp / 25e-6
    wn, wp = 15 * u, 120 * u
    swn, swp = max(2.0, 2 * u), max(6.0, 6 * u)
    return (
        # Second run: offset +131 ps at dt = 0, far more than the up/down current difference explains. The
        # output switch and the dummy switch were driven one inverter delay apart, so on each UP edge the
        # PMOS source floated (both its switches off) and later dumped that charge into the output. Now each
        # switch pair is driven by complementary signals of equal delay: an inverter for one, an always-on
        # transmission gate of matched delay for the other, both sized for the switch gates.
        # Fourth run: UP and DN first buffered by two inverters each (the PFD outputs carried unequal switch-gate
        # loads through the transmission gates: reset pulse UP 380 / DN 450 ps)
        inv("bu1", "up", "x_up1", 1, 2) + inv("bu2", "x_up1", "upq", 2, 4)
        + inv("bd1", "dn", "x_dn1", 1, 2) + inv("bd2", "x_dn1", "dnq", 2, 4)
        + inv("su", "upq", "upb", 2, 4) + tg("sut", "upq", "upd", "vdd", "0", 2, 4)
        + inv("sd", "dnq", "dnb", 2, 4) + tg("sdt", "dnq", "dnd", "vdd", "0", 2, 4)
        # NMOS bias (fixed): reference current into a diode
        + f"iref (vdd nb) isource dc={icp:.4e}\n"
        + f"mnb (nb nb 0 0) sg13_lv_nmos w={wn:g}u l=2u\n"
        # main NMOS sink, steered to the output (DN) or to the dummy node (DN low)
        + f"mn1 (nz0 nb 0 0) sg13_lv_nmos w={wn:g}u l=2u\nvimd (nz nz0) vsource dc=0\n"
        + f"mn2 (vt dnd nz 0) sg13_lv_nmos w={swn:g}u l=0.13u\n"
        + f"mn3 (vdm dnb nz 0) sg13_lv_nmos w={swn:g}u l=0.13u\n"
        # main PMOS source, gate pg from the replica amplifier; to the output (UP) or the dummy node
        + f"mp1 (pz0 pg vdd vdd) sg13_lv_pmos w={wp:g}u l=2u\nvimu (pz0 pz) vsource dc=0\n"
        + f"mp2 (vt upb pz vdd) sg13_lv_pmos w={swp:g}u l=0.13u\n"
        + f"mp3 (vdm upd pz vdd) sg13_lv_pmos w={swp:g}u l=0.13u\n"
        # dummy node held at V_tune by a unity-gain buffer (behavioural)
        + "xbuf (vt vdm) follower\n"
        # replica: both switches on, its node vr compared with V_tune; the amplifier drives pg
        + f"mrn1 (rnz0 nb 0 0) sg13_lv_nmos w={wn:g}u l=2u\nvird (rnz rnz0) vsource dc=0\n"
        + f"mrn2 (vr vdd rnz 0) sg13_lv_nmos w={swn:g}u l=0.13u\n"
        + f"mrp1 (rpz0 pg vdd vdd) sg13_lv_pmos w={wp:g}u l=2u\nviru (rpz0 rpz) vsource dc=0\n"
        + f"mrp2 (vr 0 rpz vdd) sg13_lv_pmos w={swp:g}u l=0.13u\n"
        + "xamp (vr vt pg) ota\n"
        # First run: a transconductor, Miller-compensated from pg to vr. Second run: the transconductor version let pg leave the supply range at V_tune 0.25 V (replica at
        # the rail, +937 mV). Now an ideal voltage amplifier, 60 dB, output clamped to 0 ... V_DD; with the
        # replica node vr as the only pole the loop is single-pole and stable.
        # Third run: with 60 dB and 0.5 pF the replica loop crossed over near 400 GHz, so the simulator crawled
        # (one run > 10 min). Now 30 V/V and 20 pF on vr: loop gain at DC still about 30 x g_m x r_out ~ 8000,
        # crossover about 300 MHz.
        # Fifth run: pg swung 0.2-1.19 V every cycle (replica and main up currents peaking at 7-9 mA): the ideal
        # fast amplifier made the replica loop oscillate. Sixth run: a proper two-stage compensation - the
        # amplifier is a transconductor (gain 100, 10 MOhm output, i.e. 10 uS), Miller capacitor 2 pF from pg to
        # vr; with the 20 pF of PMOS gates on pg the loop crosses over near 0.8 MHz, second pole about 7 MHz.
        # The replica only has to follow V_tune, which moves slowly in a locked loop.
        + "ccm (pg vr) capacitor c=2p\ncvr (vr 0) capacitor c=0.2p\n")


def offset_sink(icp, frac=0.2):
    """D18 offset current: an NMOS sink from V_tune mirrored from the pump bias nb (frac x I_cp), on all the
    time, so the loop locks with UP pulses about frac x T_ref long and the pump works on one side only."""
    u = icp / 25e-6
    # Eighth run: sized 0.08 the lock point came out at 0.75-1.05 ns instead of 2.2 ns (about 3.5 uA instead
    # of 8 uA - the narrow device does not mirror the 60 um diode); now 0.2 and measured through a probe
    return f"mof (vof nb 0 0) sg13_lv_nmos w={15 * u * frac:.3f}u l=2u\nviof (vt vof) vsource dc=0\n"


def run(name, corner, vt, dt, icp, ioff=False):
    from vacask.rawfile import rawread
    _, mos, vdd, temp = corner
    path = os.path.join(OUT, name + ".sim")
    ncyc = 25
    with open(path, "w") as fh:
        fh.write(HEADER.format(title=f"P2.5 step 2a: {name}", mos=mos))
        # Verilog-A parameters are model parameters in VACASK (first run: "parameter not found" on the
        # instance), so each clock gets its own model
        fh.write(f"model ota ota a=100 vh={vdd} rout=1e7\n"
                 f"model sqref sqclk f={F_REF:.6e} td=2e-9 vh={vdd}\n"
                 f"model sqdiv sqclk f={F_REF:.6e} td={2e-9 + dt:.6e} vh={vdd}\n"
                 f"vdd (vdd 0) vsource dc={vdd}\n"
                 f"xref (ref0) sqref\n"
                 f"xdiv (div0) sqdiv\n"
                 f"vtn (vt 0) vsource dc={vt}\n" + pfd(vdd) + charge_pump(icp) + (offset_sink(icp) if ioff else ""))
        fh.write("\ncontrol\n  abort always\n  options rawfile=\"binary\"\n"
                 f"  options temp={temp}\n"
                 f"  analysis tr tran stop={ncyc / F_REF:.6e} step=5p maxstep=5p\nendc\n")
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(f"vacask {name}.sim failed; end of out/{name}.log: " + open(log).read()[-600:])
    d = rawread(os.path.join(OUT, "tr.raw")).get()
    t = np.real(d["time"])
    T = 1 / F_REF
    m = t >= t[-1] - 10 * T
    i = np.real(d["vtn:flow(br)"])
    q = np.trapezoid(i[m], t[m]) / 10                  # net charge per cycle into the V_tune source
    # pulse widths in the last cycle
    w = {}
    for sig in ("up", "dn"):
        v = np.real(d[sig])
        mm = t >= t[-1] - T
        tt = np.linspace(t[mm][0], t[mm][-1], 100000)
        w[sig] = float(np.mean(np.interp(tt, t[mm], v[mm]) > vdd / 2)) * T
    # Fifth run: waveform statistics over the last 10 cycles (min / mean / max) of the nodes that set the
    # currents, and the mean source currents - the DC check was perfect (match within 0.1 %), so the fault
    # is dynamic
    stats = {}
    for k in ("pg", "vr", "nb", "pz", "nz"):
        v = np.real(d[k])[m]
        stats[k] = (v.min(), np.trapezoid(v, t[m]) / (t[m][-1] - t[m][0]), v.max())
    for k in ("vimu", "vimd", "viru", "vird"):
        v = np.abs(np.real(d[f"{k}:flow(br)"])[m])
        stats[k] = (v.min(), np.trapezoid(v, t[m]) / (t[m][-1] - t[m][0]), v.max())
    if ioff:
        stats["ioff"] = float(np.mean(np.abs(np.real(d["viof:flow(br)"])[m])))
    return q, w, float(np.real(d["pg"])[-1]), float(np.real(d["vr"])[-1]), stats


def check_dc(corners, icp):
    """Fourth run: DC check of the pump with UP / DN forced (no PFD): output current, the four source currents,
    the PMOS gate pg and the replica node. Third run gave gains of 0.4-0.8 and offsets of -370 ... +180 ps,
    and the replica 15-75 mV off V_tune, which the transient alone cannot explain."""
    from vacask.rawfile import rawread
    print("## DC check: currents with UP / DN forced [SCH]\n")
    print("Currents in µA (positive = into V_tune for I_out; source currents as magnitudes). Ideal: UP only → "
          f"I_out = +{icp*1e6:.0f}; DN only → −{icp*1e6:.0f}; both → 0.\n")
    print("| Corner | V_tune | UP, DN | I_out | Main up | Main down | Replica up | Replica down | pg (V) | vr − V_tune (mV) |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for corner in corners:
        _, mos, vdd, temp = corner
        for vt in VTS:
            for uv, dv in ((1, 0), (0, 1), (1, 1), (0, 0)):
                name = f"dc_{corner[0]}_{vt:.2f}_{uv}{dv}"
                with open(os.path.join(OUT, name + ".sim"), "w") as fh:
                    fh.write(HEADER.format(title=f"P2.5 step 2a: {name}", mos=mos))
                    fh.write(f"model ota ota a=100 vh={vdd} rout=1e7\nvdd (vdd 0) vsource dc={vdd}\nvtn (vt 0) vsource dc={vt}\n"
                             f"vup (up 0) vsource dc={uv * vdd}\nvdn (dn 0) vsource dc={dv * vdd}\n" + charge_pump(icp))
                    fh.write(f"\ncontrol\n  abort always\n  options rawfile=\"binary\"\n  options temp={temp}\n"
                             "  analysis op1 op\nendc\n")
                with open(os.path.join(OUT, name + ".log"), "w") as fh:
                    r = subprocess.run(["vacask", name + ".sim"], cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
                if r.returncode:
                    print(f"| {corner[0]} | {vt} | {uv}, {dv} | error |")
                    continue
                d = rawread(os.path.join(OUT, "op1.raw")).get()
                g = lambda k: float(np.real(d[k])[0])   # noqa: E731
                print(f"| {corner[0]} | {vt} | {uv}, {dv} | {g('vtn:flow(br)')*1e6:+.1f} | {abs(g('vimu:flow(br)'))*1e6:.1f} | "
                      f"{abs(g('vimd:flow(br)'))*1e6:.1f} | {abs(g('viru:flow(br)'))*1e6:.1f} | {abs(g('vird:flow(br)'))*1e6:.1f} | "
                      f"{g('pg'):.3f} | {(g('vr') - vt)*1e3:+.1f} |")
    print()


def check_lin(corners, icp):
    """Seventh run: the pump with the D18 offset current (8 % of I_cp) around its locked operating point.
    Locked, the net charge is zero at dt ~ 0.08 T_ref ~ 2.2 ns of UP lead; the Sigma-Delta moves the divider
    edge by about +-1 ns around that. Over dt = 1.0-5.0 ns only the UP side is active, so the curve should be a
    straight line: its deviation from the best-fit line (INL) is what folds Sigma-Delta noise into spurs."""
    print("## Linearity around the locked point, with the 8 % offset current (D18) [SCH]\n")
    print("Q / I_cp in ps per reference cycle against the UP lead dt; lock point = where Q = 0; INL = largest "
          "deviation from the straight-line fit, in ps of phase (and as % of the ±1 ns range).\n")
    dts = [1.0e-9, 1.5e-9, 2.0e-9, 2.5e-9, 3.0e-9, 3.5e-9, 4.0e-9, 5.0e-9]
    print("| Corner | V_tune | " + " | ".join(f"{x*1e9:g} ns" for x in dts)
          + " | Lock point (ns) | Slope | INL (ps) | Offset current (µA) |")
    print("|---|---|" + "---|" * len(dts) + "---|---|---|---|")
    for corner in corners:
        for vt in VTS:
            qs, io = [], float("nan")
            for dt in dts:
                try:
                    q, _, _, _, st = run(f"lin_{corner[0]}_{vt:.2f}_{dt*1e9:.1f}", corner, vt, dt, icp, ioff=True)
                    qs.append(q / icp)
                    io = st["ioff"]
                except RuntimeError:
                    qs.append(float("nan"))
            qa, da = np.array(qs), np.array(dts)
            ok = np.isfinite(qa)
            if ok.sum() < 3:
                print(f"| {corner[0]} | {vt} | error |")
                continue
            k, c = np.polyfit(da[ok], qa[ok], 1)
            inl = np.max(np.abs(qa[ok] - (k * da[ok] + c)))
            print(f"| {corner[0]} | {vt} | " + " | ".join(f"{x*1e12:+.0f}" for x in qa)
                  + f" | {-c / k * 1e9:.2f} | {k:.3f} | {inl*1e12:.1f} ({inl / 2e-9 * 100:.2f} %) | {io*1e6:.1f} |")
    print()


def main():
    os.makedirs(OUT, exist_ok=True)
    corners = [c for c in CORNERS if c[0] in sys.argv[1:]] or CORNERS
    print("# P2.5 step 2a — PFD and charge pump\n")
    if "dc" in sys.argv[1:]:
        check_dc(corners, ICP)
        return
    if "lin" in sys.argv[1:]:
        check_lin(corners, ICP)
        return
    print(f"I_cp {ICP*1e6:.0f} µA, reference {F_REF/1e6:.0f} MHz. Q/I_cp is the net charge per reference cycle "
          "divided by I_cp, in ps (ideal: equal to the phase offset dt; positive = net up). Sign check at "
          "|dt| = 3 ps for the dead zone.\n")
    for corner in corners:
        print(f"## {corner[0]} ({corner[2]} V, {corner[3]} °C)\n")
        print("| V_tune (V) | " + " | ".join(f"{dt*1e12:+.0f} ps" for dt in DTS)
              + " | Offset at 0 (ps) | Gain (slope / I_cp) | Dead zone | Reset pulse UP / DN (ps) | Replica error (mV) |")
        print("|---|" + "---|" * len(DTS) + "---|---|---|---|---|")
        diag = []
        for vt in VTS:
            qs, w0, rep = [], None, None
            for dt in DTS:
                try:
                    q, w, pg, vr, st = run(f"cp_{corner[0]}_{vt:.2f}_{dt*1e12:+.0f}", corner, vt, dt, ICP)
                except RuntimeError as e:
                    print(f"| {vt} | error: {str(e)[-150:]!r} |")
                    qs = None
                    break
                qs.append(q / ICP)
                if dt == 0.0:
                    w0, rep, st0 = w, (vr - vt) * 1e3, st
            if qs is None:
                continue
            qs = np.array(qs)
            dts = np.array(DTS)
            big = np.abs(dts) >= 50e-12
            slope = np.polyfit(dts[big], qs[big], 1)[0]
            off = qs[DTS.index(0.0)]
            small = [qs[DTS.index(-3e-12)] - off < 0, qs[DTS.index(3e-12)] - off > 0]
            dz = "none (±3 ps resolved)" if all(small) else "**≥ 3 ps**"
            print(f"| {vt} | " + " | ".join(f"{x*1e12:+.1f}" for x in qs)
                  + f" | {off*1e12:+.2f} | {slope:.3f} | {dz} | {w0['up']*1e12:.0f} / {w0['dn']*1e12:.0f} | {rep:+.2f} |")
            diag.append((vt, st0))
        print()
        if diag:
            print("Node voltages (V) and source currents (µA) at dt = 0 over the last 10 cycles, min / mean / max:\n")
            print("| V_tune | pg | vr | nb | pz | nz | main up | main down | replica up | replica down |")
            print("|---|---|---|---|---|---|---|---|---|---|")
            for vt, st in diag:
                f3 = lambda k, sc=1.0: " / ".join(f"{x*sc:.3f}" if sc == 1.0 else f"{x*sc:.1f}" for x in st[k])  # noqa: E731
                print(f"| {vt} | {f3('pg')} | {f3('vr')} | {f3('nb')} | {f3('pz')} | {f3('nz')} | "
                      f"{f3('vimu', 1e6)} | {f3('vimd', 1e6)} | {f3('viru', 1e6)} | {f3('vird', 1e6)} |")
            print()


if __name__ == "__main__":
    main()
