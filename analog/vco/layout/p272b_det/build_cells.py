#!/usr/bin/env python3
"""P2.7.2b D22 ampcal_det — bottom-up cells [SCH ampcal_det / amp_common].

Prove DRC (density waived) + KLayout LVS + netgen after each step.
Fab replacements for sch ideals: capa→cmim, res→rhigh, isource→MOS sink+en,
vsource V_LOSS→pin vthn. Ports include en (power-down) and vthn.
"""
from __future__ import annotations

import gzip
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

sys.path[:0] = [
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python",
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python/pycell4klayout-api/source/python",
]
import pya  # noqa: E402
import sg13g2_pycell_lib  # noqa: E402

DBU = 0.001
POCKET_MM2 = 0.0187
VAR_MM2 = 0.0066  # [GDS] vco_var
FORECAST_D22 = 0.0013  # [HAND]
CMIM_HOLD = 16.33  # µm side for 400 fF @ 1.5 fF/µm² [PDK]
CMIM_CMP = 5.78    # µm side for 50 fF [PDK]
RHIGH_L = 6.96     # µm for ~20 kΩ @ w=0.5, Rspec=1300 [PDK]
RHIGH_BIAS_L = 78.0  # µm → I_hold≈4 µA [SCH OP retune 2026-11-16]
W_SINK_CMP = "5.5u"  # ttail/ss2 ng=2 → I_tt≈20 µA [SCH]


