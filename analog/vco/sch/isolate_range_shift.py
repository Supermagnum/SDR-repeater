#!/usr/bin/env python3
"""P2.7.1b: isolate post-25-Oct VCO range shift vs archived range.json.

Archived circuit (25 Oct file mtime): no start-up bypass MOS in run_step2.
Today: bypass_groups bank+var+tail default on (off-state). D22 det/DAC are
ampcal injections, not in plain step2 — measured separately.
"""
from __future__ import annotations

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step2"))
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step1"))
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "ampcal"))

import run_step2 as S2
import amp_common as A

RANGE_JSON = os.path.join(REPO, "analog", "vco", "step2", "out", "range.json")
CODES = (0, 128, 255)
VT = 0.65


def load_sizing():
    rng = json.load(open(RANGE_JSON))
    S2.LSB_FF = rng["lsb"]
    S2.C_FIX_FF = rng["cfix"]
    S2.NFING = rng.get("nfing", 20)
    S2.NBITS = rng.get("nbits", 8)
    S2.TRIM = list(rng["trim"]) + [1.0] * 8
    S2.OUT = OUT
    return rng


def measure_cfg(tag, **kw):
    """Run three codes with netlist kwargs; return {code: {f, amp}}."""
    itail = kw.pop("itail")
    results = {}
    for code in CODES:
        path = S2.netlist(
            f"isol_{tag}_c{code}",
            code,
            VT,
            '  options temp=27 reltol=1e-4 rawfile="binary"\n'
            '  save v(tp) v(tn) v(tail)\n'
            '  analysis tr tran stop=60n step=5p maxstep=5p\n',
            itail=itail,
            **kw,
        )
        S2.run(path)
        m = S2.measure(os.path.join(OUT, "tr.raw"))
        results[code] = {"f": m["f"], "amp": m["amp"]}
        print(f"  {tag} c{code}: f={m['f']/1e9:.4f} GHz Amp={m['amp']:.4f} V")
    return results


def inject_det_only(path, code):
    text = open(path).read()
    text = text.replace("\ncontrol\n", "\n" + A.detector_snippet(True) + "\ncontrol\n")
    open(path, "w").write(text)


def inject_dac_only(path, code):
    # Use mid-band-ish bias code from Amp target; for range isolation use code 14
    A.inject_dac_det(path, bias_code=14, det=False)


def inject_dac_det(path, code):
    A.inject_dac_det(path, bias_code=14, det=True)


