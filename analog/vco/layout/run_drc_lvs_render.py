#!/usr/bin/env python3
"""P2.7.2 — DRC, LVS (KLayout + netgen), and KLayout PNG/SVG renders for vco_top.

    python3 -u run_drc_lvs_render.py
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
GDS = os.path.join(OUT, "vco_top.gds")
SCH_SPICE = os.path.join(OUT, "vco_top_lvs.spice")
PDK_DRC = "/foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py"
PDK_LVS = "/foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/lvs/run_lvs.py"


def run(cmd, log_path, timeout=3600):
    print("+", " ".join(cmd), flush=True)
    with open(log_path, "w") as fh:
        r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout)
    print(f"  exit {r.returncode}; log {log_path}", flush=True)
    return r.returncode


def render():
    import pya
    ly = pya.Layout()
    ly.read(GDS)
    top = ly.cell("vco_top")
    # save SVG via LayoutView if available
    views = [
        ("vco_top", top),
        ("vco_core", ly.cell("vco_core")),
        ("vco_bank", ly.cell("vco_bank")),
        ("L_2n0_tapped", ly.cell("L_2n0_tapped")),
    ]
    # Use klayout -b script for PNG
    script = os.path.join(OUT, "_render.drc")
    # simpler: write GDS cells and call klayout -zz
    for name, cell in views:
        if cell is None:
            print(f"missing cell {name}")
            continue
        path = os.path.join(OUT, f"{name}.gds")
        tmp = pya.Layout()
        tmp.dbu = ly.dbu
        # copy cell tree
        tc = tmp.create_cell(name)
        tc.copy_tree(cell)
        tmp.write(path)
    # klayout screenshot via ruby/python
    py = os.path.join(OUT, "_klayout_shot.py")
    open(py, "w").write(r'''
# KLayout -b -r script -rd out=... -rd name=...
import pya, os
gds = os.path.join(out, name + ".gds")
ly = pya.Layout(); ly.read(gds)
bb = ly.top_cell().bbox()
# PNG via LayoutView in batch
lv = pya.LayoutView()
lv.show_layout(ly, False)
lv.max_hier()
lv.zoom_fit()
png = os.path.join(out, name + ".png")
try:
    lv.save_image(png, 1600, 1200)
except Exception as e:
    open(os.path.join(out, name + "_png_err.txt"), "w").write(str(e))
# SVG: bbox stub + layer box outline (portable, no Qt required)
w = max(bb.width(), 1); h = max(bb.height(), 1)
scale = min(780.0 / w, 560.0 / h)
ow, oh = w * scale, h * scale
svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600">',
    f'<rect x="10" y="20" width="{ow:.1f}" height="{oh:.1f}" '
    f'fill="none" stroke="black" stroke-width="1"/>',
    f'<text x="10" y="14" font-size="12">{name} bbox {bb} dbu</text>',
    '</svg>\n',
]
open(os.path.join(out, name + ".svg"), "w").write("\n".join(svg))
print("rendered", name, "bbox", bb)
''')
    for name, _ in views:
        log = os.path.join(OUT, f"render_{name}.log")
        cmd = ["klayout", "-b", "-r", py, "-rd", f"out={OUT}", "-rd", f"name={name}"]
        try:
            run(cmd, log, timeout=120)
        except Exception as e:
            print(f"render {name}: {e}")
            open(os.path.join(OUT, f"{name}.svg"), "w").write(
                f'<svg xmlns="http://www.w3.org/2000/svg"><text>{name}</text></svg>\n')


def parse_violations(drc_log, rdb_path, lines):
    """Summarise violated rules; propose fill / EM waivers where applicable."""
    import re
    from collections import Counter
    text = open(drc_log).read() if os.path.exists(drc_log) else ""
    m = re.search(r"Violated rules are\s*:\s*(\{[^}]+\})", text)
    violated = set()
    if m:
        violated = set(re.findall(r"'([^']+)'", m.group(1)))
    lines.append(f"violated rules: {sorted(violated) if violated else '(none / parse miss)'}\n")
    # density / fill family — waiver candidates at block level
    density = {r for r in violated if r.endswith(".j") or r.endswith(".c")
               or r.startswith("AFil") or r.startswith("GFil")
               or r in {"TM1.c", "TM2.c", "M1.j", "M2.j", "M3.j", "M4.j", "M5.j"}}
    hard = violated - density
    waiver_path = os.path.join(OUT, "summary_drc_waivers.txt")
    wlines = ["# P2.7.2 DRC waivers / open errors\n"]
    if density:
        wlines.append("## Proposed waivers (block-level density / fill)\n")
        for r in sorted(density):
            wlines.append(f"- {r}: global density — fill deferred to top-chip "
                          f"(P2.7.8). Isolated nmos PCell shows same class.\n")
        lines.append(f"density/fill rules ({len(density)}): proposed waiver → "
                     f"`summary_drc_waivers.txt`\n")
    if hard:
        wlines.append("\n## Hard errors (must fix or waive with rule+reason)\n")
        for r in sorted(hard):
            reason = "open"
            if r == "TV2.a":
                reason = "L_2n0_tapped EM geometry (accepted tapped GDS); " \
                         "TopVia2 width in inductor — EM-locked [EM]"
            wlines.append(f"- {r}: {reason}\n")
        lines.append(f"hard rules ({len(hard)}): {sorted(hard)}\n")
    open(waiver_path, "w").writelines(x if x.endswith("\n") else x + "\n"
                                      for x in wlines)
    if rdb_path and os.path.exists(rdb_path):
        items = open(rdb_path, errors="ignore").read()
        cats = Counter(re.findall(r"<category>'([^']+)'</category>", items))
        open(os.path.join(OUT, "summary_drc_rules.txt"), "w").write(
            "\n".join(f"{k}: {v}" for k, v in cats.most_common()) + "\n")
        lines.append(f"RDB item counts (top): {cats.most_common(8)}\n")


def main():
    if not os.path.exists(GDS):
        sys.exit(f"missing {GDS} — run build_vco_layout.py first")
    lines = ["# P2.7.2 DRC / LVS / render\n"]

    # LVS schematic (ideal-L stripped)
    run([sys.executable, os.path.join(HERE, "make_lvs_netlist.py")],
        os.path.join(OUT, "make_lvs_netlist.log"), timeout=60)

    # DRC minimum then note full
    drc_dir = os.path.join(OUT, "drc")
    os.makedirs(drc_dir, exist_ok=True)
    drc_log = os.path.join(OUT, "drc_run.log")
    rc = run([
        "python3", PDK_DRC, f"--path={GDS}", "--topcell=vco_top",
        "--minimum_drc", f"--run_dir={drc_dir}", "--mp=4",
    ], drc_log, timeout=1800)
    lines.append(f"## DRC (minimum / precheck)\n\nexit {rc}\n")
    lines.append(f"log: `out/drc_run.log`; results under `out/drc/`\n\n")
    rdb = None
    for root, _, files in os.walk(drc_dir):
        for f in files:
            if f.endswith("_full.lyrdb"):
                rdb = os.path.join(root, f)
            elif rdb is None and (f.endswith(".lyrdb") or f.endswith(".rdb")):
                rdb = os.path.join(root, f)
    if rdb:
        lines.append(f"results database: `{rdb}`\n")
        parse_violations(drc_log, rdb, lines)
    else:
        lines.append("No .lyrdb found — see drc_run.log.\n")
        parse_violations(drc_log, None, lines)

    # KLayout LVS
    lvs_dir = os.path.join(OUT, "lvs_klayout")
    os.makedirs(lvs_dir, exist_ok=True)
    if os.path.exists(SCH_SPICE):
        rc2 = run([
            "python3", PDK_LVS, f"--layout={GDS}", f"--netlist={SCH_SPICE}",
            "--topcell=vco_top", f"--run_dir={lvs_dir}",
            "--disable_tap_extraction", "--ignore_top_ports_mismatch",
        ], os.path.join(OUT, "lvs_klayout_run.log"), timeout=1800)
        lines.append(f"\n## KLayout LVS\n\nexit {rc2}; log `out/lvs_klayout_run.log`\n")
        lines.append("Netlist: `out/vco_top_lvs.spice` from vco_sim_flat "
                     "(ideal L/V/I stripped; inductor black-box).\n")
        lines.append("Workarounds applied: #861 (SVaricap / ThickGateOx — "
                     "do not treat clean LVS as proof varactor present), "
                     "#753 (Nx drawn 10+10, not checked by LVS), "
                     "#512 (one rfcmim/cmim PCell per schematic MIM). "
                     "Taps disabled to align with Magic+netgen style.\n")
    else:
        lines.append("\n## KLayout LVS\n\nskipped — missing schematic spice\n")
        rc2 = 1

    # netgen schematic-vs-extracted if layout netlist produced
    lines.append("\n## netgen\n\n")
    ext = None
    for root, _, files in os.walk(lvs_dir):
        for f in files:
            if f.endswith(".cir") or f.endswith(".spice") or f.endswith(".cdl"):
                if "extract" in f.lower() or "layout" in f.lower() or f.endswith(".cir"):
                    ext = os.path.join(root, f)
    if ext and os.path.exists(SCH_SPICE):
        tcl = os.path.join(OUT, "netgen_vco.tcl")
        json_out = os.path.join(OUT, "netgen_vco.json")
        # netgen lvs wants file paths, not "cell file" pairs as bare words
        open(tcl, "w").write(f"""
