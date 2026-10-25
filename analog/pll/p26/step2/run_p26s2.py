#!/usr/bin/env python3
"""P2.6 step 2: noise from the circuits instead of the P2.2 proposals (spec/pll-topology.md §13).

Run inside the container from this folder:

    mkdir -p out
    python3 -u run_p26s2.py cp | tee out/summary_cp.txt          # charge pump + bias generator noise, ~10 min
    python3 -u run_p26s2.py lo | tee out/summary_lo.txt          # LO-chain noise floor, transient noise, a few h
    python3 -u run_p26s2.py lo tstop=1u                          # shorter trial (coarser spectrum)
    python3 -u run_p26s2.py total | tee out/summary_total.txt    # total phase noise from out/*.json (seconds)
    python3 -u run_p26s2.py cp contrib                           # plus the per-device noise contributions (UP, tt)

cp     The step-4 charge pump with its bias generator (all transistor level, offset pair on), output held at
       V_tune through a noiseless 1 Ohm sense resistor; small-signal noise analysis with the pump forced into the
       three states it takes in lock: off (sources steered to the dummy node, only the offset sink reaches the
       output), UP only, UP and DN (the reset overlap). Locked, UP is on for the D18 offset time (I_off / I_cp x
       T_ref = 2.78 ns) plus the reset (0.25 ns), DN only for the reset, so the average output noise is
       S = d_up S(UP) + d_both S(UP+DN) + (1 - d_up - d_both) S(off)      (valid for offsets << f_ref).
       Referred to the PFD: S_theta = S (2 pi / I_cp)^2; as the P2.2 figure of merit FoM = 10 log(S_theta / 2) -
       10 log f_ref, and a 1/f corner. I_cp 50 uA (code 1, the P2.2 design point) and 100 uA (code 3). Resistors
       noisy (R_B of the bias generator included). tt / ss / ff at V_tune 0.6 V.
lo     The P2.4 LO chains (final step-3 circuit: buffer, CML ÷2 / ÷3, converter, TSPC counters, retiming) driven by
       a noiseless ideal tank sine of the typical VCO swing, in a transient with device and resistor noise
       (noisemode="zoh", as validated in analog/pn-validation). The output edge times against a straight line
       give the time-interval error; its spectrum times (2 pi f_LO)^2 / 2 is L(f) of the LO output. The same run
       without noise gives the numerical floor. UHF at 3.84 GHz (480 MHz LO), VHF at 4.20 GHz (175 MHz), tt; option
       'ss' adds the slow corner. Replaces the P2.4 hand estimate (-157 / -161 dBc/Hz) - the pss/pnoise method
       failed on these dynamic circuits.
total  P2.2 model (corrected, D19 loop) with: the VCO per band from P2.3 / D20 (L at 1 MHz interpolated over the
       five simulated bands), the charge-pump FoM and corner from 'cp', the LO floor from 'lo' added at RF; at the
       duplex offsets against -136 dBc/Hz (25 W) per band edge.
Results are [SCH] (cp, lo) and [MODEL] (total).
"""
import importlib.util
import json
import math
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(HERE, "out")
ARGS = sys.argv[1:]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


F_REF = 36e6
T_REF = 1 / F_REF
T_RST = 0.25e-9
OFFS = [1e3, 1e4, 1e5, 6e5, 2e6, 1e7]


