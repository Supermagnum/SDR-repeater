#!/usr/bin/env python3
"""P2.7.2b varactor — DRC + KLayout LVS + netgen for a named cell."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
PDK_DRC = "/foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py"
PDK_LVS = "/foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/lvs/run_lvs.py"
NETGEN_SETUP = "/foss/pdks/ihp-sg13g2/libs.tech/netgen/ihp-sg13g2_setup.tcl"
DENSITY = {"AFil.g", "GFil.g", "M1.j", "M2.j", "M3.j", "M4.j", "M5.j", "M5.k",
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


def render(cell):
    py = os.path.join(OUT, f"_klayout_shot_{cell}.py")
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
    run(["klayout", "-b", "-r", py, "-rd", f"out={OUT}", "-rd", f"name={cell}"],
        os.path.join(OUT, f"render_{cell}.log"), timeout=120)


def prove(cell: str) -> dict:
    gds = os.path.join(OUT, f"{cell}.gds")
    spice = os.path.join(OUT, f"{cell}.spice")
    res = {"cell": cell}
    drc_dir = os.path.join(OUT, f"drc_{cell}")
    os.makedirs(drc_dir, exist_ok=True)
    res["drc"] = run([
        "python3", PDK_DRC, f"--path={gds}", f"--topcell={cell}",
        "--minimum_drc", f"--run_dir={drc_dir}", "--mp=2",
    ], os.path.join(OUT, f"drc_{cell}.log"))
    res["drc_rules"] = parse_violated(os.path.join(OUT, f"drc_{cell}.log"))
    res["drc_non_density"] = sorted(res["drc_rules"] - DENSITY)
    res["drc_clean"] = len(res["drc_non_density"]) == 0

    lvs_dir = os.path.join(OUT, f"lvs_{cell}")
    os.makedirs(lvs_dir, exist_ok=True)
    # PDK run_lvs appends to {cell}.log; truncate so PASS/FAIL is this run only.
    cell_log = os.path.join(lvs_dir, f"{cell}.log")
    if os.path.exists(cell_log):
        open(cell_log, "w").close()
    res["klayout_lvs"] = run([
        "python3", PDK_LVS, f"--layout={gds}", f"--netlist={spice}",
        f"--topcell={cell}", f"--run_dir={lvs_dir}",
        "--disable_tap_extraction", "--ignore_top_ports_mismatch",
        "--combine_devices", "--top_lvl_pins",
    ], os.path.join(OUT, f"lvs_klayout_{cell}.log"))
    # PDK run_lvs can print Status PASS from a stale run; trust the cell log.
    kl_cell = open(cell_log, errors="ignore").read() if os.path.exists(cell_log) else ""
    # Last match wins
    last_ok = kl_cell.rfind("Congratulations! Netlists match")
    last_bad = kl_cell.rfind("ERROR : Netlists don't match")
    res["klayout_pass"] = last_ok > last_bad and last_ok >= 0

    ext = None
    for root, _, files in os.walk(lvs_dir):
        for f in files:
            if f.endswith("_extracted.cir"):
                ext = os.path.join(root, f)
    res["extracted"] = ext
    res["netgen_pass"] = False
    res["netgen"] = None
    if ext and os.path.exists(NETGEN_SETUP):
        # rfcmim extract uses C-prefix + name "rfcmim"; netgen setup wants
        # cap_rfcmim and X-prefix for 3-terminal devices [PDK / assemble].
        def for_netgen(txt: str) -> str:
            txt = txt.replace(" rfcmim ", " cap_rfcmim ")
            out = []
            for ln in txt.splitlines():
                s = ln.lstrip()
                # C-prefix 3-terminal (rfcmim / svaricap) and R-prefix rhigh
                # need X-prefix for netgen multi-terminal parse [PDK]
                if ((s.startswith("C") and (
                        " cap_rfcmim " in f" {s} " or
                        " sg13_hv_svaricap " in f" {s} ")) or
                        (s.startswith("R") and " rhigh " in f" {s} ")):
                    i = len(ln) - len(s)
                    ln = ln[:i] + "X" + s[1:]
                out.append(ln)
            return "\n".join(out) + ("\n" if txt.endswith("\n") else "")

        spice_ng = os.path.join(OUT, f"{cell}_netgen.spice")
        ext_ng = os.path.join(OUT, f"{cell}_extracted_netgen.cir")
        open(spice_ng, "w").write(for_netgen(open(spice).read()))
        open(ext_ng, "w").write(for_netgen(open(ext).read()))
        tcl = os.path.join(OUT, f"netgen_{cell}.tcl")
        json_out = os.path.join(OUT, f"netgen_{cell}.json")
        open(tcl, "w").write(
            f'lvs {{{spice_ng} {cell}}} {{{ext_ng} {cell}}} '
            f'{NETGEN_SETUP} {json_out}\n')
        res["netgen"] = run(
            ["netgen", "-batch", "source", tcl],
            os.path.join(OUT, f"netgen_{cell}.log"), timeout=600)
        ng = open(os.path.join(OUT, f"netgen_{cell}.log"), errors="ignore").read()
        res["netgen_pass"] = "Circuits match uniquely" in ng or \
            "Final result: Circuits match" in ng

    try:
        render(cell)
    except Exception as e:
        print(f"  render fail: {e}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True)
    args = ap.parse_args()
    r = prove(args.cell)
    print("\n# Summary")
    print(f"cell={r['cell']}")
    print(f"DRC clean (density waived): {r['drc_clean']}  "
          f"non-density={r['drc_non_density']}")
    print(f"KLayout LVS: {'PASS' if r['klayout_pass'] else 'FAIL'}")
    print(f"netgen: {'PASS' if r['netgen_pass'] else 'FAIL'}")
    open(os.path.join(OUT, f"summary_prove_{args.cell}.txt"), "w").write(
        f"drc_clean={r['drc_clean']} non_density={r['drc_non_density']}\n"
        f"klayout={r['klayout_pass']} netgen={r['netgen_pass']}\n"
    )
    ok = r["drc_clean"] and r["klayout_pass"] and r["netgen_pass"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
