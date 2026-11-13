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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="a",
                    choices=list("abcde") + ["all"])
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

    if args.stage in ("d", "e") and args.stage != "all":
        b.say(f"stage {args.stage}: not yet implemented")
        return 1

    open(os.path.join(OUT, "summary_build.txt"), "w").write("\n".join(b.log) + "\n")
    open(os.path.join(OUT, "centroid_order.json"), "w").write(
        json.dumps({"CENTROID_31": CENTROID_31, "note": "kept"}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
