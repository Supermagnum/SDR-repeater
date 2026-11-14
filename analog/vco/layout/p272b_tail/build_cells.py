#!/usr/bin/env python3
"""P2.7.2b tail — compact DAC re-spin then OTA/tail/RC.

Stages (--stage):
  a) dac_unit   — abutted mdb+msw, no per-cell GR, pins inside bbox
  b) dac_array  — abutted cells, shared rails, one outer GR; ≤0.015 mm²
  c..e) later

Compact rules [decisions 2026-11-13]:
  - cells abutted, shared source/supply rails
  - one guard ring around the whole array (no per-cell rings)
  - centroid order kept (CENTROID_31), dummies at edges
  - code buses on a fixed routing track per bit; vdd one continuous rail
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
UNIT_W = "2.0u"
UNIT_L = "2.0u"
SW_L = "0.13u"
# Common-centroid order for 31 units + 1 dummy in 4×8 = 32 slots [kept].
CENTROID_31 = [
    "b4", "b3", "b2", "b4", "b3", "b4", "b1", "b4",
    "b4", "b3", "b2", "b4", "b3", "b4", "b0", "b4",
    "b4", "b3", "b2", "b4", "b3", "b4", "b1", "b4",
    "b4", "b3", "b2", "b4", "b4", "b3", "D", "b4",
]
AREA_TARGET_MM2 = 0.015


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
        self.m4 = self.ly.layer(50, 0)
        self.m5 = self.ly.layer(67, 0)
        self.tm1 = self.ly.layer(126, 0)
        self.cont = self.ly.layer(6, 0)
        self.poly = self.ly.layer(5, 0)
        self.activ = self.ly.layer(1, 0)
        self.nsd = self.ly.layer(7, 0)
        self.psd = self.ly.layer(14, 0)
        self.nw = self.ly.layer(31, 0)
        self.nbulay = self.ly.layer(32, 0)
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

    def pin_m1(self, cell, x, y, name, label=True):
        cell.shapes(self.m1).insert(pya.DBox(x - 0.25, y - 0.25, x + 0.25, y + 0.25))
        if label:
            cell.shapes(self.m1pin).insert(pya.DBox(x - 0.2, y - 0.2, x + 0.2, y + 0.2))
            cell.shapes(self.m1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def box_m1(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m1).insert(pya.DBox(min(x0, x1), min(y0, y1),
                                             max(x0, x1), max(y0, y1)))

    def box_m2(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m2).insert(pya.DBox(min(x0, x1), min(y0, y1),
                                             max(x0, x1), max(y0, y1)))

    def box_m3(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m3).insert(pya.DBox(min(x0, x1), min(y0, y1),
                                             max(x0, x1), max(y0, y1)))

    def box_m4(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m4).insert(pya.DBox(min(x0, x1), min(y0, y1),
                                             max(x0, x1), max(y0, y1)))

    def box_m5(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m5).insert(pya.DBox(min(x0, x1), min(y0, y1),
                                             max(x0, x1), max(y0, y1)))

    def nw_tap_to_m1(self, cell, x0, y0, x1, y1):
        cell.shapes(self.activ).insert(pya.DBox(x0, y0, x1, y1))
        cell.shapes(self.nsd).insert(pya.DBox(x0 - 0.05, y0 - 0.05, x1 + 0.05, y1 + 0.05))
        cell.shapes(self.nbulay).insert(pya.DBox(x0 - 0.1, y0 - 0.1, x1 + 0.1, y1 + 0.1))
        cell.shapes(self.nw).insert(pya.DBox(x0 - 0.3, y0 - 0.3, x1 + 0.3, y1 + 0.3))
        # Single Cont (Cnt.b ≥0.18 µm) centred in tap
        cx = 0.5 * (x0 + x1) - 0.08
        cy = 0.5 * (y0 + y1) - 0.08
        cell.shapes(self.cont).insert(pya.DBox(cx, cy, cx + 0.16, cy + 0.16))
        self.box_m1(cell, x0, y0, x1, y1)

    def gate_up(self, cell, gate_bb, activ_top, pin_name, label=True):
        """Poly pad + Cont + M1 pin directly above gate (no lateral stub)."""
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
        self.box_m1(cell, gx - 0.16, cy0, gx + 0.16, pad_top + 0.35)
        self.pin_m1(cell, gx, pad_top + 0.20, pin_name, label=label)
        return gx, pad_top + 0.20

    def build_dac_unit(self, with_tap=True, cell_name="dac_unit", pin_labels=True):
        """Compact 80 µA unit: mdb 2/2 + msw 2/0.13, abutted, no cell GR [SCH].

        with_tap: NW n+ to vdd for standalone LVS. Array uses with_tap=False and
        one outer GR (taps would short xraw of the left neighbour when abutted).
        pin_labels: False for array instances so unit texts do not become top pins.
        """
        c = self.ly.create_cell(cell_name)
        mdb = self.pcell("pmos", {"w": UNIT_W, "l": UNIT_L, "ng": 1, "m": 1,
                                 "guardRingType": "none"})
        msw = self.pcell("pmos", {"w": UNIT_W, "l": SW_L, "ng": 1, "m": 1,
                                 "guardRingType": "none"})
        bb0, t0 = self.place(c, mdb, 0, 0)
        # Activ gap ≥0.42 µm; xraw exits on M2 past msw (not through street)
        x_msw = 2.68 + 0.42  # mdb activ right ≈2.68 [PDK pcell]
        bb1, t1 = self.place(c, msw, x_msw, 0)
        cols0 = self.m1_cols(mdb, t0)
        cols1 = self.m1_cols(msw, t1)
        g0 = self.poly_gates(mdb, t0)[0]
        g1 = self.poly_gates(msw, t1)[0]
        at0 = self.activ_top(mdb, t0)
        at1 = self.activ_top(msw, t1)
        d_mdb, s_mdb = cols0[0], cols0[1]
        d_msw, s_msw = cols1[0], cols1[1]

        # vdd: mdb SOURCE only (msw source is xd) [SCH]
        y_vdd = max(at0, at1) + 0.45
        self.box_m1(c, s_mdb.left, s_mdb.top - 0.05, s_mdb.right, y_vdd + 0.28)
        self.box_m1(c, s_mdb.left - 0.05, y_vdd, s_mdb.right + 0.05, y_vdd + 0.28)
        self.pin_m1(c, 0.5 * (s_mdb.left + s_mdb.right), y_vdd + 0.14, "vdd",
                    label=pin_labels)
        if with_tap:
            # Compact NW n+ tap LEFT of mdb → vdd (standalone unit LVS) [LVS]
            tx1 = d_mdb.left - 0.35
            tx0 = tx1 - 0.70
            ty0 = y_vdd - 0.05
            self.nw_tap_to_m1(c, tx0, ty0, tx1, ty0 + 0.70)
            self.box_m1(c, tx1, y_vdd, s_mdb.left, y_vdd + 0.28)

        # xd: mdb.D + msw.S (series node) — U-strap under
        y_xd = min(bb0.bottom, bb1.bottom) - 0.55
        self.box_m1(c, d_mdb.left, y_xd, s_msw.right, y_xd + 0.28)
        self.box_m1(c, d_mdb.left, y_xd, d_mdb.right, d_mdb.bottom)
        self.box_m1(c, s_msw.left, y_xd, s_msw.right, s_msw.bottom)
        xd_xy = (0.5 * (d_mdb.left + d_mdb.right), y_xd + 0.14)
        self.pin_m1(c, xd_xy[0], xd_xy[1], "xd", label=pin_labels)

        # xraw: msw.D → M2 jog RIGHT past msw.S → UP (clear of xd/vdd M1)
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        y_exit = min(d_msw.top - 0.05, at1 - 0.15)
        x_via = 0.5 * (d_msw.left + d_msw.right)
        x_edge = s_msw.right + 0.70
        y_xr = max(y_vdd + 1.1, at1 + 1.5)
        self.box_m1(c, d_msw.left, y_exit - 0.16, d_msw.right, y_exit)
        # via_stack M2 is 0.29×0.20 — fully cover so merged width ≫ M2.a 0.20
        self.place(c, vs12, x_via - 0.2, y_exit - 0.10)
        self.box_m2(c, x_via - 0.35, y_exit - 0.25, x_edge + 0.35, y_exit + 0.40)
        self.box_m2(c, x_edge - 0.35, y_exit - 0.25, x_edge + 0.35, y_xr + 0.35)
        self.place(c, vs12, x_edge - 0.2, y_xr)
        xraw_xy = (x_edge, y_xr + 0.15)
        self.pin_m1(c, xraw_xy[0], xraw_xy[1], "xraw", label=pin_labels)

        # Gates: pbias lower, code higher so array M2 jogs at code Y miss pbias
        pbias_xy = self.gate_up(c, g0, max(at0, y_vdd + 0.20), "pbias",
                                label=pin_labels)
        code_xy = self.gate_up(c, g1, max(at1, y_vdd + 1.40), "code",
                               label=pin_labels)
        vdd_xy = (0.5 * (s_mdb.left + s_mdb.right), y_vdd + 0.14)

        self.unit_pins = {
            "vdd": vdd_xy, "xraw": xraw_xy, "pbias": pbias_xy,
            "code": code_xy, "xd": xd_xy,
        }
        bb = c.bbox().to_dtype(self.ly.dbu)
        self.unit_bb = bb
        self.say(f"dac_unit bbox {bb}  area={bb.width()*bb.height()*1e-6:.6f} mm2")
        self.say(f"  pins {self.unit_pins}")
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
        self.say(f"wrote {gds} (+.gz)")
        return gds

    def write_spice_dac_unit(self):
        open(os.path.join(OUT, "dac_unit.spice"), "w").write(
            """* P2.7.2b dac_unit W=2u L=2u [SCH] Pelgrom KEEP
