#!/usr/bin/env python3
"""P2.7.2b D24 bank — parameterized cells from accepted bank_unit.

Stages (--stage):
  a) bank_cell_b0  — LSB (cmim), schematic k=0
  b) bank_cell_u   — thermometer unit (rfcmim), schematic k=5
  c) all 12 cells placed; no top routing yet (bbox check)
  d) vco_bank assembled: 5 binary + 7 thermo common-centroid + ports

Lessons carried from bank_unit / core+tank:
  - Cont on L=0.13 gate → upward poly pad clear of Activ
  - Join S/D columns via side-spur + M2 (never via on dense SD col)
  - even M1 cols = net a (tp side); odd = net b (tn side)
  - rfcmim M1 shield = TIE: MINUS on M2, M1 drop only outside shield
  - cmim if side < 7 µm else rfcmim [DS]; sch may still say cap_rfcmim
  - nmos PCell clamps ng ≤ 100; finger count checked in layout [TOOL]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

sys.path[:0] = [
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python",
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python/pycell4klayout-api/source/python",
]

import pya  # noqa: E402
import sg13g2_pycell_lib  # noqa: E402, F401

DBU = 0.001
SIZES = json.load(open(os.path.join(HERE, "cell_sizes.json")))
# Thermometer common-centroid order (indices into thermo[0..6] = cells 5..11)
# 2×4 grid: U0 U1 U2 D / U3 U4 U5 U6 ; D = grounded dummy unit cell
CENTROID_ORDER = [0, 1, 2, None, 3, 4, 5, 6]

# KLayout extract property snaps [TOOL] — keyed by schematic k
# (cmim PCell w&l; MOS Activ rounding; bypass min/round)
LVS_PROP = {
    0: {"side": 2.81, "w_sw": 10.32, "bp_w": 0.15},
    1: {"side": 3.92, "w_sw": 19.8, "bp_w": 0.15},
    2: {"side": 5.53, "w_sw": 39.12, "bp_w": 0.15},
    3: {"side": 7.87, "w_sw": 77.5, "bp_w": 0.31},
    4: {"side": 11.12, "w_sw": 154.38, "bp_w": 0.62},
    5: {"side": 15.71, "w_sw": 308.5, "bp_w": 1.25},
    6: {"side": 15.71, "w_sw": 308.5, "bp_w": 1.25},
    7: {"side": 15.71, "w_sw": 308.5, "bp_w": 1.25},
    8: {"side": 15.71, "w_sw": 308.5, "bp_w": 1.25},
    9: {"side": 15.71, "w_sw": 308.5, "bp_w": 1.25},
    10: {"side": 15.71, "w_sw": 308.5, "bp_w": 1.25},
    11: {"side": 15.71, "w_sw": 308.5, "bp_w": 1.25},
}


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
        self.m3 = self.ly.layer(30, 0)
        self.cont = self.ly.layer(6, 0)
        self.poly = self.ly.layer(5, 0)
        self.activ = self.ly.layer(1, 0)
        self.m5 = self.ly.layer(67, 0)
        self.tm1 = self.ly.layer(126, 0)
        self.tm1pin = self.ly.layer(126, 2)
        self.tm1txt = self.ly.layer(126, 25)
        self.tm2 = self.ly.layer(134, 0)
        self.tm2pin = self.ly.layer(134, 2)
        self.tm2txt = self.ly.layer(134, 25)
        self.log = []

    def say(self, s=""):
        print(s, flush=True)
        self.log.append(s)

    def pcell(self, name, params):
        decl = self.lib_ly.pcell_declaration(name)
        return self.ly.add_pcell_variant(self.lib, decl.id(), params)

    def place(self, parent, cid, x, y):
        t = pya.Trans(pya.Trans.R0, um(x), um(y))
        parent.insert(pya.CellInstArray(cid, t))
        return self.ly.cell(cid).bbox().transformed(t).to_dtype(self.ly.dbu), t

    def m1_cols(self, cid, trans):
        cell = self.ly.cell(cid)
        uniq = {}
        for s in cell.shapes(self.m1).each():
            if s.is_box():
                b = s.bbox().transformed(trans).to_dtype(self.ly.dbu)
                cx = round((b.left + b.right) / 2, 3)
                uniq[cx] = b
        return [uniq[k] for k in sorted(uniq)]

    def poly_gates(self, cid, trans):
        boxes = []
        for s in self.ly.cell(cid).shapes(self.poly).each():
            if s.is_box():
                boxes.append(s.bbox().transformed(trans).to_dtype(self.ly.dbu))
        boxes.sort(key=lambda b: b.left)
        return boxes

    def activ_top(self, cid, trans):
        top = None
        for s in self.ly.cell(cid).shapes(self.activ).each():
            if s.is_box():
                b = s.bbox().transformed(trans).to_dtype(self.ly.dbu)
                top = b.top if top is None else max(top, b.top)
        return top

    def layer_boxes(self, cid, trans, layer):
        out = []
        for s in self.ly.cell(cid).shapes(layer).each():
            if s.is_box():
                out.append(s.bbox().transformed(trans).to_dtype(self.ly.dbu))
        return out

    def pin_m1(self, cell, x, y, name):
        cell.shapes(self.m1).insert(pya.DBox(x - 0.25, y - 0.25, x + 0.25, y + 0.25))
        cell.shapes(self.m1pin).insert(pya.DBox(x - 0.2, y - 0.2, x + 0.2, y + 0.2))
        cell.shapes(self.m1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def box_m1(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m1).insert(pya.DBox(min(x0, x1), min(y0, y1),
                                             max(x0, x1), max(y0, y1)))

    def box_m2(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m2).insert(pya.DBox(min(x0, x1), min(y0, y1),
                                             max(x0, x1), max(y0, y1)))

    def box_m5(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m5).insert(pya.DBox(min(x0, x1), min(y0, y1),
                                             max(x0, x1), max(y0, y1)))

    def gate_contact(self, cell, gate_bb, activ_top, x_pin, y_pin, name):
        gx = 0.5 * (gate_bb.left + gate_bb.right)
        pad_bot = max(activ_top + 0.40, gate_bb.top + 0.20)
        pad_top = pad_bot + 0.50
        stem_half = 0.5 * (gate_bb.right - gate_bb.left)
        cell.shapes(self.poly).insert(
            pya.DBox(gx - stem_half, gate_bb.top - 0.05, gx + stem_half, pad_bot + 0.05))
        cell.shapes(self.poly).insert(
            pya.DBox(gx - 0.20, pad_bot, gx + 0.20, pad_top))
        cy0, cy1 = pad_bot + 0.16, pad_bot + 0.32
        cell.shapes(self.cont).insert(pya.DBox(gx - 0.08, cy0, gx + 0.08, cy1))
        x_jog = gx + (1.20 if x_pin > gx else -1.20)
        y_rise = pad_top + 0.30
        self.box_m1(cell, gx - 0.08, cy0, gx + 0.08, y_rise + 0.16)
        self.box_m1(cell, min(gx, x_jog) - 0.08, y_rise,
                    max(gx, x_jog) + 0.08, y_rise + 0.16)
        y_clear = pad_top + 1.8
        self.box_m1(cell, x_jog - 0.10, y_rise, x_jog + 0.10, y_clear + 0.20)
        self.box_m1(cell, min(x_jog, x_pin) - 0.10, y_clear,
                    max(x_jog, x_pin) + 0.10, y_clear + 0.20)
        yp = max(y_pin, y_clear + 0.40)
        self.box_m1(cell, x_pin - 0.25, y_clear, x_pin + 0.25, yp + 0.25)
        self.pin_m1(cell, x_pin, yp, name)

    def write_cell(self, name, cid):
        tmp = pya.Layout()
        tmp.dbu = self.ly.dbu
        tc = tmp.create_cell(name)
        tc.copy_tree(self.ly.cell(cid))
        gds = os.path.join(OUT, f"{name}.gds")
        tmp.write(gds)
        with open(gds, "rb") as fi, gzip.open(gds + ".gz", "wb") as fo:
            shutil.copyfileobj(fi, fo)
        self.say(f"wrote {gds} (+ .gz)")
        return gds

    def build_bank_cell(self, sz, name=None, pin_g="g", pin_bb="bb"):
        """One D24 bank bit: 2× MIM + series switch + 2× bypass + 2× rhigh.

        Topology matches accepted bank_unit (p272a). name defaults to
        bank_cell_b{k} or bank_cell_u{k-5}.
        """
        k = int(sz["k"])
        side = float(sz["side"])
        w_sw = float(sz["w_sw"])
        ng_req = int(sz["ng"])
        ng = min(ng_req, 100)  # PCell clamp [TOOL]
        w_bp = float(sz["bp_w"])
        ng_bp = int(sz["bp_ng"])
        kind = sz["kind"]
        if name is None:
            name = f"bank_cell_b{k}" if k < 5 else f"bank_cell_u{k - 5}"

        c = self.ly.create_cell(name)
        if kind == "cmim":
            mim = self.pcell("cmim", {
                "w": f"{side:.4f}u", "l": f"{side:.4f}u",
                "C": f"{float(sz['c_mim']):.2f}f", "Calculate": "w&l",
                "guardRingType": "none",
            })
        else:
            mim = self.pcell("rfcmim", {
                "w": f"{side:.4f}u", "l": f"{side:.4f}u", "wfeed": "5.0u",
            })

        # Switch first — pitch everything from its real bbox
        sw = self.pcell("nmos", {
            "w": f"{w_sw:.2f}u", "l": "0.13u", "ng": ng, "m": 1,
            "guardRingType": "none",
        })
        # bypass: ng not extracted; keep ng=1 when W ≤ 10 µm (avoids split extract)
        ng_bp_lay = 1 if w_bp <= 10.0 else max(1, ng_bp)
        bp = self.pcell("nmos", {
            "w": f"{max(0.15, w_bp):.4f}u", "l": "0.13u",
            "ng": ng_bp_lay, "m": 1, "guardRingType": "none",
        })
        rh = self.pcell("rhigh", {
            "w": "5.0u", "l": "60.8u", "Calculate": "R", "guardRingType": "none",
        })
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs5 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal5",
            "vn_columns": 2, "vn_rows": 2,
        })
        vs52 = self.pcell("via_stack", {
            "b_layer": "Metal2", "t_layer": "Metal5",
            "vn_columns": 2, "vn_rows": 2,
        })

        # Place: r0 | bp0 | SWITCH | bp1 | r1
        bb_sw, t_sw = self.place(c, sw, 40.0, 0.0)
        cols = self.m1_cols(sw, t_sw)
        gates = self.poly_gates(sw, t_sw)
        at_sw = self.activ_top(sw, t_sw)
        nfin = len(cols) - 1
        self.say(f"{name}: W={w_sw} ng_req={ng_req} ng_lay={nfin} "
                 f"ncols={len(cols)} kind={kind} side={side}")

        bp_local = self.ly.cell(bp).bbox().to_dtype(self.ly.dbu)
        bb_bp0, t_bp0 = self.place(
            c, bp, bb_sw.left - (bp_local.width() + 10.0) - bp_local.left, 0.0)
        bb_bp1, t_bp1 = self.place(c, bp, bb_sw.right + 10.0, 0.0)
        cols_bp0 = self.m1_cols(bp, t_bp0)
        cols_bp1 = self.m1_cols(bp, t_bp1)
        g_bp0 = self.poly_gates(bp, t_bp0)[0]
        g_bp1 = self.poly_gates(bp, t_bp1)[0]
        at_bp0 = self.activ_top(bp, t_bp0)
        at_bp1 = self.activ_top(bp, t_bp1)

        rh_local = self.ly.cell(rh).bbox().to_dtype(self.ly.dbu)
        bb_r0, _ = self.place(
            c, rh, bb_bp0.left - (rh_local.width() + 14.0) - rh_local.left, 0.0)
        bb_r1, _ = self.place(c, rh, bb_bp1.right + 14.0, 0.0)

        # MIMs above switch — leave headroom for gate / vbp straps
        mim_local = self.ly.cell(mim).bbox().to_dtype(self.ly.dbu)
        y_mim = max(bb_sw.top, bb_bp0.top, bb_bp1.top) + 18.0 - mim_local.bottom
        # centre the MIM pair over the switch
        gap = 6.0
        pair_w = 2.0 * mim_local.width() + gap
        x_m0 = 0.5 * (bb_sw.left + bb_sw.right) - 0.5 * pair_w - mim_local.left
        bb_m0, t_m0 = self.place(c, mim, x_m0, y_mim)
        bb_m1, t_m1 = self.place(c, mim, bb_m0.right + gap - mim_local.left, y_mim)

        ya, yb, y_bb = -4.0, -8.0, -14.0
        evens = cols[0::2]
        odds = cols[1::2]
        a_l, a_r = evens[0], evens[-1]
        b_l, b_r = odds[0], odds[-1]
        # M2 buses ABOVE Activ (clear of gate pad / Cont at ~at_sw+0.4..2.7):
        # only even (a) or odd (b) cols extend up — no M1 rail under device.
        y_a_bus = at_sw + 10.0
        # b uses south M2 at yb (no above-Activ b-bus)

        # even (a): rise above Activ → via → M2 a-bus (west exit)
        for col in evens:
            self.box_m1(c, col.left, col.top - 0.05, col.right, y_a_bus + 0.25)
            cx = 0.5 * (col.left + col.right)
            self.place(c, vs12, cx - 0.145, y_a_bus)
        self.box_m2(c, a_l.left - 3.0, y_a_bus - 0.15,
                    a_r.right + 0.5, y_a_bus + 0.55)

        # odd (b): drop SOUTH to yb (no above-Activ jog — would cross even M1),
        # via per col at yb → M2 b-bus. Widen drop to ≥0.28 for M1.a under via.
        for col in odds:
            cx = 0.5 * (col.left + col.right)
            self.box_m1(c, cx - 0.14, yb, cx + 0.14, col.bottom)
            self.place(c, vs12, cx - 0.145, yb)
        self.box_m2(c, b_l.left - 0.5, yb - 0.15, a_r.right + 8.0, yb + 0.55)

        # south hooks: a WEST from a-bus; b already on yb M2
        x_m2a = a_l.left - 6.0
        x_m2b = a_r.right + 8.0
        self.box_m2(c, x_m2a - 0.2, ya - 0.15, a_l.left - 2.0, y_a_bus + 0.55)
        self.box_m2(c, x_m2b - 0.2, yb - 0.15, x_m2b + 0.5, yb + 0.55)
        self.place(c, vs12, x_m2a, ya)
        # x_m2b already on b M2 bus
        self.box_m1(c, x_m2a - 0.2, ya, x_m2a + 0.5, ya + 0.35)
        self.box_m1(c, x_m2b - 0.2, yb, x_m2b + 0.5, yb + 0.35)

        # --- bp0 (a): right → a via south hook; left → bb ---
        bp0_d = cols_bp0[-1]
        self.box_m1(c, bp0_d.left, ya, bp0_d.right, bp0_d.bottom)
        self.box_m1(c, bp0_d.left, ya, x_m2a + 0.5, ya + 0.35)
        x_bb0 = cols_bp0[0].left - 2.5
        self.box_m1(c, x_bb0, cols_bp0[0].bottom - 0.05,
                    cols_bp0[0].right, cols_bp0[0].bottom + 0.25)
        self.box_m1(c, x_bb0, y_bb, x_bb0 + 0.35, cols_bp0[0].bottom)

        # --- bp1 (b): left → b; right → bb ---
        bp1_s = cols_bp1[0]
        self.box_m1(c, bp1_s.left, yb, bp1_s.right, bp1_s.bottom)
        self.box_m1(c, x_m2b - 0.2, yb, bp1_s.right, yb + 0.35)
        x_bb1 = cols_bp1[-1].right + 2.5
        self.box_m1(c, cols_bp1[-1].left, cols_bp1[-1].bottom - 0.05,
                    x_bb1 + 0.35, cols_bp1[-1].bottom + 0.25)
        self.box_m1(c, x_bb1, y_bb, x_bb1 + 0.35, cols_bp1[-1].bottom)

        # --- MIM bottoms → a / b ---
        m5_0 = self.layer_boxes(mim, t_m0, self.m5)
        m5_1 = self.layer_boxes(mim, t_m1, self.m5)
        tm_0 = self.layer_boxes(mim, t_m0, self.tm1)
        tm_1 = self.layer_boxes(mim, t_m1, self.tm1)
        # plate = largest M5; feed = rightmost M5 (rfcmim) or plate (cmim)
        def plate_and_feed(m5s):
            by_area = sorted(m5s, key=lambda b: (b.right - b.left) * (b.top - b.bottom),
                             reverse=True)
            plate = by_area[0]
            feed = max(m5s, key=lambda b: b.right)
            return plate, feed

        pl0, fd0 = plate_and_feed(m5_0)
        pl1, fd1 = plate_and_feed(m5_1)
        # landing under MIM plates; keep one continuous M2 (no 0.17 µm M2.b gap)
        y_vs = min(pl0.bottom, pl1.bottom) - 4.0

        if kind == "cmim":
            # M1→M5 via on plate; M2 riser from south hook up to landing
            mx0 = 0.5 * (pl0.left + pl0.right)
            mx1 = 0.5 * (pl1.left + pl1.right)
            bb_vs0, _ = self.place(c, vs5, mx0 - 0.35, y_vs)
            bb_vs1, _ = self.place(c, vs5, mx1 - 0.35, y_vs)
            # single M2 pour covering riser + vs5 footprint (avoids M2.b to via_stack)
            self.box_m2(c, x_m2a - 0.2, ya - 0.15, bb_vs0.right + 0.2, y_vs + 0.7)
            self.place(c, vs12, x_m2a, y_vs)
            self.box_m1(c, x_m2a - 0.2, y_vs, bb_vs0.right + 0.1, y_vs + 0.5)
            self.box_m1(c, bb_vs0.left, y_vs, bb_vs0.left + 0.4, bb_vs0.bottom)
            self.box_m5(c, bb_vs0.left, bb_vs0.top - 0.1, bb_vs0.right, pl0.bottom + 0.2)
            self.box_m2(c, min(x_m2b, bb_vs1.left) - 0.2, yb - 0.15,
                        max(x_m2b, bb_vs1.right) + 0.2, y_vs + 0.7)
            self.place(c, vs12, x_m2b, y_vs)
            self.box_m1(c, min(bb_vs1.left, x_m2b) - 0.2, y_vs,
                        max(bb_vs1.right, x_m2b) + 0.35, y_vs + 0.5)
            self.box_m1(c, bb_vs1.left, y_vs, bb_vs1.left + 0.4, bb_vs1.bottom)
            self.box_m5(c, bb_vs1.left, bb_vs1.top - 0.1, bb_vs1.right, pl1.bottom + 0.2)
        else:
            # rfcmim: M1 shield = TIE over full PCell bbox. Signal stays on M2
            # until south of both MIM bboxes; M1 only outside the shield.
            y_m1_ok = min(bb_m0.bottom, bb_m1.bottom) - 3.0
            for fd, x_hook, y_hook in (
                (fd0, x_m2a, ya),
                (fd1, x_m2b, yb),
            ):
                fx = 0.5 * (fd.left + fd.right)
                fy = 0.5 * (fd.bottom + fd.top)
                self.box_m5(c, fx - 1.0, fy - 1.0, fx + 1.0, fy + 1.0)
                self.place(c, vs52, fx - 0.05, fy - 0.05)
                self.box_m2(c, fx - 0.35, fy - 0.35, fx + 0.35, fy + 0.35)
                # M2 down past shield, then to hook (still M2)
                self.box_m2(c, fx - 0.35, y_m1_ok - 0.35, fx + 0.35, fy + 0.35)
                self.box_m2(c, min(fx, x_hook) - 0.35, y_m1_ok - 0.35,
                            max(fx, x_hook) + 0.35, y_m1_ok + 0.55)
                self.box_m2(c, x_hook - 0.35, min(y_hook, y_m1_ok) - 0.15,
                            x_hook + 0.35, max(y_hook, y_m1_ok) + 0.55)
            # ensure south hooks have M1 only at ya/yb (already placed); no new
            # M1 under MIM bbox.
            self.say('rfcmim TIE: PCell shield extracts as gnd — no hand M1 strap')

        # --- rhigh: top → a/b south hooks via M2; bottom → bb ---
        x_top0, x_bot0 = bb_r0.right + 1.5, bb_r0.left - 7.0
        x_top1, x_bot1 = bb_r1.left - 1.5, bb_r1.right + 7.0
        for bb_r, y_rail, x_land, x_top in (
            (bb_r0, ya, x_m2a, x_top0),
            (bb_r1, yb, x_m2b, x_top1),
        ):
            xt = bb_r.left + 1.5
            self.box_m1(c, xt, bb_r.top - 0.3, xt + 0.6, bb_r.top + 0.4)
            self.place(c, vs12, xt, bb_r.top - 0.1)
            self.box_m2(c, min(xt, x_top) - 0.2, bb_r.top - 0.3,
                        max(xt, x_top) + 0.5, bb_r.top + 0.5)
            self.box_m2(c, x_top - 0.2, y_rail - 0.15, x_top + 0.5, bb_r.top + 0.5)
            self.box_m2(c, min(x_top, x_land) - 0.2, y_rail - 0.15,
                        max(x_top, x_land) + 0.5, y_rail + 0.55)
            self.place(c, vs12, x_land, y_rail)
        for bb_r, x_bot in ((bb_r0, x_bot0), (bb_r1, x_bot1)):
            xb = bb_r.left + 1.5
            self.box_m1(c, xb, bb_r.bottom - 0.5, xb + 0.6, bb_r.bottom + 0.3)
            self.place(c, vs12, xb, bb_r.bottom - 0.1)
            self.box_m2(c, min(xb, x_bot) - 0.2, bb_r.bottom - 0.3,
                        max(xb, x_bot) + 0.5, bb_r.bottom + 0.5)
            self.box_m2(c, x_bot - 0.2, y_bb - 0.15, x_bot + 0.5, bb_r.bottom + 0.5)
            self.place(c, vs12, x_bot, y_bb)
        for xvia in (x_bb0, x_bb1):
            self.place(c, vs12, xvia, y_bb)
        self.box_m2(c, x_bot0 - 0.2, y_bb - 0.1, x_bot1 + 0.5, y_bb + 0.5)
        self.box_m1(c, x_bb0, y_bb - 2.0, x_bb0 + 0.35, y_bb + 0.4)
        self.pin_m1(c, x_bb0 + 0.17, y_bb - 1.8, pin_bb)

        # --- gates: poly strap + Cont ONLY west of device (no Cont on finger) ---
        # Cont on finger pad shorts to upward SD M1 used for a/b M2 buses.
        g0, g_last = gates[0], gates[-1]
        y_strap0, y_strap1 = at_sw + 0.08, at_sw + 0.55
        c.shapes(self.poly).insert(pya.DBox(
            g0.left, y_strap0, g_last.right, y_strap1))
        x_gpad = bb_sw.left - 8.0
        c.shapes(self.poly).insert(pya.DBox(
            x_gpad - 0.20, y_strap0, g0.left + 0.05, y_strap1))
        c.shapes(self.poly).insert(pya.DBox(
            x_gpad - 0.20, y_strap0, x_gpad + 0.20, y_strap0 + 0.50))
        cy0, cy1 = y_strap0 + 0.16, y_strap0 + 0.32
        c.shapes(self.cont).insert(pya.DBox(x_gpad - 0.08, cy0, x_gpad + 0.08, cy1))
        y_g = at_sw + 8.0
        self.box_m1(c, x_gpad - 0.08, cy0, x_gpad + 0.08, y_g + 0.25)
        self.pin_m1(c, x_gpad, y_g, pin_g)

        # vbp above MIM stacks
        y_vbp = max(bb_m0.top, bb_m1.top) + 4.0
        self.gate_contact(c, g_bp0, at_bp0, bb_bp0.left - 6.0, y_vbp, "vbp")
        self.gate_contact(c, g_bp1, at_bp1, bb_bp1.right + 6.0, y_vbp, "vbp")
        self.place(c, vs12, bb_bp0.left - 6.2, y_vbp)
        self.place(c, vs12, bb_bp1.right + 5.8, y_vbp)
        self.box_m2(c, bb_bp0.left - 6.4, y_vbp - 0.1,
                    bb_bp1.right + 6.4, y_vbp + 0.5)

        # --- tp / tn on TM1 from top plates ---
        tw = 1.70
        for boxes, pname, side_s in ((tm_0, "tp", -1), (tm_1, "tn", +1)):
            # plate = largest TM1; prefer leftmost/rightmost feed if present
            t = max(boxes, key=lambda b: (b.right - b.left) * (b.top - b.bottom))
            x_mid = 0.5 * (t.left + t.right)
            # rfcmim has left PLUS feed — use leftmost TM1 for tp side
            if kind == "rfcmim":
                feed_tm = min(boxes, key=lambda b: b.left) if side_s < 0 \
                    else max(boxes, key=lambda b: (b.right - b.left) * (b.top - b.bottom))
                if side_s < 0:
                    x_mid = 0.5 * (feed_tm.left + feed_tm.right)
                    t = feed_tm
            x_jog = x_mid + side_s * 8.0
            y_pin = max(bb_m0.top, bb_m1.top) + 8.0
            y_bus = t.top + 2.0 if kind == "cmim" else (0.5 * (t.bottom + t.top))
            c.shapes(self.tm1).insert(pya.DBox(
                x_mid - tw * 0.5, min(t.top - 0.5, y_bus), x_mid + tw * 0.5, y_bus + tw))
            c.shapes(self.tm1).insert(pya.DBox(
                min(x_mid, x_jog) - tw * 0.5, y_bus,
                max(x_mid, x_jog) + tw * 0.5, y_bus + tw))
            c.shapes(self.tm1).insert(pya.DBox(
                x_jog - tw * 0.5, y_bus, x_jog + tw * 0.5, y_pin + tw * 0.5))
            c.shapes(self.tm1pin).insert(pya.DBox(
                x_jog - tw * 0.5, y_pin - tw * 0.5, x_jog + tw * 0.5, y_pin + tw * 0.5))
            c.shapes(self.tm1txt).insert(pya.DText(pname, pya.DTrans(x_jog, y_pin)))

        pt = self.pcell("ptap1", {"w": "0.78u", "l": "0.78u"})
        bb_pt, _ = self.place(c, pt, bb_sw.left + 2.0, -18.0)
        self.box_m1(c, bb_pt.left, bb_pt.bottom - 2.5, bb_pt.right, bb_pt.bottom + 0.2)
        # gnd only — do NOT strap to bb (bb is bias, gnd is substrate)
        self.pin_m1(c, 0.5 * (bb_pt.left + bb_pt.right), bb_pt.bottom - 2.3, "gnd")
        # rfcmim TIE: PCell shield already extracts as gnd — no hand strap

        self.say(f"  bbox {c.bbox().to_dtype(self.ly.dbu)}")
        return c.cell_index(), name

    def spice_for_cell(self, sz, name, pin_g="g", pin_bb="bb"):
        k = int(sz["k"])
        kind = sz["kind"]
        prop = LVS_PROP[k]
        side_lvs = prop["side"]
        w_sw_lvs = prop["w_sw"]
        w_bp = prop["bp_w"]
        if kind == "cmim":
            cdev = (f"Cxb tp a cap_cmim w={side_lvs}u l={side_lvs}u m=1\n"
                    f"Cxn tn b cap_cmim w={side_lvs}u l={side_lvs}u m=1")
        else:
            cdev = (f"Cxb tp a gnd rfcmim w={side_lvs}u l={side_lvs}u wfeed=5u m=1\n"
                    f"Cxn tn b gnd rfcmim w={side_lvs}u l={side_lvs}u wfeed=5u m=1")
        return (
            f"* P2.7.2b D24 {name} [SCH sizes; LVS props from extract k={k}]\n"
            f".subckt {name} tp tn {pin_g} vbp {pin_bb} gnd\n"
            f"{cdev}\n"
            f"Mms a {pin_g} b gnd sg13_lv_nmos w={w_sw_lvs}u l=0.13u\n"
            f"Rrba a {pin_bb} gnd rhigh w=5.0u l=60.8u m=1\n"
            f"Rrbb b {pin_bb} gnd rhigh w=5.0u l=60.8u m=1\n"
            f"Mbp_a a vbp {pin_bb} gnd sg13_lv_nmos w={w_bp}u l=0.13u\n"
            f"Mbp_b b vbp {pin_bb} gnd sg13_lv_nmos w={w_bp}u l=0.13u\n"
            f".ends\n"
        )

    def texts_in(self, cid, trans, layer):
        """Return [(name, x_um, y_um), ...] for text shapes in cell.

        Note: Trans.trans(Vector) skips displacement; compose Trans or use Point.
        """
        out = []
        dbu = self.ly.dbu
        for s in self.ly.cell(cid).shapes(layer).each():
            if s.is_text():
                tt = trans * pya.Trans(s.text.trans)
                out.append((s.text.string, tt.disp.x * dbu, tt.disp.y * dbu))
        return out

    def place_at_origin(self, parent, cid, x_left, y_bottom):
        """Place so cell bbox left/bottom sit at (x_left, y_bottom); no overlap."""
        local = self.ly.cell(cid).bbox().to_dtype(self.ly.dbu)
        return self.place(parent, cid, x_left - local.left, y_bottom - local.bottom)

    def rename_pin_texts(self, cid, mapping):
        """Rewrite pin text strings so dummy labels are not top-level ports."""
        for layer in (self.tm1txt, self.m1txt):
            for s in self.ly.cell(cid).shapes(layer).each():
                if s.is_text() and s.text.string in mapping:
                    t = s.text
                    t.string = mapping[s.text.string]
                    s.text = t

    def tie_dummy_pins_to_gnd(self, cid):
        """Short all pins to gnd; vias only east of the cell (avoid V1.b) [HAND].

        M1 pins → south rail (below bbox) → east → one M1↔M3 via.
        TM1 pins → east on TM1 → TM1↔M3 vias spaced ≥ 2 µm on east edge.
        Pin texts renamed to gnd (1-port LVS).
        """
        cell = self.ly.cell(cid)
        id_trans = pya.Trans(pya.Trans.R0, 0, 0)
        gnds = [(x, y) for n, x, y in self.texts_in(cid, id_trans, self.m1txt)
                if n == "gnd"]
        if not gnds:
            self.say("WARN: dummy has no gnd pin")
            return
        gx, gy = gnds[0]
        bb0 = cell.bbox().to_dtype(self.ly.dbu)
        x_east = bb0.right + 3.0
        y_rail = bb0.bottom - 2.0
        hw = 0.40
        pad = 0.80
        via_pitch = 4.0  # TM1.b ≥ 1.64 µm with tw=1.7 [DS]
        vs13 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal3",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs_tm1m3 = self.pcell("via_stack", {
            "b_layer": "Metal3", "t_layer": "TopMetal1",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs_bb = self.ly.cell(vs13).bbox().to_dtype(self.ly.dbu)

        def m3_wire(x0, y0, x1, y1):
            cell.shapes(self.m3).insert(pya.DBox(
                min(x0, x1) - hw, min(y0, y1) - hw,
                max(x0, x1) + hw, max(y0, y1) + hw))

        def place_vs13(x, y):
            self.box_m1(cell, x - pad, y - pad, x + pad, y + pad)
            cell.shapes(self.m3).insert(
                pya.DBox(x - pad, y - pad, x + pad, y + pad))
            self.place(cell, vs13, x - vs_bb.left - 0.5 * vs_bb.width(),
                       y - vs_bb.bottom - 0.5 * vs_bb.height())

        # gnd → M3 east rail (single via at gnd)
        place_vs13(gx, gy)
        m3_wire(gx, gy, x_east, gy)
        m3_wire(x_east, gy, x_east, y_rail)

        # M1 pins: jog south outside the cell, then east to one shared via
        for name, x, y in self.texts_in(cid, id_trans, self.m1txt):
            if name == "gnd":
                continue
            x_out = bb0.left - 2.0 if x < 0.5 * (bb0.left + bb0.right) \
                else bb0.right + 2.0
            # stay outside: pin → x_out at y (only if already outside activ band)
            # prefer: pin down/up to y_rail at pin x only when y already ≤ activ
            if y <= bb0.bottom + 5.0:
                self.box_m1(cell, x - hw, min(y, y_rail) - hw,
                            x + hw, max(y, y_rail) + hw)
                self.box_m1(cell, min(x, x_east) - hw, y_rail - hw,
                            max(x, x_east) + hw, y_rail + hw)
            else:
                # upper M1 pins: outboard then south on outside edge
                self.box_m1(cell, min(x, x_out) - hw, y - hw,
                            max(x, x_out) + hw, y + hw)
                self.box_m1(cell, x_out - hw, min(y, y_rail) - hw,
                            x_out + hw, max(y, y_rail) + hw)
                self.box_m1(cell, min(x_out, x_east) - hw, y_rail - hw,
                            max(x_out, x_east) + hw, y_rail + hw)
        place_vs13(x_east, y_rail)

        # TM1 pins: east on TM1, vias on east edge spaced apart
        tm1_pins = self.texts_in(cid, id_trans, self.tm1txt)
        for i, (name, x, y) in enumerate(tm1_pins):
            tw = 1.70
            y_via = y_rail + (i + 1) * via_pitch
            cell.shapes(self.tm1).insert(pya.DBox(
                min(x, x_east) - tw * 0.5, y - tw * 0.5,
                max(x, x_east) + tw * 0.5, y + tw * 0.5))
            cell.shapes(self.tm1).insert(pya.DBox(
                x_east - tw * 0.5, min(y, y_via) - tw * 0.5,
                x_east + tw * 0.5, max(y, y_via) + tw * 0.5))
            cell.shapes(self.m3).insert(
                pya.DBox(x_east - pad, y_via - pad, x_east + pad, y_via + pad))
            self.place(cell, vs_tm1m3, x_east - 0.145, y_via - 0.105)
            m3_wire(x_east, y_via, x_east, y_rail)

        self.rename_pin_texts(cid, {
            "tp": "gnd", "tn": "gnd", "vbp": "gnd",
            "xg": "gnd", "xbb": "gnd", "xtp": "gnd", "xtn": "gnd",
            "xvbp": "gnd", "g": "gnd", "bb": "gnd",
        })
        self.say("dummy pins→gnd; vias only on east corridor; texts→gnd")

    def build_bank(self):
        """Assemble vco_bank: thermo common-centroid + binary row south + buses.

        Floorplan (denser pack for ≤0.30 mm² island with core 0.1102):
          thermo 2×4 with D = grounded dummy; binary b0..b4 south.
        """
        top = self.ly.create_cell("vco_bank")
        placements = []  # (cid, trans, k, row_id)  k=-1 for dummy
        tw = 1.70  # ≥ TM1.a; space ≥ TM1.b 1.64 µm [DS]
        # Denser pack (area forecast): gap_x 2, gap_y 5.5 (≥ 2×tw + TM1.b)
        gap_x = 2.0
        gap_y = 5.5
        corridor = 4.0

        cell_ids = []
        for sz in SIZES:
            k = int(sz["k"])
            cid, _ = self.build_bank_cell(
                sz, pin_g=f"g{k}", pin_bb=f"bb{k}")
            cell_ids.append(cid)

        # Dummy = thermo unit; all pin texts labeled gnd (1-port extract).
        dum_cid, dum_name = self.build_bank_cell(
            SIZES[5], name="bank_cell_dummy", pin_g="xg", pin_bb="xbb")
        self.tie_dummy_pins_to_gnd(dum_cid)
        self.write_cell(dum_name, dum_cid)
        open(os.path.join(OUT, f"{dum_name}.spice"), "w").write(
            self.spice_dummy())

        thermo = cell_ids[5:]
        u_bb = self.ly.cell(thermo[0]).bbox().to_dtype(self.ly.dbu)
        d_bb = self.ly.cell(dum_cid).bbox().to_dtype(self.ly.dbu)
        pitch_x = max(u_bb.width(), d_bb.width()) + gap_x
        pitch_y = max(u_bb.height(), d_bb.height()) + gap_y
        self.say(
            f"centroid order "
            f"{[x if x is not None else 'D' for x in CENTROID_ORDER]}; "
            f"pitch {pitch_x:.1f}x{pitch_y:.1f} um; D=dummy→gnd; "
            f"gap_x={gap_x} gap_y={gap_y} corridor={corridor}; "
            f"binary row south; TM1 channels in row gaps")

        thermo_bbs = []
        for i, idx in enumerate(CENTROID_ORDER):
            col, row = i % 4, i // 4
            if idx is None:
                bb, t = self.place_at_origin(
                    top, dum_cid, col * pitch_x, row * pitch_y)
                thermo_bbs.append(bb)
                placements.append((dum_cid, t, -1, row))
                continue
            cid = thermo[idx]
            k = 5 + idx
            bb, t = self.place_at_origin(
                top, cid, col * pitch_x, row * pitch_y)
            thermo_bbs.append(bb)
            placements.append((cid, t, k, row))

        y_bin = max(bb.top for bb in thermo_bbs) + gap_y
        x = 0.0
        bin_row = 2
        for k in range(5):
            cid = cell_ids[k]
            bb, t = self.place_at_origin(top, cid, x, y_bin)
            placements.append((cid, t, k, bin_row))
            x = bb.right + gap_x

        pins = {n: [] for n in (
            ["tp", "tn", "vbp", "gnd"] +
            [f"g{k}" for k in range(12)] +
            [f"bb{k}" for k in range(12)])}
        pin_row = {}  # (name,x,y) → row_id for tp/tn
        for cid, t, k, row in placements:
            if k < 0:
                # dummy: only the substrate ptap gnd (lowest Y), not renamed pins
                gxy = [(x, y) for name, x, y in self.texts_in(cid, t, self.m1txt)
                       if name == "gnd"]
                if gxy:
                    pins["gnd"].append(min(gxy, key=lambda p: p[1]))
                continue
            for name, x, y in self.texts_in(cid, t, self.tm1txt):
                if name in pins:
                    pins[name].append((x, y))
                    if name in ("tp", "tn"):
                        pin_row[(name, x, y)] = row
            for name, x, y in self.texts_in(cid, t, self.m1txt):
                if name in pins:
                    pins[name].append((x, y))

        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs_tm12 = self.pcell("via_stack", {
            "b_layer": "TopMetal1", "t_layer": "TopMetal2",
            "vn_columns": 2, "vn_rows": 2,
        })
        bb0 = top.bbox().to_dtype(self.ly.dbu)
        x_west = bb0.left - corridor
        x_east = bb0.right + corridor
        tw2 = 2.0  # TM2.a min width [DS]

        def tm1_wire(x0, y0, x1, y1):
            top.shapes(self.tm1).insert(pya.DBox(
                min(x0, x1) - tw * 0.5, min(y0, y1) - tw * 0.5,
                max(x0, x1) + tw * 0.5, max(y0, y1) + tw * 0.5))

        def tm2_wire(x0, y0, x1, y1):
            top.shapes(self.tm2).insert(pya.DBox(
                min(x0, x1) - tw2 * 0.5, min(y0, y1) - tw2 * 0.5,
                max(x0, x1) + tw2 * 0.5, max(y0, y1) + tw2 * 0.5))

        # tp on TM1 west corridor; tn on TM2 east corridor (no same-layer cross)
        rows = sorted({r for *_rest, r in placements})
        row_top = {}
        for cid, t, _k, row in placements:
            bb = self.ly.cell(cid).bbox().transformed(t).to_dtype(self.ly.dbu)
            row_top[row] = max(row_top.get(row, bb.top), bb.top)

        for row in rows:
            y_ch = row_top[row] + 3.0
            tps = [(x, y) for (n, x, y), r in pin_row.items()
                   if n == "tp" and r == row]
            tns = [(x, y) for (n, x, y), r in pin_row.items()
                   if n == "tn" and r == row]
            for x, y in tps:
                tm1_wire(x, y, x, y_ch)
                tm1_wire(x, y_ch, x_west, y_ch)
            for x, y in tns:
                self.place(top, vs_tm12, x - 0.4, y - 0.4)
                tm2_wire(x, y, x, y_ch)
                tm2_wire(x, y_ch, x_east, y_ch)

        y_port = max(row_top.values()) + gap_y + 4.0
        tm1_wire(x_west, min(row_top[r] + 3.0 for r in rows), x_west, y_port)
        tm2_wire(x_east, min(row_top[r] + 3.0 for r in rows), x_east, y_port)
        x_mid = 0.5 * (bb0.left + bb0.right)
        x_port_tp, x_port_tn = x_mid - 10.0, x_mid + 10.0
        tm1_wire(x_west, y_port, x_port_tp, y_port)
        tm2_wire(x_east, y_port, x_port_tn, y_port)
        # ports on TM1 (core+tank stubs); tn via TM2→TM1 at port
        self.place(top, vs_tm12, x_port_tn - 0.4, y_port - 0.4)
        for x_port, name in ((x_port_tp, "tp"), (x_port_tn, "tn")):
            top.shapes(self.tm1).insert(pya.DBox(
                x_port - tw * 0.5, y_port - tw * 0.5,
                x_port + tw * 0.5, y_port + tw * 0.5))
            top.shapes(self.tm1pin).insert(pya.DBox(
                x_port - tw * 0.4, y_port - tw * 0.4,
                x_port + tw * 0.4, y_port + tw * 0.4))
            top.shapes(self.tm1txt).insert(
                pya.DText(name, pya.DTrans(x_port, y_port)))

        # vbp: M2 in row gaps → west corridor (never full-width at pin Y)
        if pins["vbp"]:
            for cid, t, k, row in placements:
                if k < 0:
                    continue
                y_ch = row_top[row] + 1.0
                for name, x, y in self.texts_in(cid, t, self.m1txt):
                    if name != "vbp":
                        continue
                    # via already in cell (M1↔M2); rise on M2 to gap then west
                    self.box_m2(top, x - 0.25, min(y, y_ch) - 0.1,
                                x + 0.55, max(y, y_ch) + 0.55)
                    self.box_m2(top, x_west - 0.2, y_ch - 0.15,
                                x + 0.55, y_ch + 0.55)
            self.box_m2(top, x_west - 0.2,
                        min(row_top[r] + 1.0 for r in rows) - 0.15,
                        x_west + 0.55,
                        max(row_top[r] + 1.0 for r in rows) + 0.55)
            y_vpin = min(row_top[r] + 1.0 for r in rows) - 3.0
            self.place(top, vs12, x_west, y_vpin + 2.0)
            self.pin_m1(top, x_west + 0.15, y_vpin, "vbp")

        # gnd: east M1 corridor — no verticals through the array (binary gnd
        # drop previously shorted thermo a/b M1 to gnd).
        if pins["gnd"]:
            ys = [p[1] for p in pins["gnd"]]
            x_g = x_east + 6.0
            for x, y in pins["gnd"]:
                self.box_m1(top, min(x, x_g) - 0.15, y - 0.2,
                            max(x, x_g) + 0.35, y + 0.4)
            self.box_m1(top, x_g - 0.15, min(ys) - 0.2,
                        x_g + 0.35, max(ys) + 0.4)
            self.pin_m1(top, x_g, min(ys) - 3.0, "gnd")
            self.box_m1(top, x_g - 0.15, min(ys) - 3.2,
                        x_g + 0.35, min(ys) + 0.4)

        for k in range(12):
            for net in (f"g{k}", f"bb{k}"):
                if not pins[net]:
                    self.say(f"WARN: missing {net}")
        self.say(f"pins tp={len(pins['tp'])} tn={len(pins['tn'])} "
                 f"vbp={len(pins['vbp'])} gnd={len(pins['gnd'])}")

        bb = top.bbox().to_dtype(self.ly.dbu)
        area = (bb.width() * bb.height()) * 1e-6
        self.say(f"vco_bank bbox {bb} area_mm2={area:.4f} "
                 f"({100.0 * area / 0.30:.1f}% of 0.30); "
                 f"with core 0.1102 → {area + 0.1102:.4f}")
        return top.cell_index()

    def spice_dummy(self):
        """Centroid dummy: 1-port (gnd); all device terminals → gnd [SCH]."""
        prop = LVS_PROP[5]
        side_lvs = prop["side"]
        w_sw_lvs = prop["w_sw"]
        w_bp = prop["bp_w"]
        return (
            "* P2.7.2b bank_cell_dummy — thermo unit, all terminals → gnd\n"
            ".subckt bank_cell_dummy gnd\n"
            f"Cxb gnd adum gnd rfcmim w={side_lvs}u l={side_lvs}u wfeed=5u m=1\n"
            f"Cxn gnd bdum gnd rfcmim w={side_lvs}u l={side_lvs}u wfeed=5u m=1\n"
            f"Mms adum gnd bdum gnd sg13_lv_nmos w={w_sw_lvs}u l=0.13u\n"
            f"Rrba adum gnd gnd rhigh w=5.0u l=60.8u m=1\n"
            f"Rrbb bdum gnd gnd rhigh w=5.0u l=60.8u m=1\n"
            f"Mbp_a adum gnd gnd gnd sg13_lv_nmos w={w_bp}u l=0.13u\n"
            f"Mbp_b bdum gnd gnd gnd sg13_lv_nmos w={w_bp}u l=0.13u\n"
            ".ends\n"
        )

    def spice_bank(self):
        lines = [
            "* P2.7.2b D24 vco_bank [SCH sizes; layout kind per cell]",
            ".subckt vco_bank tp tn vbp gnd "
            + " ".join(f"g{k} bb{k}" for k in range(12)),
        ]
        for sz in SIZES:
            k = int(sz["k"])
            kind = sz["kind"]
            prop = LVS_PROP[k]
            side_lvs = prop["side"]
            w_sw_lvs = prop["w_sw"]
            w_bp = prop["bp_w"]
            a, b = f"a{k}", f"b{k}"
            if kind == "cmim":
                lines.append(
                    f"Cxb{k}p tp {a} cap_cmim w={side_lvs}u l={side_lvs}u m=1")
                lines.append(
                    f"Cxb{k}n tn {b} cap_cmim w={side_lvs}u l={side_lvs}u m=1")
            else:
                lines.append(
                    f"Cxb{k}p tp {a} gnd rfcmim w={side_lvs}u l={side_lvs}u "
                    f"wfeed=5u m=1")
                lines.append(
                    f"Cxb{k}n tn {b} gnd rfcmim w={side_lvs}u l={side_lvs}u "
                    f"wfeed=5u m=1")
            lines.append(
                f"Mms{k} {a} g{k} {b} gnd sg13_lv_nmos w={w_sw_lvs}u l=0.13u")
            lines.append(
                f"Rrba{k} {a} bb{k} gnd rhigh w=5.0u l=60.8u m=1")
            lines.append(
                f"Rrbb{k} {b} bb{k} gnd rhigh w=5.0u l=60.8u m=1")
            lines.append(
                f"Mbp_a{k} {a} vbp bb{k} gnd sg13_lv_nmos w={w_bp}u l=0.13u")
            lines.append(
                f"Mbp_b{k} {b} vbp bb{k} gnd sg13_lv_nmos w={w_bp}u l=0.13u")
        # Centroid dummy (slot D): same thermo sizes, all nets → gnd
        prop = LVS_PROP[5]
        side_lvs = prop["side"]
        w_sw_lvs = prop["w_sw"]
        w_bp = prop["bp_w"]
        lines.append(
            f"Cxbdump gnd adum gnd rfcmim w={side_lvs}u l={side_lvs}u "
            f"wfeed=5u m=1")
        lines.append(
            f"Cxbdumn gnd bdum gnd rfcmim w={side_lvs}u l={side_lvs}u "
            f"wfeed=5u m=1")
        lines.append(
            f"Mmsdum adum gnd bdum gnd sg13_lv_nmos w={w_sw_lvs}u l=0.13u")
        lines.append("Rrbadum adum gnd gnd rhigh w=5.0u l=60.8u m=1")
        lines.append("Rbbdum bdum gnd gnd rhigh w=5.0u l=60.8u m=1")
        lines.append(
            f"Mbp_adum adum gnd gnd gnd sg13_lv_nmos w={w_bp}u l=0.13u")
        lines.append(
            f"Mbp_bdum bdum gnd gnd gnd sg13_lv_nmos w={w_bp}u l=0.13u")
        lines.append(".ends")
        return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="a", choices=list("abcd"))
    args = ap.parse_args()
    b = B()
    b.say(f"# P2.7.2b D24 bank build stage {args.stage}\n")

    if args.stage == "a":
        sz = SIZES[0]
        cid, name = b.build_bank_cell(sz, name="bank_cell_b0")
        b.write_cell(name, cid)
        open(os.path.join(OUT, f"{name}.spice"), "w").write(
            b.spice_for_cell(sz, name))
    elif args.stage == "b":
        sz = SIZES[5]
        cid, name = b.build_bank_cell(sz, name="bank_cell_u")
        b.write_cell(name, cid)
        open(os.path.join(OUT, f"{name}.spice"), "w").write(
            b.spice_for_cell(sz, name))
    elif args.stage == "c":
        # build all cells as separate GDS for per-cell LVS if needed
        for sz in SIZES:
            cid, name = b.build_bank_cell(sz)
            b.write_cell(name, cid)
            open(os.path.join(OUT, f"{name}.spice"), "w").write(
                b.spice_for_cell(sz, name))
    else:
        cid = b.build_bank()
        b.write_cell("vco_bank", cid)
        open(os.path.join(OUT, "vco_bank.spice"), "w").write(b.spice_bank())

    open(os.path.join(OUT, f"summary_build_{args.stage}.txt"), "w").write(
        "\n".join(b.log) + "\n")
    b.say("done")


if __name__ == "__main__":
    main()
