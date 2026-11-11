#!/usr/bin/env python3
"""One-line Amp +0.06 V check vs 25-Oct archive [SCH]."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step2"))
import run_step2 as S2

S2.OUT = OUT
arch = json.load(open(os.path.join(REPO, "analog", "vco", "step2", "out",
                                   "range_2026-10-25.json")))
cur = json.load(open(os.path.join(REPO, "analog", "vco", "step2", "out",
                                  "range.json")))
S2.LSB_FF, S2.C_FIX_FF, S2.NFING = cur["lsb"], cur["cfix"], cur["nfing"]
S2.TRIM[:len(cur["trim"])] = cur["trim"]
S2.NBITS = cur.get("nbits", 8)
S2.CMAX = (1 << S2.NBITS) - 1
it, vt, code = 4e-3, 0.65, 0


def meas(tag, **kw):
    path = S2.netlist(
        f"ampnote_{tag}", code, vt,
        '  options temp=27 reltol=1e-4 rawfile="binary"\n'
        "  save v(tp) v(tn) v(tail)\n"
        "  analysis tr tran stop=60n step=5p maxstep=5p\n",
        itail=it, **kw,
    )
    S2.run(path)
    return S2.measure(os.path.join(OUT, "tr.raw"))


a_arch = arch["meas"]["0,0.65"]["amp"]
m_bp = meas("bp", bypass=True)
m_nobp = meas("nobp", bypass=False)
m_nobuf = meas("nobuf", bypass=False, standin_buffer=False)
print("# Amp +0.06 V note [SCH]\n")
print(f"Archive Amp c0/0.65 @4 mA: {a_arch:.4f} V")
print(f"Today binary-bypass on:      {m_bp['amp']:.4f} V  "
      f"(Δ {m_bp['amp'] - a_arch:+.4f})")
print(f"Today bypass off:            {m_nobp['amp']:.4f} V  "
      f"(Δ {m_nobp['amp'] - a_arch:+.4f})")
print(f"Today nobp, no stand-in buf: {m_nobuf['amp']:.4f} V  "
      f"(Δ {m_nobuf['amp'] - a_arch:+.4f})")
# Plain step2 has no D22 DAC; delta with bypass off ⇒ not bypass C.
if abs(m_nobp["amp"] - a_arch) > 0.03:
    print("\nConclusion: +Amp vs archive remains with bypass off in plain "
          "step2 (no D22 DAC). Likely tank/load deck drift since 25-Oct "
          "(sizing/trim/stand-in buffer), not start-up bypass. D22 sets Amp "
          "in operation.")
else:
    print("\nConclusion: Amp delta largely gone with current sizing; prior "
          "+0.06 V was with the equal-size bypass baseline.")
