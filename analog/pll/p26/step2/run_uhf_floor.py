#!/usr/bin/env python3
"""P2.6 open point 3 — one UHF LO-floor method attempt (2026-10-31).

Method (distinct from the failed full-chain noisy transient):
  UHF path truncated after the CML-to-CMOS converter — buffer + CML ÷2 + AC converter
  only; no Johnson ÷4 / retiming TSPC at 1.92 GHz (that was the stiff part). Ideal tank
  sine at 3.84 GHz → measure TIE on x_clk at 1.92 GHz with the same warm-up + ZOH
  transient-noise flow that works for VHF. Refer to the 480 MHz LO by −12.04 dB (ideal ÷4).

    python3 -u run_uhf_floor.py | tee out/summary_uhf_floor.txt

One try: if NR / timestep fails at 50 / 20 / 10 / 5 GHz noise BW, record a known gap and stop.
Target ≤ −150 dBc/Hz at the LO. Results [SCH] if it converges.
"""
import importlib.util
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, HERE)
import run_p26s2 as s2  # noqa: E402

L3 = s2.load("lo_step3", "analog/lo/step3/run_step3.py")
L3.OUT = OUT
L2 = L3.L2
L1 = L3.L1

F_VCO = 3.84e9
F_CLK = F_VCO / 2          # after ÷2
F_LO = F_VCO / 8           # after ideal Johnson ÷4
AMP = 0.62                 # tt typical swing per side at 3.84 GHz
CORNER = ("tt", "mos_tt", 1.20, 27)
TSTOP = 1e-6
TARGET = -150.0


def build_div2_only():
    """Buffer + CML ÷2 + converter; stop at x_clk (1.92 GHz)."""
    ctag, mos, vdd, temp = CORNER
    i_, rl, w = L1.cml_params(L3.I_LATCH, vdd)
    body, out = L1.div_body(2, i_, rl, w, vdd)
    body = body.replace("(vdd ", "(vdv ")
    if L2.EN_NS is not None:
        body = L1.enable_at(body, L2.EN_NS * 1e-9)
    # L3 has already swapped L2.converter to the AC version when ACCONV is default
    lo = body + L2.converter(out[0], out[1], "x_clk")
    lo += "cclk (x_clk 0) capacitor c=20f\n"
    sup = f'type="pulse" val0=0 val1={vdd} delay=0.2n rise=1n fall=1n width=1'
    text = L1.HEADER.format(
        title="P2.6 open point 3: UHF div2+converter floor", mos=mos, vcm=1.1,
        amp=AMP, shape=0.0, f=F_VCO, offs=0.0, t0=-1.0, tr=1e-12,
    )
    text += (f"vdd (vdd 0) vsource {sup}\nvbufs (vbuf 0) vsource {sup}\n"
             f"vdvs (vdv 0) vsource {sup}\nvcvs (vcv 0) vsource {sup}\n"
             f"vdgs (vdg 0) vsource {sup}\nxtank (tp tn) clk\n"
             + L2.buffer() + lo)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "uhf_floor_div2.sim")
    with open(path, "w") as fh:
        fh.write(text + "\ncontrol\n  abort always\n  options rawfile=\"binary\"\n"
                 f"  options temp={temp}\n"
                 f"  analysis tr tran stop=10n step=5p maxstep=5p\nendc\n")
    return path


def run_noise(template, noisy):
    """template = deck with a single placeholder 'analysis tr tran stop=... step=5p maxstep=5p'."""
    node = "x_clk"
    text = template
    text = re.sub(r'type="pulse" val0=0 val1=(\S+) delay=\S+ rise=\S+ fall=\S+ width=1', r"dc=\1", text)
    if noisy:
        text = re.sub(
            r"(\) resistor r=(\S+))(?=\s|$)(?!\s+noisy)",
            lambda m: m.group(1) + ("" if m.group(2) == "1G" else " noisy=1"),
            text,
        )
    warm = round(60e-9 * F_CLK) / F_CLK
    err = "no attempt"
    path = os.path.join(OUT, "uhf_floor_div2.sim")
    for nf in (["50G", "20G", "10G", "5G"] if noisy else [None]):
        an = (
            f"  options strictsave=1\n"
            f'  analysis warm tran stop={warm:.6e} step=5p maxstep=5p icmode="uic" store="ss"\n'
            f"  save v({node})\n"
            f'  analysis tr tran stop={TSTOP:.4e} step=5p maxstep=5p ic="ss" icmode="uic"'
            + (f' noisemode="zoh" noisefmax={nf} noisefmin=50k oversample=1' if nf else "")
            + "\n"
        )
        body = re.sub(
            r"  analysis tr tran stop=\S+ step=5p maxstep=5p\n",
            an,
            text,
            count=1,
        )
        open(path, "w").write(body)
        try:
            d = L3.run(path)
            return d, nf
        except Exception as e:
            err = str(e)
    raise RuntimeError(err)


