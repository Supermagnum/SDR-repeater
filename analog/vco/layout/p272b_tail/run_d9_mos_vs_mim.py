#!/usr/bin/env python3
"""P2.7.2b — D9 cbf: MIM vs thin-ox moscap_n (noise / C-V / leakage).

MIM area fails the island budget (see out/summary_area_d9.txt). This script:
  1) sizes 4× moscap_n 30u/30u (~55.5 pF at Cox≈15.4 fF/µm² [PDK]);
  2) measures C(V) and gate leakage at the nbf bias over corners [SCH];
  3) compares VCO pnoise (tt mid-band) with ideal/MIM-like 50 pF vs moscap
     at 100 kHz and 1 MHz — pass if |ΔL| < 0.2 dB.

    python3 -u run_d9_mos_vs_mim.py | tee out/summary_d9_mos_vs_mim.txt
"""
from __future__ import annotations

import math
import os
import re
import subprocess
import sys

import numpy as np
from vacask.rawfile import rawread

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
STEP2 = os.path.join(HERE, "..", "..", "step2")
STEP3 = os.path.join(HERE, "..", "..", "step3")
sys.path[:0] = [STEP2, STEP3, os.path.join(HERE, "..", "..", "..", "pn-validation")]

import run_step2 as S2  # noqa: E402
import run_step3 as S3  # noqa: E402
from compare import fundamental_amplitude  # noqa: E402

S2.OUT = OUT
S3.OUT = OUT
S3.S2 = S2

# PDK numbers
CAP_CAREA = 1.5e-15          # F/µm² MIM [PDK cornerCAP]
TOXO_N = 2.2404e-9           # m [PDK moscap_n]
COX = 3.9 * 8.854e-12 / TOXO_N  # F/m²
COX_FF = COX * 1e-3           # fF/µm² (F/m² → fF/µm²)
MOS_W = MOS_L = 30.0         # µm PCell max [TOOL]
MOS_M = 5                    # sized for ≈53 pF at Vnbf=0.6 V [SCH]
C_MOS = COX * (MOS_W * 1e-6) * (MOS_L * 1e-6) * MOS_M  # strong-inv ideal
PASS_DB = 0.2
OFFS = (1e5, 1e6)


def hdr_moscap(section="moscap_tt"):
    # cornerMOSCAP already includes sg13g2_moscap_mod.lib — do not include twice
    return (
        "D9 moscap probe\n\n"
        "ground 0\n"
        'include "sg13g2_vacask_common.lib"\n'
        f'include "cornerMOSCAP.lib" section={section}\n'
        'load "resistor.osdi"\nload "capacitor.osdi"\n'
        "model resistor resistor\nmodel capacitor capacitor\n"
        "model vsource vsource\nmodel isource isource\n"
    )


def mos_instances(g_node="nbf", sub="0", prefix="cbf"):
    """4× moscap_n in parallel, gate=nbf, sub=gnd."""
    lines = []
    for i in range(MOS_M):
        lines.append(
            f"X{prefix}{i} ({g_node} {sub}) sg13_moscap_n "
            f"w={MOS_W:.0f}u l={MOS_L:.0f}u m=1\n"
        )
    return "".join(lines)


