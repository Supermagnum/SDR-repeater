#!/usr/bin/env python3
"""P2.5 step 2a: PFD + charge pump (spec/pll-topology.md §2, §7).

Run inside the container from this folder:

    mkdir -p out && python3 -u run_step2.py | tee out/summary.txt    # 3 corners x 3 V_tune x 9 phase offsets
    python3 -u run_step2.py tt                                        # one corner: tt / ss / ff
    python3 -u run_step2.py icp=200                                   # charge-pump current in uA (default 100)

Circuit (transistor level unless noted):
  clocks  REF and DIV: ideal 36 MHz near-squares (DIV delayed by dt), each sharpened by two inverters
  PFD     two static master-slave D flip-flops (D = 1, transmission gates, NOR-based asynchronous reset), reset
          = AND(UP, DN) through a delay chain (NAND + 5 inverters, about 150-250 ps) so both pump switches turn
          fully on every cycle (no dead zone)
  CP      long-channel current sources (L = 2 um; NMOS 15 um and PMOS 120 um per 25 uA - PMOS twice as wide as
          in step 1 for headroom), current steering: each source goes to the output (UP / DN) or to a dummy node
          held at V_tune by a unity-gain buffer (no charge sharing); a replica branch (both switches on) and an
          amplifier set the PMOS gate so that replica up = replica down at V_tune (D18). The two amplifiers are
          behavioural (Verilog-A: transconductor 0.1 mS, 20 uA output limit, Miller-compensated with the
          replica stage; ideal follower); their transistor-level design follows once the pump works.
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
    parameter real gm = 1e-4;
    parameter real imax = 20e-6;
    analog I(o) <+ -imax * tanh(gm * (V(p) - V(n)) / imax);
endmodule
module follower(i, o);
    inout i, o;
    electrical i, o;
    analog V(o) <+ V(i);
endmodule
>>>FILE
load "pllva.va"
model follower follower
model ota ota gm=1e-4 imax=20e-6
"""


def inv(n, a, y, wn=0.5, wp=1.0):
    return (f"x{n}p ({y} {a} vdd vdd) sg13_lv_pmos w={wp:g}u l=0.13u\n"
            f"x{n}n ({y} {a} 0 0) sg13_lv_nmos w={wn:g}u l=0.13u\n")


def tg(n, a, b, cn, cp):
    """Transmission gate between a and b, on when cn = 1 (NMOS gate) and cp = 0 (PMOS gate)."""
    return (f"x{n}n ({a} {cn} {b} 0) sg13_lv_nmos w=1u l=0.13u\n"
            f"x{n}p ({a} {cp} {b} vdd) sg13_lv_pmos w=2u l=0.13u\n")


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


def pfd():
    s = (inv("rb1", "ref0", "ref1", 1, 2) + inv("rb2", "ref1", "ref", 2, 4)
         + inv("db1", "div0", "div1", 1, 2) + inv("db2", "div1", "div", 2, 4))
    s += dff_r("fu", "ref", "rst", "up") + dff_r("fd", "div", "rst", "dn")
    s += nand2("ra", "up", "dn", "x_r0")
    nodes = ["x_r0", "x_r1", "x_r2", "x_r3", "x_r4", "rst"]
    for k in range(5):                                  # NAND + 5 inverters = AND with delay
        s += inv(f"rd{k}", nodes[k], nodes[k + 1]) + f"crd{k} ({nodes[k + 1]} 0) capacitor c=5f\n"
    return s


