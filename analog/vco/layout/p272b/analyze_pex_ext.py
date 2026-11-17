#!/usr/bin/env python3
"""Parse Magic .ext: node C + coupling on tn/tp after merge/equiv. aF -> fF /1000."""
from __future__ import annotations

from collections import defaultdict
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


# Prefer port-like names as union-find roots so tn/tp survive merges.
_PORT_PREF = (
    "tn", "tp", "gnd", "vdd", "ct", "tail", "sub!", "0",
)


def parse_ext(path: str):
    parent: dict[str, str] = {}

    def find(a: str) -> str:
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def rank(n: str) -> int:
        if n in _PORT_PREF:
            return _PORT_PREF.index(n)
        return 100 + len(n)

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        # Keep preferred port name as root
        if rank(rb) < rank(ra):
            ra, rb = rb, ra
        parent[rb] = ra

    node_c: dict[str, float] = {}
    caps: list[tuple[str, str, float]] = []
    for ln in open(path):
        toks = ln.split()
        if not toks:
            continue
        if toks[0] == "node" and len(toks) >= 4:
            name = toks[1].strip('"')
            try:
                c = float(toks[3])
            except ValueError:
                continue
            node_c[name] = node_c.get(name, 0.0) + c
        elif toks[0] in ("merge", "equiv") and len(toks) >= 3:
            union(toks[1].strip('"'), toks[2].strip('"'))
        elif toks[0] == "cap" and len(toks) >= 4:
            a = toks[1].strip('"')
            b = toks[2].strip('"')
            c = float(toks[3])
            caps.append((a, b, c))
    return find, node_c, caps


def to_ff(af: float) -> float:
    return af / 1000.0


def analyze(ext_path: str, label: str) -> str:
    find, node_c, caps = parse_ext(ext_path)
    sub_tn = sub_tp = 0.0
    for n, c in node_c.items():
        r = find(n)
        if r == "tn":
            sub_tn += c
        if r == "tp":
            sub_tp += c

    coup_tn: dict[str, float] = defaultdict(float)
    coup_tp: dict[str, float] = defaultdict(float)
    c_tn_tp = 0.0
    for a, b, c in caps:
        ra, rb = find(a), find(b)
        if ra == rb:
            continue
        if ra == "tn":
            coup_tn[rb] += c
            if rb == "tp":
                c_tn_tp += c
        elif rb == "tn":
            coup_tn[ra] += c
            if ra == "tp":
                c_tn_tp += c
        if ra == "tp":
            coup_tp[rb] += c
        elif rb == "tp":
            coup_tp[ra] += c

    def is_gnd_like(k: str) -> bool:
        r = find(k)
        if r in {"gnd", "sub!", "vdd", "ct", "0", "tail"}:
            return True
        if "sub!" in k or k.endswith("/gnd") or r.endswith("gnd"):
            return True
        return False

    def side_totals(coup, sub_c):
        c_g = sum(v for k, v in coup.items() if is_gnd_like(k))
        c_all = sum(coup.values())
        return to_ff(sub_c + c_g), to_ff(sub_c + c_all)

    c_tn_g, c_tn_all = side_totals(coup_tn, sub_tn)
    c_tp_g, c_tp_all = side_totals(coup_tp, sub_tp)
    mismatch = abs(c_tn_all - c_tp_all)

    lines = []
    lines.append(f"# {label} [PEX-RC]\n\n")
    lines.append(f"Source: `{ext_path}`\n")
    lines.append("Units: Magic .ext aF / 1000 = fF.\n")
    lines.append(
        "Intentional rfcmim / MOSFET models are devices (not in these "
        "cap lines); numbers below are interconnect + area parasitics.\n\n"
    )
    lines.append(
        f"| quantity | tn | tp | unit |\n"
        f"|---|---:|---:|---|\n"
        f"| substrate node C | {to_ff(sub_tn):.3f} | {to_ff(sub_tp):.3f} | fF |\n"
        f"| C to gnd-like + substrate | {c_tn_g:.3f} | {c_tp_g:.3f} | fF |\n"
        f"| C all partners + substrate | {c_tn_all:.3f} | {c_tp_all:.3f} | fF |\n"
        f"| tn−tp mismatch (|all|) | {mismatch:.3f} | | fF |\n"
        f"| C(tn−tp) coupling | {to_ff(c_tn_tp):.3f} | | fF |\n"
    )
    lines.append("\n## Top coupling partners (tn)\n\n")
    for k, v in sorted(coup_tn.items(), key=lambda x: -abs(x[1]))[:15]:
        lines.append(f"- `{k}`: {to_ff(v):.4f} fF\n")
    lines.append("\n## Top coupling partners (tp)\n\n")
    for k, v in sorted(coup_tp.items(), key=lambda x: -abs(x[1]))[:15]:
        lines.append(f"- `{k}`: {to_ff(v):.4f} fF\n")

    # Headline "added C per side" = all partners + substrate (wiring load)
    add = 0.5 * (c_tn_all + c_tp_all)
    lines.append("\n## Headline\n\n")
    lines.append(
        f"- Added C per side (mean of all+substrate): **{add:.2f} fF** [PEX-RC]\n"
        f"- tn / tp: **{c_tn_all:.2f} / {c_tp_all:.2f} fF** [PEX-RC]\n"
        f"- tn−tp mismatch: **{mismatch:.2f} fF** [PEX-RC]\n"
        f"- Series R: not extracted (extresist not run) — see note.\n"
    )
    return "".join(lines), {
        "c_tn": c_tn_all,
        "c_tp": c_tp_all,
        "c_mean": add,
        "mismatch": mismatch,
        "c_tn_tp": to_ff(c_tn_tp),
    }


def main():
    ext = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "out", "pex_core", "vco_core_tank.ext"
    )
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        HERE, "out", "summary_pex_core_tank.txt"
    )
    report, nums = analyze(ext, "Magic RC extract — vco_core_tank tn/tp")
    open(out, "w").write(report)
    print(report)
    print("NUMS", nums)
    print("Wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
