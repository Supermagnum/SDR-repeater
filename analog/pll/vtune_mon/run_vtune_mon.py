#!/usr/bin/env python3
"""P2.6 open point 1: V_tune window monitor comparators (D20, spec/pll-topology.md).

Run inside the container from this folder:

    mkdir -p out
    python3 -u run_vtune_mon.py | tee out/summary.txt           # trip, hyst, corners, current
    python3 -u run_vtune_mon.py mc n=50 | tee out/summary_mc.txt

Two continuous-time comparators:
  vtune_lo  high when V_tune is below ~0.28 V  → PLL_STATUS[4]
  vtune_hi  high when V_tune is above ~0.90 V  → PLL_STATUS[5]

Low flag: PMOS input pair (below NMOS Vth). High flag: NMOS pair after matched ÷2
(ss / 1.08 V headroom at 0.90 V CM). ~45 mV hysteresis. Ideal 0.28 / 0.90 V sources
are bandgap stand-ins. Tail 5 µA each. Results are [SCH].
"""
import os
import struct
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
ARGS = sys.argv[1:]

os.environ.setdefault("PDK_ROOT", "/foss/pdks")
os.environ.setdefault("PDK", "ihp-sg13g2")
sys.path.append("/foss/tools/vacask/lib/vacask/python")

# Lo: 0.28 V keeps lo_fall (after ~45 mV hyst) below the 0.34 V calibrated floor.
# Hi: option B — V_hi chosen so ss hi_rise+3σ ≤ 0.82 V (ff may trip below ff cal top 0.82 V).
VLO, VHI = 0.28, 0.775
VDD = 1.2
ITAIL = 5e-6
RS, RF = 80e3, 2e6   # lo hyst ≈ VDD·Rs/(Rs+Rf) ≈ 46 mV
RF_HI = 5e6          # normal hi hyst into the ÷2 Thevenin (~40–50 mV input-referred)

HEADER = """{title}

include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section={mos}

load "resistor.osdi"
load "capacitor.osdi"
model resistor resistor
model capacitor capacitor
model vsource vsource
model isource isource
"""

CORNERS = [
    ("tt", "mos_tt", 1.20, 27),
    ("tt 1.08 V", "mos_tt", 1.08, 27),
    ("tt 1.32 V", "mos_tt", 1.32, 27),
    ("ss", "mos_ss", 1.08, 125),
    ("ss −40", "mos_ss", 1.08, -40),
    ("ff", "mos_ff", 1.32, -40),
    ("ff hot", "mos_ff", 1.32, 125),
]


def header(title, mos="mos_tt"):
    return HEADER.format(title=title, mos=mos)


def cmp_lo(n, vin, vth_ideal, out, s1=1.0, s2=1.0):
    """PMOS-input: out high when vin < soft threshold. Soft th = ideal + hyst from out."""
    soft = f"{n}th"
    return (
        f"r{n}s ({soft} {vth_ideal}) resistor r={RS}\n"
        f"r{n}f ({soft} {out}) resistor r={RF}\n"
        f"i{n}t (vdd {n}t) isource dc={ITAIL}\n"
        # m1=threshold, m2=vin → drain b high when vin < soft th
        f"m{n}1 ({n}a {soft} {n}t vdd) sg13_lv_pmos w={8 * s1:.4f}u l=0.5u ng=2\n"
        f"m{n}2 ({n}b {vin} {n}t vdd) sg13_lv_pmos w={8 * s2:.4f}u l=0.5u ng=2\n"
        f"m{n}n1 ({n}a {n}a 0 0) sg13_lv_nmos w=1u l=2u ng=1\n"
        f"m{n}n2 ({n}b {n}a 0 0) sg13_lv_nmos w=1u l=2u ng=1\n"
        # NMOS-heavy inverter: preamp high is capped near the PMOS tail (~0.65 V)
        f"m{n}invp ({n}x {n}b vdd vdd) sg13_lv_pmos w=0.5u l=0.13u\n"
        f"m{n}invn ({n}x {n}b 0 0) sg13_lv_nmos w=1.5u l=0.13u\n"
        f"m{n}bufp ({out} {n}x vdd vdd) sg13_lv_pmos w=1u l=0.13u\n"
        f"m{n}bufn ({out} {n}x 0 0) sg13_lv_nmos w=0.5u l=0.13u\n"
        f"c{n} ({n}x 0) capacitor c=20f\n"
    )


