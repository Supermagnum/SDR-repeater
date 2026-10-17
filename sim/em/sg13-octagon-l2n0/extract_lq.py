# Differential series L and Q from a 2-port description.
# L = Im(Zdiff) / omega, Q = Im(Zdiff) / Re(Zdiff),
# Zdiff = Z11 - Z12 - Z21 + Z22, Z0 = 50 ohm.
# This is the same definition as gds2openEMS run_inductor_2port.py.
# No port de-embedding is applied.

import json
import math
import sys

import numpy as np


def s_to_zdiff(s11, s21, s12, s22, z0=50.0):
    s = np.array([[s11, s12], [s21, s22]], dtype=complex)
    i = np.eye(2)
    z = z0 * (i + s) @ np.linalg.inv(i - s)
    return z[0, 0] - z[0, 1] - z[1, 0] + z[1, 1]


def lq(freq_hz, zdiff):
    omega = 2 * math.pi * freq_hz
    return zdiff.imag / omega, zdiff.imag / zdiff.real


def from_s2p(path, targets):
    freq = []
    rows = []
    freq_scale = 1.0
    form = "MA"
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("!"):
                continue
            if line.startswith("#"):
                tokens = line[1:].split()
                unit = tokens[0].lower()
                freq_scale = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}[unit]
                form = tokens[2].upper()
                continue
            parts = line.split()
            freq.append(float(parts[0]) * freq_scale)
            rows.append([float(x) for x in parts[1:]])
    out = []
    for target in targets:
        idx = int(np.argmin([abs(f - target) for f in freq]))
        f = freq[idx]
        pair = rows[idx]
        def cx(i):
            a = pair[i]
            b = pair[i + 1]
            if form == "RI":
                return complex(a, b)
            if form == "DB":
                mag = 10 ** (a / 20.0)
                ang = math.radians(b)
                return mag * complex(math.cos(ang), math.sin(ang))
            ang = math.radians(b)
            return a * complex(math.cos(ang), math.sin(ang))
        # Touchstone order: S11 S21 S12 S22.
        zdiff = s_to_zdiff(cx(0), cx(2), cx(4), cx(6))
        series_l, q = lq(f, zdiff)
        out.append({
            "requested_Hz": target,
            "frequency_Hz": f,
            "L_nH": series_l * 1e9,
            "Q": q,
            "R_ohm": zdiff.real,
        })
    return out


def from_palace_csv(path, targets):
    header = None
    samples = []
    with open(path) as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if header is None and "Hz" in line:
                header = line.replace(",", "")
                continue
            if header is None:
                continue
            items = line.replace(",", "").split()
            if "NULL" in items:
                continue
            samples.append(items)
    # Header columns after the frequency: |Sij| arg pairs.
    # Frequency unit is the token in parentheses.
    unit = "Hz"
    for token in header.replace("(", " ").replace(")", " ").split():
        if token in ("Hz", "kHz", "MHz", "GHz"):
            unit = token
    scale = {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}[unit]
    out = []
    for target in targets:
        best = None
        for items in samples:
            f = float(items[0]) * scale
            if best is None or abs(f - target) < abs(best[0] - target):
                best = (f, items)
        f, items = best
        def cx(pair_index):
            mag_db = float(items[1 + 2 * pair_index])
            ang = math.radians(float(items[2 + 2 * pair_index]))
            mag = 10 ** (mag_db / 20.0)
            return mag * complex(math.cos(ang), math.sin(ang))
        # Palace column order follows the header. The usual order is
        # S11, S12, S21, S22. Re-read the header to map names.
        names = []
        for token in header.split():
            if token.startswith("|S"):
                names.append(token)
        mapped = {}
        for i, name in enumerate(names):
            mapped[name] = cx(i)
        def grab(*cands):
            for cand in cands:
                if cand in mapped:
                    return mapped[cand]
            raise KeyError(names)
        zdiff = s_to_zdiff(
            grab("|S[1][1]|"),
            grab("|S[2][1]|"),
            grab("|S[1][2]|"),
            grab("|S[2][2]|"))
        series_l, q = lq(f, zdiff)
        out.append({
            "requested_Hz": target,
            "frequency_Hz": f,
            "L_nH": series_l * 1e9,
            "Q": q,
            "R_ohm": zdiff.real,
            "header": header,
        })
    return out


def main():
    kind = sys.argv[1]
    path = sys.argv[2]
    targets = [2.4e9, 3.5e9]
    if kind == "s2p":
        rows = from_s2p(path, targets)
    elif kind == "palace":
        rows = from_palace_csv(path, targets)
    else:
        raise SystemExit("kind must be s2p or palace")
    json.dump(rows, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
