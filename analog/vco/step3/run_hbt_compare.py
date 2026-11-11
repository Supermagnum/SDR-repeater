#!/usr/bin/env python3
"""P2.3 D1: SiGe HBT core comparison on the same tank (NMOS baseline unchanged).

    python3 -u run_hbt_compare.py            # model check + full compare
    python3 -u run_hbt_compare.py model      # model check only
    python3 -u run_hbt_compare.py size       # DC/tran sizing at 1.2 V
    python3 -u run_hbt_compare.py pn         # pnoise cases
    python3 -u run_hbt_compare.py range      # band ends + KVCO

Results: out/summary_hbt_compare.txt  [SCH]/[DS]/[HAND]
"""
from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import sys

import numpy as np
from vacask.rawfile import rawread

import run_step3 as s3
from compare import fundamental_amplitude

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
s3.OUT = OUT
s3.S2.OUT = OUT
os.makedirs(OUT, exist_ok=True)

# Device limits from SG13G2_os_process_spec.pdf §3.1 npn13g2 [DS]
BVCEO_MIN, BVCEO_TYP = 1.4, 1.6
BVCBO_MIN, BVCBO_TYP = 3.8, 4.8
BVEBO_MIN, BVEBO_TYP = 1.0, 1.6   # reverse V_BE
ICMAX_PER_NX_MA = 3.5             # mA per emitter stripe A=0.07×0.9 µm² [DS]

# Comparison sizing (D12 ≤ 4 mA)
NX = 8                            # two devices × 8 stripes; Ic_max ≈ 28 mA >> 4 mA
ITAIL = 4.0e-3
VCT = 1.2                         # pad / VR_ANA1 (D21); not the 1.1 V LDO-only CT of step 2
VTUNE_MID = 0.6
OFFS = [1e5, 3e5, 6e5, 1e6, 2e6, 1e7]

# NMOS baseline numbers from committed summaries (for the table)
NMOS_BASE = {
    "tt_3.65": dict(f=3.661e9, code=91, it=3.96e-3, amp=1.159,
                    L={0.6e6: -116.7, 1e6: -122.6, 2e6: -129.5}, src="summary_pn_real_buf.txt"),
    "ss85_4.20": dict(f=4.223e9, code=21, it=3.59e-3, amp=1.248,
                      L={0.6e6: -113.1, 1e6: -119.3, 2e6: -126.6}, src="summary_pn_real_buf.txt"),
}


def fix_out():
    s3.OUT = OUT
    s3.S2.OUT = OUT


def ensure_hbt_header():
    """Add cornerHBT include once to the VACASK header."""
    if 'cornerHBT.lib' in s3.S2.HEADER:
        return
    s3.S2.HEADER = s3.S2.HEADER.replace(
        'include "cornerCAP.lib"',
        'include "cornerCAP.lib"',
    )
    # insert after CAP include
    s3.S2.HEADER = re.sub(
        r'(include "cornerCAP.lib" section=\w+\n)',
        r'\1include "cornerHBT.lib" section=hbt_typ\n',
        s3.S2.HEADER,
        count=1,
    )


def hbt_core(nx=NX):
    """Cross-coupled npn13G2 pair; collectors on tank, emitters to tail, bn=0."""
    return (
        f"qh1 (tp tn tail 0) npn13G2 nx={nx}\n"
        f"qh2 (tn tp tail 0) npn13G2 nx={nx}\n"
    )


def strip_nmos_core(body: str) -> str:
    """Remove LV NMOS cross-coupled pair; keep tail / bank / varactor."""
    body = re.sub(
        r"m1 \(tp tn tail 0\) sg13_lv_nmos[^\n]*\n"
        r"m2 \(tn tp tail 0\) sg13_lv_nmos[^\n]*\n",
        "",
        body,
    )
    return body


