#!/usr/bin/env python3
"""Fail if extract SUBCKT ports show merged names (gnd|nbf etc.) [TOOL]."""
from __future__ import annotations

import os
import re
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
EXT = os.path.join(OUT, "lvs_tail_block", "tail_block_extracted.cir")


def subckt_ports(txt: str, cell: str = "tail_block") -> list[str]:
    """Parse .SUBCKT ports including SPICE '+' continuation lines."""
    m = re.search(
        rf"\.SUBCKT\s+{re.escape(cell)}\s+((?:[^\n]+)(?:\n\+[^\n]*)*)",
        txt, re.I)
    if not m:
        return []
    body = m.group(1)
    # Stop before first device / comment / .ENDS if regex over-ate (no + lines).
    ports = []
    for tok in body.replace("\n+", " ").replace("+", " ").split():
        if tok.startswith("M$") or tok.startswith("R$") or tok.startswith("C$"):
            break
        if tok.startswith(".") or "=" in tok:
            break
        ports.append(tok)
    return ports


def main():
    if not os.path.exists(EXT):
        print(f"MISSING {EXT}")
        return 2
    txt = open(EXT, errors="ignore").read()
    ports = subckt_ports(txt)
    if not ports:
        print("NO_SUBCKT")
        return 2
    print(f"ports: {' '.join(ports)}")
    print(f"n_ports: {len(ports)}")
    bad = [p for p in ports if "|" in p]
    if bad:
        print(f"MERGE_FAIL: {bad}")
        return 1
    print("ports_ok: no merged names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
