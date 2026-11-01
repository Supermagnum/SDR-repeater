#!/usr/bin/env python3
"""Extract tapped-L2n0 gates from a Palace 3-port S CSV (dB/deg, f in GHz).

Baseline (P2.0 palF1 design): L ≈ 1.69 nH; Q 14.2 / 15.3 / 16.9 at 3.12 / 3.5 / 4.2 GHz.

Gates:
  - two-port mode (CT open): |ΔL| ≤ 2 %, |ΔQ| ≤ 2 %
  - |V(CT)/Vdiff| under differential drive (CT open) < 0.05
"""
import json
import math
import os
import sys

import numpy as np

BASE = {
    3.12e9: {"L_nH": 1.69, "Q": 14.2},
    3.50e9: {"L_nH": 1.69, "Q": 15.3},
    4.20e9: {"L_nH": 1.69, "Q": 16.9},
}


def dbdeg_to_c(mag_db, ang_deg):
    mag = 10 ** (mag_db / 20.0)
    ang = math.radians(ang_deg)
    return mag * complex(math.cos(ang), math.sin(ang))


def read_palace_s(path):
    """Palace port-S.csv: f(GHz), then |Sij|(dB), arg(Sij)(deg) in order
    S11,S21,S31, S12,S22,S32, S13,S23,S33.
    """
    header = None
    rows = []
    with open(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if header is None:
                header = line
                continue
            rows.append([float(x) for x in line.split(",")])
    data = np.array(rows)
    freq = data[:, 0] * 1e9  # GHz → Hz
    n = 3
    S = np.zeros((len(freq), n, n), dtype=complex)
    col = 1
    # columns: for j in 0..2: for i in 0..2: |S[i][j]|, arg
    for j in range(n):
        for i in range(n):
            S[:, i, j] = [dbdeg_to_c(data[k, col], data[k, col + 1])
                          for k in range(len(freq))]
            col += 2
    return freq, S


def s_to_z(S, z0=50.0):
    n = S.shape[0]
    I = np.eye(n)
    return z0 * (I + S) @ np.linalg.inv(I - S)


def open_port3_2port(S3):
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
    Z = s_to_z(S3, z0)
    I = np.array([1.0, -1.0, 0.0])
    V = Z @ I
    vdiff = V[0] - V[1]
    if abs(vdiff) < 1e-30:
        return float("nan")
    return float(abs(V[2] / vdiff))


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
        L = float(zd.imag / omega)
        Q = float(zd.imag / zd.real) if zd.real != 0 else float("nan")
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
            vct_over_vdiff=vct, lq_ok=bool(lq_ok), vct_ok=bool(vct_ok),
        ))

    lines.append("")
    lines.append("ALL GATES PASS" if all_ok else "GATES FAILED")
    text = "\n".join(lines) + "\n"
    print(text)
    if out_json:
        os.makedirs(os.path.dirname(os.path.abspath(out_json)) or ".",
                    exist_ok=True)
        open(out_json, "w").write(json.dumps(
            {"results": results, "pass": bool(all_ok)}, indent=2))
        md = out_json.rsplit(".", 1)[0] + ".md"
        open(md, "w").write(text)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
