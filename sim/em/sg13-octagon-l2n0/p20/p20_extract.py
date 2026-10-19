#!/usr/bin/env python3
"""L, Q and R of one P2.0 variant at the VCO frequencies, from a Palace port-S.csv or a
Touchstone .s2p. Same definitions as ../extract_lq.py (Zdiff = Z11 - Z12 - Z21 + Z22,
L = Im/omega, Q = Im/Re), which this script reuses.

    p20_extract.py <tag> <solver> <kind: palace|s2p> <file> [<deembedded .s2p>]
Writes out/p20/<tag>.json.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import extract_lq  # noqa: E402

TARGETS = [2.4e9, 3.12e9, 3.5e9, 3.65e9, 4.2e9]


def main():
    tag, solver, kind, path = sys.argv[1:5]
    deemb = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None
    rows = (extract_lq.from_palace_csv(path, TARGETS) if kind == "palace"
            else extract_lq.from_s2p(path, TARGETS))
    # keep only samples within 60 MHz of the requested frequency (the sweep has 50/100 MHz steps)
    rows = [r for r in rows if abs(r["frequency_Hz"] - r["requested_Hz"]) <= 60e6]
    for r in rows:
        r.pop("header", None)
    out = {"tag": tag, "solver": solver, "source": path, "raw": rows}
    if deemb:
        d = [r for r in extract_lq.from_s2p(deemb, TARGETS)
             if abs(r["frequency_Hz"] - r["requested_Hz"]) <= 60e6]
        out["deembedded"] = d
        out["deembedded_source"] = deemb
    for key, env in (("cell_um", "P20_CELL"), ("order", "P20_ORDER"), ("amr", "P20_AMR"),
                     ("filled", "P20_FILLED"), ("seconds", "P20_SECONDS")):
        if os.environ.get(env):
            out[key] = float(os.environ[env])
    os.makedirs(os.path.join(HERE, "out", "p20"), exist_ok=True)
    dst = os.path.join(HERE, "out", "p20", tag + ".json")
    with open(dst, "w") as fh:
        json.dump(out, fh, indent=2)
    for r in rows:
        if abs(r["requested_Hz"] - 3.65e9) < 1:
            print(f"{tag}: {r['frequency_Hz']/1e9:.3f} GHz  L {r['L_nH']:.4f} nH  Q {r['Q']:.2f}  (raw)")
    print("wrote", dst)


if __name__ == "__main__":
    main()