def band_avg(fr, L, a, b):
    m = (fr >= a) & (fr <= b)
    return 10 * math.log10(np.mean(10 ** (L[m] / 10)))


def main():
    print("# P2.6 open point 3 — UHF LO floor, one method attempt [SCH]\n")
    print("**Method:** UHF buffer + CML ÷2 + AC converter only (no Johnson / retiming TSPC). "
          f"Ideal tank {F_VCO/1e9:.2f} GHz, measure x_clk at {F_CLK/1e9:.2f} GHz, "
          f"{TSTOP*1e6:g} µs ZOH transient noise (warm-up as VHF). "
          "Refer to 480 MHz LO by −12.04 dB (ideal ÷4). "
          "Target ≤ −150 dBc/Hz at the LO.\n")
    path = build_div2_only()
    template = open(path).read()
    vdd = CORNER[2]
    th = vdd / 2
    try:
        d_n, used = run_noise(template, True)
    except RuntimeError as e:
        print("## Result: no convergence\n")
        print("Noisy transient failed after 50/20/10/5 GHz noise BW tries.\n")
        print(f"Last error (tail):\n```\n{str(e)[-500:]}\n```\n")
        print("## Known gap\n")
        print("UHF LO-chain floor remains the P2.4 hand estimate corrected by the VHF "
              "simulation-to-estimate delta ≈ **−150 dBc/Hz** `[HAND]` "
              "(`spec/pll-topology.md` §13; `out/summary_lo1.txt`). "
              "This truncated-chain method also does not converge. "
              "Open point 3 recorded as a **known gap**; not a P2.7 blocker. **Stopped.**\n")
        return 1

    import shutil
    shutil.copy(os.path.join(OUT, "tr.raw"), os.path.join(OUT, "uhf_floor_noisy.raw"))
    num = float("nan")
    try:
        d_0, _ = run_noise(template, False)
        t0, v0 = np.real(d_0["time"]), np.real(d_0["x_clk"])
        fr0, L0, _ = s2.tie_spectrum(t0, v0, th, F_CLK)
        num = band_avg(fr0, L0, 3e6, 10e6) + (-20 * math.log10(4))
    except Exception as e:
        print(f"(Noiseless numerical-floor run skipped: {str(e)[-120:]})\n")

    t, v = np.real(d_n["time"]), np.real(d_n["x_clk"])
    fr, L, jit = s2.tie_spectrum(t, v, th, F_CLK)
    # refer div2 output to LO (div4 more -> -12.04 dB on L)
    ref = -20 * math.log10(4)
    vals = [band_avg(fr, L, *r) + ref for r in ((1e6, 3e6), (3e6, 10e6), (10e6, 30e6))]
    print("## Result\n")
    print("| Stage | Noise BW | Edges | RMS jitter (fs) | L@LO 1–3 MHz | L@LO 3–10 MHz | "
          "L@LO 10–30 MHz | Numerical 3–10 MHz |")
    print("|---|---|---|---|---|---|---|---|")
    num_s = f"{num:.1f}" if num == num else "n/a"
    print(f"| div2+conv -> LO (−12 dB) | {used}Hz | {len(fr)*2} | {jit*1e15:.0f} | "
          + " | ".join(f"{x:.1f}" for x in vals) + f" | {num_s} |")
    print()
    floor = vals[1]
    if floor <= TARGET:
        print(f"**PASS:** LO-referred floor {floor:.1f} dBc/Hz ≤ {TARGET:.0f}. "
              "Open point 3 closed with this method (Johnson noise not included; "
              "add VHF CMOS floor in quadrature if a tighter budget is needed).\n")
        return 0
    print(f"**Above target:** LO-referred floor {floor:.1f} dBc/Hz > {TARGET:.0f}. "
          "Finding: raises UHF total PN; see owner. **Stopped.**\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
