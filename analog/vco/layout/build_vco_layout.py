#!/usr/bin/env python3
"""P2.7.2 — build VCO layout (KLayout / IHP SG13G2) from accepted xschem sizes.

Run inside the container:

    python3 -u build_vco_layout.py
    # writes: out/vco_top.gds, out/vco_top.gds.gz, out/summary_layout_build.txt

Floorplan (D23 Option A): inductor NW; core east of coil; bank further east
(thermo common-centroid + binary); var / fixed south of tank; tail + amp-cal south;
VR_ANA1 straps and substrate taps. Device sizes from sch/netlists + range.json.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

sys.path[:0] = [
    os.path.join(HERE, "_py_path"),
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python",
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python/pycell4klayout-api/source/python",
]

import pya  # noqa: E402
import sg13g2_pycell_lib  # noqa: E402, F401

IND_GDS = os.path.join(REPO, "sim/em/sg13-octagon-l2n0/tapped/L_2n0_tapped.gds")
RANGE_JSON = os.path.join(REPO, "analog/vco/step2/out/range.json")
INV_JSON = os.path.join(REPO, "analog/vco/sch/netlists/device_inventory.json")

# µm helpers
DBU = 0.001  # 1 nm


def um(x: float) -> int:
    return int(round(float(x) / DBU))


class Builder:
    def __init__(self):
        self.ly = pya.Layout()
        self.ly.dbu = DBU
        self.ly.technology_name = "sg13g2"
        self.lib = pya.Library.library_by_name("SG13_dev", "sg13g2")
        if self.lib is None:
            raise RuntimeError("SG13_dev library not loaded — run inside iic-osic-tools")
        self.lib_ly = self.lib.layout()
        self.layers = {}
        for name, (l, d) in {
            "Metal1": (8, 0), "Metal2": (10, 0), "Metal3": (30, 0),
            "Metal4": (50, 0), "Metal5": (67, 0), "TopMetal1": (126, 0),
            "TopMetal2": (134, 0), "Via1": (19, 0), "text": (63, 0),
            "NWell": (31, 0), "Activ": (1, 0),
        }.items():
            self.layers[name] = self.ly.layer(l, d)
        self.log = []

    def say(self, s=""):
        print(s)
        self.log.append(s)

    def pcell(self, name: str, params: dict):
        decl = self.lib_ly.pcell_declaration(name)
        if decl is None:
            raise KeyError(f"PCell {name} missing")
        # stringify widths like "32.0u"
        p = {}
        for k, v in params.items():
            p[k] = v
        return self.ly.add_pcell_variant(self.lib, decl.id(), p)

    def place(self, parent, cid, x_um, y_um, mirror=False, angle=0):
        if not isinstance(cid, int):
            cid = cid.cell_index()
        t = pya.Trans(pya.Trans.M0 if mirror else pya.Trans.R0, um(x_um), um(y_um))
        if angle:
            t = pya.Trans(angle, False, um(x_um), um(y_um))
        parent.insert(pya.CellInstArray(cid, t))
        # return bbox in parent coordinates
        local = self.ly.cell(cid).bbox()
        return local.transformed(t).to_dtype(self.ly.dbu)

    def label(self, cell, layer, x_um, y_um, text):
        cell.shapes(self.layers[layer]).insert(
            pya.DText(text, pya.DTrans(x_um, y_um)))

    def box(self, cell, layer, x0, y0, x1, y1):
        cell.shapes(self.layers[layer]).insert(
            pya.DBox(x0, y0, x1, y1))

    def strap(self, cell, layer, x0, y0, x1, y1):
        self.box(cell, layer, x0, y0, x1, y1)

    # ------------------------------------------------------------------ cells
    def build_inductor(self):
        ind = pya.Layout()
        ind.read(IND_GDS)
        src = ind.top_cell()
        # copy into our layout
        cell = self.ly.create_cell("L_2n0_tapped")
        cell.copy_tree(src)
        bb = cell.bbox().to_dtype(self.ly.dbu)
        self.say(f"inductor bbox {bb} [EM geometry]")
        return cell.cell_index(), bb

    def build_core(self):
        c = self.ly.create_cell("vco_core")
        # cross-coupled pair, common-centroid: m1 left, m2 right mirrored
        m1 = self.pcell("nmos", {"w": "32.0u", "l": "0.13u", "ng": 8, "m": 1,
                                 "guardRingType": "none"})
        m2 = self.pcell("nmos", {"w": "32.0u", "l": "0.13u", "ng": 8, "m": 1,
                                 "guardRingType": "none"})
        self.place(c, m1, 0, 0)
        self.place(c, m2, 40, 0, mirror=True)
        # fixed MIMs (series pair for C_fix) — clear enclosure overlap
        mim = self.pcell("rfcmim", {"w": "16.0u", "l": "16.0u", "wfeed": "5.0u"})
        mim_l = self.ly.cell(mim).bbox().to_dtype(self.ly.dbu)
        bb0 = self.place(c, mim, -5, 35)
        self.place(c, mim, bb0.right - mim_l.left + 3.0, 35)
        # bias R on fx
        # rhigh ~3.16 kΩ for 0.5×0.96 µm → 200 kΩ @ w=2 µm → l≈15.2 µm [DS]
        rh = self.pcell("rhigh", {"w": "2.0u", "l": "15.2u", "Calculate": "R"})
        self.place(c, rh, 15, 60)
        # labels
        self.label(c, "Metal1", 5, -5, "tp")
        self.label(c, "Metal1", 45, -5, "tn")
        self.label(c, "Metal1", 20, 10, "tail")
        self.label(c, "Metal1", 20, 55, "fx")
        # local TopMetal1 tank stubs (symmetric); TM1.b min space 1.64 µm [DS]
        self.strap(c, "TopMetal1", -10, 20, 70, 22)
        self.strap(c, "TopMetal1", -10, 25, 70, 27)
        self.say(f"vco_core bbox {c.bbox().to_dtype(self.ly.dbu)}")
        return c.cell_index()

    def bank_cell(self, k, w_mim, w_sw, ng_sw, w_bp, ng_bp, thermo=False):
        """One D24 bank bit: 2× MIM, series switch, 2× bypass, 2× 2 MΩ bias R.

        Placement is bbox-driven: rfcmim enclosure ~±5.6 µm beyond plate [DS],
        so pitch and switch Y must clear the real PCell bbox, not just w_mim.
        """
        name = f"bank_cell_{'u' if thermo else 'b'}{k}"
        c = self.ly.create_cell(name)
        # rfcmim Wmin/Lmin = 7 µm [DS]; smaller schematic MIMs use cmim (Lmin 1.14 µm)
        if w_mim + 1e-9 < 7.0:
            mim = self.pcell("cmim", {"w": f"{max(w_mim, 1.14):.4f}u",
                                     "l": f"{max(w_mim, 1.14):.4f}u"})
            self.say(f"  bank[{k}] MIM {w_mim:.3f}u < 7u → cmim (rfcmim floor) [DS]")
        else:
            mim = self.pcell("rfcmim", {"w": f"{w_mim:.4f}u", "l": f"{w_mim:.4f}u",
                                       "wfeed": "5.0u"})
        # probe local MIM bbox (unplaced) to get enclosure
        mim_local = self.ly.cell(mim).bbox().to_dtype(self.ly.dbu)
        # place MIM origin so local (0,0) plate sits with enclosure; pitch = width+3
        bb_m0 = self.place(c, mim, 0, 0)
        bb_m1 = self.place(c, mim, bb_m0.right - mim_local.left + 3.0, 0)
        mim_top = max(bb_m0.top, bb_m1.top)
        mim_bot = min(bb_m0.bottom, bb_m1.bottom)
        mim_right = max(bb_m0.right, bb_m1.right)

        sw = self.pcell("nmos", {"w": f"{w_sw:.2f}u", "l": "0.13u", "ng": int(ng_sw),
                                 "m": 1, "guardRingType": "none"})
        sw_local = self.ly.cell(sw).bbox().to_dtype(self.ly.dbu)
        # clear MIM enclosure by ≥3 µm
        y_sw = mim_top - sw_local.bottom + 3.0
        bb_sw = self.place(c, sw, 0, y_sw)

        bp = self.pcell("nmos", {"w": f"{max(0.15, w_bp):.4f}u", "l": "0.13u",
                                 "ng": max(1, int(ng_bp)), "m": 1,
                                 "guardRingType": "none"})
        bp_local = self.ly.cell(bp).bbox().to_dtype(self.ly.dbu)
        x_bp = bb_sw.right - bp_local.left + 3.0
        bb_bp0 = self.place(c, bp, x_bp, y_sw)
        self.place(c, bp, x_bp, bb_bp0.top - bp_local.bottom + 3.0)

        # 2 MΩ: w=5 µm → l≈60.8 µm [DS]; place to the right of MIM/SW/BP column
        rh = self.pcell("rhigh", {"w": "5.0u", "l": "60.8u", "Calculate": "R"})
        rh_local = self.ly.cell(rh).bbox().to_dtype(self.ly.dbu)
        x_r = max(mim_right, bb_sw.right, bb_bp0.right) - rh_local.left + 3.0
        self.place(c, rh, x_r, mim_bot - rh_local.bottom)
        self.place(c, rh, x_r + rh_local.width() + 3.0, mim_bot - rh_local.bottom)

        self.label(c, "Metal1", bb_m0.left + 1, bb_m0.bottom - 2, f"a{k}")
        self.label(c, "Metal1", bb_m1.left + 1, bb_m1.bottom - 2, f"b{k}")
        self.label(c, "Metal1", bb_sw.left + 1, bb_sw.bottom - 2, f"g{k}")
        return c.cell_index()

    def build_bank(self):
        # sizes from vco_bank.spice (µm)
        mim_w = [2.873, 3.982, 5.596, 7.874, 11.122,
                 15.712, 15.712, 15.712, 15.712, 15.712, 15.712, 15.712]
        sw_w = [10.32, 19.82, 39.15, 77.50, 154.63,
                308.58, 308.58, 308.58, 308.58, 308.58, 308.58, 308.58]
        sw_ng = [4, 8, 16, 31, 62, 123, 123, 123, 123, 123, 123, 123]
        bp_w = [0.15, 0.15, 0.1562, 0.3125, 0.625, 1.25, 1.25, 1.25, 1.25, 1.25, 1.25, 1.25]
        bp_ng = [1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2]
        cells = []
        for k in range(12):
            cells.append(self.bank_cell(
                k, mim_w[k], sw_w[k], sw_ng[k], bp_w[k], bp_ng[k],
                thermo=(k >= 5)))
        top = self.ly.create_cell("vco_bank")
        # binary 0..4 in a column — pitch from measured cell bbox
        y = 0.0
        bin_bbs = []
        for k in range(5):
            bb = self.place(top, cells[k], 0, y)
            bin_bbs.append(bb)
            y = bb.top + 8.0
        y_bin = y
        # thermometer 5..11 common-centroid + dummies; pitch from unit bbox
        thermo = cells[5:]
        dummy = self.bank_cell(99, 15.712, 308.58, 123, 1.25, 2, thermo=True)
        u_bb = self.ly.cell(thermo[0]).bbox().to_dtype(self.ly.dbu)
        pitch_x = u_bb.width() + 8.0
        pitch_y = u_bb.height() + 8.0
        # 2×4 grid: U0 U1 U2 D / U3 U4 U5 U6 ; second dummy under D column
        order = [0, 1, 2, "D", 3, 4, 5, 6]
        x0 = max((bb.right for bb in bin_bbs), default=0) + 12.0
        for i, idx in enumerate(order):
            col, row = i % 4, i // 4
            cid = dummy if idx == "D" else thermo[idx]
            self.place(top, cid, x0 + col * pitch_x, row * pitch_y)
        self.place(top, dummy, x0 + 3 * pitch_x, 2 * pitch_y)
        self.say(f"vco_bank bbox {top.bbox().to_dtype(self.ly.dbu)} "
                 f"(bin height ~{y_bin:.0f} µm; thermo pitch "
                 f"{pitch_x:.1f}×{pitch_y:.1f} µm)")
        return top.cell_index()

    def build_var(self):
        c = self.ly.create_cell("vco_var")
        # coupling MIMs — pitch from real rfcmim enclosure bbox
        mim = self.pcell("rfcmim", {"w": "21.292u", "l": "21.292u", "wfeed": "5.0u"})
        mim_l = self.ly.cell(mim).bbox().to_dtype(self.ly.dbu)
        bb0 = self.place(c, mim, 0, 0)
        bb1 = self.place(c, mim, bb0.right - mim_l.left + 3.0, 0)
        # two SVaricap Nx=10 (half of 20 fingers each) — #753: record Nx
        sv = self.pcell("SVaricap", {"w": "3.74u", "l": "0.3u", "Nx": 10,
                                    "guardRingType": "none"})
        sv_l = self.ly.cell(sv).bbox().to_dtype(self.ly.dbu)
        y_sv = max(bb0.top, bb1.top) - sv_l.bottom + 3.0
        # Nx=10 SVaricap is ~16 µm wide [DS PCell]; pitch from measured bbox
        bb_sv0 = self.place(c, sv, bb0.left - sv_l.left, y_sv)
        bb_sv1 = self.place(c, sv, bb_sv0.right - sv_l.left + 5.0, y_sv)
        # bias R 2 MOhm (w=5 → l≈60.8) + bypass, clear of SVaricap / MIM
        rh = self.pcell("rhigh", {"w": "5.0u", "l": "60.8u", "Calculate": "R"})
        rh_l = self.ly.cell(rh).bbox().to_dtype(self.ly.dbu)
        x_r = max(bb0.right, bb1.right, bb_sv0.right, bb_sv1.right) - rh_l.left + 3.0
        self.place(c, rh, x_r, bb0.bottom - rh_l.bottom)
        self.place(c, rh, x_r + rh_l.width() + 3.0, bb0.bottom - rh_l.bottom)
        bp = self.pcell("nmos", {"w": "5.0u", "l": "0.13u", "ng": 2, "m": 1,
                                 "guardRingType": "none"})
        bp_l = self.ly.cell(bp).bbox().to_dtype(self.ly.dbu)
        y_bp = max(bb_sv0.top, bb_sv1.top) - bp_l.bottom + 3.0
        self.place(c, bp, x_r, y_bp)
        self.place(c, bp, x_r + rh_l.width() + 3.0, y_bp)
        self.label(c, "Metal1", 10, 40, "vt")
        self.label(c, "Metal1", 10, -3, "tp")
        self.label(c, "Metal1", 40, -3, "tn")
        self.label(c, "Metal1", 20, 75, "vbp")
        self.say(f"vco_var bbox {c.bbox().to_dtype(self.ly.dbu)} (SVaricap Nx=10+10)")
        return c.cell_index()

    def _stack_row(self, cell, devices, y, x0=0.0, gap=3.0):
        """Place a list of (pcell_id,) left-to-right at y; return next y above row."""
        x = x0
        top = y
        for cid in devices:
            local = self.ly.cell(cid).bbox().to_dtype(self.ly.dbu)
            bb = self.place(cell, cid, x - local.left, y - local.bottom)
            x = bb.right + gap
            top = max(top, bb.top)
        return top + gap

    def build_tail(self):
        c = self.ly.create_cell("vco_tail_dac")
        # unit-cell DAC common-centroid; bbox-driven rows [SCH layout]
        bits = [(2, 1), (4, 2), (8, 4), (16, 8), (32, 16)]
        y = 0.0
        mm0 = self.pcell("pmos", {"w": "2.0u", "l": "2.0u", "ng": 1, "m": 1,
                                  "guardRingType": "none"})
        y = self._stack_row(c, [mm0], y)
        moff = self.pcell("pmos", {"w": "38.0u", "l": "2.0u", "ng": 19, "m": 1,
                                   "guardRingType": "none"})
        y = self._stack_row(c, [moff], y)
        for i, (w, ng) in enumerate(bits):
            mdb = self.pcell("pmos", {"w": f"{w:.1f}u", "l": "2.0u", "ng": ng, "m": 1,
                                      "guardRingType": "none"})
            msw = self.pcell("pmos", {"w": f"{w:.1f}u", "l": "0.13u", "ng": 1, "m": 1,
                                      "guardRingType": "none"})
            # CC: even bits left, odd bits start further right
            x0 = 0.0 if i % 2 == 0 else 40.0
            y = self._stack_row(c, [mdb, msw], y, x0=x0)
        row = []
        for name, w, l, ng in (
                ("n", 8.0, 2.0, 2), ("n", 8.0, 2.0, 2),
                ("p", 4.0, 2.0, 2), ("p", 4.0, 2.0, 2)):
            pc = "nmos" if name == "n" else "pmos"
            row.append(self.pcell(pc, {"w": f"{w}u", "l": f"{l}u", "ng": ng, "m": 1,
                                       "guardRingType": "none"}))
        y = self._stack_row(c, row, y)
        mt = self.pcell("nmos", {"w": "480.0u", "l": "4.0u", "ng": 96, "m": 1,
                                 "guardRingType": "none"})
        mr = self.pcell("nmos", {"w": "60.0u", "l": "4.0u", "ng": 12, "m": 1,
                                 "guardRingType": "none"})
        y = self._stack_row(c, [mt, mr], y, gap=5.0)
        rh = self.pcell("rhigh", {"w": "5.0u", "l": "30.4u", "Calculate": "R"})  # 1 MΩ
        bp = self.pcell("nmos", {"w": "20.0u", "l": "0.13u", "ng": 4, "m": 1,
                                 "guardRingType": "none"})
        y = self._stack_row(c, [rh, bp], y, gap=5.0)
        # filter / tail C as rfcmim tiles — pitch from enclosure bbox
        mim = self.pcell("rfcmim", {"w": "40.0u", "l": "40.0u", "wfeed": "5.0u"})
        mim_l = self.ly.cell(mim).bbox().to_dtype(self.ly.dbu)
        x = 0.0
        y_m = y
        for i in range(4):
            bb = self.place(c, mim, x - mim_l.left, y_m - mim_l.bottom)
            if i % 2 == 0:
                x = bb.right + 3.0
            else:
                x = 0.0
                y_m = bb.top + 3.0
        self.label(c, "Metal1", 5, 5, "vdd")
        self.label(c, "Metal1", 5, y + 5, "tail")
        self.label(c, "Metal1", 40, y + 5, "vbp_tail")
        self.say(f"vco_tail_dac bbox {c.bbox().to_dtype(self.ly.dbu)}")
        return c.cell_index()

    def build_ampcal(self):
        c = self.ly.create_cell("ampcal_det")
        # detector MOS + SE comparator — bbox-driven grid [SCH]
        specs = [
            ("nmos", 0.5, 0.13, 1), ("nmos", 0.5, 0.13, 1),
            ("nmos", 0.5, 0.13, 1), ("nmos", 0.5, 0.13, 1),
            ("nmos", 4.0, 0.5, 2), ("nmos", 4.0, 0.5, 2),
            ("nmos", 4.0, 0.5, 2), ("nmos", 4.0, 0.5, 2),
            ("pmos", 4.0, 0.5, 2), ("pmos", 4.0, 0.5, 2),
        ]
        y = 0.0
        for i in range(0, len(specs), 2):
            row = []
            for pc, w, l, ng in specs[i:i + 2]:
                row.append(self.pcell(pc, {"w": f"{w}u", "l": f"{l}u", "ng": ng,
                                           "m": 1, "guardRingType": "none"}))
            y = self._stack_row(c, row, y, gap=5.0)
        self.label(c, "Metal1", 5, -3, "tp")
        self.label(c, "Metal1", 25, -3, "tn")
        self.label(c, "Metal1", 10, y + 2, "cmp")
        self.say(f"ampcal_det bbox {c.bbox().to_dtype(self.ly.dbu)}")
        return c.cell_index()

    def add_guards_and_straps(self, top, bb):
        # substrate taps around outline
        pt = self.pcell("ptap1", {})
        # ring of taps every 25 µm
        x0, y0 = bb.left - 10, bb.bottom - 10
        x1, y1 = bb.right + 10, bb.top + 10
        step = 25.0
        x = x0
        while x <= x1:
            self.place(top, pt, x, y0)
            self.place(top, pt, x, y1)
            x += step
        y = y0
        while y <= y1:
            self.place(top, pt, x0, y)
            self.place(top, pt, x1, y)
            y += step
        # VR_ANA1 strap (TopMetal2) along west edge to CT
        self.strap(top, "TopMetal2", x0, (y0 + y1) / 2 - 2, x0 + 15, (y0 + y1) / 2 + 2)
        self.label(top, "TopMetal2", x0 + 1, (y0 + y1) / 2, "VR_ANA1")
        self.label(top, "TopMetal2", x0 + 1, (y0 + y1) / 2 - 10, "ct")

    def build_top(self):
        ind_id, ind_bb = self.build_inductor()
        core_id = self.build_core()
        bank_id = self.build_bank()
        var_id = self.build_var()
        tail_id = self.build_tail()
        amp_id = self.build_ampcal()

        top = self.ly.create_cell("vco_top")
        # D23 Option A: inductor NW; core east of coil; bank further east;
        # var / fixed south of tank; tail + amp-cal south [HAND floorplan]
        ind_bb = self.place(top, ind_id, 0, 0)
        # keep-out: active ≥ 30 µm from inductor bbox (p27-layout-notes)
        x_east = ind_bb.right + 30.0
        core_bb = self.place(top, core_id, x_east, ind_bb.bottom + 60.0)
        bank_bb = self.place(top, bank_id, core_bb.right + 20.0, ind_bb.bottom)
        var_bb = self.place(top, var_id, x_east, core_bb.bottom - 80.0)
        # stack tail then ampcal under var / bank
        y_south = min(var_bb.bottom, bank_bb.bottom, ind_bb.bottom) - 20.0
        tail_bb = self.place(top, tail_id, x_east, y_south - 120.0)
        amp_bb = self.place(top, amp_id, x_east, tail_bb.bottom - 40.0)

        bb = top.bbox().to_dtype(self.ly.dbu)
        self.add_guards_and_straps(top, bb)
        # interface pins (spec/analog-digital-interface.md)
        for name, x, y in (
                ("tp", core_bb.left + 10, core_bb.bottom + 20),
                ("tn", core_bb.left + 50, core_bb.bottom + 20),
                ("vtune", var_bb.left + 10, var_bb.bottom + 10),
                ("vbp", var_bb.left + 30, var_bb.top - 5),
                ("vbp_tail", tail_bb.left + 30, tail_bb.top - 5),
                ("VCO_BAND", bank_bb.left + 10, bank_bb.bottom + 10),
                ("cmp", amp_bb.left + 10, amp_bb.top - 5),
                ("vdd", tail_bb.left + 5, tail_bb.bottom + 5),
                ("gnd", tail_bb.left + 25, tail_bb.bottom + 5),
                ("ct", ind_bb.left + 5, ind_bb.bottom + 5)):
            self.label(top, "Metal2", x, y, name)

        bb = top.bbox().to_dtype(self.ly.dbu)
        area = bb.width() * bb.height() * 1e-6  # mm²
        # active island excl. keep-out / guard ring estimate
        self.say(f"\nvco_top bbox {bb}")
        self.say(f"outline area {area:.4f} mm² [SCH layout] "
                 f"(D23 VCO+inductor budget ≈ 0.15–0.20 mm² core+bank+ind; "
                 f"synth island ≈ 0.45–0.55 mm²)")
        self.say(f"inductor {ind_bb.width()*ind_bb.height()*1e-6:.4f} mm²; "
                 f"bank {bank_bb.width()*bank_bb.height()*1e-6:.4f} mm²; "
                 f"core {core_bb.width()*core_bb.height()*1e-6:.4f} mm²")
        return top.cell_index(), bb, area

    def write(self, top_id, bb, area):
        gds = os.path.join(OUT, "vco_top.gds")
        self.ly.write(gds)
        gz = gds + ".gz"
        with open(gds, "rb") as f_in, gzip.open(gz, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        self.say(f"wrote {gds} ({os.path.getsize(gds)} bytes)")
        self.say(f"wrote {gz} ({os.path.getsize(gz)} bytes)")

        # parasitics for P2.7.3
        paras = [
            "tank differential TopMetal / inductor leads (ΔC, imbalance)",
            "bank plate routing + bypass drain C (range / steps)",
            "V_tune to svaricap well (R, C; hold τ)",
            "detector node (tp/tn tap) C and kick-back",
            "VR_ANA1 strap IR / loop inductance to CT",
            "tail filter / bypass switch C when off",
        ]
        summary = os.path.join(OUT, "summary_layout_build.txt")
        with open(summary, "w") as fh:
            fh.write("# P2.7.2 VCO layout build [SCH layout]\n\n")
            fh.write("PDK SG13G2; container iic-osic-tools; PCells from SG13_dev.\n")
            fh.write("Inductor: exact EM cell `L_2n0_tapped` from "
                     "`sim/em/sg13-octagon-l2n0/tapped/L_2n0_tapped.gds`.\n")
            fh.write("Sizes: `analog/vco/sch/netlists/*.spice` + `step2/out/range.json` "
                     f"(LSB {json.load(open(RANGE_JSON))['lsb']} fF, "
                     f"cfix {json.load(open(RANGE_JSON))['cfix']} fF, "
                     f"nfing {json.load(open(RANGE_JSON))['nfing']}, bank_arch d24).\n\n")
            fh.write("\n".join(self.log) + "\n\n")
            fh.write(f"## Outline\n\nbbox {bb}\narea {area:.4f} mm²\n\n")
            fh.write("## Parasitics for P2.7.3\n\n")
            for p in paras:
                fh.write(f"- {p}\n")
            fh.write("\n## IHP LVS notes\n\n")
            fh.write("- #861 ThickGateOx / SVaricap extraction — checklist Nx/count; "
                     "do not treat clean LVS as proof varactor present.\n")
            fh.write("- #753 SVaricap Nx not checked — drawn Nx=10+10; record here.\n")
            fh.write("- #512 rfcmim series/parallel — one rfcmim PCell per schematic "
                     "instance; avoid combined banks in one extract cell.\n")
        self.say(f"wrote {summary}")
        return gds, gz


def main():
    b = Builder()
    b.say("# P2.7.2 — building vco_top layout\n")
    top_id, bb, area = b.build_top()
    b.write(top_id, bb, area)
    return 0


if __name__ == "__main__":
    sys.exit(main())
