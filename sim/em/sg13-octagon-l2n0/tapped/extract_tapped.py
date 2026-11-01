#!/usr/bin/env python3
"""Extract tapped-L2n0 gates from a Palace 3-port S CSV.

Baseline (P2.0 palF1 design, reports/phase2-review/p20-stage2.md):
  L ≈ 1.69 nH; Q 14.2 / 15.3 / 16.9 at 3.12 / 3.5 / 4.2 GHz.

Gates:
  - two-port mode (CT open): |L-L0|/L0 ≤ 2 %, |Q-Q0|/Q0 ≤ 2 %
  - |V(CT)/Vdiff| under differential drive (CT open) ≈ 0 (report; soft < 0.05)
"""
import json
import math
import os
import sys

import numpy as np

# Accepted P2.0 design values (de-embedded palF1)
BASE = {
    3.12e9: {"L_nH": 1.69, "Q": 14.2},
    3.50e9: {"L_nH": 1.69, "Q": 15.3},
    4.20e9: {"L_nH": 1.69, "Q": 16.9},
}


def read_palace_s(path):
    """Return freq_Hz array and S[f, i, j] complex (1-indexed ports → 0-based)."""
    header = None
    rows = []
    with open(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if header is None:
                header = [h.strip() for h in line.split(",")]
                continue
            rows.append([float(x) for x in line.split(",")])
    data = np.array(rows)
    # Palace port-S.csv: freq_Hz then Re/Im pairs for Sij
    freq = data[:, 0]
    # Detect n ports from column count: 1 + 2*n*n
    ncols = data.shape[1]
    n2 = (ncols - 1) // 2
    n = int(round(math.sqrt(n2)))
    S = np.zeros((len(freq), n, n), dtype=complex)
    col = 1
    for i in range(n):
        for j in range(n):
            S[:, i, j] = data[:, col] + 1j * data[:, col + 1]
            col += 2
    return freq, S


def s_to_z(S, z0=50.0):
    n = S.shape[0]
    I = np.eye(n)
    return z0 * (I + S) @ np.linalg.inv(I - S)


def open_port3_2port(S3):
    """Reduce 3-port S to 2-port with port 3 open."""
    # S'_ij = S_ij + S_i3 * S_3j / (1 - S_33)
    den = 1.0 - S3[2, 2]
    Sp = np.zeros((2, 2), dtype=complex)
    for i in range(2):
        for j in range(2):
            Sp[i, j] = S3[i, j] + S3[i, 2] * S3[2, j] / den
    return Sp


def zdiff_from_s2(S2, z0=50.0):
    Z = s_to_z(S2, z0)
    return Z[0, 0] - Z[0, 1] - Z[1, 0] + Z[1, 1]


def vct_over_vdiff(S3, z0=50.0):
    """|V3 / (V1-V2)| with I1=-I2, I3=0."""
    Z = s_to_z(S3, z0)
    # V = Z I, I = [1, -1, 0]
    I = np.array([1.0, -1.0, 0.0])
    V = Z @ I
    vdiff = V[0] - V[1]
    if abs(vdiff) < 1e-30:
        return float("nan")
    return abs(V[2] / vdiff)


def nearest(freq, target):
    return int(np.argmin(np.abs(freq - target)))


def main():
    csv = sys.argv[1]
    out_json = sys.argv[2] if len(sys.argv) > 2 else None
    freq, S = read_palace_s(csv)
    if S.shape[1] < 3:
        print("FAIL: need 3-port S-parameters, got", S.shape[1])
        return 1

    lines = ["# Tapped L2n0 EM extract", f"CSV: {csv}", ""]
    lines.append("| f (GHz) | L (nH) | Q | ΔL % | ΔQ % | |Vct/Vdiff| | L/Q | Vct |")
    lines.append("|---|---|---|---|---|---|---|---|")
    all_ok = True
    results = []
    for f0, base in BASE.items():
        i = nearest(freq, f0)
        f = float(freq[i])
        Sp = open_port3_2port(S[i])
        zd = zdiff_from_s2(Sp)
        omega = 2 * math.pi * f
        L = zd.imag / omega
        Q = zd.imag / zd.real if zd.real != 0 else float("nan")
        dL = (L * 1e9 - base["L_nH"]) / base["L_nH"] * 100
        dQ = (Q - base["Q"]) / base["Q"] * 100
        vct = vct_over_vdiff(S[i])
        lq_ok = abs(dL) <= 2.0 and abs(dQ) <= 2.0
        vct_ok = vct <= 0.05
        if not lq_ok or not vct_ok:
            all_ok = False
        lines.append(
            f"| {f/1e9:.3f} | {L*1e9:.4f} | {Q:.2f} | {dL:+.2f} | {dQ:+.2f} | "
            f"{vct:.4f} | {'PASS' if lq_ok else 'MISS'} | "
            f"{'PASS' if vct_ok else 'MISS'} |"
        )
        results.append(dict(
            f_Hz=f, L_nH=L * 1e9, Q=Q, dL_pct=dL, dQ_pct=dQ,
            vct_over_vdiff=vct, lq_ok=lq_ok, vct_ok=vct_ok,
        ))

    lines.append("")
    lines.append("ALL GATES PASS" if all_ok else "GATES FAILED")
    text = "\n".join(lines) + "\n"
    print(text)
    if out_json:
        os.makedirs(os.path.dirname(out_json) or ".", exist_ok=True)
        open(out_json, "w").write(json.dumps(
            {"results": results, "pass": all_ok}, indent=2))
        md = out_json.replace(".json", ".md")
        if md.endswith(".md"):
            open(md, "w").write(text)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
