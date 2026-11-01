#!/usr/bin/env python3
"""VCO supply pushing and LDO noise budget [SCH]+[HAND].

Measure f vs centre-tap V_CT (VDD_VCO) at tt 3.65 GHz and ss 85 °C 4.20 GHz
(bank-omitted bypass). K_push = df/dV. Convert an LDO output-noise density into
phase noise and compare to remaining margin vs ≤ −116 / −115 dBc/Hz at 1 MHz.

    python3 -u run_supply_push.py | tee out/summary_supply_push.txt
"""
import math
import os
import sys

import numpy as np

import run_step3 as s3

s3.OUT = "out"
GROUPS = ("tail", "var")
# Candidate LDO output noise at 1 MHz (white), V/√Hz — budget target to find.
SV_CANDIDATES = [10e-9, 30e-9, 100e-9, 300e-9]  # 10–300 nV/√Hz


def measure_f(code, vt, itail, temp, tag, vct):
    sim = s3.S2.netlist(
        f"s3_push_{tag}_{vct:.3f}".replace(".", "p"), code, vt, itail=itail,
        bypass=True, bypass_groups=GROUPS, vct=vct,
        analysis=(
            f"  options temp={temp}\n"
            "  save v(tp) v(tn) v(tail)\n"
            "  analysis tr tran stop=60n step=5p maxstep=5p"
        ),
    )
    s3.S2.run(sim)
    return s3.S2.measure(os.path.join(s3.OUT, "tr.raw"))


def L_from_push(K_hz_per_v, f_m, sv_v_per_rt_hz):
    """SSB L(f_m) from white supply noise S_v (V/√Hz) and K_push (Hz/V).

    S_φ(f) = (K/f)^2 S_v^2  [rad²/Hz]; L = 10 log10(S_φ/2).
    """
    s_phi = (K_hz_per_v / f_m) ** 2 * (sv_v_per_rt_hz ** 2)
    return 10 * math.log10(s_phi / 2)


def main():
    print("# VCO supply pushing and LDO noise budget\n")
    print("Centre-tap V_CT swept ±50 mV around 1.1 V; bank bypass omitted.\n")
    s3.load_sizing()
    cases = [
        ("tt_3.65", "mos_tt", "cap_typ", 27, 3.65e9, -116.0),
        ("ss85_4.20", "mos_ss", "cap_typ", 85, 4.20e9, -116.0),  # VHF limit
    ]
    # Bank-omitted PN from prior run for margin.
    L_vco = {"tt_3.65": -122.7, "ss85_4.20": -119.4}

    rows = []
    for tag, mos, cap, temp, f0, limit in cases:
        s3.set_corner(mos, cap)
        code = s3.code_for(f0, temp, f"{tag}_push")
        it = s3.itail_for(f0, s3.load_sizing()[1])
        print(f"## {tag}: code {code}, I_tail {it*1e3:.2f} mA [SCH]\n")
        pts = []
        for vct in (1.05, 1.10, 1.15):
            m = measure_f(code, s3.S2.VTUNE_MID, it, temp, tag, vct)
            print(f"  V_CT={vct:.2f} V → f={m['f']/1e9:.4f} GHz amp={m['amp']:.3f} V")
            pts.append((vct, m["f"], m["amp"]))
        # Linear fit df/dV around mid.
        vs, fs, _ = zip(*pts)
        K = float(np.polyfit(vs, fs, 1)[0])  # Hz/V
        print(f"  K_push = {K/1e6:.2f} MHz/V\n")
        L1 = L_vco[tag]
        margin = L1 - limit  # negative of usual "margin" wording: L1 is better (more neg)
        # Remaining headroom if we allow supply to eat 1 dB of the current margin:
        # find max S_v such that L_push is 10 dB below VCO (adds ~0.4 dB) or report table.
        print("  LDO white noise → L(1 MHz) from pushing [HAND]:")
        print("  | S_v (nV/√Hz) | L_push @ 1 MHz | vs VCO | add to total |")
        print("  |---|---|---|---|")
        for sv in SV_CANDIDATES:
            Lp = L_from_push(K, 1e6, sv)
            # total ≈ 10 log10(10^(L1/10)+10^(Lp/10))
            tot = 10 * math.log10(10 ** (L1 / 10) + 10 ** (Lp / 10))
            add = tot - L1
            print(f"  | {sv*1e9:.0f} | {Lp:.1f} | {Lp - L1:+.1f} dB | {add:+.2f} dB |")
        # S_v for +0.5 dB degradation
        # 10^((L1+0.5)/10) = 10^(L1/10) + 10^(Lp/10) → 10^(Lp/10) = 10^(L1/10)*(10^0.05-1)
        p_extra = 10 ** (L1 / 10) * (10 ** 0.05 - 1)
        # p_extra = 0.5 * (K/f)^2 * sv^2  → sv^2 = 2 p_extra * (f/K)^2
        sv_05 = math.sqrt(2 * p_extra) * (1e6 / abs(K)) if K else float("inf")
        print(f"\n  For ΔL ≤ 0.5 dB at 1 MHz: S_v ≤ {sv_05*1e9:.1f} nV/√Hz [HAND]")
        print(f"  VCO L(1 MHz)={L1:.1f}, limit={limit:.1f}, margin={limit - L1:+.1f} dB "
              f"(bank-omitted)\n")
        rows.append(dict(tag=tag, code=code, K=K, pts=pts, sv_0p5=sv_05, L1=L1, limit=limit))

    print("## Summary\n")
    print("| Point | K_push (MHz/V) | S_v for ≤0.5 dB @ 1 MHz |")
    print("|---|---|---|")
    for r in rows:
        print(f"| {r['tag']} | {r['K']/1e6:.2f} | {r['sv_0p5']*1e9:.1f} nV/√Hz |")
    print("\nLDO output noise (white) must stay under the tighter of the two S_v limits "
          "if pushing alone is allowed 0.5 dB of the VCO PN budget at 1 MHz.")


if __name__ == "__main__":
    main()