def cmp_hi(n, vin, vth_ideal, out, s1=1.0, s2=1.0):
    """NMOS-input after ÷2: out high when vin > V_hi.

    Matched 200 kΩ dividers keep the pair at ~0.45 V CM (ss / 1.08 V headroom at a
    0.90 V full-scale threshold). Hysteresis: Rf from a rail inverter of out into the
    divided threshold node (not into the ideal source).
    """
    vind = f"{n}vin"   # vin / 2
    thd = f"{n}thd"    # V_hi / 2 ± hyst
    return (
        f"r{n}v1 ({vin} {vind}) resistor r=200k\n"
        f"r{n}v2 ({vind} 0) resistor r=200k\n"
        f"r{n}t1 ({vth_ideal} {thd}) resistor r=200k\n"
        f"r{n}t2 ({thd} 0) resistor r=200k\n"
        f"i{n}t ({n}t 0) isource dc={ITAIL}\n"
        f"m{n}1 ({n}a {vind} {n}t 0) sg13_lv_nmos w={4 * s1:.4f}u l=0.5u ng=2\n"
        f"m{n}2 ({n}b {thd} {n}t 0) sg13_lv_nmos w={4 * s2:.4f}u l=0.5u ng=2\n"
        f"m{n}p1 ({n}a {n}a vdd vdd) sg13_lv_pmos w=2u l=2u ng=1\n"
        f"m{n}p2 ({n}b {n}a vdd vdd) sg13_lv_pmos w=2u l=2u ng=1\n"
        f"m{n}invp ({n}x {n}b vdd vdd) sg13_lv_pmos w=1u l=0.13u\n"
        f"m{n}invn ({n}x {n}b 0 0) sg13_lv_nmos w=0.5u l=0.13u\n"
        f"m{n}bufp ({out} {n}x vdd vdd) sg13_lv_pmos w=1u l=0.13u\n"
        f"m{n}bufn ({out} {n}x 0 0) sg13_lv_nmos w=0.5u l=0.13u\n"
        f"m{n}fbp ({n}fb {out} vdd vdd) sg13_lv_pmos w=1u l=0.13u\n"
        f"m{n}fbn ({n}fb {out} 0 0) sg13_lv_nmos w=0.5u l=0.13u\n"
        f"r{n}f ({thd} {n}fb) resistor r={RF_HI}\n"
        f"c{n} ({out} 0) capacitor c=20f\n"
    )


def monitors(vdd=VDD, slo=(1.0, 1.0), shi=(1.0, 1.0)):
    return (
        f"vdd (vdd 0) vsource dc={vdd}\n"
        f"vlo (vlo 0) vsource dc={VLO}\n"
        f"vhi (vhi 0) vsource dc={VHI}\n"
        + cmp_lo("lo", "vt", "vlo", "vtune_lo", slo[0], slo[1])
        + cmp_hi("hi", "vt", "vhi", "vtune_hi", shi[0], shi[1])
    )


def run_vacask(name, text, analysis):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".sim")
    with open(path, "w") as fh:
        fh.write(text + "\ncontrol\n  abort always\n  options rawfile=\"binary\"\n"
                 + analysis + "\nendc\n")
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(f"vacask {name} failed:\n" + open(log).read()[-800:])
    return os.path.join(OUT, "tr.raw") if "tran" in analysis else os.path.join(OUT, "op1.raw")


def read_raw(path):
    from vacask.rawfile import rawread
    return rawread(path).get()


def _crossings(vt, y, th, rising):
    out = []
    for i in range(len(y) - 1):
        if rising and y[i] < th <= y[i + 1]:
            out.append(vt[i] + (th - y[i]) * (vt[i + 1] - vt[i]) / (y[i + 1] - y[i]))
        if not rising and y[i] >= th > y[i + 1]:
            out.append(vt[i] + (th - y[i]) * (vt[i + 1] - vt[i]) / (y[i + 1] - y[i]))
    return out


