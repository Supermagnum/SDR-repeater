#!/usr/bin/env python3
"""P2.6 step 3: transistor-level closed loop - interface check (spec/pll-topology.md §13).

Run inside the container from this folder (needs ../../../vco/step2/out/range.json from the 8-bit VCO run):

    mkdir -p out
    python3 -u run_p26s3.py tstop=2u | tee out/summary_2u.txt    # start-up trial
    python3 -u run_p26s3.py | tee out/summary.txt                # 8 us, locks (a few h)
    options: s=<bandwidth scale, default 10>  icp=<uA, default 100>  code=<VCO band, default: from range.json>

Everything at transistor level except the 36 MHz reference (ideal square) and the supplies:
  VCO       P2.3 / D20 circuit (8-bit trimmed bank, AC-coupled varactor, 4 mA), its stand-in buffer removed
  LO        P2.4 step-3 buffer (AC-coupled, self-biased) -> CML ÷3 enabled after 500 ns (D15) -> CML-to-CMOS
            converter (AC-coupled)
  divider   five TSPC toggle flip-flops in a ripple chain, ÷32, instead of the MMD (integer-N: the MMD and the
            Sigma-Delta are RTL, P2.5 steps 2b / 2c). VCO = 3 x 32 x 36 MHz = 3.456 GHz (VHF arrangement, P = 3)
  PFD, CP   step 2a / step 4: static PFD with power-on reset, charge pump with replica loop, dummy buffer, offset
            pair, bias generator and I_cp DAC (code 3, 100 uA)
  filter    the D19 loop filter scaled to s x the bandwidth for a short simulation: C / s^2, R x s (same phase
            margin; s = 10: 600 kHz, C1 0.31 pF, C2 4.65 pF, R1 229 kOhm, R3 1.08 MOhm, C3 31 fF - the varactor's
            own well capacitance adds to C3, so the phase margin is a little lower than designed)
Start from all-zero (power-on step): V_tune 0 V, VCO starts on its kick, divider enabled at 50 ns, PFD after its
power-on reset. Checks: does the loop pull in and lock (divider period = reference period), with the right
polarity, where V_tune settles, the locked UP / DN pulse widths (D18: UP about 2.8 ns, DN only the reset),
VCO amplitude and frequency. Results are [SCH].
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(HERE, "out")
ARGS = sys.argv[1:]
opt = lambda k, d: next((float(a[len(k) + 1:].rstrip("u")) for a in ARGS if a.startswith(k + "=")), d)   # noqa: E731

os.environ.setdefault("PDK_ROOT", "/foss/pdks")
os.environ.setdefault("PDK", "ihp-sg13g2")
sys.path.append("/foss/tools/vacask/lib/vacask/python")


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


F_REF = 36e6
P, NDIV = 3, 32
F_VCO = P * NDIV * F_REF
S = opt("s", 10.0)
ICP = opt("icp", 100.0) * 1e-6
TSTOP = opt("tstop", 8.0) * 1e-6
sys.path.insert(0, os.path.join(REPO, "analog", "pll", "p26"))
import wake_timing as W  # noqa: E402
T_BYPASS = W.T_BYPASS          # afe_seq BYPASS_CYCLES (0.50 µs @ 36 MHz, ≥ 0.4 µs)
T_EN = W.T_LODIV               # D15: en_lodiv after LODIV_DELAY_CYCLES (1.0 µs @ 36 MHz)
VDD = 1.2
LF = dict(C1=30.8e-12, C2=465.2e-12, R1=22.9e3, R3=107.8e3, C3=3.08e-12)   # D19


def vco_body(V, code):
    """P2.3 VCO body: tuning → n3, no stand-in buffer; MOS bias bypass driven like afe_seq."""
    path = V.netlist("p26s3_vco", code, 0.6, itail=4e-3, analysis="", drive_vbp=True)
    text = open(path).read()
    hdr = V.HEADER.format(title="P2.3 step 2 VCO: p26s3_vco")
    body = text[len(hdr):text.index("\ncontrol")]
    keep = []
    for ln in body.splitlines():
        tok = ln.split(" ")[0] if ln else ""
        if tok in ("vdd", "vtune", "mb1", "mb2", "rl1", "rl2", "ib", "ctb", "cl1", "cl2"):
            continue                      # supply defined once; tuning from the loop filter; stand-in buffer
        ln = re.sub(r"\bvt\b", "n3", ln)
        ln = re.sub(r"\bnbf\b", "vco_nbf", ln)
        ln = re.sub(r"\bnb\b", "vco_nb", ln)
        ln = re.sub(r"^iref ", "irefvco ", ln)
        ln = re.sub(r"\btail\b", "vco_tail", ln)
        keep.append(ln)
    # vbp follows afe_seq: high for T_BYPASS then low. Second kick after bypass opens (loads the tank while on).
    # Earlier hand model used behavioural tsw at 200 ns (4 τ); that left ~2 % tail residue — T_BYPASS is ≥ 6–7 τ.
    tb, tk = T_BYPASS, T_BYPASS + 20e-9
    keep += [
        # high for T_BYPASS then low — same window as afe_seq en_vco_bias_bp
        f'vbp (vbp 0) vsource type="pulse" val0=0 val1={VDD} delay=0 rise=50p fall=50p width={tb:.6e}',
        f'ik2 (0 tn) isource type="pulse" val0=0 val1=1m delay={tk:.6e} rise=50p fall=50p width=200p',
    ]
    return "\n".join(keep) + "\n"


def header(V):
    """VCO header (MOS lv/hv, MIM corners, inductor) plus the PLL Verilog-A clock source."""
    s2 = load("pll_step2_h", "analog/pll/step2/run_step2.py")
    emb = s2.HEADER[s2.HEADER.index("embed"):]
    return V.HEADER.format(title="P2.6 step 3: transistor-level closed loop") + "\n" + emb


def lo_and_divider(L1, L2):
    i_, rl, w = L1.cml_params(0.5e-3, VDD)
    body, out = L1.div_body(P, i_, rl, w, VDD)
    body = L1.enable_at(body.replace("(vdd ", "(vdv "), T_EN)
    s = L2.buffer() + body + L2.converter(out[0], out[1], "x_clk")
    clk = "x_clk"
    for k in range(1, 6):                 # ripple ÷32: inverting TSPC toggle + inverter per stage
        s += L2.tspc(f"rc{k}", f"x_rc{k}", clk, f"x_rc{k}") + L2.inv(f"rc{k}i", f"x_rc{k}", f"x_rcb{k}")
        clk = f"x_rcb{k}"
    s = re.sub(r"\bvref\b", "vrefcml", s)      # the CML ÷3 has its own vref; the bias generator's is 0.4 V
    return s + f"cdiv ({clk} 0) capacitor c=5f\nrdivb ({clk} div0) resistor r=1\n"


def pick_code():
    rj = os.path.join(REPO, "analog", "vco", "step2", "out", "range.json")
    r = json.load(open(rj))
    meas = {tuple(float(x) for x in k.split(",")): v["f"] for k, v in r["meas"].items()}
    pts = sorted((c, f) for (c, vt), f in meas.items() if abs(vt - 0.65) < 1e-6)
    cs, fs = zip(*pts)
    y = np.interp(1 / F_VCO ** 2, [1 / f ** 2 for f in fs], cs)     # 1/f^2 is linear in code
    return int(round(y)), r


def main():
    os.makedirs(OUT, exist_ok=True)
    V = load("vco_step2", "analog/vco/step2/run_step2.py")
    V.OUT = OUT
    code, r = pick_code()
    # Without the stand-in buffer, the free-run was ~0.45 % high → code+2 (earlier p26s3). With MOS bypass
    # devices on the bank/varactor nodes the tank is a little heavier; default stays at the interpolated code.
    code = int(opt("code", code))
    V.LSB_FF, V.C_FIX_FF, V.NFING = r["lsb"], r["cfix"], r["nfing"]
    V.NBITS = r.get("nbits", 8)
    V.CMAX = (1 << V.NBITS) - 1
    V.TRIM[:len(r.get("trim", []))] = r.get("trim", [])
    L3 = load("lo_step3", "analog/lo/step3/run_step3.py")       # applies the final P2.4 options to L1 / L2
    L1, L2 = L3.L1, L3.L2
    S4 = load("pll_step4", "analog/pll/step4/run_step4.py")
    S2 = S4.S2
    lf = dict(C1=LF["C1"] / S ** 2, C2=LF["C2"] / S ** 2, C3=LF["C3"] / S ** 2, R1=LF["R1"] * S, R3=LF["R3"] * S)
    print("# P2.6 step 3 — transistor-level closed loop\n")
    print(f"VCO {F_VCO/1e9:.3f} GHz = {P} x {NDIV} x {F_REF/1e6:.0f} MHz, band code {code}; I_cp {ICP*1e6:.0f} µA; "
          f"loop filter D19 scaled {S:g} x (C1 {lf['C1']*1e12:.3f} pF, C2 {lf['C2']*1e12:.2f} pF, R1 {lf['R1']/1e3:.0f} kΩ, "
          f"R3 {lf['R3']/1e3:.0f} kΩ, C3 {lf['C3']*1e15:.0f} fF); {TSTOP*1e6:g} µs from power-on.\n")
    print(f"Bias bypass (afe_seq): closed {T_BYPASS*1e6:.2f} µs ({W.BYPASS_CYCLES} cycles @ 36 MHz); "
          f"en_lodiv at {T_EN*1e6:.2f} µs ({W.LODIV_DELAY_CYCLES} cycles). "
          f"Wake budget 150 µs: bypass is {T_BYPASS*1e6:.2f} µs of the 83–120 µs model wake.\n")
    pump = S4.use_bias(S2.pfd(VDD) + S2.charge_pump(ICP) + S2.offset_sink(ICP) + S4.biasgen())
    body = (f"vdd (vdd 0) vsource dc={VDD}\nvbufs (vbuf 0) vsource dc={VDD}\nvdvs (vdv 0) vsource dc={VDD}\n"
            f"vcvs (vcv 0) vsource dc={VDD}\nvdgs (vdg 0) vsource dc={VDD}\n"
            f"model ota ota a=100 vh={VDD} rout=1e7\n"
            f"model sqref sqclk f={F_REF:.6e} td=2e-9 vh={VDD}\nxref (ref0) sqref\n"
            + vco_body(V, code) + lo_and_divider(L1, L2) + pump
            + f"c1 (vt 0) capacitor c={lf['C1']:.4e}\nr1 (vt n2) resistor r={lf['R1']:.1f}\n"
              f"c2 (n2 0) capacitor c={lf['C2']:.4e}\nr3 (vt n3) resistor r={lf['R3']:.1f}\n"
              f"c3 (n3 0) capacitor c={lf['C3']:.4e}\n")
    # duplicate instance names would silently merge two devices
    names = [ln.split(" ")[0] for ln in body.splitlines() if ln and not ln.startswith(("model", "include", "load", "//"))]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        sys.exit(f"duplicate instance names: {dup[:20]}")
    name = "p26s3"
    with open(os.path.join(OUT, name + ".sim"), "w") as fh:
        fh.write(header(V) + body)
        fh.write("\ncontrol\n  abort always\n  options rawfile=\"binary\" strictsave=1\n"
                 "  save v(vt) v(n3) v(div0) v(ref0) v(up) v(dn) v(tp) v(tn) v(pbias) v(vbp) v(vco_nbf) v(vco_nb)\n"
                 f'  analysis tr tran stop={TSTOP:.4e} step=5p maxstep=5p icmode="uic"\nendc\n')
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        rr = subprocess.run(["vacask", name + ".sim"], cwd=OUT, stdout=fh, stderr=subprocess.STDOUT)
    if rr.returncode:
        sys.exit("vacask failed; end of out/p26s3.log:\n" + open(log).read()[-1200:])
    from vacask.rawfile import rawread
    d = rawread(os.path.join(OUT, "tr.raw")).get()
    t = np.real(d["time"])
    g = lambda k: np.real(d[k])   # noqa: E731

    def rises(v, th):
        i = np.where((v[:-1] < th) & (v[1:] >= th))[0]
        return t[i] + (th - v[i]) * (t[i + 1] - t[i]) / (v[i + 1] - v[i])
    td = rises(g("div0"), VDD / 2)
    tr_ = rises(g("ref0"), VDD / 2)
    print("## Course of the loop\n")
    print("| t (µs) | Pump output vt (V) | V_tune at the VCO (V) | Divider period / reference period − 1 (ppm) | "
          "VCO from the divider (GHz) | VCO amplitude (V diff.) |")
    print("|---|---|---|---|---|---|")
    vdiff = g("tp") - g("tn")
    for x in np.linspace(0.25e-6, TSTOP, 12):
        m = (td > x - 0.25e-6) & (td <= x)
        per = np.mean(np.diff(td[m])) if m.sum() > 2 else float("nan")
        mw = (t > x - 20e-9) & (t <= x)
        a = (vdiff[mw].max() - vdiff[mw].min()) / 2 if mw.sum() > 2 else float("nan")
        print(f"| {x*1e6:.2f} | {np.interp(x, t, g('vt')):.4f} | {np.interp(x, t, g('n3')):.4f} | {(per * F_REF - 1)*1e6:+.0f} | "
              f"{P*NDIV/per/1e9:.4f} | {a:.3f} |")
    last = td[td > TSTOP - 1e-6]
    per = np.mean(np.diff(last)) if len(last) > 3 else float("nan")
    # locked pulse widths over the last 20 reference cycles
    m = t >= TSTOP - 20 / F_REF
    tu = np.linspace(t[m][0], t[m][-1], 400000)
    wu = np.mean(np.interp(tu, t[m], g("up")[m]) > VDD / 2) / F_REF
    wd = np.mean(np.interp(tu, t[m], g("dn")[m]) > VDD / 2) / F_REF
    lead = np.mean([x - tr_[np.searchsorted(tr_, x) - 1] for x in td[td > TSTOP - 20 / F_REF] if np.searchsorted(tr_, x) > 0])
    vd = g("tp") - g("tn")
    amp = (vd[m].max() - vd[m].min()) / 2
    locked = abs(per * F_REF - 1) < 1e-4
    print(f"\nLast µs: divider period {per*1e9:.4f} ns (reference {1e9/F_REF:.4f} ns, {(per*F_REF-1)*1e6:+.1f} ppm) → "
          f"{'**locked**' if locked else '**not locked**'}; VCO {P*NDIV/per/1e9:.5f} GHz (target {F_VCO/1e9:.3f}); "
          f"pump output {np.mean(g('vt')[m]):.4f} V, V_tune at the VCO {np.mean(g('n3')[m]):.4f} V; UP {wu*1e9:.2f} ns, DN {wd*1e9:.2f} ns per cycle (D18: UP ≈ 2.8 + 0.25 ns, "
          f"DN ≈ 0.25 ns); divider edge {lead*1e9:.2f} ns after the reference edge; VCO amplitude {amp:.3f} V "
          f"differential; bias node pbias {np.mean(g('pbias')[m]):.3f} V.\n")
    try:
        nbf = g("vco_nbf")
        nb = g("vco_nb")
        nbf_open = float(np.interp(T_BYPASS, t, nbf))
        nb_open = float(np.interp(T_BYPASS, t, nb))
        nbf_end = float(np.mean(nbf[m]))
        res = (1 - nbf_open / nb_open) * 100 if nb_open else float("nan")
        print("## Bias bypass (sequencer timing)\n")
        print(f"vbp high until {T_BYPASS*1e6:.2f} µs; at open: vco_nbf = {nbf_open:.3f} V, vco_nb = {nb_open:.3f} V "
              f"(residue vs mirror {res:.1f} %; target ≤ ~0.1 % for ≥ 6–7 τ); "
              f"vco_nbf at end of run = {nbf_end:.3f} V.\n")
    except (KeyError, TypeError):
        pass


if __name__ == "__main__":
    main()
