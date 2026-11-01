#!/usr/bin/env python3
"""VCO phase noise via validated transient-noise method (pn-validation compare.py).

Used when PSS/pnoise does not converge with start-up bypass MOS present. Default cases:
  tt 3.65 GHz and worst (ss / cap_typ / 85 C) 4.20 GHz — current schematic (bypass=True).

    python3 -u run_tran_pn.py | tee out/summary_tran_pn.txt
    python3 -u run_tran_pn.py tt worst
    python3 -u run_tran_pn.py tstop=10u
"""
import math
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import run_step3 as s3

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "analog", "pn-validation"))
from compare import tran_fit_at_1mhz, tran_phase_noise_dbc  # noqa: E402

s3.OUT = os.path.join(HERE, "out")
OFFS = s3.OFFS
LIMITS = s3.LIMITS
ARGS = sys.argv[1:]
TSTOP = next((float(a[6:].rstrip("u")) * 1e-6 for a in ARGS if a.startswith("tstop=")), 10e-6)
WARM = 80e-9
NOISEFMAX = ["50G", "20G", "10G", "5G"]


def run_case(tag, mos, cap, temp, f0, bypass=True):
    s3.set_corner(mos, cap)
    r, meas = s3.load_sizing()
    code = s3.code_for(f0, temp, f"{tag}_c")
    itail = s3.itail_for(f0, meas)
    print(f"  {tag}: code {code}, I_tail {itail*1e3:.2f} mA, target {f0/1e9:.2f} GHz @ {temp} C, "
          f"bypass={'on' if bypass else 'off'}")

    last_err = None
    used_nf = None
    for nf in NOISEFMAX:
        analysis = (
            f"  options temp={temp} reltol=1e-6 strictsave=1\n"
            f'  analysis warm tran stop={WARM:.4e} step=5p maxstep=5p icmode="uic" store="ss"\n'
            f"  save v(tp) v(tn)\n"
            f'  analysis tn tran stop={TSTOP:.4e} step=5p maxstep=5p ic="ss" icmode="uic" '
            f'noisemode="zoh" noisefmax={nf} noisefmin=50k oversample=1'
        )
        sim = s3.S2.netlist(
            f"s3_tn_{tag}", code, s3.S2.VTUNE_MID, itail=itail, analysis=analysis, bypass=bypass,
        )
        try:
            s3.S2.run(sim)
            used_nf = nf
            break
        except RuntimeError as e:
            last_err = e
            print(f"  fail nf={nf}: {[x for x in str(e).splitlines() if x.strip()][-2:]}")
    else:
        print(f"  transient failed all noisefmax: "
              f"{[x for x in str(last_err).splitlines() if x.strip()][-2:]}")
        return None

    raw = rawread(os.path.join(s3.OUT, "tn.raw")).get()
    t = np.real(raw["time"])
    v = np.real(raw["tp"]) - np.real(raw["tn"])
    settle = min(1.0e-6, 0.1 * (t[-1] - t[0]))
    L1m, res = tran_fit_at_1mhz(t, v, settle=settle)
    Loffs, _ = tran_phase_noise_dbc(t, v, list(OFFS), settle=settle)
    late = v[t >= t[-1] - 20e-9]
    amp = 0.5 * (np.max(late) - np.min(late)) if len(late) else float("nan")
    zc = np.where(np.diff(np.signbit(late - np.mean(late))))[0]
    if len(zc) > 4:
        dt = np.median(np.diff(t[t >= t[-1] - 20e-9][zc])) * 2
        fp = 1.0 / dt if dt > 0 else float("nan")
    else:
        fp = float("nan")
    row = dict(tag=tag, code=code, itail=itail, f=fp, amp=amp, L1m=float(L1m),
               L={float(o): float(x) for o, x in zip(OFFS, Loffs)}, res=float(res),
               noisefmax=used_nf, bypass=bypass)
    print(f"  -> nf={used_nf} f≈{fp/1e9:.3f} GHz amp≈{amp:.3f} V  L(1 MHz fit)={L1m:.1f} dBc/Hz  "
          f"bin≈{res/1e3:.0f} kHz")
    return row


def margin(row):
    if row is None:
        return None
    margins = []
    for band, lim in LIMITS.items():
        lo, hi = (3.12e9, 4.20e9) if band == "VHF" else (3.20e9, 3.84e9)
        f = row["f"] if not math.isnan(row["f"]) else None
        if f is None:
            continue
        if lo - 30e6 <= f <= hi + 30e6:
            for o, lim_o in lim.items():
                if o in row["L"] and not math.isnan(row["L"][o]):
                    margins.append((lim_o - row["L"][o], band, o))
    return min(margins) if margins else None


def main():
    want = [a for a in ARGS if a in ("tt", "worst")] or ["tt", "worst"]
    print("# VCO transient-noise phase noise (pn-validation method)\n")
    print(f"Noiseless warm-up {WARM*1e9:.0f} ns, noisy ZOH {TSTOP*1e6:g} us, "
          f"noisefmax stepped {'/'.join(NOISEFMAX)}. Bypass MOS present (current schematic).\n")
    cases = []
    if "tt" in want:
        cases.append(("tt_3.65", "mos_tt", "cap_typ", 27, 3.65e9))
    if "worst" in want:
        cases.append(("ss85_4.20", "mos_ss", "cap_typ", 85, 4.20e9))

    rows = []
    for c in cases:
        row = run_case(*c, bypass=True)
        if row is None:
            print("  retry without bypass MOS (diagnostic only)…")
            row = run_case(*c, bypass=False)
            if row is not None:
                row["tag"] = row["tag"] + "_nobypass"
        rows.append(row)

    print("\n| Case | f (GHz) | Code | I_tail (mA) | Amp (V) | nf | L@1 MHz (fit) | "
          + " | ".join(f"L@{o/1e6:g}" for o in OFFS) + " | Worst margin |")
    print("|---|---|---|---|---|---|---|" + "---|" * len(OFFS) + "---|")
    for c, row in zip(cases, rows):
        if row is None:
            print(f"| {c[0]} | — | — | — | transient failed |")
            continue
        w = margin(row)
        ws = f"{w[0]:+.1f} dB ({w[1]} {w[2]/1e6:g} MHz)" if w else "—"
        print(f"| {row['tag']} | {row['f']/1e9:.3f} | {row['code']} | {row['itail']*1e3:.2f} | "
              f"{row['amp']:.3f} | {row['noisefmax']} | {row['L1m']:.1f} | "
              + " | ".join(f"{row['L'][o]:.1f}" for o in OFFS) + f" | {ws} |")
    print()


if __name__ == "__main__":
    main()
