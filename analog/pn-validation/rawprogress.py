#!/usr/bin/env python3
"""Progress of a binary SPICE rawfile, also while it is still being written.

    rawprogress.py <file.raw> [--target 80.5e-6] [--wall <seconds so far>]

Reads only the header and the last complete record. Prints the saved variables, the
number of points, the average time step and the simulated time reached; with --wall it
also projects the run time and file size for --target seconds of simulated time.
"""
import argparse
import os
import struct
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("--target", type=float, default=80.5e-6)
    ap.add_argument("--wall", type=float, default=None)
    a = ap.parse_args()
    with open(a.raw, "rb") as fh:
        head = fh.read(1 << 20)
    i = head.find(b"Binary:\n")
    if i < 0:
        sys.exit(f"{a.raw}: no 'Binary:' marker (empty or not a binary rawfile)")
    lines = head[:i].decode("latin-1").splitlines()
    off = i + len(b"Binary:\n")
    nvar = next(int(l.split(":")[1]) for l in lines if l.startswith("No. Variables:"))
    k = next(n for n, l in enumerate(lines) if l.startswith("Variables:"))
    names = [l.split()[1] for l in lines[k + 1:k + 1 + nvar] if len(l.split()) > 1]
    rec = 8 * nvar
    size = os.path.getsize(a.raw)
    npts = (size - off) // rec
    if npts < 2:
        sys.exit(f"{a.raw}: fewer than two points written")
    with open(a.raw, "rb") as fh:
        fh.seek(off + (npts - 1) * rec)
        t_last = struct.unpack("<d", fh.read(8))[0]
    step = t_last / (npts - 1)
    print(f"{os.path.basename(a.raw)}: saved {', '.join(names)}; {npts:,} points; "
          f"average step {step*1e15:.0f} fs; reached {t_last*1e6:.3f} us "
          f"({100*t_last/a.target:.1f} % of {a.target*1e6:.1f} us)")
    if t_last > 0:
        msg = f"  projected for {a.target*1e6:.1f} us: file {size * a.target / t_last / 1e9:.1f} GB"
        if a.wall:
            h = a.wall * a.target / t_last / 3600
            msg += f", run time {h:.1f} h (from {a.wall/60:.1f} min so far)"
        print(msg)


if __name__ == "__main__":
    main()
