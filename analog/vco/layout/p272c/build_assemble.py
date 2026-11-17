#!/usr/bin/env python3
"""P2.7.2c — assemble vco_top from accepted block GDS + inter-block routing.

Follows spec/p27-layout-notes.md P2.7.2c routing plan (2026-11-17).
Net groups (--nets): place | power | ct | tail | tn_tp | vt | controls | all
DRC + both LVS after each group (full unique LVS = sign-off).
"""
from __future__ import annotations

import gzip
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
ROOT = os.path.abspath(os.path.join(HERE, ".."))
os.makedirs(OUT, exist_ok=True)

sys.path[:0] = [
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python",
    "/foss/pdks/ihp-sg13g2/libs.tech/klayout/python/pycell4klayout-api/source/python",
]
import pya  # noqa: E402
import sg13g2_pycell_lib  # noqa: E402

DBU = 0.001
GDS = {
    "vco_core_tank": os.path.join(ROOT, "p272b", "out", "vco_core_tank.gds"),
    "vco_bank": os.path.join(ROOT, "p272b_bank", "out", "vco_bank.gds"),
    "tail_block": os.path.join(ROOT, "p272b_tail", "out", "tail_block.gds"),
    "vco_var": os.path.join(ROOT, "p272b_var", "out", "vco_var.gds"),
    "ampcal_det": os.path.join(ROOT, "p272b_det", "out", "ampcal_det.gds"),
}
SPICE_LEAF = {
    "vco_core_tank": os.path.join(ROOT, "p272b", "out", "vco_core_tank.spice"),
    "vco_bank": os.path.join(ROOT, "p272b_bank", "out", "vco_bank.spice"),
    "tail_block": os.path.join(ROOT, "p272b_tail", "out", "tail_block.spice"),
    "vco_var": os.path.join(ROOT, "p272b_var", "out", "vco_var.spice"),
    "ampcal_det": os.path.join(ROOT, "p272b_det", "out", "ampcal_det.spice"),
}
# Top ports exported (sch vco_top; en/vthn included) [SCH]
TOP_PORTS = [
    "tp", "tn", "ct", "vt", "vdd", "gnd", "vbp", "vbp_tail", "cmp", "tail",
    "hold", "rep", "en", "vthn",
    "g0", "g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "g10", "g11",
    "code0", "code1", "code2", "code3", "code4",
]
KEEP_PINS = {
    "vco_core_tank": {"tp", "tn", "tail", "ct", "gnd"},
    "vco_bank": {"tp", "tn", "vbp", "gnd"} | {f"g{i}" for i in range(12)},
    "tail_block": {
        "tail", "vdd", "gnd", "vbp_tail", "code0", "code1", "code2", "code3",
        "code4",
    },
    "vco_var": {"tp", "tn", "W", "vbp", "gnd"},
    "ampcal_det": {
        "tp", "tn", "ct", "vdd", "gnd", "cmp", "hold", "rep", "en", "vthn",
    },
}


def um(x):
    return int(round(x / DBU))


