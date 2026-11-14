#!/usr/bin/env python3
"""Fail if extract SUBCKT ports show merged names (gnd|nbf etc.) [TOOL]."""
from __future__ import annotations

import os
import re
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
EXT = os.path.join(OUT, "lvs_tail_block", "tail_block_extracted.cir")


def main():
    if not os.path.exists(EXT):
        print(f"MISSING {EXT}")
        return 2
    txt = open(EXT, errors="ignore").read()
    m = re.search(r"\.SUBCKT\s+tail_block\s+([^\n]+)", txt, re.I)
    if not m:
        print("NO_SUBCKT")
        return 2
    ports = m.group(1).strip()
    print(f"ports: {ports}")
    bad = [p for p in ports.replace("+", " ").split() if "|" in p]
    if bad:
        print(f"MERGE_FAIL: {bad}")
        return 1
    print("ports_ok: no merged names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
