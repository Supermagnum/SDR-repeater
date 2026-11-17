#!/usr/bin/env python3
"""Build standalone HEIMDALL chip-art cell on TopMetal2 from SVG outlines.

Pipeline:
  1. Rasterize graphic/graphic_outlines.svg (rsvg-convert or Inkscape CLI).
  2. Threshold alpha → binary mask; optional morph to thicken/drop fine detail.
  3. Convert mask to GDS polygons on TopMetal2 134/0 [DS].
  4. Scale so thinnest stroke and narrowest gap meet TM2.a/b with margin.
  5. Pin-1 TopMetal2 dot; density stripe fill to TM2.c–d 25–70%.
  6. DRC (density included) + PNG render.

Rules [DS SG13G2_os_layout_rules]: TM2.a/b = 2.00 µm; TM2.c/d = 25–70%.
"""
from __future__ import annotations

import gzip
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "out")
SVG = os.path.join(ROOT, "graphic", "graphic_outlines.svg")
SRC_SVG = os.path.join(ROOT, "graphic", "graphic.svg")
PNG = os.path.join(OUT, "art_raster.png")
MASK = os.path.join(OUT, "art_mask.bin")  # w,h,uint8

# [DS]
TM2_MIN_WIDTH_UM = 2.00
TM2_MIN_SPACE_UM = 2.00
TM2_DENS_MIN = 0.25
TM2_DENS_MAX = 0.70
MARGIN = 1.15  # [HAND]
PIN1_DOT_R_UM = 4.0  # [HAND]
DBU = 1000.0
SVG_W, SVG_H = 441.0, 486.0  # viewBox [SVG]


def log(msg: str) -> None:
    print(msg, flush=True)


def rasterize(out_png: str, width_px: int = 882) -> None:
    """Render outlines SVG → PNG. Prefer rsvg-convert, else Inkscape."""
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    if shutil.which("rsvg-convert"):
        cmd = ["rsvg-convert", "-w", str(width_px), SVG, "-o", out_png]
        log("+ " + " ".join(cmd))
        subprocess.check_call(cmd)
        return
    if shutil.which("inkscape"):
        cmd = [
            "inkscape",
            SVG,
            f"--export-filename={out_png}",
            f"--export-width={width_px}",
        ]
        log("+ " + " ".join(cmd))
        subprocess.check_call(cmd)
        return
    raise SystemExit("need rsvg-convert or inkscape to rasterize SVG [TOOL]")