class Asm:
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
        self.tm1 = self.ly.layer(126, 0)
        self.tm1pin = self.ly.layer(126, 2)
        self.tm1txt = self.ly.layer(126, 25)
        self.log = []
        self.place_info = {}  # name -> {ox, oy, pins_island, bb}

    def say(self, s=""):
        print(s, flush=True)
        self.log.append(s)

    def pcell(self, name, params):
        return self.ly.add_pcell_variant(
            self.lib, self.lib_ly.pcell_declaration(name).id(), params)

    def place_ll(self, parent, cid, x, y):
        """Place so child bbox lower-left is at (x,y) µm."""
        bb0 = self.ly.cell(cid).bbox().to_dtype(self.ly.dbu)
        tr = pya.DTrans(pya.DVector(x - bb0.left, y - bb0.bottom))
        parent.insert(pya.DCellInstArray(cid, tr))
        return bb0.transformed(tr), tr

    def load_child(self, name):
        gds = GDS[name]
        if not os.path.exists(gds):
            raise SystemExit(f"missing {gds}")
        src_ly = pya.Layout()
        src_ly.read(gds)
        src = src_ly.cell(name) or src_ly.top_cell()
        cell = self.ly.create_cell(name + "_j")
        cell.copy_tree(src)
        pins = {}
        for L, D in ((8, 25), (126, 25)):
            lyr = src_ly.layer(L, D)
            for s in src.shapes(lyr).each():
                if s.is_text():
                    t = s.text
                    pins[t.string] = (
                        t.trans.disp.x * src_ly.dbu,
                        t.trans.disp.y * src_ly.dbu,
                    )
        # Also hierarchical texts for bank g*
        for li in src_ly.layer_indexes():
            info = src_ly.get_info(li)
            if info.datatype != 25:
                continue
            for sh in src.begin_shapes_rec(li).each():
                if not sh.shape().is_text():
                    continue
                t = sh.shape().text
                nm = t.string
                if nm in pins:
                    continue
                if nm.startswith("g") or nm.startswith("bb") or nm in (
                    "tp", "tn", "vbp", "gnd", "W", "ct", "tail",
                ):
                    tp = sh.trans() * t
                    pins[nm] = (tp.x * src_ly.dbu, tp.y * src_ly.dbu)
        keep = KEEP_PINS.get(name, set())
        for L, D in ((8, 25), (8, 2), (126, 25), (126, 2)):
            lyr = self.ly.layer(L, D)
            # clear all pin texts/markers; re-add keepers after place via top
            cell.shapes(lyr).clear()
        bb = cell.bbox().to_dtype(self.ly.dbu)
        return cell.cell_index(), pins, bb, keep

    def pin_tm1(self, cell, x, y, name):
        cell.shapes(self.tm1).insert(pya.DBox(x - 0.5, y - 0.5, x + 0.5, y + 0.5))
        cell.shapes(self.tm1pin).insert(pya.DBox(x - 0.4, y - 0.4, x + 0.4, y + 0.4))
        cell.shapes(self.tm1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def pin_m1(self, cell, x, y, name):
        cell.shapes(self.m1).insert(pya.DBox(x - 0.25, y - 0.25, x + 0.25, y + 0.25))
        cell.shapes(self.m1pin).insert(pya.DBox(x - 0.2, y - 0.2, x + 0.2, y + 0.2))
        cell.shapes(self.m1txt).insert(pya.DText(name, pya.DTrans(x, y)))

    def strap_m2(self, cell, x0, y0, x1, y1, w=2.0):
        """Axis-aligned M2 rectangle (horizontal or vertical segment)."""
        if abs(y1 - y0) < 1e-9:  # horizontal
            y = y0
            cell.shapes(self.m2).insert(
                pya.DBox(min(x0, x1), y - w / 2, max(x0, x1), y + w / 2))
        else:  # treat as H-only plan: use M3 for vertical
            x = x0
            cell.shapes(self.m3).insert(
                pya.DBox(x - w / 2, min(y0, y1), x + w / 2, max(y0, y1)))

    def strap_tm1(self, cell, x0, y0, x1, y1, w=4.0):
        if abs(y1 - y0) < 1e-9:
            y = y0
            cell.shapes(self.tm1).insert(
                pya.DBox(min(x0, x1), y - w / 2, max(x0, x1), y + w / 2))
        else:
            x = x0
            cell.shapes(self.tm1).insert(
                pya.DBox(x - w / 2, min(y0, y1), x + w / 2, max(y0, y1)))

    def via12(self):
        return self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "Metal2",
            "vn_columns": 1, "vn_rows": 1,
        })

    def via23(self):
        return self.pcell("via_stack", {
            "b_layer": "Metal2", "t_layer": "Metal3",
            "vn_columns": 1, "vn_rows": 1,
        })

    def via2t(self):
        return self.pcell("via_stack", {
            "b_layer": "Metal2", "t_layer": "TopMetal1",
            "vn_columns": 1, "vn_rows": 1,
        })

    def via1t(self):
        return self.pcell("via_stack", {
            "b_layer": "Metal1", "t_layer": "TopMetal1",
            "vn_columns": 1, "vn_rows": 1,
        })

    def build(self, routed):
        c = self.ly.create_cell("vco_top")
        vs12 = self.via12()
        vs23 = self.via23()
        vs2t = self.via2t()
        vs1t = self.via1t()

        kids = {}
        for name in ("vco_bank", "vco_core_tank", "tail_block", "vco_var",
                     "ampcal_det"):
            cid, pins, bb, keep = self.load_child(name)
            kids[name] = {"cid": cid, "pins": pins, "bb0": bb, "keep": keep}

        # Floor place per routing plan
        gap_ct = 8.0
        bank_ll = (0.0, 0.0)
        bank_bb, bank_tr = self.place_ll(
            c, kids["vco_bank"]["cid"], bank_ll[0], bank_ll[1])
        core_ll = (0.0, bank_bb.top)
        core_bb, core_tr = self.place_ll(
            c, kids["vco_core_tank"]["cid"], core_ll[0], core_ll[1])
        tail_ll = (core_bb.right + gap_ct, bank_bb.top)
        tail_bb, tail_tr = self.place_ll(
            c, kids["tail_block"]["cid"], tail_ll[0], tail_ll[1])
        x_e = max(bank_bb.right, tail_bb.right) + 8.0
        var_ll = (x_e, bank_bb.top + 8.0)
        var_bb, var_tr = self.place_ll(
            c, kids["vco_var"]["cid"], var_ll[0], var_ll[1])
        det_ll = (x_e, var_bb.top + 8.0)
        det_bb, det_tr = self.place_ll(
            c, kids["ampcal_det"]["cid"], det_ll[0], det_ll[1])

        def island_pins(name, tr):
            out = {}
            for k, (x, y) in kids[name]["pins"].items():
                p = tr * pya.DPoint(x, y)
                out[k] = (p.x, p.y)
            return out

        self.place_info = {
            "vco_bank": {"bb": bank_bb, "pins": island_pins("vco_bank", bank_tr)},
            "vco_core_tank": {
                "bb": core_bb, "pins": island_pins("vco_core_tank", core_tr),
            },
            "tail_block": {
                "bb": tail_bb, "pins": island_pins("tail_block", tail_tr),
            },
            "vco_var": {"bb": var_bb, "pins": island_pins("vco_var", var_tr)},
            "ampcal_det": {
                "bb": det_bb, "pins": island_pins("ampcal_det", det_tr),
            },
        }
        for nm, info in self.place_info.items():
            self.say(f"place {nm} bb={info['bb']}")
            for pk in sorted(info["pins"]):
                if pk in KEEP_PINS.get(nm, set()) or pk in TOP_PORTS or pk == "W":
                    self.say(f"  pin {pk} @ ({info['pins'][pk][0]:.2f},"
                             f"{info['pins'][pk][1]:.2f})")

        outline = c.bbox().to_dtype(self.ly.dbu)
        self.say(
            f"outline bbox={outline} area="
            f"{outline.width()*outline.height()*1e-6:.4f} mm2 [GDS]"
        )

        # Export top pins at block pin locations (label only; metal already in child)
        def export_pin(net, x, y, layer="m1"):
            if layer == "tm1":
                self.pin_tm1(c, x, y, net)
            else:
                self.pin_m1(c, x, y, net)

        # Prefer core tank / ct on TM1; var W as vt; etc.
        cp = self.place_info["vco_core_tank"]["pins"]
        bp = self.place_info["vco_bank"]["pins"]
        tpins = self.place_info["tail_block"]["pins"]
        vp = self.place_info["vco_var"]["pins"]
        dp = self.place_info["ampcal_det"]["pins"]

        if "place" in routed or True:
            # Always label sch ports for LVS pin extract
            if "tp" in cp:
                export_pin("tp", *cp["tp"], "tm1")
            if "tn" in cp:
                export_pin("tn", *cp["tn"], "tm1")
            if "ct" in cp:
                export_pin("ct", *cp["ct"], "tm1")
            if "tail" in cp:
                export_pin("tail", *cp["tail"], "m1")
            if "gnd" in cp:
                export_pin("gnd", *cp["gnd"], "m1")
            if "W" in vp:
                export_pin("vt", *vp["W"], "m1")
            if "vbp" in bp:
                export_pin("vbp", *bp["vbp"], "m1")
            if "vbp_tail" in tpins:
                export_pin("vbp_tail", *tpins["vbp_tail"], "m1")
            if "vdd" in tpins:
                export_pin("vdd", *tpins["vdd"], "m1")
            for i in range(12):
                g = f"g{i}"
                if g in bp:
                    export_pin(g, *bp[g], "m1")
            for i in range(5):
                g = f"code{i}"
                if g in tpins:
                    export_pin(g, *tpins[g], "m1")
            for nm in ("cmp", "hold", "rep", "en", "vthn"):
                if nm in dp:
                    export_pin(nm, *dp[nm], "m1")

        # ---- power ----
        if "power" in routed:
            tops = [info["bb"].top for info in self.place_info.values()]
            bots = [info["bb"].bottom for info in self.place_info.values()]
            lefts = [info["bb"].left for info in self.place_info.values()]
            rights = [info["bb"].right for info in self.place_info.values()]
            y_vdd = max(tops) + 4.0
            y_gnd = min(bots) - 4.0
            x0, x1 = min(lefts) - 2.0, max(rights) + 2.0
            w_pwr = 4.0
            c.shapes(self.m2).insert(
                pya.DBox(x0, y_vdd - w_pwr / 2, x1, y_vdd + w_pwr / 2))
            c.shapes(self.m2).insert(
                pya.DBox(x0, y_gnd - w_pwr / 2, x1, y_gnd + w_pwr / 2))
            self.say(f"power spines y_vdd={y_vdd:.2f} y_gnd={y_gnd:.2f} "
                     f"x=[{x0:.1f},{x1:.1f}] w={w_pwr} [HAND]")

            def drop_power(px, py, rail_y, net):
                # M3 vertical from pin to rail; via12 at pin if M1; via23 at rail
                c.shapes(self.m3).insert(
                    pya.DBox(px - 1.0, min(py, rail_y), px + 1.0, max(py, rail_y)))
                c.insert(pya.DCellInstArray(
                    vs23, pya.DTrans(pya.DVector(px, rail_y))))
                c.insert(pya.DCellInstArray(
                    vs12, pya.DTrans(pya.DVector(px, py))))

            # vdd drops: tail + det
            for src in (tpins, dp):
                if "vdd" in src:
                    drop_power(src["vdd"][0], src["vdd"][1], y_vdd, "vdd")
            # gnd drops: core, bank, tail, var, det
            for src in (cp, bp, tpins, vp, dp):
                if "gnd" in src:
                    drop_power(src["gnd"][0], src["gnd"][1], y_gnd, "gnd")
            export_pin("vdd", x1 - 2.0, y_vdd, "m1")
            c.insert(pya.DCellInstArray(
                vs12, pya.DTrans(pya.DVector(x1 - 2.0, y_vdd))))

        # ---- ct: TM1 short from core ct toward vdd rail column ----
        if "ct" in routed and "ct" in cp:
            cx, cy = cp["ct"]
            # horizontal TM1 to east of core, then note: full ct↔vdd via in later refine
            x_ct_end = core_bb.right + 3.0
            self.strap_tm1(c, cx, cy, x_ct_end, cy, w=4.0)
            export_pin("ct", x_ct_end, cy, "tm1")
            self.say(f"ct TM1 spine ({cx:.1f},{cy:.1f})→({x_ct_end:.1f},{cy:.1f})")

        # ---- tail ----
        if "tail" in routed and "tail" in cp and "tail" in tpins:
            x0, y0 = cp["tail"]
            x1, y1 = tpins["tail"]
            # M2 H at y0 to x mid, M3 V to y1, M2 H to x1
            xm = 0.5 * (core_bb.right + tail_bb.left)
            c.shapes(self.m2).insert(
                pya.DBox(min(x0, xm), y0 - 1.0, max(x0, xm), y0 + 1.0))
            c.shapes(self.m3).insert(
                pya.DBox(xm - 1.0, min(y0, y1), xm + 1.0, max(y0, y1)))
            c.shapes(self.m2).insert(
                pya.DBox(min(xm, x1), y1 - 1.0, max(xm, x1), y1 + 1.0))
            c.insert(pya.DCellInstArray(vs12, pya.DTrans(pya.DVector(x0, y0))))
            c.insert(pya.DCellInstArray(vs23, pya.DTrans(pya.DVector(xm, y0))))
            c.insert(pya.DCellInstArray(vs23, pya.DTrans(pya.DVector(xm, y1))))
            c.insert(pya.DCellInstArray(vs12, pya.DTrans(pya.DVector(x1, y1))))
            self.say(f"tail route core→tail via x={xm:.1f}")

        # ---- tn / tp (symmetric TM1) ----
        if "tn_tp" in routed:
            for net in ("tn", "tp"):
                pts = []
                if net in cp:
                    pts.append(cp[net])
                if net in bp:
                    pts.append(bp[net])
                if net in vp:
                    pts.append(vp[net])
                if net in dp:
                    pts.append(dp[net])
                if len(pts) < 2:
                    self.say(f"{net}: need ≥2 pins, have {len(pts)}")
                    continue
                # Sort by y descending; TM1 Manhattan through a common y
                ys = [p[1] for p in pts]
                y_sp = 0.5 * (min(ys) + max(ys))
                xs = [p[0] for p in pts]
                # horizontal spine
                self.strap_tm1(c, min(xs), y_sp, max(xs), y_sp, w=4.0)
                for px, py in pts:
                    self.strap_tm1(c, px, py, px, y_sp, w=4.0)
                # via TM1→M1 at var/det pins (M1 stubs)
                for block, pp in (("vco_var", vp), ("ampcal_det", dp)):
                    if net in pp:
                        px, py = pp[net]
                        c.insert(pya.DCellInstArray(
                            vs1t, pya.DTrans(pya.DVector(px, py))))
                self.say(f"{net} TM1 spine y={y_sp:.2f} x=[{min(xs):.1f},"
                         f"{max(xs):.1f}] n_pins={len(pts)}")

        # ---- vt shielded ----
        if "vt" in routed and "W" in vp:
            vx, vy = vp["W"]
            y_vt = bank_bb.bottom - 6.0
            x_west = bank_bb.left - 10.0
            # M3 vertical drop from pin to y_vt, M2 H west
            c.shapes(self.m3).insert(
                pya.DBox(vx - 1.0, min(vy, y_vt), vx + 1.0, max(vy, y_vt)))
            c.shapes(self.m2).insert(
                pya.DBox(min(x_west, vx), y_vt - 1.0, max(x_west, vx), y_vt + 1.0))
            for dy in (-2.5, 2.5):
                c.shapes(self.m2).insert(
                    pya.DBox(min(x_west, vx), y_vt + dy - 0.7,
                             max(x_west, vx), y_vt + dy + 0.7))
            c.insert(pya.DCellInstArray(vs12, pya.DTrans(pya.DVector(vx, vy))))
            c.insert(pya.DCellInstArray(vs23, pya.DTrans(pya.DVector(vx, vy))))
            c.insert(pya.DCellInstArray(vs23, pya.DTrans(pya.DVector(vx, y_vt))))
            export_pin("vt", x_west, y_vt, "m1")
            c.insert(pya.DCellInstArray(
                vs12, pya.DTrans(pya.DVector(x_west, y_vt))))
            self.say(f"vt shielded escape y={y_vt:.2f}")

        # ---- controls (minimal: vbp bank↔var; codes/gates labelled only) ----
        if "controls" in routed:
            if "vbp" in bp and "vbp" in vp:
                x0, y0 = bp["vbp"]
                x1, y1 = vp["vbp"]
                ym = y0
                c.shapes(self.m2).insert(
                    pya.DBox(min(x0, x1), ym - 1.0, max(x0, x1), ym + 1.0))
                c.shapes(self.m3).insert(
                    pya.DBox(x1 - 1.0, min(ym, y1), x1 + 1.0, max(ym, y1)))
                c.insert(pya.DCellInstArray(
                    vs12, pya.DTrans(pya.DVector(x0, y0))))
                c.insert(pya.DCellInstArray(
                    vs23, pya.DTrans(pya.DVector(x1, ym))))
                c.insert(pya.DCellInstArray(
                    vs12, pya.DTrans(pya.DVector(x1, y1))))
                self.say("vbp bank↔var routed")
            self.say("controls: gate/code pins exported; full bus straps TBD if LVS needs")

        # write GDS
        gds = os.path.join(OUT, "vco_top.gds")
        self.ly.write(gds)
        with open(gds, "rb") as f, gzip.open(gds + ".gz", "wb") as z:
            shutil.copyfileobj(f, z)
        self.say(f"wrote {gds}.gz")
        self.write_spice()
        open(os.path.join(OUT, "summary_build_log.txt"), "w").write(
            "\n".join(self.log) + "\n")
        return outline

    def write_spice(self):
        """Hierarchical LVS spice from proven leaf netlists [TOOL]."""
        chunks = []
        for name, path in SPICE_LEAF.items():
            txt = open(path).read()
            # drop .end
            lines = [ln for ln in txt.splitlines()
                     if not ln.strip().lower().startswith(".end")]
            chunks.append("\n".join(lines))
        ports = " ".join(TOP_PORTS)
        # bb* local float nets for bank
        bbs = " ".join(f"bb{i}" for i in range(12))
        top = f"""
* P2.7.2c vco_top hierarchical LVS netlist [layout leaf spices]
.subckt vco_top {ports}
Xc tp tn tail ct gnd vco_core_tank
Xb tp tn vbp gnd g0 bb0 g1 bb1 g2 bb2 g3 bb3 g4 bb4 g5 bb5 g6 bb6 g7 bb7 g8 bb8 g9 bb9 g10 bb10 g11 bb11 vco_bank
Xv tp tn vt vbp gnd G1 G2 vco_var
Xt tail vdd gnd vbp_tail nb nbf pbias xraw code_gnd code0 code1 code2 code3 code4 code_vdd ss tail_f tail_block
Xd tp tn ct vdd gnd cmp hold rep en vthn ampcal_det
.ends
.end
"""
        # Note: G1/G2/nb/... are local floats unless exported — OK for LVS dangling
        body = "\n\n".join(chunks) + "\n" + top
        path = os.path.join(OUT, "vco_top.spice")
        open(path, "w").write(body)
        self.say(f"wrote {path}")


def main():
    nets = "place"
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        if argv[i] == "--nets" and i + 1 < len(argv):
            nets = argv[i + 1]
            i += 2
        else:
            i += 1
    order = ["place", "power", "ct", "tail", "tn_tp", "vt", "controls"]
    if nets == "all":
        routed = set(order)
    else:
        routed = set()
        for part in nets.split(","):
            part = part.strip()
            if part not in order and part != "all":
                raise SystemExit(f"unknown net group {part}")
            # include all prior groups (incremental)
            for g in order:
                routed.add(g)
                if g == part:
                    break
    print(f"routed groups: {sorted(routed)}", flush=True)
    a = Asm()
    a.build(routed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