def um(x):
    return int(round(x / DBU))


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
        self.m4 = self.ly.layer(50, 0)
        self.m5 = self.ly.layer(67, 0)
        self.tm1 = self.ly.layer(126, 0)
        self.tm1pin = self.ly.layer(126, 2)
        self.tm1txt = self.ly.layer(126, 25)
        self.cont = self.ly.layer(6, 0)
        self.poly = self.ly.layer(5, 0)
        self.activ = self.ly.layer(1, 0)
        self.nsd = self.ly.layer(7, 0)
        self.psd = self.ly.layer(14, 0)
        self.nw = self.ly.layer(31, 0)
        self.nbulay = self.ly.layer(32, 0)
        self.log = []
        self.hold_area = None
        self.det_area = None
        self.cmp_area = None
        self.bias_area = None
        self.det_top_area = None
        self.det_top_bb = None
        self.cmim_hold_w = CMIM_HOLD
        self.rhigh_l = RHIGH_L

    def say(self, s=""):
        print(s, flush=True)
        self.log.append(s)

    def pcell(self, name, params):
        return self.ly.add_pcell_variant(
            self.lib, self.lib_ly.pcell_declaration(name).id(), params)

    def place(self, parent, cid, x, y):
        t = pya.Trans(pya.Trans.R0, um(x), um(y))
        parent.insert(pya.CellInstArray(cid, t))
        return self.ly.cell(cid).bbox().transformed(t).to_dtype(self.ly.dbu), t

    def pin_m1(self, cell, x, y, name, label=True):
        cell.shapes(self.m1).insert(pya.DBox(x - 0.25, y - 0.25, x + 0.25, y + 0.25))
        if label:
            cell.shapes(self.m1pin).insert(pya.DBox(x - 0.2, y - 0.2, x + 0.2, y + 0.2))
            cell.shapes(self.m1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def pin_tm1(self, cell, x, y, name):
        cell.shapes(self.tm1).insert(pya.DBox(x - 0.5, y - 0.5, x + 0.5, y + 0.5))
        cell.shapes(self.tm1pin).insert(pya.DBox(x - 0.4, y - 0.4, x + 0.4, y + 0.4))
        cell.shapes(self.tm1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def box_m1(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m1).insert(pya.DBox(
            min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    def box_m2(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m2).insert(pya.DBox(
            min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    def box_m3(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m3).insert(pya.DBox(
            min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    def box_m5(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m5).insert(pya.DBox(
            min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    def _via13(self, c, vs13, x, y):
        self.box_m1(c, x - 0.30, y - 0.30, x + 0.30, y + 0.30)
        self.box_m3(c, x - 0.30, y - 0.30, x + 0.30, y + 0.30)
        self.place(c, vs13, x, y)

    def box_nw_fill(self, cell, x0, y0, x1, y1):
        cell.shapes(self.nw).insert(pya.DBox(x0, y0, x1, y1))
        cell.shapes(self.nbulay).insert(
            pya.DBox(x0 + 0.2, y0 + 0.2, x1 - 0.2, y1 - 0.2))

    def m1_cols(self, cid, trans):
        uniq = {}
        for s in self.ly.cell(cid).shapes(self.m1).each():
            if s.is_box():
                b = s.bbox().transformed(trans).to_dtype(self.ly.dbu)
                uniq[round((b.left + b.right) / 2, 3)] = b
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

    def activ_bottom(self, cid, trans):
        bot = None
        for s in self.ly.cell(cid).shapes(self.activ).each():
            if s.is_box():
                b = s.bbox().transformed(trans).to_dtype(self.ly.dbu)
                bot = b.bottom if bot is None else min(bot, b.bottom)
        return bot

    def activ_left(self, cid, trans):
        left = None
        for s in self.ly.cell(cid).shapes(self.activ).each():
            if s.is_box():
                b = s.bbox().transformed(trans).to_dtype(self.ly.dbu)
                left = b.left if left is None else min(left, b.left)
        return left

    def _via12(self, c, vs12, x, y):
        self.box_m1(c, x - 0.30, y - 0.30, x + 0.30, y + 0.30)
        self.box_m2(c, x - 0.30, y - 0.30, x + 0.30, y + 0.30)
        self.place(c, vs12, x, y)

    def _route_mos_sd(self, c, cols, even_is_drain=True):
        drains, sources = [], []
        for i, col in enumerate(cols):
            if (i % 2 == 0) == even_is_drain:
                drains.append(col)
            else:
                sources.append(col)
        return drains, sources

    def _gate_west(self, c, gates, at, bb, name, label=True):
        """Cont west of activ; M1 pin further west [bypass_pair pattern]."""
        g0, g1 = gates[0], gates[-1]
        y0, y1 = at + 0.08, at + 0.55
        c.shapes(self.poly).insert(pya.DBox(g0.left, y0, g1.right, y1))
        for g in gates:
            gx = 0.5 * (g.left + g.right)
            half = 0.5 * (g.right - g.left)
            c.shapes(self.poly).insert(
                pya.DBox(gx - half, g.top - 0.05, gx + half, y1))
        x_g = bb.left - 3.0
        c.shapes(self.poly).insert(pya.DBox(x_g - 0.20, y0, g0.left + 0.05, y1))
        c.shapes(self.poly).insert(pya.DBox(x_g - 0.25, y0, x_g + 0.25, y0 + 0.55))
        c.shapes(self.cont).insert(
            pya.DBox(x_g - 0.08, y0 + 0.16, x_g + 0.08, y0 + 0.32))
        self.box_m1(c, x_g - 0.20, y0 + 0.10, x_g + 0.20, y0 + 0.70)
        if label:
            self.pin_m1(c, x_g, y0 + 0.85, name)
        return x_g, y0 + 0.85

    def _gate_bus(self, c, gates, at, x_pin, y_pin, name, label=True):
        g0, g1 = gates[0], gates[-1]
        c.shapes(self.poly).insert(
            pya.DBox(g0.left, at + 0.08, g1.right, at + 0.55))
        y_pad0 = max(at + 0.50, max(g.top for g in gates) + 0.30)
        y_pad1 = y_pad0 + 0.50
        for g in gates:
            gx = 0.5 * (g.left + g.right)
            half = 0.5 * (g.right - g.left)
            c.shapes(self.poly).insert(
                pya.DBox(gx - half, g.top - 0.05, gx + half, y_pad0 + 0.05))
            c.shapes(self.cont).insert(
                pya.DBox(gx - 0.08, y_pad0 + 0.16, gx + 0.08, y_pad0 + 0.32))
        c.shapes(self.poly).insert(
            pya.DBox(g0.left - 0.05, y_pad0, g1.right + 0.05, y_pad1))
        self.box_m1(c, g0.left - 0.08, y_pad0 + 0.16,
                    g1.right + 0.08, y_pad1 + 0.16)
        self.box_m1(c, min(x_pin, g0.left) - 0.14, y_pad0 + 0.16,
                    max(x_pin, g1.right) + 0.14, y_pad1 + 0.16)
        self.box_m1(c, x_pin - 0.14, min(y_pad1, y_pin),
                    x_pin + 0.14, max(y_pad1 + 0.28, y_pin + 0.28))
        self.pin_m1(c, x_pin, y_pin, name, label=label)
        return y_pad1

    def _outer_ptap_gr(self, cell, x0, y0, x1, y1, ring=1.0, gap=1.2):
        ox0, oy0 = x0 - gap - ring, y0 - gap - ring
        ox1, oy1 = x1 + gap + ring, y1 + gap + ring
        ix0, iy0 = x0 - gap, y0 - gap
        ix1, iy1 = x1 + gap, y1 + gap
        parts = [
            (ox0, oy0, ox1, iy0),
            (ox0, iy1, ox1, oy1),
            (ox0, iy0, ix0, iy1),
            (ix1, iy0, ox1, iy1),
        ]
        for a, b, c_, d in parts:
            cell.shapes(self.activ).insert(pya.DBox(a, b, c_, d))
            cell.shapes(self.psd).insert(
                pya.DBox(a - 0.05, b - 0.05, c_ + 0.05, d + 0.05))
            self.box_m1(cell, a, b, c_, d)
        x = ox0 + 0.2
        while x < ox1 - 0.3:
            cell.shapes(self.cont).insert(
                pya.DBox(x, iy1 + 0.2, x + 0.16, iy1 + 0.36))
            x += 1.0
        return ox0, oy0, ox1, oy1

    def write_cell(self, name, cid):
        tmp = pya.Layout()
        tmp.dbu = self.ly.dbu
        tc = tmp.create_cell(name)
        tc.copy_tree(self.ly.cell(cid))
        gds = os.path.join(OUT, f"{name}.gds")
        tmp.write(gds)
        with open(gds, "rb") as fi, gzip.open(gds + ".gz", "wb") as fo:
            shutil.copyfileobj(fi, fo)
        bb = self.ly.cell(cid).bbox().to_dtype(self.ly.dbu)
        area = bb.width() * bb.height() * 1e-6
        self.say(f"wrote {gds} bbox={bb} area={area:.4f} mm2")
        return gds, area, bb

    def _cell_by_name(self, name):
        for c in self.ly.each_cell():
            if c.name == name:
                return c.cell_index()
        raise KeyError(name)

    def _copy_no_pin_texts(self, src_name, dst_name):
        src = self.ly.cell(self._cell_by_name(src_name))
        dst = self.ly.create_cell(dst_name)
        dst.copy_tree(src)
        pins = {}
        for s in list(dst.shapes(self.m1txt).each()):
            if s.is_text():
                d = s.text_dtrans.disp
                pins[s.text.string] = (d.x, d.y)
                s.delete()
        for s in list(dst.shapes(self.tm1txt).each()):
            if s.is_text():
                d = s.text_dtrans.disp
                pins[s.text.string] = (d.x, d.y)
                s.delete()
        return dst.cell_index(), pins

    def _pins_abs(self, local_pins, trans):
        out = {}
        for name, (x, y) in local_pins.items():
            out[name] = (x + trans.disp.x * self.ly.dbu,
                         y + trans.disp.y * self.ly.dbu)
        return out

    # ------------------------------------------------------------------
    def build_hold_caps(self):
        """2× cmim 400 fF (chold, crep). PLUS=TM1 → hold/rep; MINUS=M5 → gnd."""
        c = self.ly.create_cell("hold_caps")
        side = self.cmim_hold_w
        mim = self.pcell("cmim", {
            "w": f"{side:.3f}u", "l": f"{side:.3f}u",
            "C": "400f", "Calculate": "w&l", "guardRingType": "none",
        })
        vs5 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal5",
            "vn_columns": 2, "vn_rows": 2,
        })
        mloc = self.ly.cell(mim).bbox().to_dtype(self.ly.dbu)
        gap = 4.0
        bb0, t0 = self.place(c, mim, 0.0, 0.0)
        bb1, t1 = self.place(c, mim, bb0.right - mloc.left + gap, 0.0)

        def lyr_boxes(cid, trans, layer):
            out = []
            for s in self.ly.cell(cid).shapes(layer).each():
                if s.is_box():
                    out.append(s.bbox().transformed(trans).to_dtype(self.ly.dbu))
            return out

        def biggest(boxes):
            return max(boxes, key=lambda b: (b.right - b.left) * (b.top - b.bottom))

        m5_0 = biggest(lyr_boxes(mim, t0, self.m5))
        m5_1 = biggest(lyr_boxes(mim, t1, self.m5))
        tm_0 = biggest(lyr_boxes(mim, t0, self.tm1))
        tm_1 = biggest(lyr_boxes(mim, t1, self.tm1))

        y_gnd = min(m5_0.bottom, m5_1.bottom) - 3.0
        x_lo = min(m5_0.left, m5_1.left)
        x_hi = max(m5_0.right, m5_1.right)
        self.box_m1(c, x_lo, y_gnd, x_hi, y_gnd + 0.50)
        for pl in (m5_0, m5_1):
            mx = 0.5 * (pl.left + pl.right)
            y_vs = pl.bottom - 0.2
            bb_vs, _ = self.place(c, vs5, mx - 0.35, y_vs - 0.5)
            self.box_m5(c, bb_vs.left, bb_vs.top - 0.1,
                        bb_vs.right, pl.bottom + 0.3)
            self.box_m1(c, bb_vs.left - 0.1, y_gnd,
                        bb_vs.right + 0.1, bb_vs.bottom + 0.2)
        self.pin_m1(c, 0.5 * (x_lo + x_hi), y_gnd - 0.8, "gnd")
        self.box_m1(c, 0.5 * (x_lo + x_hi) - 0.30, y_gnd - 1.0,
                    0.5 * (x_lo + x_hi) + 0.30, y_gnd + 0.50)

        # PLUS pins on TM1 south stubs
        for tm, name in ((tm_0, "hold"), (tm_1, "rep")):
            cx = 0.5 * (tm.left + tm.right)
            y_pin = tm.bottom - 5.0
            c.shapes(self.tm1).insert(pya.DBox(
                cx - 1.5, y_pin - 1.0, cx + 1.5, tm.bottom + 2.0))
            self.pin_tm1(c, cx, y_pin, name)

        abb = c.bbox().to_dtype(self.ly.dbu)
        ox0, oy0, ox1, oy1 = self._outer_ptap_gr(
            c, abb.left, min(abb.bottom, y_gnd - 1.5),
            abb.right, abb.top, ring=1.0, gap=1.5)
        self.box_m1(c, ox0, y_gnd, ox0 + 1.0, oy0 + 1.0)
        self.box_m1(c, ox0, y_gnd, 0.5 * (x_lo + x_hi), y_gnd + 0.50)

        bb = c.bbox().to_dtype(self.ly.dbu)
        self.hold_area = bb.width() * bb.height() * 1e-6
        self.say(f"hold_caps bbox {bb} area={self.hold_area:.4f} mm2")
        return c.cell_index()

    def write_spice_hold_caps(self, w=None):
        w = w or self.cmim_hold_w
        open(os.path.join(OUT, "hold_caps.spice"), "w").write(
            f"""* P2.7.2b hold_caps 2× cmim 400f [SCH chold/crep]
.subckt hold_caps hold rep gnd
Cchold hold gnd cap_cmim w={w:.3f}u l={w:.3f}u m=1
Ccrep rep gnd cap_cmim w={w:.3f}u l={w:.3f}u m=1
.ends
""")
        self.say(f"wrote hold_caps.spice w={w:.3f}u")

    # ------------------------------------------------------------------
    def build_det_sf_pair(self):
        """SF peak + replica: 4× 0.5/0.13 + edge dummies, ABBA [SCH].

        Order: Dum | mdtp | mrtp | mrtn | mdtn | Dum
        Drains → vdd; sources hold (peak) / rep (replica); gates tp/ct/ct/tn.
        """
        c = self.ly.create_cell("det_sf_pair")
        mos = self.pcell("nmos", {
            "w": "0.5u", "l": "0.13u", "ng": 1, "m": 1,
            "guardRingType": "none",
        })
        dum = self.pcell("nmos", {
            "w": "0.5u", "l": "0.13u", "ng": 1, "m": 1,
            "guardRingType": "none",
        })
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs13 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal3",
            "vn_columns": 1, "vn_rows": 1,
        })
        mloc = self.ly.cell(mos).bbox().to_dtype(self.ly.dbu)
        gap = 3.5
        x = 0.0
        placed = []
        # names: dumL, mdtp, mrtp, mrtn, mdtn, dumR
        labels = ["dumL", "mdtp", "mrtp", "mrtn", "mdtn", "dumR"]
        for lab in labels:
            cid = dum if lab.startswith("dum") else mos
            bb, t = self.place(c, cid, x - mloc.left, 0.0)
            placed.append((lab, cid, bb, t))
            x = bb.right + gap

        def sd(cid, t):
            return self._route_mos_sd(c, self.m1_cols(cid, t), even_is_drain=True)

        info = {}
        for lab, cid, bb, t in placed:
            dr, sr = sd(cid, t)
            info[lab] = {
                "cid": cid, "bb": bb, "t": t, "dr": dr, "sr": sr,
                "gates": self.poly_gates(cid, t),
                "at": self.activ_top(cid, t),
            }

        y_vdd = max(i["bb"].top for i in info.values()) + 2.5
        y_hold = min(i["bb"].bottom for i in info.values()) - 2.5
        y_rep = y_hold - 3.0
        y_gnd = y_rep - 3.0

        # Active drains → vdd (M2 bus above). Dummies stay off this net [LVS].
        all_dr = []
        for lab in ("mdtp", "mdtn", "mrtp", "mrtn"):
            all_dr += info[lab]["dr"]
        for col in all_dr:
            # Keep M1 land inside the SD column — ng=1 cols are tight [DRC M1.b]
            cx = 0.5 * (col.left + col.right)
            yv = col.top - 0.05
            self.box_m1(c, col.left - 0.02, yv - 0.05, col.right + 0.02, yv + 0.25)
            self.box_m2(c, cx - 0.30, yv - 0.05, cx + 0.30, y_vdd + 0.40)
            self.place(c, vs12, cx, yv + 0.10)
        self.box_m2(c, min(col.left for col in all_dr) - 0.25, y_vdd,
                    max(col.right for col in all_dr) + 0.25, y_vdd + 0.40)
        vx = 0.5 * (min(col.left for col in all_dr) +
                    max(col.right for col in all_dr))
        self._via12(c, vs12, vx, y_vdd + 0.20)
        self.box_m1(c, vx - 0.30, y_vdd - 0.2, vx + 0.30, y_vdd + 0.60)
        self.pin_m1(c, vx, y_vdd + 0.40, "vdd")

        # Peak sources → hold; replica → rep (M2 below, separate Y)
        def drop_to(cols, y_bus):
            for col in cols:
                cx = 0.5 * (col.left + col.right)
                self.box_m1(c, col.left, y_bus, col.right, col.bottom)
                # via land on M2; M1 stays at column width [DRC M1.b]
                self.box_m1(c, col.left - 0.02, y_bus, col.right + 0.02, y_bus + 0.40)
                self.box_m2(c, cx - 0.30, y_bus, cx + 0.30, y_bus + 0.40)
                self.place(c, vs12, cx, y_bus + 0.20)
            self.box_m2(c, cols[0].left - 0.25, y_bus,
                        cols[-1].right + 0.25, y_bus + 0.40)

        hold_src = info["mdtp"]["sr"] + info["mdtn"]["sr"]
        rep_src = info["mrtp"]["sr"] + info["mrtn"]["sr"]
        drop_to(hold_src, y_hold)
        drop_to(rep_src, y_rep)
        self.box_m2(c, hold_src[0].left - 0.25, y_hold,
                    hold_src[-1].right + 0.25, y_hold + 0.40)
        self.box_m2(c, rep_src[0].left - 0.25, y_rep,
                    rep_src[-1].right + 0.25, y_rep + 0.40)
        # pins outboard
        hx = hold_src[0].left - 2.5
        self._via12(c, vs12, hx, y_hold + 0.20)
        self.box_m2(c, hx - 0.30, y_hold, hold_src[0].left, y_hold + 0.40)
        self.box_m1(c, hx - 0.30, y_hold - 1.2, hx + 0.30, y_hold + 0.40)
        self.pin_m1(c, hx, y_hold - 1.0, "hold")
        rx = rep_src[-1].right + 2.5
        self._via12(c, vs12, rx, y_rep + 0.20)
        self.box_m2(c, rep_src[-1].right, y_rep, rx + 0.30, y_rep + 0.40)
        self.box_m1(c, rx - 0.30, y_rep - 1.2, rx + 0.30, y_rep + 0.40)
        self.pin_m1(c, rx, y_rep - 1.0, "rep")

        # Dummies → gnd
        dum_cols = (info["dumL"]["dr"] + info["dumL"]["sr"] +
                    info["dumR"]["dr"] + info["dumR"]["sr"])
        drop_to(info["dumL"]["dr"] + info["dumL"]["sr"], y_gnd)
        drop_to(info["dumR"]["dr"] + info["dumR"]["sr"], y_gnd)
        self.box_m2(c, min(dc.left for dc in dum_cols) - 0.25, y_gnd,
                    max(dc.right for dc in dum_cols) + 0.25, y_gnd + 0.40)
        # short dummy gates to gnd locally
        for lab in ("dumL", "dumR"):
            gates = info[lab]["gates"]
            at = info[lab]["at"]
            sd_cols = info[lab]["dr"] + info[lab]["sr"]
            g0, g1 = gates[0], gates[-1]
            y_pad0 = max(at + 0.50, max(g.top for g in gates) + 0.30)
            y_pad1 = y_pad0 + 0.50
            for g in gates:
                gx = 0.5 * (g.left + g.right)
                half = 0.5 * (g.right - g.left)
                c.shapes(self.poly).insert(
                    pya.DBox(gx - half, g.top - 0.05, gx + half, y_pad0 + 0.05))
                c.shapes(self.cont).insert(
                    pya.DBox(gx - 0.08, y_pad0 + 0.16, gx + 0.08, y_pad0 + 0.32))
            c.shapes(self.poly).insert(
                pya.DBox(g0.left - 0.05, y_pad0, g1.right + 0.05, y_pad1))
            self.box_m1(c, g0.left - 0.08, y_pad0 + 0.16,
                        g1.right + 0.08, y_pad1 + 0.16)
            sx = 0.5 * (sd_cols[0].left + sd_cols[0].right)
            self.box_m1(c, min(g0.left, sx) - 0.14, y_pad0 + 0.16,
                        max(g1.right, sx) + 0.14, y_pad1 + 0.16)
            self.box_m1(c, sx - 0.14, sd_cols[0].top - 0.05,
                        sx + 0.14, y_pad1 + 0.16)

        gx = info["dumL"]["bb"].left - 4.0
        self._via12(c, vs12, gx, y_gnd + 0.20)
        self.box_m2(c, gx - 0.30, y_gnd,
                    min(dc.left for dc in info["dumL"]["dr"] + info["dumL"]["sr"]),
                    y_gnd + 0.40)
        self.box_m1(c, gx - 0.30, y_gnd - 1.2, gx + 0.30, y_gnd + 0.40)
        self.pin_m1(c, gx, y_gnd - 1.0, "gnd")

        # Gates: tp west of mdtp, tn east of mdtn (symmetric short taps) [SCH]
        self._gate_west(
            c, info["mdtp"]["gates"], info["mdtp"]["at"],
            info["mdtp"]["bb"], "tp")
        bb_n = info["mdtn"]["bb"]
        gates_n = info["mdtn"]["gates"]
        at_n = info["mdtn"]["at"]
        g0, g1 = gates_n[0], gates_n[-1]
        y0, y1 = at_n + 0.08, at_n + 0.55
        c.shapes(self.poly).insert(pya.DBox(g0.left, y0, g1.right, y1))
        for g in gates_n:
            gx = 0.5 * (g.left + g.right)
            half = 0.5 * (g.right - g.left)
            c.shapes(self.poly).insert(
                pya.DBox(gx - half, g.top - 0.05, gx + half, y1))
        x_tn = bb_n.right + 3.0
        c.shapes(self.poly).insert(pya.DBox(g1.right - 0.05, y0, x_tn + 0.20, y1))
        c.shapes(self.poly).insert(pya.DBox(x_tn - 0.25, y0, x_tn + 0.25, y0 + 0.55))
        c.shapes(self.cont).insert(
            pya.DBox(x_tn - 0.08, y0 + 0.16, x_tn + 0.08, y0 + 0.32))
        self.box_m1(c, x_tn - 0.20, y0 + 0.10, x_tn + 0.20, y0 + 0.70)
        self.pin_m1(c, x_tn, y0 + 0.85, "tn")

        # ct: replica gates → M1 pad → via13 → M3 above vdd (no M2 cross) [LVS]
        y_ct = y_vdd + 3.5
        ct_xs = []
        for lab in ("mrtp", "mrtn"):
            gates = info[lab]["gates"]
            at = info[lab]["at"]
            bb = info[lab]["bb"]
            g0, g1 = gates[0], gates[-1]
            # Cont in mid-gap (east of mrtp / west of mrtn), clear of SD
            if lab == "mrtp":
                x_g = bb.right + 1.2
            else:
                x_g = bb.left - 1.2
            y0, y1 = at + 0.08, at + 0.55
            c.shapes(self.poly).insert(pya.DBox(g0.left, y0, g1.right, y1))
            for g in gates:
                gx = 0.5 * (g.left + g.right)
                half = 0.5 * (g.right - g.left)
                c.shapes(self.poly).insert(
                    pya.DBox(gx - half, g.top - 0.05, gx + half, y1))
            if lab == "mrtp":
                c.shapes(self.poly).insert(
                    pya.DBox(g1.right - 0.05, y0, x_g + 0.20, y1))
            else:
                c.shapes(self.poly).insert(
                    pya.DBox(x_g - 0.20, y0, g0.left + 0.05, y1))
            c.shapes(self.poly).insert(
                pya.DBox(x_g - 0.25, y0, x_g + 0.25, y0 + 0.55))
            c.shapes(self.cont).insert(
                pya.DBox(x_g - 0.08, y0 + 0.16, x_g + 0.08, y0 + 0.32))
            self.box_m1(c, x_g - 0.20, y0 + 0.10, x_g + 0.20, y0 + 0.70)
            self._via13(c, vs13, x_g, y0 + 0.40)
            self.box_m3(c, x_g - 0.25, y0 + 0.10, x_g + 0.25, y_ct + 0.40)
            ct_xs.append(x_g)
        self.box_m3(c, min(ct_xs) - 0.25, y_ct,
                    max(ct_xs) + 0.25, y_ct + 0.40)
        ctx = 0.5 * (min(ct_xs) + max(ct_xs))
        self._via13(c, vs13, ctx, y_ct + 0.20)
        self.box_m1(c, ctx - 0.30, y_ct - 0.2, ctx + 0.30, y_ct + 1.2)
        self.pin_m1(c, ctx, y_ct + 1.0, "ct")

        abb = c.bbox().to_dtype(self.ly.dbu)
        ox0, oy0, ox1, oy1 = self._outer_ptap_gr(
            c, abb.left, abb.bottom, abb.right, abb.top, ring=1.0, gap=1.5)
        self.box_m1(c, ox0, y_gnd, gx + 0.30, y_gnd + 0.40)
        self.box_m1(c, ox0, oy0, ox0 + 1.0, y_gnd + 0.40)

        bb = c.bbox().to_dtype(self.ly.dbu)
        self.det_area = bb.width() * bb.height() * 1e-6
        self.say(f"det_sf_pair bbox {bb} area={self.det_area:.4f} mm2")
        return c.cell_index()

    def write_spice_det_sf_pair(self):
        open(os.path.join(OUT, "det_sf_pair.spice"), "w").write(
            """* P2.7.2b det_sf_pair [SCH mdtp/mdtn/mrtp/mrtn] + edge dummies
.subckt det_sf_pair tp tn ct hold rep vdd gnd
Mmdtp vdd tp hold gnd sg13_lv_nmos w=0.5u l=0.13u ng=1
Mmdtn vdd tn hold gnd sg13_lv_nmos w=0.5u l=0.13u ng=1
Mmrtp vdd ct rep gnd sg13_lv_nmos w=0.5u l=0.13u ng=1
Mmrtn vdd ct rep gnd sg13_lv_nmos w=0.5u l=0.13u ng=1
MdL gnd gnd gnd gnd sg13_lv_nmos w=0.5u l=0.13u ng=1
MdR gnd gnd gnd gnd sg13_lv_nmos w=0.5u l=0.13u ng=1
.ends
""")
        self.say("wrote det_sf_pair.spice")

    # ------------------------------------------------------------------
    def build_cmp_se(self):
        """SE comparator: matched pairs + rhigh loads [SCH]. Compact ota-style.

        Ports: hold, vthn, cmp, vdd, gnd, ttail, ss2, co, co2, n1
        """
        c = self.ly.create_cell("cmp_se")
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs13 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal3",
            "vn_columns": 1, "vn_rows": 1,
        })
        mo = self.pcell("nmos", {
            "w": "4.0u", "l": "0.5u", "ng": 2, "m": 1,
            "guardRingType": "none",
        })
        dum = self.pcell("nmos", {
            "w": "2.0u", "l": "0.5u", "ng": 1, "m": 1,
            "guardRingType": "none",
        })
        mp = self.pcell("pmos", {
            "w": "4.0u", "l": "0.5u", "ng": 2, "m": 1,
            "guardRingType": "none",
        })
        rh = self.pcell("rhigh", {
            "R": "20k", "w": "0.5u", "b": 0,
            "Calculate": "l", "guardRingType": "none",
        })
        mloc = self.ly.cell(mo).bbox().to_dtype(self.ly.dbu)
        dloc = self.ly.cell(dum).bbox().to_dtype(self.ly.dbu)
        ploc = self.ly.cell(mp).bbox().to_dtype(self.ly.dbu)
        rloc = self.ly.cell(rh).bbox().to_dtype(self.ly.dbu)

        gap = 5.0
        x = 0.0
        bb_dL, t_dL = self.place(c, dum, x - dloc.left, 0)
        x = bb_dL.right + gap
        bb1, t1 = self.place(c, mo, x - mloc.left, 0)          # mc1
        x = bb1.right + gap
        bb2, t2 = self.place(c, mo, x - mloc.left, 0)          # mc2
        x = bb2.right + gap
        bb_dR, t_dR = self.place(c, dum, x - dloc.left, 0)

        # SE stage well clear of input (large Y gap for bus stack)
        y_se = max(bb1.top, bb2.top) + 18.0
        bb_s1, ts1 = self.place(c, mo, bb1.left - mloc.left, y_se - mloc.bottom)
        bb_s2, ts2 = self.place(c, mo, bb2.left - mloc.left, y_se - mloc.bottom)

        y_p = max(bb_s1.top, bb_s2.top) + 10.0
        bb_p1, tp1 = self.place(c, mp, bb_s1.left - ploc.left, y_p - ploc.bottom)
        bb_p2, tp2 = self.place(c, mp, bb_s2.left - ploc.left, y_p - ploc.bottom)

        # rhigh outboard left/right of input pair
        bb_r1, tr1 = self.place(
            c, rh, bb_dL.left - rloc.width() - 5.0, bb1.bottom - rloc.bottom)
        bb_r2, tr2 = self.place(
            c, rh, bb_dR.right + 5.0, bb2.bottom - rloc.bottom)

        def sd_of(cid, trans):
            return self._route_mos_sd(c, self.m1_cols(cid, trans), True)

        dr1, sr1 = sd_of(mo, t1)
        dr2, sr2 = sd_of(mo, t2)
        drdL, srdL = sd_of(dum, t_dL)
        drdR, srdR = sd_of(dum, t_dR)
        ds1, ss1c = sd_of(mo, ts1)
        ds2, ss2c = sd_of(mo, ts2)
        pdr1, psr1 = sd_of(mp, tp1)
        pdr2, psr2 = sd_of(mp, tp2)

        # Bus Y stack with ≥0.6 µm gaps [DRC M2.b]
        y_ttail = min(bb1.bottom, bb2.bottom) - 2.5
        y_gnd = y_ttail - 3.5
        y_co = max(bb1.top, bb2.top) + 2.5
        y_co2 = y_co + 3.0
        y_ss2 = y_se - 2.5
        y_n1 = max(bb_s1.top, bb_s2.top) + 2.5
        y_cmp = y_n1 + 3.0
        y_vdd = max(bb_p1.top, bb_p2.top) + 4.0

        def m1_down_to_m2(cols, y_bus):
            land = 0.28
            for col in cols:
                cx = 0.5 * (col.left + col.right)
                self.box_m1(c, col.left, y_bus, col.right, col.bottom)
                self.box_m1(c, cx - land, y_bus, cx + land, y_bus + 0.40)
                self.box_m2(c, cx - land, y_bus, cx + land, y_bus + 0.40)
                self.place(c, vs12, cx, y_bus + 0.20)
            self.box_m2(c, cols[0].left - 0.25, y_bus,
                        cols[-1].right + 0.25, y_bus + 0.40)

        def m1_up_via_m2(cols, y_bus):
            land = 0.28
            for col in cols:
                cx = 0.5 * (col.left + col.right)
                yv = col.top - 0.20
                self.box_m1(c, cx - land, yv - 0.20, cx + land, yv + 0.20)
                self.box_m2(c, cx - land, yv - 0.20, cx + land, y_bus + 0.40)
                self.place(c, vs12, cx, yv)
            self.box_m2(c, cols[0].left - 0.25, y_bus,
                        cols[-1].right + 0.25, y_bus + 0.40)

        # mc sources → ttail
        m1_down_to_m2(sr1 + sr2, y_ttail)
        self.box_m2(c, sr1[0].left - 0.25, y_ttail,
                    sr2[-1].right + 0.25, y_ttail + 0.40)
        sx = sr1[0].left - 2.5
        self._via12(c, vs12, sx, y_ttail + 0.20)
        self.box_m2(c, sx - 0.30, y_ttail, sr1[0].left, y_ttail + 0.40)
        self.box_m1(c, sx - 0.30, y_ttail - 1.2, sx + 0.30, y_ttail + 0.40)
        self.pin_m1(c, sx, y_ttail - 1.0, "ttail")

        # SE sources → ss2
        m1_down_to_m2(ss1c + ss2c, y_ss2)
        self.box_m2(c, ss1c[0].left - 0.25, y_ss2,
                    ss2c[-1].right + 0.25, y_ss2 + 0.40)
        sx2 = ss1c[0].left - 2.5
        self._via12(c, vs12, sx2, y_ss2 + 0.20)
        self.box_m2(c, sx2 - 0.30, y_ss2, ss1c[0].left, y_ss2 + 0.40)
        self.box_m1(c, sx2 - 0.30, y_ss2 - 1.2, sx2 + 0.30, y_ss2 + 0.40)
        self.pin_m1(c, sx2, y_ss2 - 1.0, "ss2")

        # Dummies → gnd (separate L/R islands)
        m1_down_to_m2(drdL + srdL, y_gnd)
        m1_down_to_m2(drdR + srdR, y_gnd)
        self.box_m2(c, min(dc.left for dc in drdL + srdL) - 0.25, y_gnd,
                    max(dc.right for dc in drdL + srdL) + 0.25, y_gnd + 0.40)
        self.box_m2(c, min(dc.left for dc in drdR + srdR) - 0.25, y_gnd,
                    max(dc.right for dc in drdR + srdR) + 0.25, y_gnd + 0.40)
        for gates, at, sd_cols in (
            (self.poly_gates(dum, t_dL), self.activ_top(dum, t_dL), drdL + srdL),
            (self.poly_gates(dum, t_dR), self.activ_top(dum, t_dR), drdR + srdR),
        ):
            g0, g1 = gates[0], gates[-1]
            y_pad0 = max(at + 0.50, max(g.top for g in gates) + 0.30)
            y_pad1 = y_pad0 + 0.50
            for g in gates:
                gx = 0.5 * (g.left + g.right)
                half = 0.5 * (g.right - g.left)
                c.shapes(self.poly).insert(
                    pya.DBox(gx - half, g.top - 0.05, gx + half, y_pad0 + 0.05))
                c.shapes(self.cont).insert(
                    pya.DBox(gx - 0.08, y_pad0 + 0.16, gx + 0.08, y_pad0 + 0.32))
            c.shapes(self.poly).insert(
                pya.DBox(g0.left - 0.05, y_pad0, g1.right + 0.05, y_pad1))
            self.box_m1(c, g0.left - 0.08, y_pad0 + 0.16,
                        g1.right + 0.08, y_pad1 + 0.16)
            sx0 = 0.5 * (sd_cols[0].left + sd_cols[0].right)
            self.box_m1(c, min(g0.left, sx0) - 0.14, y_pad0 + 0.16,
                        max(g1.right, sx0) + 0.14, y_pad1 + 0.16)
            self.box_m1(c, sx0 - 0.14, sd_cols[0].top - 0.05,
                        sx0 + 0.14, y_pad1 + 0.16)

        gx = bb_dL.left - 4.0
        self._via12(c, vs12, gx, y_gnd + 0.20)
        self.box_m2(c, gx - 0.30, y_gnd,
                    min(dc.left for dc in drdL + srdL), y_gnd + 0.40)
        self.box_m1(c, gx - 0.30, y_gnd - 1.2, gx + 0.30, y_gnd + 0.40)
        self.pin_m1(c, gx, y_gnd - 1.0, "gnd")
        y_gnd_tie = y_gnd - 5.0
        x_rr = max(dc.right for dc in drdR + srdR)
        self.box_m2(c, x_rr - 0.25, y_gnd_tie, x_rr + 0.25, y_gnd + 0.40)
        self.box_m2(c, gx - 0.25, y_gnd_tie, x_rr + 0.25, y_gnd_tie + 0.40)
        self.box_m2(c, gx - 0.25, y_gnd_tie, gx + 0.25, y_gnd + 0.40)

        # Input gates
        y_gate = y_co2 + 2.5
        self._gate_bus(c, self.poly_gates(mo, t1), self.activ_top(mo, t1),
                       bb1.left - 4.0, y_gate, "hold")
        self._gate_bus(c, self.poly_gates(mo, t2), self.activ_top(mo, t2),
                       bb2.right + 4.0, y_gate, "vthn")

        # mc drains → co / co2 (separate Y)
        m1_up_via_m2(dr1, y_co)
        m1_up_via_m2(dr2, y_co2)
        self.box_m2(c, dr1[0].left - 0.25, y_co,
                    dr1[-1].right + 0.25, y_co + 0.40)
        self.box_m2(c, dr2[0].left - 0.25, y_co2,
                    dr2[-1].right + 0.25, y_co2 + 0.40)
        self._via12(c, vs12, dr1[0].left - 2.0, y_co + 0.20)
        self.box_m2(c, dr1[0].left - 2.3, y_co, dr1[0].left, y_co + 0.40)
        self.box_m1(c, dr1[0].left - 2.3, y_co - 0.5,
                    dr1[0].left - 1.7, y_co + 0.40)
        self.pin_m1(c, dr1[0].left - 2.0, y_co - 0.3, "co")
        self._via12(c, vs12, dr2[-1].right + 2.0, y_co2 + 0.20)
        self.box_m2(c, dr2[-1].right, y_co2, dr2[-1].right + 2.3, y_co2 + 0.40)
        self.box_m1(c, dr2[-1].right + 1.7, y_co2 - 0.5,
                    dr2[-1].right + 2.3, y_co2 + 0.40)
        self.pin_m1(c, dr2[-1].right + 2.0, y_co2 - 0.3, "co2")

        # rhigh: bot→co/co2, top→vdd; bulk via ptap→gnd [PDK 3-node]
        def rhigh_terms(trans):
            cols = [s.bbox().transformed(trans).to_dtype(self.ly.dbu)
                    for s in self.ly.cell(rh).shapes(self.m1).each() if s.is_box()]
            cols.sort(key=lambda b: b.bottom)
            return cols[0], cols[-1]

        for tr, y_net, drs in ((tr1, y_co, dr1), (tr2, y_co2, dr2)):
            bot, top = rhigh_terms(tr)
            cx = 0.5 * (bot.left + bot.right)
            self.box_m1(c, bot.left - 0.05, bot.bottom - 0.5, bot.right + 0.05, bot.bottom)
            self._via12(c, vs12, cx, bot.bottom - 0.3)
            self.box_m2(c, cx - 0.30, y_net, cx + 0.30, bot.bottom - 0.1)
            self.box_m2(c, min(cx, drs[0].left) - 0.25, y_net,
                        max(cx, drs[-1].right) + 0.25, y_net + 0.40)
            self.box_m1(c, top.left - 0.05, top.top, top.right + 0.05, y_vdd + 0.40)

        # SE gates ← co2 / co via M3 crosses (never span M2 under the other drain) [LVS]
        y_sg = max(self.activ_top(mo, ts1), self.activ_top(mo, ts2)) + 2.0
        x_g_co2 = bb_s1.left - 5.0
        x_g_co = bb_s2.right + 5.0
        self._gate_bus(c, self.poly_gates(mo, ts1), self.activ_top(mo, ts1),
                       x_g_co2, y_sg, "co2_g", label=False)
        self._gate_bus(c, self.poly_gates(mo, ts2), self.activ_top(mo, ts2),
                       x_g_co, y_sg, "co_g", label=False)
        # co (dr1 @ y_co) → M1 land → via13 → M3 to mcs2 (right)
        cx1 = 0.5 * (dr1[0].left + dr1[-1].right)
        self.box_m1(c, cx1 - 0.30, y_co - 0.2, cx1 + 0.30, y_co + 0.60)
        self._via13(c, vs13, cx1, y_co + 0.20)
        self.box_m3(c, cx1 - 0.25, y_co, x_g_co + 0.25, y_co + 0.40)
        self.box_m3(c, x_g_co - 0.25, y_co, x_g_co + 0.25, y_sg + 0.40)
        self._via13(c, vs13, x_g_co, y_sg)
        # co2 (dr2 @ y_co2) → M3 to mcs1 (left); Y ≠ y_co so no M3 short either
        cx2 = 0.5 * (dr2[0].left + dr2[-1].right)
        self.box_m1(c, cx2 - 0.30, y_co2 - 0.2, cx2 + 0.30, y_co2 + 0.60)
        self._via13(c, vs13, cx2, y_co2 + 0.20)
        self.box_m3(c, x_g_co2 - 0.25, y_co2, cx2 + 0.25, y_co2 + 0.40)
        self.box_m3(c, x_g_co2 - 0.25, y_co2, x_g_co2 + 0.25, y_sg + 0.40)
        self._via13(c, vs13, x_g_co2, y_sg)

        # SE drains + PMOS
        m1_up_via_m2(ds1, y_n1)
        m1_up_via_m2(ds2, y_cmp)
        self.box_m2(c, ds1[0].left - 0.25, y_n1,
                    ds1[-1].right + 0.25, y_n1 + 0.40)
        self.box_m2(c, ds2[0].left - 0.25, y_cmp,
                    ds2[-1].right + 0.25, y_cmp + 0.40)

        m1_up_via_m2(psr1 + psr2, y_vdd)
        self.box_m2(c, psr1[0].left - 0.25, y_vdd,
                    psr2[-1].right + 0.25, y_vdd + 0.40)
        # join rhigh tops
        self.box_m1(c, bb_r1.left, y_vdd, bb_r2.right, y_vdd + 0.40)
        vx = 0.5 * (psr1[0].left + psr2[-1].right)
        self._via12(c, vs12, vx, y_vdd + 0.20)
        self.box_m1(c, vx - 0.30, y_vdd - 0.2, vx + 0.30, y_vdd + 0.60)
        self.pin_m1(c, vx, y_vdd + 0.40, "vdd")

        m1_down_to_m2(pdr1, y_n1)
        m1_down_to_m2(pdr2, y_cmp)
        self.box_m2(c, min(ds1[0].left, pdr1[0].left) - 0.25, y_n1,
                    max(ds1[-1].right, pdr1[-1].right) + 0.25, y_n1 + 0.40)
        self.box_m2(c, min(ds2[0].left, pdr2[0].left) - 0.25, y_cmp,
                    max(ds2[-1].right, pdr2[-1].right) + 0.25, y_cmp + 0.40)

        # PMOS diode gates → n1
        x_pg = min(bb_p1.left, bb_s1.left) - 3.0
        x_pg2 = max(bb_p2.right, bb_s2.right) + 3.0
        y_pad_p = self._gate_bus(
            c, self.poly_gates(mp, tp1), self.activ_top(mp, tp1),
            x_pg, self.activ_top(mp, tp1) + 1.8, "d1g", label=False)
        self._gate_bus(
            c, self.poly_gates(mp, tp2), self.activ_top(mp, tp2),
            x_pg2, self.activ_top(mp, tp2) + 1.8, "d2g", label=False)
        self._via12(c, vs12, x_pg, y_pad_p)
        self._via12(c, vs12, x_pg2, y_pad_p)
        self.box_m2(c, x_pg - 0.25, y_n1, x_pg + 0.25, y_pad_p + 0.40)
        self.box_m2(c, x_pg - 0.30, y_n1,
                    max(ds1[-1].right, pdr1[-1].right), y_n1 + 0.40)
        y_over = y_vdd + 2.5
        self.box_m2(c, x_pg2 - 0.25, y_pad_p - 0.10, x_pg2 + 0.25, y_over + 0.40)
        self.box_m2(c, x_pg - 0.25, y_over, x_pg2 + 0.25, y_over + 0.40)
        self.box_m2(c, x_pg - 0.25, y_n1, x_pg + 0.25, y_over + 0.40)

        # n1 pin + x_pg diode strap: one merged M2 island (no 0.02 µm M2.b gap)
        nx = min(ds1[0].left - 2.5, x_pg - 0.50)
        self.box_m2(c, nx - 0.40, y_n1 - 0.10,
                    max(ds1[-1].right, pdr1[-1].right) + 0.25, y_n1 + 0.50)
        # thicken vertical diode strap so it merges into the n1 bus
        self.box_m2(c, x_pg - 0.50, y_n1 - 0.10, x_pg + 0.50, y_pad_p + 0.40)
        self._via12(c, vs12, nx, y_n1 + 0.20)
        self.box_m1(c, nx - 0.30, y_n1 - 0.5, nx + 0.30, y_n1 + 0.40)
        self.pin_m1(c, nx, y_n1 - 0.3, "n1")
        ox = ds2[-1].right + 2.5
        self._via12(c, vs12, ox, y_cmp + 0.20)
        self.box_m2(c, ds2[-1].right, y_cmp, ox + 0.30, y_cmp + 0.40)
        self.box_m1(c, ox - 0.30, y_cmp - 0.5, ox + 0.30, y_cmp + 0.40)
        self.pin_m1(c, ox, y_cmp - 0.3, "cmp")

        # NW + ntap
        nw_y0 = min(bb_p1.bottom, bb_p2.bottom) - 1.0
        nw_y1 = max(bb_p1.top, bb_p2.top) + 1.5
        self.box_nw_fill(c, min(bb_p1.left, bb_p2.left) - 2.5, nw_y0,
                         max(bb_p1.right, bb_p2.right) + 1.5, nw_y1)
        ntap = self.pcell("ntap1", {"w": "0.78u", "l": "0.78u"})
        ntx = bb_p1.left - 2.0
        nty = 0.5 * (bb_p1.bottom + bb_p1.top) - 0.39
        self.place(c, ntap, ntx, nty)
        self.box_m1(c, ntx, nty, ntx + 0.78, nty + 0.78)
        self._via12(c, vs12, ntx + 0.39, nty + 0.39)
        self.box_m2(c, ntx + 0.10, nty + 0.10, ntx + 0.68, y_vdd + 0.40)
        self.box_m2(c, min(vx, ntx) - 0.30, y_vdd,
                    max(vx, ntx + 0.78) + 0.30, y_vdd + 0.40)

        abb = c.bbox().to_dtype(self.ly.dbu)
        ox0, oy0, ox1, oy1 = self._outer_ptap_gr(
            c, abb.left, abb.bottom, abb.right, abb.top, ring=1.0, gap=2.0)
        strap_x = gx - 1.5
        self._via12(c, vs12, strap_x, y_gnd + 0.20)
        self.box_m2(c, strap_x - 0.30, y_gnd, gx + 0.30, y_gnd + 0.40)
        self.box_m1(c, strap_x - 0.30, oy0, strap_x + 0.30, y_gnd + 0.40)

        bb = c.bbox().to_dtype(self.ly.dbu)
        self.cmp_area = bb.width() * bb.height() * 1e-6
        self.say(f"cmp_se bbox {bb} area={self.cmp_area:.4f} mm2")
        return c.cell_index()

    def write_spice_cmp_se(self, l=None):
        l = l or self.rhigh_l
        open(os.path.join(OUT, "cmp_se.spice"), "w").write(
            f"""* P2.7.2b cmp_se [SCH mc*/mcs*/mpl*/rc*] itt/iss2 off-cell
.subckt cmp_se hold vthn cmp vdd gnd ttail ss2 co co2 n1
Mmc1 co hold ttail gnd sg13_lv_nmos w=4.0u l=0.5u ng=2
Mmc2 co2 vthn ttail gnd sg13_lv_nmos w=4.0u l=0.5u ng=2
Mmcs1 n1 co2 ss2 gnd sg13_lv_nmos w=4.0u l=0.5u ng=2
Mmcs2 cmp co ss2 gnd sg13_lv_nmos w=4.0u l=0.5u ng=2
Mmpl1 n1 n1 vdd vdd sg13_lv_pmos w=4.0u l=0.5u ng=2
Mmpl2 cmp n1 vdd vdd sg13_lv_pmos w=4.0u l=0.5u ng=2
* terminal order + ps match extract [TOOL]
Rrc1 co vdd gnd rhigh w=0.5u l={l:.3f}u ps=0u b=0 m=1
Rrc2 co2 vdd gnd rhigh w=0.5u l={l:.3f}u ps=0u b=0 m=1
* two edge dummies combine to W=4 [LVS]
Md gnd gnd gnd gnd sg13_lv_nmos w=4.0u l=0.5u ng=1
.ends
""")
        self.say(f"wrote cmp_se.spice rhigh_l={l:.3f}u")

    # ------------------------------------------------------------------
    def build_bias_pd(self):
        """Current sinks + enable: idet/irep/itt/iss2 + diode ref [SCH ideals].

        Ports: hold, rep, ttail, ss2, en, vdd, gnd, nbias
        en high → sinks on (series NMOS to gnd).
        """
        c = self.ly.create_cell("bias_pd")
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        # sink unit 1u/1u (hold/rep); 5.5u/1u ng=2 for ~20 µA cmp tails [SCH]
        ms = self.pcell("nmos", {
            "w": "1.0u", "l": "1.0u", "ng": 1, "m": 1,
            "guardRingType": "none",
        })
        mt = self.pcell("nmos", {
            "w": W_SINK_CMP, "l": "1.0u", "ng": 2, "m": 1,
            "guardRingType": "none",
        })
        men = self.pcell("nmos", {
            "w": "2.0u", "l": "0.13u", "ng": 1, "m": 1,
            "guardRingType": "none",
        })
        # Explicit drawn l=78 µm (Calculate=R). Prior Calculate=l from R=210k
        # extracted 74.19 µm; with fixed l, extract reports the drawn value
        # [GDS bias_pd5: drawn 81.81 → extract 81.81].
        rbias_drawn_l = RHIGH_BIAS_L
        rb = self.pcell("rhigh", {
            "w": "0.5u", "l": f"{rbias_drawn_l:.3f}u", "b": 0,
            "Calculate": "R", "guardRingType": "none",
        })
        sloc = self.ly.cell(ms).bbox().to_dtype(self.ly.dbu)
        tloc = self.ly.cell(mt).bbox().to_dtype(self.ly.dbu)
        eloc = self.ly.cell(men).bbox().to_dtype(self.ly.dbu)
        rloc = self.ly.cell(rb).bbox().to_dtype(self.ly.dbu)

        gap = 4.0  # keep neighbour M1 via lands ≥0.18 apart [DRC M1.b]
        # Row: diode | id_h | id_r | id_tt | id_ss   then en switches below
        x = 0.0
        devices = []
        for name, cid, loc in (
            ("diode", ms, sloc), ("id_h", ms, sloc), ("id_r", ms, sloc),
            ("id_tt", mt, tloc), ("id_ss", mt, tloc),
        ):
            bb, t = self.place(c, cid, x - loc.left, 0.0)
            devices.append((name, cid, bb, t))
            x = bb.right + gap

        y_en = min(bb.bottom for _, _, bb, _ in devices) - 6.0
        x = 0.0
        ens = []
        for name, _, bb0, _ in devices:
            bb, t = self.place(c, men, x - eloc.left, y_en - eloc.bottom)
            ens.append((name, men, bb, t))
            x = bb.right + gap

        # bias R left of diode
        bb_rb, trb = self.place(
            c, rb, devices[0][2].left - rloc.width() - 4.0, 0.0 - rloc.bottom)

        def sd_of(cid, trans):
            return self._route_mos_sd(c, self.m1_cols(cid, trans), True)

        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        y_drain = max(bb.top for _, _, bb, _ in devices) + 2.5
        y_mid = min(bb.bottom for _, _, bb, _ in devices) - 2.0
        y_gnd = min(bb.bottom for _, _, bb, _ in ens) - 2.5
        y_nbias = y_drain + 3.0
        y_vdd = max(bb_rb.top, y_nbias) + 3.0
        # en Cont SOUTH of Activ (poly-only). Cont on Activ → D=G short [GDS].
        ab_min = min(self.activ_bottom(ecid, et) for _, ecid, _, et in ens)
        y_en_pad0 = ab_min - 0.55
        y_en_pad1 = y_en_pad0 - 0.50
        y_en_m2 = y_gnd - 3.0

        pin_map = {
            "diode": "nbias", "id_h": "hold", "id_r": "rep",
            "id_tt": "ttail", "id_ss": "ss2",
        }
        # Port plan [p27-layout-notes 2026-11-17]: hold WEST, rep EAST.
        # Drain taps stored; side escapes after the device loop (need full row).
        hold_drain_xy = None
        rep_drain_xy = None
        for (name, cid, bb, t), (ename, ecid, ebb, et) in zip(devices, ens):
            dr, sr = sd_of(cid, t)
            edr, esr = sd_of(ecid, et)
            for col in dr:
                self.box_m1(c, col.left, col.top - 0.05, col.right, y_drain)
            self.box_m1(c, dr[0].left, y_drain, dr[-1].right, y_drain + 0.40)
            if name == "diode":
                gates = self.poly_gates(cid, t)
                at = self.activ_top(cid, t)
                self._gate_bus(c, gates, at, bb.left - 2.0, y_nbias, "nbias")
                self.box_m1(c, bb.left - 2.3, y_drain, bb.left - 1.7, y_nbias)
                self.box_m1(c, dr[0].left, y_drain, bb.left - 1.7, y_drain + 0.40)
            elif name in ("id_h", "id_r"):
                px = 0.5 * (dr[0].left + dr[-1].right)
                self.box_m1(c, px - 0.20, y_drain, px + 0.20, y_drain + 0.50)
                self._via12(c, vs12, px, y_drain + 0.20)
                if name == "id_h":
                    hold_drain_xy = (px, y_drain + 0.20)
                else:
                    rep_drain_xy = (px, y_drain + 0.20)
            else:
                px = 0.5 * (dr[0].left + dr[-1].right)
                self.pin_m1(c, px, y_drain + 0.60, pin_map[name])
                self.box_m1(c, px - 0.20, y_drain, px + 0.20, y_drain + 0.80)
            for col in sr:
                self.box_m1(c, col.left, y_mid, col.right, col.bottom)
            self.box_m1(c, sr[0].left, y_mid, sr[-1].right, y_mid + 0.40)
            for col in edr:
                self.box_m1(c, col.left, col.top - 0.05, col.right, y_mid + 0.40)
            self.box_m1(c, edr[0].left, y_mid, edr[-1].right, y_mid + 0.40)
            self.box_m1(c, min(sr[0].left, edr[0].left), y_mid,
                        max(sr[-1].right, edr[-1].right), y_mid + 0.40)
            for col in esr:
                self.box_m1(c, col.left, y_gnd, col.right, col.bottom)
            self.box_m1(c, esr[0].left, y_gnd, esr[-1].right, y_gnd + 0.40)
            # en Cont: poly south of Activ, then WEST off Activ — Cont M1 clear
            # of S/D M1 [DRC M1.b]; Cont on poly-only [LVS]
            gates = self.poly_gates(ecid, et)
            ab = self.activ_bottom(ecid, et)
            al = self.activ_left(ecid, et)
            g0, g1 = gates[0], gates[-1]
            x_en = al - 2.8
            for g in gates:
                gx = 0.5 * (g.left + g.right)
                half = 0.5 * (g.right - g.left)
                c.shapes(self.poly).insert(
                    pya.DBox(gx - half, y_en_pad0 - 0.05, gx + half, g.bottom + 0.05))
            c.shapes(self.poly).insert(
                pya.DBox(g0.left - 0.05, y_en_pad1, g1.right + 0.05, y_en_pad0))
            c.shapes(self.poly).insert(
                pya.DBox(x_en - 0.20, y_en_pad1, g0.left + 0.05, y_en_pad0))
            c.shapes(self.poly).insert(
                pya.DBox(x_en - 0.25, y_en_pad1, x_en + 0.25, y_en_pad0))
            if y_en_pad0 - 0.16 >= ab - 0.05:
                raise RuntimeError(
                    f"en Cont on Activ cont_top={y_en_pad0-0.16:.3f} ab={ab:.3f}")
            c.shapes(self.cont).insert(
                pya.DBox(x_en - 0.08, y_en_pad0 - 0.32, x_en + 0.08, y_en_pad0 - 0.16))
            self.box_m1(c, x_en - 0.20, y_en_pad1 - 0.05, x_en + 0.20, y_en_pad0 - 0.05)
            self.box_m2(c, x_en - 0.30, y_en_m2, x_en + 0.30, y_en_pad1 + 0.10)
            self.place(c, vs12, x_en, y_en_pad1)

        # hold WEST / rep EAST on distinct M2 Y (plan 2026-11-17)
        row_left = min(bb.left for _, _, bb, _ in devices)
        row_right = max(bb.right for _, _, bb, _ in devices)
        if hold_drain_xy is None or rep_drain_xy is None:
            raise RuntimeError("bias_pd: missing hold/rep drain taps")
        hx, hy0 = hold_drain_xy
        rx, ry0 = rep_drain_xy
        # Both escapes SOUTH of drains — north path crosses nbias M2 bus at
        # y_nbias [LVS hold|nbias]. Distinct Y; hold west, rep east.
        y_hold_m2 = y_mid - 1.5
        y_rep_m2 = y_mid - 4.0
        x_hold_pin = row_left - 3.5
        x_rep_pin = row_right + 3.5
        # hold: drain via → M2 south → west → pin
        self.box_m2(c, hx - 0.25, min(hy0, y_hold_m2) - 0.25,
                    hx + 0.25, max(hy0, y_hold_m2) + 0.25)
        self.box_m2(c, min(hx, x_hold_pin) - 0.25, y_hold_m2 - 0.25,
                    max(hx, x_hold_pin) + 0.25, y_hold_m2 + 0.25)
        self._via12(c, vs12, x_hold_pin, y_hold_m2)
        self.box_m1(c, x_hold_pin - 0.30, y_hold_m2 - 0.30,
                    x_hold_pin + 0.30, y_hold_m2 + 0.30)
        self.pin_m1(c, x_hold_pin, y_hold_m2, "hold")
        # rep: drain via → M2 south → east → pin
        self.box_m2(c, rx - 0.25, min(ry0, y_rep_m2) - 0.25,
                    rx + 0.25, max(ry0, y_rep_m2) + 0.25)
        self.box_m2(c, min(rx, x_rep_pin) - 0.25, y_rep_m2 - 0.25,
                    max(rx, x_rep_pin) + 0.25, y_rep_m2 + 0.25)
        self._via12(c, vs12, x_rep_pin, y_rep_m2)
        self.box_m1(c, x_rep_pin - 0.30, y_rep_m2 - 0.30,
                    x_rep_pin + 0.30, y_rep_m2 + 0.30)
        self.pin_m1(c, x_rep_pin, y_rep_m2, "rep")

        self.box_m2(c, ens[0][2].left - 4.0, y_en_m2,
                    ens[-1][2].right + 3.0, y_en_m2 + 0.40)
        ex = ens[-1][2].right + 2.5
        self.box_m2(c, ex - 0.30, y_en_m2, ex + 0.30, y_en_m2 + 0.40)
        self.box_m1(c, ex - 0.20, y_en_m2 - 0.2, ex + 0.20, y_en_m2 + 0.40)
        self.place(c, vs12, ex, y_en_m2 + 0.20)
        self.pin_m1(c, ex, y_en_m2 - 0.4, "en")

        r_m1 = []
        for s in self.ly.cell(rb).shapes(self.m1).each():
            if s.is_box():
                r_m1.append(s.bbox().transformed(trb).to_dtype(self.ly.dbu))
        r_m1.sort(key=lambda b: b.bottom)
        rbot, rtop = r_m1[0], r_m1[-1]
        self.box_m1(c, rbot.left, rbot.bottom - 0.5, rbot.right, rbot.bottom)
        self.box_m1(c, rbot.left - 0.1, y_nbias, rbot.right + 0.1, rbot.bottom)
        self.box_m1(c, rbot.left - 0.1, y_nbias, devices[0][2].left, y_nbias + 0.40)
        self.box_m1(c, rtop.left, rtop.top, rtop.right, y_vdd + 0.40)
        self.box_m1(c, rtop.left, y_vdd, rtop.right + 4.0, y_vdd + 0.40)
        self.pin_m1(c, rtop.right + 2.0, y_vdd + 0.20, "vdd")

        self.box_m1(c, ens[0][2].left, y_gnd, ens[-1][2].right, y_gnd + 0.40)
        self.pin_m1(c, ens[0][2].left - 2.0, y_gnd - 0.2, "gnd")
        self.box_m1(c, ens[0][2].left - 2.3, y_gnd, ens[0][2].left, y_gnd + 0.40)

        # sink gates → Cont WEST of Activ on poly north of Activ [DRC M1.b]
        for name, cid, bb, t in devices:
            if name == "diode":
                continue
            gates = self.poly_gates(cid, t)
            at = self.activ_top(cid, t)
            al = self.activ_left(cid, t)
            g0, g1 = gates[0], gates[-1]
            y_pad0 = max(at + 0.55, max(g.top for g in gates) + 0.35)
            y_pad1 = y_pad0 + 0.50
            x_g = al - 2.8
            for g in gates:
                gx = 0.5 * (g.left + g.right)
                half = 0.5 * (g.right - g.left)
                c.shapes(self.poly).insert(
                    pya.DBox(gx - half, g.top - 0.05, gx + half, y_pad0 + 0.05))
            c.shapes(self.poly).insert(
                pya.DBox(g0.left - 0.05, y_pad0, g1.right + 0.05, y_pad1))
            c.shapes(self.poly).insert(
                pya.DBox(x_g - 0.20, y_pad0, g0.left + 0.05, y_pad1))
            c.shapes(self.poly).insert(
                pya.DBox(x_g - 0.25, y_pad0, x_g + 0.25, y_pad1))
            c.shapes(self.cont).insert(
                pya.DBox(x_g - 0.08, y_pad0 + 0.16, x_g + 0.08, y_pad0 + 0.32))
            self.box_m1(c, x_g - 0.20, y_pad0 + 0.10, x_g + 0.20, y_pad0 + 0.70)
            self.box_m2(c, x_g - 0.30, y_pad0 + 0.10, x_g + 0.30, y_nbias + 0.40)
            self.place(c, vs12, x_g, y_pad0 + 0.40)
        self.box_m2(c, devices[0][2].left - 4.0, y_nbias,
                    devices[-1][2].right, y_nbias + 0.40)
        dx = devices[0][2].left - 2.0
        self.box_m1(c, dx - 0.20, y_nbias, dx + 0.20, y_nbias + 0.40)
        self.box_m2(c, dx - 0.30, y_nbias, dx + 0.30, y_nbias + 0.40)
        self.place(c, vs12, dx, y_nbias + 0.20)

        abb = c.bbox().to_dtype(self.ly.dbu)
        ox0, oy0, ox1, oy1 = self._outer_ptap_gr(
            c, abb.left, abb.bottom, abb.right, abb.top, ring=1.0, gap=1.5)
        self.box_m1(c, ox0, y_gnd, ens[0][2].left, y_gnd + 0.40)

        bb = c.bbox().to_dtype(self.ly.dbu)
        self.bias_area = bb.width() * bb.height() * 1e-6
        self.say(
            f"bias_pd bbox {bb} area={self.bias_area:.4f} mm2 "
            f"rbias_drawn_l={rbias_drawn_l:.2f}u target_extract={RHIGH_BIAS_L}u"
        )
        return c.cell_index()

    def write_spice_bias_pd(self):
        open(os.path.join(OUT, "bias_pd.spice"), "w").write(
            f"""* P2.7.2b bias_pd: MOS sinks + en PD [SCH retune I_hold=4u I_tt=20u]
.subckt bias_pd hold rep ttail ss2 en vdd gnd nbias
Rrbias vdd nbias gnd rhigh w=0.5u l={RHIGH_BIAS_L:.3f}u ps=0u b=0 m=1
Mdiode nbias nbias pd_d gnd sg13_lv_nmos w=1.0u l=1.0u ng=1
Men_d pd_d en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_h hold nbias pd_h gnd sg13_lv_nmos w=1.0u l=1.0u ng=1
Men_h pd_h en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_r rep nbias pd_r gnd sg13_lv_nmos w=1.0u l=1.0u ng=1
Men_r pd_r en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_tt ttail nbias pd_tt gnd sg13_lv_nmos w={W_SINK_CMP} l=1.0u ng=2
Men_tt pd_tt en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_ss ss2 nbias pd_ss gnd sg13_lv_nmos w={W_SINK_CMP} l=1.0u ng=2
Men_ss pd_ss en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
.ends
""")
        self.say(f"wrote bias_pd.spice rbias_l={RHIGH_BIAS_L} tt={W_SINK_CMP}")

    # ------------------------------------------------------------------
    def build_ampcal_det(self, routed=None):
        """Join: det_sf_pair + hold_caps + cmp_se + bias_pd + cl_cmp.

        Net groups (--nets): place | power | bias | hold | rep | taps | cmp | en | all.
        (aliases: cl→cmp, ports→taps+en). Order: power → nbias → hold → rep → taps →
        cmp → en. cbf lesson: cmim M5=gnd / TM1=signal — no via over M5 plate.
        """
        if routed is None:
            routed = {"place", "power", "bias", "hold", "rep", "taps", "cmp", "en"}
        else:
            routed = set(routed)
            routed.add("place")
            if "cl" in routed:
                routed.add("cmp")
            if "ports" in routed:
                routed.update({"taps", "en"})
        self.say(f"ampcal_det routed={sorted(routed)}")

        c = self.ly.create_cell("ampcal_det")
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs23 = self.pcell("via_stack", {
            "b_layer": "Metal2", "t_layer": "Metal3",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs13 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal3",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs1t = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "TopMetal1",
            "vn_columns": 1, "vn_rows": 1,
        })
        mim = self.pcell("cmim", {
            "w": f"{CMIM_CMP:.3f}u", "l": f"{CMIM_CMP:.3f}u",
            "C": "50f", "Calculate": "w&l", "guardRingType": "none",
        })
        vs5 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal5",
            "vn_columns": 2, "vn_rows": 2,
        })

        sf_cid, sf_pins = self._copy_no_pin_texts("det_sf_pair", "det_sf_pair_np")
        hc_cid, hc_pins = self._copy_no_pin_texts("hold_caps", "hold_caps_np")
        cm_cid, cm_pins = self._copy_no_pin_texts("cmp_se", "cmp_se_np")
        bp_cid, bp_pins = self._copy_no_pin_texts("bias_pd", "bias_pd_np")

        # Edge-aware gap; start 4 µm (was 6) — widen only if DRC needs it.
        gap = 4.0
        sf_loc = self.ly.cell(sf_cid).bbox().to_dtype(self.ly.dbu)
        cm_loc = self.ly.cell(cm_cid).bbox().to_dtype(self.ly.dbu)
        bp_loc = self.ly.cell(bp_cid).bbox().to_dtype(self.ly.dbu)
        mim_loc = self.ly.cell(mim).bbox().to_dtype(self.ly.dbu)

        hc_bb, hc_t = self.place(c, hc_cid, 0.0, 0.0)
        sf_y = hc_bb.top + gap - sf_loc.bottom
        sf_bb, sf_t = self.place(c, sf_cid, 0.0, sf_y)
        cm_x = max(sf_bb.right, hc_bb.right) + gap - cm_loc.left
        cm_y = 0.0 - cm_loc.bottom
        cm_bb, cm_t = self.place(c, cm_cid, cm_x, cm_y)
        bp_x = cm_bb.right + gap - bp_loc.left
        bp_y = 0.0 - bp_loc.bottom
        bp_bb, bp_t = self.place(c, bp_cid, bp_x, bp_y)
        # cl_cmp east of cmp, clear of bias; above cmp top
        cl_x = cm_bb.right + 1.0 - mim_loc.left
        if cl_x + mim_loc.right > bp_bb.left - 2.0:
            cl_x = cm_bb.left + 2.0 - mim_loc.left
        cl_y = cm_bb.top + gap - mim_loc.bottom
        cl_bb, cl_t = self.place(c, mim, cl_x, cl_y)

        sf_p = self._pins_abs(sf_pins, sf_t)
        hc_p = self._pins_abs(hc_pins, hc_t)
        cm_p = self._pins_abs(cm_pins, cm_t)
        bp_p = self._pins_abs(bp_pins, bp_t)

        # ---- routing plan helpers (spec/p27-layout-notes 2026-11-17) ----
        # M2 = H only; M3 = V only; no inter-cell M1; TM1 = hold/rep only.
        via_done = set()

        def via12_at(x, y):
            key = ("12", round(x, 3), round(y, 3))
            if key in via_done:
                return
            via_done.add(key)
            self._via12(c, vs12, x, y)

        def via23_at(x, y):
            key = ("23", round(x, 3), round(y, 3))
            if key in via_done:
                return
            via_done.add(key)
            self.box_m2(c, x - 0.32, y - 0.32, x + 0.32, y + 0.32)
            self.box_m3(c, x - 0.32, y - 0.32, x + 0.32, y + 0.32)
            self.place(c, vs23, x, y)

        def via13_at(x, y):
            key = ("13", round(x, 3), round(y, 3))
            if key in via_done:
                return
            via_done.add(key)
            self.box_m1(c, x - 0.30, y - 0.30, x + 0.30, y + 0.30)
            self.box_m3(c, x - 0.30, y - 0.30, x + 0.30, y + 0.30)
            self.place(c, vs13, x, y)

        def via1t_at(x, y):
            """M1↔TM1 — only outside cmim M5 plates [cbf]."""
            key = ("1t", round(x, 3), round(y, 3))
            if key in via_done:
                return
            via_done.add(key)
            self.box_m1(c, x - 0.35, y - 0.35, x + 0.35, y + 0.35)
            c.shapes(self.tm1).insert(pya.DBox(x - 0.50, y - 0.50, x + 0.50, y + 0.50))
            self.place(c, vs1t, x, y)

        def m2h(x0, y, x1, w=0.50):
            h = 0.5 * w
            self.box_m2(c, min(x0, x1) - h, y - h, max(x0, x1) + h, y + h)

        def m3v(x, y0, y1, w=0.50):
            h = 0.5 * w
            self.box_m3(c, x - h, min(y0, y1) - h, x + h, max(y0, y1) + h)

        def pin_to_m2_track(pin, x_col, y_track, add_via12=True, m2_y=None):
            """M2 H at m2_y to x_col → via23 → M3 V to y_track.

            m2_y defaults to pin Y. For power pins the cell via/M2 rail is
            often pin_y−0.20 (vdd) or pin_y+1.20 (gnd) — attach there so M2
            merges with the child rail (not a floating pad at pin text) [DRC].
            add_via12=False when the child already has Via1 on that rail.
            """
            px, py = pin
            my = py if m2_y is None else m2_y
            if add_via12:
                via12_at(px, my)
            # Fat merge pad on the rail [DRC M2.b]
            self.box_m2(c, px - 0.50, my - 0.50, px + 0.50, my + 0.50)
            m2h(px, my, x_col, w=0.60)
            via23_at(x_col, my)
            m3v(x_col, my, y_track)
            via23_at(x_col, y_track)

        def tap_to_tm1(pin, x_col, y_tm, add_via12=True, m2_y=None):
            """Pin → M2 H → M3 V → via12+via1t onto TM1 (no via13).

            via12 (M1↔M2) + via1t (M1↔TM1) share M1 at the landing. Avoid via13
            so a long M3 column does not also stack M1 into a gnd via pad [LVS].
            """
            pin_to_m2_track(pin, x_col, y_tm, add_via12=add_via12, m2_y=m2_y)
            via12_at(x_col, y_tm)
            via1t_at(x_col, y_tm)

        # Landing columns / tracks [plan] — always computed (used by later groups)
        # Hold via1t Xs must stay ≥1.0 µm from power M3 lanes (cell±1.5) or
        # M3 merges → gnd|hold [TOOL extract 2026-11-17].
        x_w_h = sf_bb.left - 4.5          # vs SF gnd lane sf_bb.left−1.5
        # SF rep M3: east of SF vdd (+1.5) but WEST of hold_caps right-cmim
        # via_stack M3 (≈28.9) — +3.5 sat at 0.065 µm → M3.b [TOOL DRC]
        x_e_sf = sf_bb.right + 2.8
        x_hc = hc_bb.right + 0.8          # NOT mid-gap (was ≈ cm gnd lane)
        # ttail/ss2 column: west of gap. Mid-gap sat on nbias (bp.left−1.5)
        # and formerly on cmp vdd (cm.right+1.5) → ttail|ss2|nbias|vdd [TOOL].
        x_cb = cm_bb.right + 1.0
        x_nbias_col = bp_bb.left - 1.5
        x_bh = max(cm_bb.right + 3.0, bp_bb.left - 3.5)  # bias hold; clear cm vdd
        x_br = bp_bb.right + 3.5          # bias rep; clear bp vdd/gnd at +1.5
        x_e = bp_bb.right + 3.0
        y_vdd = max(sf_bb.top, cm_bb.top, bp_bb.top, cl_bb.top) + 3.0
        y_gnd = min(sf_bb.bottom, hc_bb.bottom, cm_bb.bottom,
                    bp_bb.bottom) - 3.0
        # TM1 half-width 0.9; need centre gap ≥ 0.9+0.9+1.8=3.6 [DRC TM1.b]
        y_rep_jog = hc_bb.bottom - 1.5
        y_hold = y_rep_jog - 4.0   # was bottom−4 → only 2.5 to jog → TM1.b
        y_rep = y_hold - 5.0

        # ---- power: M2 H spines; M3 drops in corridors [plan amend] ----
        # M3 outside child bboxes (clear of SF ct / cmp co M3). Attach M2 at
        # the cell via rail Y, not pin-text Y. hold_caps gnd: M1-only → via12.
        if "power" in routed:
            # (pin, x_col, m2_y, add_via12)
            # cmp vdd: M3 at pin X — cell.right+1.5 forced M2 H across
            # cmp_se x_pg2 (n1 diode strap) → n1|vdd [TOOL extract/BFS].
            vdd_spec = [
                (sf_p["vdd"], sf_bb.right + 1.5, sf_p["vdd"][1] - 0.20, False),
                (cm_p["vdd"], cm_p["vdd"][0], cm_p["vdd"][1] - 0.20, False),
                # bias_pd vdd is M1-only (no cell via) [GDS]
                (bp_p["vdd"], bp_bb.right + 1.5, bp_p["vdd"][1], True),
            ]
            # bias gnd: do NOT attach at bp_p["gnd"] Y — that M2 H crosses the
            # en gate M2 straps (y_en_m2→pad) → en|gnd [TOOL extract]. Tap the
            # east ptap-GR M1 instead, above the en strap tops.
            y_bp_gnd_tap = max(bp_p["gnd"][1] + 8.0, 20.0)
            x_bp_gnd_m1 = bp_bb.right - 0.5  # on east GR M1
            gnd_spec = [
                (sf_p["gnd"], sf_bb.left - 1.5, sf_p["gnd"][1] + 1.20, False),
                (hc_p["gnd"], hc_bb.left - 1.5, hc_p["gnd"][1], True),
                (cm_p["gnd"], cm_bb.left - 1.5, cm_p["gnd"][1] + 1.20, False),
                ((x_bp_gnd_m1, y_bp_gnd_tap), bp_bb.right + 1.5,
                 y_bp_gnd_tap, True),
            ]
            vdd_xs, gnd_xs = [], []
            for pin, x_col, my, need12 in vdd_spec:
                pin_to_m2_track(pin, x_col, y_vdd, add_via12=need12, m2_y=my)
                vdd_xs.append(x_col)
            m2h(min(vdd_xs), y_vdd, max(vdd_xs), w=0.60)
            for pin, x_col, my, need12 in gnd_spec:
                pin_to_m2_track(pin, x_col, y_gnd, add_via12=need12, m2_y=my)
                gnd_xs.append(x_col)
            m2h(min(gnd_xs), y_gnd, max(gnd_xs), w=0.60)

        # ---- nbias / ttail / ss2: M2 H + M3 at x_cb [plan] ----
        if "bias" in routed:
            # bias_pd M2 is dense: nbias gate straps (drain band), hold/rep
            # drops, en straps (rep→en). No clear M2 H channel through the
            # cell [TOOL extract ttail|nbias, hold|rep|ttail, en|rep|ttail].
            # Amend: M3 V at pin X through the nbias band (M3∤M2), then M2 H
            # ABOVE the nbias bus (no bias M2 above it [GDS]), west to x_cb.
            y_tt_hi = bp_p["nbias"][1] + 1.20
            y_ss_hi = bp_p["nbias"][1] + 2.40
            bias_tt_y = {"ttail": y_tt_hi, "ss2": y_ss_hi}
            for nm in ("ttail", "ss2"):
                # cmp_se: pin south of M2 bus; Via1 in child → attach pin_y+1.20
                py_c = cm_p[nm][1]
                my_c = py_c + 1.20
                pin_to_m2_track(cm_p[nm], x_cb, my_c, add_via12=False, m2_y=my_c)
                # bias_pd: M1 pin → via12 → via23 → M3 V → M2 H above nbias
                px_b, py_b = bp_p[nm]
                y_hi = bias_tt_y[nm]
                via12_at(px_b, py_b)
                via23_at(px_b, py_b)
                m3v(px_b, py_b, y_hi)
                via23_at(px_b, y_hi)
                self.box_m2(c, px_b - 0.50, y_hi - 0.50, px_b + 0.50, y_hi + 0.50)
                m2h(px_b, y_hi, x_cb, w=0.60)
                via23_at(x_cb, y_hi)
                m3v(x_cb, my_c, y_hi)
            if "nbias" in bp_p:
                # nbias pin already on M2 bus + via12 in cell; column ≠ x_cb
                pin_to_m2_track(bp_p["nbias"], x_nbias_col,
                                bp_p["nbias"][1], add_via12=False,
                                m2_y=bp_p["nbias"][1])

        # ---- hold (TM1 spine + taps); rep is a separate --nets group ----
        if "hold" in routed:
            hx_h, hy_h = hc_p["hold"]
            # hold TM1: south → west to x_w_h → south → east spine
            c.shapes(self.tm1).insert(pya.DBox(
                hx_h - 0.9, min(hy_h, y_rep_jog) - 0.9,
                hx_h + 0.9, max(hy_h, y_rep_jog) + 0.9))
            c.shapes(self.tm1).insert(pya.DBox(
                min(hx_h, x_w_h) - 0.9, y_rep_jog - 0.9,
                max(hx_h, x_w_h) + 0.9, y_rep_jog + 0.9))
            c.shapes(self.tm1).insert(pya.DBox(
                x_w_h - 0.9, min(y_rep_jog, y_hold) - 0.9,
                x_w_h + 0.9, max(y_rep_jog, y_hold) + 0.9))
            # Spine only to hold landings — not through x_rep drop [LVS hold|rep]
            x_hold_end = max(x_w_h, x_hc, x_bh)
            c.shapes(self.tm1).insert(pya.DBox(
                min(x_w_h, x_hold_end) - 0.9, y_hold - 0.9,
                max(x_w_h, x_hold_end) + 0.9, y_hold + 0.9))
            tap_to_tm1(sf_p["hold"], x_w_h, y_hold, add_via12=False,
                       m2_y=sf_p["hold"][1] + 1.20)
            tap_to_tm1(cm_p["hold"], x_hc, y_hold, add_via12=True)
            tap_to_tm1(bp_p["hold"], x_bh, y_hold, add_via12=False)

        if "rep" in routed:
            hx_r, hy_r = hc_p["rep"]
            # Drop south EAST of hold spine end so TM1 V never crosses y_hold
            # hold H [TOOL extract hold|rep].
            x_hold_end = max(x_w_h, x_hc, x_bh)
            x_rep_drop = max(x_br, x_hold_end) + 2.5
            c.shapes(self.tm1).insert(pya.DBox(
                hx_r - 0.9, min(hy_r, y_rep_jog) - 0.9,
                hx_r + 0.9, max(hy_r, y_rep_jog) + 0.9))
            c.shapes(self.tm1).insert(pya.DBox(
                min(hx_r, x_rep_drop) - 0.9, y_rep_jog - 0.9,
                max(hx_r, x_rep_drop) + 0.9, y_rep_jog + 0.9))
            c.shapes(self.tm1).insert(pya.DBox(
                x_rep_drop - 0.9, min(y_rep_jog, y_rep) - 0.9,
                x_rep_drop + 0.9, max(y_rep_jog, y_rep) + 0.9))
            c.shapes(self.tm1).insert(pya.DBox(
                min(x_e_sf, x_rep_drop) - 0.9, y_rep - 0.9,
                max(x_e_sf, x_rep_drop) + 0.9, y_rep + 0.9))
            tap_to_tm1(sf_p["rep"], x_e_sf, y_rep, add_via12=False,
                       m2_y=sf_p["rep"][1] + 1.20)
            tap_to_tm1(bp_p["rep"], x_br, y_rep, add_via12=False)

        # ---- detector taps (tank west labels) ----
        if "taps" in routed:
            for name in ("tp", "tn", "ct"):
                self.pin_m1(c, sf_p[name][0], sf_p[name][1], name)
            self.pin_m1(c, sf_p["hold"][0], sf_p["hold"][1], "hold")
            self.pin_m1(c, sf_p["rep"][0], sf_p["rep"][1], "rep")
            self.pin_m1(c, sf_p["vdd"][0], sf_p["vdd"][1], "vdd")
            self.pin_m1(c, sf_p["gnd"][0], sf_p["gnd"][1], "gnd")

        # ---- comparator: cl_cmp + cmp out [plan amend] ----
        # Separate east M3 columns: MINUS→gnd on x_cmp_gnd, PLUS/cmp on
        # x_cmp_m3. Sharing one column merged cmp|gnd (M3 through y_esc) [TOOL].
        # x_cmp_gnd must sit between bias gnd lane (+1.5) and rep tap (+3.5)
        # with ≥0.21 M3 space — +3.0 touched x_br → gnd|rep [TOOL extract].
        x_cmp_gnd = bp_bb.right + 2.5
        x_cmp_m3 = bp_bb.right + 5.5
        x_en_m3 = bp_bb.right + 8.5
        y_cmp = max(cm_bb.top, cl_bb.top) + 2.0

        if "cmp" in routed:
            def lyr_boxes(cid, trans, layer):
                out = []
                for s in self.ly.cell(cid).shapes(layer).each():
                    if s.is_box():
                        out.append(
                            s.bbox().transformed(trans).to_dtype(self.ly.dbu))
                return out

            def biggest(boxes):
                return max(
                    boxes,
                    key=lambda b: (b.right - b.left) * (b.top - b.bottom))

            m5 = biggest(lyr_boxes(mim, cl_t, self.m5))
            tm = biggest(lyr_boxes(mim, cl_t, self.tm1))
            # MINUS (M5) → gnd on x_cmp_gnd only. No via12 on vs5 [DRC V1.b].
            mx = 0.5 * (m5.left + m5.right)
            y_vs = m5.bottom - 1.5
            bb_vs, _ = self.place(c, vs5, mx, y_vs)
            # M5 must cover via stack → plate; prior bridge only at plate
            # left a 1 µm gap to vs5 M5 → MINUS floating [TOOL extract]
            self.box_m5(c, min(bb_vs.left, m5.left),
                        min(bb_vs.bottom, m5.bottom) - 0.2,
                        max(bb_vs.right, m5.right), m5.bottom + 0.3)
            self.box_m1(c, bb_vs.left - 0.1, bb_vs.bottom - 0.3,
                        bb_vs.right + 0.1, bb_vs.top + 0.1)
            m2h(mx, y_vs, x_cmp_gnd)
            via23_at(x_cmp_gnd, y_vs)
            m3v(x_cmp_gnd, y_vs, y_gnd)
            via23_at(x_cmp_gnd, y_gnd)
            x_gnd_east = bp_bb.right + 1.5
            m2h(x_gnd_east, y_gnd, x_cmp_gnd, w=0.60)

            # PLUS (TM1) → x_cmp_m3 → cmp pin. via1t has M2 — no via12 [V1.b].
            tcx = 0.5 * (tm.left + tm.right)
            y_esc = m5.bottom - 3.0
            c.shapes(self.tm1).insert(pya.DBox(
                tcx - 1.0, y_esc - 0.5, tcx + 1.0, tm.bottom + 0.5))
            c.shapes(self.tm1).insert(pya.DBox(
                min(tcx, x_cmp_m3) - 0.9, y_esc - 0.9,
                max(tcx, x_cmp_m3) + 0.9, y_esc + 0.9))
            via1t_at(x_cmp_m3, y_esc)
            cx, cy = cm_p["cmp"]
            via23_at(x_cmp_m3, y_esc)
            m3v(x_cmp_m3, y_esc, y_cmp)
            via23_at(x_cmp_m3, y_cmp)
            m2h(x_cmp_m3, y_cmp, cx)
            via23_at(cx, y_cmp)
            m3v(cx, y_cmp, cy)
            via23_at(cx, cy)
            self.box_m2(c, cx - 0.40, cy - 0.40, cx + 0.40, cy + 0.40)
            self.pin_m1(c, cx, cy, "cmp")
            self.pin_m1(c, cm_p["vthn"][0], cm_p["vthn"][1], "vthn")

        # ---- en: own east M3 column (x_en_m3), away from tank / V_tune ----
        # Attach on the cell en M2 bus (pin_y+0.60), not pin text Y — pin text
        # sits 0.40 below the bus → M2.b notch vs bus [TOOL DRC]. Jog NORTH on
        # M3 to clear bias gnd M1 rail / power lane before the M1 pin [LVS en|gnd].
        if "en" in routed:
            ex, ey = bp_p["en"]
            ey_bus = ey + 0.60
            y_en_pin = max(ey_bus + 6.0, bp_p["gnd"][1] + 4.0)
            # merge onto cell en bus; no extra via12 at pin (cell has Via1)
            self.box_m2(c, ex - 0.40, ey_bus - 0.30, ex + 0.40, ey_bus + 0.30)
            m2h(ex, ey_bus, x_en_m3, w=0.60)
            via23_at(x_en_m3, ey_bus)
            m3v(x_en_m3, ey_bus, y_en_pin)
            via23_at(x_en_m3, y_en_pin)
            via12_at(x_en_m3, y_en_pin)
            self.pin_m1(c, x_en_m3, y_en_pin, "en")

        bb = c.bbox().to_dtype(self.ly.dbu)
        self.det_top_area = bb.width() * bb.height() * 1e-6
        self.det_top_bb = bb
        self.say(f"ampcal_det bbox {bb} area={self.det_top_area:.4f} mm2 gap={gap}")
        return c.cell_index()

    def write_spice_ampcal_det(self, hold_w=None, rhigh_l=None, cmim_cmp_w=None):
        hold_w = hold_w or self.cmim_hold_w
        rhigh_l = rhigh_l or self.rhigh_l
        # cl_cmp extract side (pcell w=CMIM_CMP → extract shrink, like hold) [TOOL]
        cmim_cmp_w = cmim_cmp_w or getattr(self, "cmim_cmp_w", None) or CMIM_CMP
        open(os.path.join(OUT, "ampcal_det.spice"), "w").write(
            f"""* P2.7.2b ampcal_det fab netlist [SCH + en/vthn; ideals→cmim/rhigh/MOS]
.subckt ampcal_det tp tn ct vdd gnd cmp hold rep en vthn
* SF peak + replica + dummies
Mmdtp vdd tp hold gnd sg13_lv_nmos w=0.5u l=0.13u ng=1
Mmdtn vdd tn hold gnd sg13_lv_nmos w=0.5u l=0.13u ng=1
Mmrtp vdd ct rep gnd sg13_lv_nmos w=0.5u l=0.13u ng=1
Mmrtn vdd ct rep gnd sg13_lv_nmos w=0.5u l=0.13u ng=1
MdL gnd gnd gnd gnd sg13_lv_nmos w=0.5u l=0.13u ng=1
MdR gnd gnd gnd gnd sg13_lv_nmos w=0.5u l=0.13u ng=1
* hold caps
Cchold hold gnd cap_cmim w={hold_w:.3f}u l={hold_w:.3f}u m=1
Ccrep rep gnd cap_cmim w={hold_w:.3f}u l={hold_w:.3f}u m=1
* bias + PD [SCH retune]
Rrbias vdd nbias gnd rhigh w=0.5u l={RHIGH_BIAS_L:.3f}u ps=0u b=0 m=1
Mdiode nbias nbias pd_d gnd sg13_lv_nmos w=1.0u l=1.0u ng=1
Men_d pd_d en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_h hold nbias pd_h gnd sg13_lv_nmos w=1.0u l=1.0u ng=1
Men_h pd_h en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_r rep nbias pd_r gnd sg13_lv_nmos w=1.0u l=1.0u ng=1
Men_r pd_r en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_tt ttail nbias pd_tt gnd sg13_lv_nmos w={W_SINK_CMP} l=1.0u ng=2
Men_tt pd_tt en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_ss ss2 nbias pd_ss gnd sg13_lv_nmos w={W_SINK_CMP} l=1.0u ng=2
Men_ss pd_ss en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
* comparator
Mmc1 co hold ttail gnd sg13_lv_nmos w=4.0u l=0.5u ng=2
Mmc2 co2 vthn ttail gnd sg13_lv_nmos w=4.0u l=0.5u ng=2
Mmcs1 n1 co2 ss2 gnd sg13_lv_nmos w=4.0u l=0.5u ng=2
Mmcs2 cmp co ss2 gnd sg13_lv_nmos w=4.0u l=0.5u ng=2
Mmpl1 n1 n1 vdd vdd sg13_lv_pmos w=4.0u l=0.5u ng=2
Mmpl2 cmp n1 vdd vdd sg13_lv_pmos w=4.0u l=0.5u ng=2
* rhigh pin order co/co2,vdd,gnd — match extract / cmp_se [TOOL LVS]
Rrc1 co vdd gnd rhigh w=0.5u l={rhigh_l:.3f}u ps=0u b=0 m=1
Rrc2 co2 vdd gnd rhigh w=0.5u l={rhigh_l:.3f}u ps=0u b=0 m=1
MdLc gnd gnd gnd gnd sg13_lv_nmos w=2.0u l=0.5u ng=1
MdRc gnd gnd gnd gnd sg13_lv_nmos w=2.0u l=0.5u ng=1
Ccl_cmp cmp gnd cap_cmim w={cmim_cmp_w:.3f}u l={cmim_cmp_w:.3f}u m=1
.ends
""")
        self.say(
            f"wrote ampcal_det.spice hold_w={hold_w} rhigh_l={rhigh_l} "
            f"cl_cmp_w={cmim_cmp_w}")


def prove(cell):
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "run_drc_lvs.py"), "--cell", cell],
        cwd=HERE)
    return r.returncode == 0