def trip_from_halves(vt_up, lo_up, hi_up, vt_dn, lo_dn, hi_dn, vdd):
    th = 0.5 * vdd
    lo_fall = _crossings(vt_up, lo_up, th, rising=False)
    lo_rise = _crossings(vt_dn, lo_dn, th, rising=True)
    hi_rise = _crossings(vt_up, hi_up, th, rising=True)
    hi_fall = _crossings(vt_dn, hi_dn, th, rising=False)
    return {
        "lo_fall": lo_fall[0] if lo_fall else float("nan"),
        "lo_rise": lo_rise[0] if lo_rise else float("nan"),
        "hi_rise": hi_rise[0] if hi_rise else float("nan"),
        "hi_fall": hi_fall[0] if hi_fall else float("nan"),
    }


def extract_trips(raw, vdd):
    d = read_raw(raw)
    t = np.real(d["time"])
    vt, lo, hi = np.real(d["vt"]), np.real(d["vtune_lo"]), np.real(d["vtune_hi"])
    m_up = (t >= 1e-6) & (t <= 51e-6)
    m_dn = (t >= 52e-6) & (t <= 102e-6)
    return trip_from_halves(
        vt[m_up], lo[m_up], hi[m_up], vt[m_dn], lo[m_dn], hi[m_dn], vdd,
    )


def sweep_body(mos, vdd, slo=(1.0, 1.0), shi=(1.0, 1.0)):
    body = header(f"vtune_mon {mos}", mos) + monitors(vdd, slo, shi)
    body += (f'vt (vt 0) vsource type="pulse" val0=0 val1={vdd} delay=1u '
             f'rise=50u fall=50u width=1u\n')
    return body


def do_corners():
    print("# V_tune window monitor (D20) [SCH]\n")
    print(f"Thresholds (bandgap stand-ins): V_lo = {VLO:.3f} V, V_hi = {VHI:.3f} V. "
          f"Calibrated landing 0.34–0.82 V; fixed-code p26s3 lock at 0.40 V is band-dependent "
          f"(~{0.40 - VLO:.2f} V above the low flag).\n")
    print(f"Hysteresis: lo Rs/Rf = {RS/1e3:.0f} kΩ / {RF/1e6:.1f} MΩ "
          f"(≈ {VDD * RS / (RS + RF) * 1e3:.0f} mV); "
          f"hi Rf = {RF_HI/1e6:.1f} MΩ into the ÷2 node.\n")
    print("## Trip points and hysteresis\n")
    print("| Corner | V_DD | T (°C) | lo fall / rise (V) | hyst lo (mV) | "
          "hi rise / fall (V) | hyst hi (mV) |")
    print("|---|---|---|---|---|---|---|")
    rows = []
    for name, mos, vdd, temp in CORNERS:
        text = sweep_body(mos, vdd)
        tag = name.replace(" ", "_").replace("°", "").replace("−", "m")
        # op-based IC: UIC NaNs the PMOS hi pair at ss/−40 °C
        run_vacask(f"sw_{tag}", text,
                   f"  options temp={temp}\n  save v(vt) v(vtune_lo) v(vtune_hi)\n"
                   f"  analysis op1 op\n"
                   f'  analysis tr tran stop=102u step=20n maxstep=50n icmode="op"\n')
        tr = extract_trips(os.path.join(OUT, "tr.raw"), vdd)
        # lo: clears (fall) above sets (rise); hi: sets (rise) above clears (fall)
        hlo = (tr["lo_fall"] - tr["lo_rise"]) * 1e3
        hhi = (tr["hi_rise"] - tr["hi_fall"]) * 1e3
        print(f"| {name} | {vdd:.2f} | {temp} | {tr['lo_fall']:.3f} / {tr['lo_rise']:.3f} | {hlo:.0f} | "
              f"{tr['hi_rise']:.3f} / {tr['hi_fall']:.3f} | {hhi:.0f} |")
        rows.append((name, tr, hlo, hhi))
    return rows


