#!/usr/bin/env python3
import json
import os

import numpy as np
from vacask.rawfile import rawread

import run_step3 as s3
from compare import fundamental_amplitude

s3.OUT = "out"
s3.load_sizing()
s3.set_corner("mos_tt", "cap_typ")
j = json.load(open(os.path.join(s3.OUT, "bank_bypass_off.json")))
F0 = 3.65e9
CODE = s3.code_for(F0, 27, "p2")
IT = s3.itail_for(F0, s3.load_sizing()[1])
ANALYSIS = (
    f"  options temp=27 reltol=1e-6 pss_tolscale=1e-3 pss_minpts=8000\n"
    '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
    f'  analysis pn pnoise oscillator=1 tper={1/F0:.6e} tstab=0 ic="ss" icmode="uic" '
    f'maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] outharm=1 values=[1e6] writepss=1'
)


def lin_factory(scale):
    def lin(nbits=None, p=None):
        nbits = s3.S2.NBITS if nbits is None else nbits
        cds, csb = j["c_ds"] * scale, j["c_sb"] * scale
        o = [f"// c only scale={scale}\n"]
        for side, node in (("a", "a"), ("b", "b")):
            for k in range(nbits):
                n, bb = f"{node}{k}", f"bb{k}"
                tag = f"{side}{k}"
                o.append(f"cds_{tag} ({n} {bb}) capacitor c={cds:.6g}\n"
                         f"csb_{tag} ({bb} 0) capacitor c={csb:.6g}\n")
        return "".join(o)
    return lin


def try_one(label, groups, scale):
    s3.S2.bias_bypass_bank_linear = lin_factory(scale)
    try:
        sim = s3.S2.netlist(
            f"s3_p2_{label}", CODE, s3.S2.VTUNE_MID, itail=IT, bypass=True,
            bypass_groups=groups, bank_mode="linear", analysis=ANALYSIS,
            extra="iin (0 tp) isource dc=0\n",
        )
        s3.S2.run(sim)
        pss = rawread(os.path.join(s3.OUT, "pn.pss.raw")).get()
        a, fp = fundamental_amplitude(pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
        pn = rawread(os.path.join(s3.OUT, "pn.raw")).get()
        L = 10 * np.log10(np.real(pn["onoise"]) / (a * a / 2))
        print(f"OK {label}: L@1M={float(np.real(L).ravel()[0]):.2f} amp={a:.3f}")
    except Exception as e:
        print(f"FAIL {label}: {[x for x in str(e).splitlines() if x.strip()][-2:]}")


def main():
    print(f"code={CODE} itail={IT*1e3:.2f}\n")
    try_one("bank_only_C", ("bank",), 1.0)
    try_one("all_C_0p1", ("tail", "bank", "var"), 0.1)
    try_one("bank_only_C_0p1", ("bank",), 0.1)


if __name__ == "__main__":
    main()
