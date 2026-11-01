#!/usr/bin/env python3
"""PSS/pnoise with bypass MOS removed (diagnostic / interim PN while current-SCH methods fail).

Cases: tt 3.65 GHz and ss/85 4.20 GHz.

    python3 -u run_pnoise_nobypass.py | tee out/summary_pn_nobypass.txt
"""
import os
import sys

import run_step3 as s3

s3.OUT = "out"
ARGS = sys.argv[1:]


def pnoise_nb(code, vt, f0, itail, temp, tag):
    from vacask.rawfile import rawread
    from compare import fundamental_amplitude
    import numpy as np
    vals = ", ".join(f"{x:.0f}" for x in s3.OFFS)
    for opts, npts in (("reltol=1e-6 pss_tolscale=1e-3", 16000), ("reltol=1e-6 pss_tolscale=1e-3", 8000)):
        sim = s3.S2.netlist(
            f"s3_pn_nb_{tag}", code, vt, itail=itail, bypass=False, analysis=
            f"  options temp={temp} {opts} pss_minpts={npts}\n"
            '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
            f'  analysis pn pnoise oscillator=1 tper={1/f0:.6e} tstab=0 ic="ss" icmode="uic" '
            f'maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] outharm=1 values=[{vals}] writepss=1',
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
    print("# VCO pnoise with start-up bypass MOS removed [SCH diagnostic]\n")
    print("Current schematic includes bypass devices; those break PSS. Numbers here are without "
          "the devices (pre-open-point-2 netlist for noise). Layout still waits for a current-SCH method.\n")
    r, meas = s3.load_sizing()
    cases = []
    if not ARGS or "tt" in ARGS:
        cases.append(("tt_3.65", "mos_tt", "cap_typ", 27, 3.65e9))
    if not ARGS or "worst" in ARGS:
        cases.append(("ss85_4.20", "mos_ss", "cap_typ", 85, 4.20e9))
    rows = []
    for tag, mos, cap, temp, f0 in cases:
        s3.set_corner(mos, cap)
        code = s3.code_for(f0, temp, f"{tag}_c")
        it = s3.itail_for(f0, meas)
        print(f"  {tag}: code {code}, I_tail {it*1e3:.2f} mA …")
        rows.append((tag, code, it, pnoise_nb(code, s3.S2.VTUNE_MID, f0, it, temp, tag)))
    s3.pn_table("bypass removed (dBc/Hz)", rows)


if __name__ == "__main__":
    main()
