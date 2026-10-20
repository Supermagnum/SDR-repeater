#!/usr/bin/env python3
"""P2.4 step 2: VCO buffer and both divider chains, driven by the step-2/3 VCO (spec/lo-divider-topology.md).

Run inside the container from this folder (needs ../../vco/step2/out/range.json):

    mkdir -p out && python3 -u run_step2.py | tee out/summary.txt     # 8 transients, about 1-2 h
    python3 -u run_step2.py uhf ss 3.84                                # or any of: uhf vhf tt ss <GHz>
    python3 -u run_step2.py vhf ss 4.20 en=off                         # CML divider on from t = 0 (default: 35 ns, D15)
    python3 -u run_step2.py uhf ss pq=3                                # UHF retiming output PMOS 3x (default 2)
    python3 -u run_step2.py vhf ss 3.12 nobufm                         # buffer without the extra gain inverter
    python3 -u run_step2.py vhf b2=4                                   # last buffer inverter 4/8 um (default 6/12)

Circuit per run (one chain per run, as band_sel powers one chain):
  VCO       the P2.3 VCO netlist (analog/vco/step2/run_step2.py, sizes from range.json), its stand-in
            buffer removed; bank code and tail current per band as in VCO step 3 (tail capped at 4 mA, D12)
  buffer    per side: 100 fF coupling capacitor from the tank, self-biased CMOS inverter (50 kOhm feedback),
            second inverter; weak cross-coupled inverters keep the two sides in anti-phase. Output common
            mode about V_DD/2 = V_DD - 0.6 V, swing rail to rail: meets the step-1 requirement of
            >= 0.5 V per side at about V_DD - 0.55 V for the CML dividers
  UHF       CML ÷2 (step 1, 0.5 mA per latch) -> CML-to-CMOS converter (step 1) -> TSPC Johnson ÷4
            (2 flip-flops) -> four 25 % pulses (NAND + inverter) = I+, Q+, I-, Q- (D13)
  VHF       CML ÷3 (step 1) -> converter -> TSPC Johnson ÷8 (4 flip-flops) -> 8 phases at 45° (D4)
Separate ideal supplies for buffer (vbuf), CML divider (vdv), converter (vcv) and CMOS logic (vdg), so each
current is measured. Results are [SCH].
"""
import importlib.util
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step3"))
import run_step3 as S3  # noqa: E402  (imports the VCO step 2 module as S3.S2)

S2 = S3.S2
S2.OUT = OUT
S3.OUT = OUT
_spec = importlib.util.spec_from_file_location("lo_step1", os.path.join(REPO, "analog", "lo", "step1", "run_step1.py"))
L1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L1)

CASES = {"uhf": [3.20e9, 3.84e9], "vhf": [3.12e9, 4.20e9]}
CMLBUF = "cmlbuf" in sys.argv[1:]
# D15 (2026-10-20): the CML divider is enabled by the sequencer only after the VCO has full swing. On while the
# VCO starts up, the ÷3 can lock into its free-running state (seventh run: VHF slow corner 4.20 GHz failed; step 1
# div3s: fails at 4.41 GHz with any clock ramp, passes when enabled after the ramp). Default enable 35 ns;
# option en=<ns> changes it, en=off keeps the divider on from t = 0 (old behaviour).
_en = next((a[3:] for a in sys.argv[1:] if a.startswith("en=")), "35")
EN_NS = None if _en == "off" else float(_en)
# Option pq=<x>: output PMOS of the UHF retiming flip-flops x times wider (duty-cycle check: the TSPC output rises
# one gate later than it falls, so the 25 % pulses come out narrower, 21 % at the slow corner)
PQ = next((float(a[3:]) for a in sys.argv[1:] if a.startswith("pq=")), 2.0)   # eighth run: 2 is the default
# Option bufm: an extra 3/6 um gain inverter per side between the two buffer inverters (eighth run: VHF slow
# 3.12 GHz gave only 0.43 V per side, clock duty 43.7 %, skew -20 ps: the small bottom-band tank swing at the slow
# corner does not fully switch the first inverter)
# Ninth run: bufm gave 0.56 V per side at VHF slow 3.12 GHz (0.43 V without) for +0.27 mA, so it is now the
# default; "nobufm" removes it. Option b2=<um>: NMOS width of the last buffer inverter (PMOS 2x; default 6) - with
# the gain stage it may shrink and win back the current (D7 limit).
BUFM = "nobufm" not in sys.argv[1:]
B2 = next((float(a[3:]) for a in sys.argv[1:] if a.startswith("b2=")), 6.0)
CORNERS = [("tt", "mos_tt", "cap_typ", 1.2, 27), ("ss", "mos_ss", "cap_typ", 1.08, 125)]
STANDIN = ("mb1 ", "mb2 ", "rl1 ", "rl2 ", "ib ", "ctb ", "cl1 ", "cl2 ")


