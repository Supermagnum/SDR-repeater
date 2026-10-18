#!/usr/bin/env python3
"""Phase-1 sign-off check on a LibreLane run.

Usage: python3 tools/check_signoff.py rtl/digital/runs/<tag> [--area-limit 340000]

Reads <run>/final/metrics.json. Magic DRC is reported, not gated: its findings
inside the SRAM macro are waived (reports/phase1-review/magic-drc-waiver.md),
so any change in the count has to be checked against that waiver by hand.
"""
import argparse
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("run")
ap.add_argument("--area-limit", type=float, default=340000.0,
                help="real cell area (stdcell + macro) in um^2, decisions.md 2026-10-18")
a = ap.parse_args()
m = json.load(open(Path(a.run) / "final" / "metrics.json"))


def g(key, default=None):
    v = m.get(key, default)
    return default if v is None else float(v)


real_area = g("design__instance__area__stdcell", 0.0) + g("design__instance__area__macros", 0.0)
checks = [
    ("setup WS (ns)", g("timing__setup__ws"), lambda v: v >= 0.0, ">= 0"),
    ("setup TNS (ns)", g("timing__setup__tns"), lambda v: v >= 0.0, "= 0"),
    ("hold WS (ns)", g("timing__hold__ws"), lambda v: v >= 0.08, ">= 0.08 (margin guard)"),
    ("hold TNS (ns)", g("timing__hold__tns"), lambda v: v >= 0.0, "= 0"),
    ("max-cap violations", g("design__max_cap_violation__count"), lambda v: v == 0, "= 0"),
    ("LVS errors", g("design__lvs_error__count"), lambda v: v == 0, "= 0"),
    ("antenna nets", g("antenna__violating__nets"), lambda v: v == 0, "= 0"),
    ("KLayout DRC", g("klayout__drc_error__count"), lambda v: v == 0, "= 0"),
    ("route DRC", g("route__drc_errors"), lambda v: v == 0, "= 0"),
    ("real cell area (um^2)", real_area, lambda v: v <= a.area_limit, f"<= {a.area_limit:,.0f}"),
]
fail = 0
for name, val, ok, rule in checks:
    if val is None:
        print(f"MISSING {name}")
        fail += 1
        continue
    good = ok(val)
    fail += not good
    print(f"{'PASS' if good else 'FAIL'}  {name:24s} {val:>14,.4f}   ({rule})")
print(f"INFO  Magic DRC count          {g('magic__drc_error__count', -1):>14,.0f}   "
      "(waived inside the SRAM; check the waiver if it changed)")
print("SIGN-OFF PASS" if fail == 0 else f"SIGN-OFF FAIL ({fail})")
sys.exit(0 if fail == 0 else 1)
