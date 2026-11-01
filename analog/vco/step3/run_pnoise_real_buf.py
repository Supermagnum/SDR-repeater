#!/usr/bin/env python3
"""VCO pnoise with the real P2.4 LO buffer (± first CML divider) as tank load.

Replaces the step-2 stand-in CML pair. Bank bypass MOS omitted (PSS); tail+var kept.
Compares L(1 MHz) to bank-omitted stand-in baseline (summary_pn_nobank.txt).

Modes (argv): buffer (default) = P2.4 buffer only; cml = buffer + first CML ÷2/÷3.

    python3 -u run_pnoise_real_buf.py | tee out/summary_pn_real_buf.txt
    python3 -u run_pnoise_real_buf.py cml | tee out/summary_pn_real_buf_cml.txt
"""
import importlib.util
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import run_step3 as s3
from compare import fundamental_amplitude

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MODE = "cml" if "cml" in sys.argv[1:] else "buffer"


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


L3 = _load("lo_step3_rbuf", "analog/lo/step3/run_step3.py")
# lo/step2 redirects vco step2 OUT into lo/step2/out — put it back.
s3.OUT = os.path.join(HERE, "out")
s3.S2.OUT = s3.OUT
os.makedirs(s3.OUT, exist_ok=True)

GROUPS = ("tail", "var")
BASELINE = {"tt_3.65": -122.7, "ss85_4.20": -119.4}


def lo_load(band="uhf"):
    """P2.4 buffer on tp/tn; optional first CML ÷2 (UHF) or ÷3 (VHF)."""
    L1, L2 = L3.L1, L3.L2
    vdd = 1.2
    s = 'vbufs (vbuf 0) vsource dc=1.2\n' + L2.buffer()
    if MODE == "cml":
        n_div = 2 if band == "uhf" else 3
        i_, rl, w = L1.cml_params(0.5e-3, vdd)
        body, out = L1.div_body(n_div, i_, rl, w, vdd)
        body = body.replace("(vdd ", "(vdv ")
        s += ('vdvs (vdv 0) vsource dc=1.2\n' + body
              + f"clop ({out[0]} 0) capacitor c=20f\nclon ({out[1]} 0) capacitor c=20f\n")
    else:
        # Terminate buffer clocks lightly (no CML).
        s += "clckp (ckp 0) capacitor c=20f\nclckn (ckn 0) capacitor c=20f\n"
    return s


def pnoise(code, vt, f0, itail, temp, tag, band):
    vals = ", ".join(f"{x:.0f}" for x in s3.OFFS)
    for opts, npts in (("reltol=1e-6 pss_tolscale=1e-3", 8000),
                       ("reltol=1e-6 pss_tolscale=1e-3", 16000)):
        sim = s3.S2.netlist(
            f"s3_pn_rbuf_{tag}", code, vt, itail=itail, bypass=True,
            bypass_groups=GROUPS, standin_buffer=False,
            analysis=(
                f"  options temp={temp} {opts} pss_minpts={npts}\n"
                '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
                f'  analysis pn pnoise oscillator=1 tper={1/f0:.6e} tstab=0 ic="ss" icmode="uic" '
                f'maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] outharm=1 '
                f"values=[{vals}] writepss=1"
            ),
            extra="iin (0 tp) isource dc=0\n" + lo_load(band),
        )
        try:
            s3.S2.run(sim)
            break
        except RuntimeError as e:
            print(f"  pss failed ({opts}, {npts}): "
                  f"{[x for x in str(e).splitlines() if x.strip()][-2:]}")
    else:
        return None
    pss = rawread(os.path.join(s3.OUT, "pn.pss.raw")).get()
    a, fp = fundamental_amplitude(pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
    pn = rawread(os.path.join(s3.OUT, "pn.raw")).get()
    off = np.real(pn["frequency"])
    l = 10 * np.log10(np.real(pn["onoise"]) / (a * a / 2))
    return dict(f=fp, amp=a, L={float(o): float(x) for o, x in zip(off, l)})


def main():
    print(f"# VCO pnoise — real P2.4 LO load ({MODE}) [SCH]\n")
    print("Stand-in buffer removed; bank bypass MOS omitted (PSS). "
          "Baseline: summary_pn_nobank.txt.\n")
    _, meas = s3.load_sizing()
    cases = [
        ("tt_3.65", "mos_tt", "cap_typ", 27, 3.65e9, "uhf", 91),
        ("ss85_4.20", "mos_ss", "cap_typ", 85, 4.20e9, "vhf", 21),
    ]
    rows = []
    for tag, mos, cap, temp, f0, band, code in cases:
        s3.set_corner(mos, cap)
        it = s3.itail_for(f0, meas)
        print(f"  {tag} ({band}): code {code}, I_tail {it*1e3:.2f} mA …")
        r = pnoise(code, s3.S2.VTUNE_MID, f0, it, temp, tag, band)
        rows.append((tag, code, it, r))
        if r is not None:
            L1 = r["L"][1e6]
            base = BASELINE[tag]
            print(f"    L@1 MHz = {L1:.1f} dBc/Hz (stand-in baseline {base:.1f}, "
                  f"Δ {L1 - base:+.2f} dB)")
    s3.pn_table(f"real LO {MODE} (dBc/Hz)", rows)


if __name__ == "__main__":
    main()
