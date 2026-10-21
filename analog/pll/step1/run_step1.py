#!/usr/bin/env python3
"""P2.5 step 1: device and block checks before the PLL schematic (spec/pll-topology.md §5).

Run inside the container from this folder:

    mkdir -p out && python3 -u run_step1.py | tee out/summary.txt     # all checks, about 15-30 min
    python3 -u run_step1.py cp                                          # or some of: cp cap mmd

Checks (VACASK, IHP SG13G2; corners tt 1.2 V 27 degC, ss 1.08 V 125 degC, ff 1.32 V -40 degC):
  cp    charge-pump current sources (wide-swing cascode mirrors, D18 topology without the replica amplifier):
        up and down current against the output voltage 0.15-1.05 V at 25 / 100 / 200 uA, i.e. the output
        compliance and the raw up/down mismatch the replica amplifier has to remove; leakage with the
        switches off at 125 degC
  cap   loop-filter MOS capacitors (D17): capacitance per area against voltage 0.1-1.1 V for thin-oxide NMOS
        (gate to the node, S/D/B to ground), thin-oxide PMOS (S/D/B at V_DD), the two in parallel
        (complementary, flatter), and thick-oxide NMOS; gate leakage at 125 degC
  mmd   first divide-by-2/3 cell of the feedback divider (D16): two TSPC flip-flops (as P2.4) and an AOI gate,
        ÷2 and ÷3 mode, 1.0-3.0 GHz input, tt and ss; and 10 mismatch samples at ss / 2.2 GHz
The PFD dead-zone check needs the PFD and charge-pump switches together and moves to step 2. Results [SCH].
"""
import importlib.util
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


L3 = _load("lo_step3", "analog/lo/step3/run_step3.py")   # brings LO step 2 (cells) and step 1 (clock source)
L2, L1 = L3.L2, L3.L1

CORNERS = [("tt", "mos_tt", 1.20, 27), ("ss", "mos_ss", 1.08, 125), ("ff", "mos_ff", 1.32, -40)]
HV = 'include "cornerMOShv.lib" section={mos}\n'
SUMMARY = []


def say(s=""):
    print(s)
    SUMMARY.append(s)


def sim(name, corner, body, analysis, clk=None):
    """Write and run one netlist; returns the raw data of the first analysis."""
    from vacask.rawfile import rawread
    _, mos, vdd, temp = corner
    f, amp, shape = clk or (1e9, 0.0, 0.0)
    path = os.path.join(OUT, name + ".sim")
    with open(path, "w") as fh:
        fh.write(L1.HEADER.format(title=f"P2.5 step 1: {name}", mos=mos, vcm=vdd / 2, amp=amp, shape=shape, f=f,
                                  offs=0.0, t0=-1.0, tr=1e-12))
        fh.write(HV.format(mos=mos))
        fh.write(f"vdd (vdd 0) vsource dc={vdd}\n" + body)
        fh.write(f"\ncontrol\n  abort always\n  options rawfile=\"binary\"\n  options temp={temp}\n{analysis}\nendc\n")
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(f"vacask {name}.sim failed; end of out/{name}.log: " + open(log).read()[-600:])
    an = analysis.split()[1]
    return rawread(os.path.join(OUT, an + ".raw")).get()


