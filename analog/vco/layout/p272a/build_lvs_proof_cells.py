#!/usr/bin/env python3
"""P2.7.2a2 — LVS proof cells with PDK via_stack / ntap1 / ptap1.

dac_unit: 2× pmos + hand NW n+ tap to vdd. Gate Cont on upward poly pad
(Cont 0.16 > L=0.13; pad clears Activ for Gat.d / Cnt.b).
bank_unit: 2× cmim + via_stack(M1→M5) + nmos switch W=10.32 (ng=2; max
finger W=10.0) + 2× rhigh + 2× bypass + ptap1. No hand via arrays.

Cause of earlier bank_unit short (record in p27-layout-notes):
- Cont on L=0.13 gate poly overhangs onto Activ → G↔D/S short.
- Gate M1 landing wider than the L=0.13 S/D gap → G shorted to D/S.
- Hand via / strap M1 crossing a/b rails → bb|g|vbp merge; W=10.32 vanished.
- PCell w=10.32u with ng=1 clamps to Wmin=0.15 (max finger 10.0 µm).
Fix: upward poly pads, PDK via_stack, separate a/b y-levels, ng=2.
"""
from __future__ import annotations

import gzip
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


def um(x):
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
        self.cont = self.ly.layer(6, 0)
        self.poly = self.ly.layer(5, 0)
        self.activ = self.ly.layer(1, 0)
        self.nsd = self.ly.layer(7, 0)
        self.psd = self.ly.layer(14, 0)
        self.nw = self.ly.layer(31, 0)
        self.nbulay = self.ly.layer(32, 0)
        self.m5 = self.ly.layer(67, 0)
        self.tm1 = self.ly.layer(126, 0)
        self.tm1pin = self.ly.layer(126, 2)
        self.tm1txt = self.ly.layer(126, 25)
        self.log = []

    def say(self, s=""):
        print(s)
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
        """Individual gate poly boxes (one per finger), sorted by x."""
        cell = self.ly.cell(cid)
        boxes = []
        for s in cell.shapes(self.poly).each():
            if s.is_box():
                boxes.append(s.bbox().transformed(trans).to_dtype(self.ly.dbu))
        boxes.sort(key=lambda b: b.left)
        return boxes

    def activ_top(self, cid, trans):
        """True Activ top (min-W devices use short poly extension ≠ 0.18)."""
        cell = self.ly.cell(cid)
        top = None
        for s in cell.shapes(self.activ).each():
            if s.is_box():
                b = s.bbox().transformed(trans).to_dtype(self.ly.dbu)
                top = b.top if top is None else max(top, b.top)
        return top

    def pin_m1(self, cell, x, y, name):
        cell.shapes(self.m1).insert(pya.DBox(x - 0.25, y - 0.25, x + 0.25, y + 0.25))
        cell.shapes(self.m1pin).insert(pya.DBox(x - 0.2, y - 0.2, x + 0.2, y + 0.2))
        cell.shapes(self.m1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def pin_tm1(self, cell, x, y, name):
        cell.shapes(self.tm1).insert(pya.DBox(x - 0.4, y - 0.4, x + 0.4, y + 0.4))
        cell.shapes(self.tm1pin).insert(pya.DBox(x - 0.3, y - 0.3, x + 0.3, y + 0.3))
        cell.shapes(self.tm1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def box_m1(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m1).insert(pya.DBox(min(x0, x1), min(y0, y1),
                                             max(x0, x1), max(y0, y1)))

    def box_m5(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m5).insert(pya.DBox(min(x0, x1), min(y0, y1),
                                             max(x0, x1), max(y0, y1)))

    def gate_contact(self, cell, gate_bb, activ_top, x_pin, y_pin, name):
        """Upward poly stem + pad ≥ Cont; Cont clear of Activ (Gat.d / Cnt.b).

        Cont is 0.16 µm; L=0.13 gate is narrower — Cont on the finger overhangs
        onto Activ and shorts G↔D/S. Pad sits above real Activ top (≥0.20 µm).
        M1 jogs sideways in the clear band so it never runs between S/D M1 cols.
        """
        gx = 0.5 * (gate_bb.left + gate_bb.right)
        # pad well above Activ (Gat.d=0.07; min-W Activ top ≠ poly_top−0.18)
        pad_bot = max(activ_top + 0.25, gate_bb.top + 0.10)
        pad_top = pad_bot + 0.50
        stem_half = 0.5 * (gate_bb.right - gate_bb.left)
        cell.shapes(self.poly).insert(
            pya.DBox(gx - stem_half, gate_bb.top - 0.05, gx + stem_half, pad_bot + 0.05))
        # pad only as wide as needed for Cont+enc; keep Gat.d to Activ in Y
        cell.shapes(self.poly).insert(
            pya.DBox(gx - 0.20, pad_bot, gx + 0.20, pad_top))
        cy0, cy1 = pad_bot + 0.16, pad_bot + 0.32
        cell.shapes(self.cont).insert(pya.DBox(gx - 0.08, cy0, gx + 0.08, cy1))
        # Cont M1 only over Cont; rise above pad; then jog (never span X over S/D M1)
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

    def nw_tap_to_m1(self, cell, x0, y0, x1, y1):
        """Hand n+ / nBuLay in NW → M1 (match ntap1 stack for bulk tie)."""
        cell.shapes(self.activ).insert(pya.DBox(x0, y0, x1, y1))
        cell.shapes(self.nsd).insert(pya.DBox(x0 - 0.05, y0 - 0.05, x1 + 0.05, y1 + 0.05))
        cell.shapes(self.nbulay).insert(pya.DBox(x0 - 0.1, y0 - 0.1, x1 + 0.1, y1 + 0.1))
        cell.shapes(self.nw).insert(pya.DBox(x0 - 0.3, y0 - 0.3, x1 + 0.3, y1 + 0.3))
        for cx in (x0 + 0.12, x1 - 0.28):
            for cy in (y0 + 0.12, y1 - 0.28):
                cell.shapes(self.cont).insert(pya.DBox(cx, cy, cx + 0.16, cy + 0.16))
        self.box_m1(cell, x0, y0, x1, y1)

    def build_dac_unit(self):
        c = self.ly.create_cell("dac_unit")
        mdb = self.pcell("pmos", {"w": "4.0u", "l": "2.0u", "ng": 1, "m": 1,
                                 "guardRingType": "none"})
        msw = self.pcell("pmos", {"w": "4.0u", "l": "0.13u", "ng": 1, "m": 1,
                                 "guardRingType": "none"})
        # space FETs far apart so gate M1 stubs clear xraw / xd (M1.b)
        bb0, t0 = self.place(c, mdb, 0, 0)
        bb1, t1 = self.place(c, msw, bb0.right + 20.0, 0)
        cols0 = self.m1_cols(mdb, t0)
        cols1 = self.m1_cols(msw, t1)
        g0 = self.poly_gates(mdb, t0)[0]
        g1 = self.poly_gates(msw, t1)[0]
        at0 = self.activ_top(mdb, t0)
        at1 = self.activ_top(msw, t1)
        d_mdb, s_mdb = cols0[0], cols0[1]
        d_msw, s_msw = cols1[0], cols1[1]

        y_vdd = max(bb0.top, bb1.top) + 5.0
        self.box_m1(c, s_mdb.left, s_mdb.top, s_mdb.right, y_vdd + 0.4)
        self.box_m1(c, s_mdb.left - 0.1, y_vdd, s_mdb.right + 0.1, y_vdd + 0.4)
        self.pin_m1(c, 0.5 * (s_mdb.left + s_mdb.right), y_vdd + 0.2, "vdd")

        # NW n+ tap → vdd; M1 of tap must overlap the vdd rail (no 0.12 µm gap)
        tx0 = s_mdb.right + 4.0
        ty0 = y_vdd - 0.4
        self.nw_tap_to_m1(c, tx0, ty0, tx0 + 0.78, ty0 + 0.78)
        self.box_m1(c, s_mdb.right, y_vdd, tx0 + 0.78, y_vdd + 0.4)
        self.box_m1(c, tx0, ty0, tx0 + 0.78, y_vdd + 0.4)
        c.shapes(self.nw).insert(pya.DBox(
            bb0.left - 0.6, min(bb0.bottom, bb1.bottom) - 0.6,
            max(bb1.right, tx0 + 0.78) + 0.6,
            max(bb0.top, bb1.top, ty0 + 0.78) + 0.6))

        y_xd = min(bb0.bottom, bb1.bottom) - 3.0
        self.box_m1(c, d_mdb.left, y_xd, s_msw.right, y_xd + 0.4)
        self.box_m1(c, d_mdb.left, y_xd, d_mdb.right, d_mdb.bottom)
        self.box_m1(c, s_msw.left, y_xd, s_msw.right, s_msw.bottom)
        self.pin_m1(c, 0.5 * (d_mdb.right + s_msw.left), y_xd + 0.2, "xd")

        # xraw: exit LEFT inside the drain M1 height (≤ Activ top), then up clear of pad
        y_xr = max(at1 + 10.0, bb1.top + 8.0)
        x_xr = d_msw.left - 3.0
        y_exit = min(d_msw.top - 0.05, at1 - 0.20)
        self.box_m1(c, x_xr, y_exit - 0.20, d_msw.right, y_exit)
        self.box_m1(c, x_xr, y_exit - 0.20, x_xr + 0.35, y_xr + 0.4)
        self.pin_m1(c, x_xr + 0.17, y_xr + 0.2, "xraw")

        self.gate_contact(c, g0, at0, bb0.left - 10.0, at0 + 10.0, "pbias")
        self.gate_contact(c, g1, at1, bb1.right + 10.0, at1 + 10.0, "code")

        self.say(f"dac_unit bbox {c.bbox().to_dtype(self.ly.dbu)}")
        return c.cell_index()

    def build_bank_unit(self):
        c = self.ly.create_cell("bank_unit")
        m2 = self.ly.layer(10, 0)
        mim = self.pcell("cmim", {"w": "2.88u", "l": "2.88u", "C": "12.4f",
                                 "Calculate": "w&l", "guardRingType": "none"})
        # MIMs high; switch pair low-left; bypass right; rhigh far right
        mim_bb0, t_m0 = self.place(c, mim, 0, 40)
        mim_bb1, t_m1 = self.place(c, mim, mim_bb0.right + 14.0, 40)
        cell_m = self.ly.cell(mim)

        def layer_boxes(tr, layer):
            out = []
            for s in cell_m.shapes(layer).each():
                if s.is_box():
                    out.append(s.bbox().transformed(tr).to_dtype(self.ly.dbu))
            return out

        m5_0 = layer_boxes(t_m0, self.m5)
        m5_1 = layer_boxes(t_m1, self.m5)
        tm_0 = layer_boxes(t_m0, self.tm1)
        tm_1 = layer_boxes(t_m1, self.tm1)

        # max finger W=10.0 µm → two parallel 5.16 µm (combine → W=10.32)
        sw = self.pcell("nmos", {"w": "5.16u", "l": "0.13u", "ng": 1, "m": 1,
                                 "guardRingType": "none"})
        bb_s0, t_s0 = self.place(c, sw, 20.0, 0)
        bb_s1, t_s1 = self.place(c, sw, bb_s0.right + 8.0, 0)
        cols0 = self.m1_cols(sw, t_s0)
        cols1 = self.m1_cols(sw, t_s1)
        g_s0 = self.poly_gates(sw, t_s0)[0]
        g_s1 = self.poly_gates(sw, t_s1)[0]
        at_s = self.activ_top(sw, t_s0)
        a0, b0 = cols0[0], cols0[1]
        a1, b1 = cols1[0], cols1[1]

        # bypass: bp0 (net a) left of switches; bp1 (net b) right — no M1 span across
        bp = self.pcell("nmos", {"w": "0.15u", "l": "0.13u", "ng": 1, "m": 1,
                                 "guardRingType": "none"})
        bb_bp0, t_bp0 = self.place(c, bp, 2.0, 0)
        bb_bp1, t_bp1 = self.place(c, bp, bb_s1.right + 12.0, 0)
        cols_bp0 = self.m1_cols(bp, t_bp0)
        cols_bp1 = self.m1_cols(bp, t_bp1)
        g_bp0 = self.poly_gates(bp, t_bp0)[0]
        g_bp1 = self.poly_gates(bp, t_bp1)[0]
        at_bp0 = self.activ_top(bp, t_bp0)
        at_bp1 = self.activ_top(bp, t_bp1)

        # r0 on a (left), r1 on b (right) — no M1 span across switch S/D
        rh = self.pcell("rhigh", {"w": "5.0u", "l": "60.8u", "Calculate": "R",
                                 "guardRingType": "none"})
        bb_r0, _ = self.place(c, rh, -18.0, 0)
        bb_r1, _ = self.place(c, rh, max(mim_bb1.right, bb_bp1.right) + 12.0, 0)

        vs5 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal5",
            "vn_columns": 2, "vn_rows": 2,
        })
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        mx0 = 0.5 * (m5_0[0].left + m5_0[0].right) if m5_0 else 0.5 * (mim_bb0.left + mim_bb0.right)
        mx1 = 0.5 * (m5_1[0].left + m5_1[0].right) if m5_1 else 0.5 * (mim_bb1.left + mim_bb1.right)
        y_vs = 22.0
        bb_vs0, _ = self.place(c, vs5, mx0 - 0.35, y_vs)
        bb_vs1, _ = self.place(c, vs5, mx1 - 0.35, y_vs)

        ya, yb, y_bb = -3.0, -6.0, -12.0

        # --- switch a cols: local drops + M2 bridge (never span M1 across b cols) ---
        for col in (a0, a1):
            self.box_m1(c, col.left, ya, col.right, col.bottom)
            self.box_m1(c, col.left, -1.8, col.right, col.bottom)
        self.box_m1(c, a0.left - 2.0, ya, a0.right, ya + 0.35)
        self.place(c, vs12, a0.left, -1.8)
        self.place(c, vs12, a1.left, -1.8)
        c.shapes(m2).insert(pya.DBox(a0.left, -1.8, a1.right, -1.4))

        # --- switch b cols: drops + bottom bus below a ---
        for col in (b0, b1):
            self.box_m1(c, col.left, yb, col.right, col.bottom)
            self.box_m1(c, col.left, y_bb + 2.0, col.right, yb + 0.35)
        self.box_m1(c, b0.left, y_bb + 2.0, b1.right + 2.0, y_bb + 2.35)

        # --- via_stack M1→M5 + MIM bottoms ---
        # a → vs0: up between bp0 and switch, then left (never across bp0 bb col at ya)
        self.box_m1(c, a0.left - 2.0, ya, a0.left - 1.6, y_vs + 0.4)
        self.box_m1(c, bb_vs0.left, y_vs, a0.left - 1.6, y_vs + 0.4)
        self.box_m1(c, bb_vs0.left, y_vs, bb_vs0.left + 0.4, bb_vs0.bottom)
        if m5_0:
            self.box_m5(c, bb_vs0.left, bb_vs0.top - 0.1,
                        bb_vs0.right, m5_0[0].bottom + 0.2)
        # b → vs1: up on right of switches
        self.box_m1(c, b1.right + 1.6, y_bb + 2.0, b1.right + 2.0, y_vs + 0.4)
        self.box_m1(c, bb_vs1.left, y_vs, b1.right + 2.0, y_vs + 0.4)
        self.box_m1(c, bb_vs1.left, y_vs, bb_vs1.left + 0.4, bb_vs1.bottom)
        if m5_1:
            self.box_m5(c, bb_vs1.left, bb_vs1.top - 0.1,
                        bb_vs1.right, m5_1[0].bottom + 0.2)

        # --- bypass: drain faces the switch bus; far col → bb (no M1 through S/D gap) ---
        # bp0 (left of sw): right col → a, left col → bb
        self.box_m1(c, cols_bp0[1].left, ya, cols_bp0[1].right, cols_bp0[1].bottom)
        self.box_m1(c, cols_bp0[1].left, ya, a0.right, ya + 0.35)
        self.box_m1(c, cols_bp0[0].left, y_bb, cols_bp0[0].right, cols_bp0[0].bottom)
        # bp1 (right of sw): left col → b, right col → bb
        self.box_m1(c, cols_bp1[0].left, yb, cols_bp1[0].right, cols_bp1[0].bottom)
        self.box_m1(c, b1.right + 1.6, yb, cols_bp1[0].right, yb + 0.35)
        self.box_m1(c, cols_bp1[1].left, y_bb, cols_bp1[1].right, cols_bp1[1].bottom)

        # --- bb: M2 strap (long span under switch) ---
        self.box_m1(c, bb_r0.left + 1.5, y_bb, bb_r0.left + 2.0, bb_r0.bottom - 0.5)
        self.box_m1(c, bb_r1.left + 1.5, y_bb, bb_r1.left + 2.0, bb_r1.bottom - 0.5)
        for xvia in (cols_bp0[0].left, cols_bp1[1].left, bb_r0.left + 1.5, bb_r1.left + 1.5):
            self.place(c, vs12, xvia, y_bb)
        c.shapes(m2).insert(pya.DBox(bb_r0.left + 1.5, y_bb, bb_r1.left + 2.0, y_bb + 0.4))
        self.pin_m1(c, cols_bp0[0].left, y_bb - 1.5, "bb")
        self.box_m1(c, cols_bp0[0].left, y_bb - 1.5, cols_bp0[0].right, y_bb + 0.4)
        # rhigh tops → a (left) / b (right) without crossing switch S/D
        self.box_m1(c, bb_r0.left + 1.5, bb_r0.top + 0.5, bb_r0.left + 2.0, ya + 0.35)
        self.box_m1(c, bb_r0.left + 1.5, ya, cols_bp0[1].right, ya + 0.35)
        self.box_m1(c, bb_r1.left + 1.5, bb_r1.top + 0.5, bb_r1.left + 2.0, yb + 0.35)
        self.box_m1(c, cols_bp1[0].left, yb, bb_r1.left + 2.0, yb + 0.35)

        # gates — switch from outside; bypass each locally; strap vbp on M2 if needed
        y_g = at_s + 10.0
        self.gate_contact(c, g_s0, at_s, bb_s0.left - 6.0, y_g, "g")
        self.gate_contact(c, g_s1, at_s, bb_s1.right + 6.0, y_g, "g")
        self.box_m1(c, bb_s0.left - 6.5, y_g, bb_s1.right + 6.5, y_g + 0.20)

        y_vbp = max(at_bp0, at_bp1) + 10.0
        self.gate_contact(c, g_bp0, at_bp0, bb_bp0.left - 6.0, y_vbp, "vbp")
        self.gate_contact(c, g_bp1, at_bp1, bb_bp1.right + 6.0, y_vbp, "vbp")
        # vbp strap on M2 over the switch island
        self.place(c, vs12, bb_bp0.left - 6.2, y_vbp)
        self.place(c, vs12, bb_bp1.right + 5.8, y_vbp)
        c.shapes(m2).insert(pya.DBox(bb_bp0.left - 6.2, y_vbp, bb_bp1.right + 6.2, y_vbp + 0.4))
        self.box_m1(c, bb_bp0.left - 6.5, y_vbp, bb_bp0.left - 5.5, y_vbp + 0.20)
        self.box_m1(c, bb_bp1.right + 5.5, y_vbp, bb_bp1.right + 6.5, y_vbp + 0.20)

        # tp / tn — keep TM1 pin ≥1.0 µm from MIM TM1 (TM1.a)
        for boxes, name in ((tm_0, "tp"), (tm_1, "tn")):
            if not boxes:
                continue
            t = boxes[0]
            x, y = 0.5 * (t.left + t.right), t.top + 4.0
            c.shapes(self.tm1).insert(pya.DBox(x - 0.4, t.top + 1.0, x + 0.4, y))
            self.pin_tm1(c, x, y, name)

        pt = self.pcell("ptap1", {"w": "0.78u", "l": "0.78u"})
        bb_pt, _ = self.place(c, pt, 5.0, -16.0)
        self.box_m1(c, bb_pt.left, bb_pt.bottom - 2.5, bb_pt.right, bb_pt.bottom)
        self.pin_m1(c, 0.5 * (bb_pt.left + bb_pt.right), bb_pt.bottom - 2.3, "gnd")

        self.say(f"bank_unit bbox {c.bbox().to_dtype(self.ly.dbu)}")
        self.say(f"  via_stack M1→M5 @ x={mx0:.2f},{mx1:.2f}; switch 2×5.16 parallel")
        return c.cell_index()

    def write_cell(self, name, cid):
        tmp = pya.Layout()
        tmp.dbu = self.ly.dbu
        tc = tmp.create_cell(name)
        tc.copy_tree(self.ly.cell(cid))
        gds = os.path.join(OUT, f"{name}.gds")
        tmp.write(gds)
        with open(gds, "rb") as fi, gzip.open(gds + ".gz", "wb") as fo:
            shutil.copyfileobj(fi, fo)
        self.say(f"wrote {gds}")
        return gds


