#!/usr/bin/env python3
"""DRC + KLayout LVS + netgen for vco_xc_pair; PNG/SVG render."""
from __future__ import annotations

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CELL = "vco_xc_pair"
GDS = os.path.join(OUT, f"{CELL}.gds")
SPICE = os.path.join(OUT, f"{CELL}.spice")
PDK_DRC = "/foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py"
PDK_LVS = "/foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/lvs/run_lvs.py"
NETGEN_SETUP = "/foss/pdks/ihp-sg13g2/libs.tech/netgen/ihp-sg13g2_setup.tcl"
DENSITY = {"AFil.g", "GFil.g", "M1.j", "M2.j", "M3.j", "M4.j", "M5.j",
           "TM1.c", "TM2.c", "TM1.d", "TM2.d"}


def run(cmd, log, timeout=3600):
    print("+", " ".join(cmd), flush=True)
    with open(log, "w") as fh:
        r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout)
    print(f"  exit {r.returncode}; log {log}", flush=True)
    return r.returncode


def parse_violated(log_path):
    txt = open(log_path, errors="ignore").read()
    m = re.search(r"Violated rules are : (\{[^}]+\})", txt)
    if not m:
        return set()
    return set(re.findall(r"'([^']+)'", m.group(1)))


def render():
    py = os.path.join(OUT, "_klayout_shot_pair.py")
    open(py, "w").write(r'''
import pya, os
gds = os.path.join(out, name + ".gds")
ly = pya.Layout(); ly.read(gds)
bb = ly.top_cell().bbox()
lv = pya.LayoutView()
lv.show_layout(ly, False)
lv.max_hier()
lv.zoom_fit()
png = os.path.join(out, name + ".png")
try:
    lv.save_image(png, 1600, 1200)
except Exception as e:
    open(os.path.join(out, name + "_png_err.txt"), "w").write(str(e))
w = max(bb.width(), 1); h = max(bb.height(), 1)
scale = min(780.0 / w, 560.0 / h)
ow, oh = w * scale, h * scale
open(os.path.join(out, name + ".svg"), "w").write(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600">'
    f'<rect x="10" y="20" width="{ow:.1f}" height="{oh:.1f}" '
    f'fill="none" stroke="black" stroke-width="1"/>'
    f'<text x="10" y="14" font-size="12">{name} bbox {bb} dbu</text>'
    f'</svg>\n')
print("rendered", name, "bbox", bb)
''')
    run(["klayout", "-b", "-r", py, "-rd", f"out={OUT}", "-rd", f"name={CELL}"],
        os.path.join(OUT, f"render_{CELL}.log"), timeout=120)


def main():
    lines = ["# P2.7.2b re-spin — vco_xc_pair DRC / LVS\n\n"]
    if not os.path.exists(GDS):
        lines.append("MISSING GDS\n")
        open(os.path.join(OUT, "summary_pair_drc_lvs.txt"), "w").writelines(lines)
        return 1

    drc_dir = os.path.join(OUT, f"drc_{CELL}")
    os.makedirs(drc_dir, exist_ok=True)
    run([
        "python3", PDK_DRC, f"--path={GDS}", f"--topcell={CELL}",
        f"--run_dir={drc_dir}", "--density",
    ], os.path.join(OUT, f"drc_{CELL}.log"))
    viol = parse_violated(os.path.join(OUT, f"drc_{CELL}.log"))
    hard = sorted(viol - DENSITY)
    dens = sorted(viol & DENSITY)
    lines.append(f"## DRC\n- violated: {sorted(viol) or 'none'}\n")
    lines.append(f"- density (waived): {dens or 'none'}\n")
    lines.append(f"- hard: {hard or 'none'} → {'PASS' if not hard else 'FAIL'}\n\n")

    lvs_dir = os.path.join(OUT, f"lvs_{CELL}")
    os.makedirs(lvs_dir, exist_ok=True)
    run([
        "python3", PDK_LVS, f"--layout={GDS}", f"--netlist={SPICE}",
        f"--topcell={CELL}", f"--run_dir={lvs_dir}",
        "--disable_tap_extraction", "--ignore_top_ports_mismatch",
        "--combine_devices", "--top_lvl_pins",
    ], os.path.join(OUT, f"lvs_{CELL}.log"))
    lvs_txt = open(os.path.join(OUT, f"lvs_{CELL}.log"), errors="ignore").read()
    lvs_ok = "| Status           | PASS" in lvs_txt or "Congratulations! Netlists match" in lvs_txt
    lines.append(f"## KLayout LVS\n- {'PASS' if lvs_ok else 'FAIL'}\n")
    ext = None
    for root, _, fs in os.walk(lvs_dir):
        for f in fs:
            if f.endswith("_extracted.cir"):
                ext = os.path.join(root, f)
    if ext:
        lines.append(f"- extracted: `{ext}`\n")
        lines.append("```\n" + open(ext).read() + "```\n")

    # netgen: lvs {sch file cell} {lay file cell} setup json  (bank_unit order)
    if ext:
        tcl = os.path.join(OUT, f"netgen_{CELL}.tcl")
        json_out = os.path.join(OUT, f"netgen_{CELL}.json")
        ng_log = os.path.join(OUT, f"netgen_{CELL}.log")
        open(tcl, "w").write(
            f"lvs {{{SPICE} {CELL}}} {{{ext} {CELL}}} {NETGEN_SETUP} {json_out}\n")
        run(["netgen", "-batch", "source", tcl], ng_log, timeout=300)
        ng = open(ng_log, errors="ignore").read()
        ng_ok = ("Circuits match uniquely" in ng) or ("Final result: Circuits match" in ng)
        lines.append(f"\n## netgen\n- {'PASS' if ng_ok else 'FAIL / see log'}\n")
        for ln in ng.splitlines():
            if any(k in ln for k in ("Final result", "Property", "Mismatch", "match",
                                       "Device", "Netlist", "Circuit")):
                lines.append(f"  {ln}\n")
    else:
        ng_ok = False
        lines.append("\n## netgen\n- SKIP (no extract)\n")

    render()
    lines.append(f"\n## Summary\n- DRC hard: {'PASS' if not hard else 'FAIL'}\n")
    lines.append(f"- KLayout LVS: {'PASS' if lvs_ok else 'FAIL'}\n")
    lines.append(f"- netgen: {'PASS' if ng_ok else 'FAIL'}\n")
    open(os.path.join(OUT, "summary_pair_drc_lvs.txt"), "w").writelines(lines)
    print("".join(lines))
    return 0 if (not hard and lvs_ok and ng_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
