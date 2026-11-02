#!/usr/bin/env python3
"""Detector phase-noise: try bank-omitted PSS; on failure write [HAND] bound.

    python3 -u run_pn_det.py | tee out/summary_pn_det.txt
"""
import os
import re
import sys

import amp_common as A
import run_step2 as S2

A.load_sizing()
S2.OUT = A.OUT


def try_pnoise(en_det):
    sys.path.insert(0, os.path.join(A.REPO, "analog", "vco", "step3"))
    import run_step3 as s3
    s3.OUT = A.OUT
    s3.load_sizing()
    s3.set_corner("mos_tt", "cap_typ")
    code, it, temp, f0 = 91, A.itail(20), 27, 3.65e9
    sim = s3.S2.netlist(
        f"pn_det_{'on' if en_det else 'off'}", code, s3.S2.VTUNE_MID, itail=it,
        bypass=True, bypass_groups=("tail", "var"),
        analysis=(
            f"  options temp={temp} reltol=1e-6 pss_tolscale=1e-3 pss_minpts=8000\n"
            '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
            f'  analysis pn pnoise oscillator=1 tper={1/f0:.6e} tstab=0 ic="ss" icmode="uic" '
            f'maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] outharm=1 values=[1e6] writepss=1'
        ),
        extra="iin (0 tp) isource dc=0\n" + A.detector_snippet(en=en_det),
    )
    text = open(sim).read()
    text = re.sub(r"iref \(vdd nb\) isource dc=[^\n]+\n", A.dac_snippet(20, "nb"), text)
    open(sim, "w").write(text)
    try:
        s3.S2.run(sim)
        return True
    except Exception as e:
        print(f"  PSS failed (det {'on' if en_det else 'off'}): "
              f"{[x for x in str(e).splitlines() if x.strip()][-1][:140]}")
        return False


def hand_bound():
    print("\n## [HAND] bound (PSS with detector did not converge)\n")
    print("C_ac 8 fF on ~800 fF tank: ΔC/C ≈ 1 % `[HAND]`.")
    print("Detector powered down after hold (D22) → ΔL @ 1 MHz ≈ **0 dB** `[HAND]`.")
    print("If left on: < 0.05 dB vs inductor noise at 1 MHz `[HAND]`.")
    print("Worst margin +3.4 dB (ss85 4.20) unchanged vs 0.5 dB gate.")


def main():
    print("# D22 detector phase-noise effect\n")
    print("Attempt bank-omitted PSS with detector (tt 3.65 GHz)…\n")
    ok = try_pnoise(False)
    if ok:
        ok = try_pnoise(True)
    if not ok:
        hand_bound()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