.subckt dac_unit vdd pbias xd code xraw
Mmdb xd pbias vdd vdd sg13_lv_pmos w=2.0u l=2.0u
Mmsw xraw code xd vdd sg13_lv_pmos w=2.0u l=0.13u
.ends
""")
        self.say("wrote dac_unit.spice")

    def box_nw_fill(self, cell, x0, y0, x1, y1):
        """Solid NW + NBuLay under PMOS array so bulks merge to GR/vdd [LVS]."""
        cell.shapes(self.nw).insert(pya.DBox(x0, y0, x1, y1))
        cell.shapes(self.nbulay).insert(pya.DBox(x0 + 0.2, y0 + 0.2, x1 - 0.2, y1 - 0.2))

    def _outer_gr(self, cell, x0, y0, x1, y1, ring=1.2, gap=0.6):
        """One NW n+ guard ring around array, strapped to vdd on M1."""
        # Outer activ ring
        ox0, oy0 = x0 - gap - ring, y0 - gap - ring
        ox1, oy1 = x1 + gap + ring, y1 + gap + ring
        ix0, iy0 = x0 - gap, y0 - gap
        ix1, iy1 = x1 + gap, y1 + gap
        # Four sides of activ / nsd / nw / nbulay / m1
        parts = [
            (ox0, oy0, ox1, iy0),  # bottom
            (ox0, iy1, ox1, oy1),  # top
            (ox0, iy0, ix0, iy1),  # left
            (ix1, iy0, ox1, iy1),  # right
        ]
        for a, b, c_, d in parts:
            cell.shapes(self.activ).insert(pya.DBox(a, b, c_, d))
            cell.shapes(self.nsd).insert(pya.DBox(a - 0.05, b - 0.05, c_ + 0.05, d + 0.05))
            cell.shapes(self.nbulay).insert(pya.DBox(a - 0.1, b - 0.1, c_ + 0.1, d + 0.1))
            cell.shapes(self.nw).insert(pya.DBox(a - 0.3, b - 0.3, c_ + 0.3, d + 0.3))
            self.box_m1(cell, a, b, c_, d)
        # Contacts along top edge into vdd
        x = ox0 + 0.2
        while x < ox1 - 0.3:
            cell.shapes(self.cont).insert(pya.DBox(x, iy1 + 0.2, x + 0.16, iy1 + 0.36))
            x += 1.0
        return ox0, oy0, ox1, oy1

    def build_dac_array(self, routed_codes=None):
        """DAC array with planned M2-H / M3-V routing (p27-layout-notes).

        routed_codes: set of tags among {base,b0..b4,D} with own M2 track.
        Tags not in the set tie to code_gnd. None → all bits routed.
        """
        track_order = ["base", "b0", "b1", "b2", "b3", "b4", "D"]
        if routed_codes is None:
            routed_codes = set(track_order)
        else:
            routed_codes = set(routed_codes)
        self.say(f"routed_codes={sorted(routed_codes)}")

        unit_cid = self.build_dac_unit(with_tap=False, cell_name="dac_unit_arr",
                                       pin_labels=False)
        pins = self.unit_pins
        ubb = self.unit_bb
        lane_pitch = 0.90
        n_lane = 7
        chan = n_lane * lane_pitch
        pitch_x = ubb.width() + chan + 1.0
        pitch_y = ubb.height() + 2.0
        self.say(f"pitch {pitch_x:.3f} x {pitch_y:.3f} µm  "
                 f"(unit {ubb.width():.2f}x{ubb.height():.2f}, chan={chan:.2f})")

        c = self.ly.create_cell("dac_array")
        placements = []
        y = 0.0
        n = 0
        for nc in (7, 7, 5):
            for col in range(nc):
                x0 = col * pitch_x
                self.place(c, unit_cid, x0, y)
                placements.append((x0, y, "base"))
                n += 1
            y += pitch_y
        assert n == 19
        cc_y0 = y + 0.5
        for r in range(4):
            row = CENTROID_31[r * 8:(r + 1) * 8]
            order = list(reversed(row)) if (r % 2) else list(row)
            for col, tag in enumerate(order):
                x0 = col * pitch_x
                y0 = cc_y0 + r * pitch_y
                self.place(c, unit_cid, x0, y0)
                placements.append((x0, y0, tag))

        abb = c.bbox().to_dtype(self.ly.dbu)
        tw, tp = 0.40, 0.90
        # Bus X span covers edge pins (right + chan + 3) [HAND]
        bus_x0 = abb.left - 2.0
        bus_x1 = abb.right + chan + 3.0

        y_bus0 = abb.top + 2.0
        y_vdd = y_bus0
        y_pbias = y_bus0 + tp
        # xraw spine MUST sit below the outer GR (GR bottom = abb.bottom - gap - ring
        # = abb.bottom - 2). A pin/via on the GR M1 shorts xraw to vdd [LVS].
        y_xraw = abb.bottom - 2.0 - 2.0  # = abb.bottom - 4
        code_y = {}
        y_t = y_pbias + tp
        for tag in track_order:
            code_y[tag] = y_t
            y_t += tp

        def track_m2(y0):
            self.box_m2(c, bus_x0, y0, bus_x1, y0 + tw)

        track_m2(y_vdd)
        track_m2(y_pbias)
        self.box_m2(c, bus_x0, y_xraw - tw, bus_x1, y_xraw)
        for tag in track_order:
            if tag == "base" or tag in routed_codes:
                track_m2(code_y[tag])

        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs23 = self.pcell("via_stack", {
            "b_layer": "Metal2", "t_layer": "Metal3",
            "vn_columns": 1, "vn_rows": 1,
        })

        # via_stack origin is the via centre — place at (ax, ay) [PDK]
        def via12(ax, ay):
            self.box_m1(c, ax - 0.20, ay - 0.20, ax + 0.20, ay + 0.20)
            self.place(c, vs12, ax, ay)

        def via23(ax, ay):
            # Cover via M2/M3 (0.29) without fat pads that close M2.b to xraw
            self.box_m2(c, ax - 0.20, ay - 0.20, ax + 0.20, ay + 0.20)
            self.box_m3(c, ax - 0.20, ay - 0.20, ax + 0.20, ay + 0.20)
            self.place(c, vs23, ax, ay)

        def m3_drop(ax, y_a, y_b):
            lo, hi = min(y_a, y_b), max(y_a, y_b)
            self.box_m3(c, ax - 0.20, lo - 0.20, ax + 0.20, hi + 0.20)

        def bus_via_top(ax, y_track):
            via23(ax, y_track + 0.5 * tw)

        def bus_via_bot(ax, y_top_of_track):
            # xraw track occupies [y_top_of_track - tw, y_top_of_track]
            via23(ax, y_top_of_track - 0.5 * tw)

        for x0, y0, tag in placements:
            px, py = pins["vdd"]
            ax, ay = x0 + px, y0 + py
            via12(ax, ay)
            via23(ax, ay)
            m3_drop(ax, ay, y_vdd + 0.5 * tw)
            bus_via_top(ax, y_vdd)

            px, py = pins["xraw"]
            ax, ay = x0 + px, y0 + py
            # unit already has Via1 at the xraw pin — a second via trips V1.b [DRC]
            via23(ax, ay)
            m3_drop(ax, ay, y_xraw - 0.5 * tw)
            bus_via_bot(ax, y_xraw)

            px, py = pins["pbias"]
            ax, ay = x0 + px, y0 + py
            via12(ax, ay)
            via23(ax, ay)
            m3_drop(ax, ay, y_pbias + 0.5 * tw)
            bus_via_top(ax, y_pbias)

            px, py = pins["code"]
            ax, ay = x0 + px, y0 + py
            tag_i = track_order.index(tag)
            x_lane = x0 + ubb.right + 0.45 + tag_i * lane_pitch
            bus_tag = tag if tag in routed_codes else "base"
            y_bus = code_y[bus_tag]
            via12(ax, ay)
            # M2 jog: full track width, pin → lane [PDK Mn_a 0.20]
            self.box_m2(c, min(ax, x_lane) - 0.20, ay - 0.20,
                        max(ax, x_lane) + 0.20, ay + 0.20)
            via23(x_lane, ay)
            m3_drop(x_lane, ay, y_bus + 0.5 * tw)
            bus_via_top(x_lane, y_bus)

        self._outer_gr(c, abb.left, abb.bottom, abb.right, abb.top,
                       ring=1.0, gap=1.0)
        # NW fill under the array so every PMOS bulk merges with the GR → vdd.
        # Without this, LVS reports one floating bulk net per unit (51 extras) [LVS].
        gap = 1.0
        self.box_nw_fill(c, abb.left - gap - 0.2, abb.bottom - gap - 0.2,
                         abb.right + gap + 0.2, abb.top + gap + 0.2)
        # GR → vdd track on M1/M2
        gy = y_vdd + 0.5 * tw
        via12(abb.left + 1.0, gy)
        self.box_m1(c, abb.left - 0.5, y_vdd, abb.left + 1.5, y_vdd + tw)
        self.box_m2(c, abb.left - 0.5, y_vdd, abb.left + 1.5, y_vdd + tw)

        self.pin_m1(c, abb.left + 2.0, gy, "vdd")
        via12(abb.left + 2.0, gy)
        self.pin_m1(c, abb.left + 2.0, y_xraw - 0.5 * tw, "xraw")
        via12(abb.left + 2.0, y_xraw - 0.5 * tw)
        self.pin_m1(c, bus_x1 - 1.0, y_pbias + 0.5 * tw, "pbias")
        via12(bus_x1 - 1.0, y_pbias + 0.5 * tw)

        pin_map = [("code_gnd", "base"), ("code0", "b0"), ("code1", "b1"),
                   ("code2", "b2"), ("code3", "b3"), ("code4", "b4"),
                   ("code_vdd", "D")]
        for pname, tag in pin_map:
            if tag != "base" and tag not in routed_codes:
                continue
            px = bus_x1 - 1.0
            py = code_y[tag] + 0.5 * tw
            via12(px, py)
            self.pin_m1(c, px, py, pname)

        bb = c.bbox().to_dtype(self.ly.dbu)
        area = bb.width() * bb.height() * 1e-6
        self.say(f"dac_array bbox {bb}  area={area:.4f} mm2  "
                 f"target≤{AREA_TARGET_MM2}")
        self.array_area = area
        self.routed_codes = routed_codes
        rows = []
        for r in range(4):
            row = CENTROID_31[r * 8:(r + 1) * 8]
            rows.append(" ".join(reversed(row) if r % 2 else row))
        self.say("CENTROID rows (odd R->L, kept): " + " || ".join(rows))
        if area > AREA_TARGET_MM2:
            self.say(f"AREA FAIL: {area:.4f} > {AREA_TARGET_MM2}")
        else:
            self.say(f"AREA PASS: {area:.4f} ≤ {AREA_TARGET_MM2}")
        return c.cell_index()

    def write_spice_dac_array(self, routed_codes=None):
        track_order = ["base", "b0", "b1", "b2", "b3", "b4", "D"]
        if routed_codes is None:
            routed_codes = set(track_order)
        else:
            routed_codes = set(routed_codes)
        ports = ["vdd", "pbias", "xraw", "code_gnd"]
        for b in ("b0", "b1", "b2", "b3", "b4"):
            if b in routed_codes:
                ports.append("code" + b[1])
        if "D" in routed_codes:
            ports.append("code_vdd")
        lines = [
            f"* P2.7.2b dac_array incremental routed={sorted(routed_codes)}",
            ".subckt dac_unit vdd pbias xd code xraw",
            "Mmdb xd pbias vdd vdd sg13_lv_pmos w=2.0u l=2.0u",
            "Mmsw xraw code xd vdd sg13_lv_pmos w=2.0u l=0.13u",
            ".ends",
            ".subckt dac_array " + " ".join(ports),
        ]
        for i in range(19):
            lines.append(f"Xb{i} vdd pbias xd_b{i} code_gnd xraw dac_unit")
        idx = {"b0": 0, "b1": 0, "b2": 0, "b3": 0, "b4": 0}
        for r in range(4):
            row = CENTROID_31[r * 8:(r + 1) * 8]
            order = list(reversed(row)) if (r % 2) else list(row)
            for tag in order:
                if tag == "D":
                    cnet = "code_vdd" if "D" in routed_codes else "code_gnd"
                    lines.append(
                        f"Xdmy vdd pbias xd_dmy {cnet} xraw dac_unit")
                else:
                    n = idx[tag]
                    idx[tag] += 1
                    cname = ("code" + tag[1]) if tag in routed_codes else "code_gnd"
                    lines.append(
                        f"X{tag}_{n} vdd pbias xd_{tag}_{n} {cname} xraw dac_unit")
        lines.append(".ends\n")
        open(os.path.join(OUT, "dac_array.spice"), "w").write("\n".join(lines) + "\n")
        self.say(f"wrote dac_array.spice ports={ports}")

    def build_tail_mt(self):
        """Tail mt: 480u/4u ng=96 as 2×2 common-centroid of 120u/4u ng=24 [SCH].

        Same total W/L/ng; aspect reshaped for island footprint [decisions
        2026-11-14 D23 footprint finding]. Ports: tail, nbf, gnd.
        """
        c = self.ly.create_cell("tail_mt")
        # 4 × 120u ng=24 = 480u ng=96 [SCH amp_common]
        mt = self.pcell("nmos", {
            "w": "120.0u", "l": "4.0u", "ng": 24, "m": 1,
            "guardRingType": "none",
        })
        ptap = self.pcell("ptap1", {"w": "0.78u", "l": "0.78u"})
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        bloc = self.ly.cell(mt).bbox().to_dtype(self.ly.dbu)
        gap_x, gap_y = 6.0, 10.0  # alley: M2 join, no M1 through other rows [LVS]
        # Common-centroid 2×2: A B / B A [HAND]
        places = [
            (0.0, 0.0),
            (bloc.width() + gap_x, 0.0),
            (0.0, bloc.height() + gap_y),
            (bloc.width() + gap_x, bloc.height() + gap_y),
        ]
        # Per device: (bb, drains, sources, gates, at)
        devices = []
        for ox, oy in places:
            bb, t = self.place(c, mt, ox, oy)
            cols = self.m1_cols(mt, t)
            gates = self.poly_gates(mt, t)
            assert len(gates) == 24, len(gates)
            assert len(cols) == 25, len(cols)
            drains = [cols[i] for i in range(0, len(cols), 2)]
            sources = [cols[i] for i in range(1, len(cols), 2)]
            devices.append((bb, drains, sources, gates,
                            self.activ_top(mt, t)))
        self.say(f"tail_mt 2x2 W=120 ng=24; n_dev={len(devices)}")

        x0 = min(d[0].left for d in devices)
        x1 = max(d[0].right for d in devices)
        y0 = min(d[0].bottom for d in devices)
        # South corridor rails — clear of bottom-row local spurs [DRC M2.b]
        y_gnd = y0 - 4.0
        y_tail = y0 - 7.0
        x_west = x0 - 3.0
        x_east = x1 + 3.0
        y_mid = 0.5 * (min(d[0].top for d in devices[:2]) +
                       max(d[0].bottom for d in devices[2:]))  # alley mid

        # Bottom row (0,1): drop M1 straight to south rails.
        # Top row (2,3): local M2 in alley, then west/east corridor to south.
        # Never drop M1 through another row [LVS].
        for i, (bb, drains, sources, gates, at) in enumerate(devices):
            if i < 2:
                y_loc_g, y_loc_t = y_gnd, y_tail
            else:
                y_loc_g = y_mid - 0.8
                y_loc_t = y_mid + 0.8
            for col in sources:
                self.box_m1(c, col.left, y_loc_g, col.right, col.bottom)
                self.place(c, vs12, 0.5 * (col.left + col.right), y_loc_g + 0.20)
            for col in drains:
                self.box_m1(c, col.left, y_loc_t, col.right, col.bottom)
                self.place(c, vs12, 0.5 * (col.left + col.right), y_loc_t + 0.20)
            self.box_m2(c, bb.left - 0.2, y_loc_g, bb.right + 0.2, y_loc_g + 0.40)
            self.box_m2(c, bb.left - 0.2, y_loc_t, bb.right + 0.2, y_loc_t + 0.40)
            if i >= 2:
                self.box_m2(c, x_west, y_loc_g, bb.left, y_loc_g + 0.40)
                self.box_m2(c, bb.right, y_loc_t, x_east, y_loc_t + 0.40)
                self.box_m2(c, x_west, y_gnd, x_west + 0.40, y_loc_g + 0.40)
                self.box_m2(c, x_east - 0.40, y_tail, x_east, y_loc_t + 0.40)

        self.box_m2(c, x_west, y_gnd, x1 + 0.2, y_gnd + 0.40)
        self.box_m2(c, x0 - 0.2, y_tail, x_east, y_tail + 0.40)

        # Gate: M1 west to spine (x < all devices), spine north to nbf [LVS]
        # Never run vertical M1 through another device's finger array.
        x_gspine = x0 - 1.2
        y_nbf = max(d[4] for d in devices) + 4.0
        y_pads = []
        for bb, drains, sources, gates, at in devices:
            g0, g1 = gates[0], gates[-1]
            c.shapes(self.poly).insert(
                pya.DBox(g0.left, at + 0.08, g1.right, at + 0.55))
            y_pad0 = max(at + 0.50, max(g.top for g in gates) + 0.30)
            y_pad1 = y_pad0 + 0.50
            y_pads.append(y_pad0)
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
            self.box_m1(c, x_gspine - 0.20, y_pad0 + 0.16,
                        g0.left + 0.08, y_pad1 + 0.16)
        self.box_m1(c, x_gspine - 0.20, min(y_pads),
                    x_gspine + 0.20, y_nbf + 0.28)
        self.pin_m1(c, x_gspine, y_nbf + 0.14, "nbf")

        # ptap → gnd on M2 (west of gnd corridor; clear of nbf)
        px = x_west - 3.0
        py_tap = y0 + 1.0
        self.place(c, ptap, px, py_tap)
        self.box_m1(c, px, y_gnd, px + 0.78, py_tap + 0.78)
        self.place(c, vs12, px + 0.39, y_gnd + 0.20)
        self.box_m2(c, px, y_gnd, x_west + 0.40, y_gnd + 0.40)

        gx = x_west - 1.5
        self.place(c, vs12, gx, y_gnd + 0.20)
        self.box_m2(c, gx - 0.25, y_gnd, x_west + 0.40, y_gnd + 0.40)
        self.box_m1(c, gx - 0.25, y_gnd - 1.0, gx + 0.25, y_gnd + 0.40)
        self.pin_m1(c, gx, y_gnd - 0.8, "gnd")

        tx = x_east + 1.0
        self.place(c, vs12, tx, y_tail + 0.20)
        self.box_m2(c, x_east - 0.40, y_tail, tx + 0.25, y_tail + 0.40)
        self.box_m1(c, tx - 0.25, y_tail - 1.0, tx + 0.25, y_tail + 0.40)
        self.pin_m1(c, tx, y_tail - 0.8, "tail")

        abb = c.bbox().to_dtype(self.ly.dbu)
        area = abb.width() * abb.height() * 1e-6
        ar = max(abb.width(), abb.height()) / max(min(abb.width(), abb.height()), 1e-9)
        self.say(f"tail_mt bbox {abb} area={area:.4f} mm2 aspect={ar:.2f}")
        self.tail_area = area
        return c.cell_index()

    def write_spice_tail_mt(self):
        # LVS: four parallel 120u/4u ng=24 ≡ one 480u/4u ng=96 [SCH]
        open(os.path.join(OUT, "tail_mt.spice"), "w").write(
            """* P2.7.2b tail_mt W=480u L=4u ng=96 as 4× (120u/4u ng=24) [SCH amp_common]
