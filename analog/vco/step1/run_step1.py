#!/usr/bin/env python3
"""P2.3 step 1: device checks before the VCO schematic (spec/vco-topology.md section 6).

Run inside the container from this folder:

    python3 run_step1.py            # all checks, a few minutes
    python3 run_step1.py var bank   # selected checks: limits var bank flicker ind

Writes netlists, logs and results to out/ and a summary to out/summary.md.
Each check is independent; a failing check is reported and the others still run.

  limits   LV MOS voltage limits from the SG13G2 process specification -> allowed swing
  var      sg13_hv_svaricap: differential C and Q at 3.0-4.37 GHz against tuning voltage
  bank     capacitor-bank unit cell (2 x cap_rfcmim + LV NMOS switch): C on/off and Q
           against switch width -> fixed-capacitance budget of the 7-bit bank
  flicker  drain-current noise of LV NMOS, LV PMOS and HV NMOS tail devices of equal size
  ind      lumped model of L2n0 fitted to the de-embedded EM data (P2.0, palF1), checked
           in VACASK against the EM L and Q
All results are [SCH] (PDK compact models, typical corner, 27 degC) except 'limits' [DS].
"""
import glob
import json
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

FREQS = [3.00e9, 3.12e9, 3.65e9, 4.20e9, 4.37e9]
VTANK = 1.2              # tank DC (VCO supply at the centre tap), V  [PROP, see 'limits']
C_MIN_BUDGET = 762e-15   # differential fixed-capacitance limit at 4.37 GHz (tank_budget.py)
C_SWITCHED = 955e-15     # switched range the bank must provide (tank_budget.py)
C_OTHER = 145e-15        # core 40 + inductor 45 + buffer 15 + routing 25 + varactor min 20 [HAND]

HEADER = """{title}

include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section=mos_tt
include "cornerMOShv.lib" section=mos_tt
include "cornerCAP.lib" section=cap_typ

load "resistor.osdi"
load "capacitor.osdi"
load "inductor.osdi"

model resistor  resistor
model capacitor capacitor
model inductor  inductor
model vsource   vsource
model isource   isource
"""

SUMMARY = []


def say(line=""):
    print(line)
    SUMMARY.append(line)


def vacask(name, body, control):
    """Write out/<name>.sim, run it, return the rawfile reader (or raise)."""
    path = os.path.join(OUT, name + ".sim")
    with open(path, "w") as fh:
        fh.write(HEADER.format(title=f"P2.3 step 1: {name}") + body + "\ncontrol\n  abort always\n"
                 '  options rawfile="binary"\n' + control + "\nendc\n")
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        tail = open(log).read()[-1500:]
        raise RuntimeError(f"vacask {name}.sim failed (exit {r.returncode}); end of out/{name}.log:\n{tail}")
    from vacask.rawfile import rawread
    return rawread


def ydiff(d):
    """Differential admittance from a run with v1 (port 1) driven and v2 (port 2) AC-grounded."""
    y11 = -np.asarray(d["v1:flow(br)"])
    y21 = -np.asarray(d["v2:flow(br)"])
    return (y11 - y21) / 2


def ac_values():
    return "values=[" + ", ".join(f"{f:.4e}" for f in FREQS) + "]"


# ---------------------------------------------------------------- limits
def check_limits():
    say("## 1. LV MOS voltage limits [DS]")
    say("")
    say("SG13G2 process specification Rev. 1.2 (PDK `libs.doc/doc/SG13G2_os_process_spec.pdf`), section 2.1/2.2:")
    say("LV NMOS and PMOS `VGS <= 1.65 V @ 125 degC`; BVDSS >= 2.0 V (NMOS, 10 x 0.13 um). HV devices: VGS <= 3.3 V.")
    say("")
    say("Cross-coupled NMOS pair, centre tap at V_ct, per-side amplitude A, tail node V_tail (about 0.35 V):")
    say("peak V_GD = 2 A (gate high while its drain is low); peak V_GS = V_ct + A - V_tail; the drain minimum "
        "V_ct - A must stay above V_tail (headroom). So A <= min(V_ox / 2, V_ox - V_ct + V_tail, V_ct - V_tail).")
    say("")
    say("| Oxide limit V_ox | V_ct 1.0 V | V_ct 1.1 V | V_ct 1.2 V |")
    say("|---|---|---|---|")
    vt = 0.35
    for lim, note in ((1.65, "1.65 V (spec, 125 degC)"), (1.5, "1.5 V (10 % margin)")):
        cells = []
        for vct in (1.0, 1.1, 1.2):
            a = min(lim / 2, lim - vct + vt, vct - vt)
            cells.append(f"{2*a:.2f} V diff.")
        say(f"| {note} | " + " | ".join(cells) + " |")
    say("")
    say("The memo assumed 1.0 V differential. With 10 % oxide margin the best centre-tap voltage is about "
        "V_ox / 2 + V_tail = 1.1 V, allowing about 1.5 V differential (+3.5 dB phase noise for the same tank, "
        "at proportionally more current). Final values from the transient peak voltages of the P2.3 schematic.")
    say("")


