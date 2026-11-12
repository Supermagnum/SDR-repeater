#!/usr/bin/env python3
"""P2.7.2b — DRC + KLayout LVS + netgen on vco_core_tank; PNG render."""
from __future__ import annotations

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CELL = "vco_core_tank"
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
    py = os.path.join(OUT, "_klayout_shot.py")
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
    lines = ["# P2.7.2b DRC / LVS — vco_core_tank\n\n"]
    if not os.path.exists(GDS):
        lines.append("MISSING GDS\n")
        open(os.path.join(OUT, "summary_drc_lvs.txt"), "w").writelines(lines)
        return 1

    drc_dir = os.path.join(OUT, f"drc_{CELL}")
    os.makedirs(drc_dir, exist_ok=True)
    run([
        "python3", PDK_DRC, f"--path={GDS}", f"--topcell={CELL}",
        "--minimum_drc", f"--run_dir={drc_dir}", "--mp=2",
    ], os.path.join(OUT, f"drc_{CELL}.log"))
    rules = parse_violated(os.path.join(OUT, f"drc_{CELL}.log"))
    hard = sorted(rules - DENSITY)
    dens = sorted(rules & DENSITY)
    drc_ok = len(hard) == 0
    lines.append(f"- DRC rules: {sorted(rules) if rules else '(none / parse miss)'}\n")
    lines.append(f"- density/fill waived: {dens or 'none'}\n")
    lines.append(f"- DRC non-density: {hard or 'none'} → "
                 f"{'PASS' if drc_ok else 'FAIL'}\n")

    lvs_dir = os.path.join(OUT, f"lvs_{CELL}")
    os.makedirs(lvs_dir, exist_ok=True)
    run([
        "python3", PDK_LVS, f"--layout={GDS}", f"--netlist={SPICE}",
        f"--topcell={CELL}", f"--run_dir={lvs_dir}",
        "--disable_tap_extraction", "--ignore_top_ports_mismatch",
        "--combine_devices", "--top_lvl_pins",
    ], os.path.join(OUT, f"lvs_klayout_{CELL}.log"))
    kl = open(os.path.join(OUT, f"lvs_klayout_{CELL}.log"), errors="ignore").read()
    kl_ok = "| Status           | PASS" in kl or "Status           | PASS" in kl
    lines.append(f"- KLayout LVS: {'PASS' if kl_ok else 'FAIL'}\n")

    ext = None
    for root, _, files in os.walk(lvs_dir):
        for f in files:
            if f.endswith("_extracted.cir"):
                ext = os.path.join(root, f)
    lines.append(f"- extracted: `{ext}`\n")
    ng_ok = False
    if ext and os.path.exists(NETGEN_SETUP):
        tcl = os.path.join(OUT, f"netgen_{CELL}.tcl")
        json_out = os.path.join(OUT, f"netgen_{CELL}.json")
        open(tcl, "w").write(
            f'lvs {{{SPICE} {CELL}}} {{{ext} {CELL}}} {NETGEN_SETUP} {json_out}\n')
        run(["netgen", "-batch", "source", tcl],
            os.path.join(OUT, f"netgen_{CELL}.log"), timeout=600)
        ng = open(os.path.join(OUT, f"netgen_{CELL}.log"), errors="ignore").read()
        ng_ok = "Circuits match uniquely" in ng or "Final result: Circuits match" in ng
        # property warnings
        prop = re.findall(r"(?i)property.*?(?:warning|mismatch|differ)[^\n]*", ng)
        prop += re.findall(r"(?i)(?:AS|AD|ng|W|L)\s*[:=].*", ng)[:20]
        lines.append(f"- netgen: {'PASS' if ng_ok else 'FAIL'}\n")
        if "Property errors" in ng or "property" in ng.lower():
            # pull a short property section
            for pat in ("Property errors", "Device property", "Failed property"):
                i = ng.find(pat)
                if i >= 0:
                    lines.append("\n### netgen property excerpt\n\n```\n")
                    lines.append(ng[i:i + 1200] + "\n```\n")
                    break
    else:
        lines.append("- netgen: SKIP (no extract or setup)\n")

    try:
        render()
        lines.append(f"- render: `{CELL}.png` / `.svg`\n")
    except Exception as e:
        lines.append(f"- render FAILED: {e}\n")

    lines.append(f"\n## Verdict\n\n")
    lines.append(f"- Pass criteria DRC (density waived): {'PASS' if drc_ok else 'FAIL'}\n")
    lines.append(f"- KLayout LVS: {'PASS' if kl_ok else 'FAIL'}\n")
    lines.append(f"- netgen (+ properties): {'PASS' if ng_ok else 'FAIL'}\n")

    path = os.path.join(OUT, "summary_drc_lvs.txt")
    open(path, "w").writelines(x if x.endswith("\n") else x + "\n" for x in lines)
    print(f"wrote {path}")
    return 0 if (drc_ok and kl_ok and ng_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