def extract_cmim_w(cell, near=None):
    """Return a cap_cmim w from extract. If near= is set, pick closest side."""
    for root, _, files in os.walk(os.path.join(OUT, f"lvs_{cell}")):
        for f in files:
            if f.endswith("_extracted.cir"):
                txt = open(os.path.join(root, f), errors="ignore").read()
                ms = [float(a) for a, _ in re.findall(
                    r"cap_cmim\s+w=([\d.]+)u\s+l=([\d.]+)u", txt)]
                if not ms:
                    continue
                if near is None:
                    return ms[0]
                return min(ms, key=lambda w: abs(w - near))
    return None


def extract_rhigh_l(cell):
    for root, _, files in os.walk(os.path.join(OUT, f"lvs_{cell}")):
        for f in files:
            if f.endswith("_extracted.cir"):
                txt = open(os.path.join(root, f), errors="ignore").read()
                ms = [float(x) for x in re.findall(
                    r"rhigh\s+w=0\.5u\s+l=([\d.]+)u", txt)]
                ms = [x for x in ms if x >= 3.0]  # ignore bogus l=1 shorts
                if ms:
                    return ms[0]
    return None


def _parse_args(argv):
    only = None
    nets = "all"
    i = 1
    while i < len(argv):
        if argv[i] == "--only" and i + 1 < len(argv):
            only = argv[i + 1]
            i += 2
        elif argv[i] == "--nets" and i + 1 < len(argv):
            nets = argv[i + 1]
            i += 2
        else:
            i += 1
    return only, nets


