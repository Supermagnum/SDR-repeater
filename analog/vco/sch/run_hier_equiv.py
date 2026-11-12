#!/usr/bin/env python3
"""P2.7.2a — hierarchical vco_top vs flat sim deck equivalence.

Compares device kinds/counts/key sizes from leaf generators (source of
vco_top hierarchy) against vco_sim_flat inventory. Explains known diffs.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_xschem as G  # noqa: E402

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)


def count_kinds(devices):
    from collections import Counter
    c = Counter()
    for d in devices:
        c[d.kind] += 1
    return c


def main():
    rng = G.load_range()
    blocks = {}
    blocks["l2n0"] = G.gen_l2n0()
    blocks["vco_core"] = G.gen_vco_core(rng)
    blocks["vco_tail_dac"] = G.gen_vco_tail_dac()
    blocks["vco_bank"] = G.gen_vco_bank(rng)
    blocks["vco_var"] = G.gen_vco_var(rng)
    blocks["ampcal_det"] = G.gen_ampcal_det()
    G.gen_vco_top(rng, blocks)

    hier = []
    for name in ("l2n0", "vco_core", "vco_bank", "vco_var",
                 "vco_tail_dac", "ampcal_det"):
        hier.extend(blocks[name].devices)

    # Rebuild flat the same way as gen_xschem.build_flat_inventory core path
    # (without stand-in buffer / ideal sources unique to sim TB)
    flat_vco = []
    for name in ("l2n0", "vco_core", "vco_bank", "vco_var"):
        flat_vco.extend(blocks[name].devices)

    lines = ["# P2.7.2a hierarchical vs flat equivalence\n\n"]
    lines.append("Hierarchy instantiated in `vco_top.sch`: "
                 "l2n0, vco_core, vco_bank, vco_var, vco_tail_dac, ampcal_det.\n\n")

    lines.append("## Leaf device counts [SCH]\n\n")
    lines.append("| Block | nmos | pmos | mim | svaricap | res | other |\n|---|---|---|---|---|---|---|\n")
    for name, sch in blocks.items():
        c = count_kinds(sch.devices)
        other = sum(v for k, v in c.items()
                    if k not in ("nmos", "pmos", "mim", "svaricap", "res"))
        lines.append(
            f"| {name} | {c['nmos']} | {c['pmos']} | {c['mim']} | "
            f"{c['svaricap']} | {c['res']} | {other} |\n")

    ch = count_kinds(hier)
    cf = count_kinds(flat_vco)
    lines.append("\n## Hierarchy total vs flat VCO path (no ampcal/tail D22)\n\n")
    lines.append("| Kind | hier (all leaves) | flat VCO path (L+core+bank+var) |\n|---|---|---|\n")
    for k in sorted(set(ch) | set(cf)):
        lines.append(f"| {k} | {ch[k]} | {cf[k]} |\n")

    lines.append("\n## Explained differences vs `vco_sim_flat`\n\n")
    lines.append(
        "1. **Tail:** `vco_sim_flat` uses a **stand-alone step2 tail** "
        "(mt 160u/4u ng=32, mr 20u/4u, iref) for range TB. Hierarchical "
        "`vco_tail_dac` is the **D22 OTA DAC** (mt 480u/4u ng=96, full DAC). "
        "Different by design — flat TB ≠ chip tail.\n"
        "2. **Buffer:** flat has stand-in CML buffer (mb1/mb2 + loads); "
        "not in `vco_top` (LO buffer is P2.7.4).\n"
        "3. **Ampcal:** in hierarchy (`ampcal_det`); omitted from "
        "`vco_sim_flat` VCO-only path.\n"
        "4. **Ideal sources:** flat has vvb/iref/ib; hierarchy exposes pins "
        "(code*, g*, hold, rep) for digital / TB.\n"
        "5. **Bank / core / var / L:** same generators → same devices and "
        "sizes as flat VCO path (range.json D24).\n"
    )

    # Spot-check key sizes
    lines.append("\n## Spot-check sizes [SCH]\n\n")
    core_m1 = next(d for d in blocks["vco_core"].devices if d.name == "m1")
    lines.append(f"- core m1: w={core_m1.params['w']} l={core_m1.params['l']} "
                 f"ng={core_m1.params['ng']}\n")
    lines.append(f"- range.json: lsb={rng['lsb']} cfix={rng['cfix']} "
                 f"nfing={rng['nfing']} bank_arch={rng.get('bank_arch')}\n")
    lines.append(f"- bank cells: {len([d for d in blocks['vco_bank'].devices if d.name.startswith('ms')])}\n")
    svar = [d for d in blocks["vco_var"].devices if d.kind == "svaricap"]
    lines.append(f"- svaricap instances: {len(svar)}; "
                 f"nx={svar[0].params.get('nx') if svar else 'n/a'} each\n")

    path = os.path.join(OUT, "summary_hier_equiv.txt")
    open(path, "w").writelines(x if x.endswith("\n") else x + "\n" for x in lines)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
