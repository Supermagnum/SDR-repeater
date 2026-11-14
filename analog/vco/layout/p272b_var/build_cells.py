#!/usr/bin/env python3
"""P2.7.2b varactor + bias — bottom-up cells [SCH vco_var / D11].

Prove DRC (density waived) + KLayout LVS + netgen after each step.
SVaricap recognised on this PDK pin (ThickGateOx present) [TOOL sv_probe].
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
POCKET_SHARE_MM2 = 0.0187 / 3.0
POCKET_W_UM = 43.16


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
        self.sv_g1 = (6.105, 0.140)
        self.sv_g2 = (6.105, 4.630)
        self.sv_w = (0.390, 2.385)
        self.mim_plus = (-4.600, 10.645)
        self.mim_minus = (25.890, 10.645)
        self.rhigh_l = 42.095  # extract default; updated after bias_r

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

    def pin_m1(self, cell, x, y, name):
        cell.shapes(self.m1).insert(pya.DBox(x - 0.25, y - 0.25, x + 0.25, y + 0.25))
        cell.shapes(self.m1pin).insert(pya.DBox(x - 0.2, y - 0.2, x + 0.2, y + 0.2))
        cell.shapes(self.m1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def box_m1(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m1).insert(pya.DBox(
            min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    def box_m2(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m2).insert(pya.DBox(
            min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    def box_m5(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m5).insert(pya.DBox(
            min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    def box_tm1(self, cell, x0, y0, x1, y1):
        cell.shapes(self.tm1).insert(pya.DBox(
            min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

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

    # ------------------------------------------------------------------
    def build_sv_pair(self):
        """2× SVaricap; G1→vgp, G2→vgn, W→vt. No M1 bridge across nets."""
        c = self.ly.create_cell("sv_pair")
        sv = self.pcell("SVaricap", {
            "w": "3.74u", "l": "0.3u", "Nx": 10, "guardRingType": "none",
        })
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        sloc = self.ly.cell(sv).bbox().to_dtype(self.ly.dbu)
        gap = 4.0
        bb0, t0 = self.place(c, sv, 0.0, 0.0)
        x1 = bb0.right - sloc.left + gap
        bb1, t1 = self.place(c, sv, x1, 0.0)

        def abs_xy(t, loc):
            return (loc[0] + t.disp.x * self.ly.dbu,
                    loc[1] + t.disp.y * self.ly.dbu)

        p0 = {k: abs_xy(t0, getattr(self, f"sv_{k.lower()}"))
              for k in ("G1", "G2", "W")}
        p1 = {k: abs_xy(t1, getattr(self, f"sv_{k.lower()}"))
              for k in ("G1", "G2", "W")}

        # Pin names G1/G2/W match PCell texts so netgen port match [TOOL]
        # (sch maps G1=vgp, G2=vgn, W=vt)
        y_g1 = min(bb0.bottom, bb1.bottom) - 2.5
        for p in (p0, p1):
            self.box_m1(c, p["G1"][0] - 0.30, y_g1, p["G1"][0] + 0.30, p["G1"][1] + 0.15)
        self.box_m1(c, p0["G1"][0] - 0.30, y_g1, p1["G1"][0] + 0.30, y_g1 + 0.50)
        self.pin_m1(c, 0.5 * (p0["G1"][0] + p1["G1"][0]), y_g1 - 0.1, "G1")

        y_g2 = max(bb0.top, bb1.top) + 2.5
        for p in (p0, p1):
            self.box_m1(c, p["G2"][0] - 0.30, p["G2"][1] - 0.15, p["G2"][0] + 0.30, y_g2)
        self.box_m1(c, p0["G2"][0] - 0.30, y_g2 - 0.50, p1["G2"][0] + 0.30, y_g2)
        self.pin_m1(c, 0.5 * (p0["G2"][0] + p1["G2"][0]), y_g2 + 0.1, "G2")

        # W on M2 only; M1 drop far west, clear of G1 strap
        x_w = min(bb0.left, bb1.left) - 3.5
        for p in (p0, p1):
            self._via12(c, vs12, p["W"][0], p["W"][1])
            self.box_m2(c, x_w - 0.30, p["W"][1] - 0.30, p["W"][0] + 0.30, p["W"][1] + 0.30)
        y_mid = 0.5 * (p0["W"][1] + p1["W"][1])
        self.box_m2(c, x_w - 0.30, min(p0["W"][1], p1["W"][1]) - 0.30,
                    x_w + 0.30, max(p0["W"][1], p1["W"][1]) + 0.30)
        y_w = y_g1 - 2.5
        self.box_m2(c, x_w - 0.30, y_w, x_w + 0.30, y_mid + 0.30)
        self._via12(c, vs12, x_w, y_w + 0.5)
        self.pin_m1(c, x_w, y_w, "W")

        self.say(f"sv_pair bbox {c.bbox().to_dtype(self.ly.dbu)}")
        return c.cell_index()

    def write_spice_sv_pair(self):
        open(os.path.join(OUT, "sv_pair.spice"), "w").write(
            """* P2.7.2b sv_pair [SCH xv1/xv2]; ports G1=vgp G2=vgn W=vt