# ---------------------------------------------------------------- CMOS cells (prefix x_ avoids VCO names)
def inv(n, a, y, sup="vdg", wn=0.5, wp=1.0):
    return (f"x{n}p ({y} {a} {sup} {sup}) sg13_lv_pmos w={wp}u l=0.13u\n"
            f"x{n}n ({y} {a} 0 0) sg13_lv_nmos w={wn}u l=0.13u\n")


def nand2(n, a, b, y, sup="vdg"):
    return (f"x{n}pa ({y} {a} {sup} {sup}) sg13_lv_pmos w=1u l=0.13u\n"
            f"x{n}pb ({y} {b} {sup} {sup}) sg13_lv_pmos w=1u l=0.13u\n"
            f"x{n}na ({y} {a} x_{n}m 0) sg13_lv_nmos w=1u l=0.13u\n"
            f"x{n}nb (x_{n}m {b} 0 0) sg13_lv_nmos w=1u l=0.13u\n")


def tspc(n, d, ck, q, sup="vdg", sz=2, pq=1.0):
    """Positive-edge TSPC flip-flop, inverting (q = NOT d after the edge). Size sz x (NMOS 0.5 / PMOS 1 um).
    Fourth run: size 1 (step 1 minimum) was too weak once loaded: the UHF Johnson counter miscounted at
    1.92 GHz, slow corner, and the retimed pulses came out at 21 % instead of 25 %. Default now size 2."""
    a, b, x1, x2, x3 = (f"x_{n}_{s}" for s in ("a", "b", "x1", "x2", "x3"))
    return (f"x{n}p1 ({x1} {d} {sup} {sup}) sg13_lv_pmos w={1.0*sz:g}u l=0.13u\n"
            f"x{n}p2 ({a} {ck} {x1} {sup}) sg13_lv_pmos w={1.0*sz:g}u l=0.13u\n"
            f"x{n}n1 ({a} {d} 0 0) sg13_lv_nmos w={0.5*sz:g}u l=0.13u\n"
            f"x{n}p3 ({b} {ck} {sup} {sup}) sg13_lv_pmos w={1.0*sz:g}u l=0.13u\n"
            f"x{n}n2 ({b} {a} {x2} 0) sg13_lv_nmos w={0.5*sz:g}u l=0.13u\n"
            f"x{n}n3 ({x2} {ck} 0 0) sg13_lv_nmos w={0.5*sz:g}u l=0.13u\n"
            f"x{n}p4 ({q} {b} {sup} {sup}) sg13_lv_pmos w={1.0*sz*pq:g}u l=0.13u\n"
            f"x{n}n4 ({q} {ck} {x3} 0) sg13_lv_nmos w={0.5*sz:g}u l=0.13u\n"
            f"x{n}n5 ({x3} {b} 0 0) sg13_lv_nmos w={0.5*sz:g}u l=0.13u\n"
            # 1 GOhm leaks: TSPC nodes float in some clock states, which left the DC operating point
            # singular in the first VHF runs (VACASK stopped before the transient)
            + "".join(f"rk{n}{k} ({nd} 0) resistor r=1G\n" for k, nd in enumerate((q, a, b, x1, x2, x3))))


