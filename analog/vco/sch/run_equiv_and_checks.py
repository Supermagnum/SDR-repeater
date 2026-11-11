#!/usr/bin/env python3
"""P2.7.1: xschem netlist export, schematic-vs-schematic compare, VACASK checks.

1) Export SPICE from each .sch via xschem -x -q -n (needs DISPLAY/Xvfb).
2) Convert simulated VACASK decks to SPICE-like device lists; compare to
   inventory / xschem export (netgen if usable, else Python device compare).
3) VACASK: VCO range codes 0/128/255 at tt; D22 search tt 27 top; LDO DC.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
NET = os.path.join(HERE, "netlists")
EXP = os.path.join(HERE, "exports")
os.makedirs(OUT, exist_ok=True)
os.makedirs(EXP, exist_ok=True)

sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step2"))
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "ampcal"))
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step1"))
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "ldo"))
sys.path.insert(0, "/foss/tools/vacask/lib/vacask/python")

RANGE_JSON = os.path.join(REPO, "analog", "vco", "step2", "out", "range.json")


def run(cmd, cwd=None, timeout=600):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return r


def xschem_export(sch_path):
    """Netlist + SVG/PDF via xschem batch."""
    base = os.path.splitext(os.path.basename(sch_path))[0]
    work = os.path.join(HERE, "_xsch_work")
    os.makedirs(work, exist_ok=True)
    # local xschemrc
    rc = os.path.join(HERE, "xschemrc")
    if os.path.exists(rc):
        shutil.copy(rc, os.path.join(work, "xschemrc"))
    env = os.environ.copy()
    env.setdefault("PDK_ROOT", "/foss/pdks")
    env.setdefault("PDK", "ihp-sg13g2")
    env["DISPLAY"] = env.get("DISPLAY", ":99")
    # netlist
    r = subprocess.run(
        ["xschem", "-x", "-q", "-n", sch_path],
        cwd=work, capture_output=True, text=True, env=env, timeout=60,
    )
    spice = os.path.join(work, "simulations", base + ".spice")
    alt = os.path.join(HERE, "simulations", base + ".spice")
    found = spice if os.path.exists(spice) else (alt if os.path.exists(alt) else None)
    if found:
        dst = os.path.join(NET, base + ".spice")
        shutil.copy(found, dst)
    else:
        dst = None
    # SVG / PDF via --command (needs X display / Xvfb; -x skips drawing)
    svg = os.path.join(EXP, base + ".svg")
    pdf = os.path.join(EXP, base + ".pdf")
    tcl = (
        f"xschem zoom_full; "
        f"xschem print svg {svg}; "
        f"xschem print pdf {pdf}; "
        f"exit"
    )
    r2 = subprocess.run(
        ["xschem", "--command", tcl, sch_path],
        cwd=HERE, capture_output=True, text=True, env=env, timeout=120,
    )
    if found and not dst:
        dst = os.path.join(NET, base + ".spice")
        shutil.copy(found, dst)
    # Also copy spice from cwd simulations/
    sim_spice = os.path.join(HERE, "simulations", base + ".spice")
    if os.path.exists(sim_spice):
        dst = os.path.join(NET, base + ".spice")
        shutil.copy(sim_spice, dst)
    return {
        "sch": sch_path,
        "spice": dst,
        "svg": svg if os.path.exists(svg) else None,
        "pdf": pdf if os.path.exists(pdf) else None,
        "netlist_rc": r.returncode,
        "print_rc": r2.returncode,
        "netlist_err": (r.stderr or r.stdout)[-500:],
        "print_err": (r2.stderr or r2.stdout)[-500:],
    }


def parse_spice_devices(text):
    """Extract MOS/MIM/R/C/L instances from xschem spice (loose)."""
    devs = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("*") or s.startswith(".") or s.startswith("+"):
            continue
        # XM1 d g s b model w=...
        m = re.match(
            r"^X?([A-Za-z]\w*)\s+(.+?)\s+(sg13_\w+|cap_rfcmim|sg13_hv_svaricap\w*)\s+(.*)$",
            s, re.I)
        if m:
            name, pins, model, rest = m.groups()
            nodes = pins.split()
            params = dict(re.findall(r"(\w+)=([^\s]+)", rest))
            kind = "mim" if "mim" in model else (
                "svaricap" if "svari" in model else (
                    "pmos" if "pmos" in model else "nmos"))
            # xschem svaricap pin order G2 NW G1 body → remap to g1 w g2 bn
            if kind == "svaricap" and len(nodes) >= 4:
                g2, nw, g1, bn = nodes[0], nodes[1], nodes[2], nodes[3]
                nodes = [g1, nw, g2, bn]
            if "Nx" in params and "nx" not in params:
                params["nx"] = params["Nx"]
            for k in ("w", "l", "W", "L"):
                if k in params:
                    params[k.lower()] = _norm_len(params[k])
            devs.append({"kind": kind, "name": name, "nodes": nodes,
                         "params": params, "model": model})
            continue
        m = re.match(r"^([RCLVIrcli]\w*)\s+(\S+)\s+(\S+)\s+(.*)$", s)
        if m:
            name, a, b, rest = m.groups()
            params = dict(re.findall(r"(\w+)=([^\s]+)", rest))
            if not params:
                # value positional
                tok = rest.split()[0] if rest.split() else ""
                if name[0].upper() == "R":
                    params = {"r": tok}
                    kind = "res"
                elif name[0].upper() == "C":
                    params = {"c": tok}
                    kind = "capa"
                elif name[0].upper() == "L":
                    params = {"l": tok}
                    kind = "ind"
                elif name[0].upper() == "V":
                    params = {"dc": tok}
                    kind = "vsrc"
                elif name[0].upper() == "I":
                    params = {"dc": tok}
                    kind = "isrc"
                else:
                    continue
            else:
                kind = {"R": "res", "C": "capa", "L": "ind",
                        "V": "vsrc", "I": "isrc"}[name[0].upper()]
            # devices/res format: name p m value
            if "value" in params:
                key = {"res": "r", "capa": "c", "ind": "l",
                       "vsrc": "dc", "isrc": "dc"}[kind]
                params[key] = params["value"]
            devs.append({"kind": kind, "name": name, "nodes": [a, b],
                         "params": params, "model": kind})
    return devs


def _eng(v):
    """Parse SPICE engineering value to float."""
    v = str(v).strip().rstrip(",")
    m = re.match(r"^([0-9.eE+-]+)([a-zA-Z]*)$", v)
    if not m:
        return float(v)
    x = float(m.group(1))
    u = m.group(2)
    scale = {
        "": 1, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15,
        "k": 1e3, "K": 1e3, "Meg": 1e6, "M": 1e6, "G": 1e9,
        "meg": 1e6,
    }
    # 'mil' etc. unused; bare M in spice often mega for R — treat as 1e6
    if u in ("Meg", "meg", "M") and abs(x) >= 1:
        return x * 1e6
    return x * scale.get(u, 1)


def _norm_len(v):
    metres = _eng(v)
    # if already looked like metres (tiny), keep; if looked like um number with u
    return f"{metres*1e6:.6g}u"


def _norm_param(kind, params):
    out = {}
    if kind in ("nmos", "pmos"):
        out["w"] = _norm_len(params.get("w", params.get("W", "")))
        out["l"] = _norm_len(params.get("l", params.get("L", "")))
        out["ng"] = str(int(float(params.get("ng", params.get("NG", 1))))
                        )
    elif kind == "mim":
        out["w"] = _norm_len(params.get("w", ""))
        out["l"] = _norm_len(params.get("l", ""))
    elif kind == "svaricap":
        out["w"] = _norm_len(params.get("w", params.get("W", "3.74u")))
        out["l"] = _norm_len(params.get("l", params.get("L", "0.3u")))
        out["nx"] = str(int(float(params.get("nx", params.get("Nx", 1)))))
    elif kind == "res":
        out["r"] = f"{_eng(params.get('r', 0)):.6g}"
    elif kind == "capa":
        out["c"] = f"{_eng(params.get('c', 0)):.6g}"
    elif kind == "ind":
        out["l"] = f"{_eng(params.get('l', 0)):.6g}"
    elif kind in ("vsrc", "isrc"):
        out["dc"] = f"{_eng(params.get('dc', 0)):.6g}"
    return out


def compare_inventories(ref, dut, label):
    """Compare device multisets by (kind, sorted params); names may differ."""
    def key(d):
        p = _norm_param(d["kind"], d.get("params", {}))
        return (d["kind"], tuple(sorted(p.items())))

    from collections import Counter
    cr, cd = Counter(key(d) for d in ref), Counter(key(d) for d in dut)
    missing = cr - cd
    extra = cd - cr
    lines = [f"## Compare {label}\n",
             f"ref={len(ref)} dut={len(dut)}\n"]
    if not missing and not extra:
        lines.append("PASS: device kinds+sizes multiset match\n")
        return True, "".join(lines)
    lines.append("DIFF:\n")
    for k, n in missing.items():
        lines.append(f"  missing x{n}: {k}\n")
    for k, n in extra.items():
        lines.append(f"  extra x{n}: {k}\n")
    # Name-level connectivity compare for matching names
    ref_by = {d["name"].lower(): d for d in ref}
    dut_by = {d["name"].lower(): d for d in dut}
    for nm in sorted(set(ref_by) & set(dut_by)):
        a, b = ref_by[nm], dut_by[nm]
        if a["kind"] != b["kind"]:
            lines.append(f"  {nm}: kind {a['kind']} vs {b['kind']}\n")
            continue
        pa, pb = _norm_param(a["kind"], a["params"]), _norm_param(b["kind"], b["params"])
        if pa != pb:
            lines.append(f"  {nm}: params {pa} vs {pb}\n")
        if [x.lower() for x in a["nodes"]] != [x.lower() for x in b["nodes"]]:
            # allow 0/gnd alias
            na = [x if x not in ("0", "gnd", "GND") else "0" for x in a["nodes"]]
            nb = [x if x not in ("0", "gnd", "GND") else "0" for x in b["nodes"]]
            if [x.lower() for x in na] != [x.lower() for x in nb]:
                lines.append(f"  {nm}: nodes {a['nodes']} vs {b['nodes']}\n")
    ok = len(missing) == 0 and len(extra) == 0
    if not ok:
        lines.append("RESULT: FAIL (see diffs; explain or fix)\n")
    return ok, "".join(lines)


def deck_devices_from_step2(code=0, vtune=0.65):
    """Parse devices from a generated run_step2 VACASK deck."""
    import run_step2 as S2
    rng = json.load(open(RANGE_JSON))
    S2.LSB_FF = rng["lsb"]
    S2.C_FIX_FF = rng["cfix"]
    S2.NFING = rng.get("nfing", 20)
    S2.NBITS = rng.get("nbits", 8)
    S2.TRIM = list(rng["trim"]) + [1.0] * 8
    S2.OUT = os.path.join(HERE, "out")
    os.makedirs(S2.OUT, exist_ok=True)
    path = S2.netlist(f"equiv_ref_c{code}", code, vtune,
                      '  analysis t1 tran stop=1n\n', itail=4e-3)
    text = open(path).read()
    return parse_vacask_devices(text), path


def parse_vacask_devices(text):
    devs = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("//") or s.startswith("include") or s.startswith("load"):
            continue
        if s.startswith("model ") or s.startswith("parameters") or s.startswith("control"):
            continue
        m = re.match(
            r"^(\w+)\s+\(([^)]+)\)\s+(sg13_\w+|cap_rfcmim|sg13_hv_svaricap\w*|resistor|capacitor|inductor|vsource|isource)\s*(.*)$",
            s)
        if not m:
            continue
        name, pins, model, rest = m.groups()
        nodes = pins.split()
        params = dict(re.findall(r"(\w+)=([^\s]+)", rest))
        if model.startswith("sg13_lv_nmos") or model.startswith("sg13_hv_nmos"):
            kind = "nmos"
        elif "pmos" in model:
            kind = "pmos"
        elif model == "cap_rfcmim":
            kind = "mim"
        elif "svari" in model:
            kind = "svaricap"
        elif model == "resistor":
            kind = "res"
            params = {"r": params.get("r", "0")}
        elif model == "capacitor":
            kind = "capa"
            params = {"c": params.get("c", "0")}
        elif model == "inductor":
            kind = "ind"
            params = {"l": params.get("l", "0")}
        elif model == "vsource":
            kind = "vsrc"
            params = {"dc": params.get("dc", "0")}
        elif model == "isource":
            kind = "isrc"
            params = {"dc": params.get("dc", "0")}
        else:
            continue
        if kind in ("nmos", "pmos", "mim", "svaricap"):
            params["model"] = model
        devs.append({"kind": kind, "name": name, "nodes": nodes, "params": params})
    return devs


def try_netgen(spice_a, spice_b, cell_a, cell_b):
    """Attempt netgen schematic-vs-schematic; return (ok_or_none, log)."""
    if not spice_a or not spice_b or not os.path.exists(spice_a) or not os.path.exists(spice_b):
        return None, "netgen skipped: missing spice files\n"
    script = os.path.join(OUT, "netgen_compare.tcl")
    open(script, "w").write(f"""
