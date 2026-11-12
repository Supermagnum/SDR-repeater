#!/usr/bin/env python3
"""Bank bypass wake RC (P2.7.1c / D24) [SCH].

For each physical bank cell: measure Ron (V_GS=1.2 V, V_DS=50 mV) at ss/−40 °C and
ff/125 °C; τ = Ron × C_plate with C_plate = one-side MIM from range.json.
Report n_τ in the 36-cycle windows (1.00 µs @ 36 MHz, 1.12 µs @ 32 MHz).
Pass: ≥ 6–7 τ in 1.00 µs at both corners.

    python3 -u run_wake_bank_bypass.py | tee out/summary_wake_bank_bypass.txt
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np
from vacask.rawfile import rawread

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, HERE)
import run_step2 as S2  # noqa: E402

RANGE_JSON = os.path.join(OUT, "range.json")
CORNERS = (("mos_ss", -40), ("mos_ff", 125))
VDS = 0.05
WINDOWS = (("36 MHz", 1.00e-6), ("32 MHz", 1.12e-6))


def run_vacask(name, text):
    path = os.path.join(OUT, name + ".sim")
    open(path, "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(open(log).read()[-800:])
    return log


def _flow(d, src):
    for k in d.names:
        if k.startswith(src + ":") or k == f"i({src})":
            return float(np.real(np.asarray(d[k]).ravel()[0]))
    raise KeyError(d.names)


def ron_one(w, l, ng, mos, temp, tag):
    text = f"""ground 0
include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section={mos}
load "resistor.osdi"
load "capacitor.osdi"
model resistor resistor
model capacitor capacitor
model vsource vsource
vd (dx 0) vsource dc={VDS}
vs (s 0) vsource dc=0
vg (g 0) vsource dc=1.2
vi (d dx) vsource dc=0
m (d g s 0) sg13_lv_nmos w={w:.4g}u l={l:g}u ng={ng}
control
  abort always
  options temp={temp} reltol=1e-6 rawfile="binary" strictsave=1
  save i(vi)
  analysis op1 op
endc
"""
    run_vacask(f"wake_ron_{tag}", text)
    d = rawread(os.path.join(OUT, "op1.raw")).get()
    i = abs(_flow(d, "vi"))
    if i <= 0:
        raise RuntimeError(f"I=0 for {tag}")
    return VDS / i


def plate_c_f(i, lsb):
    """One-side MIM capacitance (F) for physical cell i."""
    c_mim_ff = 2 * lsb * S2.cell_weight(i) * S2.cell_trim(i)
    return c_mim_ff * 1e-15


def main():
    if not os.path.exists(RANGE_JSON):
        lsb = S2.LSB_FF
        src = "run_step2 defaults (no range.json yet)"
    else:
        r = json.load(open(RANGE_JSON))
        lsb = r["lsb"]
        S2.apply_range_trims(r)
        src = "step2/out/range.json"

    ncell = S2.n_bank_cells()
    print(f"# Bank bypass wake timing ({S2.BANK_ARCH}, {ncell} cells) [SCH]\n")
    print(f"PDK minW = {S2.BANK_BP_W_MIN} µm. "
          f"Ref w={S2.BANK_BP_W_MSB}u @ weight {S2.BANK_BP_W_REF:g}. "
          f"Plate C from {src}.\n")
    print("| cell | wt | W (µm) | ng | C_plate (fF) | corner | Ron (Ω) | τ (ns) | "
          "nτ @1.00 µs | nτ @1.12 µs |")
    print("|---|---|---|---|---|---|---|---|---|---|")

    worst = {}
    rows = []
    for k in range(ncell):
        w, l, ng = S2.bank_bypass_geom(k)
        c = plate_c_f(k, lsb)
        wt = S2.cell_weight(k)
        for mos, temp in CORNERS:
            tag = f"c{k}_{mos}_{temp}".replace("-", "m")
            try:
                ron = ron_one(w, l, ng, mos, temp, tag)
            except Exception as e:
                print(f"| {k} | {wt} | {w:.4g} | {ng} | {c*1e15:.2f} | {mos}/{temp} | "
                      f"FAIL: {e} | | | |")
                rows.append(dict(k=k, fail=True))
                continue
            tau = ron * c
            n1 = WINDOWS[0][1] / tau if tau > 0 else float("inf")
            n2 = WINDOWS[1][1] / tau if tau > 0 else float("inf")
            key = f"{mos}/{temp}"
            worst[key] = min(worst.get(key, float("inf")), n1)
            print(f"| {k} | {wt} | {w:.4g} | {ng} | {c*1e15:.2f} | {mos}/{temp} | "
                  f"{ron:.1f} | {tau*1e9:.3f} | {n1:.0f} | {n2:.0f} |")
            rows.append(dict(k=k, w=w, ng=ng, c=c, mos=mos, temp=temp,
                             ron=ron, tau=tau, n1=n1, n2=n2, fail=False))

    print()
    for key, n in worst.items():
        ok = "PASS" if n >= 6.5 else ("MARGINAL (≥6)" if n >= 6 else "FAIL")
        print(f"Worst nτ in 1.00 µs at {key}: {n:.1f} → {ok} (need ≥ 6–7)")
    ok_bits = [r for r in rows if not r.get("fail")]
    if ok_bits:
        lim = min(ok_bits, key=lambda r: r["n1"])
        print(f"Limiting: cell {lim['k']} {lim['mos']}/{lim['temp']} "
              f"τ={lim['tau']*1e9:.3f} ns, nτ={lim['n1']:.1f}")
    print("\nVar / tail bypass unchanged (not re-sized this run).")


if __name__ == "__main__":
    main()
