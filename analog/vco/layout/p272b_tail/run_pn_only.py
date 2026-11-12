#!/usr/bin/env python3
"""Re-run only the VCO pnoise ideal vs moscap comparison."""
import sys

import run_d9_mos_vs_mim as R
import run_step3 as S3

S3.load_sizing()
print("\n## VCO pnoise re-run (fixed MOSCAP include) [SCH]\n", flush=True)
code, vt, f0, itail, temp = 91, R.S2.VTUNE_MID, 3.65e9, 4.0e-3, 27.0
Ls = {}
for kind in ("ideal", "mos"):
    print(f"  running pnoise kind={kind} …", flush=True)
    r = R.pnoise_kind(kind, code, vt, f0, itail, temp)
    Ls[kind] = r
    if r:
        parts = " ".join(f"L({o/1e3:.0f}k)={r['L'][o]:.2f}" for o in R.OFFS)
        print(f"  {kind}: f={r['f']/1e9:.3f} GHz amp={r['amp']:.3f} {parts}",
              flush=True)
    else:
        print(f"  {kind}: FAILED", flush=True)

print("\n| Offset | L ideal/MIM-like | L moscap | Δ |")
print("|---|---|---|---|")
ok = True
if Ls.get("ideal") and Ls.get("mos"):
    for o in R.OFFS:
        a, b = Ls["ideal"]["L"][o], Ls["mos"]["L"][o]
        d = b - a
        print(f"| {o/1e3:.0f} kHz | {a:.2f} | {b:.2f} | {d:+.3f} dB |")
        if abs(d) >= R.PASS_DB:
            ok = False
    print(f"\nPass (|ΔL| < {R.PASS_DB} dB): {'PASS' if ok else 'FAIL'}\n")
else:
    ok = False
    print("\nPass: FAIL (pnoise did not complete)\n")

open("out/d9_mos_pass.flag", "w").write("PASS\n" if ok else "FAIL\n")
sys.exit(0 if ok else 1)
