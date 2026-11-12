#!/usr/bin/env python3
"""P2.7.1: generate hierarchical xschem capture of VCO + D22 amp-cal + D21 LDO.

Device sizes/trims come from analog/vco/step2/out/range.json and the simulated
decks (run_step2 / amp_common / ldo_body). Also writes a VACASK-format device
netlist (netlists/*.vacask) from the same inventory for equivalence + re-sim.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "ampcal"))
sys.path.insert(0, os.path.join(REPO, "analog", "vco", "step2"))

from xsch_lib import Sch, write_sym, side_um  # noqa: E402
import run_step2 as S2  # noqa: E402

RANGE_JSON = os.path.join(REPO, "analog", "vco", "step2", "out", "range.json")
L2N0_INC = os.path.join(REPO, "analog", "vco", "models", "l2n0_lumped.inc")
CAP_AREA = 1.5
R_BIAS = 2e6
SW_PER_FF = 100 / 60


def load_range():
    r = json.load(open(RANGE_JSON))
    return r


def _net(n):
    return "0" if n in ("gnd", "GND", "0") else n


def vacask_line(d):
    """One VACASK instance from a DeviceRec."""
    n = " ".join(_net(x) for x in d.nodes)
    if d.kind in ("nmos", "pmos"):
        return (f"{d.name} ({n}) {d.params['model']} "
                f"w={d.params['w']} l={d.params['l']} ng={d.params['ng']}\n")
    if d.kind == "mim":
        return (f"{d.name} ({n}) cap_rfcmim "
                f"w={d.params['w']} l={d.params['l']}\n")
    if d.kind == "svaricap":
        return (f"{d.name} ({n}) {d.params['model']} "
                f"w={d.params['w']} l={d.params['l']} nx={d.params['nx']}\n")
    if d.kind == "res":
        return f"{d.name} ({n}) resistor r={d.params['r']}\n"
    if d.kind == "capa":
        return f"{d.name} ({n}) capacitor c={d.params['c']}\n"
    if d.kind == "ind":
        return f"{d.name} ({n}) inductor l={d.params['l']}\n"
    if d.kind == "vsrc":
        return f"{d.name} ({n}) vsource dc={d.params['dc']}\n"
    if d.kind == "isrc":
        return f"{d.name} ({n}) isource dc={d.params['dc']}\n"
    raise ValueError(d.kind)


def write_vacask(path, title, devices, extra_header=""):
    hdr = f"""{title}
