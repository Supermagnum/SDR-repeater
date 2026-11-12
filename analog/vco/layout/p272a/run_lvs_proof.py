#!/usr/bin/env python3
"""P2.7.2a — DRC + KLayout LVS + netgen (PDK setup) on dac_unit and bank_unit."""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
PDK_DRC = "/foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py"
PDK_LVS = "/foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/lvs/run_lvs.py"
NETGEN_SETUP = "/foss/pdks/ihp-sg13g2/libs.tech/netgen/ihp-sg13g2_setup.tcl"


def run(cmd, log, timeout=1800):
    print("+", " ".join(cmd), flush=True)
    with open(log, "w") as fh:
        r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout)
    print(f"  exit {r.returncode}; log {log}", flush=True)
    return r.returncode


def prove(cell: str) -> dict:
    gds = os.path.join(OUT, f"{cell}.gds")
    spice = os.path.join(OUT, f"{cell}.spice")
    res = {"cell": cell}
    # DRC
    drc_dir = os.path.join(OUT, f"drc_{cell}")
    os.makedirs(drc_dir, exist_ok=True)
    res["drc"] = run([
        "python3", PDK_DRC, f"--path={gds}", f"--topcell={cell}",
        "--minimum_drc", f"--run_dir={drc_dir}", "--mp=2",
    ], os.path.join(OUT, f"drc_{cell}.log"))
    # KLayout LVS → extract + compare
    lvs_dir = os.path.join(OUT, f"lvs_{cell}")
    os.makedirs(lvs_dir, exist_ok=True)
    res["klayout_lvs"] = run([
        "python3", PDK_LVS, f"--layout={gds}", f"--netlist={spice}",
        f"--topcell={cell}", f"--run_dir={lvs_dir}",
        "--disable_tap_extraction", "--ignore_top_ports_mismatch",
        "--combine_devices", "--top_lvl_pins",
    ], os.path.join(OUT, f"lvs_klayout_{cell}.log"))
    # Find extracted cir
    ext = None
    for root, _, files in os.walk(lvs_dir):
        for f in files:
            if f.endswith("_extracted.cir") or f.endswith(".cir"):
                ext = os.path.join(root, f)
    res["extracted"] = ext
    # netgen with PDK setup
    if ext and os.path.exists(NETGEN_SETUP):
        tcl = os.path.join(OUT, f"netgen_{cell}.tcl")
        json_out = os.path.join(OUT, f"netgen_{cell}.json")
        # Proper netgen invocation: read both nets, source setup, compare
        open(tcl, "w").write(f"""
puts "P2.7.2a netgen {cell}"
set circuit1 [readnet spice {spice}]
set circuit2 [readnet spice {ext}]
lvs "{cell} {spice}" "{cell} {ext}" {NETGEN_SETUP} {json_out}
""")
        res["netgen"] = run(
            ["netgen", "-batch", "source", tcl],
            os.path.join(OUT, f"netgen_{cell}.log"), timeout=600)
    else:
        res["netgen"] = None
        print(f"netgen skipped for {cell}: ext={ext} setup={os.path.exists(NETGEN_SETUP)}")
    return res


def main():
    lines = ["# P2.7.2a LVS proof — dac_unit + bank_unit\n\n"]
    lines.append(f"PDK netgen setup: `{NETGEN_SETUP}` "
                 f"(exists={os.path.exists(NETGEN_SETUP)})\n\n")
    lines.append("## IHP workarounds on these cells\n\n")
    lines.append("- **#861** (SVaricap / ThickGateOx): does **not** apply — "
                 "no SVaricap in dac_unit or bank_unit.\n")
    lines.append("- **#753** (SVaricap Nx): does **not** apply.\n")
    lines.append("- **#512** (rfcmim multi-port / series-parallel): bank_unit "
                 "uses **two separate** `rfcmim` PCells (one per schematic "
                 "instance); do not merge. Watch multi-port warnings on extract.\n")
    lines.append("- **SVaricap future (#861):** VCO varactor LVS cannot prove "
                 "device presence until ThickGateOx is in the deck — keep a "
                 "drawn-Nx checklist (#753) and textual waiver with issue ID.\n\n")

    all_ok = True
    for cell in ("dac_unit", "bank_unit"):
        if not os.path.exists(os.path.join(OUT, f"{cell}.gds")):
            lines.append(f"## {cell}\n\nMISSING GDS — run build_lvs_proof_cells.py\n\n")
            all_ok = False
            continue
        r = prove(cell)
        lines.append(f"## {cell}\n\n")
        lines.append(f"- DRC exit: {r['drc']}\n")
        lines.append(f"- KLayout LVS exit: {r['klayout_lvs']}\n")
        lines.append(f"- netgen exit: {r['netgen']}\n")
        lines.append(f"- extracted: `{r['extracted']}`\n")
        # Parse logs for PASS/FAIL keywords
        for label, path in (
                ("drc", os.path.join(OUT, f"drc_{cell}.log")),
                ("klayout", os.path.join(OUT, f"lvs_klayout_{cell}.log")),
                ("netgen", os.path.join(OUT, f"netgen_{cell}.log")),
        ):
            if not os.path.exists(path):
                continue
            txt = open(path, errors="ignore").read()
            if "Violated rules" in txt or "Netlists don't match" in txt:
                lines.append(f"- {label}: FAIL signature in log\n")
                all_ok = False
            elif "Final result: Circuits match" in txt or \
                    "Result: Circuits match" in txt:
                lines.append(f"- {label}: Circuits match\n")
            elif label == "drc" and r["drc"] == 0:
                lines.append(f"- {label}: PASS (exit 0)\n")
            elif "Status" in txt and "PASS" in txt and "FAIL" not in txt:
                lines.append(f"- {label}: Status PASS (check log)\n")
        lines.append("\n")

    path = os.path.join(OUT, "summary_lvs_proof.txt")
    open(path, "w").writelines(x if x.endswith("\n") else x + "\n" for x in lines)
    print(f"wrote {path}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