.subckt sv_pair G1 G2 W
Cxv1 G1 W G2 sub! sg13_hv_svaricap w=3.74u l=0.3u Nx=10
Cxv2 G1 W G2 sub! sg13_hv_svaricap w=3.74u l=0.3u Nx=10
.ends
""")

    # ------------------------------------------------------------------
    def build_mim_couple(self):
        """2× rfcmim stacked; PLUS outside shield; MINUS on M2; TIE→gnd east."""
        c = self.ly.create_cell("mim_couple")
        mim = self.pcell("rfcmim", {
            "w": "21.292u", "l": "21.292u", "wfeed": "5.0u",
        })
        vs52 = self.pcell("via_stack", {
            "b_layer": "Metal2", "t_layer": "Metal5",
            "vn_columns": 2, "vn_rows": 2,
        })
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 2, "vn_rows": 2,
        })
        vs1t = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "TopMetal1",
            "vn_columns": 2, "vn_rows": 2,
        })
        mloc = self.ly.cell(mim).bbox().to_dtype(self.ly.dbu)
        gap = 4.0
        bb_p, _ = self.place(c, mim, 0.0, 0.0)
        oy_p = 0.0
        y_n = bb_p.top - mloc.bottom + gap
        bb_n, _ = self.place(c, mim, 0.0, y_n)
        oy_n = y_n

        # gnd pin EAST of shields (never share X with tank PLUS pins)
        x_gnd = max(bb_p.right, bb_n.right) + 3.5
        y_gnd = 0.5 * (bb_p.bottom + bb_n.top)
        self.pin_m1(c, x_gnd, y_gnd, "gnd")

        for bb, oy, tank, gate in (
            (bb_p, oy_p, "tp", "vgp"),
            (bb_n, oy_n, "tn", "vgn"),
        ):
            x_plus = self.mim_plus[0]
            y_plus = oy + self.mim_plus[1]
            x_minus = self.mim_minus[0]
            y_minus = oy + self.mim_minus[1]

            # PLUS → tank WEST, clear of M1 shield; TM1 ≥2 µm (TM1.a) [DS]
            x_tank = bb.left - 4.0
            self.box_tm1(c, x_plus - 2.0, y_plus - 2.5, x_plus + 2.0, y_plus + 2.5)
            self.box_tm1(c, x_tank - 1.0, y_plus - 1.2, x_plus + 2.0, y_plus + 1.2)
            self.place(c, vs1t, x_tank, y_plus)
            self.box_m1(c, x_tank - 0.50, y_plus - 0.50, x_tank + 0.50, y_plus + 0.50)
            self.box_tm1(c, x_tank - 1.0, y_plus - 1.0, x_tank + 1.0, y_plus + 1.0)
            self.pin_m1(c, x_tank, y_plus - 2.0, tank)
            self.box_m1(c, x_tank - 0.30, y_plus - 2.0, x_tank + 0.30, y_plus)

            # MINUS → gate on M2, drop M1 east of shield (near gnd but not on it)
            self.box_m5(c, x_minus - 1.0, y_minus - 1.0, x_minus + 1.0, y_minus + 1.0)
            self.place(c, vs52, x_minus, y_minus)
            self.box_m2(c, x_minus - 0.40, y_minus - 0.40, x_minus + 0.40, y_minus + 0.40)
            x_gate = bb.right + 2.0
            self.box_m2(c, x_minus - 0.40, y_minus - 0.40, x_gate + 0.40, y_minus + 0.40)
            # M1 drop for gate: between shield and gnd pin
            self._via12(c, vs12, x_gate, y_minus)
            self.pin_m1(c, x_gate, y_minus - 1.5, gate)
            self.box_m1(c, x_gate - 0.25, y_minus - 1.5, x_gate + 0.25, y_minus)

            # TIE: strap shield south → east to gnd (M1 only on/near shield edge)
            self.box_m1(c, bb.left + 1.0, bb.bottom, bb.right - 1.0, bb.bottom + 1.5)
            self.box_m1(c, bb.right - 1.0, bb.bottom, x_gnd + 0.25, bb.bottom + 0.40)

        self.box_m1(c, x_gnd - 0.25, bb_p.bottom, x_gnd + 0.25, bb_n.top)
        self.say(f"mim_couple bbox {c.bbox().to_dtype(self.ly.dbu)}")
        return c.cell_index()

    def write_spice_mim_couple(self):
        # Extract rounds to 21.29u [TOOL]; match for KLayout property compare
        open(os.path.join(OUT, "mim_couple.spice"), "w").write(
            """* P2.7.2b mim_couple [SCH xcp/xcn]
