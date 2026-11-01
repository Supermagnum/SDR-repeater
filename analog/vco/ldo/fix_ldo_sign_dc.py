#!/usr/bin/env python3
"""Open-loop DC sign: break feedback, sweep mid, watch vg and closed-loop vout tendency."""
import math
import os
import subprocess

import numpy as np
from vacask.rawfile import rawread

OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)
VREF = (1.2 + 9.65e-3 * 10) / 2
VIN = 2.7


def run(name, text):
    open(os.path.join(OUT, name + ".sim"), "w").write(text)
    log = os.path.join(OUT, name + ".log")
    with open(log, "w") as fh:
        r = subprocess.run(["vacask", name + ".sim"], cwd=OUT,
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(open(log).read()[-800:])


HDR = """parameters title="sign"
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


def ota(pair="orig"):
    sc = math.sqrt(50e3 / 1.5)
    if pair == "orig":
        # mid on diode side, vref on output side
        p = """m1 (d1 mid t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
"""
    elif pair == "swap_gates":
        p = """m1 (d1 vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg mid t 0) sg13_lv_nmos w=16u l=2u ng=4
"""
    else:  # out_on_diode: take pass gate from d1, diode on right
        p = """m1 (vg mid t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (d1 vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m3x (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4x (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
"""
        # special - return early built
        return f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
vmid (mid 0) vsource dc={VREF}
ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
{p}cc (vg mid) capacitor c=5p
xout (vg 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
"""
    return f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
vmid (mid 0) vsource dc={VREF}
ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
{p}m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
cc (vg mid) capacitor c=5p
xout (vg 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
"""


def sweep_mid(pair):
    print(f"\n## Open-loop OTA '{pair}': mid sweep, vg response")
    print("| mid | vg | d(vg)/d(mid) sign |")
    print("|---|---|---|")
    rows = []
    for dm in (-50e-3, -10e-3, 0, 10e-3, 50e-3):
        mid = VREF + dm
        body = ota(pair).replace(f"vmid (mid 0) vsource dc={VREF}",
                                 f"vmid (mid 0) vsource dc={mid}")
        # fix out_on_diode duplicate mirrors - handle in ota
        if pair == "out_on_diode":
            sc = math.sqrt(50e3 / 1.5)
            body = f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
vmid (mid 0) vsource dc={mid}
ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
m1 (vg mid t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (d1 vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
xout (vg 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
"""
        text = HDR + body + """
control
  abort always
  options temp=27 reltol=1e-6 rawfile="binary" strictsave=1
  save v(vg) v(mid) v(d1)
  analysis op1 op
endc
"""
        tag = f"ol_{pair}_{int(dm*1e3)}"
        try:
            run(tag, text)
            op = rawread(os.path.join(OUT, "op1.raw")).get()
            vg = float(np.real(op["vg"]).ravel()[0])
            rows.append((mid, vg))
            print(f"| {mid:.4f} | {vg:.4f} | |")
        except Exception as e:
            print(f"| {mid:.4f} | FAIL | {str(e)[-50:]} |")
    if len(rows) >= 2:
        # slope around centre
        for i in range(len(rows) - 1):
            if abs(rows[i][0] - VREF) < 1e-6 or abs(rows[i + 1][0] - VREF) < 1e-6:
                continue
        # use ±10 mV
        lo = next(v for m, v in rows if abs(m - (VREF - 0.01)) < 1e-6)
        hi = next(v for m, v in rows if abs(m - (VREF + 0.01)) < 1e-6)
        dvg = hi - lo
        # For PMOS pass NEG-FB: mid↑ should give vg↑ (dvg/dmid > 0)
        need = "NEED vg↑ when mid↑ (dvg>0) for NEG-FB with PMOS pass"
        ok = dvg > 0
        print(f"  Δvg for Δmid=+20mV (from -10 to +10): {dvg*1e3:.1f} mV → "
              f"{'CORRECT for PMOS' if ok else 'INVERTED for PMOS'} ({need})")
        return ok
    return None


def closed_loop(pair, label):
    """Full LDO with given pair topology; OP + hold + soft start."""
    sc = math.sqrt(50e3 / 1.5)
    if pair == "orig":
        p = """m1 (d1 mid t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg vref t 0) sg13_lv_nmos w=16u l=2u ng=4
"""
    elif pair == "swap_gates":
        p = """m1 (d1 vref t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (vg mid t 0) sg13_lv_nmos w=16u l=2u ng=4
"""
    else:
        p = """m1 (vg mid t 0) sg13_lv_nmos w=16u l=2u ng=4
m2 (d1 vref t 0) sg13_lv_nmos w=16u l=2u ng=4
"""
    body = f"""
vref (vref 0) vsource dc={VREF}
vin (vin 0) vsource dc={VIN}
mp (vout vg vin vin) sg13_lv_pmos w=400u l=0.13u ng=80
rf1 (vout mid) resistor r=200k
rf2 (mid 0) resistor r=200k
ib (vin nb) isource dc=40u
mb (nb nb 0 0) sg13_lv_nmos w=4u l=2u ng=2
mt (t nb 0 0) sg13_lv_nmos w=8u l=2u ng=2
{p}m3 (d1 d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
m4 (vg d1 vin vin) sg13_lv_pmos w=32u l=2u ng=4
cc (vg mid) capacitor c=5p
xout (vout 0 0) cap_rfcmim w={sc:.3f}u l={sc:.3f}u
il (vout 0) isource dc=5m
"""
    text = HDR + body + """
control
  abort always
  options temp=27 reltol=1e-4 rawfile="binary" strictsave=1
  save v(vout) v(vg)
  analysis op1 op store="opx"
  analysis tr1 tran stop=5u step=1n nodeset="opx"
endc
"""
    run(f"cl_{label}", text)
    op = rawread(os.path.join(OUT, "op1.raw")).get()
    tr = rawread(os.path.join(OUT, "tr1.raw")).get()
    vo = np.real(tr["vout"]).ravel()
    opv = float(np.real(op["vout"]).ravel()[0])
    hold = abs(vo[-1] - vo[0]) < 10e-3
    print(f"  closed-loop {label}: OP={opv:.3f} hold={hold} "
          f"t1={vo[-1]:.3f} drift={(vo[-1]-vo[0])*1e3:.1f}mV")
    return hold, opv


def main():
    print(f"VREF={VREF:.4f} VIN={VIN}")
    for pair in ("orig", "swap_gates", "out_on_diode"):
        ok = sweep_mid(pair)
        closed_loop(pair, pair)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
