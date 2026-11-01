#!/usr/bin/env python3
"""One attempt: full UHF LO chain (buffer + CML ÷2 + AC converter + Johnson ÷4) transient noise."""
import json
import math
import os
import re
import sys

import numpy as np

import run_p26s2 as s2

L3 = s2.load("lo_step3", "analog/lo/step3/run_step3.py")
L3.OUT = s2.OUT

BAND, F, AMP = "uhf", 3.84e9, 0.62
CORNER = [c for c in L3.CORNERS if c[0] == "tt"][0]
F_LO = F / 8
TSTOP = 1e-6


def main():
    print("# Full UHF LO chain floor attempt (incl. Johnson ÷4)\n")
    print(f"VCO {F/1e9:.2f} GHz -> LO {F_LO/1e6:.0f} MHz, tstop={TSTOP*1e6:g} us, corner {CORNER[0]}\n")
    out = {}
    for noisy in (True, False):
        path, names, *_ = L3.build(BAND, F, CORNER, tag=f"_fulluhf{int(noisy)}", amp=AMP)
        node = names[0][1]
        print("node", node, "noisy", noisy, "deck", path)
        text = open(path).read()
        text = re.sub(
            r'type="pulse" val0=0 val1=(\S+) delay=\S+ rise=\S+ fall=\S+ width=1',
            r"dc=\1",
            text,
        )
        if noisy:
            text = re.sub(
                r"(\) resistor r=(\S+))(?=\s|$)(?!\s+noisy)",
                lambda m: m.group(1) + ("" if m.group(2) == "1G" else " noisy=1"),
                text,
            )
        warm = round(60e-9 * F_LO) / F_LO
        base = text
        d, used, err = None, None, "none"
        for nf in (["50G", "20G", "10G", "5G"] if noisy else [None]):
            an = (
                f"  options strictsave=1\n"
                f'  analysis warm tran stop={warm:.6e} step=5p maxstep=5p icmode="uic" store="ss"\n'
                f"  save v({node})\n"
                f'  analysis tr tran stop={TSTOP:.4e} step=5p maxstep=5p ic="ss" icmode="uic"'
                + (f' noisemode="zoh" noisefmax={nf} noisefmin=50k oversample=1' if nf else "")
            )
            open(path, "w").write(re.sub(r"  analysis tr tran stop=\S+ step=5p maxstep=5p", an, base))
            try:
                d, used = L3.run(path), nf
                break
            except Exception as e:
                err = str(e)
                print(f"  fail noisy={noisy} nf={nf}: {[x for x in err.splitlines() if x.strip()][-2:]}")
        if d is None:
            print("FULL_UHF_FAIL", noisy, err[-300:])
            sys.exit(2)
        t, v = np.real(d["time"]), np.real(d[node])
        out[noisy] = (node,) + s2.tie_spectrum(t, v, CORNER[2] / 2, F_LO) + (used,)
        print("ok edges~", len(out[noisy][1]) * 2, "jit_fs", out[noisy][3] * 1e15, "nf", used)

    fr, L = out[True][1], out[True][2]

    def band_avg(a, b):
        m = (fr >= a) & (fr <= b)
        return 10 * math.log10(np.mean(10 ** (L[m] / 10)))

    vals = [band_avg(1e6, 3e6), band_avg(3e6, 10e6), band_avg(10e6, 30e6)]
    print("FULL_UHF_FLOOR", vals, "PASS" if vals[1] <= -150 else "FAIL_LIMIT")
    p = os.path.join(s2.OUT, "lo_noise.json")
    lo = json.load(open(p)) if os.path.exists(p) else {}
    lo["uhf_tt"] = dict(f_lo=F_LO, floor=vals[1], fr=fr.tolist(), L=L.tolist(), method="full_chain")
    json.dump(lo, open(p, "w"))
    print("wrote uhf_tt into lo_noise.json")
    with open(os.path.join(s2.OUT, "summary_uhf_floor_full.txt"), "w") as fh:
        fh.write("# Full UHF LO chain floor (buffer + CML ÷2 + AC converter + Johnson ÷4)\n\n")
        fh.write(f"| Stage | Noise BW | L@LO 1–3 | L@LO 3–10 | L@LO 10–30 |\n|---|---|---|---|---|\n")
        fh.write(f"| full chain | {out[True][4]} | {vals[0]:.1f} | {vals[1]:.1f} | {vals[2]:.1f} |\n")


if __name__ == "__main__":
    main()