# ---------------------------------------------------------------- varactor
def svaricap_fixed():
    """Local copy of the VACASK svaricap library with the zero-coefficient v(2,4) terms removed."""
    import re
    src = os.path.join(os.environ["PDK_ROOT"], os.environ["PDK"], "libs.tech", "vacask", "models",
                       "sg13g2_svaricaphv_mod.lib")
    text = open(src).read()
    for par in ("rwellvw", "rwellwvw", "rwellnxvw"):
        if not re.search(par + r"\s*=\s*0(?![.\deE])", text):
            raise RuntimeError(f"{par} is not 0 in {src}: the v(2,4) term cannot simply be dropped")
    text, n = re.subn(r"\(\s*rwell(?:vw|wvw|nxvw)\s*\*\s*\(\s*v\(\s*2\s*,\s*4\s*\)\s*\)\s*\)", "0", text)
    if n == 0 or re.search(r"[^\w]v\(", text):
        raise RuntimeError(f"unexpected form of the well-resistance expression in {src} ({n} terms replaced)")
    text = text.replace("sg13_hv_svaricap", "sg13_hv_svaricap_fx")
    text = re.sub(r"\bdsubw\b", "dsubw_fx", text)
    dst = os.path.join(OUT, "svaricap_fx.lib")
    with open(dst, "w") as fh:
        fh.write("// Generated by run_step1.py from " + src + "\n"
                 "// (IHP Open PDK, Apache-2.0): zero-coefficient v(2,4) terms removed, names suffixed _fx.\n" + text)
    return dst


def check_var():
    say("## 2. sg13_hv_svaricap: differential C and Q [SCH]")
    say("")
    say(f"Gates (G1, G2) at the tank DC {VTANK} V, well W at V_tune, substrate 0 V. "
        "Small-signal; the real tank averages C over the swing. Spec (process spec 2.11): 35.3 fF/um^2 at 0 V, "
        "Q 43-62 at 15.8 GHz for 10 x (3.74 x 0.3) um^2.")
    say("")
    fixed = svaricap_fixed()
    say("The PDK's VACASK conversion of `sg13_hv_svaricap` does not elaborate (its well resistance uses `v(2,4)`, "
        "which VACASK expressions do not support). The coefficients of those terms are 0 in the PDK, so a local copy "
        f"with the terms set to 0 is used (`{os.path.relpath(fixed, REPO)}`, subckt `sg13_hv_svaricap_fx`); "
        "the model itself is unchanged.")
    say("")
    vtunes = [round(0.2 * i, 2) for i in range(0, 13)]       # 0 .. 2.4 V
    sizes = [(3.74, 0.3, 1), (3.74, 0.3, 2)]
    for w, l, nx in sizes:
        rows = []
        for vt in vtunes:
            name = f"var_w{w}_l{l}_nx{nx}_v{vt:.1f}"
            body = (f"vg (gm 0) vsource dc={VTANK}\n"
                    "v1 (g1 gm) vsource dc=0 mag=1\n"
                    "v2 (g2 gm) vsource dc=0\n"
                    f"vw (w 0) vsource dc={vt}\n"
                    f"xv (g1 w g2 0) sg13_hv_svaricap_fx w={w}u l={l}u nx={nx}\n")
            body = f'include "{fixed}"\n' + body
            rr = vacask(name, body, f"  analysis ac1 ac {ac_values()}")
            d = rr(os.path.join(OUT, "ac1.raw")).get()
            f = np.real(d["frequency"])
            y = ydiff(d)
            c = np.imag(y) / (2 * np.pi * f)
            q = np.imag(y) / np.real(y)
            rows.append((vt, c, q))
        say(f"**{nx} x ({w} x {l}) um^2 per side** (differential C in fF / Q):")
        say("")
        say("| V_tune (V) | V_G - V_W (V) | " + " | ".join(f"{x/1e9:.2f} GHz" for x in FREQS) + " |")
        say("|---|---|" + "---|" * len(FREQS))
        for vt, c, q in rows:
            say(f"| {vt:.1f} | {VTANK - vt:+.1f} | " + " | ".join(f"{ci*1e15:.1f} / {qi:.0f}" for ci, qi in zip(c, q)) + " |")
        c42 = np.array([r[1][3] for r in rows])
        vts = np.array([r[0] for r in rows])
        slope = np.gradient(c42, vts)
        k = int(np.argmax(np.abs(slope)))
        say("")
        say(f"C range {c42.min()*1e15:.1f}-{c42.max()*1e15:.1f} fF; steepest {abs(slope[k])*1e15:.1f} fF/V at "
            f"V_tune {vts[k]:.1f} V (at 4.2 GHz). Needed: about 10 fF over the tuning window (7-bit bank).")
        say("")


