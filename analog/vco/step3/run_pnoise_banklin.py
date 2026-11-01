#!/usr/bin/env python3
"""PSS/pnoise with linear off-state bank bypass (tail+var MOS kept).

Compares L(1 MHz) to bank-omitted results; stop if |Δ| > 0.5 dB.

    python3 -u run_pnoise_banklin.py | tee out/summary_pn_banklin.txt
"""
import json
import math
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import run_step3 as s3
from compare import fundamental_amplitude

s3.OUT = "out"
NOBANK = {
    "tt_3.65": -122.7,
    "ss85_4.20": -119.4,
}
LIMIT_DB = 0.5


def pnoise(code, vt, f0, itail, temp, tag):
    vals = ", ".join(f"{x:.0f}" for x in s3.OFFS)
    for opts, npts in (("reltol=1e-6 pss_tolscale=1e-3", 8000), ("reltol=1e-6 pss_tolscale=1e-3", 16000)):
        sim = s3.S2.netlist(
            f"s3_pn_bl_{tag}", code, vt, itail=itail,
            bypass=True, bypass_groups=("tail", "bank", "var"), bank_mode="linear",
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
    # Prefer extracted JSON if present
    jpath = os.path.join(s3.OUT, "bank_bypass_off.json")
    if os.path.exists(jpath):
        j = json.load(open(jpath))
        s3.S2.BANK_OFF.update(
            roff=j["roff"], c_ds=j["c_ds"], c_db=j["c_db"], c_sb=j["c_sb"], r_shot=j["r_shot"]
        )
        print(f"Loaded {jpath}: R_off={j['roff']:.3e} C_ds={j['c_ds']*1e15:.2f} fF "
              f"R_shot={j['r_shot']:.3e} I_leak={j['ileak_ff_hot']:.3e} A\n")

    print("# VCO pnoise — linear off-state bank bypass (tail+var MOS)\n")
    print(f"Compare to bank-omitted L@1 MHz; stop if |Δ| > {LIMIT_DB} dB.\n")
    r, meas = s3.load_sizing()
    cases = [("tt_3.65", "mos_tt", "cap_typ", 27, 3.65e9),
             ("ss85_4.20", "mos_ss", "cap_typ", 85, 4.20e9)]
    rows, stop = [], False
    for tag, mos, cap, temp, f0 in cases:
        s3.set_corner(mos, cap)
        code = s3.code_for(f0, temp, f"{tag}_c")
        it = s3.itail_for(f0, meas)
        print(f"  {tag}: code {code}, I_tail {it*1e3:.2f} mA …")
        pn = pnoise(code, s3.S2.VTUNE_MID, f0, it, temp, tag)
        rows.append((tag, code, it, pn))
        if pn is None:
            print(f"  STOP: PSS failed for {tag}")
            stop = True
            break
        l1 = pn["L"][1e6]
        ref = NOBANK[tag]
        dlt = l1 - ref
        print(f"  L@1 MHz = {l1:.1f} dBc/Hz (bank-omitted {ref:.1f}, Δ {dlt:+.2f} dB)")
        if abs(dlt) > LIMIT_DB:
            print(f"  STOP: |Δ| = {abs(dlt):.2f} dB > {LIMIT_DB} dB")
            stop = True
            break
    s3.pn_table("linear bank bypass (dBc/Hz)", rows)
    if stop:
        print("RESULT: STOP — see Δ or PSS failure above.\n")
        sys.exit(2)
    print(f"All cases within {LIMIT_DB} dB of bank-omitted. Linear equivalent OK for P2.7 PEX PN.\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