# ------------------------------------------------------------------ charge pump
# Unit cell per 25 uA: NMOS 7.5/1 um (V_ov about 0.15 V), PMOS 30/1 um; cascodes same W, L = 0.5 um.
# Wide-swing (Sooch) bias: the cascode gate comes from a diode-connected device of W/4 at the same current, so
# the current-source device sits at about one V_ov of drain voltage.
def cp_body(units, tag, vout, sw_on=True):
    i = 25e-6 * units
    wn, wp = 7.5 * units, 30 * units
    vdd_sw = "vdd" if sw_on else "0"
    vss_sw = "0" if sw_on else "vdd"
    return (
        # NMOS sink: reference branch, bias, output branch (down current), switch
        f"ir{tag}n (vdd {tag}nr) isource dc={i:.4e}\n"
        f"m{tag}n1 ({tag}nx {tag}nr 0 0) sg13_lv_nmos w={wn:g}u l=1u\n"
        f"m{tag}n2 ({tag}nr {tag}nc {tag}nx 0) sg13_lv_nmos w={wn:g}u l=0.5u\n"
        f"ib{tag}n (vdd {tag}nc) isource dc={i:.4e}\n"
        f"m{tag}n3 ({tag}nc {tag}nc 0 0) sg13_lv_nmos w={wn / 4:g}u l=1u\n"
        f"m{tag}n4 ({tag}ny {tag}nr 0 0) sg13_lv_nmos w={wn:g}u l=1u\n"
        f"m{tag}n5 ({tag}nz {tag}nc {tag}ny 0) sg13_lv_nmos w={wn:g}u l=0.5u\n"
        f"m{tag}n6 ({tag}od {vdd_sw} {tag}nz 0) sg13_lv_nmos w=4u l=0.13u\n"
        f"v{tag}d ({tag}od 0) vsource dc={vout}\n"
        # PMOS source (up current)
        f"ir{tag}p ({tag}pr 0) isource dc={i:.4e}\n"
        f"m{tag}p1 ({tag}px {tag}pr vdd vdd) sg13_lv_pmos w={wp:g}u l=1u\n"
        f"m{tag}p2 ({tag}pr {tag}pc {tag}px vdd) sg13_lv_pmos w={wp:g}u l=0.5u\n"
        f"ib{tag}p ({tag}pc 0) isource dc={i:.4e}\n"
        f"m{tag}p3 ({tag}pc {tag}pc vdd vdd) sg13_lv_pmos w={wp / 4:g}u l=1u\n"
        f"m{tag}p4 ({tag}py {tag}pr vdd vdd) sg13_lv_pmos w={wp:g}u l=1u\n"
        f"m{tag}p5 ({tag}pz {tag}pc {tag}py vdd) sg13_lv_pmos w={wp:g}u l=0.5u\n"
        f"m{tag}p6 ({tag}ou {vss_sw} {tag}pz vdd) sg13_lv_pmos w=8u l=0.13u\n"
        f"v{tag}u ({tag}ou 0) vsource dc={vout}\n")


def check_cp():
    say("## Charge-pump current sources: compliance and raw up/down mismatch [SCH]\n")
    say("Wide-swing cascode mirrors, unit cell per 25 µA (NMOS 7.5/1 µm, PMOS 30/1 µm, cascodes L 0.5 µm), "
        "switches on. Compliance: output range where the current stays within 1 % of its value at 0.6 V. "
        "Mismatch: (I_up − I_down) / I_cp — what the replica amplifier must remove. Tuning window to support: "
        "0.35–0.85 V (calibration target), 0.3–1.0 V (VCO design).\n")
    vs = np.round(np.arange(0.15, 1.051, 0.05), 3)
    say("| Corner | I_cp (µA) | Down: compliance (V) | Up: compliance (V) | Mismatch at 0.35 / 0.6 / 0.85 V (%) | "
        "Worst mismatch 0.35–0.85 V (%) |")
    say("|---|---|---|---|---|---|")
    for corner in CORNERS:
        for units in (1, 4, 8):
            idn, iup = [], []
            for v in vs:
                d = sim(f"cp_{corner[0]}_{units}_{v:.2f}", corner, cp_body(units, "a", v), "  analysis op1 op")
                idn.append(float(np.real(d["vad:flow(br)"])[0]))     # current into the output node from the source
                iup.append(-float(np.real(d["vau:flow(br)"])[0]))
            idn, iup = np.abs(np.array(idn)), np.abs(np.array(iup))
            i0 = 25e-6 * units
            k = int(np.argmin(np.abs(vs - 0.6)))

            def comp(i):
                ok = np.abs(i / i[k] - 1) <= 0.01
                lo = k
                while lo > 0 and ok[lo - 1]:
                    lo -= 1
                hi = k
                while hi < len(vs) - 1 and ok[hi + 1]:
                    hi += 1
                return f"{vs[lo]:.2f}–{vs[hi]:.2f}"
            mm = (iup - idn) / i0 * 100
            sel = (vs >= 0.349) & (vs <= 0.851)
            pick = [int(np.argmin(np.abs(vs - x))) for x in (0.35, 0.6, 0.85)]
            say(f"| {corner[0]} | {i0*1e6:.0f} | {comp(idn)} | {comp(iup)} | "
                + " / ".join(f"{mm[p]:+.1f}" for p in pick) + f" | {np.max(np.abs(mm[sel])):.1f} |")
    say("")
    say("Leakage with both switches off, 125 °C (output held at the voltage):\n")
    say("| Corner | V_out (V) | Down leakage (nA) | Up leakage (nA) | Net (nA) |")
    say("|---|---|---|---|---|")
    for corner in (("tt-hot", "mos_tt", 1.2, 125), ("ff-hot", "mos_ff", 1.32, 125)):
        for v in (0.35, 0.6, 0.85):
            d = sim(f"cpleak_{corner[0]}_{v:.2f}", corner, cp_body(8, "a", v, sw_on=False), "  analysis op1 op")
            idn = float(np.real(d["vad:flow(br)"])[0])
            iup = float(np.real(d["vau:flow(br)"])[0])
            say(f"| {corner[0]} | {v:.2f} | {abs(idn)*1e9:.2f} | {abs(iup)*1e9:.2f} | {(idn + iup)*1e9:+.2f} |")
    say("")


