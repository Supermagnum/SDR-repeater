#!/usr/bin/env python3
"""P2.7.2b — routed VCO core + tank (L2n0 + XC pair + fixed MIM + CT supply).

Hierarchy matches vco_top.sch: l2n0 + vco_core, with ports for bank / var /
detector / LO buffer (tp, tn) and tail DAC (tail). Inductor is the via-fixed
EM cell. Active devices stay outside the 30 µm keep-out [HAND floorplan].

Bank_unit lessons applied: Cont off Activ (gate pads), 1×1 via_stack landings
on S/D cols, no wide M1 across L=0.13 gaps, TM1 ≥ 1.70 µm [DS TM1.a].
"""
from __future__ import annotations

import gzip
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
IND_GDS = os.path.join(REPO, "sim/em/sg13-octagon-l2n0/tapped/L_2n0_tapped.gds")
os.makedirs(OUT, exist_ok=True)

sys.path[:0] = [
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python",
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python/pycell4klayout-api/source/python",
]

import pya  # noqa: E402
import sg13g2_pycell_lib  # noqa: E402, F401

DBU = 0.001
KEEP_OUT = 30.0  # µm from inductor bbox [HAND / p27-layout-notes]
# Open PDK process_spec has no EM current table [DS miss]. Conservative HAND
# limits (Al BEOL, ~130 nm class): M1–M5 ≈ 1.0 mA/µm, TM1 ≈ 5 mA/µm, TM2 ≈ 10.
EM_M5 = 1.0   # mA/µm [HAND]
EM_TM1 = 5.0  # mA/µm [HAND]
I_TAIL = 4.0  # mA max [DS D12]


def um(x: float) -> int:
    return int(round(float(x) / DBU))