.subckt tail_mt tail nbf gnd
Mmt0 tail nbf gnd gnd sg13_lv_nmos w=120.0u l=4.0u ng=24
Mmt1 tail nbf gnd gnd sg13_lv_nmos w=120.0u l=4.0u ng=24
Mmt2 tail nbf gnd gnd sg13_lv_nmos w=120.0u l=4.0u ng=24
Mmt3 tail nbf gnd gnd sg13_lv_nmos w=120.0u l=4.0u ng=24
.ends
""")
        self.say("wrote tail_mt.spice")

    def _route_mos_sd(self, c, cols, even_is_drain=True):
        """Split M1 SD columns into drain/source lists [pair lesson]."""
        drains, sources = [], []
        for i, col in enumerate(cols):
            if (i % 2 == 0) == even_is_drain:
                drains.append(col)
            else:
                sources.append(col)
        return drains, sources

    def _via12(self, c, vs12, x, y):
        """Place M1–M2 via with explicit M1/M2 landing (avoids V1.b / M1.b)."""
        self.box_m1(c, x - 0.30, y - 0.30, x + 0.30, y + 0.30)
        self.box_m2(c, x - 0.30, y - 0.30, x + 0.30, y + 0.30)
        self.place(c, vs12, x, y)

    def _gate_bus(self, c, gates, at, x_pin, y_pin, name, label=True):
        """Poly strap + Cont + M1 exit to pin (outboard, no bar over SD)."""
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
        # Horizontal only at pad Y, then vertical at x_pin (outboard)
        self.box_m1(c, min(x_pin, g0.left) - 0.14, y_pad0 + 0.16,
                    max(x_pin, g1.right) + 0.14, y_pad1 + 0.16)
        self.box_m1(c, x_pin - 0.14, min(y_pad1, y_pin),
                    x_pin + 0.14, max(y_pad1 + 0.28, y_pin + 0.28))
        self.pin_m1(c, x_pin, y_pin, name, label=label)
        return y_pad1

    def _outer_ptap_gr(self, cell, x0, y0, x1, y1, ring=1.0, gap=1.2):
        """P+ substrate guard ring to gnd (for NMOS / mixed cells) [PDK]."""
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

    def build_ota_vds(self):
        """V_DS-matched OTA: mo1/mo2 centroid pair + mp1/mp2 loads [SCH].

        Ports: xref, tail_f, out (d2), vdd, gnd, ss. Ideal iss is off-cell.
        Routing: local M1 at devices only; d1/d2/ss/gnd join on M2 so PMOS
        drain straps never cross the NMOS SD columns [LVS pair lesson].
        """
        c = self.ly.create_cell("ota_vds")
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        # Input pair 8u/2u ng=2; dummy fingers 4u/2u ng=1
        mo = self.pcell("nmos", {
            "w": "8.0u", "l": "2.0u", "ng": 2, "m": 1,
            "guardRingType": "none",
        })
        dum = self.pcell("nmos", {
            "w": "4.0u", "l": "2.0u", "ng": 1, "m": 1,
            "guardRingType": "none",
        })
        mp = self.pcell("pmos", {
            "w": "4.0u", "l": "2.0u", "ng": 2, "m": 1,
            "guardRingType": "none",
        })
        mloc = self.ly.cell(mo).bbox().to_dtype(self.ly.dbu)
        dloc = self.ly.cell(dum).bbox().to_dtype(self.ly.dbu)
        ploc = self.ly.cell(mp).bbox().to_dtype(self.ly.dbu)

        # Centroid row: D | mo1 | mo2 | D [HAND]
        gap = 4.0
        x = 0.0
        bb_dL, t_dL = self.place(c, dum, x - dloc.left, 0)
        x = bb_dL.right + gap
        bb1, t1 = self.place(c, mo, x - mloc.left, 0)
        x = bb1.right + gap
        bb2, t2 = self.place(c, mo, x - mloc.left, 0)
        x = bb2.right + gap
        bb_dR, t_dR = self.place(c, dum, x - dloc.left, 0)
        self.say(f"OTA pair dummies+mo1+mo2: {[bb_dL, bb1, bb2, bb_dR]}")

        # PMOS loads above, aligned to mo1/mo2 (extra gap for M2 drain vias)
        y_p = max(bb1.top, bb2.top) + 10.0
        bb_p1, tp1 = self.place(c, mp, bb1.left - ploc.left, y_p - ploc.bottom)
        bb_p2, tp2 = self.place(c, mp, bb2.left - ploc.left, y_p - ploc.bottom)

        def sd_of(cid, trans):
            cols = self.m1_cols(cid, trans)
            return self._route_mos_sd(c, cols, even_is_drain=True)

        dr1, sr1 = sd_of(mo, t1)
        dr2, sr2 = sd_of(mo, t2)
        drdL, srdL = sd_of(dum, t_dL)
        drdR, srdR = sd_of(dum, t_dR)
        pdr1, psr1 = sd_of(mp, tp1)
        pdr2, psr2 = sd_of(mp, tp2)
        self.say(f"mo1 SD nD={len(dr1)} nS={len(sr1)}; "
                 f"mp1 nD={len(pdr1)} nS={len(psr1)}")

        # Buses: ss/gnd BELOW nmos; d1/d2 BETWEEN nmos and pmos so PMOS
        # drain M2 never crosses the ss bus [LVS].
        y_ss = min(bb1.bottom, bb2.bottom) - 2.5
        y_gnd = y_ss - 3.0
        y_d1 = max(bb1.top, bb2.top) + 3.0
        y_d2 = y_d1 + 3.0
        # keep vdd rail clear of PMOS gate-pad / diode strap Y [LVS]
        y_vdd = max(bb_p1.top, bb_p2.top) + 4.0

        def m1_down_to_m2(cols, y_bus):
            """Extend SD M1 down to y_bus + via (below device; no gate cross)."""
            # via_stack is 0.29 wide; SD col is 0.16 — need M1 enclosure [DRC M1.b]
            land = 0.28  # half-width → 0.56 pad; via 0.29 needs M2.b [DRC]
            for col in cols:
                cx = 0.5 * (col.left + col.right)
                self.box_m1(c, col.left, y_bus, col.right, col.bottom)
                self.box_m1(c, cx - land, y_bus, cx + land, y_bus + 0.40)
                self.box_m2(c, cx - land, y_bus, cx + land, y_bus + 0.40)
                self.place(c, vs12, cx, y_bus + 0.20)
            self.box_m2(c, cols[0].left - 0.25, y_bus,
                        cols[-1].right + 0.25, y_bus + 0.40)

        def m1_up_via_m2(cols, y_bus):
            """Via on existing SD M1 near top; join on M2 above (gate stays M1).

            Do not extend M1 through the gate-pad Y — that shorts G↔D [LVS].
            """
            land = 0.28
            for col in cols:
                cx = 0.5 * (col.left + col.right)
                yv = col.top - 0.20
                self.box_m1(c, cx - land, yv - 0.20, cx + land, yv + 0.20)
                self.box_m2(c, cx - land, yv - 0.20, cx + land, y_bus + 0.40)
                self.place(c, vs12, cx, yv)
            self.box_m2(c, cols[0].left - 0.25, y_bus,
                        cols[-1].right + 0.25, y_bus + 0.40)

        # mo1/mo2 sources → ss (M2 below)
        m1_down_to_m2(sr1 + sr2, y_ss)
        self.box_m2(c, sr1[0].left - 0.25, y_ss,
                    sr2[-1].right + 0.25, y_ss + 0.40)
        sx = sr1[0].left - 2.5
        self._via12(c, vs12, sx, y_ss + 0.20)
        self.box_m2(c, sx - 0.30, y_ss, sr1[0].left, y_ss + 0.40)
        self.box_m1(c, sx - 0.30, y_ss - 1.2, sx + 0.30, y_ss + 0.40)
        self.pin_m1(c, sx, y_ss - 1.0, "ss")

        # mo1 drains UP to y_d1 (direct). mo2 drains jog RIGHT on M2 first so
        # the d2 riser does not cross the d1 bus X/Y [LVS].
        m1_up_via_m2(dr1, y_d1)
        x_d2_lane = bb2.right + 1.5
        for col in dr2:
            cx = 0.5 * (col.left + col.right)
            yv = col.top - 0.20
            land = 0.22
            self.box_m1(c, cx - land, yv - 0.20, cx + land, yv + 0.20)
            self.place(c, vs12, cx, yv)
            # horizontal to outboard lane at just above SD
            self.box_m2(c, cx - land, yv - 0.15, x_d2_lane + 0.25, yv + 0.25)
        self.box_m2(c, x_d2_lane - 0.25, yv - 0.15,
                    x_d2_lane + 0.25, y_d2 + 0.40)
        self.box_m2(c, x_d2_lane - 0.25, y_d2,
                    x_d2_lane + 0.25, y_d2 + 0.40)

        # Dummy SD → gnd (M2 below). Separate L/R buses — a full-width gnd
        # bar would short any signal vertical that crosses this Y [LVS].
        dum_cols = drdL + srdL + drdR + srdR
        m1_down_to_m2(drdL + srdL, y_gnd)
        m1_down_to_m2(drdR + srdR, y_gnd)
        self.box_m2(c, min(dc.left for dc in drdL + srdL) - 0.25, y_gnd,
                    max(dc.right for dc in drdL + srdL) + 0.25, y_gnd + 0.40)
        self.box_m2(c, min(dc.left for dc in drdR + srdR) - 0.25, y_gnd,
                    max(dc.right for dc in drdR + srdR) + 0.25, y_gnd + 0.40)

        # Gates: mo1→xref, mo2→tail_f; pin Y above mid drain buses
        at1 = self.activ_top(mo, t1)
        at2 = self.activ_top(mo, t2)
        g1 = self.poly_gates(mo, t1)
        g2 = self.poly_gates(mo, t2)
        # Gate pad sits on poly above activ; exit outboard clear of d1/d2 M1
        y_xref = y_d2 + 2.5
        self._gate_bus(c, g1, at1, bb1.left - 2.5, y_xref, "xref")
        self._gate_bus(c, g2, at2, bb2.right + 2.5, y_xref, "tail_f")
        # Dummy gates: local M1 short G to SD (all-gnd device) — no long via
        # run that can miss and leave a floating gate net [LVS].
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
            # strap gate M1 to first SD column M1 (G=D=S for dummy)
            sx = 0.5 * (sd_cols[0].left + sd_cols[0].right)
            self.box_m1(c, min(g0.left, sx) - 0.14, y_pad0 + 0.16,
                        max(g1.right, sx) + 0.14, y_pad1 + 0.16)
            self.box_m1(c, sx - 0.14, sd_cols[0].top - 0.05,
                        sx + 0.14, y_pad1 + 0.16)

        # PMOS sources → vdd on M2 (via at SD top). Do NOT extend M1 through
        # the gate-pad Y — that shorts G↔S=vdd and pulls d1 to vdd [LVS].
        m1_up_via_m2(psr1 + psr2, y_vdd)
        self.box_m2(c, psr1[0].left - 0.25, y_vdd,
                    psr2[-1].right + 0.25, y_vdd + 0.40)
        vx = 0.5 * (psr1[0].left + psr2[-1].right)
        self._via12(c, vs12, vx, y_vdd + 0.20)
        self.box_m1(c, vx - 0.30, y_vdd - 0.2, vx + 0.30, y_vdd + 0.60)
        self.pin_m1(c, vx, y_vdd + 0.40, "vdd")

        # PMOS drains: mp1 down to y_d1; mp2 jog to x_d2_lane then to y_d2
        m1_down_to_m2(pdr1, y_d1)
        self.box_m2(c, min(dr1[0].left, pdr1[0].left) - 0.25, y_d1,
                    max(dr1[-1].right, pdr1[-1].right) + 0.25, y_d1 + 0.40)
        for col in pdr2:
            cx = 0.5 * (col.left + col.right)
            land = 0.22
            self.box_m1(c, col.left, y_d2, col.right, col.bottom)
            self.box_m1(c, cx - land, y_d2, cx + land, y_d2 + 0.40)
            # jog: from under PMOS go right on M2 at a Y between y_d2 and PMOS
            y_jog = min(bb_p2.bottom - 1.0, (y_d2 + bb_p2.bottom) * 0.5)
            self.place(c, vs12, cx, y_jog)
            self.box_m1(c, cx - land, y_jog - 0.20, cx + land, col.bottom)
            self.box_m2(c, cx - land, y_jog - 0.15, x_d2_lane + 0.25,
                        y_jog + 0.25)
        self.box_m2(c, x_d2_lane - 0.25, y_d2,
                    x_d2_lane + 0.25, y_jog + 0.25)
        self.box_m2(c, x_d2_lane - 0.30, y_d2, x_d2_lane + 0.30, y_d2 + 0.40)

        # PMOS gates → d1 (diode). Outboard only — no cross-device strap at
        # gate Y (source M2 risers would short G to vdd) [LVS].
        gp1 = self.poly_gates(mp, tp1)
        gp2 = self.poly_gates(mp, tp2)
        atp1 = self.activ_top(mp, tp1)
        atp2 = self.activ_top(mp, tp2)
        x_pg = min(bb_p1.left, bb1.left) - 3.0
        # right gate lane must clear the right-dummy gnd island [LVS]
        x_pg2 = bb_dR.right + 4.0
        y_pad_p = self._gate_bus(c, gp1, atp1, x_pg, atp1 + 1.8,
                                 "d1_gate", label=False)
        self._gate_bus(c, gp2, atp2, x_pg2, atp2 + 1.8, "d2_gate",
                       label=False)
        self._via12(c, vs12, x_pg, y_pad_p)
        self._via12(c, vs12, x_pg2, y_pad_p)
        # left gate → d1 direct. right gate → top-over (above vdd) then left
        # to x_pg — never drops through the dummy gnd Y [LVS].
        self.box_m2(c, x_pg - 0.25, y_d1, x_pg + 0.25, y_pad_p + 0.40)
        self.box_m2(c, x_pg - 0.30, y_d1, max(dr1[-1].right, pdr1[-1].right),
                    y_d1 + 0.40)
        y_over = y_vdd + 2.5
        self.box_m2(c, x_pg2 - 0.25, y_pad_p - 0.10, x_pg2 + 0.25,
                    y_over + 0.40)
        self.box_m2(c, x_pg - 0.25, y_over, x_pg2 + 0.25, y_over + 0.40)
        self.box_m2(c, x_pg - 0.25, y_d1, x_pg + 0.25, y_over + 0.40)

        # out = d2 pin on the d2 lane
        ox = x_d2_lane + 2.0
        self._via12(c, vs12, ox, y_d2 + 0.20)
        self.box_m2(c, x_d2_lane - 0.30, y_d2, ox + 0.30, y_d2 + 0.40)
        self.box_m1(c, ox - 0.30, y_d2 - 0.5, ox + 0.30, y_d2 + 0.40)
        self.pin_m1(c, ox, y_d2 - 0.3, "out")

        # gnd pin far left → left dummy island; right island via bottom skirt
        # below the diode skirt so the mid-gap stays clear for d1 [LVS]
        gx = bb_dL.left - 4.0
        self._via12(c, vs12, gx, y_gnd + 0.20)
        self.box_m2(c, gx - 0.30, y_gnd,
                    min(dc.left for dc in drdL + srdL), y_gnd + 0.40)
        self.box_m1(c, gx - 0.30, y_gnd - 1.2, gx + 0.30, y_gnd + 0.40)
        self.pin_m1(c, gx, y_gnd - 1.0, "gnd")
        y_gnd_tie = y_gnd - 5.0
        x_r = max(dc.right for dc in drdR + srdR)
        self.box_m2(c, x_r - 0.25, y_gnd_tie, x_r + 0.25, y_gnd + 0.40)
        self.box_m2(c, gx - 0.25, y_gnd_tie, x_r + 0.25, y_gnd_tie + 0.40)
        self.box_m2(c, gx - 0.25, y_gnd_tie, gx + 0.25, y_gnd + 0.40)

        # NW fill + ntap LEFT of mp1 (right side is crossed by mp2 gate M1) [LVS]
        nw_y0 = min(bb_p1.bottom, bb_p2.bottom) - 1.0
        nw_y1 = max(bb_p1.top, bb_p2.top) + 1.5
        self.box_nw_fill(c, min(bb_p1.left, bb_p2.left) - 2.5, nw_y0,
                         max(bb_p1.right, bb_p2.right) + 1.5, nw_y1)
        ntap = self.pcell("ntap1", {"w": "0.78u", "l": "0.78u"})
        ntx = bb_p1.left - 2.0
        nty = 0.5 * (bb_p1.bottom + bb_p1.top) - 0.39
        self.place(c, ntap, ntx, nty)
        self.box_m1(c, ntx, nty, ntx + 0.78, nty + 0.78)
        # M2 up to y_vdd (M1 vertical would hit left gate exit at x_pg) [LVS]
        self._via12(c, vs12, ntx + 0.39, nty + 0.39)
        self.box_m2(c, ntx + 0.10, nty + 0.10, ntx + 0.68, y_vdd + 0.40)
        self.box_m2(c, min(vx, ntx) - 0.30, y_vdd,
                    max(vx, ntx + 0.78) + 0.30, y_vdd + 0.40)

        # Outer p+ GR → gnd
        abb = c.bbox().to_dtype(self.ly.dbu)
        ox0, oy0, ox1, oy1 = self._outer_ptap_gr(
            c, abb.left, abb.bottom, abb.right, abb.top, ring=1.0, gap=2.0)
        strap_x = gx - 1.5
        self._via12(c, vs12, strap_x, y_gnd + 0.20)
        self.box_m2(c, strap_x - 0.30, y_gnd, gx + 0.30, y_gnd + 0.40)
        self.box_m1(c, strap_x - 0.30, oy0, strap_x + 0.30, y_gnd + 0.40)

        bb = c.bbox().to_dtype(self.ly.dbu)
        area = bb.width() * bb.height() * 1e-6
        self.say(f"ota_vds bbox {bb} area={area:.4f} mm2")
        self.ota_area = area
        return c.cell_index()

    def write_spice_ota_vds(self):
        open(os.path.join(OUT, "ota_vds.spice"), "w").write(
            """* P2.7.2b ota_vds [SCH amp_common] iss off-cell at ss
