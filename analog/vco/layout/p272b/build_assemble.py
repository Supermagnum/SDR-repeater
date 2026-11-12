#!/usr/bin/env python3
"""P2.7.2b re-spin — assemble core+tank bottom-up on LVS-clean vco_xc_pair.

Stages (DRC+LVS after each; --stage N):
  a) pair + tapped L2n0 (via-fixed) + centre-tap supply
  b) + fixed tank capacitance (2× rfcmim 16u + rfx)
  c) + guard ring / gnd·tail rail reinforcement
  d) + port stubs (bank / var / detector / LO / tail·DAC)

S/D: even M1 cols = drain (tank), odd = source (tail) [pair LVS].
Inductor spiral is on non-LVS metal (layer 133); TM1 pads at LA/LB/CT for routing.
"""
from __future__ import annotations

import argparse
import gzip
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
IND_GDS = os.path.join(REPO, "sim/em/sg13-octagon-l2n0/tapped/L_2n0_tapped.gds")
PAIR_GDS = os.path.join(OUT, "vco_xc_pair.gds")
os.makedirs(OUT, exist_ok=True)

sys.path[:0] = [
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python",
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python/pycell4klayout-api/source/python",
]

import pya  # noqa: E402
import sg13g2_pycell_lib  # noqa: E402, F401

DBU = 0.001
KEEP_OUT = 30.0
# Open PDK process_spec (strings search): no EM current table [DS miss].
EM_TM1 = 5.0  # mA/µm [HAND, Al BEOL ~130 nm class]
EM_M5 = 1.0
I_TAIL = 4.0  # mA [DS D12]


def um(x: float) -> int:
    return int(round(float(x) / DBU))


