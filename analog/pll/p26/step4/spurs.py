#!/usr/bin/env python3
"""P2.6 step 4: spur summary with the final loop (D19) and the circuit results (spec/pll-topology.md §13).

Runs anywhere (numpy, scipy):   python3 spurs.py | tee out/summary.txt

1. Reference spur. Locked, the charge pump gives one UP pulse per reference cycle that returns the charge the
   D18 offset current (plus any leakage) took out over the cycle: a pulse train of height I_cp and width
   t_on = (I_off + I_leak) / I_cp x T_ref. Its Fourier components through the loop filter (C1 || (R1 + C2), then
   R3 / C3) frequency-modulate the VCO: beta_k = K_VCO x 2 |I_k| |Z(k f_ref)| / (k f_ref), spur = 20 log(beta / 2).
   Cases: I_cp / K_VCO at the bottom, middle and top of the band (D19 keeps their product about constant),
   leakage 0 / 2 / 5 uA (the MOS loop-filter capacitors at 125 degC, step 1; the hold switch adds <= 8 nA).
   Limit: -67 dBc at RF (TX spurs elsewhere, P2.2).
2. Fractional spur at the boundary offset from the pump nonlinearity: the step-3 cycle-by-cycle model
   (pll_behav.py, D19 loop) with an INL of 3.9 ps (the step-3 Monte Carlo worst case) and 10 ps. Limit -95 dBc.
3. Integer-boundary spur: set by coupling (layout, P2.7), not by the loop; the largest raw spur at the VCO that
   still meets -95 dBc on the hit channels, with the D19 loop (P2.2 model).
Results are [MODEL].
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "analog", "pll-model"))
sys.path.insert(0, os.path.join(REPO, "analog", "pll", "step3"))
import pll_model as P  # noqa: E402

LF = dict(C1=30.8e-12, C2=465.2e-12, R1=22.9e3, R3=107.8e3, C3=3.08e-12)     # D19
D = {"VHF": 24, "UHF": 8}


def ref_spur(fref, icp, kvco, ileak, k):
    T = 1 / fref
    ton = (0.1 * icp + ileak) / icp * T
    ik = icp / (math.pi * k) * abs(math.sin(math.pi * k * ton / T))
    z = abs(P.z_filter(np.array([k * fref]), LF)[0])
    beta = kvco * 2 * ik * z / (k * fref)
    return 20 * math.log10(beta / 2)


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    print("# P2.6 step 4 — spurs with the final loop\n")
    print("## 1. Reference spur (at ± f_ref and harmonics) [MODEL]\n")
    print("| f_ref | Band position: I_cp / K_VCO | Leakage | At the VCO, k = 1 / 2 / 3 (dBc) | At RF, k = 1: VHF / UHF (dBc) |")
    print("|---|---|---|---|---|")
    worst = -999.0
    for fref in (32e6, 36e6):
        for lab, icp, kv in (("bottom 125 µA / 16 MHz/V", 125e-6, 16e6), ("middle 100 µA / 20 MHz/V", 100e-6, 20e6),
                             ("top 50 µA / 38.6 MHz/V", 50e-6, 38.6e6)):
            for il in (0.0, 2e-6, 5e-6):
                s = [ref_spur(fref, icp, kv, il, k) for k in (1, 2, 3)]
                worst = max(worst, s[0] - 20 * math.log10(D["UHF"]))
                print(f"| {fref/1e6:.0f} MHz | {lab} | {il*1e6:.0f} µA | " + " / ".join(f"{x:.1f}" for x in s)
                      + f" | {s[0] - 20*math.log10(24):.1f} / {s[0] - 20*math.log10(8):.1f} |")
    print(f"\nWorst at RF: {worst:.1f} dBc against −67 dBc (margin {-67 - worst:.0f} dB). The D18 offset current is "
          "what makes the ripple; the R3 / C3 pole (≈ 480 kHz) takes 36–38 dB off it at 32–36 MHz.\n")

    print("## 2. Fractional spur at the boundary offset (pump nonlinearity) [MODEL]\n")
    import pll_behav as B
    print("| INL | VHF (dBc at RF) | UHF (dBc at RF) |")
    print("|---|---|---|")
    for lab, inl in (("none (linear pump)", None), ("3.9 ps (step-3 worst)", 3.9e-12), ("10 ps", 10e-12)):
        f = (lambda a: (lambda d: a * math.sin(2 * math.pi * (d - 1e-9) / 4e-9)))(inl) if inl else None
        r = {b: B.spur(b, f)["spur_rf"] for b in B.BANDS}
        print(f"| {lab} | {r['VHF']:.1f} | {r['UHF']:.1f} |")
    print("\nLimit −95 dBc (25 W duplex).\n")

    print("## 3. Integer-boundary spur budget with the D19 loop [MODEL]\n")
    a_kv, a_icp = 40e6, 50e-6
    for band, (n_lo, dup, _) in P.BANDS.items():
        n_fb = 3.65e9 / 32e6
        lf = P.design_loop(60e3, 62.0, a_kv, a_icp, n_fb)
        _, t_ref, _ = P.loop(np.array([dup]), lf, a_kv, a_icp, n_fb)
        att = 20 * np.log10(np.abs(t_ref[0]) / n_fb) - 20 * np.log10(n_lo)
        print(f"- {band}: a raw coupling spur of up to {P.LIM_SPUR_DUP_25W - att:.0f} dBc at the VCO (before the loop) still "
              f"meets −95 dBc at the duplex offset ({dup/1e6:g} MHz) — a layout target for P2.7.")
    print()


if __name__ == "__main__":
    main()
