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
        """Tail current device mt: 480u/4u ng=96 [SCH amp_common]. Ports: tail, nbf, gnd."""
        c = self.ly.create_cell("tail_mt")
        mt = self.pcell("nmos", {
            "w": "480.0u", "l": "4.0u", "ng": 96, "m": 1,
            "guardRingType": "none",
        })
        ptap = self.pcell("ptap1", {"w": "0.78u", "l": "0.78u"})
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        bb, t = self.place(c, mt, 0, 0)
        cols = self.m1_cols(mt, t)
        gates = self.poly_gates(mt, t)
        at = self.activ_top(mt, t)
        assert len(gates) == 96, len(gates)
        n_col = len(cols)
        assert n_col == 97, n_col
        drains = [cols[i] for i in range(0, n_col, 2)]
        sources = [cols[i] for i in range(1, n_col, 2)]
        self.say(f"tail_mt cols={n_col} drains={len(drains)} sources={len(sources)}")

        # No M1 horizontal across finger array at a Y that other SD drops cross
        # (pair lesson). Per-col M1 drop + via; join on M2 [LVS].
        y_gnd = bb.bottom - 2.0
        y_tail = bb.bottom - 5.0
        for col in sources:
            self.box_m1(c, col.left, y_gnd, col.right, col.bottom)
            self.place(c, vs12, 0.5 * (col.left + col.right), y_gnd + 0.20)
        self.box_m2(c, sources[0].left - 0.2, y_gnd,
                    sources[-1].right + 0.2, y_gnd + 0.40)
        for col in drains:
            self.box_m1(c, col.left, y_tail, col.right, col.bottom)
            self.place(c, vs12, 0.5 * (col.left + col.right), y_tail + 0.20)
        self.box_m2(c, drains[0].left - 0.2, y_tail,
                    drains[-1].right + 0.2, y_tail + 0.40)

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
        self.box_m1(c, g0.left - 0.08, y_pad0 + 0.16, g1.right + 0.08, y_pad1 + 0.16)
        # Gate exit outboard left (no bar over SD)
        x_g = bb.left - 1.5
        self.box_m1(c, g0.left - 0.08, y_pad0 + 0.16, x_g + 0.14, y_pad1 + 0.16)
        y_nbf = y_pad1 + 1.0
        self.box_m1(c, x_g - 0.14, y_pad1, x_g + 0.14, y_nbf + 0.28)
        self.pin_m1(c, x_g, y_nbf + 0.14, "nbf")

        # ptap → gnd via M2 (do not M1-strap across drains)
        px = bb.left - 3.5
        py_tap = 0.5 * (bb.bottom + bb.top) - 0.39
        self.place(c, ptap, px, py_tap)
        # M1 covers ptap and drops to the gnd via Y
        self.box_m1(c, px, y_gnd, px + 0.78, py_tap + 0.78)
        self.place(c, vs12, px + 0.39, y_gnd + 0.20)
        self.box_m2(c, px, y_gnd, sources[0].left, y_gnd + 0.40)

        # Pins outboard — not on a finger column (centre X shorts gnd↔tail via
        # the drain M1 drop that passes the gnd via Y) [LVS].
        gx = sources[0].left - 2.0
        self.place(c, vs12, gx, y_gnd + 0.20)
        self.box_m2(c, gx - 0.25, y_gnd, sources[0].left, y_gnd + 0.40)
        self.box_m1(c, gx - 0.25, y_gnd - 1.0, gx + 0.25, y_gnd + 0.40)
        self.pin_m1(c, gx, y_gnd - 0.8, "gnd")

        tx = drains[-1].right + 2.0
        self.place(c, vs12, tx, y_tail + 0.20)
        self.box_m2(c, drains[-1].right, y_tail, tx + 0.25, y_tail + 0.40)
        self.box_m1(c, tx - 0.25, y_tail - 1.0, tx + 0.25, y_tail + 0.40)
        self.pin_m1(c, tx, y_tail - 0.8, "tail")

        abb = c.bbox().to_dtype(self.ly.dbu)
        area = abb.width() * abb.height() * 1e-6
        self.say(f"tail_mt bbox {abb} area={area:.4f} mm2")
        self.tail_area = area
        return c.cell_index()

    def write_spice_tail_mt(self):
        open(os.path.join(OUT, "tail_mt.spice"), "w").write(
            """* P2.7.2b tail_mt W=480u L=4u ng=96 [SCH amp_common]
.subckt tail_mt tail nbf gnd
Mmt tail nbf gnd gnd sg13_lv_nmos w=480.0u l=4.0u ng=96
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
        """D9 filter: rhigh 1 MΩ (rbf) + mbp_rbf start-up bypass [SCH].

        Ports: nb, nbf, en_vco_bias_bp (=vbp_tail), gnd.
        rhigh with no PCell GR (bank pattern) — bulk via ptap→gnd [LVS].
        Cont on bypass gate only west of Activ (bank pattern) [LVS].
        nbf on M2 side-lane so it never crosses the resistor body [LVS].
        """
        c = self.ly.create_cell("d9_rc")
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        # No PCell GR: prior psub GR M1 rail shorted gnd into nb terminal [LVS]
        rbf = self.pcell("rhigh", {
            "R": "1e6", "w": "0.5u", "guardRingType": "none",
        })
        mbp = self.pcell("nmos", {
            "w": "20.0u", "l": "0.13u", "ng": 4, "m": 1,
            "guardRingType": "none",
        })
        ptap = self.pcell("ptap1", {"w": "0.78u", "l": "0.78u"})

        bb_r, tr = self.place(c, rbf, 0, 0)
        self.say(f"rhigh 1M bbox {bb_r}")
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
        self.say(f"d9_rc bbox {bb} area={area:.4f} mm2")
        self.d9_area = area
        return c.cell_index()

    def write_spice_d9_rc(self):
        open(os.path.join(OUT, "d9_rc.spice"), "w").write(
            """* P2.7.2b d9_rc: rbf 1M + mbp_rbf [SCH vco_tail_dac]
* en_vco_bias_bp == vbp_tail (D22 start-up / tail-only bypass gate)
.subckt d9_rc nb nbf en_vco_bias_bp gnd
Rrbf nb nbf gnd rhigh w=0.5u l=354u
Mmbp_rbf nb en_vco_bias_bp nbf gnd sg13_lv_nmos w=20.0u l=0.13u ng=4
.ends
""")
        self.say("wrote d9_rc.spice")

    def build_cbf(self):
        """16× rfcmim 45.644 µm → 50 pF filter cap [SCH cbf0..15].

        PLUS (TM1) → nbf; MINUS (M5) + TIE (M1 shield) → gnd [SCH].
        All 16 beside (rfcmim solid M1 shield shorts non-gnd M1 under
        dac_array — 0 over devices) [PDK/LVS]. Pitch 60 µm [HAND].
        """
        c = self.ly.create_cell("cbf")
        mim = self.pcell("rfcmim", {
            "w": "45.644u", "l": "45.644u", "wfeed": "5.0u",
        })
        # Tank lesson: M5→M2 then M2→M1 (not M5→M1 direct) [PDK]
        vs52 = self.pcell("via_stack", {
            "b_layer": "Metal2", "t_layer": "Metal5",
            "vn_columns": 2, "vn_rows": 2,
        })
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 2, "vn_rows": 2,
        })
        mloc = self.ly.cell(mim).bbox().to_dtype(self.ly.dbu)
        pitch = 60.0
        # Feed offsets from PCell origin [PDK probe 45.644]
        plus_dx, plus_dy = -4.6, 22.82
        minus_dx, minus_dy = 50.24, 22.82
        nrows, ncols = 4, 4
        origins = []
        for r in range(nrows):
            for col in range(ncols):
                ox = col * pitch
                oy = r * pitch
                self.place(c, mim, ox, oy)
                origins.append((ox, oy))
        self.say(f"cbf 16× rfcmim pitch={pitch}; tile_bbox={mloc}")

        # MINUS→gnd: M5→M2→M1 onto the shield (MINUS|TIE both gnd) [SCH]
        # Drop south of each shield so the via stack clears the M5 plate edge.
        for ox, oy in origins:
            mx, my = ox + minus_dx, oy + minus_dy
            c.shapes(self.m5).insert(
                pya.DBox(mx - 1.2, my - 1.2, mx + 1.2, my + 1.2))
            self.place(c, vs52, mx - 0.05, my - 0.05)
            self.box_m2(c, mx - 1.2, my - 1.2, mx + 1.2, my + 1.2)
            # jog M2 south of shield, then M2→M1 into TIE
            y_drop = oy + mloc.bottom - 2.0
            self.box_m2(c, mx - 0.40, y_drop - 0.40, mx + 0.40, my + 0.40)
            self.place(c, vs12, mx - 0.05, y_drop - 0.05)
            self.box_m1(c, mx - 0.40, y_drop - 0.40, mx + 0.40, y_drop + 0.40)
            # tie into shield M1
            self.box_m1(c, mx - 0.40, y_drop - 0.40,
                        mx + 0.40, oy + mloc.bottom + 1.0)

        # PLUS→nbf: TM1 grid, short symmetric straps [SCH]
        plus_pts = [(ox + plus_dx, oy + plus_dy) for ox, oy in origins]
        # horizontal straps per row
        for r in range(nrows):
            row = plus_pts[r * ncols:(r + 1) * ncols]
            y = row[0][1]
            c.shapes(self.tm1).insert(
                pya.DBox(row[0][0] - 1.0, y - 1.0,
                         row[-1][0] + 1.0, y + 1.0))
        # vertical spine at mid-X of the array
        xs = [p[0] for p in plus_pts]
        ys = [p[1] for p in plus_pts]
        x_spine = 0.5 * (min(xs) + max(xs))
        c.shapes(self.tm1).insert(
            pya.DBox(x_spine - 1.0, min(ys) - 1.0,
                     x_spine + 1.0, max(ys) + 1.0))
        # nbf pin on TM1 → drop to M1 pin (M1 outside shields south)
        y_nbf = min(ys) - 8.0
        c.shapes(self.tm1).insert(
            pya.DBox(x_spine - 1.0, y_nbf, x_spine + 1.0, min(ys) + 1.0))
        # TM1 pin label via M1 for LVS top_lvl_pins (Metal1.pin)
        # Keep nbf on M1 south of all shields with a named pin; TM1 bus is
        # the top-plate net — bridge with a note that extract uses TM1.
        # Place M1 pin connected through... actually PLUS is TM1 only.
        # Use TopMetal1 pin layer if available; else rely on text + via to M1
        # only outside shield for a helper net — wrong. Pin on TM1:
        tm1pin = self.ly.layer(126, 2)
        tm1txt = self.ly.layer(126, 25)
        c.shapes(tm1pin).insert(
            pya.DBox(x_spine - 0.5, y_nbf - 0.5, x_spine + 0.5, y_nbf + 0.5))
        c.shapes(tm1txt).insert(pya.DText("nbf", pya.DTrans(x_spine, y_nbf)))
        c.shapes(self.tm1).insert(
            pya.DBox(x_spine - 1.0, y_nbf - 1.0, x_spine + 1.0, y_nbf + 1.0))

        # gnd: strap M1 shields (already abutting at pitch 60; gap ~3.1 µm)
        # Fill M1 between tiles so shields merge, then south pin.
        for r in range(nrows):
            for col in range(ncols - 1):
                ox0 = col * pitch
                ox1 = (col + 1) * pitch
                oy = r * pitch
                # bridge between adjacent shields at mid-height
                self.box_m1(c, ox0 + mloc.right - 0.5, oy + 20.0,
                            ox1 + mloc.left + 0.5, oy + 25.0)
        for r in range(nrows - 1):
            for col in range(ncols):
                ox = col * pitch
                oy0 = r * pitch
                oy1 = (r + 1) * pitch
                self.box_m1(c, ox + 20.0, oy0 + mloc.top - 0.5,
                            ox + 25.0, oy1 + mloc.bottom + 0.5)
        y_gnd = min(oy for _, oy in origins) + mloc.bottom - 4.0
        x0 = min(ox for ox, _ in origins) + mloc.left
        x1 = max(ox for ox, _ in origins) + mloc.right
        self.box_m1(c, x0, y_gnd, x1, y_gnd + 0.40)
        for ox, oy in origins:
            self.box_m1(c, ox + 20.0, y_gnd,
                        ox + 25.0, oy + mloc.bottom + 0.5)
        self.pin_m1(c, 0.5 * (x0 + x1), y_gnd - 0.8, "gnd")
        self.box_m1(c, 0.5 * (x0 + x1) - 0.30, y_gnd - 1.0,
                    0.5 * (x0 + x1) + 0.30, y_gnd + 0.40)

        bb = c.bbox().to_dtype(self.ly.dbu)
        area = bb.width() * bb.height() * 1e-6
        self.say(f"cbf bbox {bb} area={area:.4f} mm2 (0 over devices)")
        self.cbf_area = area
        return c.cell_index()

    def write_spice_cbf(self):
        # LVS spice: one m=16 device at extract-rounded w/l=45.64u.
        # Sch has 16×45.644u; KLayout combine fails 45.644 vs 45.64 [TOOL].
        open(os.path.join(OUT, "cbf.spice"), "w").write(
            """* P2.7.2b cbf: 16× rfcmim [SCH cbf0..15]; LVS m=16 @ 45.64u [GDS]
.subckt cbf nbf gnd
Ccbf nbf gnd gnd rfcmim w=45.64u l=45.64u wfeed=5u m=16
.ends
""")
        self.say("wrote cbf.spice")

    def _load_child(self, name):
        """Copy a proven out/*.gds top cell into this layout; return (cid, pins)."""
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
        bb = cell.bbox().to_dtype(self.ly.dbu)
        return cell.cell_index(), pins, bb

    def build_tail_join(self):
        """Join dac_array + tail_mt + ota_vds + d9_rc + cbf [prompt].

        Floorplan [HAND]: dac west; ota south; tail_mt east of dac;
        d9_rc north (tall); cbf east beside filter. Codes stay west.
        nbf/tail routed on M2 away from code M1 [SCH].
        """
        c = self.ly.create_cell("tail_block")
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs2t = self.pcell("via_stack", {
            "b_layer": "Metal2", "t_layer": "TopMetal1",
            "vn_columns": 2, "vn_rows": 2,
        })

        dac_id, dac_p, dac_bb = self._load_child("dac_array")
        mt_id, mt_p, mt_bb = self._load_child("tail_mt")
        ota_id, ota_p, ota_bb = self._load_child("ota_vds")
        d9_id, d9_p, d9_bb = self._load_child("d9_rc")
        cbf_id, cbf_p, cbf_bb = self._load_child("cbf")

        # Place: local origin of each child = its GDS (0,0) content frame
        def put(cid, x0, y0):
            """Place so child (0,0) lands at (x0,y0); return pin map in top coords."""
            # child was saved with its own bbox; place at x0,y0 meaning
            # instance origin = (x0,y0) in top.
            self.place(c, cid, x0, y0)
            return x0, y0

        # Compact pack [HAND]: d9 west (narrow/tall); dac+ota; cbf above dac;
        # mt below (long). Avoid placing cbf east of full mt length.
        ox_d9, oy_d9 = 0.0, 0.0
        put(d9_id, ox_d9, oy_d9)
        ox_dac, oy_dac = d9_bb.width() + 15.0, 0.0
        put(dac_id, ox_dac, oy_dac)
        ox_ota, oy_ota = ox_dac, -(ota_bb.height() + 15.0)
        put(ota_id, ox_ota, oy_ota)
        ox_cbf, oy_cbf = ox_dac, dac_bb.height() + 15.0
        put(cbf_id, ox_cbf, oy_cbf)
        ox_mt, oy_mt = ox_dac, oy_ota - mt_bb.height() - 20.0
        put(mt_id, ox_mt, oy_mt)

        def P(pins, ox, oy, name):
            x, y = pins[name]
            return ox + x, oy + y

        def strap_m2(x0, y0, x1, y1, w=0.40):
            self.box_m2(c, min(x0, x1) - w / 2, min(y0, y1) - w / 2,
                        max(x0, x1) + w / 2, max(y0, y1) + w / 2)

        def via_m1m2(x, y):
            self._via12(c, vs12, x, y)

        # --- gnd mesh (M2) touching each gnd pin ---
        gnds = [
            P(mt_p, ox_mt, oy_mt, "gnd"),
            P(ota_p, ox_ota, oy_ota, "gnd"),
            P(d9_p, ox_d9, oy_d9, "gnd"),
            P(cbf_p, ox_cbf, oy_cbf, "gnd"),
        ]
        y_gnd = min(p[1] for p in gnds) - 8.0
        xg0 = min(p[0] for p in gnds) - 2.0
        xg1 = max(p[0] for p in gnds) + 2.0
        strap_m2(xg0, y_gnd, xg1, y_gnd, w=0.50)
        for gx, gy in gnds:
            via_m1m2(gx, gy)
            strap_m2(gx, gy, gx, y_gnd)
        self.box_m1(c, xg0, y_gnd - 1.2, xg0 + 0.60, y_gnd + 0.40)
        via_m1m2(xg0 + 0.30, y_gnd)
        self.pin_m1(c, xg0 + 0.30, y_gnd - 1.0, "gnd")

        # --- vdd: dac + ota ---
        vd_dac = P(dac_p, ox_dac, oy_dac, "vdd")
        vd_ota = P(ota_p, ox_ota, oy_ota, "vdd")
        via_m1m2(*vd_dac)
        via_m1m2(*vd_ota)
        strap_m2(vd_dac[0], vd_dac[1], vd_ota[0], vd_dac[1])
        strap_m2(vd_ota[0], vd_dac[1], vd_ota[0], vd_ota[1])
        self.pin_m1(c, vd_dac[0], vd_dac[1] + 2.0, "vdd")
        self.box_m1(c, vd_dac[0] - 0.30, vd_dac[1],
                    vd_dac[0] + 0.30, vd_dac[1] + 2.2)

        # --- xraw (dac) ↔ xref (ota) on M2 ---
        xr = P(dac_p, ox_dac, oy_dac, "xraw")
        xf = P(ota_p, ox_ota, oy_ota, "xref")
        via_m1m2(*xr)
        via_m1m2(*xf)
        strap_m2(xr[0], xr[1], xr[0], xf[1])
        strap_m2(xr[0], xf[1], xf[0], xf[1])
        self.pin_m1(c, xr[0] - 2.0, xr[1], "xraw")
        self.box_m1(c, xr[0] - 2.2, xr[1] - 0.30, xr[0], xr[1] + 0.30)

        # --- ota out ↔ d9 nb ---
        out_p = P(ota_p, ox_ota, oy_ota, "out")
        nb_p = P(d9_p, ox_d9, oy_d9, "nb")
        via_m1m2(*out_p)
        via_m1m2(*nb_p)
        # jog east of dac codes then north to d9
        x_jog = dac_bb.width() + 10.0
        strap_m2(out_p[0], out_p[1], x_jog, out_p[1])
        strap_m2(x_jog, out_p[1], x_jog, nb_p[1])
        strap_m2(x_jog, nb_p[1], nb_p[0], nb_p[1])
        self.pin_m1(c, nb_p[0] - 2.0, nb_p[1], "nb")
        self.box_m1(c, nb_p[0] - 2.2, nb_p[1] - 0.30, nb_p[0], nb_p[1] + 0.30)

        # --- nbf: mt + d9 + cbf(TM1) ---
        nbf_mt = P(mt_p, ox_mt, oy_mt, "nbf")
        nbf_d9 = P(d9_p, ox_d9, oy_d9, "nbf")
        nbf_cbf = P(cbf_p, ox_cbf, oy_cbf, "nbf")  # TM1
        via_m1m2(*nbf_mt)
        via_m1m2(*nbf_d9)
        # cbf nbf is TM1 → via to M2
        self.place(c, vs2t, nbf_cbf[0] - 0.05, nbf_cbf[1] - 0.05)
        self.box_m2(c, nbf_cbf[0] - 0.40, nbf_cbf[1] - 0.40,
                    nbf_cbf[0] + 0.40, nbf_cbf[1] + 0.40)
        c.shapes(self.tm1).insert(
            pya.DBox(nbf_cbf[0] - 0.40, nbf_cbf[1] - 0.40,
                     nbf_cbf[0] + 0.40, nbf_cbf[1] + 0.40))
        # M2 spine east of dac, away from codes
        x_nbf = ox_mt - 5.0
        strap_m2(nbf_mt[0], nbf_mt[1], x_nbf, nbf_mt[1])
        strap_m2(x_nbf, nbf_mt[1], x_nbf, nbf_d9[1])
        strap_m2(x_nbf, nbf_d9[1], nbf_d9[0], nbf_d9[1])
        strap_m2(x_nbf, nbf_mt[1], nbf_cbf[0], nbf_mt[1])
        strap_m2(nbf_cbf[0], nbf_mt[1], nbf_cbf[0], nbf_cbf[1])
        self.box_m1(c, x_nbf - 0.30, nbf_mt[1] - 2.0, x_nbf + 0.30, nbf_mt[1])
        via_m1m2(x_nbf, nbf_mt[1] - 1.5)
        self.pin_m1(c, x_nbf, nbf_mt[1] - 1.8, "nbf")

        # --- tail port (east, matches core stub) ---
        tail_p = P(mt_p, ox_mt, oy_mt, "tail")
        self.pin_m1(c, tail_p[0] + 2.0, tail_p[1], "tail")
        self.box_m1(c, tail_p[0], tail_p[1] - 0.30,
                    tail_p[0] + 2.2, tail_p[1] + 0.30)

        # --- remaining ports: copy pin near child pin ---
        for label, pt in (
            ("pbias", P(dac_p, ox_dac, oy_dac, "pbias")),
            ("code_gnd", P(dac_p, ox_dac, oy_dac, "code_gnd")),
            ("code0", P(dac_p, ox_dac, oy_dac, "code0")),
            ("code1", P(dac_p, ox_dac, oy_dac, "code1")),
            ("code2", P(dac_p, ox_dac, oy_dac, "code2")),
            ("code3", P(dac_p, ox_dac, oy_dac, "code3")),
            ("code4", P(dac_p, ox_dac, oy_dac, "code4")),
            ("code_vdd", P(dac_p, ox_dac, oy_dac, "code_vdd")),
            ("vbp_tail", P(d9_p, ox_d9, oy_d9, "en_vco_bias_bp")),
            ("ss", P(ota_p, ox_ota, oy_ota, "ss")),
            ("tail_f", P(ota_p, ox_ota, oy_ota, "tail_f")),
        ):
            self.pin_m1(c, pt[0] + 1.5, pt[1], label)
            self.box_m1(c, pt[0], pt[1] - 0.25, pt[0] + 1.7, pt[1] + 0.25)

        self.say(f"tail_block placed dac@0 ota@{oy_ota:.1f} mt@{ox_mt:.1f} "
                 f"d9@{oy_d9:.1f} cbf@{ox_cbf:.1f}")
        bb = c.bbox().to_dtype(self.ly.dbu)
        area = bb.width() * bb.height() * 1e-6
        self.say(f"tail_block bbox {bb} area={area:.4f} mm2")
        self.tail_block_area = area
        # Island tally is sum of sub-block GDS areas (floorplan §8 style), not
        # the joined bbox (packing whitespace) [GDS].
        parts_sum = (0.0068 + 0.0058 + 0.0017 + 0.0039 + 0.0574)  # dac..cbf
        island_sum = 0.1102 + 0.1514 + parts_sum
        self.say(f"parts sum (dac+mt+ota+d9+cbf)={parts_sum:.4f} mm2 [GDS]")
        self.say(f"island sum core+bank+parts={island_sum:.4f} mm2 "
                 f"(limit 0.34) [GDS]; join bbox={area:.4f}")
        self.island_forecast = island_sum
        # Varactor / D22 / top-routing headroom
        head = 0.34 - island_sum
        self.say(f"headroom for varactor+D22+top route ≈ {head:.4f} mm2 [HAND]")
        if island_sum > 0.34:
            # 32 tiles at same C: side /√2 → area /2 for the array [HAND]
            save = 0.0574 * 0.5
            self.say(f"OVER BUDGET: 32 smaller tiles would save ≈{save:.4f} mm2 "
                     f"[HAND] — stop for decision")
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
Mmt tail nbf gnd gnd sg13_lv_nmos w=480.0u l=4.0u ng=96
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
Rrbf nb nbf gnd rhigh w=0.5u l=354u
Mmbp_rbf nb en_vco_bias_bp nbf gnd sg13_lv_nmos w=20.0u l=0.13u ng=4
.ends
.subckt cbf nbf gnd
Ccbf nbf gnd gnd rfcmim w=45.64u l=45.64u wfeed=5u m=16
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
        # Prerequisites: proven GDS for each child in out/
        cid = b.build_tail_join()
        b.write_cell("tail_block", cid)
        b.write_spice_tail_join()

    open(os.path.join(OUT, "summary_build.txt"), "w").write("\n".join(b.log) + "\n")
    open(os.path.join(OUT, "centroid_order.json"), "w").write(
        json.dumps({"CENTROID_31": CENTROID_31, "note": "kept"}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