def buffer():
    """Capacitor-coupled self-biased inverter buffer, per side, plus weak anti-phase cross-coupling."""
    s = ""
    for side, src, out in (("p", "tp", "ckp"), ("n", "tn", "ckn")):
        s += (f"cc{side} ({src} x_bi{side}) capacitor c=100f\n"
              f"rf{side} (x_bi{side} x_bo{side}) resistor r=50k\n"
              + inv(f"b1{side}", f"x_bi{side}", f"x_bo{side}", "vbuf", 2, 4)
              + (inv(f"bm{side}", f"x_bo{side}", f"x_bm{side}", "vbuf", 3, 6) if BUFM else "")
              + inv(f"b2{side}", f"x_bm{side}" if BUFM else f"x_bo{side}", out, "vbuf", B2, 2 * B2))   # 4/8 gave 0.47 V at slow 3.12 GHz
    s += inv("bxp", "x_bop", "x_bon", "vbuf", 0.5, 1) + inv("bxn", "x_bon", "x_bop", "vbuf", 0.5, 1)
    # Fourth run: at slow corner / 4.21 GHz the CML ÷3 divided wrongly (2.7 GHz out instead of 1.40 GHz) although
    # its clock had the right swing. Suspect: skew between ckp and ckn (two separate inverter chains) makes the
    # CML clocks overlap. Stronger anti-phase coupling at the outputs themselves:
    s += inv("bop", "ckp", "ckn", "vbuf", 1, 2) + inv("bon", "ckn", "ckp", "vbuf", 1, 2)
    if CMLBUF:
        # Option 'cmlbuf': a differential current-steering stage after the inverters (exactly complementary
        # clocks, as the ideal sources in step 1). 1 mA tail, 1 kOhm loads: about 0.5 V per side, CM about V_DD - 0.5 V.
        s = s.replace(" ckp ", " x_ck0p ").replace("(ckp ", "(x_ck0p ").replace(" ckp)", " x_ck0p)")
        s = s.replace(" ckn ", " x_ck0n ").replace("(ckn ", "(x_ck0n ").replace(" ckn)", " x_ck0n)")
        s += ("mcbp (ckn x_ck0p x_cbt 0) sg13_lv_nmos w=10u l=0.13u\nmcbn (ckp x_ck0n x_cbt 0) sg13_lv_nmos w=10u l=0.13u\n"
              "rcbp (vbuf ckp) resistor r=1k\nrcbn (vbuf ckn) resistor r=1k\nicbt (x_cbt 0) isource dc=1m\n")
    return s


def converter(dp, dn, y):
    """Step-1 CML-to-CMOS converter on its own supply vcv: NMOS pair, PMOS mirror, two inverters."""
    return ("xcvp1 (x_o1 x_o1 vcv vcv) sg13_lv_pmos w=4u l=0.13u\nxcvp2 (x_o2 x_o1 vcv vcv) sg13_lv_pmos w=4u l=0.13u\n"
            f"xcvn1 (x_o1 {dn} x_tc 0) sg13_lv_nmos w=4u l=0.13u\nxcvn2 (x_o2 {dp} x_tc 0) sg13_lv_nmos w=4u l=0.13u\n"
            "icv (x_tc 0) isource dc=0.3m\n"
            + inv("cv1", "x_o2", "x_cx", "vcv", 0.5, 1) + inv("cv2", "x_cx", "x_cy", "vcv", 1, 2)
            # Clock driver (third version): with the retiming flip-flops the clock drives 6 (UHF) / 12 (VHF)
            # TSPC flip-flops; the 1/2 um inverter was too weak at the slow corner (UHF divided by 10 / 16
            # instead of 8, VHF at 4.2 GHz stopped). Tapered chain 3/6 -> 9/18 um.
            + inv("cv3", "x_cy", "x_cz", "vcv", 3, 6) + inv("cv4", "x_cz", y, "vcv", 9, 18))


