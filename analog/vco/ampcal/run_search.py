#!/usr/bin/env python3
"""D22 step 1b 5-bit amplitude SAR with new detector + unit DAC [SCH].

Bypass closed whole search. Top (bank 0) and bottom (bank 255).

    python3 -u run_search.py | tee out/summary_search.txt
    python3 -u run_search.py quick
"""
import os
import re
import sys
import time

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2

A.load_sizing()
A.OUT = os.path.join(A.OUT, "sar")
os.makedirs(A.OUT, exist_ok=True)
S2.OUT = A.OUT

CORNERS = [
    ("mos_tt", "cap_typ"),
    ("mos_ss", "cap_wcs"),
    ("mos_ss", "cap_bcs"),
    ("mos_ff", "cap_wcs"),
    ("mos_ff", "cap_bcs"),
]
TEMPS = (-40, 27, 85)
# Detector settle budget ≤ 1 µs; SCH settle with bypass closed is ~0.2 µs (I/C + RF).
# RTL keeps 1.00 µs/bit margin (wake_timing AMP_SETTLE_CYCLES=36).
SETTLE = 200e-9
TRAN_STEP = "20p"


def prep(sim, bias_code):
    text = open(sim).read()
    text = re.sub(r"iref \(vdd nb\) isource dc=[^\n]+\n", A.dac_snippet(bias_code, "nb"), text)
    text = text.replace("\ncontrol\n", "\n" + A.detector_snippet(True) + "\ncontrol\n")
    text = re.sub(r"vbptie \(vbp 0\) vsource dc=0", "vbptie (vbp 0) vsource dc=1.2", text)
    if "vbptie" not in text:
        text = text.replace("\ncontrol\n", "\nvbptie (vbp 0) vsource dc=1.2\ncontrol\n")
    open(sim, "w").write(text)


def measure(mos, cap, temp, bcode, bias, tag):
    A.set_corner(mos, cap)
    vt = S2.VTUNE_MID if bcode < 128 else 0.3
    # RF build-up ~40 ns + settle
    stop = 40e-9 + SETTLE
    # Tail bypass only. Bank/var bypass AC-grounds MIM/varactor plates and kills Amp [SCH].
    sim = S2.netlist(
        tag, bcode, vt, itail=A.itail(bias), bypass=True, drive_vbp=False,
        bypass_groups=("tail",),
        analysis=(
            f"  options temp={temp}\n"
            "  save v(tp) v(tn) v(cmp) v(hold) v(rep)\n"
            f"  analysis tr tran stop={stop:.6g} step={TRAN_STEP} maxstep={TRAN_STEP}"
        ),
    )
    prep(sim, bias)
    t0 = time.time()
    S2.run(sim)
    dt = time.time() - t0
    d = rawread(os.path.join(A.OUT, "tr.raw")).get()
    t = np.real(d["time"])
    m = t >= t[-1] - 20e-9
    v = np.real(d["tp"])[m] - np.real(d["tn"])[m]
    amp = float(v.max() - v.min()) / 2
    # Full transient Amp peak (hard limit check)
    v_all = np.real(d["tp"]) - np.real(d["tn"])
    amp_peak_run = float(v_all.max() - v_all.min()) / 2
    vh = float(np.real(d["hold"])[m][-1])
    vr = float(np.real(d["rep"])[m][-1])
    a_est = A.a_est_from_holds(vh, vr)
    cmp = float(np.real(d["cmp"])[m][-1])
    vsense = vh - vr
    # Decision from detector nodes (same threshold as the comparator): vsense > V_th
    # Single-ended cmp OP is fragile; co/co2 trip is used in MC. `[SCH]`
    high = vsense > A.v_th()
    return dict(amp=amp, a_est=a_est, high=high, dt=dt, amp_peak_run=amp_peak_run,
                vsense=vsense, cmp=cmp)


