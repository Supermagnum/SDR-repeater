#!/usr/bin/env python3
"""Which bypass devices break PSS? tt 4.20 GHz, pss_minpts=8000."""
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import run_step3 as s3
from compare import fundamental_amplitude

s3.OUT = "out"
s3.load_sizing()
s3.set_corner("mos_tt", "cap_typ")
F0 = 4.20e9
CODE = s3.code_for(F0, 27, "parts")
IT = s3.itail_for(F0, s3.load_sizing()[1])
ORIG = s3.S2.bias_bypass_switches


def make(kind):
    def fn(nbits=None):
        nbits = s3.S2.NBITS if nbits is None else nbits
        lines = ["// partial bypass A/B\n"]
        if kind in ("all", "tail"):
            lines.append("mbp_rbf (nb vbp nbf 0) sg13_lv_nmos w=20u l=0.13u ng=4\n")
        if kind in ("all", "bank"):
            for k in range(nbits):
                lines.append(f"mbp_rba{k} (a{k} vbp bb{k} 0) sg13_lv_nmos w=5u l=0.13u ng=2\n"
                             f"mbp_rbb{k} (b{k} vbp bb{k} 0) sg13_lv_nmos w=5u l=0.13u ng=2\n")
        if kind in ("all", "var"):
            lines.append("mbp_rvp (vgp vbp vvb 0) sg13_lv_nmos w=5u l=0.13u ng=2\n"
                         "mbp_rvn (vgn vbp vvb 0) sg13_lv_nmos w=5u l=0.13u ng=2\n")
        if kind == "none":
            return "// no bypass\n"
        return "".join(lines)
    return fn


def try_one(kind):
    s3.S2.bias_bypass_switches = make(kind)
    analysis = (
        f"  options temp=27 reltol=1e-6 pss_tolscale=1e-3 pss_minpts=8000\n"
        '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
        f'  analysis pn pnoise oscillator=1 tper={1/F0:.6e} tstab=0 ic="ss" icmode="uic" '
        f'maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] outharm=1 values=[1e6] writepss=1'
    )
    # force bypass devices via monkeypatch; always tie vbp
    sim = s3.S2.netlist(
        f"s3_parts_{kind}", CODE, s3.S2.VTUNE_MID, itail=IT, analysis=analysis,
        extra="iin (0 tp) isource dc=0\n", bypass=(kind != "none"),
    )
    try:
        s3.S2.run(sim)
        pss = rawread(os.path.join(s3.OUT, "pn.pss.raw")).get()
        a, fp = fundamental_amplitude(pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
        print(f"PARTS {kind}: PSS OK amp={a:.3f} f={fp/1e9:.4f}")
        return True
    except RuntimeError as e:
        print(f"PARTS {kind}: FAIL {[x for x in str(e).splitlines() if x.strip()][-2:]}")
        return False


def main():
    print(f"code={CODE} itail={IT*1e3:.2f} mA")
    results = {}
    for kind in ("none", "tail", "var", "bank", "all"):
        results[kind] = try_one(kind)
    s3.S2.bias_bypass_switches = ORIG
    path = os.path.join(s3.OUT, "summary_pss_bypass_parts.txt")
    with open(path, "w") as fh:
        fh.write("# PSS vs which bypass devices are present (tt 4.20 GHz)\n\n")
        fh.write("| Devices | PSS |\n|---|---|\n")
        for k, ok in results.items():
            fh.write(f"| {k} | {'PASS' if ok else 'FAIL'} |\n")
    print("wrote", path, results)


if __name__ == "__main__":
    sys.exit(0 if main() is None else 0)
