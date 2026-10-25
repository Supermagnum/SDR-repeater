#!/usr/bin/env python3
"""Phase 2 step P2.2 - linear PLL model for the HT13G-M LO (spec/phase2-plan.md).

Type-II charge-pump PLL, fractional-N with a MASH 1-1-1 modulator, 3rd-order passive
loop filter (C1 || (R1 + C2)) plus one extra RC pole (4th order overall).
Noise sources (all referred to the VCO, then divided to RF by N_LO = 24 or 8):
  VCO       L(f) = L1M - 20 log(f / 1 MHz), plus a 1/f^3 region below fc_vco
  PFD / CP  flat in-band floor from a figure of merit FoM_cp (dBc/Hz, 1 Hz normalised)
  reference TCXO profile, multiplied by N_fb
  MASH      quantisation noise of an n-th order MASH, shaped by the loop
Spurs:
  integer-boundary spur, raw level S0 (dBc at the VCO, as if unfiltered), at offset d
  reference spur from charge-pump leakage at +-f_ref
Every number here is a model input labelled [PROP] in the README, not a circuit result.

    python3 analog/pll-model/pll_model.py              # default case, all checks
    python3 analog/pll-model/pll_model.py --bw 100e3   # other loop bandwidth
"""
import argparse
import numpy as np
from scipy import signal

KT4 = 4 * 1.380649e-23 * 300.0

# Limits (spec/derived-limits.md section 8 and 9, spec/rf-frontend.md section 5)
LIM_PN_25W = -136.0       # dBc/Hz at the duplex offset, RF, 25 W baseline
LIM_PN_5W = -129.0
LIM_SPUR_DUP_25W = -95.0  # dBc at the duplex offset
LIM_SPUR_REF_TX = -67.0   # dBc, design target for spurs elsewhere (TX)
LIM_LOCK_S = 150e-6       # wake budget
LIM_RES_HZ = 10.0         # frequency resolution at RF

BANDS = {  # name: (LO divider, duplex offset, RF range)
    "VHF": (24, 0.6e6, (130e6, 175e6)),
    "UHF": (8, 2.0e6, (400e6, 480e6)),
}


def design_loop(fc, pm_deg, kvco, icp, n_fb, gamma=1.0024, p3_ratio=8.0):
    """Banerjee-style 3rd-order passive filter for unity-gain frequency fc and phase margin pm.
    Returns C1, C2, R1 and an extra pole (R3, C3) at p3_ratio * fc."""
    wc = 2 * np.pi * fc
    pm = np.radians(pm_deg)
    # P2.6 step 1 correction: K_phi K_VCO / N = (Icp / 2 pi) [A/rad] x (2 pi Kvco) [rad/s/V] / N = Icp Kvco[Hz/V] / N.
    # Until 2026-10-25 this line had an extra 2 pi, so the filter was sized for 2 pi too much loop gain and the
    # loop() below (which is right) gave about 42 kHz and 35 deg instead of 150 kHz and 55 deg.
    k = icp * kvco / n_fb
    # T1 (pole), T2 (zero) for the given phase margin
    t1 = (1 / np.cos(pm) - np.tan(pm)) / wc
    t2 = gamma / (wc ** 2 * t1)
    a0 = k / wc ** 2 * np.sqrt((1 + (wc * t2) ** 2) / (1 + (wc * t1) ** 2))
    c1 = a0 * t1 / t2
    c2 = a0 - c1
    r1 = t2 / c2
    c3 = c1 / 10
    r3 = 1 / (2 * np.pi * p3_ratio * fc * c3)
    return dict(C1=c1, C2=c2, R1=r1, R3=r3, C3=c3)


def z_filter(f, lf):
    s = 2j * np.pi * f
    z1 = 1 / (s * lf["C1"])
    z2 = lf["R1"] + 1 / (s * lf["C2"])
    zp = z1 * z2 / (z1 + z2)
    # extra pole: R3 in series, C3 to ground (voltage divider, loading neglected)
    return zp / (1 + s * lf["R3"] * lf["C3"])


