#!/usr/bin/env python3
"""Which linear-bank elements keep PSS alive? tt 3.65 GHz, pss_minpts=8000."""
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
s3.S2.BANK_OFF.update(
    roff=j["roff"], c_ds=j["c_ds"], c_db=j["c_db"], c_sb=j["c_sb"], r_shot=j["r_shot"]
)
F0 = 3.65e9
CODE = s3.code_for(F0, 27, "probe")
IT = s3.itail_for(F0, s3.load_sizing()[1])
ORIG = s3.S2.bias_bypass_bank_linear


def make(parts):
    def lin(nbits=None, p=None):
        p = dict(s3.S2.BANK_OFF if p is None else p)
        nbits = s3.S2.NBITS if nbits is None else nbits
        lines = [f"// probe linear bank {parts}\n"]
        for side, node in (("a", "a"), ("b", "b")):
            for k in range(nbits):
                n, bb = f"{node}{k}", f"bb{k}"
                tag = f"{side}{k}"
                if "c" in parts:
                    lines.append(f"cds_{tag} ({n} {bb}) capacitor c={p['c_ds']:.6g}\n"
                                 f"csb_{tag} ({bb} 0) capacitor c={p['c_sb']:.6g}\n")
                if "roff" in parts:
                    lines.append(f"roff_{tag} ({n} {bb}) resistor r={p['roff']:.6g}\n")
                if "rsh" in parts:
                    lines.append(f"rsh_{tag} ({n} {bb}) resistor r={p['r_shot']:.6g} noisy=1\n")
        return "".join(lines)
    return lin


def try_mode(label, parts):
    s3.S2.bias_bypass_bank_linear = make(parts)
    analysis = (
        f"  options temp=27 reltol=1e-6 pss_tolscale=1e-3 pss_minpts=8000\n"
        '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
        f'  analysis pn pnoise oscillator=1 tper={1/F0:.6e} tstab=0 ic="ss" icmode="uic" '
        f'maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] outharm=1 values=[1e6] writepss=1'
    )
    try:
        sim = s3.S2.netlist(
            f"s3_probe_{label}", CODE, s3.S2.VTUNE_MID, itail=IT, bypass=True,
            bypass_groups=("tail", "bank", "var"), bank_mode="linear",
            analysis=analysis, extra="iin (0 tp) isource dc=0\n",
        )
        s3.S2.run(sim)
        pss = rawread(os.path.join(s3.OUT, "pn.pss.raw")).get()
        a, fp = fundamental_amplitude(pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
        pn = rawread(os.path.join(s3.OUT, "pn.raw")).get()
        L = 10 * np.log10(np.real(pn["onoise"]) / (a * a / 2))
        print(f"PROBE {label}: OK L@1M={float(np.real(L).ravel()[0]):.2f} amp={a:.3f}")
        return float(np.real(L).ravel()[0])
    except Exception as e:
        print(f"PROBE {label}: FAIL {[x for x in str(e).splitlines() if x.strip()][-2:]}")
        return None
    finally:
        s3.S2.bias_bypass_bank_linear = ORIG


def main():
    print(f"code={CODE} itail={IT*1e3:.2f} mA ref bank-omitted −122.7 dBc/Hz\n")
    for lab, parts in (("C", "c"), ("C_Roff", "c,roff"), ("C_Roff_Rsh", "c,roff,rsh")):
        try_mode(lab, set(parts.split(",")))


if __name__ == "__main__":
    main()
