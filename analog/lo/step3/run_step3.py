#!/usr/bin/env python3
"""P2.4 step 3: LO chains across corners and temperature, and Monte Carlo of the phase and duty errors
(spec/lo-divider-topology.md §6, step 3).

Run inside the container from this folder:

    mkdir -p out
    python3 -u run_step3.py corners | tee out/summary_corners.txt    # 7 corners x 4 cases, about 1 h
    python3 -u run_step3.py mc | tee out/summary_mc.txt              # 2 corners x 2 cases x 25 samples, a few h
    python3 -u run_step3.py mc n=10 uhf tt                           # smaller: options uhf / vhf, tt / ss, n=<samples>

Circuit: the final step-2 chain (`analog/lo/step2/run_step2.py`: buffer with gain stage and 4/8 um last inverter,
CML ÷2 / ÷3 enabled after start-up (D15), converter, TSPC Johnson counters, all outputs retimed, UHF retiming
output PMOS 2x). The VCO is replaced by an ideal differential sine on the tank nodes, so each run takes minutes
instead of the VCO's start-up and bias settling; the VCO itself is covered by P2.3. The tank swing per side is the
lowest the VCO gives at that frequency over its corners (VCO step 3 with the 4 mA cap: 0.59 V differential at
3.12 GHz, fast / MIM worst case / 85 °C, about 1.14 V at 4.20 GHz), lowered a little more for 125 °C:
0.27 V per side at 3.12 GHz to 0.52 V at 4.20 GHz, linear in between. So every corner here sees a pessimistic clock.

Monte Carlo: PDK mismatch values (sg13g2_moslv_mismatch.lib): sigma(V_T) = 3.9 mV um / sqrt(W L) (NMOS),
2.2 mV um (PMOS); sigma(beta) = 0.5 % um / 0.33 % um; sigma(W) 4 nm, sigma(L) 2 nm. Applied per transistor as a
series gate source (V_T) and a width change (W, beta) on every LO device (buffer, CML, converter, logic), so it does
not depend on statistical support in the simulator's model library. CML load-resistor mismatch is left out: it
moves the CML duty cycle only, which the retiming removes. Results are [SCH].
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
_spec = importlib.util.spec_from_file_location("lo_step2", os.path.join(REPO, "analog", "lo", "step2", "run_step2.py"))
L2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L2)
L1 = L2.L1
L2.EN_NS = 2.0          # ideal clock is up at once; the divider still starts through the D15 enable

#           tag, section, V_DD, T (degC)
CORNERS = [("tt", "mos_tt", 1.20, 27), ("ss", "mos_ss", 1.08, 125), ("ss-cold", "mos_ss", 1.08, -40),
           ("ff", "mos_ff", 1.32, -40), ("ff-hot", "mos_ff", 1.32, 125), ("sf", "mos_sf", 1.20, 27),
           ("fs", "mos_fs", 1.20, 27)]
CASES = {"uhf": [3.20e9, 3.84e9], "vhf": [3.12e9, 4.20e9]}
MM = {"n": (3.9e-3, 0.005), "p": (2.2e-3, 0.0033)}      # A_VT (V um), A_beta (um)
DW, DL = 4e-9, 2e-9


def tank_amp(f):
    """Lowest VCO swing per side at f over the VCO corners (see module text)."""
    return float(np.interp(f, [3.12e9, 4.20e9], [0.27, 0.52]))


def mismatch(text, rng):
    """Random V_T, beta, W and L offsets on every sg13_lv MOS line of the LO netlist."""
    pat = re.compile(r"^(\S+) \((\S+) (\S+) (\S+) (\S+)\) sg13_lv_(n|p)mos w=([\d.]+)u l=([\d.]+)u(.*)$")
    out, k = [], 0
    for ln in text.splitlines():
        m = pat.match(ln)
        if not m:
            out.append(ln)
            continue
        name, d, g, s, b, typ, w, l, rest = m.groups()
        w, l = float(w), float(l)
        avt, ab = MM[typ]
        dvt = rng.normal(0, avt / math.sqrt(w * l))
        beta = rng.normal(1, ab / math.sqrt(w * l))
        w2 = (w + rng.normal(0, DW * 1e6)) * beta
        l2 = l + rng.normal(0, DL * 1e6)
        k += 1
        out.append(f"vmm{k} (x_mmg{k} {g}) vsource dc={dvt:.5e}")
        out.append(f"{name} ({d} x_mmg{k} {s} {b}) sg13_lv_{typ}mos w={w2:.4f}u l={l2:.4f}u{rest}")
    return "\n".join(out) + "\n"


def build(band, f, corner, rng=None, tag=""):
    ctag, mos, vdd, temp = corner
    body, names, ideal, ndiv, duty = L2.chain(band, vdd)
    lo = (f"vbufs (vbuf 0) vsource dc={vdd}\nvdvs (vdv 0) vsource dc={vdd}\n"
          f"vcvs (vcv 0) vsource dc={vdd}\nvdgs (vdg 0) vsource dc={vdd}\n" + L2.buffer() + body)
    if rng is not None:
        lo = mismatch(lo, rng)
    stop = 3e-9 + (24 * 8 if band == "uhf" else 20 * 24) / f
    name = f"lo3_{band}_{ctag}_{f/1e9:.2f}{tag}"
    path = os.path.join(OUT, name + ".sim")
    with open(path, "w") as fh:
        fh.write(L1.HEADER.format(title=f"P2.4 step 3: {name}", mos=mos, vcm=1.1, amp=tank_amp(f), shape=0.0,
                                  f=f, offs=0.0, t0=-1.0, tr=1e-12))
        fh.write(f"vdd (vdd 0) vsource dc={vdd}\nxtank (tp tn) clk\n" + lo)
        fh.write("\ncontrol\n  abort always\n  options rawfile=\"binary\"\n"
                 f"  options temp={temp}\n"
                 f"  analysis tr tran stop={stop:.4e} step=5p maxstep=5p\nendc\n")
    return path, names, ideal, ndiv, duty


def run(path):
    from vacask.rawfile import rawread
    name = os.path.basename(path)[:-4]
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(f"vacask {name}.sim failed; end of out/{name}.log: " + open(log).read()[-800:])
    return rawread(os.path.join(OUT, "tr.raw")).get()


def one(band, f, corner, rng=None, tag=""):
    """Run one case; returns (ok, rows, result dict)."""
    vdd = corner[2]
    path, names, ideal, ndiv, duty = build(band, f, corner, rng, tag)
    d = run(path)
    res = L2.analyse(d, names, ideal, ndiv, duty, vdd, f)
    rows = []
    ok = True
    for lab, node, fo, du, ph in res["rows"]:
        if fo is None or abs(fo * ndiv / f - 1) > 0.002:
            ok = False
            rows.append((lab, node, None, None, None))
            continue
        err = ((ph - ideal[node] + 180) % 360) - 180
        rows.append((lab, node, fo, du, err))
    return ok, rows, res, duty


def check_corners(bands, corners):
    print("## Corners and temperature [SCH]\n")
    print("Ideal tank source with the lowest VCO swing (per side): "
          + ", ".join(f"{f/1e9:.2f} GHz {tank_amp(f):.2f} V" for f in sorted({x for b in bands for x in CASES[b]}))
          + ". Systematic errors only (no mismatch).\n")
    print("| Band | Corner | V_DD | T (°C) | VCO (GHz) | Divides | Max phase error (°) | Duty (%) | "
          "Buffer per side (V) | Chain current (mA): buffer / CML / converter / logic = total |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for band in bands:
        for corner in corners:
            for f in CASES[band]:
                ctag, mos, vdd, temp = corner
                try:
                    ok, rows, res, duty = one(band, f, corner)
                except RuntimeError as e:
                    print(f"| {band.upper()} | {ctag} | {vdd} | {temp} | {f/1e9:.2f} | error | {str(e)[-200:]!r} | | | |")
                    continue
                errs = [abs(r[4]) for r in rows if r[4] is not None]
                dus = [r[3] for r in rows if r[3] is not None]
                cur = [res[k] * 1e3 for k in ("vbufs", "vdvs", "vcvs", "vdgs")]
                c = res["clk"]
                print(f"| {band.upper()} | {ctag} | {vdd} | {temp} | {f/1e9:.2f} | {'yes' if ok else '**NO**'} | "
                      f"{(max(errs) if errs else float('nan')):.2f} | "
                      f"{(min(dus) if dus else float('nan')):.1f}–{(max(dus) if dus else float('nan')):.1f} "
                      f"(ideal {duty:.0f}) | {min(c['amp_p'], c['amp_n']):.2f} | "
                      + " / ".join(f"{x:.2f}" for x in cur) + f" = {sum(cur):.2f} |")
    print()


def check_mc(bands, corners, n):
    print(f"## Monte Carlo, {n} samples per case [SCH]\n")
    print("Mismatch on every LO transistor (V_T, beta, W, L; PDK values), top frequency of each band (largest error "
          "in degrees). Phase error of each output against its ideal position, relative to the first output; "
          "duty cycle per output. UHF image rejection from the I/Q quadrature error alone (gain matched): "
          "IRR = 10 log10((1 + cos e) / (1 - cos e)), at the 3-sigma error.\n")
    for band in bands:
        f = CASES[band][-1]
        for corner in corners:
            ctag, mos, vdd, temp = corner
            errs, duties, fails = {}, {}, 0
            for k in range(n):
                rng = np.random.default_rng(1000 + k)
                try:
                    ok, rows, res, duty = one(band, f, corner, rng, f"_mc{k}")
                except RuntimeError:
                    fails += 1
                    continue
                if not ok:
                    fails += 1
                    continue
                for lab, node, fo, du, err in rows:
                    errs.setdefault(lab, []).append(err)
                    duties.setdefault(lab, []).append(du)
                print(f"  {band} {ctag} sample {k + 1}/{n} done", file=sys.stderr)
            print(f"### {band.upper()}, {ctag} ({vdd} V, {temp} °C), VCO {f/1e9:.2f} GHz: "
                  f"{n - fails} of {n} samples divide correctly\n")
            if not errs:
                print("no valid samples\n")
                continue
            print("| Output | Phase error mean (°) | sigma (°) | max abs (°) | Duty mean (%) | sigma (%) |")
            print("|---|---|---|---|---|---|")
            for lab in errs:
                e, du = np.array(errs[lab]), np.array(duties[lab])
                print(f"| {lab} | {e.mean():+.2f} | {e.std(ddof=1) if len(e) > 1 else 0:.2f} | {np.abs(e).max():.2f} | "
                      f"{du.mean():.1f} | {du.std(ddof=1) if len(du) > 1 else 0:.2f} |")
            sig = [np.std(v, ddof=1) for lab, v in errs.items() if len(v) > 1 and np.std(v) > 0]
            if band == "uhf" and "Q+" in errs and len(errs["Q+"]) > 1:
                q = np.array(errs["Q+"])                    # Q+ against I+ = quadrature error
                e3 = math.radians(abs(q.mean()) + 3 * q.std(ddof=1))
                irr = 10 * math.log10((1 + math.cos(e3)) / (1 - math.cos(e3)))
                print(f"\nQuadrature error (Q+ vs I+): mean {q.mean():+.2f}°, sigma {q.std(ddof=1):.2f}° -> "
                      f"IRR at mean + 3 sigma ({math.degrees(e3):.2f}°): **{irr:.1f} dB** (target ≥ 40 dB after "
                      f"host calibration, so before calibration this is the raw value)")
            if sig:
                print(f"\nLargest phase sigma: {max(sig):.2f}° "
                      f"({max(sig) / 360 / f * (8 if band == 'uhf' else 24) * 1e12:.1f} ps)")
            print()


def main():
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    bands = [a for a in args if a in CASES] or ["uhf", "vhf"]
    n = next((int(a[2:]) for a in args if a.startswith("n=")), 25)
    print("# P2.4 step 3 — LO chains across corners, Monte Carlo\n")
    print(f"Chain as step 2 final: buffer {'3' if L2.BUFM else '2'} inverters per side, last {L2.B2:g}/{2*L2.B2:g} um; "
          f"UHF retiming output PMOS x{L2.PQ:g}; CML enable at {L2.EN_NS:g} ns.\n")
    if "corners" in args or not any(a in args for a in ("corners", "mc")):
        corners = [c for c in CORNERS if c[0] in args] or CORNERS
        check_corners(bands, corners)
    if "mc" in args:
        corners = [c for c in CORNERS if c[0] in args and c[0] in ("tt", "ss")] or CORNERS[:2]
        check_mc(bands, corners, n)


if __name__ == "__main__":
    main()
