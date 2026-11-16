#!/usr/bin/env python3
"""Compare SVaricap w / l / Nx against schematic intent [TOOL].

Why not netgen alone
--------------------
In the vco_var LVS export the SVaricap well pin is named **W** (PCell pin
text). That same net is schematic **vt** (V_tune). Netgen therefore sees a
port called W; that is a **net name**, not the device width property.
Netgen also reports "No property ng found" / incomplete property compare on
sg13_hv_svaricap (same class as #753 for Nx). So a green netgen run does
**not** prove w / l / Nx.

This script reads:
  - schematic / LVS spice intent (w, l, Nx)
  - KLayout extracted cir (w, l, Nx)
  - GDS PCell instance parameters (when present)

Pass: every extracted device matches intent within tol.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# Schematic / layout intent [SCH] vco_var / ampcal
INTENT = {"w": 3.74, "l": 0.3, "Nx": 10}  # µm, µm, count
TOL_UM = 0.02


def parse_spice(path):
    """Return list of {w,l,Nx} from sg13_hv_svaricap lines."""
    if not os.path.exists(path):
        return []
    txt = open(path, errors="ignore").read()
    out = []
    for m in re.finditer(
        r"sg13_hv_svaricap\s+([^\n]+)", txt, re.I
    ):
        props = m.group(1)
        d = {}
        for k, pat in (
            ("w", r"w=([\d.]+)u"),
            ("l", r"l=([\d.]+)u"),
            ("Nx", r"Nx=(\d+)"),
        ):
            mm = re.search(pat, props, re.I)
            if mm:
                d[k] = float(mm.group(1)) if k != "Nx" else int(mm.group(1))
        if d:
            out.append(d)
    return out


def parse_gds_pcell():
    """Read SVaricap PCell params from vco_var.gds if klayout API available."""
    gds = os.path.join(OUT, "vco_var.gds")
    gz = gds + ".gz"
    if not os.path.exists(gds) and os.path.exists(gz):
        import gzip
        import shutil
        with gzip.open(gz, "rb") as fi, open(gds, "wb") as fo:
            shutil.copyfileobj(fi, fo)
    if not os.path.exists(gds):
        return []
    try:
        sys.path[:0] = [
            "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python",
            "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python/pycell4klayout-api/source/python",
        ]
        import pya  # noqa: E402
    except Exception as e:
        return [{"error": str(e)}]
    ly = pya.Layout()
    ly.read(gds)
    found = []

    def walk(cell):
        for inst in cell.each_inst():
            c = ly.cell(inst.cell_index)
            if "svaricap" in c.name.lower():
                # PCell parameters via cell name encoding or pdlist
                rec = {"cell": c.name}
                try:
                    # Some builds expose parameters on the instance
                    if inst.is_pcell_variant():
                        for p in inst.pcell_parameters_by_name():
                            if p in ("w", "l", "Nx", "nx"):
                                rec[p if p != "nx" else "Nx"] = inst.pcell_parameter(p)
                except Exception:
                    pass
                found.append(rec)
            walk(c)

    walk(ly.top_cell())
    return found


def match(got, intent):
    ok = True
    msgs = []
    for k, want in intent.items():
        if k not in got:
            ok = False
            msgs.append(f"{k}: missing")
            continue
        g = got[k]
        if k == "Nx":
            if int(g) != int(want):
                ok = False
                msgs.append(f"Nx={g} != {want}")
            else:
                msgs.append(f"Nx={g} OK")
        else:
            if abs(float(g) - float(want)) > TOL_UM:
                ok = False
                msgs.append(f"{k}={g} != {want}±{TOL_UM}")
            else:
                msgs.append(f"{k}={g} OK")
    return ok, "; ".join(msgs)


def main():
    spice = os.path.join(OUT, "vco_var.spice")
    # extracted may live under lvs_vco_var/
    ext = None
    for root, _, files in os.walk(os.path.join(OUT, "lvs_vco_var")):
        for f in files:
            if f.endswith("_extracted.cir"):
                ext = os.path.join(root, f)
    lines = [
        "# SVaricap dimension check — P2.7.2b vco_var [TOOL]\n\n",
        "## Why scripted\n",
        "Port **W** in the LVS netlist is the SVaricap **well** pin (schematic "
        "**vt**), not device width. Netgen property compare on "
        "`sg13_hv_svaricap` is incomplete (#753-class). Compare w/l/Nx here.\n\n",
        f"## Intent [SCH]\n`w={INTENT['w']}u l={INTENT['l']}u Nx={INTENT['Nx']}`\n\n",
    ]
    ok_all = True

    sch_devs = parse_spice(spice)
    lines.append(f"## LVS spice (`vco_var.spice`) — {len(sch_devs)} device(s)\n")
    for i, d in enumerate(sch_devs):
        ok, msg = match(d, INTENT)
        ok_all = ok_all and ok
        lines.append(f"- [{i}] {d} → {msg} → {'PASS' if ok else 'FAIL'}\n")

    ext_devs = parse_spice(ext) if ext else []
    lines.append(f"\n## Extracted (`{os.path.basename(ext) if ext else 'missing'}`) "
                 f"— {len(ext_devs)} device(s)\n")
    if not ext:
        lines.append("- extracted cir not found [TOOL]\n")
        ok_all = False
    for i, d in enumerate(ext_devs):
        ok, msg = match(d, INTENT)
        ok_all = ok_all and ok
        lines.append(f"- [{i}] {d} → {msg} → {'PASS' if ok else 'FAIL'}\n")

    if len(ext_devs) != len(sch_devs):
        lines.append(
            f"\nCount mismatch spice={len(sch_devs)} extract={len(ext_devs)} "
            "(parallel merge may reduce count) [TOOL]\n")
        # After combine_devices, 2 identical may merge to 1 — still OK if dims match
        if ext_devs and all(match(d, INTENT)[0] for d in ext_devs):
            lines.append("Extracted dims still match intent after merge.\n")
        else:
            ok_all = False

    gds = parse_gds_pcell()
    lines.append(f"\n## GDS PCell walk — {len(gds)} SVaricap-named cell(s)\n")
    for g in gds:
        lines.append(f"- {g}\n")

    lines.append(f"\n## Result: {'PASS' if ok_all else 'FAIL'}\n")
    path = os.path.join(OUT, "summary_svaricap_dims.txt")
    open(path, "w").writelines(lines)
    print("".join(lines))
    print(f"Wrote {path}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