def chain(band, vdd):
    """Divider chain for one band, its CMOS phase outputs and their ideal phases (degrees)."""
    i_, rl, w = L1.cml_params(0.5e-3, vdd)
    body, out = L1.div_body(2 if band == "uhf" else 3, i_, rl, w, vdd)
    body = body.replace("(vdd ", "(vdv ")
    if EN_NS is not None:
        body = L1.enable_at(body, EN_NS * 1e-9)
    s = body + converter(out[0], out[1], "x_clk")
    if band == "uhf":
        # Johnson ÷4: q1 = NOT q2 (inverting flip-flop), q2 = q1 (inverter in front)
        s += tspc("f1", "x_q2", "x_clk", "x_q1") + inv("i1", "x_q1", "x_q1b") + tspc("f2", "x_q1b", "x_clk", "x_q2")
        s += inv("i2", "x_q2", "x_q2b")
        pulses = {"I+": ("x_q1", "x_q2b"), "Q+": ("x_q1", "x_q2"), "I-": ("x_q1b", "x_q2"), "Q-": ("x_q1b", "x_q2b")}
        names, ideal = [], {}
        # Second version: each pulse is retimed by a TSPC flip-flop on the same clock (the NAND output is NOT P,
        # the inverting flip-flop gives P), so all four outputs leave through identical paths. The first run
        # took the pulses straight from NAND + inverter: phase errors grew to +4..+12 deg (typical) and up to
        # +52 deg with duty 18-35 % (slow corner, 480 MHz).
        for k, (lab, (a, b)) in enumerate(pulses.items()):
            node = f"x_p{k}"
            s += nand2(f"g{k}", a, b, f"x_n{k}") + tspc(f"r{k}", f"x_n{k}", "x_clk", node, pq=PQ)
            s += f"cpl{k} ({node} 0) capacitor c=20f\n"
            names.append((lab, node))
            ideal[node] = 90 * k
        return s, names, ideal, 8, 25.0
    # Johnson ÷8: q1 = NOT q4; qk = q(k-1) through an inverter in front of each inverting flip-flop
    s += tspc("f1", "x_q4", "x_clk", "x_q1")
    for k in range(2, 5):
        s += inv(f"i{k}", f"x_q{k-1}", f"x_d{k}") + tspc(f"f{k}", f"x_d{k}", "x_clk", f"x_q{k}")
    # All 8 phases retimed by TSPC flip-flops on the same clock (true phase from the complement and vice
    # versa, the flip-flop inverts), so the complements carry no extra inverter delay.
    names, ideal = [], {}
    for k in range(1, 5):
        s += inv(f"o{k}", f"x_q{k}", f"x_q{k}b")
        s += tspc(f"r{k}a", f"x_q{k}b", "x_clk", f"x_r{k}") + tspc(f"r{k}b", f"x_q{k}", "x_clk", f"x_r{k}b")
        s += f"cr{k} (x_r{k} 0) capacitor c=10f\ncrb{k} (x_r{k}b 0) capacitor c=10f\n"
        names += [(f"{45*(k-1)}°", f"x_r{k}"), (f"{45*(k-1)+180}°", f"x_r{k}b")]
        ideal[f"x_r{k}"], ideal[f"x_r{k}b"] = 45 * (k - 1), 45 * (k - 1) + 180
    return s, names, ideal, 24, 50.0


def build(band, f, corner, code, itail, stop):
    tag, mos, cap, vdd, temp = corner
    S3.set_corner(mos, cap)
    extra = (f"vbufs (vbuf 0) vsource dc={vdd}\nvdvs (vdv 0) vsource dc={vdd}\n"
             f"vcvs (vcv 0) vsource dc={vdd}\nvdgs (vdg 0) vsource dc={vdd}\n" + buffer())
    body, names, ideal, ndiv, duty = chain(band, vdd)
    title = f"lo2_{band}_{tag}_{f/1e9:.2f}"
    path = S2.netlist(title, code, S2.VTUNE_MID, itail=itail, extra=extra + body,
                      analysis=f"  options temp={temp}\n  analysis tr tran stop={stop:.3e} step=5p maxstep=5p")
    text = open(path).read()
    keep = [ln for ln in text.splitlines() if not ln.startswith(STANDIN)]
    text = "\n".join(keep) + "\n"
    text = text.replace("vdd  (vdd 0) vsource dc=1.2", f"vdd  (vdd 0) vsource dc={vdd}")
    open(path, "w").write(text)
    S3.set_corner()
    return path, names, ideal, ndiv, duty