def charge_pump(icp):
    u = icp / 25e-6
    wn, wp = 15 * u, 120 * u
    swn, swp = max(2.0, 2 * u), max(6.0, 6 * u)
    return (
        inv("su", "up", "upb", 1, 2) + inv("sd", "dn", "dnb", 1, 2)
        # NMOS bias (fixed): reference current into a diode
        + f"iref (vdd nb) isource dc={icp:.4e}\n"
        + f"mnb (nb nb 0 0) sg13_lv_nmos w={wn:g}u l=2u\n"
        # main NMOS sink, steered to the output (DN) or to the dummy node (DN low)
        + f"mn1 (nz nb 0 0) sg13_lv_nmos w={wn:g}u l=2u\n"
        + f"mn2 (vt dn nz 0) sg13_lv_nmos w={swn:g}u l=0.13u\n"
        + f"mn3 (vdm dnb nz 0) sg13_lv_nmos w={swn:g}u l=0.13u\n"
        # main PMOS source, gate pg from the replica amplifier; to the output (UP) or the dummy node
        + f"mp1 (pz pg vdd vdd) sg13_lv_pmos w={wp:g}u l=2u\n"
        + f"mp2 (vt upb pz vdd) sg13_lv_pmos w={swp:g}u l=0.13u\n"
        + f"mp3 (vdm up pz vdd) sg13_lv_pmos w={swp:g}u l=0.13u\n"
        # dummy node held at V_tune by a unity-gain buffer (behavioural)
        + "xbuf (vt vdm) follower\n"
        # replica: both switches on, its node vr compared with V_tune; the amplifier drives pg
        + f"mrn1 (rnz nb 0 0) sg13_lv_nmos w={wn:g}u l=2u\n"
        + f"mrn2 (vr vdd rnz 0) sg13_lv_nmos w={swn:g}u l=0.13u\n"
        + f"mrp1 (rpz pg vdd vdd) sg13_lv_pmos w={wp:g}u l=2u\n"
        + f"mrp2 (vr 0 rpz vdd) sg13_lv_pmos w={swp:g}u l=0.13u\n"
        + "xamp (vr vt pg) ota\n"
        # The amplifier and the replica PMOS form a two-stage loop (the replica is a common-source stage with
        # the high-impedance node vr), so it is Miller-compensated from pg to vr (UGB about gm / Cc = 16 MHz).
        # 10 MOhm to a fixed voltage only fixes the DC gain (about 60 dB) for the operating point.
        + "rpg (pg vpgb) resistor r=1e7\nvpgb (vpgb 0) vsource dc=0.5\n"
        + "ccm (pg vr) capacitor c=1p\ncvr (vr 0) capacitor c=0.2p\n")


def run(name, corner, vt, dt, icp):
    from vacask.rawfile import rawread
    _, mos, vdd, temp = corner
    path = os.path.join(OUT, name + ".sim")
    ncyc = 25
    with open(path, "w") as fh:
        fh.write(HEADER.format(title=f"P2.5 step 2a: {name}", mos=mos))
        # Verilog-A parameters are model parameters in VACASK (first run: "parameter not found" on the
        # instance), so each clock gets its own model
        fh.write(f"model sqref sqclk f={F_REF:.6e} td=2e-9 vh={vdd}\n"
                 f"model sqdiv sqclk f={F_REF:.6e} td={2e-9 + dt:.6e} vh={vdd}\n"
                 f"vdd (vdd 0) vsource dc={vdd}\n"
                 f"xref (ref0) sqref\n"
                 f"xdiv (div0) sqdiv\n"
                 f"vtn (vt 0) vsource dc={vt}\n" + pfd() + charge_pump(icp))
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
    return q, w, float(np.real(d["pg"])[-1]), float(np.real(d["vr"])[-1])


def main():
    os.makedirs(OUT, exist_ok=True)
    corners = [c for c in CORNERS if c[0] in sys.argv[1:]] or CORNERS
    print("# P2.5 step 2a — PFD and charge pump\n")
    print(f"I_cp {ICP*1e6:.0f} µA, reference {F_REF/1e6:.0f} MHz. Q/I_cp is the net charge per reference cycle "
          "divided by I_cp, in ps (ideal: equal to the phase offset dt; positive = net up). Sign check at "
          "|dt| = 3 ps for the dead zone.\n")
    for corner in corners:
        print(f"## {corner[0]} ({corner[2]} V, {corner[3]} °C)\n")
        print("| V_tune (V) | " + " | ".join(f"{dt*1e12:+.0f} ps" for dt in DTS)
              + " | Offset at 0 (ps) | Gain (slope / I_cp) | Dead zone | Reset pulse UP / DN (ps) | Replica error (mV) |")
        print("|---|" + "---|" * len(DTS) + "---|---|---|---|---|")
        for vt in VTS:
            qs, w0, rep = [], None, None
            for dt in DTS:
                try:
                    q, w, pg, vr = run(f"cp_{corner[0]}_{vt:.2f}_{dt*1e12:+.0f}", corner, vt, dt, ICP)
                except RuntimeError as e:
                    print(f"| {vt} | error: {str(e)[-150:]!r} |")
                    qs = None
                    break
                qs.append(q / ICP)
                if dt == 0.0:
                    w0, rep = w, (vr - vt) * 1e3
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
        print()


if __name__ == "__main__":
    main()
