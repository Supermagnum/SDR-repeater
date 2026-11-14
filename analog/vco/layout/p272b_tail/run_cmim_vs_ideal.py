#!/usr/bin/env python3
"""P2.7.2b — ideal cbf vs PDK cmim 50 pF (largest tiles): VCO PN + swing [SCH].

cmim Cmax=8 pF [PDK] → side_max=√(8p/1.5fF)=73.03 µm. For 50 pF: 7 tiles of
50/7 pF (side≈69.01 µm), near max. Pass: |ΔL|<0.1 dB, |Δamp|/amp<2 %.

Ideal baseline reused from summary_mim_vs_ideal (same VCO setup) [SCH] to avoid
a second long ideal PSS. cmim uses 7× parallel plates (same approach as rfcmim).

    python3 -u run_cmim_vs_ideal.py | tee out/summary_cmim_vs_ideal.txt
"""
from __future__ import annotations

import math
import os
import re
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
CAP_CAREA = 1.5e-15  # F/µm² [PDK]
CMAX = 8e-12         # F [PDK cmim_maxC]
SIDE_MAX = math.sqrt(CMAX / CAP_CAREA)  # µm
N_TILE = int(math.ceil(50e-12 / CMAX))  # 7
C_EACH = 50e-12 / N_TILE
SIDE = math.sqrt(C_EACH / CAP_CAREA)

# From summary_mim_vs_ideal.txt (ideal 8000-pt success) [SCH]
IDEAL = dict(f=3.649e9, amp=1.201, L={1e5: -92.22, 1e6: -122.18})


def patch_cmim(sim_text: str, n: int, side: float) -> str:
    """cap_cmim is 2-terminal (plus minus) [PDK vacask]."""
    repl = "".join(
        f"xcbf{i} (nbf 0) cap_cmim w={side:.3f}u l={side:.3f}u m=1\n"
        for i in range(n)
    )
    new, cnt = re.subn(r"cbf \(nbf 0\) capacitor c=50p\n", repl, sim_text)
    if cnt != 1:
        raise RuntimeError(f"cbf replace count={cnt}")
    return new


def pnoise_cmim(code, vt, f0, itail, temp):
    vals = ", ".join(f"{x:.0f}" for x in R.OFFS)
    attempts = [
        ("reltol=1e-6 pss_tolscale=3e-3", 8000, 32, 16),
        ("reltol=3e-6 pss_tolscale=1e-2", 8000, 24, 12),
        ("reltol=3e-6 pss_tolscale=1e-2", 4000, 16, 8),
    ]
    for opts, npts, mh, th in attempts:
        print(f"  try npts={npts} {opts} maxharm={mh} …", flush=True)
        sim = S2.netlist(
            "s3_pn_d9_cmim", code, vt, itail=itail, bypass=True,
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
        text = patch_cmim(open(sim).read(), N_TILE, SIDE)
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
    print("# P2.7.2b — cbf ideal vs cmim 50 pF [SCH]\n")
    print(f"PDK: cmim Cmax={CMAX*1e12:.0f} pF → side_max={SIDE_MAX:.2f} µm; "
          f"caspec=1.5 fF/µm² [PDK].")
    print(f"Tiles for 50 pF: n={N_TILE}, each C={C_EACH*1e12:.3f} pF, "
          f"side={SIDE:.3f} µm (near max) [HAND].")
    print("Ideal baseline: summary_mim_vs_ideal.txt (reused) [SCH].")
    print("Pass |ΔL|<0.1 dB, |Δamp|/amp<2 %. Parallel 7× tiles [TOOL].\n")
    S3.load_sizing()
    code, vt, f0, itail, temp = 91, S2.VTUNE_MID, 3.65e9, 4.0e-3, 27.0

    print(f"  ideal (saved): f={IDEAL['f']/1e9:.3f} GHz amp={IDEAL['amp']:.3f} "
          + " ".join(f"L({o/1e3:.0f}k)={IDEAL['L'][o]:.2f}" for o in R.OFFS),
          flush=True)

    print("  running pnoise kind=cmim …", flush=True)
    Lc = pnoise_cmim(code, vt, f0, itail, temp)
    if Lc:
        parts = " ".join(f"L({o/1e3:.0f}k)={Lc['L'][o]:.2f}" for o in R.OFFS)
        print(f"  cmim ({N_TILE}×): f={Lc['f']/1e9:.3f} GHz amp={Lc['amp']:.3f} "
              f"{parts}  [{Lc['npts']}, {Lc['opts']}]", flush=True)
    else:
        print("  cmim: FAILED", flush=True)

    print("\n| Offset | L ideal | L cmim | Δ |")
    print("|---|---|---|---|")
    ok = True
    if Lc:
        for o in R.OFFS:
            a, b = IDEAL["L"][o], Lc["L"][o]
            d = b - a
            print(f"| {o/1e3:.0f} kHz | {a:.2f} | {b:.2f} | {d:+.3f} dB |")
            if abs(d) >= PASS_DB:
                ok = False
        a0, a1 = IDEAL["amp"], Lc["amp"]
        rel = (a1 - a0) / a0
        print(f"\nSwing: ideal {a0:.3f} V → cmim {a1:.3f} V "
              f"({rel*100:+.2f} %) [SCH]")
        print(f"Swing PASS: {'PASS' if abs(rel) < PASS_SWING else 'FAIL'}")
        if abs(rel) >= PASS_SWING:
            ok = False
        print(f"\nOverall pass: {'PASS' if ok else 'FAIL'}\n")
    else:
        ok = False
        print("\nOverall pass: FAIL (pnoise incomplete)\n")

    open(os.path.join(R.OUT, "cmim_vs_ideal_pass.flag"), "w").write(
        "PASS\n" if ok else "FAIL\n")
    open(os.path.join(R.OUT, "summary_cmim_sizing.txt"), "w").write(
        f"n_tile={N_TILE}\nside_um={SIDE:.4f}\nc_each_pF={C_EACH*1e12:.4f}\n"
        f"side_max_um={SIDE_MAX:.4f}\ncmax_pF={CMAX*1e12:.1f}\n"
        f"pass={'yes' if ok else 'no'}\n"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
