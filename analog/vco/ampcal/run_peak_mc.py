#!/usr/bin/env python3
"""Transient peak Monte Carlo at the worst-peak corner [SCH].

Corner: mos_ss / cap_bcs / 85 °C / top — nominal Amp_peak = 1.493 V [SCH
summary_search_fab_retune.txt]. Inject comparator input-pair Vos (same σ as
run_cmp_mc), re-run the SAR, report peak mean / 3σ / peak+3σ vs ≤ 1.50 V.

    python3 -u run_peak_mc.py | tee out/summary_peak_mc.txt
    python3 -u run_peak_mc.py quick
"""
from __future__ import annotations

import os
import re
import sys

import numpy as np

import amp_common as A
import run_search as RS

A.load_sizing()
N = 20
W, L = 4.0, 0.5
SIG = A.SIG_VT_N / (W * L) ** 0.5
MOS, CAP, TEMP, BAND, BCODE = "mos_ss", "cap_bcs", 85, "top", 0


def inject_vos(sim: str, vos: tuple[float, float]) -> None:
    """Series Vos on cmp input gates (hold / vthn), matching run_cmp_mc."""
    text = open(sim).read()
    # Detector snippet uses: mc1 (co hold ttail 0) / mc2 (co2 vthn ttail 0)
    # Use cmp_g* — bank switches already own g0..g11 in the VCO netlist.
    text2, n1 = re.subn(
        r"mc1 \(co hold ttail 0\)",
        "mc1 (co cmp_g1 ttail 0)",
        text,
        count=1,
    )
    text2, n2 = re.subn(
        r"mc2 \(co2 vthn ttail 0\)",
        "mc2 (co2 cmp_g2 ttail 0)",
        text2,
        count=1,
    )
    if n1 != 1 or n2 != 1:
        raise RuntimeError(f"mc1/mc2 rewrite failed n1={n1} n2={n2}")
    vos_src = (
        f"vo1 (cmp_g1 hold) vsource dc={vos[0]:.6g}\n"
        f"vo2 (cmp_g2 vthn) vsource dc={vos[1]:.6g}\n"
    )
    if "\ncontrol\n" not in text2:
        raise RuntimeError("no control block")
    text2 = text2.replace("\ncontrol\n", f"\n{vos_src}control\n", 1)
    open(sim, "w").write(text2)


_orig_prep = RS.prep


def prep_vos(sim, bias_code, vos=(0.0, 0.0)):
    _orig_prep(sim, bias_code)
    inject_vos(sim, vos)


def measure_vos(mos, cap, temp, bcode, bias, tag, vos):
    A.set_corner(mos, cap)
    vt = RS.S2.VTUNE_MID if bcode < 128 else 0.3
    stop = 40e-9 + RS.SETTLE
    sim = RS.S2.netlist(
        tag, bcode, vt, itail=A.itail(bias), bypass=True, drive_vbp=False,
        bypass_groups=("tail",),
        analysis=(
            f"  options temp={temp}\n"
            "  save v(tp) v(tn) v(cmp) v(hold) v(rep)\n"
            f"  analysis tr tran stop={stop:.6g} step={RS.TRAN_STEP} "
            f"maxstep={RS.TRAN_STEP}"
        ),
    )
    prep_vos(sim, bias, vos)
    import time
    from vacask.rawfile import rawread

    t0 = time.time()
    RS.S2.run(sim)
    dt = time.time() - t0
    d = rawread(os.path.join(RS.A.OUT, "tr.raw")).get()
    t = np.real(d["time"])
    m = t >= t[-1] - 20e-9
    v = np.real(d["tp"])[m] - np.real(d["tn"])[m]
    amp = float(v.max() - v.min()) / 2
    v_all = np.real(d["tp"]) - np.real(d["tn"])
    amp_peak_run = float(v_all.max() - v_all.min()) / 2
    vh = float(np.real(d["hold"])[m][-1])
    vr = float(np.real(d["rep"])[m][-1])
    cmpv = float(np.real(d["cmp"])[m][-1])
    high = cmpv > A.CMP_HIGH
    return dict(
        amp=amp, amp_peak_run=amp_peak_run, high=high, cmp=cmpv, dt=dt,
        vsense=vh - vr,
    )


