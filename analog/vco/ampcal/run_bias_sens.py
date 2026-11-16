#!/usr/bin/env python3
"""D22 fab bias sensitivity [SCH]: calibrated Amp vs I_hold and hold/rep ratio.

tt / 27 °C / top band only. Uses ideal isources for sinks so current is exact;
cmp loads stay rhigh + cmim (fab). Replica scales with hold in (a).

    python3 -u run_bias_sens.py | tee out/summary_bias_sens.txt
"""
from __future__ import annotations

import os
import sys

import numpy as np

import amp_common as A
import run_step2 as S2
import run_search as RS

A.load_sizing()
A.OUT = os.path.join(A.OUT, "bias_sens")
os.makedirs(A.OUT, exist_ok=True)
S2.OUT = A.OUT


def det_ideal_i(i_hold, i_rep, i_tt=20e-6, i_ss=20e-6):
    """Fab cmim/rhigh/cmp with ideal sink currents [SCH sensitivity]."""
    th = A.v_th()
    return "".join([
        f"// sens I_hold={i_hold*1e6:.2f}u I_rep={i_rep*1e6:.2f}u "
        f"I_tt={i_tt*1e6:.1f}u V_LOSS={th:.3f}\n",
        f"mdtp (vdd tp hold 0) sg13_lv_nmos w={A.W_DET} l={A.L_DET} ng=1\n",
        f"mdtn (vdd tn hold 0) sg13_lv_nmos w={A.W_DET} l={A.L_DET} ng=1\n",
        f"mrtp (vdd ct rep 0) sg13_lv_nmos w={A.W_DET} l={A.L_DET} ng=1\n",
        f"mrtn (vdd ct rep 0) sg13_lv_nmos w={A.W_DET} l={A.L_DET} ng=1\n",
        f"chold (hold 0) cap_cmim w={A.CMIM_HOLD_W} l={A.CMIM_HOLD_W}\n",
        f"crep (rep 0) cap_cmim w={A.CMIM_HOLD_W} l={A.CMIM_HOLD_W}\n",
        f"idet (hold 0) isource dc={i_hold:.6g}\n",
        f"irep (rep 0) isource dc={i_rep:.6g}\n",
        f"vth (vthn rep) vsource dc={th:.6g}\n",
        "mc1 (co hold ttail 0) sg13_lv_nmos w=4u l=0.5u ng=2\n",
        "mc2 (co2 vthn ttail 0) sg13_lv_nmos w=4u l=0.5u ng=2\n",
        f"itt (ttail 0) isource dc={i_tt:.6g}\n",
        f"rc1 (vdd co 0) rhigh w=0.5u l={A.RHIGH_CMP_L} b=0\n",
        f"rc2 (vdd co2 0) rhigh w=0.5u l={A.RHIGH_CMP_L} b=0\n",
        "mcs1 (n1 co2 ss2 0) sg13_lv_nmos w=4u l=0.5u ng=2\n",
        "mcs2 (cmp co ss2 0) sg13_lv_nmos w=4u l=0.5u ng=2\n",
        f"iss2 (ss2 0) isource dc={i_ss:.6g}\n",
        "mpl1 (n1 n1 vdd vdd) sg13_lv_pmos w=4u l=0.5u ng=2\n",
        "mpl2 (cmp n1 vdd vdd) sg13_lv_pmos w=4u l=0.5u ng=2\n",
        f"cl_cmp (cmp 0) cap_cmim w={A.CMIM_CMP_W} l={A.CMIM_CMP_W}\n",
    ])


_orig_snippet = A.detector_snippet


def sar_with(i_hold, i_rep, tag):
    def snip(en=True):
        if not en:
            return det_ideal_i(1e-12, 1e-12)
        return det_ideal_i(i_hold, i_rep)

    A.detector_snippet = snip
    try:
        return RS.sar("mos_tt", "cap_typ", 27, "top", 0)
    finally:
        A.detector_snippet = _orig_snippet


def main():
    print("# D22 bias sensitivity — tt/27 top [SCH]\n")
    print("Ideal reference: code 14, Amp 1.250 V; window 1.25±0.10.\n")

    print("## (a) Absolute I_hold (= I_rep), I_tt=I_ss=20 µA\n")
    print("| I_hold (µA) | code | Amp | A_est | peak | in_window |")
    print("|---|---|---|---|---|---|")
    rows_a = []
    for ih_u in (2, 4, 6, 8, 12, 16):
        ih = ih_u * 1e-6
        r = sar_with(ih, ih, f"a_{ih_u}")
        ok = abs(r["amp_steady"] - A.A_TARGET) <= A.A_WIN + 1e-3
        rows_a.append((ih_u, r))
        print(
            f"| {ih_u} | {r['code']} | {r['amp_steady']:.3f} | "
            f"{r['final']['a_est']:.3f} | {r['amp_peak']:.3f} | "
            f"{'YES' if ok else 'NO'} |"
        )
        sys.stdout.flush()

    print("\n## (b) I_hold/I_rep ratio at I_hold=4 µA (I_tt=20 µA)\n")
    print("| ratio | I_rep (µA) | code | Amp | A_est | peak | in_window |")
    print("|---|---|---|---|---|---|---|")
    rows_b = []
    for ratio in (0.80, 0.90, 1.00, 1.10, 1.20):
        ih = 4e-6
        ir = ih / ratio  # ratio = I_hold/I_rep
        r = sar_with(ih, ir, f"b_{ratio:.2f}")
        ok = abs(r["amp_steady"] - A.A_TARGET) <= A.A_WIN + 1e-3
        rows_b.append((ratio, ir * 1e6, r))
        print(
            f"| {ratio:.2f} | {ir*1e6:.2f} | {r['code']} | {r['amp_steady']:.3f} | "
            f"{r['final']['a_est']:.3f} | {r['amp_peak']:.3f} | "
            f"{'YES' if ok else 'NO'} |"
        )
        sys.stdout.flush()

    # Which sets the amplitude error?
    amps_a = [r["amp_steady"] for _, r in rows_a]
    amps_b = [r["amp_steady"] for _, _, r in rows_b]
    span_a = max(amps_a) - min(amps_a)
    span_b = max(amps_b) - min(amps_b)
    print("\n## Conclusion [SCH]\n")
    print(f"- Amp span over (a) I_hold 2–16 µA: {span_a:.3f} V")
    print(f"- Amp span over (b) ratio ±20 % at 4 µA: {span_b:.3f} V")
    if span_a >= span_b:
        print(
            "- **Absolute hold-sink current** sets the calibrated amplitude error "
            f"(span {span_a:.3f} V ≫ ratio span {span_b:.3f} V)."
        )
    else:
        print(
            "- **Hold/replica current ratio** sets the calibrated amplitude error "
            f"(span {span_b:.3f} V ≫ abs span {span_a:.3f} V)."
        )
    # nearest to target in (a)
    best = min(rows_a, key=lambda x: abs(x[1]["amp_steady"] - A.A_TARGET))
    print(
        f"- Closest in (a): I_hold={best[0]} µA → code {best[1]['code']}, "
        f"Amp={best[1]['amp_steady']:.3f} V"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
