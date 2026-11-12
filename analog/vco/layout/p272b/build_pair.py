#!/usr/bin/env python3
"""P2.7.2b re-spin step 1 — cross-coupled NMOS pair + end dummies (pair cell only).

Lessons (bank_unit + first P2.7.2b attempt):
- PCell guardRingType=none; hand ptap for bulk/gnd (GR M1 shorts S/D when routed).
- Never M1-strap across the finger array at a Y that hits another terminal's drop;
  join same-net columns via side spurs + M2 (bank_unit).
- Gate Cont on poly pads above Activ (Cont 0.16 vs L=0.13); poly strap between
  fingers at Activ top (bank_unit).
- End dummies: G=S=D=gnd local only — never through tank metal.
- even M1 cols = drain (tank); odd = source (tail). Proved by pair extract (even→tail
  extracted as D). Mirror keeps D-S-D… left-to-right.
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


def um(x: float) -> int:
    return int(round(float(x) / DBU))


class Pair:
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
        self.cont = self.ly.layer(6, 0)
        self.poly = self.ly.layer(5, 0)
        self.activ = self.ly.layer(1, 0)
        self.log = []

    def say(self, s=""):
        print(s, flush=True)
        self.log.append(s)

    def pcell(self, name, params):
        decl = self.lib_ly.pcell_declaration(name)
        return self.ly.add_pcell_variant(self.lib, decl.id(), params)

    def place(self, parent, cid, x, y, mirror=False):
        if mirror:
            t = pya.Trans(pya.Trans.M90, um(x), um(y))
        else:
            t = pya.Trans(pya.Trans.R0, um(x), um(y))
        parent.insert(pya.CellInstArray(cid, t))
        return self.ly.cell(cid).bbox().transformed(t).to_dtype(self.ly.dbu), t

    def box(self, cell, layer, x0, y0, x1, y1):
        cell.shapes(layer).insert(
            pya.DBox(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    def pin_m1(self, cell, x, y, name):
        self.box(cell, self.m1, x - 0.25, y - 0.25, x + 0.25, y + 0.25)
        self.box(cell, self.m1pin, x - 0.2, y - 0.2, x + 0.2, y + 0.2)
        cell.shapes(self.m1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def m1_sd_cols(self, cid, trans):
        cell = self.ly.cell(cid)
        uniq = {}
        for s in cell.shapes(self.m1).each():
            if not s.is_box():
                continue
            b = s.bbox().transformed(trans).to_dtype(self.ly.dbu)
            if b.width() > 0.25 or b.height() < 1.0:
                continue
            cx = round((b.left + b.right) / 2, 3)
            uniq[cx] = b
        return [uniq[k] for k in sorted(uniq)]

    def poly_gates(self, cid, trans):
        cell = self.ly.cell(cid)
        boxes = []
        for s in cell.shapes(self.poly).each():
            if not s.is_box():
                continue
            b = s.bbox().transformed(trans).to_dtype(self.ly.dbu)
            if b.width() < 0.20 and b.height() > 1.0:
                boxes.append(b)
        boxes.sort(key=lambda b: b.left)
        return boxes

    def activ_top(self, cid, trans):
        cell = self.ly.cell(cid)
        top = None
        for s in cell.shapes(self.activ).each():
            if s.is_box():
                b = s.bbox().transformed(trans).to_dtype(self.ly.dbu)
                top = b.top if top is None else max(top, b.top)
        return top if top is not None else 0.0

    def gate_poly_strap(self, cell, gates, activ_top):
        """Connect all fingers in poly (bank_unit): fill above Activ across fingers."""
        g0, g1 = gates[0], gates[-1]
        self.box(cell, self.poly, g0.left, activ_top + 0.08, g1.right, activ_top + 0.55)

    def gate_m1_exit(self, cell, gates, activ_top, x_bus, y_bus):
        """Cont on pads; M1 exit outboard only — no bar over SD cols."""
        y_pad0 = max(activ_top + 0.50, max(g.top for g in gates) + 0.30)
        y_pad1 = y_pad0 + 0.50
        gx0 = min(g.left for g in gates)
        gx1 = max(g.right for g in gates)
        for g in gates:
            gx = 0.5 * (g.left + g.right)
            half = 0.5 * (g.right - g.left)
            self.box(cell, self.poly, gx - half, g.top - 0.05, gx + half, y_pad0 + 0.05)
        self.box(cell, self.poly, gx0 - 0.05, y_pad0, gx1 + 0.05, y_pad1)
        for g in gates:
            gx = 0.5 * (g.left + g.right)
            self.box(cell, self.cont, gx - 0.08, y_pad0 + 0.16, gx + 0.08, y_pad0 + 0.32)
            self.box(cell, self.m1, gx - 0.08, y_pad0 + 0.16, gx + 0.08, y_pad1 + 0.16)
        # M1 strap on pad only (above Activ; Cont clear of SD)
        self.box(cell, self.m1, gx0 - 0.08, y_pad0 + 0.16, gx1 + 0.08, y_pad1 + 0.16)
        g_exit = min(gates, key=lambda g: abs(0.5 * (g.left + g.right) - x_bus))
        gx = 0.5 * (g_exit.left + g_exit.right)
        y_rise = y_pad1 + 0.40
        self.box(cell, self.m1, gx - 0.10, y_pad1, gx + 0.10, y_rise + 0.28)
        self.box(cell, self.m1, min(x_bus, gx) - 0.14, y_rise,
                 max(x_bus, gx) + 0.14, y_rise + 0.28)
        self.box(cell, self.m1, x_bus - 0.14, min(y_rise, y_bus),
                 x_bus + 0.14, max(y_rise + 0.28, y_bus))
        return y_pad1

    def build(self):
        top = self.ly.create_cell("vco_xc_pair")
        nmos = self.pcell("nmos", {
            "w": "32.0u", "l": "0.13u", "ng": 8, "m": 1,
            "guardRingType": "none",
        })
        # Dummy finger matches main finger W/ng = 4 µm (W=0.15 was too short for M1 col detect)
        dum = self.pcell("nmos", {
            "w": "4.0u", "l": "0.13u", "ng": 1, "m": 1,
            "guardRingType": "none",
        })
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })
        ptap = self.pcell("ptap1", {"w": "0.78u", "l": "0.78u"})

        loc = self.ly.cell(nmos).bbox().to_dtype(self.ly.dbu)
        dloc = self.ly.cell(dum).bbox().to_dtype(self.ly.dbu)
        gap = 8.0
        y0 = 0.0
        # M1 R0 left of origin; M2 M90 right
        x_m1 = -gap / 2 - loc.right
        x_m2 = gap / 2 + loc.right
        bb1, t1 = self.place(top, nmos, x_m1, y0, mirror=False)
        bb2, t2 = self.place(top, nmos, x_m2, y0, mirror=True)
        self.say(f"M1 {bb1}; M2 {bb2} [SCH W=32 ng=8]")

        # Tank spur X between devices and dummies; dummies further outboard
        x_tp = bb1.left - 6.0
        x_tn = bb2.right + 6.0
        x_dL = x_tp - 5.0 - dloc.right
        x_dR = x_tn + 5.0 - dloc.left
        bb_dL, t_dL = self.place(top, dum, x_dL, y0)
        bb_dR, t_dR = self.place(top, dum, x_dR, y0)
        self.say(f"dummy L {bb_dL}; dummy R {bb_dR}; x_tp={x_tp:.2f} x_tn={x_tn:.2f}")

        cols1 = self.m1_sd_cols(nmos, t1)
        cols2 = self.m1_sd_cols(nmos, t2)
        g1 = self.poly_gates(nmos, t1)
        g2 = self.poly_gates(nmos, t2)
        at1 = self.activ_top(nmos, t1)
        at2 = self.activ_top(nmos, t2)
        assert len(cols1) == 9 and len(cols2) == 9, (len(cols1), len(cols2))
        assert len(g1) == 8 and len(g2) == 8, (len(g1), len(g2))

        # even = drain (tank), odd = source (tail) — pair extract: even→tail was D
        drn1 = [cols1[i] for i in range(0, 9, 2)]
        src1 = [cols1[i] for i in range(1, 9, 2)]
        drn2 = [cols2[i] for i in range(0, 9, 2)]
        src2 = [cols2[i] for i in range(1, 9, 2)]
        self.say(f"S/D order: even=D odd=S; nS={len(src1)} nD={len(drn1)} per device [LVS]")

        # --- Y rails (south of Activ; separated ≥ M1.b / M2.b) ---
        y_tail = min(bb1.bottom, bb2.bottom) - 3.0
        y_dr = y_tail - 4.0          # drain M2 join
        y_xc_tp = y_dr - 5.0
        y_xc_tn = y_xc_tp - 2.0      # ≥ M2.b 0.21
        y_gnd = y_xc_tn - 4.0
        y_port = y_gnd - 4.0         # tp/tn stubs south of gnd (never share Y with gnd)

        # Gate exits between device and tank spur (not through dummy zone)
        x_g1 = 0.5 * (bb1.left + x_tp)   # M1 gates → tn
        x_g2 = 0.5 * (bb2.right + x_tn)  # M2 gates → tp

        # --- Sources → tail: M1 drop per col + 1×1 via on col; M2 bus (no M1 across) ---
        for c in src1 + src2:
            self.box(top, self.m1, c.left, y_tail, c.right, c.bottom)
            # via centred on col (1×1 landing stays on this M1 only)
            self.place(top, vs12, 0.5 * (c.left + c.right) - 0.05, y_tail)
        self.box(top, self.m2,
                 src1[0].left - 0.3, y_tail - 0.15,
                 src2[-1].right + 0.3, y_tail + 0.55)
        # pin via centre → M1 stub south of M2 bus
        self.place(top, vs12, -0.05, y_tail - 1.5)
        self.box(top, self.m2, -0.25, y_tail - 1.5, 0.25, y_tail + 0.55)
        self.box(top, self.m1, -0.25, y_tail - 2.5, 0.25, y_tail - 1.3)
        self.pin_m1(top, 0.0, y_tail - 2.3, "tail")

        # --- Drains → tank: M1 drop to y_dr only on drain cols; via+M2 outboard ---
        # Source verticals also cross y_dr — never put M1 horizontal at y_dr.
        for c in drn1:
            self.box(top, self.m1, c.left, y_dr, c.right, c.bottom)
            self.place(top, vs12, 0.5 * (c.left + c.right) - 0.05, y_dr)
        self.box(top, self.m2,
                 x_tp - 0.20, y_dr - 0.15,
                 max(c.right for c in drn1) + 0.2, y_dr + 0.55)
        self.place(top, vs12, x_tp - 0.05, y_dr)
        self.box(top, self.m1, x_tp - 0.20, y_dr, x_tp + 0.20, y_dr + 0.40)

        for c in drn2:
            self.box(top, self.m1, c.left, y_dr, c.right, c.bottom)
            self.place(top, vs12, 0.5 * (c.left + c.right) - 0.05, y_dr)
        self.box(top, self.m2,
                 min(c.left for c in drn2) - 0.2, y_dr - 0.15,
                 x_tn + 0.20, y_dr + 0.55)
        self.place(top, vs12, x_tn - 0.05, y_dr)
        self.box(top, self.m1, x_tn - 0.20, y_dr, x_tn + 0.20, y_dr + 0.40)

        # --- Gates ---
        self.gate_poly_strap(top, g1, at1)
        self.gate_poly_strap(top, g2, at2)
        y_g_exit = max(at1, at2) + 4.0
        self.gate_m1_exit(top, g1, at1, x_g1, y_g_exit)
        self.gate_m1_exit(top, g2, at2, x_g2, y_g_exit)

        # --- Cross-couple on M2 south of drains ---
        # tp = M1_drain + M2_gate; tn = M2_drain + M1_gate
        self.box(top, self.m1, x_tp - 0.14, y_xc_tp, x_tp + 0.14, y_dr + 0.40)
        self.box(top, self.m1, x_tn - 0.14, y_xc_tn, x_tn + 0.14, y_dr + 0.40)
        self.box(top, self.m1, x_g1 - 0.14, y_xc_tn, x_g1 + 0.14, y_g_exit + 0.40)
        self.box(top, self.m1, x_g2 - 0.14, y_xc_tp, x_g2 + 0.14, y_g_exit + 0.40)
        self.place(top, vs12, x_tp - 0.05, y_xc_tp)
        self.place(top, vs12, x_tn - 0.05, y_xc_tn)
        self.place(top, vs12, x_g1 - 0.05, y_xc_tn)
        self.place(top, vs12, x_g2 - 0.05, y_xc_tp)
        # cover both via landings (x_g±0.20 was short of the far via by ~0.15 µm)
        self.box(top, self.m2,
                 min(x_g2, x_tp) - 0.30, y_xc_tp,
                 max(x_g2, x_tp) + 0.30, y_xc_tp + 0.40)
        self.box(top, self.m2,
                 min(x_g1, x_tn) - 0.30, y_xc_tn,
                 max(x_g1, x_tn) + 0.30, y_xc_tn + 0.40)
        # port stubs: M2 verticals at tank X (gnd stays outboard — no shared metal)
        self.place(top, vs12, x_tp - 0.05, y_port)
        self.place(top, vs12, x_tn - 0.05, y_port)
        self.box(top, self.m2, x_tp - 0.20, y_port, x_tp + 0.20, y_xc_tp + 0.40)
        self.box(top, self.m2, x_tn - 0.20, y_port, x_tn + 0.20, y_xc_tn + 0.40)
        self.box(top, self.m1, x_tp - 0.25, y_port - 0.5, x_tp + 0.25, y_port + 0.40)
        self.box(top, self.m1, x_tn - 0.25, y_port - 0.5, x_tn + 0.25, y_port + 0.40)
        self.pin_m1(top, x_tp, y_port - 0.3, "tp")
        self.pin_m1(top, x_tn, y_port - 0.3, "tn")

        # --- Dummies + gnd outboard of tank X ---
        x_gL = min(bb_dL.left, x_tp) - 4.0
        x_gR = max(bb_dR.right, x_tn) + 4.0
        for bb_d, t_d, x_gnd_d in ((bb_dL, t_dL, x_gL), (bb_dR, t_dR, x_gR)):
            dcols = self.m1_sd_cols(dum, t_d)
            dg = self.poly_gates(dum, t_d)
            at_d = self.activ_top(dum, t_d)
            y_dg = at_d + 2.0
            for c in dcols:
                self.box(top, self.m1, c.left, y_gnd + 1.0, c.right, c.bottom)
            if dcols:
                self.box(top, self.m1,
                         min(min(c.left for c in dcols), x_gnd_d), y_gnd + 1.0,
                         max(max(c.right for c in dcols), x_gnd_d), y_gnd + 1.35)
            if dg:
                self.gate_poly_strap(top, dg, at_d)
                self.gate_m1_exit(top, dg, at_d, x_gnd_d, y_dg)
                self.box(top, self.m1, x_gnd_d - 0.14, y_gnd + 1.0,
                         x_gnd_d + 0.14, y_dg + 0.40)
            self.box(top, self.m1, x_gnd_d - 0.20, y_gnd, x_gnd_d + 0.20, y_gnd + 1.40)

        # ptaps on outboard gnd rails only
        for x, y in ((x_gL - 0.4, bb_dL.bottom - 1.5), (x_gR - 0.4, bb_dR.bottom - 1.5),
                     (x_gL - 0.4, y_gnd), (x_gR - 0.4, y_gnd)):
            self.place(top, ptap, x, y)
            self.box(top, self.m1, x, y, x + 0.78, y + 0.78)
        self.box(top, self.m1, x_gL - 0.4, y_gnd, x_gL + 0.4, y_gnd + 0.50)
        self.box(top, self.m1, x_gR - 0.4, y_gnd, x_gR + 0.4, y_gnd + 0.50)
        # join left/right gnd south of ports (past y_port) so M2 never hits tank M2
        y_gnd_join = y_port - 3.0
        self.box(top, self.m1, x_gL - 0.20, y_gnd_join, x_gL + 0.20, y_gnd + 0.50)
        self.box(top, self.m1, x_gR - 0.20, y_gnd_join, x_gR + 0.20, y_gnd + 0.50)
        self.place(top, vs12, x_gL - 0.05, y_gnd_join)
        self.place(top, vs12, x_gR - 0.05, y_gnd_join)
        self.box(top, self.m2, x_gL - 0.20, y_gnd_join - 0.15,
                 x_gR + 0.20, y_gnd_join + 0.55)
        self.place(top, vs12, -0.05, y_gnd_join)
        self.box(top, self.m1, -0.25, y_gnd_join - 2.0, 0.25, y_gnd_join + 0.40)
        self.pin_m1(top, 0.0, y_gnd_join - 1.8, "gnd")

        bb = top.bbox().to_dtype(self.ly.dbu)
        area = (bb.right - bb.left) * (bb.top - bb.bottom) * 1e-6
        self.say(f"pair bbox {bb}; area {area:.4f} mm² [GDS]")

        gds = os.path.join(OUT, "vco_xc_pair.gds")
        self.ly.write(gds)
        with open(gds, "rb") as f, gzip.open(gds + ".gz", "wb") as z:
            shutil.copyfileobj(f, z)
        spice = os.path.join(OUT, "vco_xc_pair.spice")
        # M-prefix (not X): IHP KLayout LVS spice reader; ng omitted like bank_unit
        # (extract has no ng; W total matches). Dummies combine → W=8 [LVS].
        open(spice, "w").write("""* P2.7.2b pair cell — XC NMOS + end dummies
* Schematic: vco_core M1/M2; dummies G=S=D=gnd (layout-only, finger W=4×2)
.subckt vco_xc_pair tp tn tail gnd
Mm1 tp tn tail gnd sg13_lv_nmos w=32u l=0.13u
Mm2 tn tp tail gnd sg13_lv_nmos w=32u l=0.13u
Mdum gnd gnd gnd gnd sg13_lv_nmos w=8u l=0.13u
.ends
.end
""")
        open(os.path.join(OUT, "build_pair_log.txt"), "w").write("\n".join(self.log) + "\n")
        self.say(f"wrote {gds}")
        return 0


if __name__ == "__main__":
    sys.exit(Pair().build())
