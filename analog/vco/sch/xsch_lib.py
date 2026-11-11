#!/usr/bin/env python3
"""Minimal xschem .sch / .sym writer for P2.7.1 hierarchical capture.

Devices are placed on a grid; each terminal gets a lab_pin at the symbol pin
offset so nets connect by name (no drawn wires). Ideal R/C/L/V/I use devices/*
to match the VACASK deck element classes; MOS / MIM / svaricap use PDK symbols.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field


HDR = "v {xschem version=3.4.7 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"


# Pin offsets relative to instance origin (rot=0, flip=0), from PDK / devices symbols.
# NMOS: D top (−30), S bottom (+30). PMOS symbol swaps D/S vertically.
PINS = {
    "nmos": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
    "pmos": {"D": (20, 30), "G": (-20, 0), "S": (20, -30), "B": (20, 0)},
    "mim": {"c0": (0, -30), "c1": (0, 30), "bn": (-30, 0)},
    "svaricap": {"G2": (-40, 0), "NW": (0, -30), "G1": (40, 0)},
    "res": {"p": (0, -30), "m": (0, 30)},
    "capa": {"p": (0, -30), "m": (0, 30)},
    "ind": {"p": (0, -30), "m": (0, 30)},
    "vsource": {"p": (0, -30), "m": (0, 30)},
    "isource": {"p": (0, -30), "m": (0, 30)},
}


@dataclass
class DeviceRec:
    """One device for equivalence / VACASK export (canonical VACASK pin order)."""
    kind: str
    name: str
    nodes: list[str]
    params: dict


@dataclass
class Sch:
    name: str
    path: str
    lines: list[str] = field(default_factory=list)
    devices: list[DeviceRec] = field(default_factory=list)
    ports: list[str] = field(default_factory=list)
    _lab_i: int = 0
    _y: float = 0.0
    _x: float = 0.0
    _col: int = 0
    _row_h: float = 120.0
    _col_w: float = 220.0

    def __post_init__(self):
        self.lines = [HDR]

    def _lab(self, x, y, net, flip=0):
        """Label a net at (x,y); draw a 0-length stub so the pin attaches."""
        self._lab_i += 1
        # Zero-length wire node at the pin location helps attachment.
        self.lines.append(f"N {x:g} {y:g} {x:g} {y:g} {{lab={net}}}\n")
        self.lines.append(
            f"C {{devices/lab_pin.sym}} {x:g} {y:g} 0 {flip} "
            f"{{name=p{self._lab_i} sig_type=std_logic lab={net}}}\n"
        )

    def _slot(self):
        x = self._x + self._col * self._col_w
        y = self._y
        self._col += 1
        if self._col >= 6:
            self._col = 0
            self._y += self._row_h
        return x, y

    def iopin(self, net, side="left"):
        """Port pin for hierarchical symbol (iopin)."""
        if net not in self.ports:
            self.ports.append(net)
        x = -200 if side == "left" else 1200
        y = -40 * (len(self.ports))
        self.lines.append(
            f"C {{devices/iopin.sym}} {x:g} {y:g} 0 0 "
            f"{{name={net} lab={net}}}\n"
        )

    def title(self, text):
        self.lines.append(
            f"C {{devices/title.sym}} 0 40 0 0 "
            f"{{name=t1 author=\"HT13G-M P2.7.1\"}}\n"
        )
        self.lines.append(
            f"C {{devices/lab_pin.sym}} 200 40 0 0 "
            f"{{name=ttitle lab={text}}}\n"
        )

    def nmos(self, name, d, g, s, b, w, l, ng, model="sg13_lv_nmos"):
        x, y = self._slot()
        self.lines.append(
            f"C {{sg13g2_pr/sg13_lv_nmos.sym}} {x:g} {y:g} 0 0 {{name={name}\n"
            f"w={w}\nl={l}\nng={ng}\nm=1\nmodel={model}\nspiceprefix=X\n}}\n"
        )
        for pin, net in (("D", d), ("G", g), ("S", s), ("B", b)):
            ox, oy = PINS["nmos"][pin]
            self._lab(x + ox, y + oy, net, flip=1 if pin == "G" else 0)
        self.devices.append(DeviceRec(
            "nmos", name, [d, g, s, b],
            {"w": w, "l": l, "ng": str(ng), "model": model}))

    def pmos(self, name, d, g, s, b, w, l, ng, model="sg13_lv_pmos"):
        x, y = self._slot()
        self.lines.append(
            f"C {{sg13g2_pr/sg13_lv_pmos.sym}} {x:g} {y:g} 0 0 {{name={name}\n"
            f"w={w}\nl={l}\nng={ng}\nm=1\nmodel={model}\nspiceprefix=X\n}}\n"
        )
        for pin, net in (("D", d), ("G", g), ("S", s), ("B", b)):
            ox, oy = PINS["pmos"][pin]
            self._lab(x + ox, y + oy, net, flip=1 if pin == "G" else 0)
        self.devices.append(DeviceRec(
            "pmos", name, [d, g, s, b],
            {"w": w, "l": l, "ng": str(ng), "model": model}))

    def mim(self, name, c0, c1, bn, w_um, l_um):
        x, y = self._slot()
        # xschem template uses metres; VACASK decks use um suffix on numbers.
        wu = float(str(w_um).rstrip("u")) * 1e-6
        lu = float(str(l_um).rstrip("u")) * 1e-6
        self.lines.append(
            f"C {{sg13g2_pr/cap_rfcmim.sym}} {x:g} {y:g} 0 0 {{name={name}\n"
            f"model=cap_rfcmim\nlvs_model=rfcmim\n"
            f"w={wu:.6e}\nl={lu:.6e}\nwfeed=5.0e-6\nm=1\nmm_ok=1\n"
            f"spiceprefix=X\n}}\n"
        )
        for pin, net in (("c0", c0), ("c1", c1), ("bn", bn)):
            ox, oy = PINS["mim"][pin]
            self._lab(x + ox, y + oy, net)
        self.devices.append(DeviceRec(
            "mim", name, [c0, c1, bn],
            {"w": f"{float(str(w_um).rstrip('u')):.3f}u",
             "l": f"{float(str(l_um).rstrip('u')):.3f}u",
             "model": "cap_rfcmim"}))

    def svaricap_fx(self, name, g1, w, g2, bn, wu="3.74u", lu="0.3u", nx=10):
        """Place PDK svaricap symbol with model override to local _fx."""
        x, y = self._slot()
        # Symbol pin order netlists as G2, NW, G1, body — VACASK is (g1 w g2 bn).
        # Connect: G1=g1, NW=w, G2=g2. Converter remaps pin order for VACASK.
        self.lines.append(
            f"C {{sg13g2_pr/sg13_svaricap.sym}} {x:g} {y:g} 0 0 {{name={name}\n"
            f"model=sg13_hv_svaricap_fx\n"
            f"W={float(str(wu).rstrip('u'))*1e-6:.6e}\n"
            f"L={float(str(lu).rstrip('u'))*1e-6:.6e}\n"
            f"Nx={nx}\nspiceprefix=X\n}}\n"
        )
        # body via lab at NW area — PDK uses body=sub! attr; force with lab on NW
        # and a separate body attribute is not a pin; attach bn with a note lab near NW.
        for pin, net in (("G1", g1), ("NW", w), ("G2", g2)):
            ox, oy = PINS["svaricap"][pin]
            self._lab(x + ox, y + oy, net)
        # substrate: PDK attribute body=sub!; override by placing lab named bn on a
        # short wire is not available — set body prop via extra attr in instance.
        # Re-emit instance line is awkward; add body= in a comment device and
        # rewrite file: patch last C block. Simpler: use code.sym for body tie.
        self.lines[-1] = self.lines[-1].replace(
            "spiceprefix=X\n}",
            f"spiceprefix=X\nbody={bn}\n}}",
        )
        self.devices.append(DeviceRec(
            "svaricap", name, [g1, w, g2, bn],
            {"w": wu, "l": lu, "nx": str(nx), "model": "sg13_hv_svaricap_fx"}))

    def res(self, name, a, b, r):
        x, y = self._slot()
        self.lines.append(
            f"C {{devices/res.sym}} {x:g} {y:g} 0 0 {{name={name}\n"
            f"value={r}\nm=1\nfootprint=1206\ndevice=resistor\n"
            f"sim_device=resistor\n}}\n"
        )
        for pin, net in (("p", a), ("m", b)):
            ox, oy = PINS["res"][pin]
            self._lab(x + ox, y + oy, net)
        self.devices.append(DeviceRec("res", name, [a, b], {"r": str(r)}))

    def capa(self, name, a, b, c):
        x, y = self._slot()
        self.lines.append(
            f"C {{devices/capa.sym}} {x:g} {y:g} 0 0 {{name={name}\n"
            f"value={c}\nm=1\nfootprint=1206\ndevice=capacitor\n"
            f"sim_device=capacitor\n}}\n"
        )
        for pin, net in (("p", a), ("m", b)):
            ox, oy = PINS["capa"][pin]
            self._lab(x + ox, y + oy, net)
        self.devices.append(DeviceRec("capa", name, [a, b], {"c": str(c)}))

    def ind(self, name, a, b, l):
        x, y = self._slot()
        self.lines.append(
            f"C {{devices/ind.sym}} {x:g} {y:g} 0 0 {{name={name}\n"
            f"value={l}\nm=1\nfootprint=1206\ndevice=inductor\n"
            f"sim_device=inductor\n}}\n"
        )
        for pin, net in (("p", a), ("m", b)):
            ox, oy = PINS["ind"][pin]
            self._lab(x + ox, y + oy, net)
        self.devices.append(DeviceRec("ind", name, [a, b], {"l": str(l)}))

    def vsrc(self, name, p, m, dc):
        x, y = self._slot()
        self.lines.append(
            f"C {{devices/vsource.sym}} {x:g} {y:g} 0 0 "
            f"{{name={name} value={dc}}}\n"
        )
        for pin, net in (("p", p), ("m", m)):
            ox, oy = PINS["vsource"][pin]
            self._lab(x + ox, y + oy, net)
        self.devices.append(DeviceRec("vsrc", name, [p, m], {"dc": str(dc)}))

    def isrc(self, name, p, m, dc):
        x, y = self._slot()
        self.lines.append(
            f"C {{devices/isource.sym}} {x:g} {y:g} 0 0 "
            f"{{name={name} value={dc}}}\n"
        )
        for pin, net in (("p", p), ("m", m)):
            ox, oy = PINS["isource"][pin]
            self._lab(x + ox, y + oy, net)
        self.devices.append(DeviceRec("isrc", name, [p, m], {"dc": str(dc)}))

    def gnd(self, net="0"):
        x, y = self._slot()
        self.lines.append(
            f"C {{devices/gnd.sym}} {x:g} {y:g} 0 0 {{name=gnd_{self._lab_i} lab={net}}}\n"
        )

    def code_block(self, name, text):
        """Embed raw spice/vacask lines (e.g. .include of EM model)."""
        x, y = self._slot()
        esc = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
        self.lines.append(
            f"C {{devices/code.sym}} {x:g} {y:g} 0 0 {{name={name}\n"
            f"only_toplevel=false\nvalue=\"{esc}\"\n}}\n"
        )

    def subckt_inst(self, sym_rel, name, pin_nets: dict, x=None, y=None):
        """Instantiate a hierarchical symbol; pin_nets maps pin name -> net."""
        if x is None:
            x, y = self._slot()
        attrs = "\n".join(f"{k}={v}" for k, v in pin_nets.items())
        # xschem hierarchical: connect with lab_pins at pin positions from .sym
        self.lines.append(
            f"C {{{sym_rel}}} {x:g} {y:g} 0 0 {{name={name}\n{attrs}\n}}\n"
        )
        return x, y

    def write(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w") as fh:
            fh.writelines(self.lines)
        return self.path


def write_sym(path, cell, pins, pin_side="left"):
    """Hierarchical symbol: pins listed top-to-bottom on the left (or split)."""
    lines = [
        "v {xschem version=3.4.7 file_version=1.2}\n",
        "G {}\n",
        "K {type=subcircuit\n",
        'format="@name @pinlist @symname"\n',
        'template="name=x1"\n}\n',
        "V {}\nS {}\nE {}\n",
        "L 4 -80 -40 80 -40 {}\n",
        "L 4 -80 40 80 40 {}\n",
        "L 4 -80 -40 -80 40 {}\n",
        "L 4 80 -40 80 40 {}\n",
        f"T {{{cell}}} -60 -10 0 0 0.3 0.3 {{}}\n",
        "T {@name} 40 -30 0 0 0.2 0.2 {}\n",
    ]
    n = len(pins)
    for i, p in enumerate(pins):
        yy = -30 + (60 * i / max(n - 1, 1)) if n > 1 else 0
        if pin_side == "left":
            lines.append(
                f"B 5 -82.5 {yy-2.5:g} -77.5 {yy+2.5:g} "
                f"{{name={p} dir=inout}}\n"
            )
            lines.append(f"T {{{p}}} -75 {yy:g} 0 0 0.15 0.15 {{}}\n")
        else:
            lines.append(
                f"B 5 77.5 {yy-2.5:g} 82.5 {yy+2.5:g} "
                f"{{name={p} dir=inout}}\n"
            )
            lines.append(f"T {{{p}}} 50 {yy:g} 0 0 0.15 0.15 {{}}\n")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        fh.writelines(lines)


def side_um(c_ff, cap_area=1.5):
    return math.sqrt(c_ff / cap_area)

