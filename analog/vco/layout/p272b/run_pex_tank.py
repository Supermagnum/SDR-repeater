#!/usr/bin/env python3
"""P2.7.2c — Magic RC extract on vco_core_tank tn/tp [PEX-RC].

Uses PDK magicrc + extract style with parasitics (hrhc). Reports C and R
seen from tn/tp vs schematic devices (subtract ideal rfcmim if present).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "pex_core")
GDS = os.path.join(HERE, "out", "vco_core_tank.gds")
CELL = "vco_core_tank"
PDK_MAGICRC = "/foss/pdks/ihp-sg13g2/libs.tech/magic/ihp-sg13g2.magicrc"
os.makedirs(OUT, exist_ok=True)


def main():
    if not os.path.exists(GDS):
        raise SystemExit(f"missing {GDS}")
    tcl = os.path.join(OUT, "extract.tcl")
    spice = os.path.join(OUT, f"{CELL}.spice")
    # magic writes .ext in cwd; work inside OUT
    open(tcl, "w").write(f"""
drc off
gds flat true
gds read {GDS}
load {CELL}
select top cell
expand
extract path {OUT}
extract do local
extract all
ext2spice lvs
ext2spice cthresh 0.01
ext2spice rthresh 0.01
ext2spice scale off
ext2spice -o {spice}
quit -noprompt
""")
    log = os.path.join(OUT, "magic_extract.log")
    cmd = [
        "magic", "-dnull", "-noconsole",
        "-rcfile", PDK_MAGICRC,
        tcl,
    ]
    print("+", " ".join(cmd), flush=True)
    with open(log, "w") as fh:
        r = subprocess.run(cmd, cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
    print(f"exit {r.returncode}; log {log}", flush=True)
    if r.returncode != 0 or not os.path.exists(spice):
        # retry with default extract (may still get devices)
        print("retry without cthresh...", flush=True)
        open(tcl, "w").write(f"""