.subckt mim_couple tp tn vgp vgn gnd
Cxcp tp vgp gnd rfcmim w=21.29u l=21.29u wfeed=5u m=1
Cxcn tn vgn gnd rfcmim w=21.29u l=21.29u wfeed=5u m=1
.ends
""")

    # ------------------------------------------------------------------
    def build_bias_r(self):
        c = self.ly.create_cell("bias_r")
        rh = self.pcell("rhigh", {
            "R": "2e6", "w": "0.5u", "b": "16",
            "Calculate": "l", "guardRingType": "none",
        })
        ptap = self.pcell("ptap1", {"w": "0.78u", "l": "0.78u"})
        rloc = self.ly.cell(rh).bbox().to_dtype(self.ly.dbu)
        gap = 4.0
        bb0, t0 = self.place(c, rh, 0.0, 0.0)
        bb1, t1 = self.place(c, rh, bb0.right - rloc.left + gap, 0.0)

        def terms(trans):
            m1s = [s.bbox().transformed(trans).to_dtype(self.ly.dbu)
                   for s in self.ly.cell(rh).shapes(self.m1).each() if s.is_box()]
            return min(m1s, key=lambda b: b.bottom), max(m1s, key=lambda b: b.top)

        bot0, top0 = terms(t0)
        bot1, top1 = terms(t1)
        self.box_m1(c, top0.left, top0.top - 0.05, top0.right, top0.top + 1.2)
        self.pin_m1(c, 0.5 * (top0.left + top0.right), top0.top + 1.0, "vgp")
        self.box_m1(c, top1.left, top1.top - 0.05, top1.right, top1.top + 1.2)
        self.pin_m1(c, 0.5 * (top1.left + top1.right), top1.top + 1.0, "vgn")

        y_vvb = min(bot0.bottom, bot1.bottom) - 1.8
        self.box_m1(c, bot0.left, y_vvb, bot0.right, bot0.bottom + 0.05)
        self.box_m1(c, bot1.left, y_vvb, bot1.right, bot1.bottom + 0.05)
        self.box_m1(c, bot0.left, y_vvb, bot1.right, y_vvb + 0.40)
        self.pin_m1(c, 0.5 * (bot0.left + bot1.right), y_vvb - 0.1, "vvb")

        gx = bb1.right + 2.5
        gy = y_vvb - 2.5
        self.place(c, ptap, gx, gy)
        self.box_m1(c, gx - 0.05, gy - 1.2, gx + 0.83, gy + 0.83)
        self.pin_m1(c, gx + 0.39, gy - 1.0, "gnd")
        self.say(f"bias_r bbox {c.bbox().to_dtype(self.ly.dbu)}")
        return c.cell_index()

    def write_spice_bias_r(self, l=None):
        l = l if l is not None else self.rhigh_l
        open(os.path.join(OUT, "bias_r.spice"), "w").write(
            f"""* P2.7.2b bias_r 2M folded b=16 [SCH rvp/rvn]
