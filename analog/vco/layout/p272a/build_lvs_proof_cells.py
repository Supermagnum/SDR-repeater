#!/usr/bin/env python3
"""P2.7.2a — small routed cells to prove KLayout extract + netgen LVS.

dac_unit: single-finger PMOS pair (mdb L=2u W=4u ng=1; msw L=0.13u W=4u ng=1)
bank_unit: D24 LSB cell (cmim + switch ng=1 + bias R + bypass)

IHP pin convention (LVS layers_definitions):
  metal1 drawing 8/0, metal1_pin polygons 8/2, metal1_text labels 8/25.
Gate poly needs Cont+M1 added (PCell has no gate contact).
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
        self.m1pin = self.ly.layer(8, 2)      # metal1_pin polygons
        self.m1txt = self.ly.layer(8, 25)     # metal1_text labels
        self.cont = self.ly.layer(6, 0)
        self.poly = self.ly.layer(5, 0)
        self.activ = self.ly.layer(1, 0)
        self.nsd = self.ly.layer(7, 0)
        self.nwell = self.ly.layer(31, 0)
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
        """Return sorted list of M1 column bboxes in µm after placement."""
        cell = self.ly.cell(cid)
        cols = []
        for s in cell.shapes(self.m1).each():
            if s.is_box():
                cols.append(s.bbox().transformed(trans).to_dtype(self.ly.dbu))
        # unique by centre-x
        uniq = {}
        for b in cols:
            cx = round((b.left + b.right) / 2, 3)
            uniq[cx] = b
        return [uniq[k] for k in sorted(uniq)]

    def poly_gate(self, cid, trans):
        cell = self.ly.cell(cid)
        boxes = []
        for s in cell.shapes(self.poly).each():
            if s.is_box():
                boxes.append(s.bbox().transformed(trans).to_dtype(self.ly.dbu))
        if not boxes:
            return None
        # merge extent
        b0 = boxes[0]
        for b in boxes[1:]:
            b0 = pya.DBox(min(b0.left, b.left), min(b0.bottom, b.bottom),
                          max(b0.right, b.right), max(b0.top, b.top))
        return b0

    def pin(self, cell, x, y, name):
        """Label on 8/25 + pin marker 8/2 + M1 landing, ≥0.18 µm from neighbours."""
        cell.shapes(self.m1).insert(pya.DBox(x - 0.4, y - 0.4, x + 0.4, y + 0.4))
        cell.shapes(self.m1pin).insert(pya.DBox(x - 0.3, y - 0.3, x + 0.3, y + 0.3))
        cell.shapes(self.m1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def box_m1(self, cell, x0, y0, x1, y1):
        cell.shapes(self.m1).insert(pya.DBox(x0, y0, x1, y1))

    def gate_contact(self, cell, gate_bb, x_pin, y_pin, name, side="left"):
        """Poly side-extension + Cont outside Activ (clears Cnt.b vs S/D Cont).

        Cont on the top overhang sits next to S/D Conts → Cnt.b. Extend poly
        sideways, place Cont there, jog M1 up, then out to the pin.
        """
        gy0 = gate_bb.top - 0.16
        gy1 = gate_bb.top
        if side == "left":
            # poly stub to the left of the gate
            px1 = gate_bb.left
            px0 = px1 - 0.6
            cx = px0 + 0.2
        else:
            px0 = gate_bb.right
            px1 = px0 + 0.6
            cx = px1 - 0.2
        cell.shapes(self.poly).insert(pya.DBox(px0, gy0, px1, gy1))
        cell.shapes(self.cont).insert(pya.DBox(cx - 0.08, gy0, cx + 0.08, gy1))
        y_clear = gate_bb.top + 1.2
        self.box_m1(cell, cx - 0.08, gy0, cx + 0.08, y_clear + 0.16)
        self.box_m1(cell, min(cx, x_pin), y_clear, max(cx, x_pin), y_clear + 0.16)
        self.box_m1(cell, x_pin - 0.2, min(y_clear, y_pin), x_pin + 0.2,
                    max(y_clear + 0.16, y_pin))
        self.pin(cell, x_pin, max(y_pin, y_clear + 0.08), name)

    def build_dac_unit(self):
        c = self.ly.create_cell("dac_unit")
        mdb = self.pcell("pmos", {"w": "4.0u", "l": "2.0u", "ng": 1, "m": 1,
                                 "guardRingType": "none"})
        msw = self.pcell("pmos", {"w": "4.0u", "l": "0.13u", "ng": 1, "m": 1,
                                 "guardRingType": "none"})
        # Large gap so M1.b (0.18 µm) and routing stay clear
        bb0, t0 = self.place(c, mdb, 0, 0)
        bb1, t1 = self.place(c, msw, bb0.right + 12.0, 0)
        cols0 = self.m1_cols(mdb, t0)  # [left, right] S/D
        cols1 = self.m1_cols(msw, t1)
        g0 = self.poly_gate(mdb, t0)
        g1 = self.poly_gate(msw, t1)
        assert len(cols0) >= 2 and len(cols1) >= 2, (cols0, cols1)

        # Convention: left M1 = drain-ish, right = source-ish (LVS permutes S/D).
        # Topology: mdb D=xd, S=vdd; msw D=xraw, S=xd; both B=vdd.
        d_mdb, s_mdb = cols0[0], cols0[1]
        d_msw, s_msw = cols1[0], cols1[1]

        # vdd on source of mdb (top side only — keep clear of xd bottom strap)
        y_vdd = max(bb0.top, bb1.top) + 2.0
        self.box_m1(c, s_mdb.left, s_mdb.top, s_mdb.right, y_vdd + 0.5)
        self.box_m1(c, s_mdb.left - 0.1, y_vdd, s_mdb.right + 0.1, y_vdd + 0.5)
        self.pin(c, (s_mdb.left + s_mdb.right) / 2, y_vdd + 0.25, "vdd")

        # xd: d_mdb ↔ s_msw along the BOTTOM (no crossing with NW-tap M1)
        y_xd = min(bb0.bottom, bb1.bottom) - 2.0
        self.box_m1(c, d_mdb.left, y_xd, s_msw.right, y_xd + 0.5)
        self.box_m1(c, d_mdb.left, y_xd, d_mdb.right, d_mdb.bottom)
        self.box_m1(c, s_msw.left, y_xd, s_msw.right, s_msw.bottom)
        self.pin(c, (d_mdb.right + s_msw.left) / 2, y_xd + 0.25, "xd")

        # xraw: d_msw
        y_xr = bb1.top + 2.0
        self.box_m1(c, d_msw.left, d_msw.top, d_msw.right, y_xr + 0.5)
        self.pin(c, (d_msw.left + d_msw.right) / 2, y_xr + 0.25, "xraw")

        # gates (side extensions clear of S/D Cont)
        self.gate_contact(c, g0, bb0.left - 3.0, g0.top + 2.0, "pbias", side="left")
        self.gate_contact(c, g1, bb1.right + 3.0, g1.top + 2.0, "code", side="right")

        # NW tap → vdd: place tap to the RIGHT of mdb source column, M1 up to
        # y_vdd only (never crosses the bottom xd strap)
        c.shapes(self.nwell).insert(pya.DBox(bb0.left - 0.5, bb0.bottom - 0.5,
                                             bb1.right + 0.5, max(bb0.top, bb1.top) + 0.5))
        tx0 = s_mdb.right + 1.0
        ty0 = s_mdb.top + 0.5
        tx1, ty1 = tx0 + 0.6, ty0 + 0.6
        c.shapes(self.nwell).insert(pya.DBox(tx0 - 0.3, ty0 - 0.3, tx1 + 0.3, ty1 + 0.3))
        c.shapes(self.activ).insert(pya.DBox(tx0, ty0, tx1, ty1))
        c.shapes(self.nsd).insert(pya.DBox(tx0, ty0, tx1, ty1))
        c.shapes(self.cont).insert(pya.DBox(tx0 + 0.1, ty0 + 0.1, tx0 + 0.26, ty0 + 0.26))
        self.box_m1(c, tx0, ty0, tx1, y_vdd + 0.5)
        self.box_m1(c, s_mdb.right, y_vdd, tx1, y_vdd + 0.5)

        self.say(f"dac_unit bbox {c.bbox().to_dtype(self.ly.dbu)}")
        self.say(f"  cols0={cols0} cols1={cols1}")
        return c.cell_index()

    def via_stack_m1_to_m5(self, cell, x, y):
        """Via1..Via4 stack, landings 0.5 µm, vias 0.19 µm."""
        for ml in (8, 10, 30, 50, 67):
            cell.shapes(self.ly.layer(ml, 0)).insert(
                pya.DBox(x - 0.25, y - 0.25, x + 0.25, y + 0.25))
        for vl in (19, 29, 49, 66):
            cell.shapes(self.ly.layer(vl, 0)).insert(
                pya.DBox(x - 0.095, y - 0.095, x + 0.095, y + 0.095))

    def build_bank_unit(self):
        """LSB bank proof: 2×cmim + switch + 2×rhigh + 2×bypass, large gaps."""
        c = self.ly.create_cell("bank_unit")
        mim = self.pcell("cmim", {"w": "2.88u", "l": "2.88u", "C": "12.4f",
                                 "Calculate": "w&l", "guardRingType": "none"})
        # Row of MIMs at y=20 (leave room below for via+straps)
        mim_bb0, t_m0 = self.place(c, mim, 0, 20)
        mim_bb1, t_m1 = self.place(c, mim, mim_bb0.right + 8.0, 20)
        cell_m = self.ly.cell(mim)

        def m5_boxes(tr):
            out = []
            for s in cell_m.shapes(self.ly.layer(67, 0)).each():
                if s.is_box():
                    out.append(s.bbox().transformed(tr).to_dtype(self.ly.dbu))
            return out

        def tm1_boxes(tr):
            out = []
            for s in cell_m.shapes(self.ly.layer(126, 0)).each():
                if s.is_box():
                    out.append(s.bbox().transformed(tr).to_dtype(self.ly.dbu))
            return out

        m5_0, m5_1 = m5_boxes(t_m0), m5_boxes(t_m1)
        tm_0, tm_1 = tm1_boxes(t_m0), tm1_boxes(t_m1)

        # Switch below MIMs, centred
        sw = self.pcell("nmos", {"w": "10.32u", "l": "0.13u", "ng": 1, "m": 1,
                                 "guardRingType": "none"})
        bb_sw, t_sw = self.place(c, sw, 4.0, 0)
        cols_sw = self.m1_cols(sw, t_sw)
        g_sw = self.poly_gate(sw, t_sw)
        a_col, b_col = cols_sw[0], cols_sw[1]

        # Bypass FETs to the right of switch
        bp = self.pcell("nmos", {"w": "0.15u", "l": "0.13u", "ng": 1, "m": 1,
                                 "guardRingType": "none"})
        bb_bp0, t_bp0 = self.place(c, bp, bb_sw.right + 6.0, 0)
        bb_bp1, t_bp1 = self.place(c, bp, bb_sw.right + 6.0, bb_bp0.top + 4.0)
        cols_bp0 = self.m1_cols(bp, t_bp0)
        cols_bp1 = self.m1_cols(bp, t_bp1)
        g_bp0 = self.poly_gate(bp, t_bp0)
        g_bp1 = self.poly_gate(bp, t_bp1)

        # rhigh further right (proof R, not 2 MΩ)
        rh = self.pcell("rhigh", {"w": "5.0u", "l": "60.8u", "Calculate": "R",
                                 "guardRingType": "none"})
        x_r = max(mim_bb1.right, bb_bp0.right) + 6.0
        bb_r0, _ = self.place(c, rh, x_r, 0)
        bb_r1, _ = self.place(c, rh, x_r + 10.0, 0)

        # --- net a: switch left + mim0 bottom + bp0 drain + r0 top ---
        ya = -2.0
        self.box_m1(c, a_col.left, ya, a_col.right, a_col.bottom)
        if m5_0:
            mx = 0.5 * (m5_0[0].left + m5_0[0].right)
            my = 10.0  # between switch and MIM
            self.box_m1(c, min(a_col.left, mx - 0.25), ya,
                        max(a_col.right, mx + 0.25), ya + 0.4)
            self.box_m1(c, mx - 0.25, ya, mx + 0.25, my + 0.25)
            self.via_stack_m1_to_m5(c, mx, my)
            c.shapes(self.ly.layer(67, 0)).insert(
                pya.DBox(mx - 0.3, my - 0.3, mx + 0.3, m5_0[0].bottom + 0.2))
        self.box_m1(c, cols_bp0[0].left, ya, cols_bp0[0].right, cols_bp0[0].bottom)
        self.box_m1(c, a_col.left, ya, cols_bp0[0].right, ya + 0.4)

        # --- net b: switch right + mim1 bottom + bp1 drain + r1 top ---
        yb = -4.5
        self.box_m1(c, b_col.left, yb, b_col.right, b_col.bottom)
        # jog left of a-rail to avoid short
        self.box_m1(c, b_col.left - 1.5, yb, b_col.left - 1.0, ya + 0.4)
        if m5_1:
            mx = 0.5 * (m5_1[0].left + m5_1[0].right)
            my = 10.0
            self.box_m1(c, mx - 0.25, yb, mx + 0.25, my + 0.25)
            self.box_m1(c, b_col.left - 1.5, yb, mx + 0.25, yb + 0.4)
            self.via_stack_m1_to_m5(c, mx, my)
            c.shapes(self.ly.layer(67, 0)).insert(
                pya.DBox(mx - 0.3, my - 0.3, mx + 0.3, m5_1[0].bottom + 0.2))
        self.box_m1(c, cols_bp1[0].left, yb, cols_bp1[0].right, cols_bp1[0].bottom)
        self.box_m1(c, b_col.left - 1.5, yb, cols_bp1[0].right, yb + 0.4)

        # --- bb: bypass sources + rhigh bottoms + pin ---
        y_bb = -7.0
        self.box_m1(c, cols_bp0[1].left, y_bb, cols_bp0[1].right, cols_bp0[1].bottom)
        self.box_m1(c, cols_bp1[1].left, y_bb, cols_bp1[1].right, cols_bp1[1].bottom)
        self.box_m1(c, cols_bp0[1].left, y_bb, bb_r1.right, y_bb + 0.4)
        # rhigh bottoms (assume bottom terminal near bbox.bottom)
        self.box_m1(c, bb_r0.left + 1.0, y_bb, bb_r0.left + 2.0, bb_r0.bottom + 0.5)
        self.box_m1(c, bb_r1.left + 1.0, y_bb, bb_r1.left + 2.0, bb_r1.bottom + 0.5)
        # rhigh tops → a / b
        self.box_m1(c, bb_r0.left + 1.0, bb_r0.top - 0.5, bb_r0.left + 2.0, ya + 0.4)
        self.box_m1(c, bb_r0.left + 1.0, ya, a_col.right, ya + 0.4)
        self.box_m1(c, bb_r1.left + 1.0, bb_r1.top - 0.5, bb_r1.left + 2.0, yb + 0.4)
        self.box_m1(c, bb_r1.left + 1.0, yb, b_col.left - 1.0, yb + 0.4)
        self.pin(c, 0.5 * (bb_r0.left + bb_r1.right), y_bb + 0.2, "bb")

        # gates
        self.gate_contact(c, g_sw, bb_sw.left - 3.0, g_sw.top + 2.0, "g", side="left")
        self.gate_contact(c, g_bp0, bb_bp0.right + 3.0, g_bp0.top + 2.0, "vbp",
                          side="right")
        self.gate_contact(c, g_bp1, bb_bp1.right + 3.0, g_bp1.top + 2.0, "vbp2",
                          side="right")
        # strap vbp2 → vbp
        self.box_m1(c, bb_bp0.right + 2.8, g_bp0.top + 1.2,
                    bb_bp1.right + 3.2, g_bp1.top + 2.5)

        # tp / tn on TopMetal1
        tm1 = self.ly.layer(126, 0)
        tm1pin = self.ly.layer(126, 2)
        tm1txt = self.ly.layer(126, 25)
        for boxes, name in ((tm_0, "tp"), (tm_1, "tn")):
            if not boxes:
                continue
            t = boxes[0]
            x, y = 0.5 * (t.left + t.right), t.top + 1.5
            c.shapes(tm1).insert(pya.DBox(x - 0.5, t.top, x + 0.5, y + 0.4))
            c.shapes(tm1pin).insert(pya.DBox(x - 0.3, y - 0.3, x + 0.3, y + 0.3))
            c.shapes(tm1txt).insert(pya.DText(name, pya.DTrans(x, y)))

        # substrate tap for NMOS bulk=gnd (p+ Activ outside NW)
        self.psd = self.ly.layer(14, 0)  # pSD
        tx0, ty0 = bb_sw.left - 4.0, -9.0
        c.shapes(self.activ).insert(pya.DBox(tx0, ty0, tx0 + 0.6, ty0 + 0.6))
        c.shapes(self.psd).insert(pya.DBox(tx0, ty0, tx0 + 0.6, ty0 + 0.6))
        c.shapes(self.cont).insert(pya.DBox(tx0 + 0.1, ty0 + 0.1, tx0 + 0.26, ty0 + 0.26))
        self.box_m1(c, tx0, ty0, tx0 + 0.6, ty0 + 0.6)
        self.pin(c, tx0 + 0.3, ty0 - 1.5, "gnd")
        self.box_m1(c, tx0, ty0 - 1.7, tx0 + 0.6, ty0)

        self.say(f"bank_unit bbox {c.bbox().to_dtype(self.ly.dbu)} (LSB)")
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
    dac = os.path.join(OUT, "dac_unit.spice")
    # Use M-devices (not X-subckts) so netgen matches KLayout extract primitives
    open(dac, "w").write("""* P2.7.2a dac_unit [SCH]
.subckt dac_unit vdd pbias xd code xraw
Mmdb xd pbias vdd vdd sg13_lv_pmos w=4.0u l=2.0u
Mmsw xraw code xd vdd sg13_lv_pmos w=4.0u l=0.13u
.ends
""")
    bank = os.path.join(OUT, "bank_unit.spice")
    # R matches rhigh w=5u l=60.8u at Rspec=1300 → 15808 Ω
    # cmim C-mode 12.38f → extract w/l ≈ 2.87
    # switch ng=1 W=10.32
    # cap_cmim extract is 2-terminal; rhigh extract is 3-terminal (ends+bulk)
    open(bank, "w").write("""* P2.7.2a bank_unit LSB [SCH]
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
    print(f"wrote {dac}\nwrote {bank}")


def main():
    b = B()
    b.say("# P2.7.2a LVS proof cells\n")
    b.write_cell("dac_unit", b.build_dac_unit())
    b.write_cell("bank_unit", b.build_bank_unit())
    write_spice()
    open(os.path.join(OUT, "summary_proof_build.txt"), "w").write(
        "\n".join(b.log) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