def run_vacask(name: str, text: str) -> None:
    path = os.path.join(OUT, name + ".sim")
    open(path, "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(f"{name} failed:\n" + open(log).read()[-800:])


def cv_and_leak():
    """C_eff ≈ ΔQ/ΔV and Ig at V_nbf over corners [SCH]."""
    print("## MOSCAP C(V) and leakage [SCH]\n")
    print(f"Device: {MOS_M}× sg13_moscap_n W=L={MOS_W:g} µm; "
          f"Cox≈{COX_FF:.2f} fF/µm² → C_ideal≈{C_MOS*1e12:.1f} pF [PDK]\n")
    rows = []
    # vacask cornerMOSCAP.lib only ships moscap_tt (+ mismatch/stat) [PDK/TOOL]
    sec = "moscap_tt"
    print("Note: vacask cornerMOSCAP has only moscap_tt — temp sweep stands in for "
          "process corners [TOOL].\n")
    for temp in (-40, 27, 125):
        # AC capacitance at bias Vb: i(vac)/ (2πf·vac)
        for vb in (0.2, 0.4, 0.6, 0.8, 1.0):
            name = f"cv_{sec}_t{temp}_v{vb:.1f}".replace(".", "p").replace("-", "m")
            text = hdr_moscap(sec) + f"""
vb (nbf 0) vsource dc={vb} mag=1
{mos_instances()}
control
  abort always
  options temp={temp} reltol=1e-6 rawfile="binary" strictsave=1
  save di(vb)
  analysis ac1 ac values=[1e3]
endc
"""
            try:
                run_vacask(name, text)
                d = rawread(os.path.join(OUT, "ac1.raw")).get()
                i = None
                for k in d.names:
                    if k != "frequency":
                        i = complex(np.asarray(d[k]).ravel()[0])
                        break
                f = float(np.real(np.asarray(d["frequency"]).ravel()[0]))
                c = abs(i.imag) / (2 * math.pi * f)  # F
                rows.append((sec, temp, vb, c, "ac"))
            except Exception as e:
                print(f"  CV fail {name}: {e}")
        # DC gate leakage at 0.6 V (typical nbf)
        name = f"ig_{sec}_t{temp}".replace("-", "m")
        text = hdr_moscap(sec) + f"""
vb (nbf 0) vsource dc=0.6
vi (n nbf) vsource dc=0
{mos_instances("n", "0", "cbf")}
control
  abort always
  options temp={temp} reltol=1e-6 rawfile="binary" strictsave=1
  save di(vi)
  analysis op1 op
endc
"""
        try:
            run_vacask(name, text)
            d = rawread(os.path.join(OUT, "op1.raw")).get()
            ig = float(np.real(np.asarray(d["vi:flow(br)"]).ravel()[0]))
            rows.append((sec, temp, 0.6, ig, "ig"))
            print(f"| {sec} | {temp} °C | Ig @ 0.6 V = {ig:.3e} A |")
        except Exception as e:
            print(f"  Ig fail {name}: {e}")

    # summarise C at 0.6 V
    print("\n| Corner | T | V (V) | C (pF) |")
    print("|---|---|---|---|")
    for sec, temp, vb, c, kind in rows:
        if kind == "ac":
            print(f"| {sec} | {temp} | {vb:.1f} | {c*1e12:.2f} |")
    cs = [c for *_, c, kind in rows if kind == "ac" and abs(_[2] - 0.6) < 0.01]
    if len(cs) >= 2:
        c0 = cs[0]
        # voltage coeff over 0.2–1.0 at tt/27
        tt = [(vb, c) for sec, temp, vb, c, kind in rows
              if kind == "ac" and sec == "moscap_tt" and temp == 27]
        if len(tt) >= 2:
            vcs = [(c - tt[0][1]) / tt[0][1] / (vb - tt[0][0])
                   for vb, c in tt[1:] if abs(vb - tt[0][0]) > 1e-6]
            print(f"\nVoltage coefficient (tt/27, vs 0.2 V ref) ≈ "
                  f"{np.mean(vcs)*100:.2f} %/V [SCH]\n")
    return rows


def patch_cbf(sim_text: str, kind: str) -> str:
    """Replace ideal cbf line with MIM or moscap."""
    if kind == "mim":
        # rfcmim equivalent area for 50 pF: side = sqrt(50p/1.5f)
        side = math.sqrt(50e-12 / CAP_CAREA)
        repl = (f"xcbf (nbf 0 0) cap_rfcmim w={side:.3f}u l={side:.3f}u wfeed=5.0u\n")
    elif kind == "mos":
        repl = mos_instances()
    else:
        repl = "cbf (nbf 0) capacitor c=50p\n"
    # step2 netlist uses: cbf (nbf 0) capacitor c=50p
    new, n = re.subn(r"cbf \(nbf 0\) capacitor c=50p\n", repl, sim_text)
    if n != 1:
        raise RuntimeError(f"cbf replace count={n}")
    if kind == "mos":
        if "cornerMOSCAP" not in new:
            # Keep the MOSlv section=… clause; insert MOSCAP on the next line.
            new = re.sub(
                r'(include "cornerMOSlv\.lib" section=\w+)',
                r'\1\ninclude "cornerMOSCAP.lib" section=moscap_tt',
                new,
                count=1,
            )
    if kind == "mim":
        if "cornerCAP" not in new:
            # step2 already includes cornerCAP via common / capacitors
            pass
    return new


def pnoise_kind(kind: str, code: int, vt: float, f0: float, itail: float, temp: float):
    vals = ", ".join(f"{x:.0f}" for x in OFFS)
    tag = f"d9_{kind}"
    for opts, npts in (("reltol=1e-6 pss_tolscale=1e-3", 16000),
                       ("reltol=1e-6 pss_tolscale=1e-3", 8000)):
        sim = S2.netlist(
            f"s3_pn_{tag}", code, vt, itail=itail, bypass=True,
            bypass_groups=("tail", "var"),
            analysis=(
                f"  options temp={temp} {opts} pss_minpts={npts}\n"
                '  analysis warm tran stop=60n step=5p maxstep=5p store="ss"\n'
                f'  analysis pn pnoise oscillator=1 tper={1/f0:.6e} tstab=0 '
                f'ic="ss" icmode="uic" maxharm=32 truncharm=16 in="iin" '
                f'out=["tp", "tn"] outharm=1 values=[{vals}] writepss=1'
            ),
            extra="iin (0 tp) isource dc=0\n",
        )
        text = open(sim).read()
        text = patch_cbf(text, kind)
        open(sim, "w").write(text)
        try:
            S2.run(sim)
            break
        except RuntimeError as e:
            print(f"  pss failed ({kind}, {npts}): "
                  f"{[x for x in str(e).splitlines() if x.strip()][-2:]}")
    else:
        return None
    pss = rawread(os.path.join(OUT, "pn.pss.raw")).get()
    a, fp = fundamental_amplitude(pss["time"], np.real(pss["tp"]) - np.real(pss["tn"]))
    pn = rawread(os.path.join(OUT, "pn.raw")).get()
    off = np.real(pn["frequency"])
    l = 10 * np.log10(np.real(pn["onoise"]) / (a * a / 2))
    return dict(f=fp, amp=a, L={float(o): float(x) for o, x in zip(off, l)})


def bias_noise_compare():
    """Tail-node voltage noise of the simple D9 bias (mt/rbf/cbf) [SCH].

    Sense Rs=10 Ω from drain to a quiet 0.3 V supply; Sid ≈ Svn / Rs².
    """
    print("## Tail-current noise: ideal/MIM-like vs moscap [SCH]\n")
    RS = 10.0
    results = {}
    for kind in ("ideal", "mos"):
        cbf = ("cbf (nbf 0) capacitor c=50p\n" if kind == "ideal"
               else mos_instances())
        mos_inc = ""
        if kind == "mos":
            mos_inc = 'include "cornerMOSCAP.lib" section=moscap_tt\n'
        text = f"""D9 bias noise {kind}

ground 0
include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section=mos_tt
{mos_inc}load "resistor.osdi"
load "capacitor.osdi"
model resistor resistor
model capacitor capacitor
model vsource vsource
model isource isource
vdd (vdd 0) vsource dc=1.2
iref (vdd nb) isource dc=0.5m
mr (nb nb 0 0) sg13_lv_nmos w=20u l=4u ng=4
rbf (nb nbf) resistor r=1M noisy=1
{cbf}mt (tail nbf 0 0) sg13_lv_nmos w=160u l=4u ng=32
rs (tail sense) resistor r={RS:g} noisy=0
vs (sense 0) vsource dc=0.3
iin (0 sense) isource dc=0
control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(tail) v(nbf)
  analysis op1 op
  analysis n1 noise in="iin" out=["tail"] values=[1e5, 3e5, 1e6]
endc
"""
        name = f"bias_n_{kind}"
        try:
            run_vacask(name, text)
            d = rawread(os.path.join(OUT, "n1.raw")).get()
            f = np.real(np.asarray(d["frequency"]).ravel())
            y = np.real(np.asarray(d["onoise"]).ravel())  # V²/Hz
            sid = y / (RS * RS)  # A²/Hz
            results[kind] = (f, sid)
            print(f"{kind}: points={len(f)}")
        except Exception as e:
            print(f"  bias noise {kind} failed: {e}")
            results[kind] = None
    if results.get("ideal") and results.get("mos"):
        f0, y0 = results["ideal"]
        f1, y1 = results["mos"]
        print("\n| f | Sid ideal (A²/Hz) | Sid mos (A²/Hz) | Δ (dB) |")
        print("|---|---|---|---|")
        for f in OFFS:
            i0 = int(np.argmin(np.abs(f0 - f)))
            i1 = int(np.argmin(np.abs(f1 - f)))
            s0, s1 = max(y0[i0], 1e-40), max(y1[i1], 1e-40)
            print(f"| {f/1e3:.0f} kHz | {s0:.3e} | {s1:.3e} | "
                  f"{10*np.log10(s1/s0):+.3f} |")
    return results


def main():
    print("# P2.7.2b D9 — MOS vs MIM for cbf=50 pF\n")
    print(f"MIM density 1.5 fF/µm² → 50 pF plate 0.0333 mm², rfcmim bbox "
          f"0.03757 mm² [PDK/TOOL] — island would be ~0.316 mm² > 0.30.\n")
    print(f"Proposal: thin-ox moscap_n, {MOS_M}×{MOS_W:g}/{MOS_L:g} µm, "
          f"C≈{C_MOS*1e12:.1f} pF, place ≈0.0053 mm² [HAND/PDK].\n")

    cv_and_leak()
    bias_noise_compare()

    print("\n## VCO pnoise contribution [SCH]\n")
    print("tt mid-band ≈ 3.65 GHz, bank bypass omitted (known PSS issue), "
          f"pass |ΔL| < {PASS_DB} dB at 100 kHz and 1 MHz.\n")
    S3.load_sizing()
    code, vt, f0, itail, temp = 91, S2.VTUNE_MID, 3.65e9, 4.0e-3, 27.0
    Ls = {}
    for kind in ("ideal", "mos"):
        print(f"  running pnoise kind={kind} …", flush=True)
        r = pnoise_kind(kind, code, vt, f0, itail, temp)
        Ls[kind] = r
        if r:
            print(f"  {kind}: f={r['f']/1e9:.3f} GHz amp={r['amp']:.3f} "
                  + " ".join(f"L({o/1e3:.0f}k)={r['L'][o]:.2f}" for o in OFFS),
                  flush=True)
        else:
            print(f"  {kind}: FAILED", flush=True)

    print("\n| Offset | L ideal/MIM-like | L moscap | Δ |")
    print("|---|---|---|---|")
    ok = True
    if Ls.get("ideal") and Ls.get("mos"):
        for o in OFFS:
            a, b = Ls["ideal"]["L"][o], Ls["mos"]["L"][o]
            d = b - a
            print(f"| {o/1e3:.0f} kHz | {a:.2f} | {b:.2f} | {d:+.3f} dB |")
            if abs(d) >= PASS_DB:
                ok = False
        print(f"\nPass (|ΔL| < {PASS_DB} dB): {'PASS' if ok else 'FAIL'}\n")
    else:
        ok = False
        print("\nPass: FAIL (pnoise did not complete)\n")

    open(os.path.join(OUT, "d9_mos_pass.flag"), "w").write(
        "PASS\n" if ok else "FAIL\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