def sar_vos(vos, tag_prefix):
    code = 0
    amp_peak = 0.0
    peak_step = None
    steps = []
    for bit in range(4, -1, -1):
        trial = code | (1 << bit)
        tag = f"{tag_prefix}_b{bit}_c{trial}"
        r = measure_vos(MOS, CAP, TEMP, BCODE, trial, tag, vos)
        for key in ("amp", "amp_peak_run"):
            if r[key] >= amp_peak:
                amp_peak = r[key]
                peak_step = dict(bit=bit, trial=trial, kind=key, val=r[key])
        keep = not r["high"]
        if keep:
            code = trial
        steps.append(dict(bit=bit, trial=trial, keep=keep, **r))
    fin = measure_vos(
        MOS, CAP, TEMP, BCODE, code, f"{tag_prefix}_fin_c{code}", vos)
    for key in ("amp", "amp_peak_run"):
        if fin[key] >= amp_peak:
            amp_peak = fin[key]
            peak_step = dict(bit=-1, trial=code, kind=key, val=fin[key])
    return dict(
        code=code, amp_peak=amp_peak, peak_step=peak_step,
        amp_steady=fin["amp"], steps=steps, final=fin,
    )


def main():
    quick = "quick" in sys.argv
    n = 5 if quick else N
    print("# D22 transient peak MC at worst-peak corner [SCH]\n")
    print(
        f"Corner: {MOS}/{CAP}/{TEMP}°C/{BAND}; "
        f"σ_VT={SIG*1e3:.2f} mV; N={n}; limit ≤ {A.A_HARD_TRANSIENT:.2f} V\n"
    )
    # Nominal (vos=0) sanity
    nom = sar_vos((0.0, 0.0), "peak_nom")
    print(
        f"Nominal vos=0: code={nom['code']} Amp={nom['amp_steady']:.3f} "
        f"peak={nom['amp_peak']:.3f} at bit={nom['peak_step']['bit']} "
        f"trial={nom['peak_step']['trial']} ({nom['peak_step']['kind']}) `[SCH]`"
    )

    rng = np.random.default_rng(7)
    peaks = []
    over = []
    for i in range(n):
        vos = (float(rng.normal(0, SIG)), float(rng.normal(0, SIG)))
        r = sar_vos(vos, f"peak_mc{i}")
        peaks.append(r["amp_peak"])
        mark = ""
        if r["amp_peak"] > A.A_HARD_TRANSIENT + 1e-3:
            over.append(dict(i=i, **r, vos=vos))
            mark = " OVER"
        print(
            f"  [{i}] vos=({vos[0]*1e3:+.2f},{vos[1]*1e3:+.2f}) mV "
            f"code={r['code']} Amp={r['amp_steady']:.3f} "
            f"peak={r['amp_peak']:.3f} "
            f"@bit{r['peak_step']['bit']}/c{r['peak_step']['trial']}{mark}",
            flush=True,
        )

    arr = np.array(peaks, dtype=float)
    mean = float(np.mean(arr))
    sig = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    p3 = 3.0 * sig
    hi = mean + p3
    print()
    print(f"peak mean = {mean:.4f} V `[SCH]`")
    print(f"peak σ = {sig*1e3:.2f} mV; 3σ = {p3*1e3:.2f} mV `[SCH]`")
    print(f"peak + 3σ = {hi:.4f} V  (limit {A.A_HARD_TRANSIENT:.2f} V) `[SCH]`")
    if hi <= A.A_HARD_TRANSIENT + 1e-4:
        print(f"vs ≤1.50 V: PASS (margin {(A.A_HARD_TRANSIENT - hi)*1e3:.1f} mV)")
    else:
        print(
            f"vs ≤1.50 V: OVER by {(hi - A.A_HARD_TRANSIENT)*1e3:.1f} mV "
            f"— finding for owner (process abs 1.65 V); design unchanged"
        )
    if over:
        print(f"\nSamples with peak > 1.50 V: {len(over)}/{n}")
        for o in over[:5]:
            ps = o["peak_step"]
            print(
                f"  i={o['i']} peak={o['amp_peak']:.3f} "
                f"@ bit={ps['bit']} trial={ps['trial']}"
            )
    print(f"\nObserved peak min/max = {arr.min():.3f} / {arr.max():.3f} V `[SCH]`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
