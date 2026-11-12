#!/usr/bin/env python3
"""P2.7.2 gate: pump linearity at D20 landing extremes on VR_ANA1 pad supplies [SCH]+[MODEL].

Step-4 lin check (Q(dt) at 1–5 ns, offset on, real bias generator, I_cp = 100 µA) at:
  ss 1.108 V / 85 °C: 0.244, mid, 0.897 V
  tt 1.200 V / 27 °C: 0.361, mid, 0.936 V
  ff 1.295 V / −40 °C: 0.457, mid, 0.970 V

Pass: INL ≤ 30 ps; |ΔI_cp| ≤ 10 % vs mid-window slope; lock point on UP side (> 0);
boundary spur ≤ −105 dBc at RF (pll_behav, D19 loop).

    python3 -u run_p272_lin.py 2>&1 | tee out/summary_p272_lin.txt
    # use pipefail so the exit code is the script's, not tee's
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

# Load step4 helpers (biasgen / use_bias) and pll step2 as they do
import importlib.util

spec4 = importlib.util.spec_from_file_location("pll_step4_lin", os.path.join(HERE, "run_step4.py"))
S4 = importlib.util.module_from_spec(spec4)
# Avoid running main: exec module but step4 only runs main under __main__
spec4.loader.exec_module(S4)
S2 = S4.S2
S2.OUT = OUT
S4.OUT = OUT

sys.path.insert(0, os.path.join(REPO, "analog", "pll", "step3"))
import pll_behav as B  # noqa: E402

DTS = [1e-9, 2e-9, 3e-9, 4e-9, 5e-9]
ICP = S2.ICP  # 100 µA default

# (label, mos, vdd, temp, vt_lo, vt_mid, vt_hi) — landing extremes + hold mid
CASES = [
    ("ss", "mos_ss", 1.108, 85, 0.244, 0.524, 0.897),
    ("tt", "mos_tt", 1.200, 27, 0.361, 0.577, 0.936),
    ("ff", "mos_ff", 1.295, -40, 0.457, 0.636, 0.970),
]

INL_LIM = 30e-12       # 30 ps
DICP_LIM = 0.10        # 10 %
SPUR_LIM = -105.0      # dBc at RF


def measure(cname, mos, vdd, temp, vt):
    corner = (cname, mos, vdd, temp)
    qs, st_last = [], None
    for dt in DTS:
        name = f"p272lin_{cname}_{vt:.3f}_{dt*1e9:.0f}"
        q, _, _, _, st = S2.run(
            name, corner, vt, dt, ICP, ioff=True,
            post=lambda x: S4.use_bias(x + S4.biasgen()),
        )
        qs.append(q / ICP)
        st_last = st
    da, qa = np.array(DTS), np.array(qs)
    k, c = np.polyfit(da, qa, 1)
    inl = float(np.max(np.abs(qa - (k * da + c))))
    lock = float(-c / k)
    return dict(
        cname=cname, vdd=vdd, temp=temp, vt=vt,
        dts=DTS, qs=[float(x) for x in qs],
        slope=float(k), lock=lock, inl=inl,
        ioff=float(st_last["ioff"]), ivdd=float(st_last["ivdd"]),
        nb=list(st_last["nb"]),
    )


def main():
    print("# P2.7.2 — pump linearity at landing extremes (VR_ANA1) [SCH]+[MODEL]\n")
    print("Q(dt) 1–5 ns, offset on, bias generator, I_cp 100 µA. "
          "ΔI_cp = (slope / slope_mid − 1). Spur from pll_behav (D19 60 kHz loop) [MODEL].\n")
    print("Pass: INL ≤ 30 ps; |ΔI_cp| ≤ 10 %; lock > 0 (UP side); spur ≤ −105 dBc at RF.\n")

    print("| Corner | V_DD | T | V_tune | INL (ps) | Lock (ns) | Slope | "
          "ΔI_cp (%) | Spur VHF/UHF (dBc) | PASS |")
    print("|---|---|---|---|---|---|---|---|---|---|")

    results = {}
    ok_all = True
    for cname, mos, vdd, temp, vlo, vmid, vhi in CASES:
        mid = measure(cname, mos, vdd, temp, vmid)
        results[(cname, vmid)] = mid
        for vt, tag in ((vlo, "lo"), (vhi, "hi")):
            r = measure(cname, mos, vdd, temp, vt)
            dicp = r["slope"] / mid["slope"] - 1.0
            inl_f = B.inl_from_curve(r["dts"], np.array(r["qs"]))
            sp_vhf = B.spur("VHF", inl_f)["spur_rf"]
            sp_uhf = B.spur("UHF", inl_f)["spur_rf"]
            lock_ok = r["lock"] > 0.0
            inl_ok = r["inl"] <= INL_LIM
            dicp_ok = abs(dicp) <= DICP_LIM
            spur_ok = (sp_vhf <= SPUR_LIM) and (sp_uhf <= SPUR_LIM)
            ok = inl_ok and dicp_ok and lock_ok and spur_ok
            ok_all = ok_all and ok
            flag = "PASS" if ok else "FAIL"
            reasons = []
            if not inl_ok:
                reasons.append(f"INL {r['inl']*1e12:.1f}>30")
            if not dicp_ok:
                reasons.append(f"|ΔI| {abs(dicp)*100:.1f}%>10")
            if not lock_ok:
                reasons.append(f"lock {r['lock']*1e9:.2f}ns not UP")
            if not spur_ok:
                reasons.append(f"spur {sp_vhf:.1f}/{sp_uhf:.1f}")
            note = (" " + ";".join(reasons)) if reasons else ""
            print(f"| {cname} | {vdd:.3f} | {temp} | {vt:.3f} | {r['inl']*1e12:.1f} | "
                  f"{r['lock']*1e9:.2f} | {r['slope']:.3f} | {dicp*100:+.1f} | "
                  f"{sp_vhf:.1f}/{sp_uhf:.1f} | {flag}{note} |", flush=True)
            r.update(dict(dicp=dicp, spur_vhf=sp_vhf, spur_uhf=sp_uhf, ok=ok,
                          mid_slope=mid["slope"]))
            results[(cname, vt)] = r
        # also print mid row for reference
        inl_f = B.inl_from_curve(mid["dts"], np.array(mid["qs"]))
        sp_vhf = B.spur("VHF", inl_f)["spur_rf"]
        sp_uhf = B.spur("UHF", inl_f)["spur_rf"]
        print(f"| {cname} | {vdd:.3f} | {temp} | {vmid:.3f} mid | {mid['inl']*1e12:.1f} | "
              f"{mid['lock']*1e9:.2f} | {mid['slope']:.3f} | +0.0 | "
              f"{sp_vhf:.1f}/{sp_uhf:.1f} | ref |", flush=True)
        mid.update(dict(dicp=0.0, spur_vhf=sp_vhf, spur_uhf=sp_uhf, ok=True))

    print("\n## Verdict\n")
    if ok_all:
        print("PASS — all landing extremes meet INL / ΔI_cp / UP lock / spur ≤ −105 dBc. "
              "VCO layout may proceed.\n")
    else:
        print("FAIL — finding; no layout.\n")
        for (cn, vt), r in results.items():
            if vt in (0.524, 0.577, 0.636):
                continue
            if not r.get("ok", True):
                print(f"- {cn} @ {vt:.3f} V: INL={r['inl']*1e12:.1f} ps, "
                      f"ΔI_cp={r['dicp']*100:+.1f} %, lock={r['lock']*1e9:.2f} ns, "
                      f"spur={r['spur_vhf']:.1f}/{r['spur_uhf']:.1f} dBc")

    def jsafe(x):
        if isinstance(x, (float, np.floating)):
            return float(x)
        if isinstance(x, (list, tuple)):
            return [jsafe(y) for y in x]
        return x

    out = {f"{k[0]}_{k[1]:.3f}": {kk: jsafe(vv) for kk, vv in v.items()
                                   if kk not in ("dts",)}
           for k, v in results.items()}
    json.dump(dict(pass_=ok_all, cases=out), open(os.path.join(OUT, "p272_lin.json"), "w"), indent=1)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
