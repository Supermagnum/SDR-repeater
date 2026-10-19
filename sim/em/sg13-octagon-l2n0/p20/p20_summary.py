#!/usr/bin/env python3
"""Summarise the P2.0 mesh study: L and Q per variant at the VCO frequencies, step-to-step
changes, convergence verdict (both L and Q move < 2 % between the two finest steps of a
solver) and the solver comparison. Writes out/p20/summary.md and prints it.

Comparison basis: raw S-parameters (ports included), the same definition as Phase 0, so
both solvers are compared like for like. The Palace de-embedded values (port series
inductance removed, a geometric estimate) are listed separately as the design values.
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "p20")
FREQS = [2.4e9, 3.12e9, 3.5e9, 3.65e9, 4.2e9]
LIMIT = 2.0  # percent
LADDER = {  # coarse -> fine, the uniform-mesh refinement path per model
    "palace": ["pal5", "pal3", "pal2", "pal1"],               # surface-impedance conductors
    "palace_filled": ["palF3", "palF2", "palF1"],             # filled metals + via fill-factor correction
    "openems": ["oem2", "oem1", "oem07", "oem05"],
}
# Upstream anchor (gds2palace v0.8.2, more_examples/measured_vs_simulated/more_accurate_models_L6n2_v2,
# measured L6n2 vs Palace models, Q at 3.5 GHz): measured 14.92; surface + via merge (this study's
# "palace") 18.50; surface + correction 17.21; filled + correction 13.64; filled + conformal 1 um 14.05.
ANCHOR = {"measured": 14.92, "surface_merge": 18.50, "filled_corr": 13.64}
CHECKS = {"pal2o3": "order 3 at 2 um", "palamr": "AMR, 5 um start, 2 iterations"}


def load():
    runs = {}
    for p in glob.glob(os.path.join(OUT, "*.json")):
        with open(p) as fh:
            d = json.load(fh)
        runs[d["tag"]] = d
    return runs


def at(d, f, key="raw"):
    for r in d.get(key, []):
        if abs(r["requested_Hz"] - f) < 1:
            return r
    return None


def pct(a, b):
    return 100.0 * (a - b) / b


def main():
    runs = load()
    lines = ["# P2.0 mesh study — SG13_Octagon_L2n0", ""]
    if not runs:
        print("no finished steps in out/p20/")
        return
    lines += ["| Step | Solver | Cell (µm) | Order | AMR | Time (s) | " +
              " | ".join(f"L @ {f/1e9:.2f} GHz (nH) | Q @ {f/1e9:.2f}" for f in FREQS) + " |",
              "|---|---|---|---|---|---|" + "---|---|" * len(FREQS)]
    order = [t for s in LADDER.values() for t in s] + list(CHECKS)
    for tag in order + sorted(set(runs) - set(order)):
        if tag not in runs:
            continue
        d = runs[tag]
        cells = []
        for f in FREQS:
            r = at(d, f)
            cells += [f"{r['L_nH']:.4f}", f"{r['Q']:.2f}"] if r else ["—", "—"]
        lines.append(f"| {tag} | {d['solver']} | {d.get('cell_um', '—')} | {int(d['order']) if 'order' in d else '—'} | "
                     f"{int(d['amr']) if 'amr' in d else '—'} | {int(d['seconds']) if 'seconds' in d else '—'} | "
                     + " | ".join(cells) + " |")
    lines.append("")
    verdict = {}
    for solver, ladder in LADDER.items():
        done = [t for t in ladder if t in runs]
        lines.append(f"## {solver}: change between successive mesh steps (raw)")
        if len(done) < 2:
            lines += ["", "fewer than two steps finished", ""]
            continue
        lines += ["", "| From → to | " + " | ".join(f"ΔL / ΔQ @ {f/1e9:.2f} GHz (%)" for f in FREQS) + " |",
                  "|---|" + "---|" * len(FREQS)]
        worst_last = 0.0
        for a, b in zip(done, done[1:]):
            row = []
            for f in FREQS:
                ra, rb = at(runs[a], f), at(runs[b], f)
                if not (ra and rb):
                    row.append("—")
                    continue
                dl, dq = pct(rb["L_nH"], ra["L_nH"]), pct(rb["Q"], ra["Q"])
                row.append(f"{dl:+.2f} / {dq:+.2f}")
                if b == done[-1] and 3.0e9 <= f <= 4.3e9:
                    worst_last = max(worst_last, abs(dl), abs(dq))
            lines.append(f"| {a} → {b} | " + " | ".join(row) + " |")
        ok = worst_last < LIMIT
        verdict[solver] = (ok, done[-1], worst_last)
        lines += ["", f"**{solver}: {'converged' if ok else 'NOT converged'}** — last step "
                  f"{done[-2]} → {done[-1]} moves L or Q by up to {worst_last:.2f} % in 3.1–4.2 GHz "
                  f"(limit {LIMIT} %).", ""]
    # cross-checks against the finest Palace step
    fin = verdict.get("palace", (False, None, 0))[1]
    fin_f = verdict.get("palace_filled", (False, None, 0))[1]
    if fin:
        for tag, what in CHECKS.items():
            if tag in runs:
                diffs = []
                for f in FREQS:
                    ra, rb = at(runs[fin], f), at(runs[tag], f)
                    if not (ra and rb):
                        diffs.append("—")
                        continue
                    diffs.append(f"{pct(rb['L_nH'], ra['L_nH']):+.2f} / {pct(rb['Q'], ra['Q']):+.2f}")
                lines.append(f"Cross-check {tag} ({what}) vs {fin}, ΔL / ΔQ %: " + ", ".join(
                    f"{f/1e9:.2f} GHz {d}" for f, d in zip(FREQS, diffs)))
        lines.append("")
    # solver comparison at the finest steps
    for pk in ("palace", "palace_filled"):
        if pk not in verdict or "openems" not in verdict:
            continue
        p, o = runs[verdict[pk][1]], runs[verdict["openems"][1]]
        lines += [f"## Palace ({verdict[pk][1]}) vs openEMS ({verdict['openems'][1]}), raw", "",
                  "| f (GHz) | L Palace | L openEMS | ΔL (%) | Q Palace | Q openEMS | ΔQ (%) |",
                  "|---|---|---|---|---|---|---|"]
        for f in FREQS:
            rp, ro = at(p, f), at(o, f)
            if not (rp and ro):
                continue
            lines.append(f"| {f/1e9:.2f} | {rp['L_nH']:.4f} | {ro['L_nH']:.4f} | {pct(rp['L_nH'], ro['L_nH']):+.2f} | "
                         f"{rp['Q']:.2f} | {ro['Q']:.2f} | {pct(rp['Q'], ro['Q']):+.2f} |")
        lines.append("")
    # design values: finest filled-metal Palace if available (closest to measurement upstream), de-embedded
    best = fin_f or fin
    if best and "deembedded" in runs[best]:
        lines += [f"## Design values (Palace {best}, de-embedded: port series inductance removed)", "",
                  "| f (GHz) | L (nH) | Q | R (Ω) |", "|---|---|---|---|"]
        for f in FREQS:
            r = at(runs[best], f, "deembedded")
            if not r:
                continue
            lines.append(f"| {f/1e9:.2f} | {r['L_nH']:.4f} | {r['Q']:.2f} | {r['R_ohm']:.3f} |")
        lines.append("")
    if fin:
        r = at(runs[fin], 3.5e9)
        if r:
            k = ANCHOR["measured"] / ANCHOR["surface_merge"]
            lines += [f"Measurement-anchored estimate: surface-model Q × {k:.3f} (upstream L6n2 measured / same model) "
                      f"= {r['Q'] * k:.2f} at 3.5 GHz from {fin}. Indicative only: L6n2 is a different coil.", ""]
    lines += ["Phase 0 baseline for reference (raw): Palace 5 µm 1.664 nH / Q 18.7 and openEMS 1 µm 1.641 nH / "
              "Q 14.9 at 3.5 GHz; provisional design Q 14.9.", ""]
    text = "\n".join(lines)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "summary.md"), "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
