#!/usr/bin/env python3
"""Retry worst-corner PN for Q gate with looser PSS / archive code 11."""
from __future__ import annotations

import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(HERE, "out", "q_gate")
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step2"))
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step3"))
import run_step2 as S2  # noqa: E402
import run_step3 as S3  # noqa: E402

S2.OUT = OUT
S3.OUT = OUT

DQ = 0.0363


def main():
    scale = 1.0 / (1.0 - DQ)
    src = os.path.join(REPO, "analog", "vco", "models", "l2n0_lumped.inc")
    text = re.sub(
        r"r=([0-9.eE+-]+)",
        lambda m: f"r={float(m.group(1)) * scale:.6g}",
        open(src).read(),
    )
    scaled = os.path.join(OUT, "l2n0_lumped_qscaled.inc")
    open(scaled, "w").write(text)

    def noisy_inductor():
        t = re.sub(r"(resistor r=[^\s]+)", r"\1 noisy=1", open(scaled).read())
        dst = os.path.join(OUT, "l2n0_lumped_noisy.inc")
        open(dst, "w").write(t)
        return dst

    S2.noisy_inductor = noisy_inductor
    S3.set_corner("mos_ss", "cap_typ")
    S3.load_sizing()

    from vacask.rawfile import rawread
    from compare import fundamental_amplitude

    # archive point from summary_4ma (7-bit era code 11 ≈ 4.20 GHz)
    code, itail, temp, f0 = 11, 3.59e-3, 85, 4.20e9
    vals = ", ".join(f"{x:.0f}" for x in S3.OFFS)
    for opts, npts in (
        ("reltol=1e-6 pss_tolscale=1e-3", 4000),
        ("reltol=1e-5 pss_tolscale=1e-2", 4000),
    ):
        sim = S2.netlist(
            "s3_pn_retry",
            code,
            S2.VTUNE_MID,
            itail=itail,
            analysis=(
                f"  options temp={temp} {opts} pss_minpts={npts}\n"
                '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
                f'  analysis pn pnoise oscillator=1 tper={1 / f0:.6e} tstab=0 '
                f'ic="ss" icmode="uic" maxharm=16 truncharm=8 in="iin" '
                f'out=["tp", "tn"] outharm=1 values=[{vals}] writepss=1'
            ),
            extra="iin (0 tp) isource dc=0\n",
        )
        try:
            print(f"try {opts} npts={npts} ...", flush=True)
            S2.run(sim)
            pss = rawread(os.path.join(OUT, "pn.pss.raw")).get()
            a, fp = fundamental_amplitude(
                pss["time"], np.real(pss["tp"]) - np.real(pss["tn"])
            )
            pn = rawread(os.path.join(OUT, "pn.raw")).get()
            off = np.real(pn["frequency"])
            L = 10 * np.log10(np.real(pn["onoise"]) / (a * a / 2))
            Ld = dict(zip(off, L))
            print(f"OK f={fp / 1e9:.4f} Amp={a:.3f}")
            margins = []
            for band, lim in S3.LIMITS.items():
                lo, hi = (3.12e9, 4.20e9) if band == "VHF" else (3.20e9, 3.84e9)
                if lo - 30e6 <= fp <= hi + 30e6:
                    for o, limv in lim.items():
                        margins.append(
                            (limv - float(Ld[o]), band, o, float(Ld[o]), limv)
                        )
            for marg, band, o, Lv, limv in sorted(margins):
                print(
                    f"  {band} {o / 1e6:g} MHz L={Lv:.1f} lim={limv:.1f} m={marg:+.1f}"
                )
            worst = min(margins)
            print(f"WORST {worst[0]:+.1f} dB -> {'PASS' if worst[0] > 0 else 'FAIL'}")
            open(os.path.join(OUT, "summary_q_gate_pn_retry.txt"), "w").write(
                f"PN retry SCH margin={worst[0]:+.1f} dB opts={opts} npts={npts}\n"
            )
            return 0 if worst[0] > 0 else 1
        except Exception as e:
            print(f"FAIL {opts}: {e}", flush=True)
    open(os.path.join(OUT, "summary_q_gate_pn_retry.txt"), "w").write(
        "PN retry: both attempts failed\n"
    )
    print("ALL RETRIES FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