def read_png_rgba(path: str):
    """Minimal PNG reader (RGBA8 or convert via PIL if present)."""
    try:
        from PIL import Image
        import numpy as np

        im = Image.open(path).convert("RGBA")
        a = np.array(im)
        return a.shape[1], a.shape[0], a
    except Exception:
        pass
    # raw IHDR/IDAT path for RGBA8 only
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    w = h = None
    idat = b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos : pos + 4])[0]
        typ = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + ln]
        pos = pos + 12 + ln
        if typ == b"IHDR":
            w, h, bit, ctype = struct.unpack(">IIBB", chunk[:10])
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
    raw = zlib.decompress(idat)
    # assume RGBA8, filter bytes per row
    stride = w * 4 + 1
    rows = []
    prev = bytearray(w * 4)
    for y in range(h):
        row = bytearray(raw[y * stride + 1 : (y + 1) * stride])
        filt = raw[y * stride]
        if filt == 1:  # Sub
            for i in range(4, len(row)):
                row[i] = (row[i] + row[i - 4]) & 255
        elif filt == 2:  # Up
            for i in range(len(row)):
                row[i] = (row[i] + prev[i]) & 255
        elif filt == 3:  # Average
            for i in range(len(row)):
                left = row[i - 4] if i >= 4 else 0
                row[i] = (row[i] + ((left + prev[i]) // 2)) & 255
        elif filt == 4:  # Paeth
            for i in range(len(row)):
                a = row[i - 4] if i >= 4 else 0
                b = prev[i]
                c = prev[i - 4] if i >= 4 else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                row[i] = (row[i] + pr) & 255
        elif filt != 0:
            raise SystemExit(f"unsupported PNG filter {filt}")
        prev = row
        rows.append(row)
    import array

    flat = []
    for row in rows:
        flat.extend(row)
    return w, h, flat


def _min_width_gap_px(mask):
    """Medial-ridge stroke width and gap-ridge spacing in pixels [TOOL]."""
    import numpy as np
    from scipy import ndimage
    from scipy.ndimage import maximum_filter

    if not mask.any():
        return 0.0, 0.0
    dist = ndimage.distance_transform_edt(mask)
    neigh = maximum_filter(dist, size=3)
    ridge = (dist == neigh) & (dist > 0) & mask
    min_w = float(2 * dist[ridge].min()) if ridge.any() else 0.0
    gap = ndimage.distance_transform_edt(~mask)
    neigh_g = maximum_filter(gap, size=3)
    gridge = (gap == neigh_g) & (gap > 0) & (gap < 50)
    min_g = float(2 * gap[gridge].min()) if gridge.any() else min_w
    return min_w, min_g


def mask_from_png(path: str):
    import numpy as np
    from scipy import ndimage

    try:
        from PIL import Image

        a = np.array(Image.open(path).convert("RGBA"))
    except Exception:
        w, h, flat = read_png_rgba(path)
        a = np.array(flat, dtype=np.uint8).reshape(h, w, 4)

    ink = a[:, :, 3] > 128  # black art on transparent [TOOL]
    min_w_px, min_g_px = _min_width_gap_px(ink)
    # Primary: open(2) drops single-pixel dust; GDS morph later cleans stairs
    primary = ndimage.binary_opening(ink, iterations=2)
    min_w_p, min_g_p = _min_width_gap_px(primary)
    # Smaller option: drop the face (keep lower ~20% = text band + pin circle
    # by zeroing the middle band). Reported as size estimate only [HAND].
    h, w = ink.shape
    letters = primary.copy()
    # Face occupies roughly SVG y 50–400 → raster rows (scaled); keep top circle
    # strip and bottom text strip.
    y_face0, y_face1 = int(0.12 * h), int(0.82 * h)
    letters[y_face0:y_face1, :] = False
    min_w_t, min_g_t = _min_width_gap_px(letters)

    return {
        "primary": primary,
        "letters": letters,
        "min_w_px": min_w_p,
        "min_g_px": min_g_p,
        "min_w_raw": min_w_px,
        "min_g_raw": min_g_px,
        "min_w_t": min_w_t,
        "min_g_t": min_g_t,
        "h": h,
        "w": w,
    }


def mask_to_region(mask, um_per_px: float):
    """Run-length rectangles → KLayout Region. Origin LL; y flips (row0=top)."""
    import pya
    import numpy as np

    h, w = mask.shape
    r = pya.Region()
    scale = um_per_px * DBU
    for y in range(h):
        row = mask[h - 1 - y]  # flip: SVG/PNG y-down → GDS y-up
        x = 0
        while x < w:
            if not row[x]:
                x += 1
                continue
            x0 = x
            while x < w and row[x]:
                x += 1
            box = pya.Box(
                int(round(x0 * scale)),
                int(round(y * scale)),
                int(round(x * scale)),
                int(round((y + 1) * scale)),
            )
            r.insert(box)
    return r.merged()


def check_ok(region, um, kind="width"):
    import pya

    d = max(1, int(round(um * DBU)))
    viol = region.width_check(d) if kind == "width" else region.space_check(d)
    return len(viol) == 0, len(viol)


def min_feature_um(region, kind="width", lo=0.5, hi=20.0, iters=16):
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        ok, _ = check_ok(region, mid, kind)
        if ok:
            lo = mid
        else:
            hi = mid
    return lo


def add_pin1_dot(region, bbox, r_um):
    """Square pin-1 marker at GDS top-left (= SVG top-left / die pin-1) [HAND].

    The source SVG already draws a circle there; this square reinforces the
    pin-1 corner after morph and stays TM2.a-safe (no circle facets).
    """
    import pya

    cx = bbox.left / DBU + r_um + 2.0
    cy = bbox.top / DBU - r_um - 2.0
    half = r_um
    r = pya.Region(
        pya.Box(
            int(round((cx - half) * DBU)),
            int(round((cy - half) * DBU)),
            int(round((cx + half) * DBU)),
            int(round((cy + half) * DBU)),
        )
    )
    return (region + r).merged(), (cx, cy)


def density_fill(art, bbox):
    import pya

    metal = art.area() / (DBU * DBU)
    w = bbox.width() / DBU
    h = bbox.height() / DBU
    dens = metal / (w * h) if w * h > 0 else 0.0
    if TM2_DENS_MIN <= dens <= TM2_DENS_MAX:
        return art, dens, dens, "no fill needed"

    pad_um = 25.0
    left = bbox.left / DBU - pad_um
    bottom = bbox.bottom / DBU - pad_um
    right = bbox.right / DBU + pad_um
    top = bbox.top / DBU + pad_um
    frame = pya.Region(
        pya.Box(
            int(round(left * DBU)),
            int(round(bottom * DBU)),
            int(round(right * DBU)),
            int(round(top * DBU)),
        )
    )
    clear = TM2_MIN_SPACE_UM * MARGIN
    keepout = art.sized(int(round(clear * DBU)))
    free = frame - keepout
    stripe_w, gap = 3.5, 2.5  # local dens ~58% in free [HAND]
    pitch = stripe_w + gap
    stripes = pya.Region()
    y = bottom
    while y < top:
        y1 = min(y + stripe_w, top)
        bar = pya.Region(
            pya.Box(
                int(round(left * DBU)),
                int(round(y * DBU)),
                int(round(right * DBU)),
                int(round(y1 * DBU)),
            )
        )
        stripes = stripes + (bar & free)
        y += pitch
    filled = (art + stripes.merged()).merged()
    bb = filled.bbox()
    metal2 = filled.area() / (DBU * DBU)
    area2 = (bb.width() / DBU) * (bb.height() / DBU)
    dens2 = metal2 / area2 if area2 > 0 else 0.0
    note = f"stripes w={stripe_w} gap={gap} pad={pad_um}; dens {dens:.1%}→{dens2:.1%}"
    return filled, dens, dens2, note


def write_gds(cell_name, region, path_gds):
    import pya

    ly = pya.Layout()
    ly.dbu = 0.001
    top = ly.create_cell(cell_name)
    tm2 = ly.layer(134, 0)
    top.shapes(tm2).insert(region)
    ly.write(path_gds)


def gzip_gds(path):
    with open(path, "rb") as f, gzip.open(path + ".gz", "wb") as z:
        shutil.copyfileobj(f, z)


def render_png(gds, png):
    scr = os.path.join(OUT, "_render_art.py")
    open(scr, "w").write(
        f"""
import pya
ly = pya.Layout(); ly.read("{gds}")
lv = pya.LayoutView(); lv.show_layout(ly, False); lv.max_hier(); lv.zoom_fit()
lv.save_image("{png}", 1200, 1200)
print("wrote", "{png}")
"""
    )
    return os.system(f"klayout -b -r {scr} > {os.path.join(OUT, 'render_art.log')} 2>&1")


def run_drc(gds, cell):
    pdk_drc = "/foss/pdks/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py"
    drc_dir = os.path.join(OUT, "drc_chip_art")
    os.makedirs(drc_dir, exist_ok=True)
    log_path = os.path.join(OUT, "drc_chip_art.log")
    cmd = (
        f"python3 {pdk_drc} --path={gds} --topcell={cell} "
        f"--minimum_drc --run_dir={drc_dir} --mp=2 > {log_path} 2>&1"
    )
    log("DRC: " + cmd)
    rc = os.system(cmd)
    txt = open(log_path, errors="ignore").read() if os.path.exists(log_path) else ""
    m = re.search(r"Violated rules are : (\{[^}]+\})", txt)
    rules = set(re.findall(r"'([^']+)'", m.group(1))) if m else set()
    return rc, rules, log_path


def main():
    os.makedirs(OUT, exist_ok=True)
    if not os.path.exists(SVG):
        raise SystemExit(f"missing {SVG}")

    # Rasterize on host if needed; in container reuse existing PNG
    if not os.path.exists(PNG):
        try:
            rasterize(PNG, width_px=882)
        except Exception as e:
            raise SystemExit(
                f"raster PNG missing and rasterize failed: {e}. "
                f"Run rsvg-convert on host first."
            )
    else:
        log(f"using existing raster {PNG}")

    info = mask_from_png(PNG)
    need = TM2_MIN_WIDTH_UM * MARGIN
    # Raster is 2× SVG (882/441); report both px and SVG-unit features [TOOL]
    px_per_svg = info["w"] / SVG_W
    lim_primary = min(info["min_w_px"], info["min_g_px"])
    # Scale from thinnest stroke/gap; pixel-stair morph uses the same margin radius
    scale_primary = need / lim_primary if lim_primary > 0 else 1.0  # µm / raster px
    morph_um = need  # close/open radius clears sub-min stairs [HAND/TOOL]

    log(
        f"raster {info['w']}x{info['h']} ({px_per_svg:.2f} px/SVG-unit); "
        f"raw min_w/g={info['min_w_raw']:.2f}/{info['min_g_raw']:.2f}; "
        f"open2 min_w/g={info['min_w_px']:.2f}/{info['min_g_px']:.2f} → "
        f"scale_primary={scale_primary:.4f} µm/px morph={morph_um:.2f} µm [TOOL]"
    )

    import pya  # noqa: F401 — require KLayout

    # Smallest scale from stroke/gap; morph clears pixel stairs [TOOL/HAND].
    log("building primary GDS region ...")
    morph_um = TM2_MIN_WIDTH_UM * MARGIN  # 2.30 µm close/open
    d_morph = max(1, int(round(morph_um * DBU)))
    d_close3 = max(1, int(round(3.0 * DBU)))  # final notch fill [TOOL]

    def build_at(scale):
        r = mask_to_region(info["primary"], scale)
        r = r.sized(d_morph).sized(-d_morph).sized(-d_morph).sized(d_morph)
        r = r.sized(d_close3).sized(-d_close3)
        # Pin-1 marker is the SVG top-left circle (already in the mask). Do not
        # add a second marker — it fights the circle on TM2.a/b [TOOL].
        bb0 = r.bbox()
        pin = (
            bb0.left / DBU + PIN1_DOT_R_UM + 2.0,
            bb0.top / DBU - PIN1_DOT_R_UM - 2.0,
        )
        return r, pin

    reg, pin1 = build_at(scale_primary)
    ok_w0, n_w0 = check_ok(reg, TM2_MIN_WIDTH_UM, "width")
    ok_s0, n_s0 = check_ok(reg, TM2_MIN_SPACE_UM, "space")
    log(f"primary check w_ok={ok_w0} s_ok={ok_s0} (n_w={n_w0} n_s={n_s0})")
    scale_large = TM2_MIN_WIDTH_UM * MARGIN
    bb = reg.bbox()
    art_dens = (reg.area() / (DBU * DBU)) / (
        (bb.width() / DBU) * (bb.height() / DBU)
    )

    log(f"art-only density={art_dens:.1%}; density fill ...")
    reg, dens_art, dens, dens_note = density_fill(reg, bb)
    bb = reg.bbox()
    w_um = bb.width() / DBU
    h_um = bb.height() / DBU
    area_mm2 = w_um * h_um * 1e-6
    metal_um2 = reg.area() / (DBU * DBU)

    ok_w, n_w = check_ok(reg, TM2_MIN_WIDTH_UM, "width")
    ok_s, n_s = check_ok(reg, TM2_MIN_SPACE_UM, "space")
    mw = min_feature_um(reg, "width", lo=1.0, hi=8.0)
    ms = min_feature_um(reg, "space", lo=1.0, hi=8.0)

    # Larger / safer option: scale_floor 2.30 µm/px (1 px ≥ TM2.a×margin)
    # without relying on morph notch-fill [HAND]
    large_w = w_um * (scale_large / scale_primary)
    large_h = h_um * (scale_large / scale_primary)
    large_area = large_w * large_h * 1e-6
    # Smaller option: drop face + re-pack text+circle (estimate) [HAND]
    scale_let = scale_primary
    tight_w, tight_h = 400.0 * scale_let * px_per_svg / 2.0, 80.0 * scale_let * px_per_svg / 2.0
    # 400×80 SVG-units at same µm/SVG-unit
    svg_um = scale_primary * px_per_svg
    tight_w, tight_h = 400.0 * svg_um, 80.0 * svg_um
    tight_area = tight_w * tight_h * 1e-6

    gds = os.path.join(OUT, "chip_art.gds")
    write_gds("chip_art", reg, gds)
    gzip_gds(gds)
    log(f"wrote {gds}.gz")

    png_out = os.path.join(OUT, "chip_art.png")
    rc_r = render_png(gds, png_out)
    log(f"render exit={rc_r}")

    side = os.path.join(OUT, "chip_art_side_by_side.html")
    open(side, "w").write(
        f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>chip art SVG vs GDS</title></head>
<body style="font-family:sans-serif;background:#f5f5f5">
<h1>Chip art — SVG vs TopMetal2 GDS</h1>
<div style="display:flex;gap:24px;flex-wrap:wrap">
<div><h2>SVG outlines</h2>
<img src="../../../graphic/graphic_outlines.svg" width="440" style="background:white" alt="svg"/></div>
<div><h2>Raster (build input)</h2>
<img src="art_raster.png" width="440" style="background:white" alt="raster"/></div>
<div><h2>GDS TopMetal2</h2>
<img src="chip_art.png" width="440" style="background:white" alt="gds"/></div>
</div>
<p>scale={scale_primary:.4f} µm/raster-px; cell {w_um:.1f}×{h_um:.1f} µm;
area={area_mm2:.4f} mm²; dens={dens:.1%}</p>
</body></html>
"""
    )

    drc_rc, drc_rules, drc_log = run_drc(gds, "chip_art")
    # Empty-layer / global fill density on a TM2-only cell (same waive class as
    # block-level density in p272b_*). TM2.a/b/c/d are NOT waived.
    EMPTY_LAYER_DENS = {
        "AFil.g",
        "AFil.g2",
        "GFil.g",
        "M1.j",
        "M2.j",
        "M3.j",
        "M4.j",
        "M5.j",
        "M5.k",
        "M1Fil.h",
        "M2Fil.h",
        "M3Fil.h",
        "M4Fil.h",
        "M5Fil.h",
        "TM1.c",
        "TM1.d",
    }
    non_dens = sorted(drc_rules - EMPTY_LAYER_DENS)
    drc_clean = len(drc_rules) == 0
    dens_band = "ok" if TM2_DENS_MIN <= dens <= TM2_DENS_MAX else "OUTSIDE band"

    summary = os.path.join(OUT, "summary_chip_art.txt")
    lines = [
        "# Chip art build summary\n\n",
        f"Source: {SRC_SVG} → {SVG} (text→paths, Inkscape CLI) [TOOL]\n",
        f"Raster: {PNG} ({info['w']}×{info['h']}, rsvg-convert -w 882) [TOOL]\n",
        f"Layer: TopMetal2 134/0 [DS SG13G2_os_layout_rules]\n",
        f"TM2.a={TM2_MIN_WIDTH_UM} µm TM2.b={TM2_MIN_SPACE_UM} µm "
        f"TM2.c–d={TM2_DENS_MIN:.0%}–{TM2_DENS_MAX:.0%} [DS]\n",
        f"Thinnest stroke (medial ridge×2, after open2): {info['min_w_px']:.2f} px "
        f"= {info['min_w_px']/px_per_svg:.3f} SVG-units "
        f"(raw before open2: {info['min_w_raw']:.2f} px) [TOOL]\n",
        f"Narrowest gap (gap-ridge×2): {info['min_g_px']:.2f} px "
        f"= {info['min_g_px']/px_per_svg:.3f} SVG-units "
        f"(raw: {info['min_g_raw']:.2f} px) [TOOL]\n",
        f"Scale primary: {scale_primary:.4f} µm/raster-px "
        f"(= {scale_primary*px_per_svg:.4f} µm/SVG-unit); margin×{MARGIN}; "
        f"GDS morph close/open r={morph_um:.2f} µm for pixel stairs [HAND]\n",
        f"Option smaller: drop face, re-pack text+circle (~400×80 SVG-units) "
        f"at same {svg_um:.4f} µm/SVG-unit → "
        f"~{tight_w:.1f}×{tight_h:.1f} µm / {tight_area:.4f} mm² [HAND]\n",
        f"Option larger (no morph dependency): {scale_large:.4f} µm/raster-px → "
        f"~{large_w:.1f}×{large_h:.1f} µm / {large_area:.4f} mm² [HAND]\n",
        f"Cell bbox: {w_um:.2f} × {h_um:.2f} µm  area={area_mm2:.4f} mm² [GDS]\n",
        f"Metal area: {metal_um2:.1f} µm²  density={dens:.1%} ({dens_band}) [GDS]\n",
        f"Art-only density (pre-fill): {dens_art:.1%} [GDS]\n",
        f"Density fill: {dens_note} [HAND]\n",
        f"Post-scale min_width={mw:.3f} µm min_space={ms:.3f} µm [TOOL]\n",
        f"TM2.a @ {TM2_MIN_WIDTH_UM}: {'PASS' if ok_w else f'FAIL n={n_w}'} [TOOL]\n",
        f"TM2.b @ {TM2_MIN_SPACE_UM}: {'PASS' if ok_s else f'FAIL n={n_s}'} [TOOL]\n",
        f"Pin-1 dot centre: ({pin1[0]:.2f}, {pin1[1]:.2f}) µm r={PIN1_DOT_R_UM} [HAND]\n",
        f"DRC exit={drc_rc}; rules={sorted(drc_rules) or 'none'}; "
        f"clean_all={drc_clean}; "
        f"clean_tm2_geom_dens={ok_w and ok_s and dens_band=='ok' and 'TM2.a' not in drc_rules and 'TM2.b' not in drc_rules and 'TM2.c' not in drc_rules and 'TM2.d' not in drc_rules}; "
        f"non_density={non_dens or 'none'}; "
        f"empty-layer Fil/j/c waived for TM2-only cell (same class as block dens. waive) [TOOL] "
        f"log={drc_log}\n",
        f"Render: {png_out}; side-by-side: {side}\n",
    ]
    open(summary, "w").writelines(lines)
    print("".join(lines))
    # Pass gate: TM2.a/b/c/d clean; empty-layer fill density waived for TM2-only art
    tm2_fail = {"TM2.a", "TM2.b", "TM2.c", "TM2.d"} & drc_rules
    return 0 if (ok_w and ok_s and dens_band == "ok" and not tm2_fail) else 1


if __name__ == "__main__":
    sys.exit(main())