class Asm:
    def __init__(self, stage: str):
        self.stage = stage
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
        self.tm1pin = self.ly.layer(126, 2)
        self.tm1txt = self.ly.layer(126, 25)
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

    def pin_tm1(self, cell, x, y, name):
        self.box(cell, self.tm1, x - 0.5, y - 0.5, x + 0.5, y + 0.5)
        self.box(cell, self.tm1pin, x - 0.4, y - 0.4, x + 0.4, y + 0.4)
        cell.shapes(self.tm1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def pin_m1(self, cell, x, y, name):
        self.box(cell, self.m1, x - 0.25, y - 0.25, x + 0.25, y + 0.25)
        self.box(cell, self.m1pin, x - 0.2, y - 0.2, x + 0.2, y + 0.2)
        cell.shapes(self.m1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def build(self):
        if not os.path.exists(PAIR_GDS):
            raise SystemExit(f"missing pair GDS {PAIR_GDS}; run build_pair.py first")
        if not os.path.exists(IND_GDS):
            raise SystemExit(f"missing inductor {IND_GDS}")

        top = self.ly.create_cell("vco_core_tank")
        # --- inductor: full EM geometry in cell l2n0_em (DRC/fab); LVS uses
        # pin-only l2n0 (spiral+via layers 133/134 short LA–CT–LB in LVS stack).
        ind_ly = pya.Layout()
        ind_ly.read(IND_GDS)
        ind_em = self.ly.create_cell("l2n0_em")
        ind_em.copy_tree(ind_ly.top_cell())
        ind = self.ly.create_cell("l2n0")
        # pin-only pads at LA/LB/CT (no texts — top cell owns tp/tn/ct names)
        for x, y in ((-27.5, 3.0), (27.5, 3.0), (0.0, 3.0)):
            self.box(ind, self.tm1, x - 1.5, y - 1.5, x + 1.5, y + 1.5)
        # place EM under pin cell (same origin); LVS GDS will drop l2n0_em
        ind_bb, _ = self.place(top, ind_em.cell_index(), 0, 0)
        self.place(top, ind.cell_index(), 0, 0)
        self.say(f"inductor bbox {ind_bb} [EM]; LVS black-box l2n0 pin-only")
        self.say("NOTE: EM TM1 pads overlap LVS pads → fab GDS still DC-shorts "
                 "through spiral; LVS run uses stripped GDS (no l2n0_em)")
        y_keep = ind_bb.bottom - KEEP_OUT
        la_x, lb_x, port_y = -27.5, 27.5, 3.0
        self.say(f"keep-out Activ y ≤ {y_keep:.2f} µm [HAND]")

        # --- pair cell ---
        pair_ly = pya.Layout()
        pair_ly.read(PAIR_GDS)
        pair = self.ly.create_cell("vco_xc_pair")
        pair.copy_tree(pair_ly.top_cell())
        pbb0 = pair.bbox().to_dtype(self.ly.dbu)
        # place so pair top is below keep-out
        y_pair = y_keep - pbb0.top - 2.0
        bb_p, _ = self.place(top, pair.cell_index(), 0, y_pair)
        self.say(f"pair at y={y_pair:.2f} bbox {bb_p}")

        # Pair port locations (from build_pair): tp/tn M1 south, tail/gnd centre
        # Re-read pair pin texts in placed coords
        pins = {}
        for s in pair.shapes(self.m1txt).each():
            if s.is_text():
                d = s.text_trans.disp.to_dtype(self.ly.dbu)
                pins[s.text_string] = (d.x, d.y + y_pair)
        self.say(f"pair pins {pins}")
        x_tp, y_tp = pins["tp"]
        x_tn, y_tn = pins["tn"]
        x_tail, y_tail = pins["tail"]
        x_gnd, y_gnd = pins["gnd"]

        vs15 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal5",
            "vn_columns": 1, "vn_rows": 1,
        })
        vs5t = self.pcell("via_stack", {
            "b_layer": "Metal5", "t_layer": "TopMetal1",
            "vn_columns": 2, "vn_rows": 2,
        })
        vs12 = self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })

        # --- stage a: tank TM1 to LA/LB + CT supply ---
        w_tank = 4.0
        w_ct = 8.0
        y_via = y_keep - 4.0
        # M1 → M5 → TM1 at tank spurs
        for x in (x_tp, x_tn):
            self.box(top, self.m1, x - 0.25, y_tp if x == x_tp else y_tn, x + 0.25, y_via + 0.4)
            self.place(top, vs15, x - 0.05, y_via)
            self.box(top, self.m5, x - 1.2, y_via - 0.5, x + 1.2, y_via + 1.0)
            self.place(top, vs5t, x - 0.1, y_via)
            self.box(top, self.tm1, x - w_tank / 2, y_via - 0.5, x + w_tank / 2, port_y + 2.0)
        # horizontal to LA/LB
        self.box(top, self.tm1, la_x - w_tank / 2, port_y,
                 x_tp + w_tank / 2, port_y + w_tank)
        self.box(top, self.tm1, x_tn - w_tank / 2, port_y,
                 lb_x + w_tank / 2, port_y + w_tank)
        # CT / vdd strap (wide); south of coil only for now
        y_ct_south = y_via + 2.0
        self.box(top, self.tm1, -w_ct / 2, y_ct_south, w_ct / 2, port_y + 2.0)
        # ct ≡ vdd (centre-tap supply); one net, both labels
        self.pin_tm1(top, 0.0, y_ct_south + 1.0, "ct")
        self.pin_tm1(top, 0.0, y_ct_south + 4.0, "vdd")
        # expose tp/tn at tank (same nets as l2n0 p/n pads)
        self.pin_tm1(top, x_tp, y_via - 2.0, "tp")
        self.pin_tm1(top, x_tn, y_via - 2.0, "tn")
        # rename l2n0 pad texts would fight hierarchy; ignore_top_ports covers p|tp
        self.box(top, self.tm1, x_tp - w_tank / 2, y_via - 2.5, x_tp + w_tank / 2, y_via)
        self.box(top, self.tm1, x_tn - w_tank / 2, y_via - 2.5, x_tn + w_tank / 2, y_via)
        # promote tail/gnd pins to top
        self.pin_m1(top, x_tail, y_tail - 1.0, "tail")
        self.box(top, self.m1, x_tail - 0.25, y_tail - 1.0, x_tail + 0.25, y_tail + 0.3)
        self.pin_m1(top, x_gnd, y_gnd - 1.0, "gnd")
        self.box(top, self.m1, x_gnd - 0.25, y_gnd - 1.0, x_gnd + 0.25, y_gnd + 0.3)

        j_tank = I_TAIL / w_tank
        j_ct = I_TAIL / w_ct
        self.say(f"EM dens [HAND]: tank TM1 {w_tank} µm → J={j_tank:.2f} mA/µm "
                 f"(limit {EM_TM1}); CT {w_ct} µm → J={j_ct:.2f} (limit {EM_TM1})")
        self.say("EM source: SG13G2_os_process_spec.pdf strings — no mA/µm table [DS miss]")

        if self.stage >= "b":
            # --- fixed MIMs: keep rfcmim (schematic Xxf1/Xxf2) ---
            # PCell has solid M1 shield = TIE/gnd over full bbox (−5.6..21.6).
            # Any M5→M1 via on MINUS shorts fx to TIE. Route fx on M2, drop to
            # M1 only outside the shield [probe LVS PASS].
            mim = self.pcell("rfcmim", {"w": "16.0u", "l": "16.0u", "wfeed": "5.0u"})
            mloc = self.ly.cell(mim).bbox().to_dtype(self.ly.dbu)
            vs52 = self.pcell("via_stack", {
                "b_layer": "Metal2", "t_layer": "Metal5",
                "vn_columns": 2, "vn_rows": 2,
            })
            vs12b = self.pcell("via_stack", {
                "b_layer": "Metal1", "t_layer": "Metal2",
                "vn_columns": 2, "vn_rows": 2,
            })
            y_mim = min(y_tp, y_tn) - (mloc.top - mloc.bottom) - 14.0
            # origin so PLUS feed (local x≈−5.6) / MINUS (local x≈19.6) clear of CT
            x_mim_l = x_tp - 25.0 - mloc.right
            x_mim_r = x_tn + 25.0 - mloc.left
            bb_xf1, _ = self.place(top, mim, x_mim_l, y_mim)
            bb_xf2, _ = self.place(top, mim, x_mim_r, y_mim)
            self.say(f"MIM L {bb_xf1}; MIM R {bb_xf2}")
            self.say("rfcmim M1 shield = TIE; fx on M2, M1 drop outside shield [PDK]")
            # PLUS = TM1 left feed (local ≈ (−4.6, 8) from origin) → tank
            y_plus = y_mim + 8.0
            for bb, x_orig, x_tank in (
                (bb_xf1, x_mim_l, x_tp),
                (bb_xf2, x_mim_r, x_tn),
            ):
                x_plus = x_orig - 4.6
                self.box(top, self.tm1, x_plus - 1.0, y_plus - 2.5,
                         x_plus + 1.0, y_plus + 2.5)
                self.box(top, self.tm1, min(x_plus, x_tank) - w_tank / 2, y_plus - 0.85,
                         max(x_plus, x_tank) + w_tank / 2, y_plus + 0.85)
                self.box(top, self.tm1, x_tank - w_tank / 2, y_plus,
                         x_tank + w_tank / 2, y_via)
            # MINUS = M5 right feed (local ≈ (20.6, 8)) → M2 → fx (never M1 on shield)
            y_m2 = y_mim + 8.0
            minus_pts = []
            for x_orig in (x_mim_l, x_mim_r):
                x_minus = x_orig + 20.6
                self.box(top, self.m5, x_minus - 1.0, y_m2 - 1.0,
                         x_minus + 1.0, y_m2 + 1.0)
                self.place(top, vs52, x_minus - 0.05, y_m2 - 0.05)
                self.box(top, self.m2, x_minus - 0.35, y_m2 - 0.35,
                         x_minus + 0.35, y_m2 + 0.35)
                minus_pts.append(x_minus)
            self.box(top, self.m2, min(minus_pts) - 0.35, y_m2 - 0.35,
                     max(minus_pts) + 0.35, y_m2 + 0.35)
            x_fx = 0.0  # gap between MIM shields
            y_m1_drop = min(bb_xf1.bottom, bb_xf2.bottom) - 3.0
            self.box(top, self.m2, x_fx - 0.35, y_m1_drop - 0.35,
                     x_fx + 0.35, y_m2 + 0.35)
            self.place(top, vs12b, x_fx - 0.05, y_m1_drop - 0.05)
            self.box(top, self.m1, x_fx - 0.35, y_m1_drop - 0.35,
                     x_fx + 0.35, y_m1_drop + 0.35)
            # TIE: outboard straps from shield south edge → gnd (no centre spine)
            for bb, side in ((bb_xf1, -1), (bb_xf2, +1)):
                x_drop = bb.left - 3.0 if side < 0 else bb.right + 3.0
                self.box(top, self.m1, bb.left + 0.5, bb.bottom,
                         bb.right - 0.5, bb.bottom + 2.0)
                self.box(top, self.m1, min(x_drop, bb.left + 0.5), bb.bottom,
                         max(x_drop, bb.right - 0.5), bb.bottom + 0.40)
                self.box(top, self.m1, x_drop - 0.25, y_gnd - 2.5,
                         x_drop + 0.25, bb.bottom + 0.40)
            # gnd join only under the pair (north of MIMs), not across fx
            self.box(top, self.m1, bb_xf1.left - 3.2, y_gnd - 2.5,
                     x_gnd + 0.25, y_gnd - 2.0)
            self.box(top, self.m1, x_gnd - 0.25, y_gnd - 2.5,
                     bb_xf2.right + 3.2, y_gnd - 2.0)
            self.box(top, self.m1, x_gnd - 0.25, y_gnd - 2.5, x_gnd + 0.25, y_gnd - 0.5)
            # rhigh: place east of centre so gnd riser never shares X with fx drop
            rh = self.pcell("rhigh", {
                "w": "2.0u", "l": "15.2u", "Calculate": "R", "guardRingType": "none",
            })
            ptap_b = self.pcell("ptap1", {"w": "0.78u", "l": "0.78u"})
            x_r = 4.0
            y_r = y_m1_drop - 20.0
            bb_r, _ = self.place(top, rh, x_r, y_r)
            # fx M1: drop → rhigh top only (stay south of shields, east to rhigh)
            self.box(top, self.m1, x_fx - 0.35, y_m1_drop - 0.35,
                     x_fx + 0.35, y_m1_drop + 0.35)
            self.box(top, self.m1, x_fx - 0.35, bb_r.top - 0.2,
                     x_fx + 0.35, y_m1_drop + 0.35)
            self.box(top, self.m1, x_fx - 0.35, bb_r.top - 0.2,
                     bb_r.right - 0.1, bb_r.top + 0.35)
            self.box(top, self.m1, bb_r.left + 0.1, bb_r.top - 0.5,
                     bb_r.right - 0.1, bb_r.top + 0.35)
            # gnd end: bottom pin only, then SOUTH, then west to outboard gnd drop
            self.box(top, self.m1, bb_r.left + 0.1, y_r - 0.5,
                     bb_r.right - 0.1, y_r + 0.1)
            y_gnd_south = min(bb_r.bottom, y_r) - 2.0
            self.box(top, self.m1, bb_r.left + 0.1, y_gnd_south,
                     bb_r.right - 0.1, y_r + 0.1)
            # outboard east gnd drop already at bb_xf2.right+3; join under rhigh
            x_gnd_east = bb_xf2.right + 3.0
            self.box(top, self.m1, bb_r.left + 0.1, y_gnd_south,
                     x_gnd_east + 0.25, y_gnd_south + 0.40)
            self.box(top, self.m1, x_gnd_east - 0.25, y_gnd_south,
                     x_gnd_east + 0.25, y_gnd - 2.0)
            self.place(top, ptap_b, bb_r.right + 1.0, y_r - 1.5)
            self.box(top, self.m1, bb_r.right + 1.0, y_gnd_south,
                     bb_r.right + 1.78, y_r - 0.72)
            # fx is internal (no top-level pin — avoids netgen pin mismatch)
            self.say(f"rhigh {bb_r}; fx M2 bus + M1 drop @ ({x_fx},{y_m1_drop})")

        if self.stage >= "c":
            # reinforce guard: extra ptaps around pair, widen gnd/tail rails
            ptap = self.pcell("ptap1", {"w": "0.78u", "l": "0.78u"})
            for x, y in (
                (bb_p.left - 8.0, bb_p.top + 2.0),
                (bb_p.right + 7.0, bb_p.top + 2.0),
                (bb_p.left - 8.0, bb_p.bottom - 2.0),
                (bb_p.right + 7.0, bb_p.bottom - 2.0),
            ):
                self.place(top, ptap, x, y)
                self.box(top, self.m1, x, y, x + 0.78, y + 0.78)
            # gnd ring strap (M2) around pair — keep clear of fx M2 bus (y_m2 region)
            self.box(top, self.m1, bb_p.left - 8.0, bb_p.bottom - 2.0,
                     bb_p.left - 7.2, bb_p.top + 2.8)
            self.box(top, self.m1, bb_p.right + 7.0, bb_p.bottom - 2.0,
                     bb_p.right + 7.8, bb_p.top + 2.8)
            self.place(top, vs12, bb_p.left - 8.0, bb_p.bottom - 2.0)
            self.place(top, vs12, bb_p.right + 7.0, bb_p.bottom - 2.0)
            # M2 gnd strap only under the pair (north of MIMs), not across fx bus
            self.box(top, self.m2, bb_p.left - 8.2, bb_p.bottom - 2.2,
                     bb_p.right + 8.0, bb_p.bottom - 1.5)
            self.box(top, self.m1, x_tail - 1.0, y_tail - 3.0, x_tail + 1.0, y_tail + 0.3)
            self.say("guard ptaps + gnd M2 strap (pair-only) + wide tail [stage c]")

        if self.stage >= "d":
            # Landing stubs for bank / var / detector / LO / DAC — metal only.
            # No pin/text on pin layers: labels would merge into LVS port names
            # (tp|tp_bank|…) and break netgen pin matching. TEXT.drawing only.
            text = self.ly.layer(63, 0)
            y_stub = min(y_tp, y_tn) - 8.0
            stubs = [
                (x_tp - 10.0, y_stub, "tp_bank"),
                (x_tn + 10.0, y_stub, "tn_bank"),
                (x_tp - 10.0, y_stub - 3.0, "tp_var"),
                (x_tn + 10.0, y_stub - 3.0, "tn_var"),
                (x_tp - 10.0, y_stub - 6.0, "tp_det"),
                (x_tn + 10.0, y_stub - 6.0, "tn_det"),
                (x_tp - 10.0, y_stub - 9.0, "tp_lo"),
                (x_tn + 10.0, y_stub - 9.0, "tn_lo"),
            ]
            for x, y, name in stubs:
                x_tank = x_tp if x < 0 else x_tn
                self.box(top, self.tm1, min(x, x_tank) - 0.85, y,
                         max(x, x_tank) + 0.85, y + 1.70)
                top.shapes(text).insert(pya.DText(name, pya.DTrans(x, y + 0.85)))
            self.box(top, self.m1, x_tail - 0.5, y_tail - 6.0, x_tail + 0.5, y_tail)
            top.shapes(text).insert(pya.DText("tail_dac", pya.DTrans(x_tail, y_tail - 5.5)))
            self.say("port stubs bank/var/det/LO/tail_dac metal-only [stage d]")

        bb = top.bbox().to_dtype(self.ly.dbu)
        area = bb.width() * bb.height() * 1e-6
        self.say(f"vco_core_tank stage={self.stage} bbox {bb}")
        self.say(f"area {area:.4f} mm² = {100*area/0.30:.1f}% of ≤0.30 mm² [GDS]")

        gds = os.path.join(OUT, "vco_core_tank.gds")
        self.ly.write(gds)
        with open(gds, "rb") as fi, gzip.open(gds + ".gz", "wb") as fo:
            shutil.copyfileobj(fi, fo)

        # LVS variant: delete l2n0_em instances so spiral cannot short p/n/ct
        ly_lvs = pya.Layout()
        ly_lvs.read(gds)
        tc = ly_lvs.top_cell()
        em_idx = None
        for c in ly_lvs.each_cell():
            if c.name == "l2n0_em":
                em_idx = c.cell_index()
        if em_idx is not None:
            to_del = [i for i in tc.each_inst() if i.cell_index == em_idx]
            for i in to_del:
                i.delete()
            # drop orphan so GDS has a single top cell
            ly_lvs.delete_cell(em_idx)
        gds_lvs = os.path.join(OUT, "vco_core_tank_lvs.gds")
        ly_lvs.write(gds_lvs)
        self.say(f"wrote LVS GDS {gds_lvs} (l2n0_em removed)")

        sp = os.path.join(OUT, "vco_core_tank.spice")
        open(sp, "w").write(self.spice())
        open(os.path.join(OUT, f"build_assemble_{self.stage}_log.txt"), "w").write(
            "\n".join(self.log) + "\n")
        self.say(f"wrote {gds} stage={self.stage}")
        return gds, area

    def spice(self):
        # M-prefix; inductor is layout pin-only black-box (no xl — flat LVS).
        # ct ≡ vdd (same metal); one port name "ct" (vdd text also on that net).
        lines = [
            f"* P2.7.2b re-spin stage {self.stage} — vco_core_tank",
            "* Inductor: LVS GDS pin-only l2n0; fab GDS adds l2n0_em spiral.",
            ".subckt vco_core_tank tp tn tail ct gnd",
            "Mm1 tp tn tail gnd sg13_lv_nmos w=32u l=0.13u",
            "Mm2 tn tp tail gnd sg13_lv_nmos w=32u l=0.13u",
            "Mdum gnd gnd gnd gnd sg13_lv_nmos w=8u l=0.13u",
        ]
        if self.stage >= "b":
            # LVS device name is rfcmim (extract); sch lvs_model=rfcmim [SCH]
            lines += [
                "Cxf1 tp fx gnd rfcmim w=16u l=16u wfeed=5u m=1",
                "Cxf2 tn fx gnd rfcmim w=16u l=16u wfeed=5u m=1",
                "Rrfx fx gnd gnd rhigh w=2u l=15.2u m=1",
            ]
        lines += [".ends", ".end", ""]
        return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="a", choices=list("abcd"))
    args = ap.parse_args()
    Asm(args.stage).build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
