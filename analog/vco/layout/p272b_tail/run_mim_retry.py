#!/usr/bin/env python3
"""Retry rfcmim-only pnoise with relaxed PSS; compare to saved ideal [SCH]."""
from __future__ import annotations

import os
import sys

import numpy as np
from vacask.rawfile import rawread

import run_d9_mos_vs_mim as R
import run_step2 as S2
import run_step3 as S3
from compare import fundamental_amplitude

S2.OUT = R.OUT
S3.OUT = R.OUT
PASS_DB = 0.1
PASS_SWING = 0.02
# From summary_mim_vs_ideal (ideal 8000-pt success)
IDEAL = dict(f=3.649e9, amp=1.201, L={1e5: -92.22, 1e6: -122.18})


def pnoise_mim_relaxed(code, vt, f0, itail, temp):
    vals = ", ".join(f"{x:.0f}" for x in R.OFFS)
    attempts = [
        ("reltol=1e-6 pss_tolscale=3e-3", 8000, 32, 16),
        ("reltol=3e-6 pss_tolscale=1e-2", 8000, 24, 12),
        ("reltol=3e-6 pss_tolscale=1e-2", 4000, 16, 8),
    ]
    for opts, npts, mh, th in attempts:
        print(f"  try npts={npts} {opts} maxharm={mh} …", flush=True)
        sim = S2.netlist(
            "s3_pn_d9_mim_r", code, vt, itail=itail, bypass=True,
            bypass_groups=("tail", "var"),
            analysis=(
                f"  options temp={temp} {opts} pss_minpts={npts}\n"
                '  analysis warm tran stop=80n step=5p maxstep=5p store="ss"\n'
                f'  analysis pn pnoise oscillator=1 tper={1/f0:.6e} tstab=0 '
                f'ic="ss" icmode="uic" maxharm={mh} truncharm={th} in="iin" '
                f'out=["tp", "tn"] outharm=1 values=[{vals}] writepss=1'
            ),
            extra="iin (0 tp) isource dc=0\n",
        )
        text = open(sim).read()
        text = R.patch_cbf(text, "mim")
        open(sim, "w").write(text)
        try:
            S2.run(sim)
        except RuntimeError as e:
            print(f"    fail: {[x for x in str(e).splitlines() if x.strip()][-2:]}",
                  flush=True)
            continue
        pss = rawread(os.path.join(R.OUT, "pn.pss.raw")).get()
        a, fp = fundamental_amplitude(
            pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
        pn = rawread(os.path.join(R.OUT, "pn.raw")).get()
        off = np.real(pn["frequency"])
        l = 10 * np.log10(np.real(pn["onoise"]) / (a * a / 2))
        return dict(f=fp, amp=a, L={float(o): float(x) for o, x in zip(off, l)},
                    npts=npts, opts=opts)
    return None


def main():
    print("# rfcmim PN retry (relaxed PSS) vs saved ideal [SCH]\n")
    S3.load_sizing()
    code, vt, f0, itail, temp = 91, S2.VTUNE_MID, 3.65e9, 4.0e-3, 27.0
    r = pnoise_mim_relaxed(code, vt, f0, itail, temp)
    if not r:
        print("mim: FAILED all attempts\nOverall pass: FAIL\n")
        open(os.path.join(R.OUT, "mim_vs_ideal_pass.flag"), "w").write("FAIL\n")
        return 1
    print(f"  mim: f={r['f']/1e9:.3f} GHz amp={r['amp']:.3f} "
          + " ".join(f"L({o/1e3:.0f}k)={r['L'][o]:.2f}" for o in R.OFFS)
          + f"  [{r['npts']}, {r['opts']}]", flush=True)
    print("\n| Offset | L ideal | L rfcmim | Δ |")
    print("|---|---|---|---|")
    ok = True
    for o in R.OFFS:
        a, b = IDEAL["L"][o], r["L"][o]
        d = b - a
        print(f"| {o/1e3:.0f} kHz | {a:.2f} | {b:.2f} | {d:+.3f} dB |")
        if abs(d) >= PASS_DB:
            ok = False
    a0, a1 = IDEAL["amp"], r["amp"]
    rel = (a1 - a0) / a0
    print(f"\nSwing: ideal {a0:.3f} V → rfcmim {a1:.3f} V ({rel*100:+.2f} %) [SCH]")
    print(f"Swing PASS: {'PASS' if abs(rel) < PASS_SWING else 'FAIL'}")
    if abs(rel) >= PASS_SWING:
        ok = False
    print(f"\nOverall pass: {'PASS' if ok else 'FAIL'}\n")
    open(os.path.join(R.OUT, "mim_vs_ideal_pass.flag"), "w").write(
        "PASS\n" if ok else "FAIL\n")
    open(os.path.join(R.OUT, "summary_mim_retry.txt"), "w").write(
        open(os.path.join(R.OUT, "summary_mim_vs_ideal.txt")).read()
        if False else "")  # filled by tee
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