puts "netgen P2.7.2 vco_top"
set search [list]
lvs "{SCH_SPICE}" "{ext}" "$search" "{json_out}"
""")
        rc3 = run(["netgen", "-batch", "source", tcl],
                  os.path.join(OUT, "netgen_vco.log"), timeout=600)
        lines.append(f"netgen exit {rc3}; see `out/netgen_vco.log`\n")
    else:
        lines.append("netgen skipped — no extracted layout netlist yet "
                     "(KLayout LVS must produce one). Compare will use "
                     "schematic spice vs layout extract when available.\n")
        # Still try netgen schematic-only smoke
        lines.append("Documented: netgen LVS intended against xschem "
                     "`vco_top.spice`; extraction path depends on KLayout LVS "
                     "output. #861/#753/#512 apply as in p27-layout-notes.\n")
        rc3 = None

    # renders
    lines.append("\n## Renders\n\n")
    try:
        render()
        lines.append("PNG/SVG attempted for vco_top, vco_core, vco_bank, L_2n0_tapped "
                     "under `out/`.\n")
    except Exception as e:
        lines.append(f"render error: {e}\n")

    path = os.path.join(OUT, "summary_drc_lvs.txt")
    open(path, "w").writelines(x if x.endswith("\n") else x + "\n" for x in lines)
    print(f"wrote {path}")
    # overall
    print("DRC_RC", rc, "LVS_RC", rc2)
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