# ------------------------------------------------------------------------------------------------------ cp
def check_cp():
    S4 = load("pll_step4", "analog/pll/step4/run_step4.py")
    S2 = S4.S2
    S4.OUT = OUT
    S2.OUT = OUT
    print("## Charge-pump and bias-generator noise [SCH]\n")
    print("Output current noise (A²/Hz) of the step-4 pump with its bias generator, offset pair on, V_tune 0.6 V. "
          "States: off (only the offset sink reaches the output), UP, UP + DN. Average in lock with d_up = "
          f"(0.1 T_ref + {T_RST*1e9:.2f} ns) / T_ref and d_both = {T_RST*1e9:.2f} ns / T_ref. FoM as in P2.2 "
          "(PFD-referred, 1 Hz, normalised to f_ref); P2.2 assumed −218 dBc/Hz with a 20 kHz corner.\n")
    d_both = T_RST / T_REF
    d_up = 0.1
    res = {}
    print("| Corner | I_cp (µA) | State | " + " | ".join(f"{o/1e3:g} kHz" for o in OFFS) + " |")
    print("|---|---|---|" + "---|" * len(OFFS))
    summary = []
    for cname in ("tt", "ss", "ff"):
        _, mos, vdd, temp = next(c for c in S2.CORNERS if c[0] == cname)
        for icp in (50e-6, 100e-6):
            spec = {}
            for lab, uv, dv in (("off", 0, 0), ("UP", 1, 0), ("UP+DN", 1, 1)):
                body = (f"vdd (vdd 0) vsource dc={vdd}\n"
                        "rs (vt vtx) resistor r=1 noisy=0\nvtn (vtx 0) vsource dc=0.6\n"
                        f"vup (up 0) vsource dc={uv * vdd}\nvdn (dn 0) vsource dc={dv * vdd}\n"
                        + S4.use_bias(S2.charge_pump(icp) + S2.offset_sink(icp) + S4.biasgen()))
                # resistors noisy (the bias generator's R_B in particular); the sense resistor stays noiseless
                body = re.sub(r"(\) resistor r=\S+)(?=\s|$)(?!\s+noisy)", r"\1 noisy=1", body)
                name = f"cpn_{cname}_{icp*1e6:.0f}_{lab.replace('+', '')}"
                try:
                    d = S4.sim(name, mos, temp, f"model ota ota a=100 vh={vdd} rout=1e7\n" + body,
                               "analysis op1 op\n  analysis n1 noise out=[\"vt\", \"vtx\"] in=\"vtn\" "
                               "from=100 to=100M mode=\"dec\" points=20", "n1.raw")
                except RuntimeError as e:
                    print(f"| {cname} | {icp*1e6:.0f} | {lab} | error: {str(e)[-150:]!r} |")
                    continue
                f = np.real(d["frequency"])
                s = np.real(d["onoise"])
                spec[lab] = (f, s)
                print(f"| {cname} | {icp*1e6:.0f} | {lab} | " + " | ".join(
                    f"{float(np.interp(math.log10(o), np.log10(f), s)):.2e}" for o in OFFS) + " |")
            if len(spec) < 3:
                continue
            f = spec["off"][0]
            avg = (d_up * spec["UP"][1] + d_both * spec["UP+DN"][1] + (1 - d_up - d_both) * spec["off"][1])
            st = avg * (2 * math.pi / icp) ** 2
            white = float(np.median(st[(f >= 1e6) & (f <= 1e7)]))
            fom = 10 * math.log10(white / 2) - 10 * math.log10(F_REF)
            above = np.where((st > 2 * white) & (f < 1e6))[0]
            corner = float(f[above.max()]) if len(above) else 0.0
            res[f"{cname}_{icp*1e6:.0f}"] = dict(fom=fom, fc=corner, f=f.tolist(), s=avg.tolist())
            summary.append((cname, icp, avg, f, fom, corner))
    print("\n| Corner | I_cp (µA) | Average output noise at 100 kHz / 1 MHz (A²/Hz) | FoM (dBc/Hz) | 1/f corner |")
    print("|---|---|---|---|---|")
    for cname, icp, avg, f, fom, corner in summary:
        a = lambda o: float(np.interp(math.log10(o), np.log10(f), avg))   # noqa: E731
        print(f"| {cname} | {icp*1e6:.0f} | {a(1e5):.2e} / {a(1e6):.2e} | {fom:.1f} | {corner/1e3:.0f} kHz |")
    json.dump(res, open(os.path.join(OUT, "cp_noise.json"), "w"))
    print()
    if "contrib" in ARGS:
        cp_contrib(S4, S2)