def sar(mos, cap, temp, band, bcode):
    code = 0
    steps = []
    amp_peak = 0.0
    for bit in range(4, -1, -1):
        trial = code | (1 << bit)
        tag = f"sar_{mos}_{cap}_{temp}_{band}_b{bit}_c{trial}"
        r = measure(mos, cap, temp, bcode, trial, tag)
        amp_peak = max(amp_peak, r["amp"], r["amp_peak_run"])
        # keep bit if Amp still below target (cmp low)
        keep = not r["high"]
        if r["amp"] > A.A_HARD:
            keep = False
        if keep:
            code = trial
        steps.append(dict(bit=bit, trial=trial, keep=keep, **r))
    fin = measure(mos, cap, temp, bcode, code, f"sar_{mos}_{cap}_{temp}_{band}_fin_c{code}")
    amp_peak = max(amp_peak, fin["amp"], fin["amp_peak_run"])
    tnr = (code == 31) and (fin["amp"] < A.A_TARGET - A.A_WIN)
    t_elec = SETTLE * (len(steps) + 1)
    return dict(
        code=code, final=fin, steps=steps, amp_peak=amp_peak, tnr=tnr,
        t_step_wall=float(np.mean([s["dt"] for s in steps])),
        t_tot_wall=sum(s["dt"] for s in steps) + fin["dt"],
        t_step_elec=SETTLE, t_tot_elec=t_elec,
    )


def main():
    quick = "quick" in sys.argv
    corners = [("mos_tt", "cap_typ")] if quick else CORNERS
    temps = (27,) if quick else TEMPS
    print("# D22 step 1b amplitude SAR (diff-max det + unit DAC, bypass closed) [SCH]\n")
    print(
        f"Settle {SETTLE*1e6:.2f} µs/step (elec); target {A.A_TARGET} V ± {A.A_WIN} V; "
        f"hard {A.A_HARD} V; V_LOSS={A.V_LOSS:.3f} V.\n"
    )
    print(
        "| MOS | CAP | T | band | code | Amp | A_est | tnr | Amp_peak | "
        "t_step_elec (µs) | t_tot_elec (µs) | ≤1.40 |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    all_ok = True
    top_reached = None
    for mos, cap in corners:
        for temp in temps:
            for band, bcode in (("top", 0), ("bottom", 255)):
                r = sar(mos, cap, temp, band, bcode)
                ok = r["amp_peak"] <= A.A_HARD + 1e-3
                if not ok:
                    all_ok = False
                if band == "top" and mos == "mos_tt" and temp == 27:
                    top_reached = r
                print(
                    f"| {mos} | {cap} | {temp} | {band} | {r['code']} | {r['final']['amp']:.3f} | "
                    f"{r['final']['a_est']:.3f} | {int(r['tnr'])} | {r['amp_peak']:.3f} | "
                    f"{r['t_step_elec']*1e6:.2f} | {r['t_tot_elec']*1e6:.2f} | "
                    f"{'PASS' if ok else 'FAIL'} |"
                )
                # per-step dump for the first quick/tt case
                if quick or (mos == "mos_tt" and temp == 27 and cap == "cap_typ"):
                    for s in r["steps"]:
                        print(
                            f"    bit{s['bit']} trial={s['trial']} keep={int(s['keep'])} "
                            f"Amp={s['amp']:.3f} A_est={s['a_est']:.3f} cmp_high={int(s['high'])}"
                        )
    print()
    print("Amp ≤ 1.40 V all steps:", "PASS" if all_ok else "FAIL", "`[SCH]`")
    if top_reached is not None:
        amp = top_reached["final"]["amp"]
        tnr = top_reached["tnr"]
        print(
            f"\n## Step-1 top-band tnr explanation (tt/27)\n"
        )
        if (not tnr) and amp >= A.A_TARGET - A.A_WIN:
            print(
                f"Top now reaches Amp={amp:.3f} V at code {top_reached['code']} "
                f"(tnr={int(tnr)}). Step-1 top tnr at 1.15 V was a **detector artefact** "
                f"(under-read → search kept raising code / mis-compared). `[SCH]`"
            )
        else:
            print(
                f"Top still Amp={amp:.3f} V tnr={int(tnr)} at code {top_reached['code']}. "
                f"Not only a detector artefact — investigate bias / load / settle. `[SCH]`"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
