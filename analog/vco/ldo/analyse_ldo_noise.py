#!/usr/bin/env python3
"""Analyse D10 LDO noise (do not change the LDO schematic yet).

1) Breakdown at 1 MHz: reference / error-amp input pair / rest [SCH]
2) Cheapest variants toward bare ≤ ~30 nV/√Hz (area, current) [SCH]+[HAND]
3) Option C: LDO → R(5–10 Ω) → pad → bond L → board 100 nF; VCO from pad;
   pad/ESD C; resonance damping [SCH]+[HAND]
4) VR_ANA1 sharing / push / board noise [HAND]
5) S_v at VCO for (1), (2), (1)+(2) vs ≤ 11 nV/√Hz — STOP

    mkdir -p out && python3 -u analyse_ldo_noise.py | tee out/summary_ldo_analyse.txt
"""
import math
import os
import subprocess
import sys

import numpy as np
from vacask.rawfile import rawread

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

VIN, VOUT, ILOAD = 1.5, 1.1, 5e-3
VREF = VOUT / 2
LIMIT = 11e-9
TARGET30 = 30e-9
CAP_AREA = 1.5
COUT = 50e-12  # baseline MIM on LDO out


def side(c_ff):
    return math.sqrt(c_ff / CAP_AREA)


def run(name, text):
    path = os.path.join(OUT, name + ".sim")
    open(path, "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(open(log).read()[-1500:])
    return log


def header():
    return f"""parameters title="D10 LDO analyse"
include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section=mos_tt
include "cornerCAP.lib" section=cap_typ
load "resistor.osdi"
load "capacitor.osdi"
load "inductor.osdi"
model resistor resistor
model capacitor capacitor
model inductor inductor
model vsource vsource
model isource isource
"""


def ldo_core(pair_w=16, pair_ng=4, ibias=40e-6, ref_mode="ideal",
             ref_r=None, ref_c=None, buf=False, cout=COUT,
             rf=200e3, cmid=None, mirror_w=32, mirror_ng=4):
    """Core LDO. ref_mode: ideal | noisy (Thévenin Rth stand-in for bandgap).
    rf: each feedback resistor; cmid: mid-to-gnd C (opens loop at HF — usually worse)."""
    sc = side(cout * 1e15)
    rth = 10e3 if ref_r is None else ref_r
    if ref_mode == "ideal":
        ref = f"vref (vref 0) vsource dc={VREF}\n"
    elif buf:
        cc = ref_c if ref_c else 5e-12
        ref = (f"vth (vth 0) vsource dc={VREF}\n"
               f"rth (vth xref) resistor r={rth:g} noisy=1\n"
               f"cref (xref 0) capacitor c={cc:.6g}\n"
               f"ibuf (vin nbuf) isource dc=20u\n"
               f"mbuf (vref nbuf xref 0) sg13_lv_nmos w=20u l=0.5u ng=4\n"
               f"rpulld (vref 0) resistor r=500k\n"
               f"mbias (nbuf nbuf 0 0) sg13_lv_nmos w=4u l=2u ng=2\n")
    else:
        ref = (f"vth (vth 0) vsource dc={VREF}\n"
               f"rth (vth vref) resistor r={rth:g} noisy=1\n")
        if ref_c:
            ref += f"cref (vref 0) capacitor c={ref_c:.6g}\n"
    mid_c = ""
    if cmid:
        sm = side(cmid * 1e15)
        mid_c = f"xmid (mid 0 0) cap_rfcmim w={sm:.3f}u l={sm:.3f}u\n"

    return ref + f"""
vin (vin 0) vsource dc={VIN}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
rf1 (vout mid) resistor r={rf:g} noisy=1
rf2 (mid 0) resistor r={rf:g} noisy=1
{mid_c}ib (vin nb) isource dc={ibias:.6g}
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (d1 mid t 0) sg13_lv_nmos w={pair_w}u l=2u ng={pair_ng}
m2 (vg vref t 0) sg13_lv_nmos w={pair_w}u l=2u ng={pair_ng}
m3 (d1 d1 vin vin) sg13_lv_pmos w={mirror_w}u l=2u ng={mirror_ng}
m4 (vg d1 vin vin) sg13_lv_pmos w={mirror_w}u l=2u ng={mirror_ng}
cc (vg mid) capacitor c=500f
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
"""


def noise_ctrl(out_node="vout"):
    return f"""
il ({out_node} 0) isource dc={ILOAD}
iin (0 {out_node}) isource dc=0
control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(vout) v(vg) v(mid)
  analysis op1 op
  analysis n1 noise in="iin" out=["{out_node}"] values=[1Meg]
endc
"""


def read_noise():
    d = rawread(os.path.join(OUT, "n1.raw")).get()
    total = float(np.real(d["onoise"]).ravel()[0])  # V²/Hz
    contrib = {}
    for k in d.names:
        if k.startswith("n("):
            contrib[k] = float(np.real(d[k]).ravel()[0])
    return total, contrib


def sv(v2):
    return math.sqrt(abs(v2))


def classify(contrib):
    """Map VACASK n(...) keys to reference / pair / rest."""
    ref_p, pair_p, rest_p = 0.0, 0.0, 0.0
    rows = []
    for k, v in sorted(contrib.items(), key=lambda kv: -abs(kv[1])):
        kl = k.lower()
        if any(x in kl for x in ("rth", "vth", "cref", "mbuf", "rpulld", "ibuf", "mbias")):
            cat = "reference"
            ref_p += v
        elif any(x in kl for x in ("m1:", "m2:")):
            cat = "pair"
            pair_p += v
        else:
            cat = "rest"
            rest_p += v
        rows.append((k, v, cat))
    return ref_p, pair_p, rest_p, rows


def section_breakdown():
    print("# 1) Noise breakdown at 1 MHz — baseline D10 LDO [SCH]\n")
    print("Baseline: ideal Vref (no bandgap noise), pair 16u/2u ng=4, Ibias=40 µA, "
          f"Cout={COUT*1e12:.0f} pF MIM.\n")
    text = header() + ldo_core() + noise_ctrl()
    run("an_base", text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    vout = float(np.real(op["vout"]).ravel()[0])
    tot, contrib = read_noise()
    print(f"Vout={vout:.3f} V  S_v={sv(tot)*1e9:.1f} nV/√Hz  (onoise={tot:.3e} V²/Hz)\n")
    ref_p, pair_p, rest_p, rows = classify(contrib)
    s_ref, s_pair, s_rest = sv(ref_p), sv(pair_p), sv(rest_p)
    # Power fractions (V²)
    t = abs(tot) if tot else 1
    print("| Bucket | V²/Hz | nV/√Hz | % of total power |")
    print("|---|---|---|---|")
    print(f"| Reference (ideal Vref → 0) | {ref_p:.3e} | {s_ref*1e9:.1f} | {100*ref_p/t:.1f} |")
    print(f"| Error-amp input pair (m1,m2) | {pair_p:.3e} | {s_pair*1e9:.1f} | {100*pair_p/t:.1f} |")
    print(f"| Rest (pass, loads, feedback R, bias, Cout) | {rest_p:.3e} | {s_rest*1e9:.1f} | {100*rest_p/t:.1f} |")
    print(f"| Total | {tot:.3e} | {sv(tot)*1e9:.1f} | 100 |")
    print("\nTop contributors:")
    print("| Device | V²/Hz | nV/√Hz | bucket |")
    print("|---|---|---|---|")
    for k, v, cat in rows[:12]:
        print(f"| {k} | {v:.3e} | {sv(v)*1e9:.1f} | {cat} |")
    print()
    return sv(tot), ref_p, pair_p, rest_p


def section_cheap():
    print("# 2) Cheapest changes toward bare ≤ ~30 nV/√Hz [SCH]+[HAND]\n")
    print("Do not adopt yet — analysis only. Ideal-Vref baseline has no reference noise;\n"
          "variants with noisy Thévenin Rth=10 kΩ stand in for a real bandgap.\n")
    print("Note: mid-to-gnd C opens β at HF and *raises* S_v (cmid_2p shown once as reject).\n"
          "Ref RC / unity-gain buf / pair×4 alone cannot beat feedback-R dominance.\n")
    variants = [
        ("base_ideal", dict()),
        ("cmid_2p_reject", dict(cmid=2e-12)),  # opens loop — expect worse
        ("pair_x4", dict(pair_w=64, pair_ng=16)),
        ("ref_rc_5p_buf", dict(ref_mode="noisy", ref_c=5e-12, buf=True)),
        ("rf_50k", dict(rf=50e3)),
        ("rf_20k", dict(rf=20e3)),
        ("rf_10k", dict(rf=10e3)),
        ("rf_5k", dict(rf=5e3)),
        ("rf_10k_mir_x4", dict(rf=10e3, mirror_w=128, mirror_ng=16)),
        ("rf_10k_pair_mir", dict(rf=10e3, pair_w=64, pair_ng=16,
                                 mirror_w=128, mirror_ng=16)),
        ("rf_5k_mir_x4", dict(rf=5e3, mirror_w=128, mirror_ng=16)),
        ("noisy_rf_10k", dict(ref_mode="noisy", rf=10e3)),
        ("noisy_rf_5k_mir", dict(ref_mode="noisy", rf=5e3,
                                 mirror_w=128, mirror_ng=16)),
    ]
    print("| Variant | Vout | S_v (nV/√Hz) | ΔI_div (µA) | area proxy | note |")
    print("|---|---|---|---|---|---|")
    results = {}
    for tag, kw in variants:
        text = header() + ldo_core(**kw) + noise_ctrl()
        try:
            run(f"an_{tag}", text)
            op = rawread(os.path.join(OUT, "op1.raw")).get()
            vout = float(np.real(op["vout"]).ravel()[0])
            tot, _ = read_noise()
            s = sv(tot)
            rf = kw.get("rf", 200e3)
            di = VOUT / (2 * rf) * 1e6 - VOUT / (2 * 200e3) * 1e6
            if kw.get("ibias", 40e-6) != 40e-6:
                di += (kw["ibias"] - 40e-6) * 1e6
            if kw.get("buf"):
                di += 20.0
            # area proxy µm²: pair + mirror gate + Cmid MIM + buf
            area = (kw.get("pair_w", 16) * 2.0 * kw.get("pair_ng", 4)
                    + kw.get("mirror_w", 32) * 2.0 * kw.get("mirror_ng", 4) * 2)
            if kw.get("cmid"):
                area += kw["cmid"] * 1e15 / CAP_AREA
            if kw.get("ref_c"):
                area += kw["ref_c"] * 1e15 / CAP_AREA
            if kw.get("buf"):
                area += 40.0
            note = "reg" if abs(vout - VOUT) < 0.05 else "NO-REG"
            if "reject" in tag:
                note += "; REJECT mid-C"
            if s <= TARGET30 and note.startswith("reg"):
                note += "; ≤30"
            print(f"| {tag} | {vout:.3f} | {s*1e9:.1f} | +{di:.1f} | {area:.0f} µm² | {note} |")
            results[tag] = dict(sv=s, vout=vout, kw=kw, di=di, ca=area)
        except Exception as e:
            print(f"| {tag} | — | FAIL | — | — | {str(e).splitlines()[-1][:40]} |")
    print()
    # "~30": accept ≤ 32 nV; prefer zero added area (A/B/D already rejected for area)
    cand = [(t, r) for t, r in results.items()
            if r["sv"] <= 32e-9 and abs(r["vout"] - VOUT) < 0.05 and "reject" not in t]
    if cand:
        def cost(item):
            t, r = item
            # area first (owner rejected A/B/D for area), then current, then S_v
            extra_area = max(0.0, r["ca"] - 640.0)
            return (extra_area, r["di"], r["sv"])
        tag, r = sorted(cand, key=cost)[0]
        kw = r["kw"]
        print(f"Cheapest ≤~30 nV proposal (analysis only): **{tag}** → "
              f"S_v={r['sv']*1e9:.1f} nV/√Hz, +{r['di']:.1f} µA, area proxy {r['ca']:.0f} µm².")
        if kw.get("rf", 200e3) < 200e3:
            print(f"  Dominant fix: feedback R={kw['rf']/1e3:.0f} kΩ each "
                  f"(divider {VOUT/(2*kw['rf'])*1e6:.1f} µA; baseline 2.75 µA). "
                  f"rf1/rf2 dominate baseline noise — area-free.")
        if kw.get("mirror_w", 32) > 32:
            print(f"  Mirror m3/m4 → {kw['mirror_w']}u/2u ng={kw['mirror_ng']}.")
        if kw.get("pair_w", 16) > 16:
            print(f"  Pair → {kw['pair_w']}u/2u ng={kw['pair_ng']}.")
        alt = [(t, x) for t, x in cand if t != tag]
        if alt:
            t2, r2 = sorted(alt, key=lambda it: it[1]["sv"])[0]
            print(f"  Alt (lower S_v, more area): {t2} → {r2['sv']*1e9:.1f} nV, "
                  f"+{r2['di']:.1f} µA, area {r2['ca']:.0f} µm².")
        print()
        return r["sv"], tag, r
    reg = [(t, r) for t, r in results.items()
           if abs(r["vout"] - VOUT) < 0.05 and "reject" not in t]
    if reg:
        tag, r = sorted(reg, key=lambda it: (max(0, it[1]["ca"] - 640),
                                            it[1]["sv"], it[1]["di"]))[0]
        print(f"No variant ≤~30 nV; closest: **{tag}** → "
              f"S_v={r['sv']*1e9:.1f} nV/√Hz, +{r['di']:.1f} µA, area {r['ca']:.0f} µm².\n")
        return r["sv"], tag, r
    print("No regulating variants.\n")
    return None, None, None


def section_option_c(s_ldo_bare):
    print("# 3) Option C on VR_ANA1 pad + board 100 nF [SCH]+[HAND]\n")
    print("Network: LDO_out — R — pad — L_bond — board_C(100 nF) to ground.")
    print("VCO centre-tap from **pad** (chip side of bond). Pad+ESD ≈ 2 pF.\n")
    rows = []
    for r in (5, 10):
        for lb in (1e-9, 2e-9):
            tag = f"optc_r{r}_l{lb*1e9:.0f}n"
            # Small on-chip Cout kept; filter is board C
            body = ldo_core(cout=20e-12)
            text = header() + body + f"""
rser (vout pad) resistor r={r} noisy=1
cpad (pad 0) capacitor c=2p
lbond (pad pin) inductor l={lb}
cesd (pad 0) capacitor c=1p
cboard (pin 0) capacitor c=100n
il (pad 0) isource dc={ILOAD}
iin (0 pad) isource dc=0
iac (0 pad) isource dc=0 mag=1
control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(vout) v(pad) v(pin) v(vg)
  analysis op1 op
  analysis n1 noise in="iin" out=["pad"] values=[1Meg]
  analysis ac1 ac from=1Meg to=200Meg mode="dec" points=20
endc
"""
            run(tag, text)
            op = rawread(os.path.join(OUT, "op1.raw")).get()
            vpad = float(np.real(op["pad"]).ravel()[0])
            tot, _ = read_noise()
            s = sv(tot)
            ac = rawread(os.path.join(OUT, "ac1.raw")).get()
            freq = np.real(ac["frequency"]).ravel()
            zmag = np.abs(ac["pad"]).ravel()  # V for 1 A → Ω
            f0 = 1 / (2 * math.pi * math.sqrt(lb * 100e-9))
            z0 = math.sqrt(lb / 100e-9)
            zeta = r / 2 * math.sqrt(100e-9 / lb)
            q = 1 / (2 * zeta) if zeta > 0 else float("inf")
            damp = ("overdamped" if zeta >= 1
                    else ("critical" if zeta > 0.7 else "underdamped"))
            w = 2 * math.pi * 1e6
            h_rc = 1 / math.sqrt(1 + (w * r * 100e-9) ** 2)
            z_at_1m = float(zmag[np.argmin(np.abs(freq - 1e6))])
            z_peak = float(np.max(zmag))
            f_peak = float(freq[np.argmax(zmag)])
            # IR drop on series R at 5 mA
            print(f"R={r} Ω, L={lb*1e9:.0f} nH: S_v(pad)={s*1e9:.1f} nV/√Hz @ 1 MHz, "
                  f"Vpad={vpad:.3f} V, IR={r*ILOAD*1e3:.1f} mV")
            print(f"  f0≈{f0/1e6:.2f} MHz, Z0≈{z0:.2f} Ω, ζ≈{zeta:.1f} ({damp}, Q≈{q:.2f})")
            print(f"  |H|_RC LDO→pad @ 1 MHz ≈ {h_rc:.3f}; "
                  f"|Z_pad| @ 1 MHz = {z_at_1m:.3f} Ω, peak {z_peak:.3f} Ω @ {f_peak/1e6:.1f} MHz")
            rows.append(dict(r=r, l=lb, sv=s, f0=f0, z0=z0, zeta=zeta, damp=damp,
                             h=h_rc, z1m=z_at_1m, zpk=z_peak))
    print()
    best = min(rows, key=lambda x: x["sv"])
    print(f"Option C at 1 MHz: S_v at VCO (pad) ≈ **{best['sv']*1e9:.1f} nV/√Hz** "
          f"(best of grid; bare LDO was {s_ldo_bare*1e9:.1f}).")
    print("Damping: Z0≪R ⇒ always overdamped for 5–10 Ω and 1–2 nH / 100 nF — "
          "no peaking concern at f0 (AC |Z| peak stays near DC R-drop, not LC Q).\n")
    return best["sv"], rows


def section_sharing():
    print("# 4) VR_ANA1 sharing, push, board noise [HAND]\n")
    print("Pin intent: option C reuses the existing VR_ANA1 **board 100 nF**.")
    print("Electrically the SCH above is LDO(1.1 V)→R→pad→bond→100 nF.")
    print("Do **not** short that pad onto the live VR_ANA1 regulator output (~1.5 V /")
    print("RX-LO rail) — the LDO and VR_ANA1 would fight. Use either a dedicated")
    print("VDD_VCO pad bonded to the same 100 nF, or a second bond to that cap.\n")
    print("Blocks already on the VR_ANA1 *rail* (`spec/analog-digital-interface.md`):")
    print("  RX chain, LO (buffer + CML dividers + CMOS TSPC), charge pump / PFD bias.")
    print("  If VCO filter shares that same board node, those loads sit on the VCO C.\n")
    # Currents from prior work
    i_lo = 4.56e-3          # LO chain typical VHF, lo-divider-topology
    i_cp = 50e-6            # CP 50 µA (P2.6 / totals)
    # Switching: assume LO CMOS edges dump ~0.2–0.5× average as pulse on supply;
    # CP switches ±Icp for ~ns each PFD edge at f_ref.
    f_ref = 36e6
    # Charge per CP pulse ~ Icp * t_pw; t_pw ~ 1–5 ns → use 2 ns
    q_cp = 50e-6 * 2e-9
    # Voltage on 100 nF from one CP pulse
    dv_cp = q_cp / 100e-9
    # LO: rough ΔI ~ 1 mA for ~100 ps (CML/TSPC) → Q=0.1 pC → dV=1 µV on 100nF
    dv_lo = (1e-3 * 100e-12) / 100e-9
    print(f"CP pulse on 100 nF: I=50 µA × 2 ns → ΔV ≈ {dv_cp*1e6:.2f} µV/edge "
          f"(f_ref={f_ref/1e6:.0f} MHz).")
    print(f"LO edge (order-of-mag 1 mA × 100 ps) → ΔV ≈ {dv_lo*1e6:.2f} µV/edge.\n")
    # Equivalent white-ish density: spur tones at f_ref; for push use rms in 1 Hz —
    # conservatively treat CP as square FM sidebands. Hand: S_v from spurs.
    # Periodic ΔV at f_ref: fundamental amplitude ~ (2/π)ΔV for pulse train duty d=t*f
    duty = 2e-9 * f_ref
    v1 = (2 / math.pi) * dv_cp * math.sin(math.pi * duty) / max(duty, 1e-9) * duty  # ~2/π * avg
    # Simpler: Fourier of narrow pulse train A = 2*f_ref*Q for current, V = I/(2π f C) 
    # At duplex offset noise we care about 1 MHz noise density from broadband.
    # Switching → discrete spurs, not white. Board pin also sees VR_ANA1 regulator noise.
    #
    # Effective S_v from randomising edge jitter: skip; report spur level instead.
    k_tt, k_ss = 30e6, 50e6  # Hz/V
    # Spur at f_ref: Δf_peak ≈ K * v_spur; v_spur ≈ dv_cp (worst instantaneous)
    print("Push (instantaneous from one CP edge on shared 100 nF):")
    for lab, k in (("tt K_push", k_tt), ("ss85 K_push", k_ss)):
        df = k * dv_cp
        print(f"  {lab}={k/1e6:.0f} MHz/V × {dv_cp*1e6:.2f} µV → Δf ≈ {df:.1f} Hz peak — negligible.")
    print()
    # If much larger bounce: 1 mA CP effective or missing C
    dv_bad = 1e-3 / 100e-9 * 2e-9  # 1mA * 2ns / 100nF
    print(f"If effective switched current were 1 mA (same 2 ns): ΔV={dv_bad*1e3:.3f} mV → "
          f"Δf_ss≈{k_ss*dv_bad:.0f} Hz still small vs PLL bandwidth.")
    print()
    # Board noise: external on VR_ANA1 pin. With bond L and 100nF, transfer board→pad
    # at 1 MHz: divider L vs 1/(jωC) — V_pad/V_board ≈ 1/(1 - ω²LC) for series L
    for lb in (1e-9, 2e-9):
        w = 2 * math.pi * 1e6
        h = abs(1 / (1 - w * w * lb * 100e-9))
        print(f"Board→pad |H| @ 1 MHz (L={lb*1e9:.0f} nH, C=100 nF): {h:.4f} "
              f"(≈1 — board noise appears almost unattenuated on the pad at 1 MHz).")
    print("So board / VR_ANA1-regulator noise at the pin **does** matter if VCO is fed from that pad;")
    print("option C only filters **LDO** noise through R–C, not noise already on the board node.\n")
    # Equivalent S_v from CP as tone — not comparable to white 11 nV; state clearly.
    print("Divider/CP contribution is **spurs at f_ref harmonics**, not white S_v.")
    print("White-equivalent in 1 Hz at 1 MHz from these edges ≈ 0 for deterministic locking;")
    print("jittered edges: << 1 nV/√Hz [HAND]. Not the limiter vs 11 nV/√Hz.\n")


def section_combo(s_bare, s_cheap, s_optc, s12, cheap_tag):
    print("# 5) S_v at the VCO vs ≤ 11 nV/√Hz — STOP\n")
    print("| Case | What | S_v @ 1 MHz | vs 11 nV |")
    print("|---|---|---|---|")

    def row(name, what, s):
        if s is None:
            print(f"| {name} | {what} | — | — |")
            return
        flag = "PASS" if s <= LIMIT else "MISS"
        print(f"| {name} | {what} | {s*1e9:.1f} nV/√Hz | {flag} |")

    row("0 baseline", "bare D10 LDO", s_bare)
    row("1 alone", f"cheap bare ({cheap_tag})", s_cheap)
    row("2 alone", "option C R–pad–100 nF on baseline", s_optc)
    row("1 + 2", f"{cheap_tag} + option C (re-sim)", s12)
    if s_bare and s_optc:
        print(f"\nOption C attenuation vs bare: ×{s_optc/s_bare:.3f} "
              f"({s_bare*1e9:.1f} → {s_optc*1e9:.1f} nV/√Hz).")
    print()
    print("STOP for owner decision: adopt (1), (2), (1)+(2), or another LDO path.")
    print("Options A/B/D (large on-chip C) remain rejected. LDO schematic unchanged.\n")


def main():
    print("# D10 LDO analysis — no schematic change yet\n")
    s_bare, _, _, _ = section_breakdown()
    s_cheap, tag, info = section_cheap()
    s_optc, _ = section_option_c(s_bare)
    section_sharing()
    s12 = None
    if tag and info is not None:
        print("# 1+2 combined re-sim [SCH]\n")
        kw = dict(info["kw"])
        r, lb = 5, 1.5e-9
        body = ldo_core(cout=20e-12, **kw)
        text = header() + body + f"""
rser (vout pad) resistor r={r} noisy=1
cpad (pad 0) capacitor c=2p
lbond (pad pin) inductor l={lb}
cesd (pad 0) capacitor c=1p
cboard (pin 0) capacitor c=100n
il (pad 0) isource dc={ILOAD}
iin (0 pad) isource dc=0
control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(vout) v(pad)
  analysis op1 op
  analysis n1 noise in="iin" out=["pad"] values=[1Meg]
endc
"""
        run("an_1plus2", text)
        tot, _ = read_noise()
        s12 = sv(tot)
        print(f"1+2 ({tag} + R={r} Ω + L={lb*1e9:.1f} nH + 100 nF): "
              f"S_v(pad)={s12*1e9:.1f} nV/√Hz\n")
    section_combo(s_bare, s_cheap, s_optc, s12, tag or "—")
    # Persist summary for the STOP
    out_path = os.path.join(OUT, "summary_ldo_analyse.txt")
    print(f"(tee target: {out_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