# ------------------------------------------------------------------ loop-filter MOS capacitors
CAPS = [("thin NMOS (S/D/B to ground)", lambda n: f"m{n} (0 g{n} 0 0) sg13_lv_nmos w=10u l=10u\n", 100),
        ("thin PMOS (S/D/B at V_DD)", lambda n: f"m{n} (vdd g{n} vdd vdd) sg13_lv_pmos w=10u l=10u\n", 100),
        ("thin NMOS + PMOS in parallel", lambda n: f"m{n}a (0 g{n} 0 0) sg13_lv_nmos w=10u l=10u\n"
                                                    f"m{n}b (vdd g{n} vdd vdd) sg13_lv_pmos w=10u l=10u\n", 200),
        ("thick NMOS (S/D/B to ground)", lambda n: f"m{n} (0 g{n} 0 0) sg13_hv_nmos w=10u l=10u\n", 100)]


def check_cap():
    say("## Loop-filter MOS capacitors: density, voltage dependence, leakage [SCH]\n")
    say("Each 10 × 10 µm (100 µm² of gate; the complementary pair 200 µm²). Capacitance from the displacement "
        "current of a 1 V/µs ramp, per µm² of gate. Loop filter needs C1 ≈ 39 pF and C2 ≈ 355 pF over V_tune "
        "0.35–0.85 V; MIM reference ≈ 1.5 fF/µm².\n")
    vpts = [0.1, 0.2, 0.35, 0.5, 0.6, 0.7, 0.85, 1.0, 1.1]
    dens = {}
    say("| Corner | Capacitor | " + " | ".join(f"{v:g} V" for v in vpts) + " | Spread 0.35–0.85 V |")
    say("|---|---|" + "---|" * len(vpts) + "---|")
    for corner in CORNERS:
        for k, (label, cell, area) in enumerate(CAPS):
            body = (cell(k) + f'vg{k} (g{k} 0) vsource type="pulse" val0=0 val1=1.2 delay=10n rise=1.2u '
                    f"fall=1n width=1\n")
            d = sim(f"cap_{corner[0]}_{k}", corner, body,
                    "  analysis tr1 tran stop=1.2u step=2n maxstep=2n")
            t = np.real(d["time"])
            v = np.real(d[f"g{k}"])
            i = -np.real(d[f"vg{k}:flow(br)"])
            slope = 1.2 / 1.2e-6
            c = np.abs(i) / slope / area * 1e15                         # fF/um2
            cv = [float(np.interp(x, v[(t > 20e-9)], c[(t > 20e-9)])) for x in vpts]
            sel = [cv[j] for j, x in enumerate(vpts) if 0.35 <= x <= 0.85]
            if corner[0] == "tt":
                dens[k] = min(sel)                                      # worst density over the window
            say(f"| {corner[0]} | {label} | " + " | ".join(f"{x:.2f}" for x in cv)
                + f" | {max(sel) / min(sel):.2f}× |")
    say("")
    say("Gate leakage at 125 °C (tt): per µm², and for C2 = 355 pF built at the lowest typical density over "
        "0.35–0.85 V (the reference-spur budget allows about 100 nA, P2.2):\n")
    say("| Capacitor | V (V) | Leakage (pA/µm²) | Area for 355 pF (µm²) | Leakage for 355 pF (nA) |")
    say("|---|---|---|---|---|")
    corner = ("tt-hot", "mos_tt", 1.2, 125)
    for k, (label, cell, area) in enumerate(CAPS):
        for vv in (0.35, 0.85):
            d0 = sim(f"capl_{k}_{vv}", corner, cell(k) + f"vg{k} (g{k} 0) vsource dc={vv}\n", "  analysis op1 op")
            il = abs(float(np.real(d0[f"vg{k}:flow(br)"])[0])) / area          # A per um2 of gate
            a355 = 355e3 / dens[k] if dens.get(k) else float("nan")            # um2
            say(f"| {label} | {vv} | {il*1e12:.3f} | {a355:,.0f} | {il*a355*1e9:.2f} |")
    say("")