def loop(f, lf, kvco, icp, n_fb):
    s = 2j * np.pi * f
    g = icp / (2 * np.pi) * z_filter(f, lf) * (kvco * 2 * np.pi) / s  # VCO phase per PFD phase
    olg = g / n_fb
    t_ref = g / (1 + olg)            # reference/PFD-referred -> VCO, lowpass, DC gain N
    t_vco = 1 / (1 + olg)            # VCO -> output, highpass
    return olg, t_ref, t_vco


def noise(f, a, lf, n_fb, fpfd, n_lo, presc=1):
    olg, t_ref, t_vco = loop(f, lf, a.kvco, a.icp, n_fb)
    t_div = t_ref / n_fb             # divider-phase -> VCO phase, DC gain 1
    # VCO (dBc/Hz -> rad^2/Hz single sideband *2)
    lv = a.l1m - 20 * np.log10(f / 1e6) + 10 * np.log10(1 + a.fc_vco / f)
    s_vco = 2 * 10 ** (lv / 10) * np.abs(t_vco) ** 2
    # PFD / CP floor at the VCO, in-band: FoM + 10log fpfd + 20log N
    lcp = a.fom_cp + 10 * np.log10(fpfd) + 10 * np.log10(1 + a.fc_cp / f)
    s_cp = 2 * 10 ** (lcp / 10) * np.abs(t_ref) ** 2
    # Reference (TCXO) profile, points in dBc/Hz
    ref_f = np.array([1e2, 1e3, 1e4, 1e5, 1e6, 1e7])
    ref_l = np.array(a.ref_profile)
    lref = np.interp(np.log10(f), np.log10(ref_f), ref_l)
    s_ref = 2 * 10 ** (lref / 10) * np.abs(t_ref) ** 2
    # MASH n-th order: divider-modulus noise (VCO cycles) -> VCO phase
    # P2.5: with a prescaler P in front of the multi-modulus divider one modulus step is P VCO cycles
    sq = presc ** 2 * (2 * np.pi) ** 2 / (12 * fpfd) * (2 * np.sin(np.pi * f / fpfd)) ** (2 * (a.mash - 1))
    s_sd = sq * np.abs(t_div) ** 2
    # Loop-filter resistor noise (R1, R3) -> control voltage -> VCO phase
    s = 2j * np.pi * f
    zc1 = 1 / (s * lf["C1"]); zc2 = 1 / (s * lf["C2"]); zc3 = 1 / (s * lf["C3"])
    # R1 noise current divides into C1 (shunt) ; voltage at node = vn1 * zc1/(zc1 + R1 + zc2) roughly
    v1 = np.sqrt(KT4 * lf["R1"]) * np.abs(zc1 / (zc1 + lf["R1"] + zc2)) / np.abs(1 + s * lf["R3"] * lf["C3"])
    v3 = np.sqrt(KT4 * lf["R3"]) * np.abs(1 / (1 + s * lf["R3"] * lf["C3"]))
    kv = a.kvco * 2 * np.pi
    s_r = (v1 ** 2 + v3 ** 2) * (kv / (2 * np.pi * f)) ** 2 * np.abs(t_vco) ** 2  # one-sided S_phi (rad^2/Hz); db() halves it to L(f)
    tot = s_vco + s_cp + s_ref + s_sd + s_r
    to_rf = -20 * np.log10(n_lo)
    db = lambda s: 10 * np.log10(s / 2) + to_rf
    return dict(total=db(tot), vco=db(s_vco), cp=db(s_cp), ref=db(s_ref), sd=db(s_sd), r=db(s_r))