# ---------------------------------------------------------------- bank
def check_bank():
    say("## 3. Capacitor-bank unit cell [SCH]")
    say("")
    say("Differential cell: tank+ - cap_rfcmim - a - LV NMOS switch - b - cap_rfcmim - tank-; a and b biased through "
        "R_bias to 0 V (switch on, gate 1.2 V) or 1.2 V (switch off, gate 0 V). Bottom plates toward the switch.")
    wm = 9.0                                                  # MIM 9 x 9 um: about 120 fF each, ~60 fF differential
    widths = [16, 32, 64, 96, 128]
    rbias = [20e3, 200e3]
    say(f"MIM {wm} x {wm} um each (about {1.5*wm*wm/2:.0f} fF differential when on). First run (2026-10-20): "
        "switches of 2-32 um gave Q_on 2-28 at 4.2 GHz, so wider switches are tried here.")
    say("")
    say("Bank evaluation: a 7-bit bank of scaled cells switching 955 fF. All on at 3.12 GHz (low edge) and all off "
        "at 4.20 GHz (high edge); tank Q from EM 14.2 / 16.9; 'Q kept' = tank Q with the bank / without "
        "(the memo assumed 0.85 for bank and varactor together).")
    say("")
    say("| R_bias | W (um) | C_on (fF) | C_off (fF) | C_on/C_off | Q_on 3.12 | Q_off 4.20 | Bank off-C (fF) | "
        "Budget margin (fF) | Q kept, low edge | Q kept, high edge |")
    say("|---|---|---|---|---|---|---|---|---|---|---|")
    i312, i42 = FREQS.index(3.12e9), FREQS.index(4.20e9)
    ct_lo = 1 / ((2 * math.pi * 3.12e9) ** 2 * 1.69e-9)
    ct_hi = 1 / ((2 * math.pi * 4.20e9) ** 2 * 1.69e-9)
    res = []
    for rb in rbias:
        for ws in widths:
            ng = max(1, int(round(ws / 2.0)))
            out = {}
            for state, vg, vb in (("on", 1.2, 0.0), ("off", 0.0, 1.2)):
                name = f"bank_r{int(rb/1e3)}k_w{ws}_{state}"
                body = (f"vt (tc 0) vsource dc={VTANK}\n"
                        "v1 (tp tc) vsource dc=0 mag=1\n"
                        "v2 (tn tc) vsource dc=0\n"
                        f"xc1 (tp a 0) cap_rfcmim w={wm}u l={wm}u\n"
                        f"xc2 (tn b 0) cap_rfcmim w={wm}u l={wm}u\n"
                        f"ms (a g b 0) sg13_lv_nmos w={ws}u l=0.13u ng={ng}\n"
                        f"vg (g 0) vsource dc={vg}\n"
                        f"ra (a bias) resistor r={rb:g}\n"
                        f"rb (b bias) resistor r={rb:g}\n"
                        f"vb (bias 0) vsource dc={vb}\n")
                rr = vacask(name, body, f"  analysis ac1 ac {ac_values()}")
                d = rr(os.path.join(OUT, "ac1.raw")).get()
                f = np.real(d["frequency"])
                y = ydiff(d)
                out[state] = (np.imag(y) / (2 * np.pi * f), np.imag(y) / np.real(y))
            con, qon = out["on"]
            coff, qoff = out["off"]
            r = con[i42] / coff[i42]
            c_on_tot = C_SWITCHED * r / (r - 1)
            c_off_tot = C_SWITCHED / (r - 1)
            margin = C_MIN_BUDGET - C_OTHER - c_off_tot
            q_lo = 1 / (1 / 14.2 + (c_on_tot / ct_lo) / qon[i312])
            q_hi = 1 / (1 / 16.9 + (c_off_tot / ct_hi) / qoff[i42])
            k_lo, k_hi = q_lo / 14.2, q_hi / 16.9
            res.append((rb, ws, r, margin, k_lo, k_hi))
            say(f"| {rb/1e3:.0f} k | {ws} | {con[i42]*1e15:.1f} | {coff[i42]*1e15:.1f} | {r:.2f} | {qon[i312]:.0f} | "
                f"{qoff[i42]:.0f} | {c_off_tot*1e15:.0f} | {margin*1e15:+.0f} | {k_lo:.2f} | {k_hi:.2f} |")
    say("")
    ok = [x for x in res if x[3] >= 50e-15]
    if ok:
        rb, ws, r, margin, k_lo, k_hi = max(ok, key=lambda x: min(x[4], x[5]))
        say(f"Best with at least 50 fF budget margin: R_bias {rb/1e3:.0f} kOhm, W {ws} um per 60 fF cell "
            f"(C_on/C_off {r:.2f}): Q kept {k_lo:.2f} (low edge) / {k_hi:.2f} (high edge), margin {margin*1e15:+.0f} fF.")
    else:
        say("**No cell leaves 50 fF budget margin:** the tuning range or the bank structure has to change.")
    say("")