def edges(t, v, th):
    s = v > th
    i = np.where(~s[:-1] & s[1:])[0]
    return t[i] + (th - v[i]) * (t[i + 1] - t[i]) / (v[i + 1] - v[i])


def analyse(d, names, ideal, ndiv, duty_ideal, vdd, f_vco):
    t = np.real(d["time"])
    keep = t >= t[-1] * 0.45
    tk = t[keep]
    res = {}
    ckp, ckn = np.real(d["ckp"])[keep], np.real(d["ckn"])[keep]
    res["clk"] = dict(amp_p=(ckp.max() - ckp.min()) / 2, cm_p=(ckp.max() + ckp.min()) / 2,
                      amp_n=(ckn.max() - ckn.min()) / 2)
    ref = None
    rows = []
    for lab, node in names:
        v = np.real(d[node])[keep]
        e = edges(tk, v, vdd / 2)
        if len(e) < 3:
            rows.append((lab, node, None, None, None))
            continue
        period = np.mean(np.diff(e))
        duty = 100 * np.mean(v > vdd / 2)
        if ref is None:
            ref = (node, e, period)
        # phase relative to the first output, averaged over all edges
        de = np.array([(x - ref[1][np.argmin(np.abs(ref[1] - x))]) for x in e])
        ang = 2 * np.pi * de / ref[2]
        ph = 0.0 if node == ref[0] else float(np.degrees(np.angle(np.mean(np.exp(1j * ang)))) % 360)   # circular mean
        rows.append((lab, node, 1 / period, duty, ph))
    res["rows"] = rows
    for nm in ("vbufs", "vdvs", "vcvs", "vdgs"):
        try:
            res[nm] = float(np.mean(np.abs(np.real(d[f"{nm}:flow(br)"])[keep])))
        except (KeyError, ValueError, IndexError):
            res[nm] = float("nan")
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    bands = [a for a in args if a in CASES] or ["uhf", "vhf"]
    corners = [c for c in CORNERS if c[0] in args] or CORNERS
    fsel = []
    for a in args:
        if a.startswith(("en=", "pq=", "b2=")) or a in ("bufm", "nobufm"):
            continue
        try:
            fsel.append(float(a) * 1e9)          # e.g. 3.84 selects the 3.84 GHz case
        except ValueError:
            pass
    r, meas = S3.load_sizing()
    from vacask.rawfile import rawread
    print("# P2.4 step 2 — VCO buffer and divider chains with the VCO\n")
    print(f"VCO sizing from step 2: LSB {S2.LSB_FF:.2f} fF, fixed {S2.C_FIX_FF:.0f} fF; tail cap {S2.I_MAX*1e3:.0f} mA.")
    en_txt = "t = 0" if EN_NS is None else f"{EN_NS:g} ns"
    print(f"CML divider enabled at {en_txt} (D15); UHF retiming output PMOS x{PQ:g}; "
          f"buffer {'3' if BUFM else '2'} inverters per side, last {B2:g}/{2*B2:g} um.\n")
    for band in bands:
        for corner in corners:
            tag, mos, cap, vdd, temp = corner
            for f in [x for x in CASES[band] if not fsel or any(abs(x - y) < 5e6 for y in fsel)]:
                S3.set_corner(mos, cap)
                code = S3.code_for(f, temp, f"lo2_{band}_{tag}_{f/1e9:.2f}")
                S3.set_corner()
                itail = S3.itail_for(f, meas)
                stop = 40e-9 + (24 * 8 if band == "uhf" else 20 * 24) / f    # VCO start-up + about 20 output periods
                path, names, ideal, ndiv, duty_ideal = build(band, f, corner, code, itail, stop)
                print(f"## {band.upper()}, {tag} ({vdd} V, {temp} °C), VCO target {f/1e9:.2f} GHz "
                      f"(code {code}, {itail*1e3:.2f} mA), {stop*1e9:.0f} ns\n")
                try:
                    S2.run(path)
                except RuntimeError as e:
                    print(f"failed: {str(e)[-1500:]}\n")
                    continue
                d = rawread(os.path.join(OUT, "tr.raw")).get()
                fv, _ = L1.freq(d["time"], np.real(d["tp"]) - np.real(d["tn"]), frac=0.3)
                res = analyse(d, names, ideal, ndiv, duty_ideal, vdd, fv)
                c = res["clk"]
                # Stage-by-stage check (third run: two slow-corner cases gave no or partial output):
                # frequency and swing at each stage, expected f in brackets
                t = np.real(d["time"])
                dv = ("qp", "qn") if band == "uhf" else ("q2p", "q2n")
                nd = 2 if band == "uhf" else 3
                stages = [("buffer ckp-ckn", np.real(d["ckp"]) - np.real(d["ckn"]), fv),
                          ("CML divider out", np.real(d[dv[0]]) - np.real(d[dv[1]]), fv / nd),
                          ("converter x_o2", np.real(d["x_o2"]), fv / nd),
                          ("clock x_clk", np.real(d["x_clk"]), fv / nd),
                          ("counter x_q1", np.real(d["x_q1"]), fv / ndiv)]
                diag = []
                for lab, v, fexp in stages:
                    fo, amp = L1.freq(t, v, frac=0.5)
                    diag.append(f"{lab} {fo/1e9:.3f} GHz ({fexp/1e9:.3f}), {amp:.2f} V")
                print("Stages: " + "; ".join(diag) + ".")
                # ckp / ckn crossing skew: rising ckp against falling ckn at their common mode
                cp, cn = np.real(d["ckp"]), np.real(d["ckn"])
                m = t >= t[-1] * 0.5
                th = 0.5 * (cp[m].max() + cp[m].min())
                er = edges(t[m], cp[m], th)
                ef = edges(t[m], -cn[m], -th)
                if len(er) > 2 and len(ef) > 2:
                    sk = np.array([ef[np.argmin(np.abs(ef - x))] - x for x in er])
                    tu = np.linspace(t[m][0], t[m][-1], 200000)
                    duty = 100 * np.mean(np.interp(tu, t[m], cp[m]) > th)
                    print(f"Clock skew (ckn falling - ckp rising): {np.mean(sk)*1e12:+.1f} ps (period {1e12/fv:.0f} ps); "
                          f"ckp duty {duty:.1f} %.")
                print(f"VCO {fv/1e9:.4f} GHz. Buffer output: {c['amp_p']:.2f} / {c['amp_n']:.2f} V per side "
                      f"(need ≥ 0.5 × {vdd/1.2:.2f}), common mode {c['cm_p']:.2f} V.")
                print(f"Currents: buffer {res['vbufs']*1e3:.2f} mA, CML divider {res['vdvs']*1e3:.2f} mA, "
                      f"converter {res['vcvs']*1e3:.2f} mA, CMOS logic {res['vdgs']*1e3:.2f} mA.\n")
                print(f"| Output | Node | f (MHz) | Expected (MHz) | Duty (%) | Phase (°) | Ideal (°) | Error (°) |")
                print("|---|---|---|---|---|---|---|---|")
                for lab, node, fo, du, ph in res["rows"]:
                    if fo is None:
                        print(f"| {lab} | {node} | no output |")
                        continue
                    err = ((ph - ideal[node] + 180) % 360) - 180
                    print(f"| {lab} | {node} | {fo/1e6:.2f} | {fv/ndiv/1e6:.2f} | {du:.1f} (ideal {duty_ideal:.0f}) | "
                          f"{ph:.1f} | {ideal[node]} | {err:+.2f} |")
                print()


if __name__ == "__main__":
    main()
