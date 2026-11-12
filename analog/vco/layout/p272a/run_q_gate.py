#!/usr/bin/env python3
"""P2.7.2a3 inductor Q gate: mesh1 ΔQ, then swing + PN if |ΔQ| ≥ 2 %.

Series-R scaled so tank Q drops by dq_frac. Results [SCH] + [EM] for ΔQ.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(HERE, "out", "q_gate")
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step2"))
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step3"))
import run_step2 as S2  # noqa: E402
import run_step3 as S3  # noqa: E402

S2.OUT = OUT
S3.OUT = OUT

DQ_FRAC = 0.0363  # mesh1 worst |ΔQ| @ 3.5 GHz [EM]
PASS_SWING = 0.54
MESH1 = os.path.join(
    REPO, "sim/em/sg13-octagon-l2n0/tapped/review/em_summary_p272a2_mesh1.md"
)


def install_scaled_inductor(dq_frac: float) -> None:
    src = os.path.join(REPO, "analog", "vco", "models", "l2n0_lumped.inc")
    scale = 1.0 / (1.0 - dq_frac)
    text = open(src).read()

    def repl(m):
        return f"r={float(m.group(1)) * scale:.6g}"

    text = re.sub(r"r=([0-9.eE+-]+)", repl, text)
    scaled = os.path.join(OUT, "l2n0_lumped_qscaled.inc")
    open(scaled, "w").write(
        f"// Q-scaled: R × {scale:.6g} for ΔQ={-100 * dq_frac:.2f} % [EM]\n" + text
    )

    def noisy_inductor():
        t = open(scaled).read()
        t = re.sub(r"(resistor r=[^\s]+)", r"\1 noisy=1", t)
        dst = os.path.join(OUT, "l2n0_lumped_noisy.inc")
        open(dst, "w").write(
            f"// noisy Q-scaled lumped P2.7.2a3 (ΔQ={-100 * dq_frac:.2f} %)\n" + t
        )
        return dst

    S2.noisy_inductor = noisy_inductor


def swing_ff_mim_worst():
    S3.set_corner("mos_ff", "cap_wcs")
    S3.load_sizing()
    itail = S2.I_MAX
    code = S2.CMAX
    m = S3.tran(code, 0.3, "swing_ff_wcs_85_topdac", itail, 85)
    amp = m["amp"]
    print(
        "## Bottom-band swing [SCH]\n"
        f"- mos_ff / cap_wcs / 85 °C; code {code}; I_tail {itail * 1e3:.2f} mA\n"
        f"- Amp = {amp:.4f} V diff; pass ≥ {PASS_SWING} V → "
        f"{'PASS' if amp >= PASS_SWING else 'FAIL'}\n"
        f"- f = {m['f'] / 1e9:.4f} GHz\n"
    )
    return amp


def pn_worst():
    S3.set_corner("mos_ss", "cap_typ")
    _r, meas = S3.load_sizing()
    f0 = 4.20e9
    temp = 85
    tag = "pn_ss_typ_85_4p20"
    itail = S3.itail_for(f0, meas)
    code = S3.code_for(f0, temp, tag)
    m = S3.tran(code, S2.VTUNE_MID, f"{tag}_chk", itail, temp)
    print(
        "## Worst-corner PN [SCH]\n"
        f"- mos_ss / cap_typ / 85 °C; code {code}, f={m['f'] / 1e9:.4f} GHz, "
        f"Amp={m['amp']:.3f} V, I_tail={itail * 1e3:.2f} mA\n"
    )
    pn = S3.pnoise(code, S2.VTUNE_MID, m["f"], itail, temp, tag)
    if pn is None:
        print("PSS/pnoise failed\n")
        return None, False
    margins = []
    for band, lim in S3.LIMITS.items():
        lo, hi = (3.12e9, 4.20e9) if band == "VHF" else (3.20e9, 3.84e9)
        if lo - 30e6 <= pn["f"] <= hi + 30e6:
            for o, limv in lim.items():
                if o in pn["L"]:
                    margins.append((limv - pn["L"][o], band, o, pn["L"][o], limv))
    print("| band offset | L | limit | margin |")
    print("|---|---|---|---|")
    for marg, band, o, L, limv in sorted(margins, key=lambda x: x[0]):
        print(f"| {band} {o / 1e6:g} MHz | {L:.1f} | {limv:.1f} | {marg:+.1f} dB |")
    worst = min(margins) if margins else None
    ok = worst is not None and worst[0] > 0
    print(
        f"\nWorst margin: {worst[0]:+.1f} dB → {'PASS' if ok else 'FAIL'} [SCH]\n"
        if worst
        else "\nNo margins\n"
    )
    return (worst[0] if worst else None), ok


def main():
    print("# P2.7.2a3 inductor Q gate\n")
    if os.path.isfile(MESH1):
        print(f"mesh1: {MESH1}")
        print("ΔQ source: mesh1 EM worst −3.63 % @ 3.5 GHz [EM]\n")
        dq = DQ_FRAC
    else:
        print("mesh1 missing — fallback ΔQ = −3.8 % [decisions]\n")
        dq = 0.038
    install_scaled_inductor(dq)
    if dq < 0.02:
        summary = f"PASS: ΔQ=−{100 * dq:.2f}% < 2%\n"
        print(summary)
        open(os.path.join(OUT, "summary_q_gate.txt"), "w").write(summary)
        return 0
    print(f"ΔQ ≥ 2 % → swing + PN with R scale for −{100 * dq:.2f} %\n")
    amp = swing_ff_mim_worst()
    margin, pn_ok = pn_worst()
    swing_ok = amp >= PASS_SWING
    ok = swing_ok and pn_ok
    summary = (
        f"# P2.7.2a3 Q gate\n"
        f"- ΔQ = −{100 * dq:.2f} % (mesh1 worst @ 3.5 GHz) [EM]\n"
        f"- Swing ff/cap_wcs/85 I_tail={S2.I_MAX * 1e3:.0f} mA: {amp:.4f} V "
        f"({'PASS' if swing_ok else 'FAIL'} ≥ {PASS_SWING}) [SCH]\n"
        f"- PN worst margin: "
        f"{'n/a' if margin is None else f'{margin:+.1f} dB'} "
        f"({'PASS' if pn_ok else 'FAIL'} > 0) [SCH]\n"
        f"- Gate: {'PASS' if ok else 'FAIL'}\n"
    )
    print(summary)
    open(os.path.join(OUT, "summary_q_gate.txt"), "w").write(summary)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