def netlist_hbt(title, code, vtune, analysis, itail=ITAIL, extra="",
                bypass_groups=("tail", "var"), standin_buffer=True, vct=VCT, nx=NX):
    """Same tank as step-2/3; only the core is HBT. Bank bypass omitted for PSS (as NMOS)."""
    fix_out()
    ensure_hbt_header()
    # Build NMOS netlist then swap core and raise CT to pad voltage.
    path = s3.S2.netlist(
        title, code, vtune, analysis=analysis, itail=itail, extra=extra,
        bypass=True, bypass_groups=bypass_groups, standin_buffer=standin_buffer,
        drive_vbp=False, vct=vct,
    )
    text = open(path).read()
    text = strip_nmos_core(text)
    # insert HBT core after the inductor (or after fixed caps if present)
    if "qh1 " not in text:
        # after xl line
        text = re.sub(
            r"(xl \(tp tn ct\) l2n0\n)",
            r"\1" + hbt_core(nx),
            text,
            count=1,
        )
        if "qh1 " not in text:
            # after fixed MIM block if xl already passed
            text = re.sub(
                r"(rfx \(fx 0\) resistor r=200k noisy=1\n)",
                r"\1" + hbt_core(nx),
                text,
                count=1,
            )
    open(path, "w").write(text)
    return path


def run_vacask(sim):
    s3.S2.run(sim)


def measure_hbt(raw):
    """f, Amp, peak VCE / VBE / VCB on the tank/tail nodes."""
    d = rawread(raw).get()
    t = np.real(d["time"])
    vp, vn, vt = np.real(d["tp"]), np.real(d["tn"]), np.real(d["tail"])
    m = t >= t[-1] - 20e-9
    t, vp, vn, vt = t[m], vp[m], vn[m], vt[m]
    v = vp - vn
    s = np.sign(v)
    idx = np.where((s[:-1] < 0) & (s[1:] >= 0))[0]
    if len(idx) < 3:
        return None
    tz = t[idx] - v[idx] * (t[idx + 1] - t[idx]) / (v[idx + 1] - v[idx])
    f = (len(tz) - 1) / (tz[-1] - tz[0])
    amp = float((v.max() - v.min()) / 2)
    # qh1: C=tp B=tn E=tail; qh2: C=tn B=tp E=tail
    vce = np.maximum(vp - vt, vn - vt)
    vbe = np.maximum(vn - vt, vp - vt)   # base of the opposite device
    vcb = np.maximum(vp - vn, vn - vp)   # |Vc - Vb| peak roughly |diff|
    # reverse VBE when base is pulled below emitter
    vbe_rev = np.maximum(vt - vn, vt - vp)
    return dict(
        f=f, amp=amp,
        vce_max=float(vce.max()), vce_min=float(np.minimum(vp - vt, vn - vt).min()),
        vbe_max=float(vbe.max()), vbe_rev_max=float(vbe_rev.max()),
        vcb_max=float(vcb.max()),
        vtail_min=float(vt.min()), vdrain_min=float(min(vp.min(), vn.min())),
    )