def do_current():
    print("\n## Supply current (tt, 27 °C, V_tune = 0.6 V)\n")
    text = header("vtune_mon current") + (
        f"vddx (vddx 0) vsource dc={VDD}\n"
        f"ivdd (vddx vdd) vsource dc=0\n"
        f"vlo (vlo 0) vsource dc={VLO}\n"
        f"vhi (vhi 0) vsource dc={VHI}\n"
        f"vt (vt 0) vsource dc=0.6\n"
        + cmp_lo("lo", "vt", "vlo", "vtune_lo")
        + cmp_hi("hi", "vt", "vhi", "vtune_hi")
    )
    run_vacask("cur", text, "  options temp=27\n  save i(ivdd)\n  analysis op1 op\n")
    raw = open(os.path.join(OUT, "op1.raw"), "rb").read()
    i = raw.index(b"Binary:\n") + len(b"Binary:\n")
    cur = abs(struct.unpack("<d", raw[i:i + 8])[0])
    print(f"I_VDD = {cur * 1e6:.1f} µA (two tails {2 * ITAIL * 1e6:.0f} µA plus loads/inverters).\n")
    return cur


def do_mc(n=50):
    print(f"\n## Input-offset Monte Carlo (tt, 27 °C, n = {n})\n")
    print("Mismatch: 1 % relative σ on each input-pair finger width (hand model of local mismatch).\n")
    rng = np.random.default_rng(42)
    lo_trips, hi_trips = [], []
    for k in range(n):
        dlo = 1 + 0.01 * rng.standard_normal(2)
        dhi = 1 + 0.01 * rng.standard_normal(2)
        body = sweep_body("mos_tt", VDD, slo=dlo, shi=dhi)
        run_vacask(f"mc_{k}", body,
                   "  options temp=27\n  save v(vt) v(vtune_lo) v(vtune_hi)\n"
                   "  analysis op1 op\n"
                   '  analysis tr tran stop=102u step=20n maxstep=50n icmode="op"\n')
        tr = extract_trips(os.path.join(OUT, "tr.raw"), VDD)
        lo_trips.append(0.5 * (tr["lo_fall"] + tr["lo_rise"]))
        hi_trips.append(0.5 * (tr["hi_rise"] + tr["hi_fall"]))
        if (k + 1) % 10 == 0:
            print(f"  … {k + 1}/{n}")
    lo_trips, hi_trips = np.array(lo_trips), np.array(hi_trips)
    lo_3 = lo_trips.mean() + 3 * lo_trips.std()
    hi_3 = hi_trips.mean() - 3 * hi_trips.std()
    print("| Flag | mean (V) | σ (mV) | ±3σ edge (V) | margin to cal 0.34 / 0.82 V |")
    print("|---|---|---|---|---|")
    print(f"| lo | {lo_trips.mean():.4f} | {lo_trips.std()*1e3:.1f} | +3σ {lo_3:.4f} | "
          f"0.34 − +3σ = {0.34 - lo_3:+.3f} V |")
    print(f"| hi | {hi_trips.mean():.4f} | {hi_trips.std()*1e3:.1f} | −3σ {hi_3:.4f} | "
          f"−3σ − 0.82 = {hi_3 - 0.82:+.3f} V |")
    print("\nPass if both margins are positive (no false flags on calibrated lock).\n")
    return lo_trips, hi_trips


def main():
    if "mc" in ARGS:
        n = 50
        for a in ARGS:
            if a.startswith("n="):
                n = int(a.split("=", 1)[1])
        do_mc(n)
        return
    do_corners()
    do_current()
    print("## Register map\n")
    print("`PLL_STATUS`[4] = V_tune below window (`vtune_lo`); [5] = above (`vtune_hi`) — "
          "`spec/analog-digital-interface.md` §5.2. Synchronised in `rtl/afe/vtune_sync.sv`.\n")


if __name__ == "__main__":
    main()