.subckt bias_r vgp vgn vvb gnd
Rrvp vgp vvb gnd rhigh w=0.5u l={l:.3f}u ps=0.18u b=16 m=1
Rrvn vgn vvb gnd rhigh w=0.5u l={l:.3f}u ps=0.18u b=16 m=1
.ends
""")

    # ------------------------------------------------------------------
    def build_bypass_pair(self):
        """2× nmos ng=2; gate exit west only — never cross SD columns."""
        c = self.ly.create_cell("bypass_pair")
        mos = self.pcell("nmos", {
            "w": "5.0u", "l": "0.13u", "ng": 2, "m": 1,
            "guardRingType": "none",
        })
        ptap = self.pcell("ptap1", {"w": "0.78u", "l": "0.78u"})
        mloc = self.ly.cell(mos).bbox().to_dtype(self.ly.dbu)
        gap = 6.0
        bb0, t0 = self.place(c, mos, 0.0, 0.0)
        bb1, t1 = self.place(c, mos, bb0.right - mloc.left + gap, 0.0)

        gate_xs = []
        src_ys = []
        for bb, t, dname in ((bb0, t0, "vgp"), (bb1, t1, "vgn")):
            cols = self.m1_cols(mos, t)
            # ng=2 → 3 cols: D S D
            drains = [cols[0], cols[2]]
            sources = [cols[1]]
            gates = self.poly_gates(mos, t)
            at = self.activ_top(mos, t)

            # Drain south
            y_d = bb.bottom - 2.2
            for col in drains:
                self.box_m1(c, col.left, y_d, col.right, col.bottom)
            self.box_m1(c, drains[0].left, y_d, drains[-1].right, y_d + 0.40)
            self.pin_m1(c, 0.5 * (drains[0].left + drains[-1].right), y_d - 0.1, dname)

            # Source north
            y_s = bb.top + 2.2
            for col in sources:
                self.box_m1(c, col.left, col.top - 0.05, col.right, y_s)
            self.box_m1(c, sources[0].left - 0.05, y_s - 0.40, sources[0].right + 0.05, y_s)
            src_ys.append((sources[0], y_s))

            # Gate: Cont WEST of activ only; no horizontal through device
            g0, g1 = gates[0], gates[-1]
            y0, y1 = at + 0.08, at + 0.55
            c.shapes(self.poly).insert(pya.DBox(g0.left, y0, g1.right, y1))
            for g in gates:
                gx = 0.5 * (g.left + g.right)
                half = 0.5 * (g.right - g.left)
                c.shapes(self.poly).insert(
                    pya.DBox(gx - half, g.top - 0.05, gx + half, y1))
            x_g = bb.left - 3.5
            c.shapes(self.poly).insert(pya.DBox(x_g - 0.20, y0, g0.left + 0.05, y1))
            c.shapes(self.poly).insert(pya.DBox(x_g - 0.25, y0, x_g + 0.25, y0 + 0.55))
            c.shapes(self.cont).insert(
                pya.DBox(x_g - 0.08, y0 + 0.16, x_g + 0.08, y0 + 0.32))
            self.box_m1(c, x_g - 0.20, y0 + 0.10, x_g + 0.20, y0 + 0.70)
            gate_xs.append((x_g, y0 + 0.85))

        # Join sources → vvb (north strap continuous through pin) [LVS]
        y_vvb = max(y for _, y in src_ys) + 0.2
        x_lo = min(col.left for col, _ in src_ys)
        x_hi = max(col.right for col, _ in src_ys)
        for col, y_s in src_ys:
            self.box_m1(c, col.left, y_s - 0.40, col.right, y_vvb + 0.80)
        self.box_m1(c, x_lo, y_vvb, x_hi, y_vvb + 0.80)
        self.pin_m1(c, 0.5 * (x_lo + x_hi), y_vvb + 0.40, "vvb")

        # Join gates: each goes WEST to x_bus first (no M1 through neighbour SD)
        # Left device: x_g already west. Right device: route south under, then west.
        x_bus = min(bb0.left, bb1.left) - 5.0
        y_under = min(bb0.bottom, bb1.bottom) - 3.5
        # left gate → bus
        x_g0, y_g0 = gate_xs[0]
        self.box_m1(c, x_bus - 0.25, y_g0 - 0.25, x_g0 + 0.25, y_g0 + 0.25)
        # right gate → down → under → bus (clears left source risers)
        x_g1, y_g1 = gate_xs[1]
        self.box_m1(c, x_g1 - 0.25, y_under, x_g1 + 0.25, y_g1 + 0.25)
        self.box_m1(c, x_bus - 0.25, y_under, x_g1 + 0.25, y_under + 0.50)
        self.box_m1(c, x_bus - 0.25, y_under, x_bus + 0.25, max(y_g0, y_g1) + 0.25)
        self.pin_m1(c, x_bus, max(y_g0, y_g1) + 1.5, "vbp")
        self.box_m1(c, x_bus - 0.25, max(y_g0, y_g1) - 0.25,
                    x_bus + 0.25, max(y_g0, y_g1) + 1.5)

        gx = bb1.right + 2.5
        gy = bb0.bottom - 3.5
        self.place(c, ptap, gx, gy)
        self.box_m1(c, gx - 0.05, gy - 1.2, gx + 0.83, gy + 0.83)
        self.pin_m1(c, gx + 0.39, gy - 1.0, "gnd")
        self.say(f"bypass_pair bbox {c.bbox().to_dtype(self.ly.dbu)}")
        return c.cell_index()

    def write_spice_bypass_pair(self):
        open(os.path.join(OUT, "bypass_pair.spice"), "w").write(
            """* P2.7.2b bypass_pair [SCH mbp_rvp/rvn]