# ---------------------------------------------------------------- flicker
def check_flicker():
    say("## 4. Tail-device current noise [SCH]")
    say("")
    itail = 3e-3
    say(f"Each device biased at {itail*1e3:.0f} mA by a replica whose gate is shorted to AC ground by 1 F (so only the "
        "device under test is noisy), drain held at |V_DS| = 0.6 V and 0.35 V (the expected tail node) through 1 Ohm; "
        "output = drain current noise; I_D shows whether the device keeps its current at 0.35 V (headroom).")
    say("First run (2026-10-20, 0.6 V): corner LV NMOS 80/2 1.26 MHz, LV PMOS 3.2 MHz, HV NMOS 0.5 MHz.")
    say("")
    devs = [
        ("LV NMOS 80/2 um", "sg13_lv_nmos", 80, 2.0, "n"),
        ("LV PMOS 80/2 um", "sg13_lv_pmos", 80, 2.0, "p"),
        ("HV NMOS 80/2 um", "sg13_hv_nmos", 80, 2.0, "n"),
        ("LV NMOS 160/4 um (4x area)", "sg13_lv_nmos", 160, 4.0, "n"),
        ("HV NMOS 160/4 um (4x area)", "sg13_hv_nmos", 160, 4.0, "n"),
    ]
    offs = [1e4, 1e5, 6e5, 1e6, 2e6]
    say("| Device | V_DS | I_D (mA) | " + " | ".join(f"S_i @ {f/1e3:.0f} kHz" if f < 1e6 else f"S_i @ {f/1e6:.0f} MHz" for f in offs)
        + " | White floor | 1/f corner |")
    say("|---|---|---|" + "---|" * (len(offs) + 2))
    for (label, mdl, w, l, pol), vds in [(dv, v) for dv in devs for v in (0.6, 0.35)]:
        ng = max(1, int(round(w / 5.0)))
        name = "flk_" + label.split()[0].lower() + "_" + label.split()[1].lower() + f"_w{w}_l{l}_vds{vds}"
        if pol == "n":
            body = (f"vdd (vdd 0) vsource dc=1.2\n"
                    f"iref (vdd g) isource dc={itail}\n"
                    f"mr (g g 0 0) {mdl} w={w}u l={l}u ng={ng}\n"
                    "cg (g 0) capacitor c=1\n"
                    f"md (d g 0 0) {mdl} w={w}u l={l}u ng={ng}\n")
        else:
            body = (f"vdd (vdd 0) vsource dc=1.2\n"
                    f"iref (g 0) isource dc={itail}\n"
                    f"mr (g g vdd vdd) {mdl} w={w}u l={l}u ng={ng}\n"
                    "cg (g 0) capacitor c=1\n"
                    f"md (d g vdd vdd) {mdl} w={w}u l={l}u ng={ng}\n")
        vdc = vds if pol == "n" else 1.2 - vds
        body += f"rs (d vd) resistor r=1 noisy=0\nvd (vd 0) vsource dc={vdc}\n"
        try:
            rr = vacask(name, body, "  analysis op1 op\n"
                        '  analysis n1 noise out=["d", "vd"] in="vd" from=1k to=1G mode="dec" points=20')
            d = rr(os.path.join(OUT, "n1.raw")).get()
            idrain = abs(float(np.real(np.asarray(rr(os.path.join(OUT, "op1.raw")).get()["vd:flow(br)"])).ravel()[0]))
        except Exception as e:                                   # noqa: BLE001
            say(f"| {label} | failed: {str(e).splitlines()[0]} |")
            continue
        f = np.real(d["frequency"])
        s = np.real(d["onoise"])                                 # V^2/Hz across 1 ohm = A^2/Hz
        floor = float(np.median(s[(f >= 1e8) & (f <= 5e8)]))
        above = np.where(s > 2 * floor)[0]
        corner = f[above.max()] if len(above) else float("nan")
        vals = [float(np.interp(math.log10(x), np.log10(f), s)) for x in offs]
        say(f"| {label} | {vds:.2f} | {idrain*1e3:.2f} | " + " | ".join(f"{v:.2e}" for v in vals) + f" | {floor:.2e} | "
            + (f"{corner/1e3:.0f} kHz" if corner == corner else "—") + " |")
    say("")
    say("Units A^2/Hz. A device that loses current at 0.35 V lacks headroom for the tail. Flicker scales about as "
        "1/(W L): the 4x-area rows show what size buys.")
    say("")


