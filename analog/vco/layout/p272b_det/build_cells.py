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
        # sink unit 1u/1u for ~4 µA-class; 2u/1u ng=2 for 20 µA-class [HAND]
        ms = self.pcell("nmos", {
            "w": "1.0u", "l": "1.0u", "ng": 1, "m": 1,
            "guardRingType": "none",
        })
        mt = self.pcell("nmos", {
            "w": "2.0u", "l": "1.0u", "ng": 2, "m": 1,
            "guardRingType": "none",
        })
        men = self.pcell("nmos", {
            "w": "2.0u", "l": "0.13u", "ng": 1, "m": 1,
            "guardRingType": "none",
        })
        # small pmos or rhigh from vdd for bias current — use rhigh ~50k
        rb = self.pcell("rhigh", {
            "w": "0.5u", "l": "19.23u", "b": 0,  # ~50 kΩ
            "Calculate": "l", "guardRingType": "none",
        })
        sloc = self.ly.cell(ms).bbox().to_dtype(self.ly.dbu)
        tloc = self.ly.cell(mt).bbox().to_dtype(self.ly.dbu)
        eloc = self.ly.cell(men).bbox().to_dtype(self.ly.dbu)
        rloc = self.ly.cell(rb).bbox().to_dtype(self.ly.dbu)

        gap = 3.0
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

        y_drain = max(bb.top for _, _, bb, _ in devices) + 2.5
        y_mid = min(bb.bottom for _, _, bb, _ in devices) - 2.0
        y_gnd = min(bb.bottom for _, _, bb, _ in ens) - 2.5
        y_nbias = y_drain + 3.0
        y_en_gate = max(bb.top for _, _, bb, _ in ens) + 2.0
        y_vdd = max(bb_rb.top, y_nbias) + 3.0

        # Wire each sink: drain→named pin, source→en drain, en source→gnd
        pin_map = {
            "diode": "nbias", "id_h": "hold", "id_r": "rep",
            "id_tt": "ttail", "id_ss": "ss2",
        }
        for (name, cid, bb, t), (ename, ecid, ebb, et) in zip(devices, ens):
            dr, sr = sd_of(cid, t)
            edr, esr = sd_of(ecid, et)
            # drain up to bus / pin
            for col in dr:
                self.box_m1(c, col.left, col.top - 0.05, col.right, y_drain)
            self.box_m1(c, dr[0].left, y_drain, dr[-1].right, y_drain + 0.40)
            if name == "diode":
                # diode: gate shorted to drain (=nbias)
                gates = self.poly_gates(cid, t)
                at = self.activ_top(cid, t)
                self._gate_bus(c, gates, at, bb.left - 2.0, y_nbias, "nbias")
                self.box_m1(c, bb.left - 2.3, y_drain,
                            bb.left - 1.7, y_nbias)
                self.box_m1(c, dr[0].left, y_drain, bb.left - 1.7, y_drain + 0.40)
            else:
                px = 0.5 * (dr[0].left + dr[-1].right)
                self.pin_m1(c, px, y_drain + 0.60, pin_map[name])
                self.box_m1(c, px - 0.25, y_drain, px + 0.25, y_drain + 0.80)
            # source down to mid, then to en drain
            for col in sr:
                self.box_m1(c, col.left, y_mid, col.right, col.bottom)
            self.box_m1(c, sr[0].left, y_mid, sr[-1].right, y_mid + 0.40)
            # en drain up to mid
            for col in edr:
                self.box_m1(c, col.left, col.top - 0.05, col.right, y_mid + 0.40)
            self.box_m1(c, edr[0].left, y_mid, edr[-1].right, y_mid + 0.40)
            # join source bus to en drain
            self.box_m1(c, min(sr[0].left, edr[0].left), y_mid,
                        max(sr[-1].right, edr[-1].right), y_mid + 0.40)
            # en source → gnd
            for col in esr:
                self.box_m1(c, col.left, y_gnd, col.right, col.bottom)
            self.box_m1(c, esr[0].left, y_gnd, esr[-1].right, y_gnd + 0.40)
            # en gate → shared en bus
            gates = self.poly_gates(ecid, et)
            at = self.activ_top(ecid, et)
            g0, g1 = gates[0], gates[-1]
            y0, y1 = at + 0.08, at + 0.55
            c.shapes(self.poly).insert(pya.DBox(g0.left, y0, g1.right, y1))
            for g in gates:
                gx = 0.5 * (g.left + g.right)
                half = 0.5 * (g.right - g.left)
                c.shapes(self.poly).insert(
                    pya.DBox(gx - half, g.top - 0.05, gx + half, y1))
            # contact above
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
            self.box_m1(c, g0.left - 0.08, y_pad1, g1.right + 0.08, y_en_gate + 0.40)

        self.box_m1(c, ens[0][2].left, y_en_gate,
                    ens[-1][2].right, y_en_gate + 0.40)
        ex = ens[-1][2].right + 2.5
        self.box_m1(c, ens[-1][2].right, y_en_gate, ex + 0.30, y_en_gate + 0.40)
        self.pin_m1(c, ex, y_en_gate + 0.20, "en")

        # rhigh: bot→nbias, top→vdd
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

        # gnd bus
        self.box_m1(c, ens[0][2].left, y_gnd, ens[-1][2].right, y_gnd + 0.40)
        self.pin_m1(c, ens[0][2].left - 2.0, y_gnd - 0.2, "gnd")
        self.box_m1(c, ens[0][2].left - 2.3, y_gnd, ens[0][2].left, y_gnd + 0.40)

        # non-diode sink gates → nbias (mirror)
        for name, cid, bb, t in devices:
            if name == "diode":
                continue
            gates = self.poly_gates(cid, t)
            at = self.activ_top(cid, t)
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
            self.box_m1(c, g0.left - 0.08, y_pad1, g1.right + 0.08, y_nbias + 0.40)
        self.box_m1(c, devices[0][2].left - 2.5, y_nbias,
                    devices[-1][2].right, y_nbias + 0.40)

        abb = c.bbox().to_dtype(self.ly.dbu)
        ox0, oy0, ox1, oy1 = self._outer_ptap_gr(
            c, abb.left, abb.bottom, abb.right, abb.top, ring=1.0, gap=1.5)
        self.box_m1(c, ox0, y_gnd, ens[0][2].left, y_gnd + 0.40)

        bb = c.bbox().to_dtype(self.ly.dbu)
        self.bias_area = bb.width() * bb.height() * 1e-6
        self.say(f"bias_pd bbox {bb} area={self.bias_area:.4f} mm2")
        return c.cell_index()

    def write_spice_bias_pd(self):
        open(os.path.join(OUT, "bias_pd.spice"), "w").write(
            """* P2.7.2b bias_pd: MOS sinks + en PD [SCH idet/irep/itt/iss2]
.subckt bias_pd hold rep ttail ss2 en vdd gnd nbias
* diode ref + ~50k from vdd
Rrbias vdd nbias gnd rhigh w=0.5u l=19.23u ps=0.18u b=0 m=1
Mdiode nbias nbias pd_d gnd sg13_lv_nmos w=1.0u l=1.0u ng=1
Men_d pd_d en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_h hold nbias pd_h gnd sg13_lv_nmos w=1.0u l=1.0u ng=1
Men_h pd_h en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_r rep nbias pd_r gnd sg13_lv_nmos w=1.0u l=1.0u ng=1
Men_r pd_r en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_tt ttail nbias pd_tt gnd sg13_lv_nmos w=2.0u l=1.0u ng=2
Men_tt pd_tt en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_ss ss2 nbias pd_ss gnd sg13_lv_nmos w=2.0u l=1.0u ng=2
Men_ss pd_ss en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
.ends
""")
        self.say("wrote bias_pd.spice")

    # ------------------------------------------------------------------
    def build_ampcal_det(self):
        """Join: det_sf_pair + hold_caps + cmp_se + bias_pd + cl_cmp.

        Ports match island + sch: tp tn ct vdd gnd cmp hold rep en vthn
        Digital (cmp, en) on east, away from tank/V_tune [SCH].
        """
        c = self.ly.create_cell("ampcal_det")
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        # cl_cmp 50 fF
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

        # Place: SF west (tank taps), caps south of SF, cmp east, bias south-east
        sf_bb, sf_t = self.place(c, sf_cid, 0.0, 20.0)
        hc_bb, hc_t = self.place(c, hc_cid, 0.0, -5.0)
        cm_bb, cm_t = self.place(
            c, cm_cid, sf_bb.right + 8.0, 10.0)
        bp_bb, bp_t = self.place(
            c, bp_cid, cm_bb.left, -5.0)
        cl_bb, cl_t = self.place(
            c, mim, cm_bb.right + 2.0, cm_bb.top - 10.0)

        sf_p = self._pins_abs(sf_pins, sf_t)
        hc_p = self._pins_abs(hc_pins, hc_t)
        cm_p = self._pins_abs(cm_pins, cm_t)
        bp_p = self._pins_abs(bp_pins, bp_t)

        def strap(a, b, w=0.40):
            """M1 Manhattan a→b."""
            ax, ay = a
            bx, by = b
            h = 0.5 * w
            self.box_m1(c, ax - h, ay - h, ax + h, by + h)
            self.box_m1(c, min(ax, bx) - h, by - h, max(ax, bx) + h, by + h)

        def strap_m2(a, b, w=0.40):
            ax, ay = a
            bx, by = b
            h = 0.5 * w
            self._via12(c, vs12, ax, ay)
            self._via12(c, vs12, bx, by)
            self.box_m2(c, ax - h, ay - h, ax + h, by + h)
            self.box_m2(c, min(ax, bx) - h, by - h, max(ax, bx) + h, by + h)

        # hold: SF ↔ caps ↔ bias ↔ cmp
        strap(sf_p["hold"], hc_p["hold"])
        strap_m2(hc_p["hold"], bp_p["hold"])
        strap_m2(bp_p["hold"], cm_p["hold"])
        # rep
        strap(sf_p["rep"], hc_p["rep"])
        strap_m2(hc_p["rep"], bp_p["rep"])
        # ttail / ss2: cmp ↔ bias
        strap(cm_p["ttail"], bp_p["ttail"])
        strap(cm_p["ss2"], bp_p["ss2"])
        # vdd / gnd
        strap_m2(sf_p["vdd"], cm_p["vdd"])
        strap_m2(cm_p["vdd"], bp_p["vdd"])
        strap_m2(sf_p["gnd"], hc_p["gnd"])
        strap_m2(hc_p["gnd"], cm_p["gnd"])
        strap_m2(cm_p["gnd"], bp_p["gnd"])

        # cl_cmp: PLUS→cmp, MINUS→gnd
        def lyr_boxes(cid, trans, layer):
            out = []
            for s in self.ly.cell(cid).shapes(layer).each():
                if s.is_box():
                    out.append(s.bbox().transformed(trans).to_dtype(self.ly.dbu))
            return out

        def biggest(boxes):
            return max(boxes, key=lambda b: (b.right - b.left) * (b.top - b.bottom))

        m5 = biggest(lyr_boxes(mim, cl_t, self.m5))
        tm = biggest(lyr_boxes(mim, cl_t, self.tm1))
        mx = 0.5 * (m5.left + m5.right)
        y_vs = m5.bottom - 0.2
        bb_vs, _ = self.place(c, vs5, mx - 0.35, y_vs - 0.5)
        self.box_m5(c, bb_vs.left, bb_vs.top - 0.1, bb_vs.right, m5.bottom + 0.3)
        self.box_m1(c, bb_vs.left - 0.1, bb_vs.bottom - 0.5,
                    bb_vs.right + 0.1, bb_vs.bottom + 0.2)
        # gnd strap
        strap((mx, bb_vs.bottom - 0.3), cm_p["gnd"])
        # cmp on TM1
        tcx = 0.5 * (tm.left + tm.right)
        y_cmp_cap = tm.bottom - 3.0
        c.shapes(self.tm1).insert(pya.DBox(
            tcx - 1.0, y_cmp_cap - 0.5, tcx + 1.0, tm.bottom + 1.0))
        # drop to M1 via... TM1 pin only; strap cmp M1 from cm_p
        # Use M1 pin at cmp and note TM1 is same net via extraction of cmim PLUS
        # Connect: place M1 near cmp pin and rely on... actually need TopVia.
        # Simpler: label TM1 as cmp and also M1 cmp pin from comparator.
        self.pin_tm1(c, tcx, y_cmp_cap, "cmp")
        # Also expose M1 cmp from comparator (same net name → LVS merge by label)
        self.pin_m1(c, cm_p["cmp"][0], cm_p["cmp"][1], "cmp")

        # Top ports — tank west, digital east
        for name in ("tp", "tn", "ct"):
            self.pin_m1(c, sf_p[name][0], sf_p[name][1], name)
        self.pin_m1(c, sf_p["hold"][0], sf_p["hold"][1] - 2.0, "hold")
        self.box_m1(c, sf_p["hold"][0] - 0.25, sf_p["hold"][1] - 2.2,
                    sf_p["hold"][0] + 0.25, sf_p["hold"][1])
        self.pin_m1(c, sf_p["rep"][0], sf_p["rep"][1] - 2.0, "rep")
        self.box_m1(c, sf_p["rep"][0] - 0.25, sf_p["rep"][1] - 2.2,
                    sf_p["rep"][0] + 0.25, sf_p["rep"][1])
        self.pin_m1(c, cm_p["vthn"][0], cm_p["vthn"][1], "vthn")
        self.pin_m1(c, bp_p["en"][0] + 2.0, bp_p["en"][1], "en")
        self.box_m1(c, bp_p["en"][0], bp_p["en"][1] - 0.25,
                    bp_p["en"][0] + 2.3, bp_p["en"][1] + 0.25)
        self.pin_m1(c, sf_p["vdd"][0], sf_p["vdd"][1] + 2.0, "vdd")
        self.box_m1(c, sf_p["vdd"][0] - 0.25, sf_p["vdd"][1],
                    sf_p["vdd"][0] + 0.25, sf_p["vdd"][1] + 2.2)
        self.pin_m1(c, sf_p["gnd"][0], sf_p["gnd"][1] - 2.0, "gnd")
        self.box_m1(c, sf_p["gnd"][0] - 0.25, sf_p["gnd"][1] - 2.2,
                    sf_p["gnd"][0] + 0.25, sf_p["gnd"][1])

        abb = c.bbox().to_dtype(self.ly.dbu)
        ox0, oy0, ox1, oy1 = self._outer_ptap_gr(
            c, abb.left, abb.bottom, abb.right, abb.top, ring=1.0, gap=2.0)
        self.box_m1(c, ox0, sf_p["gnd"][1] - 0.2, sf_p["gnd"][0], sf_p["gnd"][1] + 0.2)

        bb = c.bbox().to_dtype(self.ly.dbu)
        self.det_top_area = bb.width() * bb.height() * 1e-6
        self.det_top_bb = bb
        self.say(f"ampcal_det bbox {bb} area={self.det_top_area:.4f} mm2")
        return c.cell_index()

    def write_spice_ampcal_det(self, hold_w=None, rhigh_l=None):
        hold_w = hold_w or self.cmim_hold_w
        rhigh_l = rhigh_l or self.rhigh_l
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
* bias + PD
Rrbias vdd nbias gnd rhigh w=0.5u l=19.23u ps=0.18u b=0 m=1
Mdiode nbias nbias pd_d gnd sg13_lv_nmos w=1.0u l=1.0u ng=1
Men_d pd_d en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_h hold nbias pd_h gnd sg13_lv_nmos w=1.0u l=1.0u ng=1
Men_h pd_h en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_r rep nbias pd_r gnd sg13_lv_nmos w=1.0u l=1.0u ng=1
Men_r pd_r en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_tt ttail nbias pd_tt gnd sg13_lv_nmos w=2.0u l=1.0u ng=2
Men_tt pd_tt en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
Mid_ss ss2 nbias pd_ss gnd sg13_lv_nmos w=2.0u l=1.0u ng=2
Men_ss pd_ss en gnd gnd sg13_lv_nmos w=2.0u l=0.13u ng=1
* comparator
Mmc1 co hold ttail gnd sg13_lv_nmos w=4.0u l=0.5u ng=2
Mmc2 co2 vthn ttail gnd sg13_lv_nmos w=4.0u l=0.5u ng=2
Mmcs1 n1 co2 ss2 gnd sg13_lv_nmos w=4.0u l=0.5u ng=2
Mmcs2 cmp co ss2 gnd sg13_lv_nmos w=4.0u l=0.5u ng=2
Mmpl1 n1 n1 vdd vdd sg13_lv_pmos w=4.0u l=0.5u ng=2
Mmpl2 cmp n1 vdd vdd sg13_lv_pmos w=4.0u l=0.5u ng=2
Rrc1 vdd co gnd rhigh w=0.5u l={rhigh_l:.3f}u ps=0.18u b=0 m=1
Rrc2 vdd co2 gnd rhigh w=0.5u l={rhigh_l:.3f}u ps=0.18u b=0 m=1
MdLc gnd gnd gnd gnd sg13_lv_nmos w=2.0u l=0.5u ng=1
MdRc gnd gnd gnd gnd sg13_lv_nmos w=2.0u l=0.5u ng=1
Ccl_cmp cmp gnd cap_cmim w={CMIM_CMP:.3f}u l={CMIM_CMP:.3f}u m=1
.ends
""")
        self.say("wrote ampcal_det.spice")


def prove(cell):
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "run_drc_lvs.py"), "--cell", cell],
        cwd=HERE)
    return r.returncode == 0


def extract_cmim_w(cell):
    for root, _, files in os.walk(os.path.join(OUT, f"lvs_{cell}")):
        for f in files:
            if f.endswith("_extracted.cir"):
                txt = open(os.path.join(root, f), errors="ignore").read()
                ms = re.findall(r"cap_cmim\s+w=([\d.]+)u\s+l=([\d.]+)u", txt)
                if ms:
                    return float(ms[0][0])
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


def main():
    only = None
    if len(sys.argv) > 1 and sys.argv[1] == "--only":
        only = sys.argv[2] if len(sys.argv) > 2 else None

    b = B()
    results = {}
    steps = [
        ("hold_caps", b.build_hold_caps, b.write_spice_hold_caps),
        ("det_sf_pair", b.build_det_sf_pair, b.write_spice_det_sf_pair),
        ("cmp_se", b.build_cmp_se, b.write_spice_cmp_se),
        ("bias_pd", b.build_bias_pd, b.write_spice_bias_pd),
        ("ampcal_det", b.build_ampcal_det, b.write_spice_ampcal_det),
    ]
    for name, builder, writer in steps:
        need_prove = (only is None) or (name == only)
        if only and name != only and only == "ampcal_det":
            cid = builder()
            writer()
            b.write_cell(name, cid)
            results[name] = "built"
            continue
        if only and name != only:
            continue
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