def cp_contrib(S4, S2):
    """Which devices make the UP-state noise (tt, 50 uA): per-instance contributions of the noise analysis."""
    _, mos, vdd, temp = next(c for c in S2.CORNERS if c[0] == "tt")
    icp = 50e-6
    body = (f"vdd (vdd 0) vsource dc={vdd}\n"
            "rs (vt vtx) resistor r=1 noisy=0\nvtn (vtx 0) vsource dc=0.6\n"
            f"vup (up 0) vsource dc={vdd}\nvdn (dn 0) vsource dc=0\n"
            + S4.use_bias(S2.charge_pump(icp) + S2.offset_sink(icp) + S4.biasgen()))
    body = re.sub(r"(\) resistor r=\S+)(?=\s|$)(?!\s+noisy)", r"\1 noisy=1", body)
    d = S4.sim("cpn_contrib", mos, temp, f"model ota ota a=100 vh={vdd} rout=1e7\n" + body,
               "analysis op1 op\n  save full\n  analysis n1 noise out=[\"vt\", \"vtx\"] in=\"vtn\" "
               "from=100 to=100M mode=\"dec\" points=20", "n1.raw")
    allnames = [x.decode() if isinstance(x, bytes) else x for x in getattr(d, "names", [])]
    names = [k for k in allnames if k.startswith("n(") and "," not in k]
    if not names:
        print("(no per-instance contributions in n1.raw)")
        return
    f = np.real(d["frequency"])
    tot = np.real(d["onoise"])
    groups = {}
    for k in names:
        inst = k[2:-1]
        groups[inst] = groups.get(inst, 0) + np.abs(np.real(d[allnames.index(k)]))
    show = [1e4, 1e5, 6e5, 2e6]
    cols = [int(np.argmin(np.abs(f - x))) for x in show]
    print("## UP-state noise contributions (tt, 50 µA)\n")
    print("| Instance | " + " | ".join(f"{f[c]/1e3:.0f} kHz" for c in cols) + " |")
    print("|---|" + "---|" * len(cols))
    for g in sorted(groups, key=lambda g: -groups[g][cols[2]])[:15]:
        print(f"| {g} | " + " | ".join(f"{100*groups[g][c]/tot[c]:.1f} %" for c in cols) + " |")
    print()