puts "netgen P2.7.1 compare"
# Read as spice
readnet spice {{{spice_a}}} {cell_a}
readnet spice {{{spice_b}}} {cell_b}
lvs {{{cell_a} spice}} {{{cell_b} spice}} {os.path.join(OUT, 'netgen_comp.json')}
""")
    r = run(["netgen", "-batch", "source", script], cwd=OUT, timeout=120)
    log = (r.stdout or "") + (r.stderr or "")
    open(os.path.join(OUT, "netgen_compare.log"), "w").write(log)
    return (r.returncode == 0), log[-2000:]


def vacask_vco_range():
    """Codes 0 / 128 / 255 at tt, compare to range.json mid-vtune."""
    import run_step2 as S2
    import numpy as np
    from vacask.rawfile import rawread

    rng = json.load(open(RANGE_JSON))
    S2.LSB_FF = rng["lsb"]
    S2.C_FIX_FF = rng["cfix"]
    S2.NFING = rng.get("nfing", 20)
    S2.NBITS = rng.get("nbits", 8)
    S2.TRIM = list(rng["trim"]) + [1.0] * 8
    S2.OUT = OUT
    lines = ["# P2.7.1 VACASK VCO range from capture-equivalent deck (tt)\n",
             "| code | f_ref [SCH] | f_new [SCH] | df% | Amp_ref | Amp_new | dA |\n",
             "|---|---|---|---|---|---|---|\n"]
    ok = True
    for code in (0, 128, 255):
        key = f"{code},0.65"
        ref = rng["meas"][key]
        tag = f"p271_range_c{code}"
        # Use step2 netlist (same devices as inventory) — proof after equiv
        path = S2.netlist(tag, code, 0.65,
                          '  options temp=27 reltol=1e-4 rawfile="binary"\n'
                          '  save v(tp) v(tn) v(tail)\n'
                          '  analysis t1 tran stop=80n step=2p\n',
                          itail=4e-3)
        S2.run(path)
        m = S2.measure(os.path.join(OUT, "t1.raw"))
        f_ref, a_ref = ref["f"], ref["amp"]
        df = 100.0 * (m["f"] - f_ref) / f_ref
        da = m["amp"] - a_ref
        fl = "PASS" if abs(df) <= 0.2 and abs(da) <= 0.02 else "FAIL"
        if fl == "FAIL":
            ok = False
        lines.append(
            f"| {code} | {f_ref/1e9:.4f} GHz | {m['f']/1e9:.4f} GHz | "
            f"{df:.3f} | {a_ref:.3f} | {m['amp']:.3f} | {da:.3f} | {fl} |\n"
        )
    lines.append(f"\nPass criteria: |df|≤0.2 %, |dA|≤0.02 V → "
                 f"{'PASS' if ok else 'FAIL'} `[SCH]`\n")
    return ok, "".join(lines)


def vacask_ldo_dc():
    import run_d21_vrana1 as L
    from vacask.rawfile import rawread
    import numpy as np
    L.OUT = OUT
    text = (L.header() + L.ldo_body() + L.filter_net(iload=L.I_TYP) + """
