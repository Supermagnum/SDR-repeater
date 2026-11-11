#!/usr/bin/env python3
"""V_DS-match servo with correct current sense (no short of xref to vdd) [SCH]."""
import os
import numpy as np
from vacask.rawfile import rawread
import amp_common as A
import run_step2 as S2

A.load_sizing()
OUT = os.path.join(A.HERE, "out", "dbgscale")
os.makedirs(OUT, exist_ok=True)
S2.OUT = OUT
A.set_corner("mos_tt", "cap_typ")

WR, NR = "60u", 12
WT, NT = "480u", 96


def op(body, tag, saves):
    path = os.path.join(OUT, f"{tag}.sim")
    save = " ".join(saves)
    open(path, "w").write(
        S2.HEADER.format(title=tag) + body
        + "\ncontrol\n  abort always\n  options rawfile=\"binary\" temp=27\n"
        + f"  save {save}\n  analysis op1 op\nendc\n"
    )
    try:
        S2.run(path)
    except Exception as e:
        print(f"\n== {tag} FAIL == {[x for x in str(e).splitlines() if x.strip()][-1][:140]}")
        return None
    d = rawread(os.path.join(OUT, "op1.raw")).get()
    print(f"\n== {tag} ==")
    vals = {n: float(np.real(d[n]).ravel()[0]) for n in d.names}
    for n, v in vals.items():
        print(f"  {n}: {v}")
    it = abs(vals.get("vt:flow(br)", vals.get("vs:flow(br)", 0)))
    ir = abs(vals.get("vsense:flow(br)", 0))
    print(f"  >> I_tail={it*1e3:.3f} mA  I_ref={ir*1e6:.1f} uA  ratio={it/ir if ir>1e-9 else float('nan'):.3f}")
    return vals


def discrete_dac(code):
    """DAC dumps into xraw; caller senses into xref."""
    bits = [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16)]
    n = [
        f"// discrete DAC code={code}\n",
        "imaster (pbias 0) isource dc=10u\n",
        "mm0 (pbias pbias vdd vdd) sg13_lv_pmos w=2u l=2u ng=1\n",
    ]
    for i in range(19):
        n.append(f"moff{i} (xoff pbias vdd vdd) sg13_lv_pmos w=2u l=2u ng=1\n")
    n.append("msoff (xraw 0 xoff vdd) sg13_lv_pmos w=38u l=0.13u ng=1\n")
    for b, m in bits:
        on = (int(code) >> b) & 1
        gsw = "0" if on else "vdd"
        for i in range(m):
            n.append(f"mdb{b}_{i} (xd{b}_{i} pbias vdd vdd) sg13_lv_pmos w=2u l=2u ng=1\n")
            n.append(
                f"msw{b}_{i} (xraw {gsw} xd{b}_{i} vdd) sg13_lv_pmos w=2u l=0.13u ng=1\n"
            )
    return "".join(n)


def servo_beh(vtail=0.47):
    return (
        f"vt (tail 0) vsource dc={vtail}\n"
        "vsense (xraw xref) vsource dc=0\n"
        f"mr (xref nbf 0 0) sg13_lv_nmos w={WR} l=4u ng={NR}\n"
        f"mt (tail nbf 0 0) sg13_lv_nmos w={WT} l=4u ng={NT}\n"
        # Positive: xref>tail → current into nbf from gnd side negative = pull up
        # i(p→n): use i=-gm*(v(xref)-v(tail)) so positive error sources into nbf from 0
        # Actually (nbf 0) i=expr means current p→n = expr. To raise nbf, need current into nbf
        # from outside, i.e. negative i (current flowing n→p into nbf).
        "berra (nbf 0) i=-4e-4*(v(xref)-v(tail))\n"
        "rl (nbf 0) resistor r=50k\n"
        "cl (nbf 0) capacitor c=5p\n"
        "rpu (vdd nbf) resistor r=200k\n"
    )


def servo_mos(vtail=0.47):
    return (
        f"vt (tail 0) vsource dc={vtail}\n"
        "vsense (xraw xref) vsource dc=0\n"
        f"mr (xref nbf 0 0) sg13_lv_nmos w={WR} l=4u ng={NR}\n"
        f"mt (tail nbf 0 0) sg13_lv_nmos w={WT} l=4u ng={NT}\n"
        "mo1 (d1 xref ss 0) sg13_lv_nmos w=8u l=2u ng=2\n"
        "mo2 (d2 tail ss 0) sg13_lv_nmos w=8u l=2u ng=2\n"
        "iss (ss 0) isource dc=20u\n"
        "mp1 (d1 d1 vdd vdd) sg13_lv_pmos w=4u l=2u ng=2\n"
        "mp2 (d2 d1 vdd vdd) sg13_lv_pmos w=4u l=2u ng=2\n"
        "rout (d2 nbf) resistor r=1\n"
        "cl (nbf 0) capacitor c=10p\n"
        "rpd (nbf 0) resistor r=200k\n"
    )


print("=== ideal 500u + beh servo ===")
op(
    "vdd (vdd 0) vsource dc=1.2\n"
    "idac (vdd xraw) isource dc=500u\n"
    + servo_beh(0.47),
    "beh500",
    ["i(vt)", "i(vsense)", "v(xref)", "v(nbf)", "v(tail)", "v(xraw)"],
)

print("=== discrete 31 + beh servo ===")
op(
    "vdd (vdd 0) vsource dc=1.2\n" + discrete_dac(31) + servo_beh(0.47),
    "beh31",
    ["i(vt)", "i(vsense)", "v(xref)", "v(nbf)", "v(xraw)"],
)

print("=== discrete 0 + beh servo ===")
op(
    "vdd (vdd 0) vsource dc=1.2\n" + discrete_dac(0) + servo_beh(0.47),
    "beh0",
    ["i(vt)", "i(vsense)", "v(xref)", "v(nbf)"],
)

print("=== discrete 31 + MOS OTA servo ===")
op(
    "vdd (vdd 0) vsource dc=1.2\n" + discrete_dac(31) + servo_mos(0.47),
    "mos31",
    ["i(vt)", "i(vsense)", "v(xref)", "v(nbf)", "v(d1)", "v(d2)", "v(ss)"],
)

print("=== discrete 0/16/31 + MOS OTA @0.47 ===")
for code in (0, 16, 31):
    op(
        "vdd (vdd 0) vsource dc=1.2\n" + discrete_dac(code) + servo_mos(0.47),
        f"mos{code}",
        ["i(vt)", "i(vsense)", "v(xref)", "v(nbf)"],
    )
