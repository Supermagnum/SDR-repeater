#!/usr/bin/env python3
"""P2.7.2a2 — DRC + KLayout LVS + netgen on dac_unit and bank_unit."""
from __future__ import annotations

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
PDK_DRC = "/foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py"
PDK_LVS = "/foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/lvs/run_lvs.py"
NETGEN_SETUP = "/foss/pdks/ihp-sg13g2/libs.tech/netgen/ihp-sg13g2_setup.tcl"

# Block-level density fill waived (decisions.md); everything else must be clean
DENSITY = {"AFil.g", "GFil.g", "M1.j", "M2.j", "M3.j", "M4.j", "M5.j",
           "TM1.c", "TM2.c", "TM1.d", "TM2.d"}


def run(cmd, log, timeout=1800):
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
    # {'AFil.g', 'M1.b', ...}
    return set(re.findall(r"'([^']+)'", m.group(1)))


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
    res["klayout_lvs"] = run([
        "python3", PDK_LVS, f"--layout={gds}", f"--netlist={spice}",
        f"--topcell={cell}", f"--run_dir={lvs_dir}",
        "--disable_tap_extraction", "--ignore_top_ports_mismatch",
        "--combine_devices", "--top_lvl_pins",
    ], os.path.join(OUT, f"lvs_klayout_{cell}.log"))
    kl = open(os.path.join(OUT, f"lvs_klayout_{cell}.log"), errors="ignore").read()
    res["klayout_pass"] = "| Status           | PASS" in kl or "Status           | PASS" in kl

    ext = None
    for root, _, files in os.walk(lvs_dir):
        for f in files:
            if f.endswith("_extracted.cir"):
                ext = os.path.join(root, f)
    res["extracted"] = ext
    if ext and os.path.exists(NETGEN_SETUP):
        tcl = os.path.join(OUT, f"netgen_{cell}.tcl")
        json_out = os.path.join(OUT, f"netgen_{cell}.json")
        # netgen lvs args are "{file cell}" (file first), not "{cell file}"
        open(tcl, "w").write(
            f'lvs {{{spice} {cell}}} {{{ext} {cell}}} {NETGEN_SETUP} {json_out}\n')
        res["netgen"] = run(
            ["netgen", "-batch", "source", tcl],
            os.path.join(OUT, f"netgen_{cell}.log"), timeout=600)
        ng = open(os.path.join(OUT, f"netgen_{cell}.log"), errors="ignore").read()
        res["netgen_pass"] = "Circuits match uniquely" in ng or \
            "Final result: Circuits match" in ng
    else:
        res["netgen"] = None
        res["netgen_pass"] = False
    return res


def main():
    lines = ["# P2.7.2a2 LVS proof — dac_unit + bank_unit\n\n"]
    lines.append(f"PDK netgen setup: `{NETGEN_SETUP}` "
                 f"(exists={os.path.exists(NETGEN_SETUP)})\n\n")
    lines.append("## IHP workarounds\n\n")
    lines.append("- **#861 / #753:** no SVaricap in these cells.\n")
    lines.append("- **#512:** two separate `cmim` PCells in bank_unit.\n")
    lines.append("- **SVaricap future (#861):** ThickGateOx missing — waiver + "
                 "Nx checklist on varactor blocks.\n\n")
    lines.append("## Earlier bank_unit short (avoid in sub-block runs)\n\n")
    lines.append("- Gate M1 landing wider than L=0.13 S/D gap → G shorted to D/S.\n")
    lines.append("- Cont on poly overhang next to S/D Conts → Cnt.b + risk of merge.\n")
    lines.append("- Hand via / strap M1 crossed a/b rails → `bb|g|vbp` merge; "
                 "W=10.32 switch vanished from extract.\n")
    lines.append("- Fix: PDK `via_stack`, upward poly stubs, separate a/b y-levels.\n\n")

    all_ok = True
    for cell in ("dac_unit", "bank_unit"):
        if not os.path.exists(os.path.join(OUT, f"{cell}.gds")):
            lines.append(f"## {cell}\n\nMISSING GDS\n\n")
            all_ok = False
            continue
        r = prove(cell)
        lines.append(f"## {cell}\n\n")
        lines.append(f"- DRC exit: {r['drc']}; rules: {sorted(r['drc_rules'])}\n")
        lines.append(f"- DRC non-density: {r['drc_non_density'] or 'none'} → "
                     f"{'PASS' if r['drc_clean'] else 'FAIL'}\n")
        lines.append(f"- KLayout LVS: {'PASS' if r['klayout_pass'] else 'FAIL'} "
                     f"(exit {r['klayout_lvs']})\n")
        lines.append(f"- netgen: {'PASS' if r['netgen_pass'] else 'FAIL'} "
                     f"(exit {r['netgen']})\n")
        lines.append(f"- extracted: `{r['extracted']}`\n\n")
        if not (r["drc_clean"] and r["klayout_pass"] and r["netgen_pass"]):
            all_ok = False

    path = os.path.join(OUT, "summary_lvs_proof.txt")
    open(path, "w").writelines(x if x.endswith("\n") else x + "\n" for x in lines)
    print(f"wrote {path}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