def lock_time(lf, a, n_fb, n_lo, step_hz, tol_rf_hz):
    """Linear settling of the VCO frequency after a frequency step (residual error after band
    calibration): frequency error follows the step response of 1 / (1 + G(s))."""
    c1, c2, r1, r3, c3 = lf["C1"], lf["C2"], lf["R1"], lf["R3"], lf["C3"]
    ct = c1 + c2
    t1 = r1 * c1 * c2 / ct
    # Z(s) = (1 + s R1 C2) / (s Ct (1 + s T1) (1 + s R3 C3))
    num_z = [r1 * c2, 1.0]
    den_z = np.polymul(np.polymul([ct, 0.0], [t1, 1.0]), [r3 * c3, 1.0])
    k = a.icp * a.kvco / n_fb                     # Icp/(2pi) * Kvco*2pi / N
    num_g = np.polymul([k], num_z)
    den_g = np.polymul(den_z, [1.0, 0.0])
    # E(s) = 1/(1+G) = den_g / (den_g + num_g)
    den_e = np.polyadd(den_g, num_g)
    t = np.linspace(0, 600e-6, 60001)
    _, y = signal.step(signal.lti(den_g, den_e), T=t)
    err = np.abs(y) * step_hz / n_lo
    bad = np.where(err > tol_rf_hz)[0]
    return t[bad[-1] + 1] if len(bad) else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bw", type=float, default=150e3, help="loop unity-gain bandwidth, Hz")
    ap.add_argument("--pm", type=float, default=55.0, help="phase margin, degrees")
    ap.add_argument("--kvco", type=float, default=40e6, help="VCO gain per band, Hz/V [PROP]")
    ap.add_argument("--icp", type=float, default=50e-6, help="charge-pump current, A [PROP]")
    ap.add_argument("--l1m", type=float, default=-116.0, help="VCO phase noise at 1 MHz, dBc/Hz (plan target)")
    ap.add_argument("--fc-vco", type=float, default=200e3, help="VCO 1/f^3 corner, Hz [PROP]")
    ap.add_argument("--fom-cp", type=float, default=-218.0, help="PFD/CP figure of merit, dBc/Hz [PROP]")
    ap.add_argument("--fc-cp", type=float, default=20e3, help="CP 1/f corner, Hz [PROP]")
    ap.add_argument("--mash", type=int, default=3)
    ap.add_argument("--s0", type=float, default=-45.0, help="raw boundary spur at the VCO, dBc [PROP]")
    ap.add_argument("--ileak", type=float, default=1e-9, help="CP leakage, A [PROP]")
    ap.add_argument("--presc", action="store_true",
                    help="P2.5 proposal: MMD clocked after the LO chain's first CML stage (÷2 UHF, ÷3 VHF)")
    ap.add_argument("--ref-profile", type=float, nargs=6,
                    default=[-110, -135, -150, -155, -158, -160],
                    help="TCXO L(f) at 100 Hz..10 MHz, dBc/Hz [PROP]")
    a = ap.parse_args()

    print(f"Loop: BW {a.bw/1e3:.0f} kHz, PM {a.pm:.0f} deg, Kvco {a.kvco/1e6:.0f} MHz/V, Icp {a.icp*1e6:.0f} uA, "
          f"MASH {a.mash}, VCO {a.l1m:.0f} dBc/Hz @ 1 MHz" + (", prescaler ÷2 UHF / ÷3 VHF before the MMD" if a.presc else ""))
    ok_all = True
    for ref in (32e6, 36e6):
        for band, (n_lo, dup, (flo, fhi)) in BANDS.items():
            for frf in (flo, fhi):
                fvco = frf * n_lo
                n_fb = fvco / ref
                lf = design_loop(a.bw, a.pm, a.kvco, a.icp, n_fb)
                f = np.array([dup])
                presc = (3 if band == "VHF" else 2) if a.presc else 1
                pn = noise(f, a, lf, n_fb, ref, n_lo, presc)
                p = pn["total"][0]
                # integer-boundary spur at offset d = duplex offset
                _, t_ref, _ = loop(f, lf, a.kvco, a.icp, n_fb)
                spur_dup = a.s0 + 20 * np.log10(np.abs(t_ref[0]) / n_fb) - 20 * np.log10(n_lo)
                # reference spur from CP leakage at f_ref
                zr = np.abs(z_filter(np.array([ref]), lf))[0]
                beta = a.kvco * 2 * a.ileak * zr / ref
                spur_ref = 20 * np.log10(beta / 2) - 20 * np.log10(n_lo)
                res = ref / 2 ** 24 / n_lo
                ok = (p <= LIM_PN_25W) and (spur_dup <= LIM_SPUR_DUP_25W) and (spur_ref <= LIM_SPUR_REF_TX) and res <= LIM_RES_HZ
                ok_all &= ok
                print(f"  ref {ref/1e6:.0f} MHz {band} {frf/1e6:6.1f} MHz (VCO {fvco/1e9:.3f} GHz, N {n_fb:6.2f}): "
                      f"PN @{dup/1e6:.1f} MHz {p:7.1f} dBc/Hz "
                      f"[VCO {pn['vco'][0]:.1f}, CP {pn['cp'][0]:.1f}, R {pn['r'][0]:.1f}, ref {pn['ref'][0]:.1f}, SD {pn['sd'][0]:.1f}]  "
                      f"boundary spur {spur_dup:6.1f} dBc  ref spur {spur_ref:6.1f} dBc  "
                      f"{'OK' if ok else 'FAIL'}")
    # lock time and loop values at the mid band, 32 MHz
    n_lo, dup, _ = BANDS["VHF"]
    n_fb = 3.65e9 / 32e6
    lf = design_loop(a.bw, a.pm, a.kvco, a.icp, n_fb)
    tl = lock_time(lf, a, n_fb, n_lo, step_hz=2e6, tol_rf_hz=LIM_RES_HZ)
    ff = np.logspace(3, 7, 20000)
    olg, _, _ = loop(ff, lf, a.kvco, a.icp, n_fb)
    ic = np.argmin(np.abs(np.abs(olg) - 1))
    print(f"Check of the designed filter: unity-gain frequency {ff[ic]/1e3:.0f} kHz, phase margin "
          f"{180 + np.degrees(np.angle(olg[ic])):.0f} deg (asked {a.bw/1e3:.0f} kHz, {a.pm:.0f} deg)")
    print(f"Loop filter (N = {n_fb:.1f}): C1 {lf['C1']*1e12:.1f} pF, C2 {lf['C2']*1e12:.1f} pF, "
          f"R1 {lf['R1']/1e3:.2f} kOhm, R3 {lf['R3']/1e3:.2f} kOhm, C3 {lf['C3']*1e12:.2f} pF; "
          f"total C {(lf['C1']+lf['C2']+lf['C3'])*1e12:.0f} pF")
    print(f"Linear lock time, 2 MHz VCO step to 10 Hz at RF (VHF): {tl*1e6:.0f} us (budget {LIM_LOCK_S*1e6:.0f} us, "
          f"plus band calibration)")
    print(f"Loop-filter capacitance on chip: about {(lf['C1']+lf['C2']+lf['C3'])*1e12/8/1e3:.3f} mm2 as MOS capacitors "
          f"(about 8 fF/um2) or {(lf['C1']+lf['C2']+lf['C3'])*1e12/1.5/1e3:.2f} mm2 as MIM (about 1.5 fF/um2) [PROP densities]")
    ok_all &= tl <= LIM_LOCK_S
    s0_max = []
    for band, (n_lo, dup, _) in BANDS.items():
        n_fb = 3.65e9 / 32e6
        lf = design_loop(a.bw, a.pm, a.kvco, a.icp, n_fb)
        _, t_ref, _ = loop(np.array([dup]), lf, a.kvco, a.icp, n_fb)
        att = 20 * np.log10(np.abs(t_ref[0]) / n_fb) - 20 * np.log10(n_lo)
        s0_max.append(f"{band} {LIM_SPUR_DUP_25W - att:.0f} dBc")
    print("Largest raw boundary spur (at the VCO, before the loop) that still meets -95 dBc on the hit channels: "
          + ", ".join(s0_max))
    print("RESULT:", "PASS" if ok_all else "FAIL")


if __name__ == "__main__":
    main()
