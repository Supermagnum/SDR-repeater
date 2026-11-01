#!/usr/bin/env python3
"""A/B: does removing start-up bypass MOS restore PSS? tt, 4.20 GHz."""
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import run_step3 as s3
from compare import fundamental_amplitude

s3.OUT = "out"
r, meas = s3.load_sizing()
s3.set_corner("mos_tt", "cap_typ")
F0 = 4.20e9
CODE = s3.code_for(F0, 27, "ab")
IT = s3.itail_for(F0, meas)
print(f"code={CODE} itail={IT*1e3:.3f} mA f0={F0/1e9}")

ORIG = s3.S2.bias_bypass_switches


def none_bypass(nbits=None):
    return "// bypass switches removed for A/B\n"


def try_pss(tag, with_bypass, npts=8000):
    s3.S2.bias_bypass_switches = ORIG if with_bypass else none_bypass
    opts = "reltol=1e-6 pss_tolscale=1e-3"
    analysis = (
        f"  options temp=27 {opts} pss_minpts={npts}\n"
        '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
        f'  analysis pn pnoise oscillator=1 tper={1/F0:.6e} tstab=0 ic="ss" icmode="uic" '
        f'maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] outharm=1 values=[1e6] writepss=1'
    )
    sim = s3.S2.netlist(
        f"s3_ab_{tag}", CODE, s3.S2.VTUNE_MID, itail=IT, analysis=analysis,
        extra="iin (0 tp) isource dc=0\n",
    )
    try:
        s3.S2.run(sim)
        pss = rawread(os.path.join(s3.OUT, "pn.pss.raw")).get()
        a, fp = fundamental_amplitude(pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
        print(f"AB {tag}: PSS OK amp={a:.3f} f={fp/1e9:.4f} GHz")
        return True
    except RuntimeError as e:
        print(f"AB {tag}: PSS FAIL {[x for x in str(e).splitlines() if x.strip()][-2:]}")
        return False


def main():
    ok_on = try_pss("bypass_on", True)
    ok_off = try_pss("bypass_off", False)
    print("AB_SUMMARY bypass_on", ok_on, "bypass_off", ok_off)
    s3.S2.bias_bypass_switches = ORIG
    path = os.path.join(s3.OUT, "summary_pss_bypass_ab.txt")
    with open(path, "w") as fh:
        fh.write("# VCO PSS A/B — start-up bypass MOS present vs removed\n\n")
        fh.write(f"tt / cap_typ / 27 C, {F0/1e9:.2f} GHz, code {CODE}, I_tail {IT*1e3:.2f} mA\n")
        fh.write(f"pss_minpts=8000, reltol=1e-6 pss_tolscale=1e-3\n\n")
        fh.write(f"| Case | Result |\n|---|---|\n")
        fh.write(f"| bypass MOS present (vbp tied 0) | {'PASS' if ok_on else 'PSS failed'} |\n")
        fh.write(f"| bypass MOS removed | {'PASS' if ok_off else 'PSS failed'} |\n")
    print("wrote", path)
    return 0 if (ok_on or ok_off) else 1


if __name__ == "__main__":
    sys.exit(main())