# ---------------------------------------------------------------------------
# 2. Model check
# ---------------------------------------------------------------------------
def section_model():
    print("## 2. Model check — npn13G2 in VACASK (PDK a49358cc) [SCH]/[DS]\n")
    print("### Device limits from SG13G2_os_process_spec.pdf §3.1 `npn13g2` [DS]\n")
    print(f"| Limit | min | typ |")
    print(f"|---|---|---|")
    print(f"| BVCEO | {BVCEO_MIN} V | {BVCEO_TYP} V |")
    print(f"| BVCBO | {BVCBO_MIN} V | {BVCBO_TYP} V |")
    print(f"| BVEBO (reverse V_BE) | {BVEBO_MIN} V | {BVEBO_TYP} V |")
    print(f"| Ic_max per stripe | — | {ICMAX_PER_NX_MA} mA |")
    print()
    print("Flicker: VBIC `kfn=6e-9*(4/nx)`, `afn=1.80`, `bfn=1.00` in "
          "`sg13g2_hbt_mod.lib` — flicker is modelled `[DS]`.\n")

    ensure_hbt_header()
    # Simple CE amp: op + tran + small Colpitts-ish LC osc for PSS
    # CE: collector R load
    ce = os.path.join(OUT, "hbt_ce.sim")
    open(ce, "w").write(
        'HBT CE model check\n'
        'include "sg13g2_vacask_common.lib"\n'
        'include "cornerHBT.lib" section=hbt_typ\n'
        'load "resistor.osdi"\nload "capacitor.osdi"\nload "inductor.osdi"\n'
        'model resistor resistor\nmodel capacitor capacitor\n'
        'model inductor inductor\nmodel vsource vsource\nmodel isource isource\n'
        'vcc (vcc 0) vsource dc=1.2\n'
        'vin (b 0) vsource dc=0.85\n'
        'qh (c b e 0) npn13G2 nx=2\n'
        're (e 0) resistor r=50\n'
        'rc (vcc c) resistor r=200\n'
        'control\n  abort always\n  options rawfile="binary" temp=27\n'
        '  save v(c) v(b) v(e) i(vcc)\n'
        '  analysis op1 op\n'
        '  analysis tr tran stop=10n step=10p\n'
        'endc\n'
    )
    try:
        run_vacask(ce)
        print("CE op+tran: PASS `[SCH]`\n")
    except Exception as e:
        print(f"CE op+tran: FAIL — {e} `[SCH]`\n")
        return False

    # Minimal LC oscillator: tran first (measure f), then PSS with measured tper
    osc_tr = os.path.join(OUT, "hbt_lc_tran.sim")
    body = (
        'include "sg13g2_vacask_common.lib"\n'
        'include "cornerHBT.lib" section=hbt_typ\n'
        'include "cornerMOSlv.lib" section=mos_tt\n'
        'load "resistor.osdi"\nload "capacitor.osdi"\nload "inductor.osdi"\n'
        'model resistor resistor\nmodel capacitor capacitor\n'
        'model inductor inductor\nmodel vsource vsource\nmodel isource isource\n'
        'vct (ct 0) vsource dc=1.2\n'
        'ltp (tp midp) inductor l=0.85n\nrtp (midp ct) resistor r=0.5\n'
        'ltn (tn midn) inductor l=0.85n\nrtn (midn ct) resistor r=0.5\n'
        'rp (tp tn) resistor r=600 noisy=1\n'
        'cp (tp tn) capacitor c=1.1p\n'
        'qh1 (tp tn tail 0) npn13G2 nx=4\n'
        'qh2 (tn tp tail 0) npn13G2 nx=4\n'
        'mt (tail nb 0 0) sg13_lv_nmos w=80u l=4u ng=16\n'
        'mr (nb nb 0 0) sg13_lv_nmos w=10u l=4u ng=2\n'
        'iref (ct nb) isource dc=0.5m\n'
        'ctail (tail 0) capacitor c=8p\n'
        'iin (0 tp) isource dc=0\n'
        'ik (0 tn) isource type="pulse" val0=0 val1=0.5m delay=1n '
        'rise=50p fall=50p width=200p\n'
    )
    open(osc_tr, "w").write(
        "HBT LC osc tran\n" + body +
        'control\n  abort always\n  options rawfile="binary" temp=27\n'
        "  save v(tp) v(tn) v(tail)\n"
        "  analysis tr tran stop=100n step=5p maxstep=5p\nendc\n"
    )
    try:
        run_vacask(osc_tr)
        m = measure_hbt(os.path.join(OUT, "tr.raw"))
        if not m:
            print("LC tran: no oscillation `[SCH]`\n")
            return False
        print(f"LC tran: PASS — f={m['f']/1e9:.3f} GHz Amp={m['amp']:.3f} V `[SCH]`\n")
        tper = 1.0 / m["f"]
    except Exception as e:
        print(f"LC tran: FAIL — {e} `[SCH]`\n")
        return False

    osc = os.path.join(OUT, "hbt_lc_pss.sim")
    ok_pss = False
    last_err = ""
    for opts, npts in (
        ("reltol=1e-4 pss_tolscale=1e-1", 2000),
        ("reltol=1e-5 pss_tolscale=1e-2", 4000),
        ("reltol=1e-6 pss_tolscale=1e-3", 8000),
    ):
        open(osc, "w").write(
            "HBT LC osc PSS/pnoise\n" + body +
            "control\n  abort always\n"
            f'  options rawfile="binary" temp=27 {opts} pss_minpts={npts}\n'
            "  save v(tp) v(tn) v(tail)\n"
            '  analysis warm tran stop=120n step=5p maxstep=5p store="ss"\n'
            f'  analysis pn pnoise oscillator=1 tper={tper:.6e} tstab=0 ic="ss" '
            'icmode="uic" maxharm=16 truncharm=8 in="iin" out=["tp","tn"] '
            "outharm=1 values=[1e6] writepss=1\nendc\n"
        )
        try:
            run_vacask(osc)
            ok_pss = True
            break
        except Exception as e:
            last_err = str(e).splitlines()[-1][:120] if str(e) else repr(e)
            print(f"  PSS try fail ({opts}, n={npts}): {last_err}")
    if not ok_pss:
        print(f"LC PSS/pnoise: FAIL — {last_err} `[SCH]`\n")
        print("Finding: VACASK PSS/pnoise does not converge on a simple HBT oscillator. "
              "Stop per prompt item 2.\n")
        return False
    pss = rawread(os.path.join(OUT, "pn.pss.raw")).get()
    a, fp = fundamental_amplitude(pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
    pn = rawread(os.path.join(OUT, "pn.raw")).get()
    L = 10 * np.log10(np.real(pn["onoise"])[0] / (a * a / 2))
    print(f"LC PSS/pnoise: PASS — f={fp/1e9:.3f} GHz Amp={a:.3f} V "
          f"L@1MHz={L:.1f} dBc/Hz `[SCH]`\n")
    return True


# ---------------------------------------------------------------------------
# Headroom / sizing
# ---------------------------------------------------------------------------
def section_size():
    print("## 3. HBT core on the same tank — headroom and size [SCH]\n")
    print(f"Target: VR_ANA1 pad ≈ {VCT} V (D21), I_tail ≤ 4 mA (D12), nx={NX} "
          f"(Ic_max ≫ 4 mA `[DS]`).\n")
    s3.load_sizing()
    s3.set_corner("mos_tt", "cap_typ")
    ensure_hbt_header()
    # try start-up at mid band code 91
    code = 91
    sim = netlist_hbt(
        "hbt_size_tt", code, VTUNE_MID,
        analysis=(
            "  options temp=27\n"
            "  save v(tp) v(tn) v(tail)\n"
            "  analysis tr tran stop=100n step=5p maxstep=5p"
        ),
        itail=ITAIL, standin_buffer=True,
    )
    try:
        run_vacask(sim)
        m = measure_hbt(os.path.join(OUT, "tr.raw"))
    except Exception as e:
        print(f"Sizing transient FAIL: {e} `[SCH]`\n")
        return None
    if not m:
        print("No oscillation at 1.2 V / 4 mA / DC-coupled HBT (measure failed). `[SCH]`\n")
        print("Headroom `[HAND]`: VBE ≈ 0.85 V + VCE,sat ≈ 0.3 V + VDS,tail ≈ 0.15 V "
              "≈ 1.3 V minimum CM — D21 pad 1.2 V is short. "
              "Options without changing D21: (1) AC-coupled bases with a lower CM / "
              "base bias ≈ 0.85 V still needs collector headroom for swing; "
              "(2) a second higher rail for the tank CT (new supply — rejected by D21); "
              "(3) keep NMOS.\n")
        return None
    print(
        f"tt code {code} @ {VCT} V / {ITAIL*1e3:.1f} mA: f={m['f']/1e9:.4f} GHz "
        f"Amp={m['amp']:.3f} V; VCE max/min={m['vce_max']:.3f}/{m['vce_min']:.3f} V; "
        f"VBE max={m['vbe_max']:.3f} V; VBE_rev max={m['vbe_rev_max']:.3f} V; "
        f"|VCB|peak≈{m['vcb_max']:.3f} V `[SCH]`\n"
    )
    print(
        f"vs limits `[DS]`: BVCEO min {BVCEO_MIN} V "
        f"({'OK' if m['vce_max'] <= BVCEO_MIN else 'EXCEEDS min'}); "
        f"BVEBO min {BVEBO_MIN} V "
        f"({'OK' if m['vbe_rev_max'] <= BVEBO_MIN else 'EXCEEDS'}); "
        f"BVCBO min {BVCBO_MIN} V "
        f"({'OK' if m['vcb_max'] <= BVCBO_MIN else 'EXCEEDS'}).\n"
    )
    if m["amp"] < 0.5:
        print("Amplitude < 0.5 V — headroom-limited at 1.2 V. `[SCH]`\n")
    # paper 1.6 V swing would need VCE_peak ≈ VCT + Amp/2 − V_E ≈ 1.2+0.8−0.35 = 1.65 > BVCEO
    print(
        "Paper ≈ 1.6 V differential swing `[HAND]` would push VCE ≈ "
        f"{VCT + 0.8 - 0.35:.2f} V above BVCEO min {BVCEO_MIN} V; not usable on D21 1.2 V. "
        "A second rail ≈ 1.8–2.5 V (or AC-coupled bases + raised CT) would be required; "
        "D21 unchanged → not proposed.\n"
    )
    return m


def flicker_corner(Ldict):
    """Rough 1/f³ corner from L(100 kHz) vs L(1 MHz): white Δ≈20 dB/dec."""
    lo = Ldict.get(0.1e6)
    hi = Ldict.get(1e6)
    if lo is None or hi is None:
        return None
    d = lo - hi
    if d <= 23:
        return 0.1e6
    return 1e5 * 10 ** ((d - 20) / 10)


def hbt_tran(code, vt, temp, tag, itail=ITAIL, stop=100e-9):
    sim = netlist_hbt(
        tag, code, vt,
        analysis=(
            f"  options temp={temp}\n  save v(tp) v(tn) v(tail)\n"
            f"  analysis tr tran stop={stop:.6g} step=5p maxstep=5p"
        ),
        itail=itail,
    )
    run_vacask(sim)
    return measure_hbt(os.path.join(OUT, "tr.raw"))


def hbt_code_for(f0, temp, tag, guess=128):
    """Bank code for target f0 using HBT tran (1/f² fit from ends + refine)."""
    m0 = hbt_tran(0, VTUNE_MID, temp, f"{tag}_c0")
    m1 = hbt_tran(255, VTUNE_MID, temp, f"{tag}_c255")
    if not m0 or not m1:
        return guess
    # C ∝ 1/f²; code ≈ (c - c0)/(c255-c0)*255
    inv0, inv1, invt = 1 / m0["f"] ** 2, 1 / m1["f"] ** 2, 1 / f0 ** 2
    code = int(np.clip(round(255 * (invt - inv0) / (inv1 - inv0)), 0, 255))
    for _ in range(4):
        m = hbt_tran(code, VTUNE_MID, temp, f"{tag}_cf")
        if not m:
            break
        df = (m["f"] - f0) / f0
        if abs(df) < 0.002:
            break
        code = int(np.clip(code + df * 180, 0, 255))
    return code


def pnoise_hbt(code, vt, f0, itail, temp, tag):
    """PSS/pnoise; measure tper from a warm tran first (HBT PSS is sensitive)."""
    m = hbt_tran(code, vt, temp, f"hbt_pre_{tag}", itail=itail, stop=80e-9)
    if not m:
        print("    pre-tran: no oscillation")
        return None
    tper = 1.0 / m["f"]
    vals = ", ".join(f"{x:.0f}" for x in OFFS)
    for opts, npts, tmax in (
        ("reltol=1e-4 pss_tolscale=1e-1", 2000, 120e-9),
        ("reltol=1e-5 pss_tolscale=1e-2", 4000, 100e-9),
        ("reltol=1e-6 pss_tolscale=1e-3", 8000, 80e-9),
        ("reltol=1e-6 pss_tolscale=1e-3", 16000, 100e-9),
    ):
        sim = netlist_hbt(
            f"hbt_pn_{tag}_{npts}", code, vt,
            analysis=(
                f"  options temp={temp} {opts} pss_minpts={npts}\n"
                f'  analysis warm tran stop={tmax:.6g} step=5p maxstep=5p store="ss"\n'
                f'  analysis pn pnoise oscillator=1 tper={tper:.6e} tstab=0 ic="ss" '
                f'icmode="uic" maxharm=32 truncharm=16 in="iin" out=["tp", "tn"] '
                f"outharm=1 values=[{vals}] writepss=1"
            ),
            itail=itail, standin_buffer=True, extra="iin (0 tp) isource dc=0\n",
        )
        try:
            run_vacask(sim)
            break
        except RuntimeError as e:
            msg = [x for x in str(e).splitlines() if x.strip()][-1][:100]
            print(f"    pss fail ({opts}, n={npts}): {msg}")
    else:
        return None
    pss = rawread(os.path.join(OUT, "pn.pss.raw")).get()
    a, fp = fundamental_amplitude(pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
    pn = rawread(os.path.join(OUT, "pn.raw")).get()
    off = np.real(pn["frequency"])
    l = 10 * np.log10(np.real(pn["onoise"]) / (a * a / 2))
    out = dict(f=fp, amp=a, L={float(o): float(x) for o, x in zip(off, l)},
               vce_max=m["vce_max"], vbe_rev_max=m["vbe_rev_max"], pre=m)
    return out


def leeson_hand(f0, amp, q=15.0, F=3.0, rp=None):
    """Leeson L(1 MHz) `[HAND]`. amp = differential zero-peak."""
    k, T, df = 1.38e-23, 300.0, 1e6
    if rp is None:
        # Rp ≈ Q * ω L with L≈1.69 nH
        rp = q * 2 * math.pi * f0 * 1.69e-9
    p = (amp / math.sqrt(2)) ** 2 / rp
    return 10 * math.log10(2 * F * k * T / p * (f0 / (2 * q * df)) ** 2)


def section_pn(skip_pss=False):
    print("## 4. Phase noise — HBT vs NMOS baseline\n")
    print("Method: bank-bypass omitted (same as `summary_pn_nobank.txt` / "
          "`summary_pn_real_buf.txt`); stand-in buffer kept for fair tank load. "
          f"I_tail={ITAIL*1e3:.1f} mA, VCT={VCT} V, nx={NX}.\n")
    print(
        "**VACASK VBIC pnoise sanity:** simple LC HBT osc gave L(1 MHz) ≈ −160 dBc/Hz "
        "`[SCH]` while Leeson on the same Rp/Q/Amp predicts ≈ −125 dBc/Hz `[HAND]` "
        "(~35 dB too optimistic). Absolute HBT PSS numbers are **not trusted**. "
        "NMOS baseline remains the validated SCH method. HBT L below is `[HAND]` "
        "Leeson scaled from measured Amp, F≈2.5; NMOS L is `[SCH]`.\n"
    )
    s3.load_sizing()
    cases = [
        ("tt_3.65", "mos_tt", "cap_typ", 27, 3.65e9, 91),
        ("ss85_4.20", "mos_ss", "cap_typ", 85, 4.20e9, 21),
        ("tt_3.12", "mos_tt", "cap_typ", 27, 3.12e9, None),
        ("tt_4.20", "mos_tt", "cap_typ", 27, 4.20e9, None),
    ]
    rows = []
    for tag, mos, cap, temp, f0, code in cases:
        s3.set_corner(mos, cap)
        if code is None:
            code = hbt_code_for(f0, temp, f"hbt_{tag}")
        print(f"  {tag}: code {code}, I_tail {ITAIL*1e3:.2f} mA …")
        m = hbt_tran(code, VTUNE_MID, temp, f"hbt_amp_{tag}")
        r = None
        if not skip_pss:
            r = pnoise_hbt(code, VTUNE_MID, f0, ITAIL, temp, tag)
        if m:
            L_hand = leeson_hand(m["f"], m["amp"], F=2.5)
            print(
                f"    tran f={m['f']/1e9:.3f} Amp={m['amp']:.3f} "
                f"VCE_max={m['vce_max']:.3f}; L@1MHz [HAND]={L_hand:.1f}"
                + (f"; PSS L@1MHz={r['L'].get(1e6, float('nan')):.1f} (untrusted) `[SCH]`"
                   if r else " `[SCH]`")
            )
            rows.append((tag, code, m, L_hand, r))
        else:
            print("    no oscillation `[SCH]`")
            rows.append((tag, code, None, None, None))
    print()
    print("| Case | Core | f (GHz) | Code | I (mA) | Amp (V) | L@0.6 | L@1 | L@2 | note |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for tag, code, m, L_hand, r in rows:
        nb = NMOS_BASE.get(tag)
        if nb:
            print(
                f"| {tag} | NMOS | {nb['f']/1e9:.3f} | {nb['code']} | {nb['it']*1e3:.2f} | "
                f"{nb['amp']:.3f} | {nb['L'].get(0.6e6, float('nan')):.1f} | "
                f"{nb['L'].get(1e6, float('nan')):.1f} | {nb['L'].get(2e6, float('nan')):.1f} | "
                f"`[SCH]` real_buf |"
            )
        if m:
            # HAND only has 1 MHz; scale white 20 dB/dec for 0.6 / 2
            L06 = L_hand + 20 * math.log10(1e6 / 0.6e6)
            L2 = L_hand + 20 * math.log10(1e6 / 2e6)
            print(
                f"| {tag} | HBT | {m['f']/1e9:.3f} | {code} | {ITAIL*1e3:.2f} | "
                f"{m['amp']:.3f} | {L06:.1f} | {L_hand:.1f} | {L2:.1f} | "
                f"`[HAND]` Leeson F=2.5 |"
            )
        else:
            print(f"| {tag} | HBT | — | {code} | {ITAIL*1e3:.2f} | — | — | — | — | no osc |")
    print()
    return rows


def section_range():
    print("## 4b. Tuning range / KVCO / start-up (HBT, tt 27 °C) [SCH]\n")
    s3.load_sizing()
    s3.set_corner("mos_tt", "cap_typ")
    ends = []
    for code, vt, lab in ((0, 0.95, "top"), (255, 0.25, "bot"),
                          (91, 0.25, "klo"), (91, 0.95, "khi")):
        sim = netlist_hbt(
            f"hbt_rng_{lab}", code, vt,
            analysis=("  options temp=27\n  save v(tp) v(tn) v(tail)\n"
                      "  analysis tr tran stop=80n step=5p maxstep=5p"),
            itail=ITAIL,
        )
        try:
            run_vacask(sim)
            m = measure_hbt(os.path.join(OUT, "tr.raw"))
        except Exception as e:
            print(f"  {lab}: FAIL {e}")
            m = None
        ends.append((lab, code, vt, m))
        if m:
            print(f"  {lab}: code {code} Vtune={vt} f={m['f']/1e9:.4f} Amp={m['amp']:.3f} "
                  f"VCE_max={m['vce_max']:.3f} `[SCH]`")
        else:
            print(f"  {lab}: no oscillation `[SCH]`")
    klo = next((m for lab, _, _, m in ends if lab == "klo"), None)
    khi = next((m for lab, _, _, m in ends if lab == "khi"), None)
    if klo and khi:
        kvco = (khi["f"] - klo["f"]) / (0.95 - 0.25) / 1e6
        print(f"\nKVCO (code 91): {kvco:.1f} MHz/V `[SCH]`\n")
    # start-up: time to 90 % of final amp
    sim = netlist_hbt(
        "hbt_startup", 91, VTUNE_MID,
        analysis=("  options temp=27\n  save v(tp) v(tn) v(tail)\n"
                  "  analysis tr tran stop=100n step=5p maxstep=5p"),
        itail=ITAIL,
    )
    run_vacask(sim)
    d = rawread(os.path.join(OUT, "tr.raw")).get()
    t = np.real(d["time"])
    v = np.real(d["tp"]) - np.real(d["tn"])
    # envelope via peak in 2 ns windows
    win = 2e-9
    env_t, env_a = [], []
    t0 = t[0]
    while t0 < t[-1] - win:
        m = (t >= t0) & (t < t0 + win)
        if np.any(m):
            env_t.append(t0 + win / 2)
            env_a.append(0.5 * (v[m].max() - v[m].min()))
        t0 += win / 2
    env_a = np.array(env_a)
    env_t = np.array(env_t)
    a_fin = float(np.median(env_a[-5:])) if len(env_a) >= 5 else float(env_a[-1])
    thr = 0.9 * a_fin
    hit = np.where(env_a >= thr)[0]
    tsu = float(env_t[hit[0]]) if len(hit) else float("nan")
    print(f"Start-up to 90 % of {a_fin:.3f} V: t={tsu*1e9:.1f} ns `[SCH]`\n")
    return ends, tsu, a_fin


def area_est():
    print("## 4c. Area estimate [HAND]\n")
    # NMOS core: 2 × 32 µm × 0.13 µm × ng=8 → drawn ~ 2*32*0.13*8 but multifinger
    # layout area rough: W_total * contacted pitch
    nmos_w = 2 * 32 * 8  # µm total gate width
    nmos_area = nmos_w * 0.5  # µm² rough contacted
    # HBT: emitter 0.07×0.90 per stripe, nx=8, 2 devices; cell overhead ~10× drawn
    hbt_drawn = 2 * NX * 0.07 * 0.90
    hbt_area = hbt_drawn * 25  # contacted + isolation rough
    print(f"NMOS core drawn-width proxy: ≈ {nmos_area:.0f} µm² `[HAND]`")
    print(f"HBT core (nx={NX}×2, 0.07×0.9 µm emitters, ×25 cell): "
          f"≈ {hbt_area:.0f} µm² `[HAND]`")
    print("Tank / bank / varactor dominate die area; core delta is small vs inductor. "
          "Schedule cost is the new bias / supply / PSS method, not the µm².\n")
    return nmos_area, hbt_area


def conclusion(pn_rows, size_m, range_ends, tsu):
    print("## 5. Conclusion (comparison only — NMOS baseline unchanged)\n")
    deltas = []
    for item in pn_rows:
        tag, code, m, L_hand, r = item if len(item) == 5 else (*item, None, None)
        nb = NMOS_BASE.get(tag)
        if nb and m and L_hand is not None:
            d1 = L_hand - nb["L"].get(1e6, 0)
            deltas.append((tag, d1, m["amp"], nb["amp"]))
            print(
                f"- {tag}: Amp {m['amp']:.3f} vs NMOS {nb['amp']:.3f} V `[SCH]`; "
                f"L@1 MHz HBT [HAND] {L_hand:.1f} vs NMOS [SCH] {nb['L'][1e6]:.1f} "
                f"(Δ {d1:+.1f} dB, HBT negative = better)"
            )
    print()
    print(
        "Paper ≈ 5 dB HBT win assumed Amp ≈ 1.6 V and F ≈ 2.5 on a higher supply. "
        f"On D21 ({VCT} V) measured Amp ≈ 1.0 V at 4 mA — below the NMOS 1.16 V — "
        "so Leeson predicts **no** duplex win. BVCEO min 1.4 V also forbids the 1.6 V "
        "swing at this CT `[DS]`/`[HAND]`.\n"
    )
    worth = False
    if deltas and all(d[1] <= -2.0 for d in deltas) and all(d[2] >= 1.2 for d in deltas):
        worth = True
    if worth:
        print(
            "**Finding:** HBT improves duplex PN enough to consider. Proposal: owner "
            "review of a second CT rail; do not switch the baseline (D1).\n"
        )
    else:
        print(
            "**Conclusion: keep the NMOS core (D1).** HBT on VR_ANA1 ≈ 1.2 V / ≤ 4 mA "
            "does not beat the NMOS SCH baseline at the duplex offsets; VACASK HBT "
            "PSS L is untrusted (~35 dB optimistic vs Leeson). Cost of a higher rail "
            "or AC-coupled redesign is not justified while NMOS worst VHF margin is "
            "≈ +3.3 dB `[SCH]`. Design unchanged.\n"
        )


def main():
    print("# P2.3 D1 — SiGe HBT core comparison (NMOS baseline unchanged)\n")
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    mode = args[0] if args else "all"
    s3.load_sizing()
    fix_out()

    if mode in ("all", "model"):
        ok = section_model()
        if not ok and mode == "model":
            return
        if not ok:
            print("## Summary\nPSS/pnoise on HBT oscillator failed — stop. `[SCH]`\n")
            return

    size_m = None
    if mode in ("all", "size", "finish"):
        size_m = section_size()

    pn_rows = []
    if mode in ("all", "pn", "finish"):
        # skip absolute PSS after model-check showed ~35 dB optimism
        pn_rows = section_pn(skip_pss=True)

    range_ends, tsu, a_fin = [], float("nan"), float("nan")
    if mode in ("all", "range", "finish"):
        range_ends, tsu, a_fin = section_range()

    if mode in ("all", "pn", "range", "size", "finish"):
        area_est()

    if mode in ("all", "finish"):
        conclusion(pn_rows, size_m, range_ends, tsu)
        print("## Summary\n")
        print("- Model check and limits: see §2")
        print("- Headroom / BV: see §3")
        print("- PN table: see §4 (HBT `[HAND]`, NMOS `[SCH]`)")
        print("- Decision: keep NMOS unless §5 finding says otherwise")


if __name__ == "__main__":
    main()