class B:
    def __init__(self):
        self.ly = pya.Layout()
        self.ly.dbu = DBU
        self.ly.technology_name = "sg13g2"
        self.lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
        self.lib_ly = self.lib.layout()
        self.m1 = self.ly.layer(8, 0)
        self.m1pin = self.ly.layer(8, 2)
        self.m1txt = self.ly.layer(8, 25)
        self.m2 = self.ly.layer(10, 0)
        self.m5 = self.ly.layer(67, 0)
        self.tm1 = self.ly.layer(126, 0)
        self.tm1pin = self.ly.layer(126, 2)
        self.tm1txt = self.ly.layer(126, 25)
        self.cont = self.ly.layer(6, 0)
        self.poly = self.ly.layer(5, 0)
        self.activ = self.ly.layer(1, 0)
        self.log = []

    def say(self, s=""):
        print(s, flush=True)
        self.log.append(s)

    def pcell(self, name, params):
        decl = self.lib_ly.pcell_declaration(name)
        return self.ly.add_pcell_variant(self.lib, decl.id(), params)

    def place(self, parent, cid, x, y, mirror=False):
        if mirror:
            t = pya.Trans(pya.Trans.M90, um(x), um(y))
        else:
            t = pya.Trans(pya.Trans.R0, um(x), um(y))
        parent.insert(pya.CellInstArray(cid, t))
        return self.ly.cell(cid).bbox().transformed(t).to_dtype(self.ly.dbu), t

    def box(self, cell, layer, x0, y0, x1, y1):
        cell.shapes(layer).insert(
            pya.DBox(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    def pin_tm1(self, cell, x, y, name):
        self.box(cell, self.tm1, x - 0.5, y - 0.5, x + 0.5, y + 0.5)
        self.box(cell, self.tm1pin, x - 0.4, y - 0.4, x + 0.4, y + 0.4)
        cell.shapes(self.tm1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def pin_m1(self, cell, x, y, name):
        self.box(cell, self.m1, x - 0.25, y - 0.25, x + 0.25, y + 0.25)
        self.box(cell, self.m1pin, x - 0.2, y - 0.2, x + 0.2, y + 0.2)
        cell.shapes(self.m1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def m1_sd_cols(self, cid, trans):
        """S/D M1 columns of an nmos (exclude guard-ring straps)."""
        cell = self.ly.cell(cid)
        uniq = {}
        for s in cell.shapes(self.m1).each():
            if not s.is_box():
                continue
            b = s.bbox().transformed(trans).to_dtype(self.ly.dbu)
            # SD fingers: ~0.16 µm wide, ≥1 µm tall; GR straps are wider / short
            if b.width() > 0.25 or b.height() < 1.0:
                continue
            cx = round((b.left + b.right) / 2, 3)
            uniq[cx] = b
        return [uniq[k] for k in sorted(uniq)]

    def poly_gates(self, cid, trans):
        cell = self.ly.cell(cid)
        boxes = []
        for s in cell.shapes(self.poly).each():
            if s.is_box():
                boxes.append(s.bbox().transformed(trans).to_dtype(self.ly.dbu))
        boxes.sort(key=lambda b: b.left)
        return boxes

    def activ_top(self, cid, trans):
        cell = self.ly.cell(cid)
        top = None
        for s in cell.shapes(self.activ).each():
            if s.is_box():
                b = s.bbox().transformed(trans).to_dtype(self.ly.dbu)
                top = b.top if top is None else max(top, b.top)
        return top if top is not None else 0.0

    def gate_bus(self, cell, gates, activ_top, x_bus, y_bus, net_name):
        """Shared poly strap above Activ + Conts; M1 exits outboard only [bank_unit].

        No full-width M1 bar over the finger array (that sat near SD M1 tops and
        merged G↔D). Cont M1 stays on the pad; a single side exit reaches x_bus.
        """
        y_pad0 = max(activ_top + 0.50, max(g.top for g in gates) + 0.30)
        y_pad1 = y_pad0 + 0.50
        gx0 = min(g.left for g in gates)
        gx1 = max(g.right for g in gates)
        for g in gates:
            gx = 0.5 * (g.left + g.right)
            half = 0.5 * (g.right - g.left)
            self.box(cell, self.poly, gx - half, g.top - 0.05, gx + half, y_pad0 + 0.05)
        self.box(cell, self.poly, gx0 - 0.05, y_pad0, gx1 + 0.05, y_pad1)
        # Cont + tiny M1 only on pads; strap M1 on the outboard half toward x_bus
        for g in gates:
            gx = 0.5 * (g.left + g.right)
            self.box(cell, self.cont, gx - 0.08, y_pad0 + 0.16, gx + 0.08, y_pad0 + 0.32)
            self.box(cell, self.m1, gx - 0.08, y_pad0 + 0.16, gx + 0.08, y_pad1 + 0.16)
        # poly already straps gates; pick the Cont nearest x_bus for M1 exit
        g_exit = min(gates, key=lambda g: abs(0.5 * (g.left + g.right) - x_bus))
        gx = 0.5 * (g_exit.left + g_exit.right)
        y_rise = y_pad1 + 0.40
        self.box(cell, self.m1, gx - 0.10, y_pad1, gx + 0.10, y_rise + 0.28)
        self.box(cell, self.m1, min(x_bus, gx) - 0.14, y_rise,
                 max(x_bus, gx) + 0.14, y_rise + 0.28)
        self.box(cell, self.m1, x_bus - 0.14, min(y_rise, y_bus),
                 x_bus + 0.14, max(y_rise + 0.28, y_bus))
        return y_pad1

    def build(self):
        top = self.ly.create_cell("vco_core_tank")
        # --- inductor (via-fixed EM GDS) ---
        ind_ly = pya.Layout()
        ind_ly.read(IND_GDS)
        src = ind_ly.top_cell()
        ind = self.ly.create_cell("L_2n0_tapped")
        ind.copy_tree(src)
        ind_bb, _ = self.place(top, ind.cell_index(), 0, 0)
        self.say(f"inductor bbox {ind_bb} [EM]")

        # Port targets on inductor: LA / LB texts ≈ (±27.5, 3); CT stub x=0
        la_x, lb_x = -27.5, 27.5
        port_y = ind_bb.bottom  # south edge of coil cell
        # keep-out south limit for Activ
        y_keep = ind_bb.bottom - KEEP_OUT
        self.say(f"keep-out Activ y ≤ {y_keep:.2f} µm (30 µm from ind) [HAND]")

        # --- XC pair: mirrored pair (no PCell GR — GR M1 shorts S/D when routed) ---
        nmos = self.pcell("nmos", {
            "w": "32.0u", "l": "0.13u", "ng": 8, "m": 1,
            "guardRingType": "none",
        })
        loc = self.ly.cell(nmos).bbox().to_dtype(self.ly.dbu)
        gap = 6.0
        y_pair = y_keep - (loc.top - loc.bottom) - 8.0
        # M1 (R0): right edge at -gap/2. M2 (M90): left edge at +gap/2.
        x_m1 = -gap / 2 - loc.right
        x_m2_origin = gap / 2 + loc.right
        bb_m1, t_m1 = self.place(top, nmos, x_m1, y_pair, mirror=False)
        bb_m2, t_m2 = self.place(top, nmos, x_m2_origin, y_pair, mirror=True)
        self.say(f"M1 {bb_m1}; M2 {bb_m2}")
        # End dummies deferred: prior attempt bridged gnd into tank M1 (LVS merge).

        # psub guard: ptap1 far outboard (clear of tank spur M1)
        ptap = self.pcell("ptap1", {"w": "0.78u", "l": "0.78u"})
        ring_y0 = min(bb_m1.bottom, bb_m2.bottom) - 2.5
        ring_y1 = max(bb_m1.top, bb_m2.top) + 2.5
        ring_x0 = bb_m1.left - 12.0
        ring_x1 = bb_m2.right + 12.0
        for x in (ring_x0, ring_x1 - 0.78):
            for y in (ring_y0, ring_y1 - 0.78):
                self.place(top, ptap, x, y)

        cols1 = self.m1_sd_cols(nmos, t_m1)
        cols2 = self.m1_sd_cols(nmos, t_m2)
        g1 = self.poly_gates(nmos, t_m1)
        g2 = self.poly_gates(nmos, t_m2)
        at1 = self.activ_top(nmos, t_m1)
        at2 = self.activ_top(nmos, t_m2)
        assert len(cols1) == 9 and len(cols2) == 9, (len(cols1), len(cols2))
        # even = source (tail), odd = drain (tank)
        src1 = [cols1[i] for i in range(0, 9, 2)]
        drn1 = [cols1[i] for i in range(1, 9, 2)]
        src2 = [cols2[i] for i in range(0, 9, 2)]
        drn2 = [cols2[i] for i in range(1, 9, 2)]

        vs15 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal5",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs5t = self.pcell("via_stack", {
            "b_layer": "Metal5", "t_layer": "TopMetal1",
            "vn_columns": 2, "vn_rows": 2,
        })
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })

        # --- tail rail (M1) under sources only; gnd stays separate ---
        y_tail = min(bb_m1.bottom, bb_m2.bottom) - 3.0
        for c in src1 + src2:
            self.box(top, self.m1, c.left, y_tail, c.right, c.bottom)
        self.box(top, self.m1,
                 min(src1[0].left, src2[0].left) - 0.2, y_tail,
                 max(src1[-1].right, src2[-1].right) + 0.2, y_tail + 0.40)
        self.pin_m1(top, 0.0, y_tail + 0.2, "tail")

        # Outboard spur X (far from SD cols)
        x_tp_spur = bb_m1.left - 5.0
        x_tn_spur = bb_m2.right + 5.0
        x_g_m1 = bb_m1.left - 9.0   # M1 gates → tn
        x_g_m2 = bb_m2.right + 9.0  # M2 gates → tp

        # Drain collect NORTH of Activ only
        y_dr_tp = max(at1, at2) + 3.0
        y_dr_tn = y_dr_tp + 1.5  # ≥ M1.b 0.18
        for c in drn1:
            self.box(top, self.m1, c.left, y_dr_tp, c.right, c.bottom)
        self.box(top, self.m1, min(c.left for c in drn1), y_dr_tp,
                 max(c.right for c in drn1), y_dr_tp + 0.40)
        self.box(top, self.m1, x_tp_spur, y_dr_tp,
                 max(c.right for c in drn1), y_dr_tp + 0.40)
        for c in drn2:
            self.box(top, self.m1, c.left, y_dr_tn, c.right, c.bottom)
        self.box(top, self.m1, min(c.left for c in drn2), y_dr_tn,
                 max(c.right for c in drn2), y_dr_tn + 0.40)
        self.box(top, self.m1, min(c.left for c in drn2), y_dr_tn,
                 x_tn_spur, y_dr_tn + 0.40)

        # Gate buses exit ABOVE drain Y so the outboard jog never crosses drain M1
        y_g_exit = max(y_dr_tp, y_dr_tn) + 2.0
        self.gate_bus(top, g1, at1, x_g_m1, y_g_exit, "tn")
        self.gate_bus(top, g2, at2, x_g_m2, y_g_exit, "tp")

        # Cross-couple SOUTH of the pair on M2
        y_xc_tp = y_tail - 6.0
        y_xc_tn = y_tail - 8.0  # ≥ M2.b 0.21
        # drain spur M1: only down from drain Y to XC (not up into gate exit Y)
        self.box(top, self.m1, x_tp_spur - 0.14, y_xc_tp, x_tp_spur + 0.14, y_dr_tp + 0.40)
        self.box(top, self.m1, x_tn_spur - 0.14, y_xc_tn, x_tn_spur + 0.14, y_dr_tn + 0.40)
        self.place(top, vs12, x_tp_spur - 0.05, y_xc_tp)
        self.place(top, vs12, x_tn_spur - 0.05, y_xc_tn)
        # gate M1: only on far-outboard X from exit Y down to XC (never at spur X)
        self.box(top, self.m1, x_g_m1 - 0.14, y_xc_tn, x_g_m1 + 0.14, y_g_exit + 0.40)
        self.box(top, self.m1, x_g_m2 - 0.14, y_xc_tp, x_g_m2 + 0.14, y_g_exit + 0.40)
        self.place(top, vs12, x_g_m1 - 0.05, y_xc_tn)
        self.place(top, vs12, x_g_m2 - 0.05, y_xc_tp)
        self.box(top, self.m2, x_g_m1 - 0.20, y_xc_tn, x_tn_spur + 0.20, y_xc_tn + 0.40)
        self.box(top, self.m2, x_g_m2 - 0.20, y_xc_tp, x_tp_spur + 0.20, y_xc_tp + 0.40)

        # gnd: south spine + drop to far-outboard ptaps only (no M1 beside tank spurs)
        y_gnd_d = y_xc_tn - 4.0
        self.box(top, self.m1, ring_x0, y_gnd_d, ring_x0 + 0.78, ring_y0 + 0.78)
        self.box(top, self.m1, ring_x1 - 0.78, y_gnd_d, ring_x1, ring_y0 + 0.78)

        # Tank risers NORTH only (from drain Y up) — never pass through XC Y
        y_via = y_keep - 4.0
        self.box(top, self.m2, x_tp_spur - 0.20, y_dr_tp, x_tp_spur + 0.20, y_via + 0.40)
        self.box(top, self.m2, x_tn_spur - 0.20, y_dr_tn, x_tn_spur + 0.20, y_via + 0.40)
        self.place(top, vs12, x_tp_spur - 0.05, y_dr_tp)
        self.place(top, vs12, x_tn_spur - 0.05, y_dr_tn)
        self.place(top, vs12, x_tp_spur - 0.05, y_via)
        self.place(top, vs12, x_tn_spur - 0.05, y_via)
        self.box(top, self.m1, x_tp_spur - 0.20, y_via, x_tp_spur + 0.20, y_via + 0.40)
        self.box(top, self.m1, x_tn_spur - 0.20, y_via, x_tn_spur + 0.20, y_via + 0.40)
        self.place(top, vs15, x_tp_spur - 0.05, y_via)
        self.place(top, vs15, x_tn_spur - 0.05, y_via)
        self.box(top, self.m5, x_tp_spur - 1.2, y_via - 0.5, x_tp_spur + 1.2, y_via + 1.0)
        self.box(top, self.m5, x_tn_spur - 1.2, y_via - 0.5, x_tn_spur + 1.2, y_via + 1.0)
        self.place(top, vs5t, x_tp_spur - 0.1, y_via)
        self.place(top, vs5t, x_tn_spur - 0.1, y_via)

        # --- wide TM1 tank + CT (symmetric); TM1.a ≥ 1.64 ---
        w_tank = 4.0
        w_ct = 8.0
        self.box(top, self.tm1, x_tp_spur - w_tank / 2, y_via - 0.5,
                 x_tp_spur + w_tank / 2, port_y + 2.0)
        self.box(top, self.tm1, x_tn_spur - w_tank / 2, y_via - 0.5,
                 x_tn_spur + w_tank / 2, port_y + 2.0)
        self.box(top, self.tm1, la_x - w_tank / 2, port_y,
                 x_tp_spur + w_tank / 2, port_y + w_tank)
        self.box(top, self.tm1, x_tn_spur - w_tank / 2, port_y,
                 lb_x + w_tank / 2, port_y + w_tank)
        y_port_ext = y_xc_tn - 6.0
        self.box(top, self.tm1, x_tp_spur - w_tank / 2, y_port_ext,
                 x_tp_spur + w_tank / 2, y_via)
        self.box(top, self.tm1, x_tn_spur - w_tank / 2, y_port_ext,
                 x_tn_spur + w_tank / 2, y_via)
        self.pin_tm1(top, x_tp_spur, y_port_ext + 0.5, "tp")
        self.pin_tm1(top, x_tn_spur, y_port_ext + 0.5, "tn")
        # CT / vdd: only between inductor and above MIM Y (never beside MIM TM1 plates)
        # MIM plates are ~27 µm tall; keep CT strap for y > y_port_ext only up to coil,
        # and place MIMs far outboard so plate X clears |x|≥ w_ct/2 + TM1.b.
        j_tank = I_TAIL / w_tank
        j_ct = I_TAIL / w_ct
        self.say(f"EM dens [HAND]: tank TM1 {w_tank} µm → J={j_tank:.2f} mA/µm "
                 f"(limit {EM_TM1}); CT {w_ct} µm → J={j_ct:.2f} (limit {EM_TM1})")

        # --- fixed MIMs + rfx (outboard: TM1 plate must not touch CT) ---
        mim = self.pcell("rfcmim", {"w": "16.0u", "l": "16.0u", "wfeed": "5.0u"})
        mloc = self.ly.cell(mim).bbox().to_dtype(self.ly.dbu)
        y_mim = y_port_ext - (mloc.top - mloc.bottom) - 8.0
        # place origin so plate right edge of left MIM ≤ -w_ct/2 - 2.0
        # plate local ~ (0.36..15.64); enclosure bbox mloc
        x_mim_l = -w_ct / 2 - 2.0 - mloc.right
        x_mim_r = w_ct / 2 + 2.0 - mloc.left
        bb_xf1, _ = self.place(top, mim, x_mim_l, y_mim)
        bb_xf2, _ = self.place(top, mim, x_mim_r, y_mim)
        self.say(f"MIM L {bb_xf1}; MIM R {bb_xf2} (clear of CT |x|<{w_ct/2})")
        # top plate (TM1) → tank straps (jog outboard, not across CT)
        self.box(top, self.tm1, bb_xf1.right - 3.0, bb_xf1.bottom + 5.0,
                 x_tp_spur + w_tank / 2, bb_xf1.bottom + 9.0)
        self.box(top, self.tm1, x_tp_spur - w_tank / 2, bb_xf1.bottom + 5.0,
                 x_tp_spur + w_tank / 2, y_port_ext + 1.0)
        self.box(top, self.tm1, x_tn_spur - w_tank / 2, bb_xf2.bottom + 5.0,
                 bb_xf2.left + 3.0, bb_xf2.bottom + 9.0)
        self.box(top, self.tm1, x_tn_spur - w_tank / 2, bb_xf2.bottom + 5.0,
                 x_tn_spur + w_tank / 2, y_port_ext + 1.0)

        # CT strap after MIMs placed: only above MIM top (clear of plates)
        y_ct_bot = max(bb_xf1.top, bb_xf2.top) + 2.0  # ≥ TM1.b above MIM
        self.box(top, self.tm1, -w_ct / 2, y_ct_bot, w_ct / 2, 2.0)
        self.pin_tm1(top, 0.0, y_ct_bot + 0.5, "ct")
        self.pin_tm1(top, 0.0, y_ct_bot + 3.0, "vdd")
        # bottom (M1 pin south of rfcmim) → fx
        y_fx = min(bb_xf1.bottom, bb_xf2.bottom) - 0.5
        self.box(top, self.m1, bb_xf1.left + 1.0, y_fx - 0.5,
                 bb_xf1.right - 1.0, bb_xf1.bottom + 0.2)
        self.box(top, self.m1, bb_xf2.left + 1.0, y_fx - 0.5,
                 bb_xf2.right - 1.0, bb_xf2.bottom + 0.2)
        self.box(top, self.m1, bb_xf1.left + 1.0, y_fx - 0.5,
                 bb_xf2.right - 1.0, y_fx - 0.1)

        rh = self.pcell("rhigh", {
            "w": "2.0u", "l": "15.2u", "Calculate": "R", "guardRingType": "none",
        })
        bb_r, _ = self.place(top, rh, -1.0, y_fx - 20.0)
        self.box(top, self.m1, -0.5, y_fx - 0.5, 0.5, bb_r.top + 0.2)
        self.box(top, self.m1, bb_r.left, bb_r.bottom - 1.5, bb_r.right, bb_r.bottom)
        # gnd pin + strap to dummy gnd rail (not to tail)
        self.pin_m1(top, 0.0, bb_r.bottom - 1.2, "gnd")
        # gnd spine: resistor up to y_gnd_d, then outboard to ptap (stay at x=0
        # only below XC so we do not hit tank M1)
        self.box(top, self.m1, -0.4, bb_r.bottom - 1.5, 0.4, y_gnd_d + 0.35)
        self.box(top, self.m1, ring_x0, y_gnd_d, 0.4, y_gnd_d + 0.40)
        self.box(top, self.m1, -0.4, y_gnd_d, ring_x1, y_gnd_d + 0.40)

        bb = top.bbox().to_dtype(self.ly.dbu)
        area = bb.width() * bb.height() * 1e-6
        share = 100.0 * area / 0.30
        self.say(f"vco_core_tank bbox {bb}")
        self.say(f"area {area:.4f} mm² = {share:.1f} % of ≤ 0.30 mm² island [SCH layout]")

        gds = os.path.join(OUT, "vco_core_tank.gds")
        self.ly.write(gds)
        with open(gds, "rb") as fi, gzip.open(gds + ".gz", "wb") as fo:
            shutil.copyfileobj(fi, fo)
        self.say(f"wrote {gds} ({os.path.getsize(gds)} bytes)")
        self.say(f"wrote {gds}.gz")

        # LVS spice (inductor black-box; dummies present)
        sp = os.path.join(OUT, "vco_core_tank.spice")
        open(sp, "w").write("""* P2.7.2b LVS netlist — vco_core_tank [SCH]
* Core from vco_core.sch; inductor black-box (EM metal); CT shorted to vdd.
.subckt l2n0 p n ct
* empty — layout is metal geometry only
.ends
.subckt vco_core_tank tp tn tail ct vdd gnd
Xm1 tp tn tail gnd sg13_lv_nmos w=32u l=0.13u ng=8 m=1
Xm2 tn tp tail gnd sg13_lv_nmos w=32u l=0.13u ng=8 m=1
Xxf1 tp fx gnd cap_rfcmim w=1.600000e-05 l=1.600000e-05 wfeed=5.0e-6 m=1
Xxf2 tn fx gnd cap_rfcmim w=1.600000e-05 l=1.600000e-05 wfeed=5.0e-6 m=1
rfx fx gnd 200000.0
xl tp tn ct l2n0
* ct ≡ vdd (centre-tap supply)
Rct_vdd ct vdd 0.001
.ends
.end
""")
        self.say(f"wrote {sp}")

        summary = os.path.join(OUT, "summary_build.txt")
        with open(summary, "w") as fh:
            fh.write("# P2.7.2b vco_core_tank build\n\n")
            fh.write("PDK a49358cc; container iic-osic-tools:2026.10.\n")
            fh.write(f"Inductor: `{IND_GDS}` (via-fixed TV2 arrays).\n\n")
            fh.write("\n".join(self.log) + "\n")
        self.say(f"wrote {summary}")
        return gds, area, bb


def main():
    b = B()
    b.say("# P2.7.2b — building vco_core_tank\n")
    b.build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
