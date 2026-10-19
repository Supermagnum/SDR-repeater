#!/usr/bin/env python3
"""Real cell area check: stdcell + macro instance area (no filler) <= limit.

Usage: python3 tools/check_area.py rtl/digital/runs/<tag> [--limit 340000]
"""
import argparse, json, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("run")
ap.add_argument("--limit", type=float, default=340000.0, help="um^2 (decisions.md 2026-10-18)")
a = ap.parse_args()
m = json.load(open(Path(a.run) / "final" / "metrics.json"))
std = float(m["design__instance__area__stdcell"])
mac = float(m.get("design__instance__area__macros", 0.0))
fill = float(m.get("design__instance__area__class:fill_cell", 0.0))
die = float(m.get("design__die__area", 0.0))
real = std + mac
print(f"stdcell {std:,.0f} + macro {mac:,.0f} = real {real:,.0f} um^2 "
      f"(limit {a.limit:,.0f}); filler {fill:,.0f}; die {die:,.0f}")
ok = real <= a.limit
print("AREA PASS" if ok else "AREA FAIL")
sys.exit(0 if ok else 1)