# ---------------------------------------------------------------- inductor
def read_s2p(path):
    freq, rows, scale, form = [], [], 1.0, "MA"
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("!"):
            continue
        if line.startswith("#"):
            t = line[1:].split()
            scale = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}[t[0].lower()]
            form = t[2].upper()
            continue
        p = [float(x) for x in line.split()]
        freq.append(p[0] * scale)
        rows.append(p[1:9])
    def cx(a, b):
        if form == "RI":
            return complex(a, b)
        mag = 10 ** (a / 20) if form == "DB" else a
        return mag * complex(math.cos(math.radians(b)), math.sin(math.radians(b)))
    f = np.array(freq)
    zd = []
    for r in rows:
        s11, s21, s12, s22 = cx(r[0], r[1]), cx(r[2], r[3]), cx(r[4], r[5]), cx(r[6], r[7])
        s = np.array([[s11, s12], [s21, s22]])
        z = 50 * (np.eye(2) + s) @ np.linalg.inv(np.eye(2) - s)
        zd.append(z[0, 0] - z[0, 1] - z[1, 0] + z[1, 1])
    return f, np.array(zd)


def model_z(p, f):
    l1, r1, r2, l2, cp = p
    w = 2 * np.pi * f
    zs = r1 + 1j * w * l1 + (r2 * 1j * w * l2) / (r2 + 1j * w * l2)
    return 1 / (1 / zs + 1j * w * cp)