.subckt ota_vds xref tail_f out vdd gnd ss
Mmo1 d1 xref ss gnd sg13_lv_nmos w=8.0u l=2.0u ng=2
Mmo2 out tail_f ss gnd sg13_lv_nmos w=8.0u l=2.0u ng=2
Mmp1 d1 d1 vdd vdd sg13_lv_pmos w=4.0u l=2.0u ng=2
Mmp2 out d1 vdd vdd sg13_lv_pmos w=4.0u l=2.0u ng=2
* edge dummies (gates/SD to gnd)
MdL gnd gnd gnd gnd sg13_lv_nmos w=4.0u l=2.0u ng=1
MdR gnd gnd gnd gnd sg13_lv_nmos w=4.0u l=2.0u ng=1
.ends
""")
        self.say("wrote ota_vds.spice")

    def build_d9_rc(self):
        """D9 filter: rhigh 1 MΩ (rbf) folded + mbp_rbf start-up bypass [SCH].

        Ports: nb, nbf, en_vco_bias_bp (=vbp_tail), gnd.
        Serpentine b=16, same R/w (Calculate=l); aspect ≤ 2:1 [decisions
        2026-11-14 D23 footprint finding]. No PCell GR — bulk via ptap→gnd.
        Cont on bypass gate only west of Activ (bank pattern) [LVS].
        nbf on M2 side-lane so it never crosses the resistor body [LVS].
        """
        c = self.ly.create_cell("d9_rc")
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        # Folded serpentine: b=16 → aspect ≈ 1.93 [GDS probe]; R kept by Calculate=l
        RHIGH_BENDS = 16
        rbf = self.pcell("rhigh", {
            "R": "1e6", "w": "0.5u", "b": str(RHIGH_BENDS),
            "Calculate": "l", "guardRingType": "none",
        })
        mbp = self.pcell("nmos", {
            "w": "20.0u", "l": "0.13u", "ng": 4, "m": 1,
            "guardRingType": "none",
        })
        ptap = self.pcell("ptap1", {"w": "0.78u", "l": "0.78u"})

        bb_r, tr = self.place(c, rbf, 0, 0)
        ar_r = max(bb_r.width(), bb_r.height()) / max(
            min(bb_r.width(), bb_r.height()), 1e-9)
        self.say(f"rhigh 1M folded b={RHIGH_BENDS} bbox {bb_r} aspect={ar_r:.2f}")
        # PDK R before (straight b=0 L=354) / after (folded Calculate=l) [SCH/PDK]
        try:
            from sg13g2_pycell_lib.ihp.utility_functions import CbResCalc
            r_before = float(CbResCalc("R", 0, 354.0, 0.5, 0, 0.52, "rhigh"))
            # segment L for b=16 ≈ 20.6 µm at R≈1e6 [PDK probe]
            r_after = float(CbResCalc("R", 0, 20.6, 0.5, RHIGH_BENDS, 0.52, "rhigh"))
            self.say(f"rhigh R before (b=0 L=354)={r_before:.0f} Ohm [PDK]; "
                     f"after (b={RHIGH_BENDS} L=20.6)={r_after:.0f} Ohm [PDK]; "
                     f"target 1e6")
        except Exception as e:
            self.say(f"rhigh R calc skipped: {e}")
        m1s = []
        for s in self.ly.cell(rbf).shapes(self.m1).each():
            if s.is_box():
                m1s.append(s.bbox().transformed(tr).to_dtype(self.ly.dbu))
        assert len(m1s) >= 2, f"rhigh M1 not found: {m1s}"
        bot = min(m1s, key=lambda b: b.bottom)
        top = max(m1s, key=lambda b: b.top)
        nb_x = 0.5 * (bot.left + bot.right)
        nbf_x = 0.5 * (top.left + top.right)
        self.say(f"rhigh terminals bot={bot} top={top}")

        # Bypass MOS below the resistor (nb end) [SCH]
        bloc = self.ly.cell(mbp).bbox().to_dtype(self.ly.dbu)
        x_m = bb_r.left - bloc.left
        y_m = bb_r.bottom - 8.0 - bloc.height()
        bb_m, tm = self.place(c, mbp, x_m, y_m)
        cols = self.m1_cols(mbp, tm)
        drains, sources = self._route_mos_sd(c, cols, even_is_drain=True)
        gates = self.poly_gates(mbp, tm)
        at = self.activ_top(mbp, tm)
        g0, g1 = gates[0], gates[-1]

        # Drain → nb: M1 within columns only; M2 via outboard west [LVS]
        y_nb = bb_m.bottom - 2.5
        for col in drains:
            self.box_m1(c, col.left, y_nb, col.right, col.bottom)
        self.box_m1(c, drains[0].left, y_nb, drains[-1].right, y_nb + 0.28)
        px_nb = bb_m.left - 4.0
        self.box_m1(c, px_nb - 0.30, y_nb, drains[0].left, y_nb + 0.28)
        self._via12(c, vs12, px_nb, y_nb + 0.14)
        # Resistor bottom → nb on M2 (clear of MOS)
        self.box_m1(c, bot.left, bot.bottom - 0.5, bot.right, bot.bottom + 0.05)
        self._via12(c, vs12, nb_x, bot.bottom - 0.25)
        self.box_m2(c, px_nb - 0.30, y_nb, nb_x + 0.30, y_nb + 0.40)
        self.box_m2(c, nb_x - 0.30, y_nb, nb_x + 0.30, bot.bottom - 0.05)
        self.box_m1(c, px_nb - 0.30, y_nb - 1.2, px_nb + 0.30, y_nb + 0.40)
        self.pin_m1(c, px_nb, y_nb - 1.0, "nb")

        # Source → nbf: M2 east lane to resistor top [LVS]
        x_lane = max(bb_r.right, bb_m.right) + 3.0
        y_src = bb_m.top + 2.5
        for col in sources:
            self.box_m1(c, col.left, col.top - 0.05, col.right, y_src)
        self.box_m1(c, sources[0].left, y_src - 0.28, sources[-1].right, y_src)
        px_s = bb_m.right + 2.5
        self.box_m1(c, sources[-1].right, y_src - 0.28, px_s + 0.30, y_src)
        self._via12(c, vs12, px_s, y_src - 0.14)
        self.box_m2(c, px_s - 0.30, y_src - 0.30, x_lane + 0.25, y_src + 0.20)
        self.box_m2(c, x_lane - 0.25, y_src - 0.30, x_lane + 0.25, top.top + 0.5)
        self.box_m1(c, top.left, top.top - 0.05, top.right, top.top + 0.6)
        self._via12(c, vs12, nbf_x, top.top + 0.3)
        self.box_m2(c, nbf_x - 0.25, top.top + 0.1, x_lane + 0.25, top.top + 0.5)
        self.box_m1(c, nbf_x - 0.25, top.top + 0.3, nbf_x + 0.25, top.top + 1.2)
        self.pin_m1(c, nbf_x, top.top + 1.0, "nbf")

        # Gate Cont west of Activ only (bank pattern) — continuous poly, no gap
        y_s0, y_s1 = at + 0.08, at + 0.55
        c.shapes(self.poly).insert(pya.DBox(g0.left, y_s0, g1.right, y_s1))
        for g in gates:
            gx = 0.5 * (g.left + g.right)
            half = 0.5 * (g.right - g.left)
            c.shapes(self.poly).insert(
                pya.DBox(gx - half, g.top - 0.05, gx + half, y_s1))
        x_g = bb_m.left - 3.5
        c.shapes(self.poly).insert(
            pya.DBox(x_g - 0.20, y_s0, g0.left + 0.05, y_s1))
        c.shapes(self.poly).insert(
            pya.DBox(x_g - 0.25, y_s0, x_g + 0.25, y_s0 + 0.55))
        cy0, cy1 = y_s0 + 0.16, y_s0 + 0.32
        c.shapes(self.cont).insert(
            pya.DBox(x_g - 0.08, cy0, x_g + 0.08, cy1))
        # M1 ≥0.18 wide, covers Cont with margin (M1.b / Cont enclosure)
        self.box_m1(c, x_g - 0.20, cy0 - 0.05, x_g + 0.20, y_s0 + 0.70)
        self.pin_m1(c, x_g, y_s0 + 0.85, "en_vco_bias_bp")

        # gnd: ptap only — no metal strap into rhigh body [LVS bulk].
        # Continuous M1 from ptap through pin (gap orphans gnd → bulk=$1) [LVS].
        gx = bb_m.right + 3.0
        y_gnd = y_nb - 3.5
        self.place(c, ptap, gx, y_gnd)
        self.box_m1(c, gx - 0.05, y_gnd - 1.2, gx + 0.83, y_gnd + 0.83)
        self.pin_m1(c, gx + 0.39, y_gnd - 1.0, "gnd")

        bb = c.bbox().to_dtype(self.ly.dbu)
        area = bb.width() * bb.height() * 1e-6
        ar = max(bb.width(), bb.height()) / max(min(bb.width(), bb.height()), 1e-9)
        self.say(f"d9_rc bbox {bb} area={area:.4f} mm2 aspect={ar:.2f}")
        self.d9_area = area
        return c.cell_index()

    def write_spice_d9_rc(self):
        # Folded extract: LVS often reports segment l≈20.6u (b=16); keep w=0.5u.
        # If LVS wants total-path l, adjust after prove [TOOL].
        open(os.path.join(OUT, "d9_rc.spice"), "w").write(
            """* P2.7.2b d9_rc: rbf 1M folded b=16 + mbp_rbf [SCH vco_tail_dac]