.subckt bypass_pair vgp vgn vbp vvb gnd
Mmbp_rvp vgp vbp vvb gnd sg13_lv_nmos w=5.0u l=0.13u ng=2
Mmbp_rvn vgn vbp vvb gnd sg13_lv_nmos w=5.0u l=0.13u ng=2
.ends
""")

    def _cell_by_name(self, name):
        for c in self.ly.each_cell():
            if c.name == name:
                return c.cell_index()
        raise KeyError(name)

    def _copy_no_pin_texts(self, src_name, dst_name):
        """Copy cell; keep M1pin boxes, drop texts so they are not top ports."""
        src = self.ly.cell(self._cell_by_name(src_name))
        dst = self.ly.create_cell(dst_name)
        dst.copy_tree(src)
        # Record pin positions before deleting texts
        pins = {}
        for s in list(dst.shapes(self.m1txt).each()):
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

    def _strap_m1(self, c, a, b, w=0.40):
        """Manhattan M1 strap a→b (horizontal then vertical), width w ≥ M1.b."""
        ax, ay = a
        bx, by = b
        h = 0.5 * w
        self.box_m1(c, min(ax, bx) - h, ay - h, max(ax, bx) + h, ay + h)
        self.box_m1(c, bx - h, min(ay, by) - h, bx + h, max(ay, by) + h)

    def _strap_m2(self, c, a, b, w=0.40):
        ax, ay = a
        bx, by = b
        h = 0.5 * w
        self.box_m2(c, min(ax, bx) - h, ay - h, max(ax, bx) + h, ay + h)
        self.box_m2(c, bx - h, min(ay, by) - h, bx + h, max(ay, by) + h)

    # ------------------------------------------------------------------
    def build_vco_var(self):
        """Hierarchical join of proven sub-cells; V_tune M2 west shield."""
        c = self.ly.create_cell("vco_var")
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        mim_id, mim_pins = self._copy_no_pin_texts("mim_couple", "mim_couple_j")
        sv_id, sv_pins = self._copy_no_pin_texts("sv_pair", "sv_pair_j")
        br_id, br_pins = self._copy_no_pin_texts("bias_r", "bias_r_j")
        bp_id, bp_pins = self._copy_no_pin_texts("bypass_pair", "bypass_pair_j")
        mloc = self.ly.cell(mim_id).bbox().to_dtype(self.ly.dbu)
        sloc = self.ly.cell(sv_id).bbox().to_dtype(self.ly.dbu)
        rloc = self.ly.cell(br_id).bbox().to_dtype(self.ly.dbu)
        ploc = self.ly.cell(bp_id).bbox().to_dtype(self.ly.dbu)
        gap = 5.0

        # Stack for pocket width: MIM, SV, bias_r, bypass
        bb_m, t_m = self.place(c, mim_id, 0.0, 0.0)
        y = bb_m.top - sloc.bottom + gap
        x_sv = 0.5 * (bb_m.left + bb_m.right) - 0.5 * sloc.width() - sloc.left
        bb_s, t_s = self.place(c, sv_id, x_sv, y)
        y = bb_s.top - rloc.bottom + gap
        x_r = 0.5 * (bb_m.left + bb_m.right) - 0.5 * rloc.width() - rloc.left
        bb_r, t_r = self.place(c, br_id, x_r, y)
        y = bb_r.top - ploc.bottom + gap
        x_p = 0.5 * (bb_m.left + bb_m.right) - 0.5 * ploc.width() - ploc.left
        bb_p, t_p = self.place(c, bp_id, x_p, y)

        pm = self._pins_abs(mim_pins, t_m)
        ps = self._pins_abs(sv_pins, t_s)
        pr = self._pins_abs(br_pins, t_r)
        pp = self._pins_abs(bp_pins, t_p)
        self.say(f"pins mim={list(pm)} sv={list(ps)} bias={list(pr)} byp={list(pp)}")

        # Net joins (sch): G1=vgp, G2=vgn, W=vt
        # vgp: mim.vgp, sv.G1, bias.vgp, byp.vgp
        self._strap_m1(c, pm["vgp"], ps["G1"])
        self._strap_m1(c, ps["G1"], pr["vgp"])
        self._strap_m1(c, pr["vgp"], pp["vgp"])
        # vgn on M2 to avoid crossing vgp
        self._via12(c, vs12, *pm["vgn"])
        self._via12(c, vs12, *ps["G2"])
        self._strap_m2(c, pm["vgn"], ps["G2"])
        self._via12(c, vs12, *pr["vgn"])
        self._strap_m2(c, ps["G2"], pr["vgn"])
        self._via12(c, vs12, *pp["vgn"])
        self._strap_m2(c, pr["vgn"], pp["vgn"])
        # vvb: bias ↔ bypass
        self._strap_m1(c, pr["vvb"], pp["vvb"])
        # gnd: mim ↔ bias ↔ bypass; top pin
        self._strap_m1(c, pm["gnd"], pr["gnd"])
        self._strap_m1(c, pr["gnd"], pp["gnd"])
        self.pin_m1(c, pm["gnd"][0], pm["gnd"][1] - 2.0, "gnd")
        self.box_m1(c, pm["gnd"][0] - 0.25, pm["gnd"][1] - 2.0,
                    pm["gnd"][0] + 0.25, pm["gnd"][1])
        # tank ports from MIM
        self.pin_m1(c, pm["tp"][0], pm["tp"][1], "tp")
        self.pin_m1(c, pm["tn"][0], pm["tn"][1], "tn")
        # vbp from bypass
        self.pin_m1(c, pp["vbp"][0], pp["vbp"][1], "vbp")
        # vt: M2 west spine from sv.W, shielded by gnd M1 flanks
        x_vt = min(bb_m.left, bb_s.left, bb_r.left, bb_p.left) - 4.0
        self._via12(c, vs12, *ps["W"])
        self.box_m2(c, x_vt - 0.30, ps["W"][1] - 0.30, ps["W"][0] + 0.30, ps["W"][1] + 0.30)
        y_vt0 = bb_m.bottom - 2.0
        self.box_m2(c, x_vt - 0.30, y_vt0, x_vt + 0.30, ps["W"][1] + 0.30)
        # shield flanks tied only to gnd pin (south), not through devices
        self.box_m1(c, x_vt - 1.4, y_vt0, x_vt - 0.7, bb_p.top)
        self.box_m1(c, x_vt + 0.7, y_vt0, x_vt + 1.4, bb_p.top)
        self.box_m1(c, x_vt - 1.4, y_vt0 - 0.40, pm["gnd"][0] + 0.25, y_vt0)
        self._via12(c, vs12, x_vt, y_vt0 + 0.5)
        self.pin_m1(c, x_vt, y_vt0 - 1.2, "vt")

        bb = c.bbox().to_dtype(self.ly.dbu)
        area = bb.width() * bb.height() * 1e-6
        self.var_area = area
        self.var_bb = bb
        self.say(f"vco_var bbox {bb} area={area:.4f} mm2 "
                 f"(share {POCKET_SHARE_MM2:.4f}; strip_w={POCKET_W_UM:.2f})")
        self.say(f"pocket fit area={'YES' if area <= POCKET_SHARE_MM2 else 'NO'}; "
                 f"width={'YES' if bb.width() <= POCKET_W_UM + 1 else 'NO'}")
        return c.cell_index()

    def write_spice_vco_var(self, l=None):
        l = l if l is not None else self.rhigh_l
        open(os.path.join(OUT, "vco_var.spice"), "w").write(
            f"""* P2.7.2b vco_var [SCH vco_var D11]