def check_ind():
    from scipy.optimize import least_squares
    say("## 5. Lumped model of L2n0 [EM] -> [SCH]")
    say("")
    p20 = os.path.join(REPO, "sim", "em", "sg13-octagon-l2n0", "p20")
    src = None
    js = os.path.join(p20, "out", "p20", "palF1.json")
    if os.path.exists(js):
        cand = json.load(open(js)).get("deembedded_source")
        for c in (cand, os.path.join(p20, cand or "")):
            if c and os.path.exists(c):
                src = c
                break
    if not src:
        hits = glob.glob(os.path.join(p20, "palace_model", "*palF1*", "**", "*_deembedded.s2p"), recursive=True)
        src = hits[0] if hits else None
    if not src:
        say("De-embedded EM file of palF1 not found (P2.0 output under sim/em/sg13-octagon-l2n0/p20/); check skipped.")
        say("")
        return
    f, zd = read_s2p(src)
    m = (f >= 2.0e9) & (f <= 4.5e9)
    f, zd = f[m], zd[m]
    x0 = np.log([1.6e-9, 1.5, 20.0, 0.1e-9, 10e-15])
    def resid(x):
        e = (model_z(np.exp(x), f) - zd) / np.abs(zd)
        return np.concatenate([e.real, e.imag])
    fit = least_squares(resid, x0, xtol=1e-12, ftol=1e-12, max_nfev=20000)
    p = np.exp(fit.x)
    l1, r1, r2, l2, cp = p
    say(f"Source: `{os.path.relpath(src, REPO)}` ({len(f)} points, 2.0-4.5 GHz).")
    say(f"Fit: L1 {l1*1e9:.4f} nH, R1 {r1:.3f} Ohm, R2 {r2:.2f} Ohm parallel L2 {l2*1e12:.1f} pH, "
        f"Cp {cp*1e15:.2f} fF (differential), worst relative error {np.max(np.abs(resid(fit.x)))*100:.2f} %.")
    inc = os.path.join(HERE, "..", "models", "l2n0_lumped.inc")
    os.makedirs(os.path.dirname(inc), exist_ok=True)
    with open(inc, "w") as fh:
        fh.write("// Lumped differential model of SG13_Octagon_L2n0, fitted to the de-embedded EM data of P2.0\n"
                 "// (Palace, filled metals, 1 um; analog/vco/step1/run_step1.py). Valid 2.0-4.5 GHz, differential\n"
                 "// mode. The centre tap is the electrical midpoint of a symmetric split; the L2n0 GDS is a\n"
                 "// two-port without a tap, so the tap is an assumption until a tapped layout is EM-simulated.\n"
                 "// Needs models resistor, inductor, capacitor in the including netlist.\n"
                 "subckt l2n0(p n ct)\n"
                 f"  r1p (p p1) resistor r={r1/2:.6g}\n"
                 f"  l1p (p1 p2) inductor l={l1/2:.6g}\n"
                 f"  r2p (p2 ct) resistor r={r2/2:.6g}\n"
                 f"  l2p (p2 ct) inductor l={l2/2:.6g}\n"
                 f"  r1n (n n1) resistor r={r1/2:.6g}\n"
                 f"  l1n (n1 n2) inductor l={l1/2:.6g}\n"
                 f"  r2n (n2 ct) resistor r={r2/2:.6g}\n"
                 f"  l2n (n2 ct) inductor l={l2/2:.6g}\n"
                 f"  cp (p n) capacitor c={cp:.6g}\n"
                 "ends\n")
    say(f"Written: `analog/vco/models/l2n0_lumped.inc` (subckt `l2n0 (p n ct)`).")
    body = ('include "' + os.path.abspath(inc) + '"\n'
            "vg (gm 0) vsource dc=0\nv1 (p gm) vsource dc=0 mag=1\nv2 (n gm) vsource dc=0\nxl (p n ct) l2n0\n")
    rr = vacask("ind_check", body, f"  analysis ac1 ac {ac_values()}")
    d = rr(os.path.join(OUT, "ac1.raw")).get()
    fv = np.real(d["frequency"])
    zv = 1 / ydiff(d)              # Zdiff = (V1 - V2) / I1 under differential drive = Z11 - Z12 - Z21 + Z22
    say("")
    say("| f (GHz) | L EM (nH) | L model (nH) | Q EM | Q model | dL | dQ |")
    say("|---|---|---|---|---|---|---|")
    worst = 0.0
    for fi, zi in zip(fv, zv):
        ze = np.interp(fi, f, zd.real) + 1j * np.interp(fi, f, zd.imag)
        w = 2 * np.pi * fi
        le, qe = ze.imag / w, ze.imag / ze.real
        lm, qm = zi.imag / w, zi.imag / zi.real
        dl, dq = 100 * (lm / le - 1), 100 * (qm / qe - 1)
        worst = max(worst, abs(dl), abs(dq))
        say(f"| {fi/1e9:.2f} | {le*1e9:.4f} | {lm*1e9:.4f} | {qe:.2f} | {qm:.2f} | {dl:+.2f} % | {dq:+.2f} % |")
    say("")
    say(f"Worst difference {worst:.2f} % ({'PASS' if worst <= 1 else 'FAIL'}, limit 1 %).")
    say("")


CHECKS = {"limits": check_limits, "var": check_var, "bank": check_bank, "flicker": check_flicker,
          "ind": check_ind}


def main():
    os.makedirs(OUT, exist_ok=True)
    sel = sys.argv[1:] or list(CHECKS)
    say("# P2.3 step 1 — device checks")
    say("")
    for k in sel:
        try:
            CHECKS[k]()
        except Exception as e:                                   # noqa: BLE001
            say(f"**Check '{k}' failed:** {e}")
            say("")
    with open(os.path.join(OUT, "summary.md"), "w") as fh:
        fh.write("\n".join(SUMMARY) + "\n")
    print(f"\nSummary written to {os.path.relpath(os.path.join(OUT, 'summary.md'), REPO)}")


if __name__ == "__main__":
    main()