include "sg13g2_vacask_common.lib"
include "cornerMOSlv.lib" section=mos_tt
include "cornerMOShv.lib" section=mos_tt
include "cornerCAP.lib" section=cap_typ
load "resistor.osdi"
load "capacitor.osdi"
load "inductor.osdi"
model resistor resistor
model capacitor capacitor
model inductor inductor
model vsource vsource
model isource isource
{extra_header}
"""
    body = "".join(vacask_line(d) for d in devices)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(hdr + body)
    return path


def gen_l2n0():
    """Tapped L2n0 lumped EM model as hierarchical sch (values from l2n0_lumped.inc)."""
    sch = Sch("l2n0", os.path.join(HERE, "l2n0.sch"))
    for p in ("p", "n", "ct"):
        sch.iopin(p)
    sch.title("l2n0_EM_lumped")
    # From analog/vco/models/l2n0_lumped.inc [EM]
    sch.res("r1p", "p", "p1", 0.814837)
    sch.ind("l1p", "p1", "p2", 8.05663e-10)
    sch.res("r2p", "p2", "ct", 0.827877)
    sch.ind("l2p", "p2", "ct", 3.196e-11)
    sch.res("r1n", "n", "n1", 0.814837)
    sch.ind("l1n", "n1", "n2", 8.05663e-10)
    sch.res("r2n", "n2", "ct", 0.827877)
    sch.ind("l2n", "n2", "ct", 3.196e-11)
    sch.capa("cp", "p", "n", 2.98589e-14)
    sch.write()
    write_sym(os.path.join(HERE, "l2n0.sym"), "l2n0", ["p", "n", "ct"])
    write_vacask(os.path.join(HERE, "netlists", "l2n0.vacask"),
                 "P2.7.1 l2n0 lumped", sch.devices,
                 extra_header="// subckt body only — wrap for top\n")
    return sch


def gen_vco_core(rng):
    sch = Sch("vco_core", os.path.join(HERE, "vco_core.sch"))
    for p in ("tp", "tn", "tail", "ct", "vdd", "gnd"):
        sch.iopin(p)
    sch.title("vco_core_XC")
    # Cross-coupled pair (run_step2)
    sch.nmos("m1", "tp", "tn", "tail", "gnd", "32u", "0.13u", 8)
    sch.nmos("m2", "tn", "tp", "tail", "gnd", "32u", "0.13u", 8)
    cfix = float(rng["cfix"])
    if cfix > 0:
        s = side_um(2 * cfix)
        sch.mim("xf1", "tp", "fx", "gnd", f"{s:.3f}u", f"{s:.3f}u")
        sch.mim("xf2", "tn", "fx", "gnd", f"{s:.3f}u", f"{s:.3f}u")
        sch.res("rfx", "fx", "gnd", 200e3)
    sch.write()
    write_sym(os.path.join(HERE, "vco_core.sym"), "vco_core",
              ["tp", "tn", "tail", "ct", "vdd", "gnd"])
    return sch


def gen_vco_tail_dac():
    """D22 V_DS-matched OTA DAC + tail (amp_common sizes) + D9 filter + bypass."""
    import amp_common as A
    sch = Sch("vco_tail_dac", os.path.join(HERE, "vco_tail_dac.sch"))
    for p in ("tail", "vdd", "gnd", "vbp_tail", "nb", "nbf",
              "code0", "code1", "code2", "code3", "code4"):
        sch.iopin(p)
    sch.title("vco_tail_dac_D22")
    # Unit DAC (code pins drive switch gates: 0=on in sim via logic; here pins)
    # Master + offset + 5 bits — switches gated by code* (1.2=off, 0=on in deck)
    sch.isrc("imaster", "pbias", "gnd", A.I_MASTER)
    sch.pmos("mm0", "pbias", "pbias", "vdd", "vdd", "2u", "2u", 1)
    sch.pmos("moff", "xoff", "pbias", "vdd", "vdd", "38u", "2u", 19)
    sch.pmos("msoff", "xraw", "gnd", "xoff", "vdd", "38u", "0.13u", 1)
    bits = [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16)]
    for b, m in bits:
        sch.pmos(f"mdb{b}", f"xd{b}", "pbias", "vdd", "vdd",
                 f"{2*m}u", "2u", m)
        # Switch gate = code{b}: schematic pin; TB ties 0 or vdd
        sch.pmos(f"msw{b}", "xraw", f"code{b}", f"xd{b}", "vdd",
                 f"{2*m}u", "0.13u", 1)
    # V_DS-matched mirror + OTA
    sch.vsrc("vsense", "xraw", "xref", 0)
    sch.nmos("mr", "xref", "nbf", "gnd", "gnd", A.W_MR, "4u", A.NG_MR)
    sch.nmos("mt", "tail", "nbf", "gnd", "gnd", A.W_MT, "4u", A.NG_MT)
    sch.res("rtf", "tail", "tail_f", 100e3)
    sch.capa("ctf", "tail_f", "gnd", 1e-12)
    sch.nmos("mo1", "d1", "xref", "ss", "gnd", "8u", "2u", 2)
    sch.nmos("mo2", "d2", "tail_f", "ss", "gnd", "8u", "2u", 2)
    sch.isrc("iss", "ss", "gnd", 20e-6)
    sch.pmos("mp1", "d1", "d1", "vdd", "vdd", "4u", "2u", 2)
    sch.pmos("mp2", "d2", "d1", "vdd", "vdd", "4u", "2u", 2)
    sch.res("rout", "d2", "nb", 1)
    sch.res("rbf", "nb", "nbf", 1e6)
    sch.capa("cbf", "nbf", "gnd", 50e-12)
    sch.res("rpd", "nb", "gnd", 200e3)
    sch.capa("ctail", "tail", "gnd", 8e-12)
    # start-up bypass across rbf
    sch.nmos("mbp_rbf", "nb", "vbp_tail", "nbf", "gnd", "20u", "0.13u", 4)
    sch.write()
    write_sym(os.path.join(HERE, "vco_tail_dac.sym"), "vco_tail_dac",
              ["tail", "vdd", "gnd", "vbp_tail", "nb", "nbf",
               "code0", "code1", "code2", "code3", "code4"])
    return sch


def gen_vco_bank(rng):
    """D24 segmented bank: 5 binary + 7 thermometer unit cells (or legacy binary)."""
    S2.apply_range_trims(rng)
    ncell = S2.n_bank_cells()
    sch = Sch("vco_bank", os.path.join(HERE, "vco_bank.sch"))
    ports = ["tp", "tn", "vbp", "gnd"]
    for k in range(ncell):
        ports += [f"g{k}", f"bb{k}"]
    for p in ports:
        sch.iopin(p)
    title = ("vco_bank_D24_seg" if S2.BANK_ARCH == "d24"
             else "vco_bank_8bit_trim")
    sch.title(title)
    lsb = float(rng["lsb"])
    for k in range(ncell):
        wt = S2.cell_weight(k)
        tr = S2.cell_trim(k)
        c_mim = 2 * lsb * wt * tr
        s = side_um(c_mim)
        w = SW_PER_FF * lsb * wt * tr
        ng = max(1, int(round(w / 2.5)))
        sch.mim(f"xb{k}p", "tp", f"a{k}", "gnd", f"{s:.3f}u", f"{s:.3f}u")
        sch.mim(f"xb{k}n", "tn", f"b{k}", "gnd", f"{s:.3f}u", f"{s:.3f}u")
        sch.nmos(f"ms{k}", f"a{k}", f"g{k}", f"b{k}", "gnd",
                 f"{w:.2f}u", "0.13u", ng)
        sch.res(f"rba{k}", f"a{k}", f"bb{k}", R_BIAS)
        sch.res(f"rbb{k}", f"b{k}", f"bb{k}", R_BIAS)
        bw, bl, bng = S2.bank_bypass_geom(k)
        sch.nmos(f"mbp_rba{k}", f"a{k}", "vbp", f"bb{k}", "gnd",
                 f"{bw:.4g}u", f"{bl:g}u", bng)
        sch.nmos(f"mbp_rbb{k}", f"b{k}", "vbp", f"bb{k}", "gnd",
                 f"{bw:.4g}u", f"{bl:g}u", bng)
    sch.write()
    write_sym(os.path.join(HERE, "vco_bank.sym"), "vco_bank", ports)
    return sch


def gen_vco_var(rng):
    sch = Sch("vco_var", os.path.join(HERE, "vco_var.sch"))
    for p in ("tp", "tn", "vt", "vbp", "gnd"):
        sch.iopin(p)
    sch.title("vco_var_AC_D11")
    nfing = int(rng.get("nfing", 20))
    sc = side_um(5 * nfing * 6.8)
    sch.mim("xcp", "tp", "vgp", "gnd", f"{sc:.3f}u", f"{sc:.3f}u")
    sch.mim("xcn", "tn", "vgn", "gnd", f"{sc:.3f}u", f"{sc:.3f}u")
    sch.res("rvp", "vgp", "vvb", R_BIAS)
    sch.res("rvn", "vgn", "vvb", R_BIAS)
    sch.vsrc("vvb", "vvb", "gnd", 0.3)
    nx1 = nfing - nfing // 2
    nx2 = nfing // 2
    sch.svaricap_fx("xv1", "vgp", "vt", "vgn", "gnd", nx=nx1)
    sch.svaricap_fx("xv2", "vgp", "vt", "vgn", "gnd", nx=nx2)
    sch.nmos("mbp_rvp", "vgp", "vbp", "vvb", "gnd", "5u", "0.13u", 2)
    sch.nmos("mbp_rvn", "vgn", "vbp", "vvb", "gnd", "5u", "0.13u", 2)
    sch.write()
    write_sym(os.path.join(HERE, "vco_var.sym"), "vco_var",
              ["tp", "tn", "vt", "vbp", "gnd"])
    return sch


def gen_ampcal_det():
    import amp_common as A
    sch = Sch("ampcal_det", os.path.join(HERE, "ampcal_det.sch"))
    for p in ("tp", "tn", "ct", "vdd", "gnd", "cmp", "hold", "rep"):
        sch.iopin(p)
    sch.title("ampcal_det_cmp_D22")
    th = A.v_th()
    sch.nmos("mdtp", "vdd", "tp", "hold", "gnd", A.W_DET, A.L_DET, 1)
    sch.nmos("mdtn", "vdd", "tn", "hold", "gnd", A.W_DET, A.L_DET, 1)
    sch.isrc("idet", "hold", "gnd", A.I_DET)
    sch.capa("chold", "hold", "gnd", A.C_HOLD)
    sch.nmos("mrtp", "vdd", "ct", "rep", "gnd", A.W_DET, A.L_DET, 1)
    sch.nmos("mrtn", "vdd", "ct", "rep", "gnd", A.W_DET, A.L_DET, 1)
    sch.isrc("irep", "rep", "gnd", A.I_DET)
    sch.capa("crep", "rep", "gnd", A.C_HOLD)
    sch.vsrc("vth", "vthn", "rep", th)
    sch.nmos("mc1", "co", "hold", "ttail", "gnd", "4u", "0.5u", 2)
    sch.nmos("mc2", "co2", "vthn", "ttail", "gnd", "4u", "0.5u", 2)
    sch.isrc("itt", "ttail", "gnd", 20e-6)
    sch.res("rc1", "vdd", "co", 20e3)
    sch.res("rc2", "vdd", "co2", 20e3)
    sch.nmos("mcs1", "n1", "co2", "ss2", "gnd", "4u", "0.5u", 2)
    sch.nmos("mcs2", "cmp", "co", "ss2", "gnd", "4u", "0.5u", 2)
    sch.isrc("iss2", "ss2", "gnd", 20e-6)
    sch.pmos("mpl1", "n1", "n1", "vdd", "vdd", "4u", "0.5u", 2)
    sch.pmos("mpl2", "cmp", "n1", "vdd", "vdd", "4u", "0.5u", 2)
    sch.capa("cl_cmp", "cmp", "gnd", 50e-15)
    sch.write()
    write_sym(os.path.join(HERE, "ampcal_det.sym"), "ampcal_det",
              ["tp", "tn", "ct", "vdd", "gnd", "cmp", "hold", "rep"])
    return sch


def gen_ldo():
    """D21 VR_ANA1 LDO core (ldo_body): sense at vout, Rz+Cg compensation."""
    sch = Sch("vrana1_ldo", os.path.join(HERE, "vrana1_ldo.sch"))
    for p in ("vin", "vout", "vref", "gnd"):
        sch.iopin(p)
    sch.title("vrana1_ldo_D21")
    sch.pmos("mp", "vout", "vg", "vin", "vin", "400u", "0.13u", 80)
    sch.res("rf1", "vout", "mid", 200e3)
    sch.res("rf2", "mid", "gnd", 200e3)
    sch.isrc("ib", "vin", "nb", 40e-6)
    sch.nmos("mb", "nb", "nb", "gnd", "gnd", "4u", "2u", 2)
    sch.nmos("mt", "t", "nb", "gnd", "gnd", "8u", "2u", 2)
    sch.nmos("m1", "d1", "mid", "t", "gnd", "16u", "2u", 4)
    sch.nmos("m2", "vg", "vref", "t", "gnd", "16u", "2u", 4)
    sch.pmos("m3", "d1", "d1", "vin", "vin", "32u", "2u", 4)
    sch.pmos("m4", "vg", "d1", "vin", "vin", "32u", "2u", 4)
    sch.res("rz", "vg", "ncg", 500)
    sch.capa("cg", "ncg", "gnd", 100e-12)
    # Cout ~100 fF MIM (side from ldo_body)
    sc = math.sqrt(100e-12 * 1e15 / 1.5)  # c_ff / CAP_AREA
    sch.mim("xout", "vout", "gnd", "gnd", f"{sc:.3f}u", f"{sc:.3f}u")
    sch.write()
    write_sym(os.path.join(HERE, "vrana1_ldo.sym"), "vrana1_ldo",
              ["vin", "vout", "vref", "gnd"])
    return sch


def gen_vco_top(rng, blocks):
    """Hierarchical VCO top: leaf symbols wired by net name (P2.7.2a).

    Instantiates l2n0, vco_core, vco_bank (D24), vco_var, vco_tail_dac,
    ampcal_det. Fixed MIM lives in vco_core; bypasses in bank/var/tail.
    Digital: bank gates g0..g11 and DAC code0..code4 are top ports.
    """
    S2.apply_range_trims(rng)
    ncell = S2.n_bank_cells()
    top_ports = [
        "tp", "tn", "ct", "vt", "vdd", "gnd", "vbp", "vbp_tail",
        "cmp", "tail", "hold", "rep",
    ]
    top_ports += [f"g{k}" for k in range(ncell)]
    top_ports += [f"code{b}" for b in range(5)]

    sch = Sch("vco_top", os.path.join(HERE, "vco_top.sch"))
    for p in top_ports:
        sch.iopin(p)
    sch.title("vco_top_P272a_hier")

    # Inductor (tank L)
    sch.subckt_inst("l2n0.sym", "xl",
                    {"p": "tp", "n": "tn", "ct": "ct"}, x=0, y=0)

    # Core + fixed cap
    sch.subckt_inst(
        "vco_core.sym", "xcore",
        {"tp": "tp", "tn": "tn", "tail": "tail", "ct": "ct",
         "vdd": "vdd", "gnd": "gnd"},
        x=200, y=0)

    # D24 bank
    bank_nets = {"tp": "tp", "tn": "tn", "vbp": "vbp", "gnd": "gnd"}
    for k in range(ncell):
        bank_nets[f"g{k}"] = f"g{k}"
        bank_nets[f"bb{k}"] = f"bb{k}"
    sch.subckt_inst("vco_bank.sym", "xbank", bank_nets, x=400, y=0)

    # Varactor + bias / bypass
    sch.subckt_inst(
        "vco_var.sym", "xvar",
        {"tp": "tp", "tn": "tn", "vt": "vt", "vbp": "vbp", "gnd": "gnd"},
        x=600, y=0)

    # Tail DAC / OTA / RC / bypass
    sch.subckt_inst(
        "vco_tail_dac.sym", "xtail",
        {"tail": "tail", "vdd": "vdd", "gnd": "gnd", "vbp_tail": "vbp_tail",
         "nb": "nb", "nbf": "nbf",
         "code0": "code0", "code1": "code1", "code2": "code2",
         "code3": "code3", "code4": "code4"},
        x=200, y=200)

    # D22 detector + SE comparator
    sch.subckt_inst(
        "ampcal_det.sym", "xdet",
        {"tp": "tp", "tn": "tn", "ct": "ct", "vdd": "vdd", "gnd": "gnd",
         "cmp": "cmp", "hold": "hold", "rep": "rep"},
        x=400, y=200)

    sch.write()
    write_sym(os.path.join(HERE, "vco_top.sym"), "vco_top", top_ports)
    return sch


def build_flat_inventory(rng):
    """One flat device list matching the simulated VCO+D22+LDO decks."""
    # Rebuild by calling each gen_* and concatenating .devices — but gens write
    # files. Call them and collect.
    blocks = {}
    blocks["l2n0"] = gen_l2n0()
    blocks["vco_core"] = gen_vco_core(rng)
    blocks["vco_tail_dac"] = gen_vco_tail_dac()
    blocks["vco_bank"] = gen_vco_bank(rng)
    blocks["vco_var"] = gen_vco_var(rng)
    blocks["ampcal_det"] = gen_ampcal_det()
    blocks["vrana1_ldo"] = gen_ldo()
    gen_vco_top(rng, blocks)

    # Flat VACASK for VCO core path (stand-alone range TB uses step2 topology
    # with ideal iref — keep a 'vco_sim' that mirrors run_step2 netlist closely)
    sim = Sch("vco_sim_flat", os.path.join(HERE, "vco_sim_flat.sch"))
    for p in ("tp", "tn", "ct", "vt", "vdd", "gnd", "vbp", "vbp_tail"):
        sim.iopin(p)
    sim.title("vco_sim_flat_step2")
    # Inductor elements
    for d in blocks["l2n0"].devices:
        _emit(sim, d)
    # Core
    for d in blocks["vco_core"].devices:
        _emit(sim, d)
    # Bank
    for d in blocks["vco_bank"].devices:
        _emit(sim, d)
    # Var
    for d in blocks["vco_var"].devices:
        _emit(sim, d)
    # Stand-alone tail (step2 style) for range TB — also emit D22 block separately
    sim.capa("ctail", "tail", "gnd", 8e-12)
    sim.nmos("mt", "tail", "nbf", "gnd", "gnd", "160u", "4u", 32)
    sim.res("rbf", "nb", "nbf", 1e6)
    sim.capa("cbf", "nbf", "gnd", 50e-12)
    sim.nmos("mr", "nb", "nb", "gnd", "gnd", "20u", "4u", 4)
    sim.isrc("iref", "vdd", "nb", 4e-3 / 8)
    sim.nmos("mbp_rbf", "nb", "vbp_tail", "nbf", "gnd", "20u", "0.13u", 4)
    # Stand-in buffer
    sim.nmos("mb1", "op", "tp", "tb", "gnd", "10u", "0.13u", 4)
    sim.nmos("mb2", "on", "tn", "tb", "gnd", "10u", "0.13u", 4)
    sim.res("rl1", "vdd", "op", 400)
    sim.res("rl2", "vdd", "on", 400)
    sim.isrc("ib", "tb", "gnd", 1e-3)
    sim.capa("ctb", "tb", "gnd", 2e-12)
    sim.capa("cl1", "op", "gnd", 20e-15)
    sim.capa("cl2", "on", "gnd", 20e-15)
    sim.write()
    write_sym(os.path.join(HERE, "vco_sim_flat.sym"), "vco_sim_flat",
              ["tp", "tn", "ct", "vt", "vdd", "gnd", "vbp", "vbp_tail"])

    # Combined inventory JSON
    inv = {}
    for k, sch in blocks.items():
        inv[k] = [
            {"kind": d.kind, "name": d.name, "nodes": d.nodes, "params": d.params}
            for d in sch.devices
        ]
    inv["vco_sim_flat"] = [
        {"kind": d.kind, "name": d.name, "nodes": d.nodes, "params": d.params}
        for d in sim.devices
    ]
    open(os.path.join(HERE, "netlists", "device_inventory.json"), "w").write(
        json.dumps(inv, indent=2)
    )

    # Per-block vacask
    for k, sch in blocks.items():
        write_vacask(os.path.join(HERE, "netlists", f"{k}.vacask"),
                     f"P2.7.1 {k}", sch.devices)
    write_vacask(os.path.join(HERE, "netlists", "vco_sim_flat.vacask"),
                 "P2.7.1 vco_sim_flat", sim.devices)

    # Copy EM include next to netlists for sims
    shutil.copy(L2N0_INC, os.path.join(HERE, "netlists", "l2n0_lumped.inc"))
    return blocks, sim


def _emit(sch: Sch, d):
    p = d.params
    if d.kind == "nmos":
        sch.nmos(d.name, *d.nodes, p["w"], p["l"], int(p["ng"]), p["model"])
    elif d.kind == "pmos":
        sch.pmos(d.name, *d.nodes, p["w"], p["l"], int(p["ng"]), p["model"])
    elif d.kind == "mim":
        sch.mim(d.name, *d.nodes, p["w"], p["l"])
    elif d.kind == "svaricap":
        sch.svaricap_fx(d.name, *d.nodes, p["w"], p["l"], int(p["nx"]))
    elif d.kind == "res":
        sch.res(d.name, *d.nodes, float(p["r"]))
    elif d.kind == "capa":
        sch.capa(d.name, *d.nodes, float(p["c"]))
    elif d.kind == "ind":
        sch.ind(d.name, *d.nodes, float(p["l"]))
    elif d.kind == "vsrc":
        sch.vsrc(d.name, *d.nodes, float(p["dc"]))
    elif d.kind == "isrc":
        sch.isrc(d.name, *d.nodes, float(p["dc"]))
    else:
        raise ValueError(d.kind)


def write_xschemrc():
    src = "/foss/pdks/ihp-sg13g2/libs.tech/xschem/xschemrc"
    dst = os.path.join(HERE, "xschemrc")
    if os.path.exists(src):
        text = open(src).read()
        # Prepend local path
        text = (
            f'set XSCHEM_LIBRARY_PATH {HERE}:$XSCHEM_LIBRARY_PATH\n'
            + text
        )
        open(dst, "w").write(text)
    else:
        open(dst, "w").write(
            f"set XSCHEM_LIBRARY_PATH {HERE}\n"
            "append XSCHEM_LIBRARY_PATH :$env(PDK_ROOT)/$env(PDK)/libs.tech/xschem\n"
        )


def main():
    rng = load_range()
    write_xschemrc()
    blocks, sim = build_flat_inventory(rng)
    # README
    open(os.path.join(HERE, "README.md"), "w").write(
        "# P2.7.1 xschem capture (VCO + D22 amp-cal + D21 LDO)\n\n"
        "Generated by `gen_xschem.py` from `step2/out/range.json`, "
        "`ampcal/amp_common.py`, and `ldo/run_d21_vrana1.py` `ldo_body`.\n\n"
        "## Hierarchy\n\n"
        "| Cell | Role |\n|---|---|\n"
        "| `l2n0` | Tapped inductor lumped EM model |\n"
        "| `vco_core` | XC pair + fixed MIM |\n"
        "| `vco_bank` | 8-bit bank + trims + bypass |\n"
        "| `vco_var` | AC-coupled svaricap_fx + bypass |\n"
        "| `vco_tail_dac` | D22 OTA DAC + tail + D9 filter |\n"
        "| `ampcal_det` | D22 peak det + SE comparator |\n"
        "| `vrana1_ldo` | D21 LDO |\n"
        "| `vco_sim_flat` | Flat VCO for netlist/sim export |\n\n"
        "Exports: `exports/*.svg`, `exports/*.pdf`. "
        "Netlists: `netlists/`. Summaries: `out/summary_*.txt`.\n"
    )
    print("Generated cells:", ", ".join(blocks.keys()), "+ vco_sim_flat")
    print("Devices in vco_sim_flat:", len(sim.devices))
    for k, sch in blocks.items():
        print(f"  {k}: {len(sch.devices)} devices")


if __name__ == "__main__":
    main()