# ------------------------------------------------------------------ MMD first 2/3 cell
def mmd_cell(mc):
    """Divide-by-2/3: q1' = NOR(q1, q2 AND mc), q2' = q1 (TSPC flip-flops are inverting: q = NOT d)."""
    s = ("vdgs (vdg 0) vsource dc={vdd}\n"          # the P2.4 cells run on the logic supply node vdg
         "xck1p (ckb x_ck vdd vdd) sg13_lv_pmos w=2u l=0.13u\nxck1n (ckb x_ck 0 0) sg13_lv_nmos w=1u l=0.13u\n"
         "xck2p (ck ckb vdd vdd) sg13_lv_pmos w=6u l=0.13u\nxck2n (ck ckb 0 0) sg13_lv_nmos w=3u l=0.13u\n")
    s += f"vmc (mc 0) vsource dc={'1.32' if mc else '0'}\n".replace("1.32", "{vdd}")
    # AOI21: y = NOT(q1 OR (q2 AND mc)); then inverter -> d1 = q1 OR (q2 AND mc); FF1 inverting -> q1' = NOR(...)
    s += ("xa1 (aoi_m q2 vdd vdd) sg13_lv_pmos w=2u l=0.13u\nxa2 (aoi_m mc vdd vdd) sg13_lv_pmos w=2u l=0.13u\n"
          "xa3 (aoi q1 aoi_m vdd) sg13_lv_pmos w=2u l=0.13u\n"
          "xa4 (aoi q1 0 0) sg13_lv_nmos w=1u l=0.13u\nxa5 (aoi q2 x_an 0) sg13_lv_nmos w=1u l=0.13u\n"
          "xa6 (x_an mc 0 0) sg13_lv_nmos w=1u l=0.13u\n")
    s += L2.inv("ai", "aoi", "d1") + L2.tspc("f1", "d1", "ck", "q1") + L2.inv("i2", "q1", "q1b")
    s += L2.tspc("f2", "q1b", "ck", "q2") + "cq1 (q1 0) capacitor c=5f\n"
    return s


def check_mmd():
    say("## Feedback divider: first divide-by-2/3 cell [SCH]\n")
    say("Two TSPC flip-flops (size 2, as P2.4) and an AOI21 gate in the loop; clock from a near-square source "
        "through two inverters (realistic edges). Input up to 2.2 GHz in use (UHF ÷2 of 4.41 GHz); "
        "pass needs ≥ 1.3 × 2.2 = 2.9 GHz at the slow corner.\n")
    freqs = [1.0e9, 1.5e9, 2.0e9, 2.2e9, 2.5e9, 2.9e9, 3.3e9]
    say("| Corner | Mode | " + " | ".join(f"{f/1e9:g} GHz" for f in freqs) + " |")
    say("|---|---|" + "---|" * len(freqs))
    for corner in CORNERS[:2]:
        vdd = corner[2]
        for mc, n in ((0, 2), (1, 3)):
            cells = []
            for f in freqs:
                body = "xclk (x_ck x_ckn) clk\n" + mmd_cell(mc).replace("{vdd}", f"{vdd}")
                try:
                    d = sim(f"mmd_{corner[0]}_{n}_{f/1e9:.1f}", corner, body,
                            f"  analysis tr1 tran stop={60 / f:.4e} step={1 / f / 40:.3e} maxstep={1 / f / 40:.3e}",
                            clk=(f, vdd / 2, 4.0))
                    fo, a = L1.freq(d["time"], np.real(d["q1"]) - vdd / 2)
                    cells.append("OK" if abs(fo * n / f - 1) < 0.01 and a > 0.35 * vdd else f"fail ({fo/1e9:.2f})")
                except RuntimeError:
                    cells.append("error")
            say(f"| {corner[0]} | ÷{n} | " + " | ".join(cells) + " |")
    say("")
    say("Mismatch, slow corner, 2.2 GHz, 10 samples per mode (PDK mismatch values as P2.4):\n")
    corner = CORNERS[1]
    vdd = corner[2]
    for mc, n in ((0, 2), (1, 3)):
        good = 0
        for k in range(10):
            body = "xclk (x_ck x_ckn) clk\n" + L3.mismatch(mmd_cell(mc).replace("{vdd}", f"{vdd}"),
                                                           np.random.default_rng(2000 + k))
            f = 2.2e9
            try:
                d = sim(f"mmdmc_{n}_{k}", corner, body,
                        f"  analysis tr1 tran stop={60 / f:.4e} step={1 / f / 40:.3e} maxstep={1 / f / 40:.3e}",
                        clk=(f, vdd / 2, 4.0))
                fo, a = L1.freq(d["time"], np.real(d["q1"]) - vdd / 2)
                good += abs(fo * n / f - 1) < 0.01 and a > 0.35 * vdd
            except RuntimeError:
                pass
        say(f"- ÷{n}: {good} of 10 samples correct")
    say("")


CHECKS = {"cp": check_cp, "cap": check_cap, "mmd": check_mmd}


def main():
    os.makedirs(OUT, exist_ok=True)
    sel = [a for a in sys.argv[1:] if a in CHECKS] or list(CHECKS)
    say("# P2.5 step 1 — PLL device and block checks\n")
    for k in sel:
        CHECKS[k]()


if __name__ == "__main__":
    main()
