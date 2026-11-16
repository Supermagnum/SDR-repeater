#!/usr/bin/env python3
"""Hold droop over one settle step with fab detector [SCH]."""
import os
import sys

import numpy as np
from vacask.rawfile import rawread

import amp_common as A
import run_step2 as S2
import run_search as RS

A.load_sizing()
A.OUT = os.path.join(A.OUT, "sar_droop")
os.makedirs(A.OUT, exist_ok=True)
S2.OUT = A.OUT
A.set_corner("mos_tt", "cap_typ")
r = RS.measure("mos_tt", "cap_typ", 27, 0, 20, "droop_c20")
d = rawread(os.path.join(A.OUT, "tr.raw")).get()
t = np.real(d["time"])
h = np.real(d["hold"])
rp = np.real(d["rep"])
m0 = (t >= 40e-9) & (t <= 60e-9)
m1 = t >= t[-1] - 20e-9
print(
    f"hold early={h[m0].mean():.4f} late={h[m1].mean():.4f} "
    f"droop_mV={(h[m0].mean() - h[m1].mean()) * 1e3:.2f}"
)
print(
    f"rep early={rp[m0].mean():.4f} late={rp[m1].mean():.4f} "
    f"vsense_late={h[m1].mean() - rp[m1].mean():.4f}"
)
print(f"Amp={r['amp']:.3f} cmp={r['cmp']:.3f} [SCH]")