.subckt vco_var tp tn vt vbp gnd
Cxcp tp vgp gnd rfcmim w=21.29u l=21.29u wfeed=5u m=1
Cxcn tn vgn gnd rfcmim w=21.29u l=21.29u wfeed=5u m=1
Rrvp vgp vvb gnd rhigh w=0.5u l={l:.3f}u ps=0.18u b=16 m=1
Rrvn vgn vvb gnd rhigh w=0.5u l={l:.3f}u ps=0.18u b=16 m=1
Cxv1 vgp vt vgn sub! sg13_hv_svaricap w=3.74u l=0.3u Nx=10
Cxv2 vgp vt vgn sub! sg13_hv_svaricap w=3.74u l=0.3u Nx=10
Mmbp_rvp vgp vbp vvb gnd sg13_lv_nmos w=5.0u l=0.13u ng=2
Mmbp_rvn vgn vbp vvb gnd sg13_lv_nmos w=5.0u l=0.13u ng=2
.ends
""")


def prove(cell):
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "run_drc_lvs.py"), "--cell", cell],
        cwd=HERE)
    return r.returncode == 0


def extract_rhigh_l(cell):
    for root, _, files in os.walk(os.path.join(OUT, f"lvs_{cell}")):
        for f in files:
            if f.endswith("_extracted.cir"):
                txt = open(os.path.join(root, f), errors="ignore").read()
                ms = re.findall(r"l=([\d.]+)u\s+ps=[\d.]+u\s+b=16", txt)
                if ms:
                    return float(ms[0])
    return None


def main():
    b = B()
    results = {}

    steps = [
        ("sv_pair", b.build_sv_pair, b.write_spice_sv_pair),
        ("mim_couple", b.build_mim_couple, b.write_spice_mim_couple),
        ("bias_r", b.build_bias_r, b.write_spice_bias_r),
        ("bypass_pair", b.build_bypass_pair, b.write_spice_bypass_pair),
        ("vco_var", b.build_vco_var, b.write_spice_vco_var),
    ]
    for name, builder, writer in steps:
        cid = builder()
        writer()
        b.write_cell(name, cid)
        ok = prove(name)
        if name in ("bias_r", "vco_var"):
            l = extract_rhigh_l(name)
            if l:
                b.rhigh_l = l
                writer(l)
                b.say(f"{name}: spice l←extract {l}u; re-prove")
                ok = prove(name)
        results[name] = ok
        b.say(f"prove {name}: {'PASS' if ok else 'FAIL'}")

    lines = ["# P2.7.2b varactor build summary\n\n"]
    for k, v in results.items():
        lines.append(f"- {k}: {'PASS' if v else 'FAIL'}\n")
    if hasattr(b, "var_area"):
        lines.append(f"\nvco_var area={b.var_area:.4f} mm2 bbox={b.var_bb} [GDS]\n")
        lines.append(f"pocket share={POCKET_SHARE_MM2:.4f} mm2 "
                     f"strip_w={POCKET_W_UM:.2f} um [GDS/HAND]\n")
        lines.append(f"fit area: {'YES' if b.var_area <= POCKET_SHARE_MM2 else 'NO'}\n")
        lines.append(
            f"fit width: {'YES' if b.var_bb.width() <= POCKET_W_UM + 1 else 'NO'}\n")
    open(os.path.join(OUT, "summary_build.txt"), "w").writelines(lines)
    open(os.path.join(OUT, "summary_build_log.txt"), "w").write("\n".join(b.log) + "\n")
    print("".join(lines))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
