#!/usr/bin/env python3
"""P2.6 open point 3 — UHF LO-floor (full chain).

Method: full UHF LO path from analog/lo/step3 — buffer + CML ÷2 + AC converter +
Johnson ÷4 / retiming. Ideal tank sine at 3.84 GHz; measure Q+ at 480 MHz with the
same warm-up + ZOH transient-noise flow as VHF. Noise BW tried 50 / 20 / 10 / 5 GHz
(converges at 5 GHz on 2026.10 / a49358cc).

    python3 -u run_uhf_floor.py | tee out/summary_uhf_floor.txt

Target ≤ −150 dBc/Hz at the LO. Results [SCH].
"""
import json
import math
import os
import re
import sys

import numpy as np

import run_p26s2 as s2

L3 = s2.load("lo_step3", "analog/lo/step3/run_step3.py")
L3.OUT = s2.OUT

F_VCO = 3.84e9
F_LO = F_VCO / 8
AMP = 0.62
CORNER = ("tt", "mos_tt", 1.20, 27)
TSTOP = 1e-6
TARGET = -150.0


def main():
    print("# P2.6 open point 3 — UHF LO floor [SCH]\n")
    print("**Method:** full UHF LO chain — buffer + CML ÷2 + AC converter + Johnson ÷4 / "
          f"retiming. Ideal tank {F_VCO/1e9:.2f} GHz, measure Q+ at {F_LO/1e6:.0f} MHz, "
          f"{TSTOP*1e6:g} µs ZOH transient noise (warm-up as VHF). "
          f"Target ≤ {TARGET:.0f} dBc/Hz at the LO.\n")
    ctag, mos, vdd, temp = CORNER
    corner = (ctag, mos, vdd, temp)
    out = {}
    for noisy in (True, False):
        path, names, *_ = L3.build("uhf", F_VCO, corner, tag=f"_uhffloor{int(noisy)}", amp=AMP)
        node = names[0][1]
        text = open(path).read()
        text = re.sub(
            r'type="pulse" val0=0 val1=(\S+) delay=\S+ rise=\S+ fall=\S+ width=1',
            r"dc=\1", text,
        )
        if noisy:
            text = re.sub(
                r"(\) resistor r=(\S+))(?=\s|$)(?!\s+noisy)",
                lambda m: m.group(1) + ("" if m.group(2) == "1G" else " noisy=1"),
                text,
            )
        warm = round(60e-9 * F_LO) / F_LO
        base, d, used, err = text, None, None, "none"
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
                print(f"  fail noisy={noisy} nf={nf}: "
                      f"{[x for x in err.splitlines() if x.strip()][-2:]}")
        if d is None:
            print(f"\n**KNOWN GAP:** full UHF chain did not converge. Last error:\n{err[-400:]}")
            sys.exit(2)
        t, v = np.real(d["time"]), np.real(d[node])
        out[noisy] = (node,) + s2.tie_spectrum(t, v, vdd / 2, F_LO) + (used,)

    fr, L, jit, used = out[True][1], out[True][2], out[True][3], out[True][4]
    fr0, L0 = out[False][1], out[False][2]

    def band_avg(fr_, L_, a, b):
        m = (fr_ >= a) & (fr_ <= b)
        return 10 * math.log10(np.mean(10 ** (L_[m] / 10)))

    vals = [band_avg(fr, L, *r) for r in ((1e6, 3e6), (3e6, 10e6), (10e6, 30e6))]
    num = band_avg(fr0, L0, 3e6, 10e6)
    print("## Result\n")
    print("| Stage | Noise BW | Edges | RMS jitter (fs) | L@LO 1–3 MHz | L@LO 3–10 MHz | "
          "L@LO 10–30 MHz | Numerical 3–10 MHz |")
    print("|---|---|---|---|---|---|---|---|")
    print(f"| full UHF (÷2+Johnson) -> LO | {used} | {len(fr)*2} | {jit*1e15:.0f} | "
          + " | ".join(f"{x:.1f}" for x in vals) + f" | {num:.1f} |")
    print()
    ok = vals[1] <= TARGET
    print(f"**{'PASS' if ok else 'FAIL'}:** LO-referred floor {vals[1]:.1f} dBc/Hz "
          f"{'≤' if ok else '>'} {TARGET:.0f}.")
    lo_path = os.path.join(s2.OUT, "lo_noise.json")
    lo = json.load(open(lo_path)) if os.path.exists(lo_path) else {}
    lo["uhf_tt"] = dict(f_lo=F_LO, floor=vals[1], fr=fr.tolist(), L=L.tolist(),
                        method="full_chain", noisefmax=used)
    json.dump(lo, open(lo_path, "w"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
