#!/usr/bin/env python3
"""P2.7.2c — trim fixed tank C to absorb PEX + direct-pack island parasitics [SCH].

Parasitics per side (conservative highs):
  core extract     23.66 fF [PEX-RC]  (p272b summary_pex_core_tank; no-L)
  bank wiring      36.87 fF [PEX-RC]  (p272b_bank summary_pex_bank; coupling-only)
  island (direct)  37.00 fF [HAND]    (decisions 2026-11-17; use 37)
  series R          2.0  Ω  [HAND]    (shorter direct pack vs prior 3.4 Ω)

Fixed C today: cfix = 192 fF differential → 2×16 µm rfcmim [SCH/PDK].

Sweep legal square rfcmim sides (0.5 µm steps, ≥ 2 µm [PDK practice]), set
C_FIX_FF = 0.5 * side² * 1.5, with parasitics attached. Pick the size that
balances |top_margin − bot_margin| while both ≥ 40 MHz. Then re-check overlap
pairs at least-overlap corners and a single worst-corner swing (tran amp).

D20 / full pnoise: heavy; run only a light D20 land call if band+overlap pass,
and one pnoise spot if time — else report deferred.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "step2"))
import run_step2 as S2  # noqa: E402
import run_step3 as S3  # noqa: E402
from run_p272c_gate import V_SS, _patch_vdd  # noqa: E402

C_CORE_FF = 23.66
C_BANK_FF = 36.87
C_ISLAND_FF = 37.00
C_SIDE_FF = C_CORE_FF + C_BANK_FF + C_ISLAND_FF  # 97.53
R_SERIES = 2.0
C_FIX_TODAY = 192.0
SIDE_TODAY = 16.0
CAP_AREA = 1.5
MARGIN_MIN = 40e6  # Hz
F_TOP = 4.20e9
F_BOT = 3.12e9

PARASITIC_EXTRA = (
    f"Rr_p (tp nr_p) resistor r={R_SERIES}\n"
    f"Cr_p (nr_p 0) capacitor c={C_SIDE_FF}f\n"
    f"Rr_n (tn nr_n) resistor r={R_SERIES}\n"
    f"Cr_n (nr_n 0) capacitor c={C_SIDE_FF}f\n"
)

CASES = [
    ("top", "mos_ss", "cap_wcs", -40, 0, 1.0),
    ("bot", "mos_ss", "cap_bcs", -40, None, 0.3),
]


def cfix_from_side(side_um: float) -> float:
    """Differential C_FIX from two series square rfcmim of side_um."""
    return 0.5 * (side_um * side_um * CAP_AREA)


def legal_sides(cfix_min: float = 20.0, cfix_max: float = 192.0):
    """Square rfcmim sides on 0.5 µm grid, cfix in [min,max]."""
    s_lo = math.ceil(math.sqrt(2 * cfix_min / CAP_AREA) * 2) / 2
    s_hi = math.floor(math.sqrt(2 * cfix_max / CAP_AREA) * 2) / 2
    s = max(2.0, s_lo)  # keep ≥ 2 µm
    out = []
    while s <= s_hi + 1e-9:
        out.append(round(s, 2))
        s += 0.5
    return out


def run_case(tag, mos, cap, temp, code, vt, cfix, itail_tab, extra=""):
    # Do not call load_sizing() here — it resets C_FIX_FF from range.json.
    S2.C_FIX_FF = cfix
    if code is None:
        code = S2.CMAX
    itail = S3.itail_for(4.4e9 if tag == "top" else 2.95e9, itail_tab)
    S3.set_corner(mos, cap)
    S2.C_FIX_FF = cfix  # set_corner is fine; keep explicit
    title = f"trim_{'par' if extra else 'base'}_{tag}_{cfix:.0f}"
    sim = S2.netlist(
        title, code, vt, itail=itail,
        analysis=(f"  options temp={temp}\n  save v(tp) v(tn) v(tail)\n"
                  "  analysis tr tran stop=60n step=5p maxstep=5p"),
        vct=V_SS, extra=extra)
    _patch_vdd(sim, V_SS)
    S2.run(sim)
    return S2.measure(os.path.join(OUT, "tr.raw"))


def margins_at(cfix: float, itail_tab, with_par: bool):
    extra = PARASITIC_EXTRA if with_par else ""
    out = {}
    for tag, mos, cap, temp, code, vt in CASES:
        m = run_case(tag, mos, cap, temp, code, vt, cfix, itail_tab, extra=extra)
        if tag == "top":
            margin = m["f"] - F_TOP
        else:
            margin = F_BOT - m["f"]
        out[tag] = dict(f=m["f"], amp=m["amp"], margin=margin)
    return out


def main():
    S2.OUT = S3.OUT = OUT
    _, itail_tab = S3.load_sizing()
    lines = [
        "# P2.7.2c trim fixed tank C for PEX + direct-pack parasitics [SCH]\n\n",
        "## Parasitic budget per side\n\n",
        f"| term | C (fF) | tag |\n|---|---:|---|\n",
        f"| core (max side) | {C_CORE_FF:.2f} | [PEX-RC] |\n",
        f"| bank wiring (max side) | {C_BANK_FF:.2f} | [PEX-RC] |\n",
        f"| island direct pack | {C_ISLAND_FF:.2f} | [HAND] |\n",
        f"| **total** | **{C_SIDE_FF:.2f}** | |\n",
        f"| series R | {R_SERIES:.1f} Ω | [HAND] |\n\n",
        f"Fixed C today: **{C_FIX_TODAY:.0f} fF** differential "
        f"({SIDE_TODAY:.0f} µm square ×2) [SCH/PDK].\n\n",
    ]
    print("".join(lines), flush=True)

    # Baseline: today's C_FIX with parasitics
    print("## Baseline (cfix=192) with parasitics\n", flush=True)
    base = margins_at(C_FIX_TODAY, itail_tab, True)
    for tag in ("top", "bot"):
        r = base[tag]
        print(f"  {tag}: f={r['f']/1e9:.3f} GHz margin={r['margin']/1e6:.1f} MHz "
              f"Amp={r['amp']:.2f}", flush=True)
        lines.append(
            f"- baseline {tag} cfix=192 +par: f={r['f']/1e9:.3f} GHz "
            f"margin={r['margin']/1e6:.1f} MHz Amp={r['amp']:.2f} [SCH]\n")

    if base["top"]["margin"] < MARGIN_MIN:
        lines.append(
            f"\nBaseline top margin {base['top']['margin']/1e6:.1f} MHz "
            f"< 40 MHz — trim must raise top [SCH].\n")

    # First-order target: cfix' ≈ cfix − C_side (same units as differential load)
    target = max(20.0, C_FIX_TODAY - C_SIDE_FF)
    print(f"\nFirst-order target cfix ≈ {target:.1f} fF\n", flush=True)
    lines.append(f"\nFirst-order target cfix ≈ {target:.1f} fF "
                 f"(192 − {C_SIDE_FF:.1f}) [HAND].\n\n")

    # Balance is expected above the first-order target (top still rich at ~100 fF).
    sides = legal_sides(90.0, 192.0)
    print(f"Sweep sides: {sides}\n", flush=True)
    lines.append("## Sweep (with parasitics) [SCH]\n\n")
    lines.append(
        "| side (µm) | cfix (fF) | top mar (MHz) | bot mar (MHz) | "
        "|Δ| (MHz) | Amp top/bot | both≥40 |\n"
        "|---:|---:|---:|---:|---:|---|---|\n")

    best = None
    rows = []
    for side in sides:
        cfix = cfix_from_side(side)
        m = margins_at(cfix, itail_tab, True)
        top_m, bot_m = m["top"]["margin"], m["bot"]["margin"]
        bal = abs(top_m - bot_m)
        ok = (top_m >= MARGIN_MIN) and (bot_m >= MARGIN_MIN)
        row = (side, cfix, top_m, bot_m, bal, m["top"]["amp"], m["bot"]["amp"], ok)
        rows.append(row)
        print(
            f"  side={side:.1f} cfix={cfix:.1f} top={top_m/1e6:.1f} "
            f"bot={bot_m/1e6:.1f} |Δ|={bal/1e6:.1f} ok={ok}",
            flush=True)
        lines.append(
            f"| {side:.1f} | {cfix:.1f} | {top_m/1e6:.1f} | {bot_m/1e6:.1f} | "
            f"{bal/1e6:.1f} | {m['top']['amp']:.2f}/{m['bot']['amp']:.2f} | "
            f"{'yes' if ok else 'no'} |\n")
        if ok:
            if best is None or bal < best[4]:
                best = row

    lines.append("\n## Selection\n\n")
    if best is None:
        # report closest even if fail
        cand = min(rows, key=lambda r: (
            0 if r[7] else 1,
            max(0, MARGIN_MIN - r[2]) + max(0, MARGIN_MIN - r[3]),
            r[4]))
        lines.append(
            f"**FAIL:** no legal size with both margins ≥ 40 MHz [SCH]. "
            f"Closest: side={cand[0]:.1f} µm cfix={cand[1]:.1f} fF "
            f"top={cand[2]/1e6:.1f} bot={cand[3]/1e6:.1f} MHz.\n")
        if cand[1] < C_SIDE_FF * 0.5:
            lines.append(
                "Fixed capacitor too small relative to parasitics — finding "
                "to owner (decision 2026-11-17).\n")
        path = os.path.join(OUT, "summary_p272c_trim_fixed_c.txt")
        open(path, "w").writelines(lines)
        dest = os.path.join(
            HERE, "..", "layout", "p272c", "out", "summary_p272c_trim_fixed_c.txt")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "w").writelines(lines)
        print("FAIL — wrote", path, flush=True)
        return 1

    side, cfix, top_m, bot_m, bal, at, ab, _ = best
    lines.append(
        f"**PASS pick:** side=**{side:.1f} µm**, cfix=**{cfix:.1f} fF** "
        f"(was {C_FIX_TODAY:.0f}), top margin {top_m/1e6:.1f} MHz, "
        f"bot {bot_m/1e6:.1f} MHz, |Δ|={bal/1e6:.1f} MHz [SCH].\n")
    print(f"\nPASS pick side={side} cfix={cfix:.1f}\n", flush=True)

    # Overlap spot-check at carry codes (ss/wcs/−40 and ss/bcs/−40)
    lines.append("\n## Band overlap spot (neighbouring codes) [SCH]\n\n")
    S2.C_FIX_FF = cfix
    pairs = [(0, 1), (31, 32), (127, 128), (254, 255)]
    lines.append("| corner | pair | f0 | f1 | step (MHz) | ok |\n")
    lines.append("|---|---|---:|---:|---:|---|\n")
    overlap_ok = True

    def tran_code(mos, cap, temp, code, vt, itail, tag):
        S3.set_corner(mos, cap)
        S2.C_FIX_FF = cfix
        sim = S2.netlist(
            tag, code, vt, itail=itail,
            analysis=(f"  options temp={temp}\n  save v(tp) v(tn) v(tail)\n"
                      "  analysis tr tran stop=60n step=5p maxstep=5p"),
            vct=V_SS, extra=PARASITIC_EXTRA)
        _patch_vdd(sim, V_SS)
        S2.run(sim)
        return S2.measure(os.path.join(OUT, "tr.raw"))

    for mos, cap, temp in (("mos_ss", "cap_wcs", -40), ("mos_ss", "cap_bcs", -40)):
        it = S3.itail_for(3.6e9, itail_tab)
        for c0, c1 in pairs:
            a = tran_code(mos, cap, temp, c0, 0.65, it, f"ov_{c0}")
            b = tran_code(mos, cap, temp, c1, 0.65, it, f"ov_{c1}")
            step = a["f"] - b["f"]
            ok = step > 0
            overlap_ok = overlap_ok and ok
            lines.append(
                f"| {mos}/{cap}/{temp} | {c0}→{c1} | {a['f']/1e9:.4f} | "
                f"{b['f']/1e9:.4f} | {step/1e6:.2f} | "
                f"{'yes' if ok else 'NO'} |\n")
            print(f"  overlap {mos} {c0}->{c1} step={step/1e6:.2f} MHz ok={ok}",
                  flush=True)
    lines.append(
        f"\nOverlap monotonicity at Vtune=0.65: "
        f"{'PASS' if overlap_ok else 'FAIL'} [SCH].\n")
    lines.append(
        "D20 V_tune landing (0.25–0.95) and worst-corner pnoise are re-run "
        "next if bands+overlap pass (separate invocations).\n")

    gate = True  # band margins already ok by selection
    lines.append(
        f"\n## Gate\n\n"
        f"- Band margins ≥ 40 MHz both ends: PASS [SCH]\n"
        f"- Overlap monotonic: {'PASS' if overlap_ok else 'FAIL'} [SCH]\n"
        f"- D20 0.25–0.95 landing: **not re-run this job** [TOOL]\n"
        f"- Worst-corner pnoise: **not re-run this job** [TOOL]\n"
        f"- Overall step-3 trim gate (bands+overlap): "
        f"{'PASS' if (gate and overlap_ok) else 'FAIL'}\n")

    path = os.path.join(OUT, "summary_p272c_trim_fixed_c.txt")
    open(path, "w").writelines(lines)
    dest = os.path.join(
        HERE, "..", "layout", "p272c", "out", "summary_p272c_trim_fixed_c.txt")
    open(dest, "w").writelines(lines)
    # machine-readable pick
    pick = os.path.join(OUT, "trim_fixed_c_pick.json")
    import json
    json.dump(dict(
        side_um=float(side), cfix_ff=float(cfix), c_side_ff=float(C_SIDE_FF),
        top_margin_mhz=float(top_m / 1e6), bot_margin_mhz=float(bot_m / 1e6),
        overlap_ok=bool(overlap_ok),
        sources=dict(core=C_CORE_FF, bank=C_BANK_FF, island=C_ISLAND_FF),
    ), open(pick, "w"), indent=2)
    print(f"Wrote {path}\nWrote {pick}", flush=True)
    return 0 if (gate and overlap_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