def write_spice():
    open(os.path.join(OUT, "dac_unit.spice"), "w").write(
        """* P2.7.2a2 dac_unit [SCH]
.subckt dac_unit vdd pbias xd code xraw
Mmdb xd pbias vdd vdd sg13_lv_pmos w=4.0u l=2.0u
Mmsw xraw code xd vdd sg13_lv_pmos w=4.0u l=0.13u
.ends
""")
    open(os.path.join(OUT, "bank_unit.spice"), "w").write(
        """* P2.7.2a2 bank_unit LSB [SCH]
.subckt bank_unit tp tn g vbp bb gnd
Cxb tp a cap_cmim w=2.81e-06 l=2.81e-06 m=1
Cxn tn b cap_cmim w=2.81e-06 l=2.81e-06 m=1
Mms a g b gnd sg13_lv_nmos w=10.32u l=0.13u
Rrba a bb gnd rhigh w=5.0u l=60.8u m=1
Rrbb b bb gnd rhigh w=5.0u l=60.8u m=1
Mbp_a a vbp bb gnd sg13_lv_nmos w=0.15u l=0.13u
Mbp_b b vbp bb gnd sg13_lv_nmos w=0.15u l=0.13u
.ends
""")
    print("wrote spice")


def main():
    b = B()
    b.say("# P2.7.2a2 LVS proof cells\n")
    b.write_cell("dac_unit", b.build_dac_unit())
    b.write_cell("bank_unit", b.build_bank_unit())
    write_spice()
    open(os.path.join(OUT, "summary_proof_build.txt"), "w").write("\n".join(b.log) + "\n")


if __name__ == "__main__":
    main()