def _sizes_for_join():
    """Prefer prior LVS extracts; fall back to child spice / defaults [GDS]."""
    hold_w = extract_cmim_w("hold_caps")
    rhigh_l = extract_rhigh_l("cmp_se")
    if hold_w is None:
        hc = os.path.join(OUT, "hold_caps.spice")
        if os.path.exists(hc):
            ms = re.findall(r"cap_cmim\s+w=([\d.]+)u", open(hc).read())
            if ms:
                hold_w = float(ms[0])
    if rhigh_l is None:
        cs = os.path.join(OUT, "cmp_se.spice")
        if os.path.exists(cs):
            ms = re.findall(r"rhigh\s+w=0\.5u\s+l=([\d.]+)u", open(cs).read())
            if ms:
                rhigh_l = float(ms[0])
    return hold_w or CMIM_HOLD, rhigh_l or RHIGH_L


def main():
    only, nets_arg = _parse_args(sys.argv)
    if nets_arg.strip() == "all":
        routed = None
    else:
        routed = {p.strip() for p in nets_arg.split(",") if p.strip()}
        routed.add("place")

    b = B()
    results = {}
    steps = [
        ("hold_caps", b.build_hold_caps, b.write_spice_hold_caps),
        ("det_sf_pair", b.build_det_sf_pair, b.write_spice_det_sf_pair),
        ("cmp_se", b.build_cmp_se, b.write_spice_cmp_se),
        ("bias_pd", b.build_bias_pd, b.write_spice_bias_pd),
        ("ampcal_det", None, b.write_spice_ampcal_det),
    ]
    for name, builder, writer in steps:
        need_prove = (only is None) or (name == only)
        if only and name != only and only == "ampcal_det":
            cid = builder()
            if name == "hold_caps":
                # Keep drawn CMIM_HOLD; join spice uses extract size below
                writer()
            else:
                writer()
            b.write_cell(name, cid)
            results[name] = "built"
            continue
        if only and name != only:
            continue
        if name == "ampcal_det":
            hold_w, rhigh_l = _sizes_for_join()
            b.cmim_hold_w = hold_w
            b.rhigh_l = rhigh_l
            # prior join extract for cl_cmp shrink; else pcell nominal [TOOL]
            cl_w = extract_cmim_w("ampcal_det", near=CMIM_CMP) or CMIM_CMP
            b.cmim_cmp_w = cl_w
            cid = b.build_ampcal_det(routed=routed)
            writer(hold_w, rhigh_l, cl_w)
            b.write_cell(name, cid)
            b.say(
                f"ampcal_det spice hold_w={hold_w} rhigh_l={rhigh_l} "
                f"cl_cmp_w={cl_w}")
        else:
            cid = builder()
            writer()
            b.write_cell(name, cid)
        ok = prove(name) if need_prove else True
        if need_prove and name == "hold_caps":
            w = extract_cmim_w(name)
            if w:
                b.cmim_hold_w = w
                writer(w)
                b.say(f"{name}: spice w←extract {w}u; re-prove")
                ok = prove(name)
        if need_prove and name == "cmp_se":
            l = extract_rhigh_l(name)
            if l:
                b.rhigh_l = l
                writer(l)
                b.say(f"{name}: spice l←extract {l}u; re-prove")
                ok = prove(name)
        if need_prove and name == "bias_pd":
            l = extract_rhigh_l(name)
            b.say(f"{name}: extract rbias l={l} (sch target {RHIGH_BIAS_L})")
            if l is not None and abs(l - RHIGH_BIAS_L) > 0.05:
                b.say(
                    f"{name}: extract≠sch — adjust drawn length and rebuild "
                    f"(delta {l - RHIGH_BIAS_L:+.2f} µm)"
                )
        results[name] = ok
        b.say(f"prove {name}: {'PASS' if ok else 'FAIL'}")
        if need_prove and not ok and only is None:
            b.say(f"STOP at {name}")
            break

    lines = ["# P2.7.2b D22 ampcal_det build summary\n\n"]
    for k, v in results.items():
        if isinstance(v, bool):
            lines.append(f"- {k}: {'PASS' if v else 'FAIL'}\n")
        else:
            lines.append(f"- {k}: {v}\n")
    rem = POCKET_MM2 - VAR_MM2
    if b.det_top_area is not None:
        lines.append(f"\nampcal_det area={b.det_top_area:.4f} mm2 "
                     f"bbox={b.det_top_bb} [GDS]\n")
        lines.append(f"remaining pocket after vco_var="
                     f"{rem:.4f} mm2 (0.0187-0.0066) [GDS]\n")
        lines.append(f"fit remaining: "
                     f"{'YES' if b.det_top_area <= rem else 'NO'}\n")
        lines.append(f"D22 forecast≈{FORECAST_D22:.4f} mm2 [HAND]; "
                     f"vs GDS: "
                     f"{'YES' if b.det_top_area <= FORECAST_D22 else 'NO'}\n")
    open(os.path.join(OUT, "summary_build.txt"), "w").writelines(lines)
    open(os.path.join(OUT, "summary_build_log.txt"), "w").write("\n".join(b.log) + "\n")
    print("".join(lines))
    proved = [v for v in results.values() if isinstance(v, bool)]
    return 0 if proved and all(proved) else 1


if __name__ == "__main__":
    sys.exit(main())
