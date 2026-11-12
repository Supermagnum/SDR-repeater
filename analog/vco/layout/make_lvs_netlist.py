#!/usr/bin/env python3
"""Build an LVS-oriented schematic netlist for vco_top.

Source: accepted flat sim deck `sch/netlists/vco_sim_flat.spice` [SCH].
Edits for KLayout/netgen spice readers:
  - rename subckt → vco_top (xschem writes `**.subckt`; keep it)
  - black-box EM inductor (drop ideal L/R/C lumped model; layout is metal-only)
  - drop ideal V/I sources (vvb, iref, ib) and load R/C not in layout
  - keep PDK X-devices and poly resistors

Writes: out/vco_top_lvs.spice
"""
from __future__ import annotations

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "sch", "netlists", "vco_sim_flat.spice")
OUT = os.path.join(HERE, "out", "vco_top_lvs.spice")

DROP = re.compile(
    r"^(r1p|l1p|r2p|l2p|r1n|l1n|r2n|l2n|cp|vvb|iref|ib|rl1|rl2|ctb|cl1|cl2|"
    r"ctail|cbf)\b",
    re.I,
)


def main():
    raw = open(SRC).read().splitlines()
    body = []
    for ln in raw:
        # xschem: `**.subckt name ...` and `**.ends` — keep as .subckt / .ends
        if ln.startswith("**.subckt") or ln.startswith("**.ends"):
            ln = ln[1:]  # one star → *.subckt still wrong; strip all leading *
            ln = ln.lstrip("*")
            if not ln.startswith("."):
                ln = "." + ln
        elif ln.startswith("**"):
            continue
        body.append(ln)

    text = "\n".join(body)
    text = text.replace(".subckt vco_sim_flat", ".subckt vco_top")
    kept = []
    for ln in text.splitlines():
        if DROP.match(ln.strip()):
            continue
        kept.append(ln)

    header = [
        "* P2.7.2 LVS schematic for vco_top [SCH]",
        "* Derived from vco_sim_flat.spice; ideal L/V/I stripped for LVS.",
        "* Inductor L_2n0_tapped is a black box (EM GDS); #861/#753/#512 apply.",
        ".subckt l2n0 p n ct",
        "* empty — layout is metal geometry only",
        ".ends",
        "",
    ]
    final = []
    injected = False
    for ln in header + kept:
        final.append(ln)
        if (not injected) and ln.strip().startswith(".subckt vco_top"):
            final.append("xl tp tn ct l2n0")
            injected = True

    if not any(l.strip().startswith(".subckt vco_top") for l in final):
        raise SystemExit("make_lvs_netlist: .subckt vco_top missing — check source")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write("\n".join(final) + "\n")
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes); injected_xl={injected}")


if __name__ == "__main__":
    main()
