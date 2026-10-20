#!/usr/bin/env python3
"""VCO tank and tuning budget for the P2.3 topology memo (spec/vco-topology.md). [HAND]

Hand estimates only: tank capacitance budget, capacitor-bank steps, the varactor gain
(KVCO) each bank size needs, and Leeson phase-noise estimates for the candidate cores.
Inputs are the accepted EM tank values (spec/provisional-tank-q.md) and [PROP] numbers
marked below. Nothing here is a circuit result.

    python3 analog/vco/tank_budget.py
    python3 analog/vco/tank_budget.py --bits 6 --vwin 0.6
"""
import argparse
import math

K, T = 1.380649e-23, 300.15

# Accepted EM values (P2.0): differential L and Q of SG13_Octagon_L2n0, de-embedded
EM = [(3.12e9, 14.2), (3.50e9, 15.3), (3.65e9, 15.5), (4.20e9, 16.9)]
L_NOM = 1.69e-9
L_TOL = 0.03                      # solver offset, P2.0


def c_tank(f, l):
    """Differential tank capacitance for resonance at f."""
    return 1.0 / ((2 * math.pi * f) ** 2 * l)


def q_at(f):
    """EM Q, linear interpolation over the accepted table."""
    pts = EM
    if f <= pts[0][0]:
        return pts[0][1]
    for (f1, q1), (f2, q2) in zip(pts, pts[1:]):
        if f <= f2:
            return q1 + (q2 - q1) * (f - f1) / (f2 - f1)
    return pts[-1][1]


def leeson(f0, q, rp, a, fnoise, df=1e6):
    """L(df) = 2 F k T / Psig * (f0 / (2 Q df))^2, Psig = A^2 / (2 Rp) (A differential peak)."""
    psig = a * a / (2 * rp)
    return 10 * math.log10(2 * fnoise * K * T / psig * (f0 / (2 * q * df)) ** 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fmin", type=float, default=3.00e9, help="design low edge (3.12 GHz - 4 %%) [PROP]")
    ap.add_argument("--fmax", type=float, default=4.37e9, help="design high edge (4.20 GHz + 4 %%) [PROP]")
    ap.add_argument("--bits", type=int, nargs="+", default=[6, 7], help="capacitor-bank bits to compare")
    ap.add_argument("--overlap", type=float, default=1.3, help="varactor span / band step [PROP]")
    ap.add_argument("--vwin", type=float, default=0.6, help="usable tuning-voltage window, V [PROP]")
    ap.add_argument("--qbank", type=float, default=0.85, help="tank Q kept with bank and varactor loss [PROP]")
    a = ap.parse_args()

    cmax = c_tank(a.fmin, L_NOM * (1 - L_TOL))       # low edge with the smallest L
    cmin = c_tank(a.fmax, L_NOM * (1 + L_TOL))       # high edge with the largest L
    print(f"Tank (differential): L {L_NOM*1e9:.2f} nH +-{L_TOL*100:.0f} %, design range "
          f"{a.fmin/1e9:.2f}-{a.fmax/1e9:.2f} GHz")
    print(f"  C needed: max {cmax*1e15:.0f} fF (low edge, L -3 %), min {cmin*1e15:.0f} fF (high edge, L +3 %); "
          f"ratio {cmax/cmin:.2f}; switched range {(cmax-cmin)*1e15:.0f} fF")
    print(f"  everything fixed at the high edge (core, inductor self-C, bank off-C, varactor min, buffer,"
          f" routing) must stay below {cmin*1e15:.0f} fF differential")

    print("\nCapacitor bank and varactor gain (binary bank, equal C steps):")
    for b in a.bits:
        dc = (cmax - cmin) / (2 ** b - 1)
        step_lo = a.fmin / (2 * cmax) * dc
        step_hi = a.fmax / (2 * cmin) * dc
        k_lo = a.overlap * step_lo / a.vwin
        k_hi = a.overlap * step_hi / a.vwin
        dcv = a.overlap * dc
        print(f"  {b} bits: unit {dc*1e15:5.1f} fF; band step {step_lo/1e6:4.1f} MHz (low edge) .. "
              f"{step_hi/1e6:4.1f} MHz (high edge); KVCO needed {k_lo/1e6:3.0f}-{k_hi/1e6:3.0f} MHz/V "
              f"over {a.vwin:.1f} V; varactor swing {dcv*1e15:.1f} fF")

    print(f"\nLeeson estimates at 1 MHz (tank Q x {a.qbank} for bank/varactor loss) [HAND]:")
    cands = [  # name, differential amplitude (V), noise factor F, current factor, supply (V)
        ("A  NMOS cross-coupled, LV, swing 1.0 V, F 3", 1.0, 3.0, 2, 1.2),
        ("A' same, F 4 (residual tail/bias noise)", 1.0, 4.0, 2, 1.2),
        ("B  complementary CMOS, swing 1.0 V, F 3", 1.0, 3.0, 4, 1.2),
        ("C  SiGe HBT cross-coupled, swing 1.6 V, F 2.5", 1.6, 2.5, 2, 2.5),
    ]
    for f0 in (3.12e9, 3.65e9, 4.20e9):
        q = q_at(f0) * a.qbank
        rp = q * 2 * math.pi * f0 * L_NOM
        print(f"  {f0/1e9:.2f} GHz: Q {q:.1f}, Rp {rp:.0f} ohm (differential)")
        for name, amp, fn, cf, vdd in cands:
            i = amp * math.pi / (cf * rp)            # current-limited: A = (cf/pi) I Rp
            l1 = leeson(f0, q, rp, amp, fn)
            p = i * vdd
            fom = -l1 + 20 * math.log10(f0 / 1e6) - 10 * math.log10(p / 1e-3)
            print(f"    {name:48s} I {i*1e3:4.1f} mA  L(1 MHz) {l1:6.1f} dBc/Hz  FoM {fom:3.0f} dB")
    print("\nTargets at 1 MHz: VHF <= -116, UHF <= -115 dBc/Hz (spec/phase2-plan.md 2.1).")


if __name__ == "__main__":
    main()