drc off
gds flat true
gds read {GDS}
load {CELL}
select top cell
expand
extract path {OUT}
extract all
ext2spice lvs
ext2spice
ext2spice -o {spice}
quit -noprompt
""")
        with open(log, "a") as fh:
            r = subprocess.run(cmd, cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
        print(f"retry exit {r.returncode}", flush=True)
    if not os.path.exists(spice):
        raise SystemExit("no spice written")
    txt = open(spice).read()
    open(os.path.join(OUT, "summary_pex_raw.txt"), "w").write(txt)
    # Parse capacitors and resistors touching tn/tp
    report = analyze(txt)
    path = os.path.join(HERE, "out", "summary_pex_core_tank.txt")
    open(path, "w").write(report)
    print(report)
    print(f"Wrote {path}")
    return 0


def analyze(txt: str) -> str:
    lines = [
        "# P2.7.2c Magic RC extract — vco_core_tank tn/tp [PEX-RC]\n\n",
        f"GDS: `{GDS}`  cell: `{CELL}`\n",
        "Tool: magic + ihp-sg13g2.magicrc; ext2spice lvs + cthresh/rthresh 0.01.\n\n",
    ]
    # Collect C and R connected to tn or tp
    caps = []  # (name, n1, n2, c)
    res = []
    for ln in txt.splitlines():
        s = ln.strip()
        if not s or s.startswith("*") or s.startswith("."):
            continue
        toks = s.replace("(", " ").replace(")", " ").split()
        if not toks:
            continue
        name = toks[0]
        if name[0] in "Cc" and len(toks) >= 4:
            # Cxxx n1 n2 [n3] ... c=val or val
            nodes = []
            cval = None
            for t in toks[1:]:
                if t.startswith("c=") or t.startswith("C="):
                    cval = parse_farad(t.split("=", 1)[1])
                elif re.match(r"^[0-9.]+[a-zA-Z]*$", t) and cval is None and len(nodes) >= 2:
                    try:
                        cval = parse_farad(t)
                    except Exception:
                        nodes.append(t)
                else:
                    nodes.append(t)
            if cval is not None and len(nodes) >= 2:
                caps.append((name, nodes[0], nodes[1], cval, nodes))
        if name[0] in "Rr" and len(toks) >= 4:
            nodes = []
            rval = None
            for t in toks[1:]:
                if t.startswith("r=") or t.startswith("R="):
                    rval = parse_ohm(t.split("=", 1)[1])
                elif re.match(r"^[0-9.]+[a-zA-Z]*$", t) and rval is None and len(nodes) >= 2:
                    try:
                        rval = parse_ohm(t)
                    except Exception:
                        nodes.append(t)
                else:
                    nodes.append(t)
            if rval is not None and len(nodes) >= 2:
                res.append((name, nodes[0], nodes[1], rval))

    def touches(nset, a, b):
        return a in nset or b in nset

    tank = {"tn", "tp", "TN", "TP"}
    # Sum C from tn/tp to anything else (exclude intentional rfcmim if labelled)
    c_tn = c_tp = 0.0
    c_tn_list = []
    c_tp_list = []
    for name, a, b, c, nodes in caps:
        al = a.lower()
        bl = b.lower()
        # skip if looks like intentional MIM already in sch (large ~384 fF)
        # we still report all
        if al in ("tn",) or bl in ("tn",):
            c_tn += c
            c_tn_list.append((name, a, b, c))
        if al in ("tp",) or bl in ("tp",):
            c_tp += c
            c_tp_list.append((name, a, b, c))

    # Schematic intentional: 2× rfcmim 16×16 → 384 fF each plate [PDK 1.5 fF/µm²]
    C_MIM_SCH = 16.0 * 16.0 * 1.5  # fF per side plate to fx/gnd stack
    lines.append("## Capacitors touching tn / tp\n\n")
    lines.append("| name | n1 | n2 | C (fF) |\n|---|---|---|---|\n")
    for name, a, b, c in c_tn_list + c_tp_list:
        # dedupe
        pass
    seen = set()
    for name, a, b, c in c_tn_list + c_tp_list:
        key = (name, a, b, c)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"| {name} | {a} | {b} | {c*1e15:.3f} |\n")

    lines.append(f"\nSum C on tn (all caps): **{c_tn*1e15:.2f} fF** [PEX-RC]\n")
    lines.append(f"Sum C on tp (all caps): **{c_tp*1e15:.2f} fF** [PEX-RC]\n")
    lines.append(
        f"Schematic rfcmim plate (16×16×1.5): **{C_MIM_SCH:.1f} fF**/side [PDK]\n"
    )
    # Added wiring ≈ total − schematic MIM (if extract includes MIM)
    add_tn = c_tn * 1e15 - C_MIM_SCH
    add_tp = c_tp * 1e15 - C_MIM_SCH
    lines.append(
        f"Added C vs sch MIM (tn/tp): **{add_tn:.2f} / {add_tp:.2f} fF** "
        f"[PEX-RC − PDK]\n"
    )
    lines.append(
        f"Hand bound was 15–30 fF (used 30): "
        f"{'within' if 0 <= max(add_tn, add_tp) <= 40 else 'outside'} "
        f"loose check [HAND].\n\n"
    )

    lines.append("## Resistors touching tn / tp\n\n")
    lines.append("| name | n1 | n2 | R (Ω) |\n|---|---|---|---|\n")
    r_tn = r_tp = 0.0
    for name, a, b, r in res:
        al, bl = a.lower(), b.lower()
        if al in ("tn", "tp") or bl in ("tn", "tp"):
            lines.append(f"| {name} | {a} | {b} | {r:.4g} |\n")
            if "tn" in (al, bl):
                r_tn += r
            if "tp" in (al, bl):
                r_tp += r
    lines.append(f"\nSum R on tn/tp nets (crude): {r_tn:.3g} / {r_tp:.3g} Ω [PEX-RC]\n")
    lines.append(
        "Hand bound series Rs 0.2–0.4 Ω/side [HAND summary_rc_tank]; "
        "compare only path resistors if extract separates them.\n"
    )
    if not caps:
        lines.append(
            "\n**WARNING:** no capacitors parsed from extract — tool may have "
            "failed or used LVS-only style without parasitics. See magic log.\n"
        )
    return "".join(lines)


def parse_farad(s: str) -> float:
    s = s.strip().lower().replace("f", "")
    # spice suffixes
    m = re.match(r"^([0-9.eE+-]+)(a|f|p|n|u|m|k|meg|g)?$", s)
    if not m:
        # maybe already had trailing f as femto in "20f"
        m = re.match(r"^([0-9.eE+-]+)([afpnumk])$", s)
    if not m:
        return float(s)
    v = float(m.group(1))
    suf = (m.group(2) or "")
    scale = {
        "a": 1e-18, "f": 1e-15, "p": 1e-12, "n": 1e-9,
        "u": 1e-6, "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9, "": 1.0,
    }.get(suf, 1.0)
    # if original ended with 'f' as farad unit marker after number with suffix
    return v * scale


def parse_ohm(s: str) -> float:
    s = s.strip().lower()
    m = re.match(r"^([0-9.eE+-]+)(m|k|meg|g)?$", s)
    if not m:
        return float(s)
    v = float(m.group(1))
    suf = m.group(2) or ""
    return v * {"m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9, "": 1.0}[suf]


if __name__ == "__main__":
    sys.exit(main())