* en_vco_bias_bp == vbp_tail (D22 start-up / tail-only bypass gate)
.subckt d9_rc nb nbf en_vco_bias_bp gnd
Rrbf nb nbf gnd rhigh w=0.5u l=20.6u
Mmbp_rbf nb en_vco_bias_bp nbf gnd sg13_lv_nmos w=20.0u l=0.13u ng=4
.ends
""")
        self.say("wrote d9_rc.spice")

    def build_cbf(self):
        """7× cmim ≈69.007 µm → 50 pF [SCH cbf0..6]; PN/swing PASS 2026-11-14.

        PLUS (TM1) → nbf; MINUS (M5) → gnd. Compact 3×3 block (7 tiles, one
        empty slot for routing), M5 abutting (same-net gnd), one outer ptap GR
        [decisions 2026-11-14 D23 footprint finding].
        """
        SIDE = 69.007  # µm = √((50p/7)/1.5f) [PDK]
        N = 7
        c = self.ly.create_cell("cbf")
        mim = self.pcell("cmim", {
            "w": f"{SIDE:.3f}u", "l": f"{SIDE:.3f}u",
            "C": f"{(50e3 / N):.2f}f", "Calculate": "w&l",
            "guardRingType": "none",
        })
        # cmim bottoms: bank uses Metal1→Metal5 via_stack [GDS]
        vs5 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal5",
            "vn_columns": 2, "vn_rows": 2,
        })
        mloc = self.ly.cell(mim).bbox().to_dtype(self.ly.dbu)
        pitch = mloc.width()  # abut M5 same-net [HAND tightest]
        ncols = 3
        # 3×3 block: occupy spine column in every row so TM1 vertical join
        # reaches all tiles; empty corners (0,2) and (2,2) for routing [GDS]
        slots = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (1, 2)]
        assert len(slots) == N
        placed = []
        for col, row in slots:
            ox, oy = col * pitch, row * pitch
            bb, t = self.place(c, mim, ox, oy)
            placed.append((ox, oy, bb, t))
        self.say(f"cbf {N}× cmim 3x3 (corners empty) side={SIDE} pitch={pitch}; "
                 f"tile_bbox={mloc}")

        tm1pin = self.ly.layer(126, 2)
        tm1txt = self.ly.layer(126, 25)

        # Per-tile M5 / TM1 plates (transformed)
        def lyr_boxes(cid, trans, layer):
            out = []
            for s in self.ly.cell(cid).shapes(layer).each():
                if s.is_box():
                    out.append(s.bbox().transformed(trans).to_dtype(self.ly.dbu))
            return out

        m5_plates = []
        tm_plates = []
        for ox, oy, bb, t in placed:
            m5s = lyr_boxes(mim, t, self.m5)
            tms = lyr_boxes(mim, t, self.tm1)
            m5_plates.append(max(
                m5s, key=lambda b: (b.right - b.left) * (b.top - b.bottom)))
            tm_plates.append(max(
                tms, key=lambda b: (b.right - b.left) * (b.top - b.bottom)))

        # MINUS→gnd: via under south edge of each M5 plate → M1 bus
        y_gnd = min(p.bottom for p in m5_plates) - 3.0
        x_left = min(p.left for p in m5_plates)
        x_right = max(p.right for p in m5_plates)
        self.box_m1(c, x_left, y_gnd, x_right, y_gnd + 0.50)
        for pl in m5_plates:
            mx = 0.5 * (pl.left + pl.right)
            y_vs = pl.bottom - 0.2
            bb_vs, _ = self.place(c, vs5, mx - 0.35, y_vs - 0.5)
            self.box_m5(c, bb_vs.left, bb_vs.top - 0.1,
                        bb_vs.right, pl.bottom + 0.3)
            self.box_m1(c, bb_vs.left - 0.1, y_gnd,
                        bb_vs.right + 0.1, bb_vs.bottom + 0.2)
        self.pin_m1(c, 0.5 * (x_left + x_right), y_gnd - 0.8, "gnd")
        self.box_m1(c, 0.5 * (x_left + x_right) - 0.30, y_gnd - 1.0,
                    0.5 * (x_left + x_right) + 0.30, y_gnd + 0.50)

        # PLUS→nbf: fill inter-tile TM1 gaps (same net), pin on a plate [SCH]
        # Prior spine at array mid-X sat in the 2.1 µm col gap → floating pin [GDS].
        tw = 3.0
        by_row = {}
        for i, ((col, row), (ox, oy, bb, t)) in enumerate(zip(slots, placed)):
            by_row.setdefault(row, []).append(tm_plates[i])
        for r, plates in by_row.items():
            plates = sorted(plates, key=lambda b: b.left)
            y0 = min(p.bottom for p in plates) + 1.0
            y1 = max(p.top for p in plates) - 1.0
            for a, b in zip(plates, plates[1:]):
                # solid fill of the ~2.1 µm gap between abutting tiles
                c.shapes(self.tm1).insert(pya.DBox(
                    a.right - 0.2, y0, b.left + 0.2, y1))
        # vertical join on spine column (col=1) — present in every row
        bot = sorted(by_row[0], key=lambda b: b.left)
        join = bot[min(1, len(bot) - 1)]  # col-1 tile of bottom row
        x_spine = 0.5 * (join.left + join.right)
        y_lo = min(p.bottom for p in tm_plates)
        y_hi = max(p.top for p in tm_plates)
        if 1 in by_row:
            c.shapes(self.tm1).insert(pya.DBox(
                x_spine - tw * 0.5, y_lo + 1.0,
                x_spine + tw * 0.5, y_hi - 1.0))
        # nbf pin: continuous stub from plate south edge (overlaps plate)
        y_nbf = y_lo - 5.0
        c.shapes(self.tm1).insert(pya.DBox(
            x_spine - tw * 0.5, y_nbf - 1.0,
            x_spine + tw * 0.5, y_lo + 3.0))
        c.shapes(tm1pin).insert(pya.DBox(
            x_spine - 0.5, y_nbf - 0.5, x_spine + 0.5, y_nbf + 0.5))
        c.shapes(tm1txt).insert(pya.DText("nbf", pya.DTrans(x_spine, y_nbf)))

        # One ptap guard ring around the group [decisions]
        arr_x0 = min(bb.left for _, _, bb, _ in placed)
        arr_y0 = min(bb.bottom for _, _, bb, _ in placed)
        arr_x1 = max(bb.right for _, _, bb, _ in placed)
        arr_y1 = max(bb.top for _, _, bb, _ in placed)
        # Keep pin stubs inside ring by expanding south for gnd/nbf pads
        ox0, oy0, ox1, oy1 = self._outer_ptap_gr(
            c, arr_x0, min(arr_y0, y_gnd - 1.5, y_nbf - 1.5),
            arr_x1, arr_y1, ring=1.0, gap=1.5)
        # Strap GR M1 to gnd pin
        self.box_m1(c, ox0, y_gnd, ox0 + 1.0, oy0 + 1.0)
        self.box_m1(c, ox0, y_gnd, 0.5 * (x_left + x_right), y_gnd + 0.50)

        bb = c.bbox().to_dtype(self.ly.dbu)
        area = bb.width() * bb.height() * 1e-6
        ar = max(bb.width(), bb.height()) / max(min(bb.width(), bb.height()), 1e-9)
        self.say(f"cbf bbox {bb} area={area:.4f} mm2 aspect={ar:.2f} "
                 f"(GR outer {ox0:.1f},{oy0:.1f}→{ox1:.1f},{oy1:.1f})")
        self.cbf_area = area
        return c.cell_index()

    def write_spice_cbf(self):
        # LVS: m=7 @ extract-rounded w/l. Probe often → 69.01u [GDS/PDK].
        open(os.path.join(OUT, "cbf.spice"), "w").write(
            """* P2.7.2b cbf: 7× cmim [SCH cbf0..6]; LVS m=7 @ 68.94u [GDS extract]
