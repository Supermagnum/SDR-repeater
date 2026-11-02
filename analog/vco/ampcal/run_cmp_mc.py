#!/usr/bin/env python3
"""Comparator input-referred offset Monte Carlo [SCH].

Mismatch: σV_T = 3.9 mV·µm (NMOS), as P2.4 step 3. Devices W=4 µm L=0.5 µm →
σV_T_device = 3.9e-3 / sqrt(W·L) V.

    python3 -u run_cmp_mc.py | tee out/summary_cmp_mc.txt
"""
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2

A.load_sizing()
S2.OUT = A.OUT
N = 40
W, L = 4.0, 0.5
SIG = A.SIG_VT_N / (W * L) ** 0.5


def one(vos, tag):
    """Force vip = vin + vos sweep → find trip. Faster: DC vip=vin+delta, read cmp."""
    # Sweep differential input around 0; find where cmp crosses 0.6 V
    trips = []
    for dv in np.linspace(-0.05, 0.05, 21):
        body = (
            f"vdd (vdd 0) vsource dc=1.2\n"
            f"vip (vip 0) vsource dc={0.6 + dv:.6g}\n"
            f"vin (vin 0) vsource dc=0.6\n"
            f"e1 (g1 0) vsource dc={vos[0]:.6g}\n"
            f"e2 (g2 0) vsource dc={vos[1]:.6g}\n"
            f"mc1 (co vipx tt 0) sg13_lv_nmos w={W}u l={L}u ng=2\n"
            f"mc2 (co2 vinx tt 0) sg13_lv_nmos w={W}u l={L}u ng=2\n"
            "rv1 (vip vipx) resistor r=1\n"
            "rv2 (vin vinx) resistor r=1\n"
            "ve1 (vipx vip) vsource dc=0\n"  # placeholder — apply offset in series with gates
        )
        # Apply offset as gate series voltage:
        body = (
            f"vdd (vdd 0) vsource dc=1.2\n"
            f"vip (vip 0) vsource dc={0.6 + dv:.6g}\n"
            f"vin (vin 0) vsource dc=0.6\n"
            f"vo1 (g1 vip) vsource dc={vos[0]:.6g}\n"
            f"vo2 (g2 vin) vsource dc={vos[1]:.6g}\n"
            f"mc1 (co g1 tt 0) sg13_lv_nmos w={W}u l={L}u ng=2\n"
            f"mc2 (co2 g2 tt 0) sg13_lv_nmos w={W}u l={L}u ng=2\n"
            "itt (tt 0) isource dc=20u\n"
            "rc1 (vdd co) resistor r=20k\n"
            "rc2 (vdd co2) resistor r=20k\n"
            "minv (cmp co 0 0) sg13_lv_nmos w=2u l=0.13u ng=1\n"
            "rpu (vdd cmp) resistor r=50k\n"
        )
        path = os.path.join(A.OUT, f"cmp_{tag}.sim")
        open(path, "w").write(
            S2.HEADER.format(title=f"cmp_{tag}") + body
            + "\ncontrol\n  abort always\n  options rawfile=\"binary\" temp=27\n"
            + "  save v(cmp)\n  analysis op1 op\nendc\n"
        )
        try:
            S2.run(path)
            d = rawread(os.path.join(A.OUT, "op1.raw")).get()
            cmpv = float(np.real(d["cmp"]).ravel()[0])
            trips.append((dv, cmpv))
        except Exception:
            continue
    # find crossing 0.6
    for i in range(len(trips) - 1):
        a, b = trips[i], trips[i + 1]
        if (a[1] - 0.6) * (b[1] - 0.6) <= 0:
            # interpolate
            t = (0.6 - a[1]) / (b[1] - a[1] + 1e-30)
            return a[0] + t * (b[0] - a[0])
    return float("nan")


def main():
    print("# Comparator offset Monte Carlo [SCH]\n")
    print(f"N={N}, σV_T/device = {SIG*1e3:.2f} mV (W={W} µm L={L} µm).\n")
    A.set_corner("mos_tt", "cap_typ")
    rng = np.random.default_rng(22)
    offs = []
    for i in range(N):
        vos = rng.normal(0, SIG, size=2)
        o = one(vos, f"mc{i}")
        if o == o:
            offs.append(o)
        if (i + 1) % 20 == 0:
            print(f"  … {i+1}/{N}", flush=True)
    offs = np.array(offs)
    print(f"\nSamples: {len(offs)}")
    print(f"Offset mean {offs.mean()*1e3:.2f} mV, σ {offs.std()*1e3:.2f} mV, "
          f"|max| {np.max(np.abs(offs))*1e3:.2f} mV `[SCH]`")
    print(f"3σ ≈ {3*offs.std()*1e3:.1f} mV → Amp error ≈ {2*3*offs.std()*1e3:.1f} mV differential "
          f"(cmp sees Amp/2) `[HAND]`")
    ok = 3 * offs.std() < 0.05  # 50 mV at Amp/2 node → 100 mV Amp
    print("MC vs ±0.10 V Amp window:", "PASS" if ok else "TIGHT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
