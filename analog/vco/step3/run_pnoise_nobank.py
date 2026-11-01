#!/usr/bin/env python3
"""PSS/pnoise with bank bypass MOS omitted (tail+var kept).

Bank-group off-state devices break PSS; tail and varactor groups do not
(summary_pss_bypass_parts.txt). Not the full current schematic — VCO layout still
waits for a method that includes bank bypasses.

    python3 -u run_pnoise_nobank.py | tee out/summary_pn_nobank.txt
"""
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import run_step3 as s3
from compare import fundamental_amplitude

s3.OUT = "out"
GROUPS = ("tail", "var")


def pnoise(code, vt, f0, itail, temp, tag):
    vals = ", ".join(f"{x:.0f}" for x in s3.OFFS)
    for opts, npts in (("reltol=1e-6 pss_tolscale=1e-3", 16000), ("reltol=1e-6 pss_tolscale=1e-3", 8000)):
        sim = s3.S2.netlist(
            f"s3_pn_nbk_{tag}", code, vt, itail=itail, bypass=True, bypass_groups=GROUPS,
            analysis=(
                f"  options temp={temp} {opts} pss_minpts={npts}\n"
                '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
                f'  analysis pn pnoise oscillator=1 tper={1/f0:.6e} tstab=0 ic="ss" icmode="uic" '
                f'maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] outharm=1 values=[{vals}] writepss=1'
            ),
            extra="iin (0 tp) isource dc=0\n",
        )
        try:
            s3.S2.run(sim)
            break
        except RuntimeError as e:
            print(f"  pss failed ({opts}, {npts}): {[x for x in str(e).splitlines() if x.strip()][-2:]}")
    else:
        return None
    pss = rawread(os.path.join(s3.OUT, "pn.pss.raw")).get()
    a, fp = fundamental_amplitude(pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
    pn = rawread(os.path.join(s3.OUT, "pn.raw")).get()
    off = np.real(pn["frequency"])
    l = 10 * np.log10(np.real(pn["onoise"]) / (a * a / 2))
    return dict(f=fp, amp=a, L={float(o): float(x) for o, x in zip(off, l)})


def main():
    print("# VCO pnoise — bank bypass MOS omitted (tail+var present)\n")
    print("Full current schematic includes bank bypasses; those alone break PSS. "
          "This run keeps tail and varactor bypass devices with vbp=0.\n")
    r, meas = s3.load_sizing()
    cases = [("tt_3.65", "mos_tt", "cap_typ", 27, 3.65e9),
             ("ss85_4.20", "mos_ss", "cap_typ", 85, 4.20e9)]
    want = [a for a in sys.argv[1:] if a in ("tt", "worst")] or ["tt", "worst"]
    rows = []
    for tag, mos, cap, temp, f0 in cases:
        if tag.startswith("tt") and "tt" not in want:
            continue
        if tag.startswith("ss") and "worst" not in want:
            continue
        s3.set_corner(mos, cap)
        code = s3.code_for(f0, temp, f"{tag}_c")
        it = s3.itail_for(f0, meas)
        print(f"  {tag}: code {code}, I_tail {it*1e3:.2f} mA …")
        rows.append((tag, code, it, pnoise(code, s3.S2.VTUNE_MID, f0, it, temp, tag)))
    s3.pn_table("tail+var bypass, no bank (dBc/Hz)", rows)


if __name__ == "__main__":
    main()
