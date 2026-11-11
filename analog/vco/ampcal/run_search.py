#!/usr/bin/env python3
"""D22 step 1d: amplitude SAR on the real single-ended comparator [SCH].

Detector → SE cmp → digital SAR → V_DS-matched DAC → VCO; tail-only bypass.
Decision: cmp > CMP_HIGH (not vsense > V_th). Steady ≤ 1.40 V; transient ≤ 1.50 V.

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
SETTLE = 200e-9
TRAN_STEP = "20p"

# Step 1c final codes (vsense path) for comparison — summary_search.txt 1c [SCH]
STEP1C = {
    ("mos_tt", "cap_typ", -40, "top"): 11,
    ("mos_tt", "cap_typ", -40, "bottom"): 31,
    ("mos_tt", "cap_typ", 27, "top"): 14,
    ("mos_tt", "cap_typ", 27, "bottom"): 31,
    ("mos_tt", "cap_typ", 85, "top"): 16,
    ("mos_tt", "cap_typ", 85, "bottom"): 31,
    ("mos_ss", "cap_wcs", -40, "top"): 11,
    ("mos_ss", "cap_wcs", -40, "bottom"): 31,
    ("mos_ss", "cap_wcs", 27, "top"): 13,
    ("mos_ss", "cap_wcs", 27, "bottom"): 31,
    ("mos_ss", "cap_wcs", 85, "top"): 16,
    ("mos_ss", "cap_wcs", 85, "bottom"): 31,
    ("mos_ss", "cap_bcs", -40, "top"): 9,
    ("mos_ss", "cap_bcs", -40, "bottom"): 31,
    ("mos_ss", "cap_bcs", 27, "top"): 11,
    ("mos_ss", "cap_bcs", 27, "bottom"): 31,
    ("mos_ss", "cap_bcs", 85, "top"): 13,
    ("mos_ss", "cap_bcs", 85, "bottom"): 31,
    ("mos_ff", "cap_wcs", -40, "top"): 14,
    ("mos_ff", "cap_wcs", -40, "bottom"): 31,
    ("mos_ff", "cap_wcs", 27, "top"): 16,
    ("mos_ff", "cap_wcs", 27, "bottom"): 31,
    ("mos_ff", "cap_wcs", 85, "top"): 19,
    ("mos_ff", "cap_wcs", 85, "bottom"): 31,
    ("mos_ff", "cap_bcs", -40, "top"): 12,
    ("mos_ff", "cap_bcs", -40, "bottom"): 31,
    ("mos_ff", "cap_bcs", 27, "top"): 14,
    ("mos_ff", "cap_bcs", 27, "bottom"): 31,
    ("mos_ff", "cap_bcs", 85, "top"): 17,
    ("mos_ff", "cap_bcs", 85, "bottom"): 31,
}


def prep(sim, bias_code):
    """Inject V_DS-matched DAC + detector/cmp; close tail-only bypass."""
    A.inject_dac_det(sim, bias_code, det=True)
    text = open(sim).read()
    text = re.sub(
        r"vbptailtie \(vbp_tail 0\) vsource dc=0",
        "vbptailtie (vbp_tail 0) vsource dc=1.2",
        text,
    )
    if "vbptailtie" not in text:
        text = text.replace(
            "\ncontrol\n", "\nvbptailtie (vbp_tail 0) vsource dc=1.2\ncontrol\n"
        )
    open(sim, "w").write(text)


def measure(mos, cap, temp, bcode, bias, tag):
    A.set_corner(mos, cap)
    vt = S2.VTUNE_MID if bcode < 128 else 0.3
    stop = 40e-9 + SETTLE
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
    v_all = np.real(d["tp"]) - np.real(d["tn"])
    amp_peak_run = float(v_all.max() - v_all.min()) / 2
    vh = float(np.real(d["hold"])[m][-1])
    vr = float(np.real(d["rep"])[m][-1])
    a_est = A.a_est_from_holds(vh, vr)
    cmpv = float(np.real(d["cmp"])[m][-1])
    vsense = vh - vr
    # Step 1d: digital search reads the single-ended comparator [SCH]
    high = cmpv > A.CMP_HIGH
    high_vsense = vsense > A.v_th()  # 1c path, for disagreement log
    return dict(
        amp=amp, a_est=a_est, high=high, high_vsense=high_vsense, dt=dt,
        amp_peak_run=amp_peak_run, vsense=vsense, cmp=cmpv,
    )


def sar(mos, cap, temp, band, bcode):
    code = 0
    steps = []
    amp_peak = 0.0
    for bit in range(4, -1, -1):
        trial = code | (1 << bit)
        tag = f"sar_{mos}_{cap}_{temp}_{band}_b{bit}_c{trial}"
        r = measure(mos, cap, temp, bcode, trial, tag)
        amp_peak = max(amp_peak, r["amp"], r["amp_peak_run"])
        # Keep bit if Amp still below target (cmp low)
        keep = not r["high"]
        if keep:
            code = trial
        steps.append(dict(bit=bit, trial=trial, keep=keep, **r))
    fin = measure(mos, cap, temp, bcode, code, f"sar_{mos}_{cap}_{temp}_{band}_fin_c{code}")
    amp_peak = max(amp_peak, fin["amp"], fin["amp_peak_run"])
    tnr = (code == 31) and (not fin["high"])
    t_elec = SETTLE * (len(steps) + 1)
    return dict(
        code=code, final=fin, steps=steps, amp_peak=amp_peak, tnr=tnr,
        amp_steady=fin["amp"],
        t_step_wall=float(np.mean([s["dt"] for s in steps])),
        t_tot_wall=sum(s["dt"] for s in steps) + fin["dt"],
        t_step_elec=SETTLE, t_tot_elec=t_elec,
    )


def main():
    quick = "quick" in sys.argv
    corners = [("mos_tt", "cap_typ")] if quick else CORNERS
    temps = (27,) if quick else TEMPS
    print("# D22 step 1d amplitude SAR on single-ended cmp [SCH]\n")
    print(
        f"Decision: v(cmp) > {A.CMP_HIGH:.2f} V; settle {SETTLE*1e6:.2f} µs/step; "
        f"target {A.A_TARGET}±{A.A_WIN} V; steady ≤{A.A_HARD} V; "
        f"transient ≤{A.A_HARD_TRANSIENT} V.\n"
    )
    print(
        "| MOS | CAP | T | band | code | Amp | A_est | tnr | Amp_peak | "
        "code_1c | Δcode | t_tot (µs) | steady≤1.40 | peak≤1.50 |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    all_ok = True
    code_changes = []
    for mos, cap in corners:
        for temp in temps:
            for band, bcode in (("top", 0), ("bottom", 255)):
                r = sar(mos, cap, temp, band, bcode)
                ok_s = r["amp_steady"] <= A.A_HARD + 1e-3
                ok_p = r["amp_peak"] <= A.A_HARD_TRANSIENT + 1e-3
                # Top band also wants final Amp inside window when tnr=0
                if band == "top" and not r["tnr"]:
                    if not (A.A_TARGET - A.A_WIN - 1e-3 <= r["amp_steady"] <= A.A_HARD + 1e-3):
                        # still gate on hard limits primarily; window is soft report
                        pass
                ok = ok_s and ok_p
                if not ok:
                    all_ok = False
                c1c = STEP1C.get((mos, cap, temp, band))
                dcode = (r["code"] - c1c) if c1c is not None else None
                if dcode not in (None, 0):
                    # explain from last disagreeing step if any
                    disagree = [
                        s for s in r["steps"]
                        if s["high"] != s["high_vsense"]
                    ]
                    reason = (
                        f"cmp/vsense disagree on {len(disagree)} bit(s)"
                        if disagree else "cmp trip near threshold / offset"
                    )
                    code_changes.append(
                        (mos, cap, temp, band, c1c, r["code"], reason, r)
                    )
                print(
                    f"| {mos} | {cap} | {temp} | {band} | {r['code']} | "
                    f"{r['final']['amp']:.3f} | {r['final']['a_est']:.3f} | "
                    f"{int(r['tnr'])} | {r['amp_peak']:.3f} | "
                    f"{c1c if c1c is not None else '-'} | "
                    f"{dcode if dcode is not None else '-'} | "
                    f"{r['t_tot_elec']*1e6:.2f} | "
                    f"{'PASS' if ok_s else 'FAIL'} | "
                    f"{'PASS' if ok_p else 'FAIL'} |"
                )
                if quick or (mos == "mos_tt" and temp == 27 and cap == "cap_typ"):
                    for s in r["steps"]:
                        print(
                            f"    bit{s['bit']} trial={s['trial']} keep={int(s['keep'])} "
                            f"Amp={s['amp']:.3f} cmp={s['cmp']:.3f} "
                            f"cmp_high={int(s['high'])} vsense_high={int(s['high_vsense'])}"
                        )
    print()
    print(
        f"Steady ≤ {A.A_HARD} V and peak ≤ {A.A_HARD_TRANSIENT} V all cases:",
        "PASS" if all_ok else "FAIL",
        "`[SCH]`",
    )
    if code_changes:
        print("\n## Code changes vs step 1c [SCH]\n")
        for mos, cap, temp, band, c1c, c1d, reason, r in code_changes:
            print(
                f"- {mos}/{cap}/{temp}/{band}: {c1c} → {c1d} ({reason}); "
                f"final Amp={r['final']['amp']:.3f} V, cmp={r['final']['cmp']:.3f} V"
            )
    else:
        print("\nNo code changes vs step 1c. `[SCH]`")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