# ------------------------------------------------------------------------------------------------------ lo
def tie_spectrum(t, v, th, f_lo):
    """Rising edges of v through th -> time-interval error -> L(f) of the output (dBc/Hz), offsets."""
    i = np.where((v[:-1] < th) & (v[1:] >= th))[0]
    te = t[i] + (th - v[i]) * (t[i + 1] - t[i]) / (v[i + 1] - v[i])
    te = te[len(te) // 10:]                         # skip the start
    k = np.arange(len(te))
    x = te - np.polyval(np.polyfit(k, te, 1), k)    # TIE (s)
    n = len(x)
    w = np.hanning(n)
    X = np.fft.rfft(x * w)
    fs = f_lo                                       # one sample per output period
    psd = 2 * np.abs(X) ** 2 / (fs * np.sum(w ** 2))   # one-sided, s^2/Hz
    fr = np.fft.rfftfreq(n, 1 / fs)
    L = 10 * np.log10((2 * math.pi * f_lo) ** 2 * psd / 2 + 1e-300)
    return fr[1:], L[1:], float(np.std(x))


def check_lo():
    L3 = load("lo_step3", "analog/lo/step3/run_step3.py")
    L3.OUT = OUT
    tstop = next((float(a[6:].rstrip("u")) * 1e-6 for a in ARGS if a.startswith("tstop=")), 3e-6)
    print("## LO-chain noise floor, transient noise [SCH]\n")
    print(f"Ideal noiseless tank sine (typical VCO swing), {tstop*1e6:g} µs with device and resistor noise "
          "(noisemode zoh, 50 kHz–50 GHz), output edges → time-interval error → L(f) at the LO output. 'Numerical' = "
          "the same run without noise. Band averages of L over 1–3, 3–10 and 10–30 MHz. P2.4 hand estimate: "
          "−157 (UHF) / −161 (VHF) dBc/Hz; target ≤ −150.\n")
    print("| Band | Corner | VCO (GHz) | LO (MHz) | Node | Edges | RMS jitter (fs) | L 1–3 MHz | L 3–10 MHz | "
          "L 10–30 MHz | Numerical floor 3–10 MHz |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    cases = [("uhf", 3.84e9, 0.62), ("vhf", 4.20e9, 0.65)]
    corners = [c for c in L3.CORNERS if c[0] == "tt"] + ([c for c in L3.CORNERS if c[0] == "ss"] if "ss" in ARGS else [])
    res = {}
    for band, f, amp in cases:
        ndiv = 8 if band == "uhf" else 24
        f_lo = f / ndiv
        for corner in corners:
            amp_c = amp if corner[0] == "tt" else L3.tank_amp(f)
            out = {}
            for noisy in (True, False):
                path, names, _, _, _ = L3.build(band, f, corner, tag=f"_tn{int(noisy)}", amp=amp_c)
                node = names[0][1]
                text = open(path).read()
                # First trial (2026-10-25): the noisy transient from t = 0 failed at once (NR / timestep too small)
                # in both bands. Now as in the validated analog/pn-validation level 2: a noiseless warm-up
                # transient, stored, then the noisy transient from that state. Every source must then be the same
                # at the start of the second analysis, so the supply ramps and the D15 enable become DC (the clock
                # is up from t = 0, so the divider still starts with the clock present), the warm-up lasts whole
                # output periods (the tank sine continues in phase), and only the measured node is saved.
                text = re.sub(r'type="pulse" val0=0 val1=(\S+) delay=\S+ rise=\S+ fall=\S+ width=1', r"dc=\1", text)
                if noisy:
                    # device and resistor noise; the 1 GOhm leak resistors on dynamic nodes are simulation aids
                    text = re.sub(r"(\) resistor r=(\S+))(?=\s|$)(?!\s+noisy)",
                                  lambda m: m.group(1) + ("" if m.group(2) == "1G" else " noisy=1"), text)
                warm = round(60e-9 * f_lo) / f_lo
                # Second trial: with DC supplies the VHF operating point failed (homotopy, as at ff / 125 degC in
                # P2.4), and the UHF noisy transient failed again. Now the warm-up starts from the all-zero state
                # (icmode "uic", like a power-on step with the clock already up), and the noisy transient is tried
                # with a falling noise bandwidth (50 / 20 / 10 GHz; the output edges take about 20-30 ps, so
                # 20 GHz still holds most of the noise that moves them).
                base = text
                d, used = None, None
                for nf in (["50G", "20G", "10G"] if noisy else [None]):
                    an = (f"  options strictsave=1\n"
                          f'  analysis warm tran stop={warm:.6e} step=5p maxstep=5p icmode="uic" store="ss"\n'
                          f"  save v({node})\n"
                          f'  analysis tr tran stop={tstop:.4e} step=5p maxstep=5p ic="ss" icmode="uic"'
                          + (f' noisemode="zoh" noisefmax={nf} noisefmin=50k oversample=1' if nf else ""))
                    open(path, "w").write(re.sub(r"  analysis tr tran stop=\S+ step=5p maxstep=5p", an, base))
                    try:
                        d, used = L3.run(path), nf
                        break
                    except RuntimeError as e:
                        err = str(e)
                if d is None:
                    print(f"| {band.upper()} | {corner[0]} | {f/1e9:.2f} | {f_lo/1e6:.0f} | {'noisy' if noisy else 'noiseless'} "
                          f"run failed: {err[-150:]!r} |")
                    break
                t, v = np.real(d["time"]), np.real(d[node])
                out[noisy] = (node,) + tie_spectrum(t, v, corner[2] / 2, f_lo) + (used,)
            if len(out) < 2:
                continue
            node, fr, L, jit, used = out[True]
            _, fr0, L0, _, _ = out[False]
            band_avg = lambda fr_, L_, a, b: 10 * math.log10(np.mean(10 ** (L_[(fr_ >= a) & (fr_ <= b)] / 10)))  # noqa: E731
            vals = [band_avg(fr, L, *r) for r in ((1e6, 3e6), (3e6, 10e6), (10e6, 30e6))]
            res[f"{band}_{corner[0]}"] = dict(f_lo=f_lo, floor=vals[1], fr=fr.tolist(), L=L.tolist())
            print(f"| {band.upper()} | {corner[0]} | {f/1e9:.2f} | {f_lo/1e6:.0f} | {node} (noise to {used}Hz) | {len(fr)*2} | "
                  f"{jit*1e15:.0f} | " + " | ".join(f"{x:.1f}" for x in vals)
                  + f" | {band_avg(fr0, L0, 3e6, 10e6):.1f} |")
    json.dump(res, open(os.path.join(OUT, "lo_noise.json"), "w"))
    print()


# --------------------------------------------------------------------------------------------------- total
VCO_1M = [(3.12e9, -124.4), (3.40e9, -123.4), (3.65e9, -122.7), (3.90e9, -121.5), (4.20e9, -119.9)]  # P2.3 / D20


def check_total():
    pm = load("pll_model", "analog/pll-model/pll_model.py")
    cp = json.load(open(os.path.join(OUT, "cp_noise.json"))) if os.path.exists(os.path.join(OUT, "cp_noise.json")) else {}
    lo = json.load(open(os.path.join(OUT, "lo_noise.json"))) if os.path.exists(os.path.join(OUT, "lo_noise.json")) else {}
    print("## Total phase noise at the duplex offset [MODEL]\n")
    c = cp.get("tt_50") or {}
    fom, fc = c.get("fom", -218.0), c.get("fc", 20e3)
    print(f"Inputs: charge pump FoM {fom:.1f} dBc/Hz, 1/f corner {fc/1e3:.0f} kHz ({'cp, tt, 50 µA' if c else 'P2.2 proposal'}); "
          "VCO L(1 MHz) per band from P2.3 / D20 (typical); LO floor "
          + ((", ".join(f"{k} {v['floor']:.1f}" for k, v in lo.items())
              + ("; UHF: P2.4 hand estimate −157 corrected by the VHF simulation-to-estimate difference"
                 if "uhf_tt" not in lo else "")) if lo else "not yet simulated (P2.4 hand estimate used)")
          + "; loop D19 (60 kHz / 55°); reference TCXO profile and Σ-Δ as P2.2.\n")
    print("| Ref | Band | RF (MHz) | VCO (GHz) | L(1 MHz) VCO | PN at duplex (dBc/Hz, RF) | of which VCO / CP / R / SD | "
          "LO floor | Total with floor | Limit | Margin |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")

    class A:
        pass
    a = A()
    a.kvco, a.icp, a.fc_vco, a.fom_cp, a.fc_cp, a.mash = 40e6, 50e-6, 200e3, fom, fc, 3
    a.ref_profile = [-110, -135, -150, -155, -158, -160]
    for ref in (32e6, 36e6):
        for band, (n_lo, dup, (flo, fhi)) in pm.BANDS.items():
            for frf in (flo, fhi):
                fvco = frf * n_lo
                n_fb = fvco / ref
                a.l1m = float(np.interp(fvco, [x for x, _ in VCO_1M], [y for _, y in VCO_1M]))
                lf = pm.design_loop(60e3, 62.0, a.kvco, a.icp, n_fb)
                pn = pm.noise(np.array([dup]), a, lf, n_fb, ref, n_lo, 3 if band == "VHF" else 2)
                key = f"{band.lower()}_tt"
                hand = -157.0 if band == "UHF" else -161.0
                if key in lo:
                    floor = lo[key]["floor"]
                elif "vhf_tt" in lo:
                    # UHF transient noise does not converge (2026-10-25): the P2.4 hand estimate, corrected by the
                    # amount the VHF simulation came out worse than its own hand estimate
                    floor = hand + (lo["vhf_tt"]["floor"] - (-161.0))
                else:
                    floor = hand
                tot = 10 * math.log10(10 ** (pn["total"][0] / 10) + 10 ** (floor / 10))
                print(f"| {ref/1e6:.0f} | {band} | {frf/1e6:.0f} | {fvco/1e9:.3f} | {a.l1m:.1f} | {pn['total'][0]:.1f} | "
                      f"{pn['vco'][0]:.1f} / {pn['cp'][0]:.1f} / {pn['r'][0]:.1f} / {pn['sd'][0]:.1f} | {floor:.1f} | "
                      f"{tot:.1f} | {pm.LIM_PN_25W:.0f} | {pm.LIM_PN_25W - tot:+.1f} dB |")
    print()


def main():
    os.makedirs(OUT, exist_ok=True)
    modes = [m for m in ("cp", "lo", "total") if m in ARGS] or ["cp", "total"]
    print("# P2.6 step 2 — noise from the circuits\n")
    for m in modes:
        globals()[f"check_{m}"]()


if __name__ == "__main__":
    main()