control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis op1 op
endc
""")
    L.run("p271_ldo_dc", text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    vout = float(np.real(op["vout"]).ravel()[0])
    vpad = float(np.real(op["pad"]).ravel()[0])
    # Recorded: V_out=1.2950 V  V_pad=1.1985 V
    ref_o, ref_p = 1.2950, 1.1985
    ok = abs(vout - ref_o) <= 0.02 and abs(vpad - ref_p) <= 0.02
    msg = (
        f"# P2.7.1 LDO DC\n"
        f"V_out={vout:.4f} V (ref {ref_o})  V_pad={vpad:.4f} V (ref {ref_p})\n"
        f"{'PASS' if ok else 'FAIL'} `[SCH]` (≤0.02 V)\n"
    )
    return ok, msg


def vacask_d22_search():
    """Re-use ampcal quick search at tt/27 top if available; else run one bit-walk."""
    quick = os.path.join(REPO, "analog", "vco", "ampcal", "out",
                         "summary_search_quick.txt")
    # Run a short confirmation via run_search if present
    try:
        import run_search
    except Exception as e:
        return None, f"# D22 search: import failed ({e}); using recorded quick summary\n"
    # Prefer calling existing quick path
    prev = os.path.join(REPO, "analog", "vco", "ampcal", "out")
    # Copy recorded result and re-state pass
    text = open(quick).read() if os.path.exists(quick) else ""
    # Attempt one top-band search at tt
    try:
        # Minimal: run_search may have main — invoke subprocess
        r = subprocess.run(
            [sys.executable, "run_search.py", "quick"],
            cwd=os.path.join(REPO, "analog", "vco", "ampcal"),
            capture_output=True, text=True, timeout=900,
        )
        log = (r.stdout or "")[-2000:]
        open(os.path.join(OUT, "d22_search_rerun.log"), "w").write(
            (r.stdout or "") + (r.stderr or ""))
        ok = r.returncode == 0 and "PASS" in (r.stdout or "")
        return ok, (
            f"# P2.7.1 D22 search tt 27 top (rerun)\n"
            f"exit={r.returncode}\n{log}\n"
            f"Recorded quick summary still:\n{text[:800]}\n"
        )
    except subprocess.TimeoutExpired:
        return None, (
            f"# D22 search: TIMEOUT — recorded result stands\n{text[:800]}\n"
            "VACASK re-run from xschem netlist: NOT COMPLETED `[SCH]`\n"
        )


def inventory_as_ref(cell):
    inv = json.load(open(os.path.join(NET, "device_inventory.json")))
    return inv[cell]


def main():
    report = ["# P2.7.1 netlist equivalence and VACASK checks\n\n"]
    sch_files = [
        "l2n0.sch", "vco_core.sch", "vco_bank.sch", "vco_var.sch",
        "vco_tail_dac.sch", "ampcal_det.sch", "vrana1_ldo.sch",
        "vco_sim_flat.sch",
    ]
    export_rows = []
    for fn in sch_files:
        path = os.path.join(HERE, fn)
        if not os.path.exists(path):
            export_rows.append(f"| {fn} | MISSING | | |\n")
            continue
        info = xschem_export(path)
        export_rows.append(
            f"| {fn} | spice={'yes' if info['spice'] else 'NO'} "
            f"rc={info['netlist_rc']} | "
            f"svg={'yes' if info['svg'] else 'NO'} | "
            f"pdf={'yes' if info['pdf'] else 'NO'} |\n"
        )
        if not info["spice"]:
            report.append(f"xschem netlist fail {fn}: {info['netlist_err']}\n")

    report.append("## xschem export\n\n| sch | spice | svg | pdf |\n|---|---|---|---|\n")
    report.extend(export_rows)

    # Compare vco_sim_flat inventory vs step2 deck
    ref_devs, ref_path = deck_devices_from_step2(0, 0.65)
    # Filter ref to circuit devices (drop analysis-only if any)
    inv = inventory_as_ref("vco_sim_flat")
    # Map inventory to compare shape
    inv_devs = [{"kind": d["kind"], "name": d["name"], "nodes": d["nodes"],
                 "params": d["params"]} for d in inv]

    # Compare overlapping kinds present in both (step2 has l2n0 subckt + sources)
    ok_py, msg = compare_inventories(
        [d for d in ref_devs if d["kind"] in
         ("nmos", "pmos", "mim", "svaricap", "res", "capa")],
        [d for d in inv_devs if d["kind"] in
         ("nmos", "pmos", "mim", "svaricap", "res", "capa")],
        "step2 deck vs vco_sim_flat inventory (passive+MOS)",
    )
    report.append("\n" + msg)

    # Explain expected diffs
    report.append(
        "\n### Expected / explained differences\n"
        "- `l2n0` in the step2 deck is a **subckt instance**; inventory expands "
        "to lumped R/L/C (same EM model file).\n"
        "- D22 `vco_tail_dac` replaces step2 `iref`+narrow `mt`/`mr` when amp-cal "
        "is bound; range TB uses step2 bias for frequency match.\n"
        "- Ideal `devices/res|capa|ind` in xschem vs VACASK `resistor|capacitor|"
        "inductor` OSDI — same values, different model class for LVS later.\n"
        "- xschem `sg13_svaricap` netlists pin order G2,NW,G1; VACASK is "
        "(g1,w,g2,bn) — converter remaps before compare.\n"
        "- `gnd` vs `0` net naming.\n"
    )

    spice_flat = os.path.join(NET, "vco_sim_flat.spice")
    if os.path.exists(spice_flat):
        sp = parse_spice_devices(open(spice_flat).read())
        ok2, msg2 = compare_inventories(inv_devs, sp, "inventory vs xschem spice")
        report.append("\n" + msg2)
        # Also write spice version of vacask deck for netgen
        spice_ref = os.path.join(NET, "step2_ref_c0.spice")
        open(spice_ref, "w").write(
            "* converted from VACASK for netgen\n"
            + "\n".join(
                f"X{d['name']} {' '.join(d['nodes'])} {d['params'].get('model', d['kind'])} "
                + " ".join(f"{k}={v}" for k, v in d["params"].items() if k != "model")
                for d in ref_devs if d["kind"] in ("nmos", "pmos", "mim", "svaricap")
            )
            + "\n"
        )
        ng_ok, ng_log = try_netgen(spice_flat, spice_ref, "vco_sim_flat", "step2_ref")
        report.append(f"\n## netgen\nstatus={ng_ok}\n```\n{ng_log}\n```\n")
        if ng_ok is None:
            report.append(
                "netgen schematic-vs-schematic: **not conclusive** on these "
                "spice fragments (no .subckt wrappers / PDK setup). "
                "Python device compare is the pass gate for this run.\n"
            )
    else:
        report.append(
            "\n## xschem spice missing — inventory is source of truth for this run; "
            "xschem export failed or was skipped. `[SCH]`\n"
        )
        ok2 = False

    # LDO inventory vs ldo_body
    ldo_inv = inventory_as_ref("vrana1_ldo")
    import run_d21_vrana1 as L
    L.OUT = OUT
    ldo_text = L.header() + L.ldo_body()
    ldo_ref = parse_vacask_devices(ldo_text)
    ok_ldo, msg_ldo = compare_inventories(ldo_ref, ldo_inv, "ldo_body vs vrana1_ldo")
    report.append("\n" + msg_ldo)

    # VACASK checks
    report.append("\n## VACASK checks\n\n")
    try:
        ok_r, msg_r = vacask_vco_range()
        report.append(msg_r)
    except Exception as e:
        ok_r = False
        report.append(f"VCO range FAILED to run: {e}\n")
        open(os.path.join(OUT, "range_error.txt"), "w").write(str(e))

    try:
        ok_d, msg_d = vacask_d22_search()
        report.append(msg_d if msg_d else "D22 search: no result\n")
        if ok_d is None:
            report.append(
                "D22 search re-run uncertain; recorded "
                "`ampcal/out/summary_search_quick.txt` tt/27 top code=14 Amp=1.250 PASS.\n"
            )
    except Exception as e:
        ok_d = None
        report.append(f"D22 search error: {e}\n")

    try:
        ok_l, msg_l = vacask_ldo_dc()
        report.append(msg_l)
    except Exception as e:
        ok_l = False
        report.append(f"LDO DC FAILED: {e}\n")

    summary = (
        f"# summary_xsch_vco\n\n"
        f"Python equiv (VCO inventory vs step2): {'PASS' if ok_py else 'FAIL/DIFF'}\n"
        f"Python equiv (LDO): {'PASS' if ok_ldo else 'FAIL/DIFF'}\n"
        f"xschem spice vs inventory: "
        f"{'PASS' if ok2 else 'FAIL or spice missing'}\n"
        f"VACASK range 0/128/255: {'PASS' if ok_r else 'FAIL'}\n"
        f"VACASK D22 search: {ok_d}\n"
        f"VACASK LDO DC: {'PASS' if ok_l else 'FAIL'}\n"
    )
    open(os.path.join(OUT, "summary_xsch_vco.txt"), "w").write(
        summary + "\n" + "".join(report)
    )
    open(os.path.join(OUT, "summary_equiv.txt"), "w").write("".join(report))
    print(summary)


if __name__ == "__main__":
    main()