.subckt cbf nbf gnd
Ccbf nbf gnd cap_cmim w=68.94u l=68.94u m=7
.ends
""")
        self.say("wrote cbf.spice")

    def _load_child(self, name, strip_pins=True):
        """Copy proven out/*.gds; return (cid, pins, bb).

        strip_pins: remove child pin texts + pin markers so they are not
        top-level ports when instanced (dac_array unit lesson) [LVS].
        """
        gds = os.path.join(OUT, f"{name}.gds")
        ly = pya.Layout()
        ly.read(gds)
        src = ly.top_cell()
        cell = self.ly.create_cell(name + "_j")
        cell.copy_tree(src)
        pins = {}
        for L, D in ((8, 25), (126, 25)):
            lyr = ly.layer(L, D)
            for s in src.shapes(lyr).each():
                if s.is_text():
                    t = s.text
                    pins[t.string] = (
                        t.trans.disp.x * ly.dbu, t.trans.disp.y * ly.dbu)
        if strip_pins:
            for L, D in ((8, 25), (8, 2), (126, 25), (126, 2)):
                lyr = self.ly.layer(L, D)
                cell.shapes(lyr).clear()
        bb = cell.bbox().to_dtype(self.ly.dbu)
        return cell.cell_index(), pins, bb

    def build_tail_join(self, routed=None):
        """Join dac_array + tail_mt + ota_vds + d9_rc + cbf [prompt].

        routed groups: place | power | tail | filter | nb | xraw | bypass | codes
        Signals on M3 in corridors (M4 over dac); power on M2 corridors only
        [spec/p27-layout-notes.md join layer map]. Child pin texts stripped.
        """
        if routed is None:
            routed = {"place", "power", "tail", "filter", "nb", "xraw",
                      "bypass", "codes"}
        c = self.ly.create_cell("tail_block")
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs13 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal3",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs34 = self.pcell("via_stack", {
            "b_layer": "Metal3", "t_layer": "Metal4",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs2t = self.pcell("via_stack", {
            "b_layer": "Metal2", "t_layer": "TopMetal1",
            "vn_columns": 2, "vn_rows": 2,
        })
        vs23 = self.pcell("via_stack", {
            "b_layer": "Metal2", "t_layer": "Metal3",
            "vn_columns": 1, "vn_rows": 1,
        })

        dac_id, dac_p, dac_bb = self._load_child("dac_array")
        mt_id, mt_p, mt_bb = self._load_child("tail_mt")
        ota_id, ota_p, ota_bb = self._load_child("ota_vds")
        d9_id, d9_p, d9_bb = self._load_child("d9_rc")
        cbf_id, cbf_p, cbf_bb = self._load_child("cbf")

        # Compact pack after reshape [HAND / decisions 2026-11-14]:
        #   south strip: dac | ota | d9; mt above; cbf above mt.
        # Target footprint ≈ 0.08 mm² before corridors.
        gap = 6.0
        # mt pin stubs extend ~8 µm south of origin — clear the south strip [GDS]
        gap_mt = max(12.0, 2.0 - mt_bb.bottom)
        ox_dac, oy_dac = 0.0, 0.0
        self.place(c, dac_id, ox_dac, oy_dac)
        ox_ota = dac_bb.width() + gap
        oy_ota = 0.0
        self.place(c, ota_id, ox_ota, oy_ota)
        ox_d9 = ox_ota + ota_bb.width() + gap
        oy_d9 = 0.0
        self.place(c, d9_id, ox_d9, oy_d9)
        row_h = max(dac_bb.height(), ota_bb.height(), d9_bb.height())
        ox_mt, oy_mt = 0.0, row_h + gap_mt
        self.place(c, mt_id, ox_mt, oy_mt)
        ox_cbf, oy_cbf = 0.0, oy_mt + mt_bb.height() + gap
        self.place(c, cbf_id, ox_cbf, oy_cbf)
        plan_w = max(ox_mt + mt_bb.width(), ox_cbf + cbf_bb.width(),
                     ox_d9 + d9_bb.width())
        plan_h = oy_cbf + cbf_bb.height()
        self.say(f"floorplan HAND cells-only {plan_w:.1f}x{plan_h:.1f} um = "
                 f"{plan_w * plan_h * 1e-6:.4f} mm2 (target ≈ 0.08)")

        def P(pins, ox, oy, name):
            x, y = pins[name]
            return ox + x, oy + y

        def strap_m2(x0, y0, x1, y1, w=0.50):
            hw = w / 2
            self.box_m2(c, min(x0, x1) - hw, min(y0, y1) - hw,
                        max(x0, x1) + hw, max(y0, y1) + hw)

        def via_m1m2(x, y, ox=0.0, oy=0.0):
            vx, vy = x + ox, y + oy
            if ox or oy:
                self.box_m1(c, min(x, vx) - 0.20, min(y, vy) - 0.20,
                            max(x, vx) + 0.20, max(y, vy) + 0.20)
            self._via12(c, vs12, vx, vy)

        def strap_m3(x0, y0, x1, y1, w=0.50):
            hw = w / 2
            self.box_m3(c, min(x0, x1) - hw, min(y0, y1) - hw,
                        max(x0, x1) + hw, max(y0, y1) + hw)

        def escape_m3(px, py, tx, ty):
            """M1 pin → M1-M3 via at (tx,ty) in corridor (outside child metal)."""
            self.box_m1(c, min(px, tx) - 0.20, min(py, ty) - 0.20,
                        max(px, tx) + 0.20, max(py, ty) + 0.20)
            self.box_m3(c, tx - 0.30, ty - 0.30, tx + 0.30, ty + 0.30)
            self.place(c, vs13, tx, ty)

        self.say(f"tail_block place d9@({ox_d9},{oy_d9}) dac@({ox_dac},{oy_dac}) "
                 f"ota@({ox_ota},{oy_ota:.1f}) cbf@({ox_cbf},{oy_cbf:.1f}) "
                 f"mt@({ox_mt},{oy_mt:.1f}); routed={sorted(routed)}")

        # Corridor anchors (outside all child bboxes) [layer map]
        x_east_edge = max(
            ox_dac + dac_bb.width(), ox_cbf + cbf_bb.width(),
            ox_mt + mt_bb.width(), ox_ota + ota_bb.width(),
            ox_d9 + d9_bb.width())
        x_west = -8.0
        x_sig_w = -12.0          # M3 signal west of M2 gnd
        x_vdd = x_east_edge + 6.0
        x_gnd_e = x_vdd + 5.0
        x_sig_e = x_gnd_e + 5.0  # M3 signal east of M2 power
        y_south = min(
            oy_mt + mt_bb.bottom, oy_ota + ota_bb.bottom,
            oy_d9 + d9_bb.bottom, oy_cbf + cbf_bb.bottom,
            oy_dac + dac_bb.bottom) - 8.0

        # ---- power: gnd + vdd on M2 corridors only (known-good pattern) ----
        if "power" in routed:
            # New floorplan: dac|ota|d9 south strip — never strap M2 west
            # through dac [LVS]. South-strip gnds go south to y_south first.
            gx_mt, gy_mt = P(mt_p, ox_mt, oy_mt, "gnd")
            gnds_s = [
                P(d9_p, ox_d9, oy_d9, "gnd"),
                P(ota_p, ox_ota, oy_ota, "gnd"),
            ]
            gnds_e = [P(cbf_p, ox_cbf, oy_cbf, "gnd")]
            # gnd south rail stops west of vdd spine — no M2 cross [LVS gnd|vdd]
            x_gnd_south_e = x_vdd - 4.0
            strap_m2(x_west, y_south, x_gnd_south_e, y_south, w=0.60)
            strap_m2(x_west, y_south, x_west, gy_mt + 2.0, w=0.60)
            for gx, gy in gnds_s:
                via_m1m2(gx, gy)
                strap_m2(gx, gy, gx, y_south, w=0.50)
                strap_m2(min(gx, x_gnd_south_e), y_south, x_west, y_south, w=0.50)
            # mt gnd: via at pin, M2 west outside mt, then corridor [LVS]
            x_mt_w = ox_mt + mt_bb.left - 2.0
            via_m1m2(gx_mt, gy_mt)
            strap_m2(gx_mt, gy_mt, x_mt_w, gy_mt, w=0.50)
            strap_m2(x_mt_w, gy_mt, x_west, gy_mt, w=0.50)
            # cbf gnd: east spine all the way south of vdd stub, then west
            # (never cross vdd spine on same Y) [LVS gnd|vdd]
            y_gnd_below = y_south - 6.0
            for gx, gy in gnds_e:
                via_m1m2(gx, gy, ox=2.0)
                strap_m2(gx + 2.0, gy, x_gnd_e, gy, w=0.50)
                strap_m2(x_gnd_e, gy, x_gnd_e, y_gnd_below, w=0.50)
                strap_m2(x_gnd_e, y_gnd_below, x_west, y_gnd_below, w=0.50)
                strap_m2(x_west, y_gnd_below, x_west, y_south, w=0.50)
            via_m1m2(x_west, y_south)
            self.box_m1(c, x_west - 0.30, y_south - 2.5,
                        x_west + 0.30, y_south + 0.30)
            self.pin_m1(c, x_west, y_south - 2.0, "gnd")

            # vdd: dac escapes NORTH into alley (not south through body) [LVS];
            # ota M3 east; east spine; pin north of alley clear of gnd.
            vd_dac = P(dac_p, ox_dac, oy_dac, "vdd")
            vd_ota = P(ota_p, ox_ota, oy_ota, "vdd")
            # alley Y between dac top and mt metal bottom
            y_alley = 0.5 * ((oy_dac + dac_bb.top) + (oy_mt + mt_bb.bottom))
            x_ota_e = ox_ota + ota_bb.right + 2.0
            via_m1m2(*vd_dac)
            strap_m2(vd_dac[0], vd_dac[1], vd_dac[0], y_alley, w=0.50)
            strap_m2(vd_dac[0], y_alley, x_vdd, y_alley, w=0.50)
            # ota: M3 east outside → M2 spine (avoid d1 on M2) [LVS]
            vo = (vd_ota[0] + 1.5, vd_ota[1])
            self.box_m1(c, min(vd_ota[0], vo[0]) - 0.20, vd_ota[1] - 0.20,
                        max(vd_ota[0], vo[0]) + 0.20, vd_ota[1] + 0.20)
            self.box_m3(c, vo[0] - 0.30, vo[1] - 0.30, vo[0] + 0.30, vo[1] + 0.30)
            self.place(c, vs13, *vo)
            strap_m3(vo[0], vo[1], x_ota_e, vo[1])
            self.place(c, vs23, x_ota_e, vo[1])
            self.box_m2(c, x_ota_e - 0.30, vo[1] - 0.30,
                        x_ota_e + 0.30, vo[1] + 0.30)
            strap_m2(x_ota_e, vo[1], x_vdd, vo[1], w=0.50)
            strap_m2(x_vdd, min(vd_ota[1], y_alley), x_vdd, y_alley, w=0.50)
            via_m1m2(x_vdd, y_alley)
            self.box_m1(c, x_vdd - 0.30, y_alley - 0.30,
                        x_vdd + 2.5, y_alley + 0.30)
            self.pin_m1(c, x_vdd + 2.0, y_alley, "vdd")

        # ---- tail port only (M1 stub east of mt — no M2 into mt body) ----
        if "tail" in routed:
            tail_p = P(mt_p, ox_mt, oy_mt, "tail")
            self.box_m1(c, tail_p[0], tail_p[1] - 0.20,
                        tail_p[0] + 4.0, tail_p[1] + 0.20)
            self.pin_m1(c, tail_p[0] + 3.5, tail_p[1], "tail")

        # ---- filter nbf on M3 corridors (around cells; TM1 only at cbf pin) ----
        if "filter" in routed:
            nbf_mt = P(mt_p, ox_mt, oy_mt, "nbf")
            nbf_d9 = P(d9_p, ox_d9, oy_d9, "nbf")
            nbf_cbf = P(cbf_p, ox_cbf, oy_cbf, "nbf")
            y_sky = max(oy_cbf + cbf_bb.top + 4.0, nbf_d9[1] + 20.0)
            # All nbf on east M3 spine — keep clear of west gnd M2 [LVS]
            y_mt_n = oy_mt + mt_bb.top + 3.0
            escape_m3(nbf_mt[0], nbf_mt[1], nbf_mt[0], y_mt_n)
            strap_m3(nbf_mt[0], y_mt_n, x_sig_e, y_mt_n)
            escape_m3(nbf_d9[0], nbf_d9[1], x_sig_e, nbf_d9[1])
            strap_m3(x_sig_e, nbf_d9[1], x_sig_e, y_sky)
            strap_m3(x_sig_e, y_mt_n, x_sig_e, y_sky)
            # cbf: TM1→M2 at pin, M2→M3 at east edge (outside plate array)
            self.place(c, vs2t, nbf_cbf[0] - 0.05, nbf_cbf[1] - 0.05)
            self.box_m2(c, nbf_cbf[0] - 0.40, nbf_cbf[1] - 0.40,
                        nbf_cbf[0] + 0.40, nbf_cbf[1] + 0.40)
            c.shapes(self.tm1).insert(pya.DBox(
                nbf_cbf[0] - 0.40, nbf_cbf[1] - 0.40,
                nbf_cbf[0] + 0.40, nbf_cbf[1] + 0.40))
            # North of cbf to sky (avoid vdd alley under mt) [LVS nbf|vdd]
            y_cbf_n = oy_cbf + cbf_bb.top + 4.0
            self.box_m2(c, nbf_cbf[0] - 0.30, nbf_cbf[1],
                        nbf_cbf[0] + 0.30, y_cbf_n)
            self.place(c, vs23, nbf_cbf[0], y_cbf_n)
            self.box_m3(c, nbf_cbf[0] - 0.30, y_cbf_n - 0.30,
                        nbf_cbf[0] + 0.30, y_cbf_n + 0.30)
            strap_m3(nbf_cbf[0], y_cbf_n, x_sig_e, y_cbf_n)
            strap_m3(x_sig_e, y_cbf_n, x_sig_e, y_sky)
            # nbf port on M3→M1 at east sky
            self.place(c, vs13, x_sig_e, y_sky)
            self.box_m1(c, x_sig_e - 0.30, y_sky - 0.30,
                        x_sig_e + 2.5, y_sky + 0.30)
            self.pin_m1(c, x_sig_e + 2.0, y_sky, "nbf")

        # ---- nb: ota.out ↔ d9.nb on M3 (free over ota/d9; dac owns M3) ----
        # Do NOT M1-jog through cells: that hit ota/d9 rails → gnd|nb|vdd + M1.b
        # [LVS/DRC 2026-11-14]. ota.out is already on M2 — M2–M3 via inside
        # that island (via at pin → M2.b vs existing pin via). d9.nb: M1–M3 at pin.
        if "nb" in routed:
            nb_p = P(d9_p, ox_d9, oy_d9, "nb")
            # out M2 strip local; via on real metal [LVS]
            out_via = (ox_ota + 22.3, oy_ota + 10.38)
            self.box_m3(c, out_via[0] - 0.30, out_via[1] - 0.30,
                        out_via[0] + 0.30, out_via[1] + 0.30)
            self.place(c, vs23, *out_via)
            self.box_m3(c, nb_p[0] - 0.30, nb_p[1] - 0.30,
                        nb_p[0] + 0.30, nb_p[1] + 0.30)
            self.place(c, vs13, *nb_p)
            # South then east between neighbours — avoid xref pad Y [LVS]
            y_nb_cor = min(oy_ota + ota_bb.bottom, oy_d9 + d9_bb.bottom) - 3.0
            strap_m3(out_via[0], out_via[1], out_via[0], y_nb_cor)
            strap_m3(nb_p[0], nb_p[1], nb_p[0], y_nb_cor)
            strap_m3(out_via[0], y_nb_cor, nb_p[0], y_nb_cor)
            x_nb_port = ox_d9 + d9_bb.right + 4.0
            strap_m3(nb_p[0], nb_p[1], x_nb_port, nb_p[1])
            self.place(c, vs13, x_nb_port, nb_p[1])
            self.box_m1(c, x_nb_port - 0.30, nb_p[1] - 0.30,
                        x_nb_port + 0.30, nb_p[1] + 0.30)
            self.pin_m1(c, x_nb_port, nb_p[1], "nb")

        # ---- xraw: dac.xraw ↔ ota.xref — M3 only in gap (dac owns M3) ----
        # Escape dac pin M1 south outside bbox before any via (via M3 would
        # land on dac M3). ota: M1–M3 at xref, M3 free over ota.
        if "xraw" in routed:
            xr = P(dac_p, ox_dac, oy_dac, "xraw")
            xf = P(ota_p, ox_ota, oy_ota, "xref")
            y_gap = oy_dac - 10.0
            y_dac_s = oy_dac + dac_bb.bottom - 2.0
            self.box_m1(c, xr[0] - 0.20, min(xr[1], y_dac_s) - 0.20,
                        xr[0] + 0.20, max(xr[1], y_dac_s) + 0.20)
            self.box_m3(c, xr[0] - 0.30, y_dac_s - 0.30,
                        xr[0] + 0.30, y_dac_s + 0.30)
            self.place(c, vs13, xr[0], y_dac_s)
            strap_m3(xr[0], y_dac_s, xr[0], y_gap)
            # ota xref M1 strip local (4.04..4.32). Via on strip → M2.b vs M2
            # at x=3.93. Jog M1 east into clear space, via at x=6.0.
            xf_via = (ox_ota + 6.0, oy_ota + 10.0)
            self.box_m1(c, ox_ota + 4.04, xf_via[1] - 0.20,
                        xf_via[0] + 0.20, xf_via[1] + 0.20)
            self.box_m3(c, xf_via[0] - 0.30, xf_via[1] - 0.30,
                        xf_via[0] + 0.30, xf_via[1] + 0.30)
            self.place(c, vs13, *xf_via)
            strap_m3(xf_via[0], xf_via[1], xf_via[0], y_gap)
            strap_m3(xr[0], y_gap, xf_via[0], y_gap)
            self.place(c, vs13, xr[0], y_gap)
            self.box_m1(c, xr[0] - 0.30, y_gap - 2.5,
                        xr[0] + 0.30, y_gap + 0.30)
            self.pin_m1(c, xr[0], y_gap - 2.0, "xraw")

        # ---- bypass ports: M1 stubs only, outside neighbour pins ----
        if "bypass" in routed:
            pb = P(dac_p, ox_dac, oy_dac, "pbias")
            # West only — do NOT jog north through the code bus [M1 short]
            self.box_m1(c, pb[0] - 4.0, pb[1] - 0.14, pb[0] + 0.14, pb[1] + 0.14)
            self.pin_m1(c, pb[0] - 3.5, pb[1], "pbias")
            for label, pt, dx, dy in (
                ("vbp_tail", P(d9_p, ox_d9, oy_d9, "en_vco_bias_bp"), -4.0, 0.0),
                ("ss", P(ota_p, ox_ota, oy_ota, "ss"), 0.0, -4.0),
                ("tail_f", P(ota_p, ox_ota, oy_ota, "tail_f"), 5.0, 0.0),
            ):
                self.box_m1(c, min(pt[0], pt[0] + dx) - 0.20,
                            min(pt[1], pt[1] + dy) - 0.20,
                            max(pt[0], pt[0] + dx) + 0.20,
                            max(pt[1], pt[1] + dy) + 0.20)
                self.pin_m1(c, pt[0] + dx, pt[1] + dy, label)

        # ---- code bus: thin M1 east stubs (0.9 µm pitch — continuous to pin) ----
        if "codes" in routed:
            codes = [
                ("code_gnd", P(dac_p, ox_dac, oy_dac, "code_gnd")),
                ("code0", P(dac_p, ox_dac, oy_dac, "code0")),
                ("code1", P(dac_p, ox_dac, oy_dac, "code1")),
                ("code2", P(dac_p, ox_dac, oy_dac, "code2")),
                ("code3", P(dac_p, ox_dac, oy_dac, "code3")),
                ("code4", P(dac_p, ox_dac, oy_dac, "code4")),
                ("code_vdd", P(dac_p, ox_dac, oy_dac, "code_vdd")),
            ]
            for label, pt in codes:
                # Stub must overlap pin pad (gap 0.05 µm → M1.b)
                self.box_m1(c, pt[0], pt[1] - 0.14, pt[0] + 4.6, pt[1] + 0.14)
                self.pin_m1(c, pt[0] + 4.3, pt[1], label)

        bb = c.bbox().to_dtype(self.ly.dbu)
        area = bb.width() * bb.height() * 1e-6
        self.say(f"tail_block bbox {bb} area={area:.4f} mm2")
        self.tail_block_area = area
        # Footprint method: join bbox + core + bank + forecast [decisions]
        forecast = 0.017  # varactor+D22+top [HAND]
        island_fp = 0.1102 + 0.1514 + area + forecast
        self.say(f"join footprint={area:.4f} mm2 [GDS]; "
                 f"island outline forecast sum="
                 f"0.1102+0.1514+{area:.4f}+{forecast:.3f}={island_fp:.4f} "
                 f"(≤0.34 / ≤0.36) [GDS/HAND]")
        self.island_forecast = island_fp
        return c.cell_index()

    def write_spice_tail_join(self):
        """Hierarchical spice matching the five joined cells [SCH wiring]."""
        open(os.path.join(OUT, "tail_block.spice"), "w").write(
            """* P2.7.2b tail_block: dac_array+tail_mt+ota_vds+d9_rc+cbf [SCH]
.subckt dac_unit vdd pbias xd code xraw
Mmdb xd pbias vdd vdd sg13_lv_pmos w=2.0u l=2.0u
Mmsw xraw code xd vdd sg13_lv_pmos w=2.0u l=0.13u
.ends
.subckt dac_array vdd pbias xraw code_gnd code0 code1 code2 code3 code4 code_vdd
Xb0 vdd pbias xd_b0 code_gnd xraw dac_unit
Xb1 vdd pbias xd_b1 code_gnd xraw dac_unit
Xb2 vdd pbias xd_b2 code_gnd xraw dac_unit
Xb3 vdd pbias xd_b3 code_gnd xraw dac_unit
Xb4 vdd pbias xd_b4 code_gnd xraw dac_unit
Xb5 vdd pbias xd_b5 code_gnd xraw dac_unit
Xb6 vdd pbias xd_b6 code_gnd xraw dac_unit
Xb7 vdd pbias xd_b7 code_gnd xraw dac_unit
Xb8 vdd pbias xd_b8 code_gnd xraw dac_unit
Xb9 vdd pbias xd_b9 code_gnd xraw dac_unit
Xb10 vdd pbias xd_b10 code_gnd xraw dac_unit
Xb11 vdd pbias xd_b11 code_gnd xraw dac_unit
Xb12 vdd pbias xd_b12 code_gnd xraw dac_unit
Xb13 vdd pbias xd_b13 code_gnd xraw dac_unit
Xb14 vdd pbias xd_b14 code_gnd xraw dac_unit
Xb15 vdd pbias xd_b15 code_gnd xraw dac_unit
Xb16 vdd pbias xd_b16 code_gnd xraw dac_unit
Xb17 vdd pbias xd_b17 code_gnd xraw dac_unit
Xb18 vdd pbias xd_b18 code_gnd xraw dac_unit
Xb4_0 vdd pbias xd_b4_0 code4 xraw dac_unit
Xb3_0 vdd pbias xd_b3_0 code3 xraw dac_unit
Xb2_0 vdd pbias xd_b2_0 code2 xraw dac_unit
Xb4_1 vdd pbias xd_b4_1 code4 xraw dac_unit
Xb3_1 vdd pbias xd_b3_1 code3 xraw dac_unit
Xb4_2 vdd pbias xd_b4_2 code4 xraw dac_unit
Xb1_0 vdd pbias xd_b1_0 code1 xraw dac_unit
Xb4_3 vdd pbias xd_b4_3 code4 xraw dac_unit
Xb4_4 vdd pbias xd_b4_4 code4 xraw dac_unit
Xb0_0 vdd pbias xd_b0_0 code0 xraw dac_unit
Xb4_5 vdd pbias xd_b4_5 code4 xraw dac_unit
Xb3_2 vdd pbias xd_b3_2 code3 xraw dac_unit
Xb4_6 vdd pbias xd_b4_6 code4 xraw dac_unit
Xb2_1 vdd pbias xd_b2_1 code2 xraw dac_unit
Xb3_3 vdd pbias xd_b3_3 code3 xraw dac_unit
Xb4_7 vdd pbias xd_b4_7 code4 xraw dac_unit
Xb4_8 vdd pbias xd_b4_8 code4 xraw dac_unit
Xb3_4 vdd pbias xd_b3_4 code3 xraw dac_unit
Xb2_2 vdd pbias xd_b2_2 code2 xraw dac_unit
Xb4_9 vdd pbias xd_b4_9 code4 xraw dac_unit
Xb3_5 vdd pbias xd_b3_5 code3 xraw dac_unit
Xb4_10 vdd pbias xd_b4_10 code4 xraw dac_unit
Xb1_1 vdd pbias xd_b1_1 code1 xraw dac_unit
Xb4_11 vdd pbias xd_b4_11 code4 xraw dac_unit
Xb4_12 vdd pbias xd_b4_12 code4 xraw dac_unit
Xdmy vdd pbias xd_dmy code_vdd xraw dac_unit
Xb3_6 vdd pbias xd_b3_6 code3 xraw dac_unit
Xb4_13 vdd pbias xd_b4_13 code4 xraw dac_unit
Xb4_14 vdd pbias xd_b4_14 code4 xraw dac_unit
Xb2_3 vdd pbias xd_b2_3 code2 xraw dac_unit
Xb3_7 vdd pbias xd_b3_7 code3 xraw dac_unit
Xb4_15 vdd pbias xd_b4_15 code4 xraw dac_unit
.ends
.subckt tail_mt tail nbf gnd
Mmt0 tail nbf gnd gnd sg13_lv_nmos w=120.0u l=4.0u ng=24
Mmt1 tail nbf gnd gnd sg13_lv_nmos w=120.0u l=4.0u ng=24
Mmt2 tail nbf gnd gnd sg13_lv_nmos w=120.0u l=4.0u ng=24
Mmt3 tail nbf gnd gnd sg13_lv_nmos w=120.0u l=4.0u ng=24
.ends
.subckt ota_vds xref tail_f out vdd gnd ss
Mmo1 d1 xref ss gnd sg13_lv_nmos w=8.0u l=2.0u ng=2
Mmo2 out tail_f ss gnd sg13_lv_nmos w=8.0u l=2.0u ng=2
Mmp1 d1 d1 vdd vdd sg13_lv_pmos w=4.0u l=2.0u ng=2
Mmp2 out d1 vdd vdd sg13_lv_pmos w=4.0u l=2.0u ng=2
MdL gnd gnd gnd gnd sg13_lv_nmos w=4.0u l=2.0u ng=1
MdR gnd gnd gnd gnd sg13_lv_nmos w=4.0u l=2.0u ng=1
.ends
.subckt d9_rc nb nbf en_vco_bias_bp gnd
Rrbf nb nbf gnd rhigh w=0.5u l=20.6u
Mmbp_rbf nb en_vco_bias_bp nbf gnd sg13_lv_nmos w=20.0u l=0.13u ng=4
.ends
.subckt cbf nbf gnd
Ccbf nbf gnd cap_cmim w=68.94u l=68.94u m=7
.ends
.subckt tail_block tail vdd gnd vbp_tail nb nbf pbias xraw code_gnd code0 code1 code2 code3 code4 code_vdd ss tail_f
* vsense: xraw≡xref [SCH]; vbp_tail≡en_vco_bias_bp [SCH]
Xdac vdd pbias xraw code_gnd code0 code1 code2 code3 code4 code_vdd dac_array
Xmt tail nbf gnd tail_mt
Xota xraw tail_f nb vdd gnd ss ota_vds
Xd9 nb nbf vbp_tail gnd d9_rc
Xcbf nbf gnd cbf
.ends
""")
        self.say("wrote tail_block.spice")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="a",
                    choices=list("abcde") + ["all"] + ["f", "g"])
    ap.add_argument("--nets", default="all",
                    help="array incremental: vdd | vdd,b0 | … | all")
    args = ap.parse_args()
    b = B()
    b.say(f"# P2.7.2b DAC build stage={args.stage} nets={args.nets}\n")

    from collections import Counter
    cnt = Counter(CENTROID_31)
    b.say(f"CENTROID_31 counts: {dict(cnt)}")
    assert cnt["b0"] == 1 and cnt["b1"] == 2 and cnt["b2"] == 4
    assert cnt["b3"] == 8 and cnt["b4"] == 16 and cnt["D"] == 1

    if args.stage in ("a", "all"):
        cid = b.build_dac_unit()
        b.write_cell("dac_unit", cid)
        b.write_spice_dac_unit()

    if args.stage in ("b", "all"):
        if args.nets.strip() == "vdd":
            routed = set()
        elif args.nets.strip() == "all":
            routed = None
        else:
            routed = set()
            for p in args.nets.split(","):
                p = p.strip()
                if p in ("vdd", "pbias", "xraw", ""):
                    continue
                if p.startswith("b") and len(p) == 2:
                    routed.add(p)
                elif p in ("base", "D"):
                    routed.add(p)
                elif p == "code_gnd":
                    routed.add("base")
        cid = b.build_dac_array(routed_codes=routed)
        b.write_cell("dac_array", cid)
        b.write_spice_dac_array(
            routed_codes=None if routed is None else routed)
        if getattr(b, "array_area", 0) > AREA_TARGET_MM2:
            open(os.path.join(OUT, "summary_build.txt"), "w").write(
                "\n".join(b.log) + "\n")
            return 2

    if args.stage in ("c", "all"):
        cid = b.build_tail_mt()
        b.write_cell("tail_mt", cid)
        b.write_spice_tail_mt()

    if args.stage in ("d", "all"):
        cid = b.build_ota_vds()
        b.write_cell("ota_vds", cid)
        b.write_spice_ota_vds()

    if args.stage in ("e", "all"):
        cid = b.build_d9_rc()
        b.write_cell("d9_rc", cid)
        b.write_spice_d9_rc()

    if args.stage in ("f", "all"):
        cid = b.build_cbf()
        b.write_cell("cbf", cid)
        b.write_spice_cbf()

    if args.stage in ("g", "all"):
        # --nets power | power,tail | power,tail,filter | … | all
        if args.nets.strip() == "all":
            routed = None
        else:
            routed = {p.strip() for p in args.nets.split(",") if p.strip()}
            routed.add("place")
        cid = b.build_tail_join(routed=routed)
        b.write_cell("tail_block", cid)
        b.write_spice_tail_join()

    open(os.path.join(OUT, "summary_build.txt"), "w").write("\n".join(b.log) + "\n")
    open(os.path.join(OUT, "centroid_order.json"), "w").write(
        json.dumps({"CENTROID_31": CENTROID_31, "note": "kept"}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
