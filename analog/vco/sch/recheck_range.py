#!/usr/bin/env python3
"""Re-check VCO range codes 0/128/255 via exact step2 tran path."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step2"))
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step1"))

import run_step2 as S2

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
rng = json.load(open(os.path.join(REPO, "analog", "vco", "step2", "out", "range.json")))
S2.LSB_FF = rng["lsb"]
S2.C_FIX_FF = rng["cfix"]
S2.NFING = rng.get("nfing", 20)
S2.NBITS = rng.get("nbits", 8)
S2.TRIM = list(rng["trim"]) + [1.0] * 8
S2.OUT = OUT
itail = rng["itail"]

lines = [
    "# P2.7.1 VCO range via S2.tran (exact step2 path)\n",
    f"itail={itail} lsb={S2.LSB_FF} cfix={S2.C_FIX_FF}\n\n",
    "| code | f_ref | f_new | df% | A_ref | A_new | dA | |\n",
    "|---|---|---|---|---|---|---|---|\n",
]
ok = True
for code in (0, 128, 255):
    key = f"{code},0.65"
    ref = rng["meas"][key]
    m = S2.tran(code, 0.65, f"p271t_c{code}", itail=itail)
    df = 100.0 * (m["f"] - ref["f"]) / ref["f"]
    da = m["amp"] - ref["amp"]
    fl = "PASS" if abs(df) <= 0.2 and abs(da) <= 0.02 else "FAIL"
    if fl == "FAIL":
        ok = False
    row = (
        f"| {code} | {ref['f']/1e9:.4f} | {m['f']/1e9:.4f} | {df:.4f} | "
        f"{ref['amp']:.4f} | {m['amp']:.4f} | {da:.4f} | {fl} |"
    )
    lines.append(row + "\n")
    print(row)
lines.append(f"\nOverall: {'PASS' if ok else 'FAIL'} [SCH]\n")
path = os.path.join(OUT, "summary_range_recheck.txt")
open(path, "w").write("".join(lines))
print("wrote", path, "Overall", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