def main():
    rng = load_sizing()
    itail = rng["itail"]
    ref = {c: rng["meas"][f"{c},{VT}"] for c in CODES}

    # PDK / container
    pdk_commit = open("/foss/pdks/ihp-sg13g2/COMMIT").read().strip()
    lines = [
        "# P2.7.1b VCO range shift isolation [SCH]\n\n",
        f"PDK COMMIT: `{pdk_commit}` (pinned target a49358cc)\n",
        f"Container: hpretl/iic-osic-tools:2026.10\n",
        f"Archived range.json mtime 2026-10-25; itail={itail*1e3:.3f} mA; "
        f"lsb={S2.LSB_FF:.4f} fF; cfix={S2.C_FIX_FF:.3f} fF; nbits={S2.NBITS}\n\n",
    ]

    # 1) Total shift: today's default vs archive
    print("## today_default")
    today = measure_cfg(
        "today",
        itail=itail,
        bypass=True,
        bypass_groups=("tail", "bank", "var"),
        standin_buffer=True,
    )

    lines.append("## 1. Total shift — today's deck vs range.json (tt 27 °C, V_tune 0.65 V)\n\n")
    lines.append("| code | f_arch [SCH] | f_today [SCH] | Δf (MHz) | Δf (%) | Amp_arch | Amp_today | ΔA (V) |\n")
    lines.append("|---|---|---|---|---|---|---|---|\n")
    for c in CODES:
        fa, ft = ref[c]["f"], today[c]["f"]
        df = ft - fa
        dfp = 100.0 * df / fa
        da = today[c]["amp"] - ref[c]["amp"]
        lines.append(
            f"| {c} | {fa/1e9:.4f} GHz | {ft/1e9:.4f} GHz | {df/1e6:.2f} | "
            f"{dfp:.3f} | {ref[c]['amp']:.4f} | {today[c]['amp']:.4f} | {da:.4f} |\n"
        )
    lines.append("\n")

    # 2) Archive-equivalent: no bypass
    print("## no_bypass (25-Oct style)")
    base = measure_cfg("nobp", itail=itail, bypass=False, standin_buffer=True)

    lines.append("## 2. 25-Oct-style circuit (bypass=False) vs archive\n\n")
    lines.append("| code | f_arch | f_nobp | Δf (MHz) | Δf (%) |\n|---|---|---|---|---|\n")
    for c in CODES:
        fa, fb = ref[c]["f"], base[c]["f"]
        lines.append(
            f"| {c} | {fa/1e9:.4f} | {fb/1e9:.4f} | {(fb-fa)/1e6:.2f} | "
            f"{100*(fb-fa)/fa:.3f} |\n"
        )
    lines.append(
        "\nIf nobp ≈ archive, the shift is from post-25-Oct additions, not PDK/tool.\n\n"
    )

    # 3) One addition at a time from nobp baseline
    configs = [
        ("bank_bypass", dict(bypass=True, bypass_groups=("bank",), standin_buffer=True)),
        ("var_bypass", dict(bypass=True, bypass_groups=("var",), standin_buffer=True)),
        ("tail_bypass", dict(bypass=True, bypass_groups=("tail",), standin_buffer=True)),
        ("all_bypass", dict(bypass=True, bypass_groups=("tail", "bank", "var"),
                            standin_buffer=True)),
        ("no_standin", dict(bypass=False, standin_buffer=False)),
    ]

    measured = {"nobp": base, "today": today}
    for name, kw in configs:
        print(f"## {name}")
        measured[name] = measure_cfg(name, itail=itail, **kw)

    # D22 injections on nobp base (copy path approach: measure with inject hook)
    # Re-implement via netlist + inject
    def meas_inject(tag, inject_fn, bypass=False, groups=()):
        results = {}
        for code in CODES:
            path = S2.netlist(
                f"isol_{tag}_c{code}",
                code,
                VT,
                '  options temp=27 reltol=1e-4 rawfile="binary"\n'
                '  save v(tp) v(tn) v(tail)\n'
                '  analysis tr tran stop=60n step=5p maxstep=5p\n',
                itail=itail,
                bypass=bypass,
                bypass_groups=groups if groups else ("tail",),
                standin_buffer=True,
            )
            inject_fn(path, code)
            S2.run(path)
            m = S2.measure(os.path.join(OUT, "tr.raw"))
            results[code] = {"f": m["f"], "amp": m["amp"]}
            print(f"  {tag} c{code}: f={m['f']/1e9:.4f} Amp={m['amp']:.4f}")
        return results

    print("## det_on_nobp")
    measured["det"] = meas_inject("det", inject_det_only, bypass=False)
    print("## dac_on_nobp")
    measured["dac"] = meas_inject("dac", inject_dac_only, bypass=False)
    print("## dac_det_today")
    measured["dac_det"] = meas_inject(
        "dacdet", inject_dac_det, bypass=True, groups=("tail", "bank", "var"))

    lines.append(
        "## 3. Addition → Δf vs nobp baseline (MHz) [SCH]\n\n"
        "Δf = f(config) − f(nobp). Sum of bank+var+tail should ≈ all_bypass − nobp.\n\n"
        "| addition | Δf c0 (MHz) | Δf c128 | Δf c255 | notes |\n"
        "|---|---|---|---|---|\n"
    )

    def drow(name, note=""):
        row = f"| {name} |"
        for c in CODES:
            df = (measured[name][c]["f"] - base[c]["f"]) / 1e6
            row += f" {df:.2f} |"
        row += f" {note} |\n"
        return row

    lines.append(drow("bank_bypass", "off-state MOS on bank bias R"))
    lines.append(drow("var_bypass", "off-state MOS on var bias R"))
    lines.append(drow("tail_bypass", "off-state MOS across rbf"))
    lines.append(drow("all_bypass", "today step2 default"))
    lines.append(drow("no_standin", "remove stand-in CML buffer"))
    lines.append(drow("det", "D22 detector on tank (ampcal)"))
    lines.append(drow("dac", "D22 OTA DAC replaces iref/mt"))
    lines.append(drow("dac_det", "DAC+det on today's bypass deck"))
    lines.append(drow("today", "same as all_bypass"))

    # Sum check
    lines.append("\n### Sum check (bypass parts vs all_bypass)\n\n")
    lines.append("| code | bank+var+tail (MHz) | all_bypass (MHz) | residual (MHz) |\n|---|---|---|---|\n")
    for c in CODES:
        s = sum(
            (measured[k][c]["f"] - base[c]["f"]) / 1e6
            for k in ("bank_bypass", "var_bypass", "tail_bypass")
        )
        a = (measured["all_bypass"][c]["f"] - base[c]["f"]) / 1e6
        lines.append(f"| {c} | {s:.2f} | {a:.2f} | {a-s:.2f} |\n")

    lines.append(
        "\n### vs archive residual after nobp\n\n"
        "If nobp still differs from archive, residual is tool/model (not circuit).\n\n"
        "| code | archive−nobp (MHz) | archive−today (MHz) |\n|---|---|---|\n"
    )
    for c in CODES:
        lines.append(
            f"| {c} | {(ref[c]['f']-base[c]['f'])/1e6:.2f} | "
            f"{(ref[c]['f']-today[c]['f'])/1e6:.2f} |\n"
        )

    path = os.path.join(OUT, "summary_range_shift.txt")
    open(path, "w").write("".join(lines))
    # also JSON for later
    dump = {
        "ref": {str(c): ref[c] for c in CODES},
        "measured": {
            k: {str(c): v[c] for c in CODES} for k, v in measured.items()
        },
        "pdk": pdk_commit,
        "itail": itail,
    }
    open(os.path.join(OUT, "range_shift.json"), "w").write(json.dumps(dump, indent=2))
    print("wrote", path)
    print("".join(lines))


if __name__ == "__main__":
    main()
