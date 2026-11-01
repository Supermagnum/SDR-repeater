#!/usr/bin/env python3
"""Pre-EM checks for tapped L2n0: TM1 islands distinct; DC R match.

1) TM1 connectivity: P, N, CT must be three separate nets.
2) Conductor = L134 ∪ TM1 (north underpass bridges the two L134 pieces):
   R(P–CT) ≈ R(N–CT) ≈ R(P–N)/2 within 2 %.
"""
import os
import sys
import heapq

import numpy as np
import pya

HERE = os.path.dirname(os.path.abspath(__file__))
GDS = os.path.join(HERE, "L_2n0_tapped.gds")
OUT = os.path.join(HERE, "review", "net_r_check.txt")
PITCH = 0.5  # µm


def um_box(dbu, x0, y0, x1, y1):
    return pya.Box(int(round(x0 / dbu)), int(round(y0 / dbu)),
                   int(round(x1 / dbu)), int(round(y1 / dbu)))


def mask_grid(region, dbu, pitch):
    bbox = region.bbox()
    x0, y0 = bbox.left * dbu, bbox.bottom * dbu
    x1, y1 = bbox.right * dbu, bbox.top * dbu
    nx = int(np.ceil((x1 - x0) / pitch))
    ny = int(np.ceil((y1 - y0) / pitch))
    mask = np.zeros((ny, nx), dtype=bool)
    for iy in range(ny):
        y = y0 + (iy + 0.5) * pitch
        row = region & pya.Region(um_box(dbu, x0, y - pitch / 2, x1, y + pitch / 2))
        if row.is_empty():
            continue
        for ix in range(nx):
            x = x0 + (ix + 0.5) * pitch
            cell = um_box(dbu, x - pitch / 2, y - pitch / 2,
                          x + pitch / 2, y + pitch / 2)
            if (row & pya.Region(cell)).area() > 0:
                mask[iy, ix] = True
    return mask, x0, y0


def flood_labels(mask):
    from collections import deque
    ny, nx = mask.shape
    lab = -np.ones((ny, nx), dtype=np.int32)
    n = 0
    for iy in range(ny):
        for ix in range(nx):
            if not mask[iy, ix] or lab[iy, ix] >= 0:
                continue
            q = deque([(iy, ix)])
            lab[iy, ix] = n
            while q:
                y, x = q.popleft()
                for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    yy, xx = y + dy, x + dx
                    if (0 <= yy < ny and 0 <= xx < nx
                            and mask[yy, xx] and lab[yy, xx] < 0):
                        lab[yy, xx] = n
                        q.append((yy, xx))
            n += 1
    return lab, n


def nearest_true(mask, iy, ix):
    if mask[iy, ix]:
        return iy, ix
    ny, nx = mask.shape
    for r in range(1, max(ny, nx)):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if abs(dy) != r and abs(dx) != r:
                    continue
                y, x = iy + dy, ix + dx
                if 0 <= y < ny and 0 <= x < nx and mask[y, x]:
                    return y, x
    return None


def dijkstra(mask, start, goal):
    if start is None or goal is None:
        return None
    ny, nx = mask.shape
    dist = {start: 0.0}
    pq = [(0.0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == goal:
            return d
        if d > dist.get(u, 1e99):
            continue
        y, x = u
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            yy, xx = y + dy, x + dx
            if not (0 <= yy < ny and 0 <= xx < nx and mask[yy, xx]):
                continue
            nd = d + 1.0
            v = (yy, xx)
            if nd < dist.get(v, 1e99):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return None


def main():
    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    layout = pya.Layout()
    layout.read(GDS)
    dbu = layout.dbu
    top = layout.cell(next(layout.each_top_cell()))
    r134 = pya.Region(top.begin_shapes_rec(layout.layer(134, 0)))
    r126 = pya.Region(top.begin_shapes_rec(layout.layer(126, 0)))

    ports = {}
    for lyr, name in ((201, "P"), (202, "N"), (203, "CT")):
        sh = list(top.shapes(layout.layer(lyr, 0)).each())
        if not sh:
            say(f"FAIL: missing port {name}")
            return 1
        b = sh[0].bbox()
        ports[name] = (0.5 * (b.left + b.right) * dbu,
                       0.5 * (b.bottom + b.top) * dbu)

    say("# Tapped L2n0 net / R check")
    say(f"GDS: {GDS}")
    say("Ports µm: " + ", ".join(f"{k}={v}" for k, v in ports.items()))

    # --- 1) TM1 nets ---
    say(f"\n## TM1-only connectivity (pitch={PITCH} µm)")
    m126, x0, y0 = mask_grid(r126, dbu, PITCH)
    lab, ncomp = flood_labels(m126)
    say(f"  TM1 components: {ncomp}")
    port_comp = {}
    tm1_ok = True
    for name, xy in ports.items():
        iy = int((xy[1] - y0) / PITCH)
        ix = int((xy[0] - x0) / PITCH)
        cell = nearest_true(m126, iy, ix)
        if cell is None:
            say(f"FAIL: port {name} not on TM1")
            tm1_ok = False
            continue
        port_comp[name] = int(lab[cell])
        say(f"  {name} -> component {port_comp[name]}")
    if tm1_ok and len(set(port_comp[n] for n in ("P", "N", "CT"))) == 3:
        say("PASS: P, N, CT are three distinct TM1 nets.")
    else:
        say(f"FAIL: TM1 nets not distinct: {port_comp}")
        tm1_ok = False

    # CT stub only (south, y_top < 100) — do not flag the north underpass bar
    under = pya.Box(int(-25 / dbu), int(250 / dbu),
                    int(25 / dbu), int(290 / dbu))
    stub_clear = True
    for s in top.shapes(layout.layer(126, 0)).each():
        b = s.bbox()
        cx = 0.5 * (b.left + b.right) * dbu
        yt = b.top * dbu
        if abs(cx) < 8 and yt < 100:
            hit = pya.Region(b) & pya.Region(under)
            if not hit.is_empty():
                say("FAIL: CT stub overlaps north underpass zone")
                stub_clear = False
                tm1_ok = False
            else:
                say(f"CT stub (y_top={yt:.1f}) ∩ north underpass: NONE (clear)")
            break
    if stub_clear and tm1_ok:
        pass

    # --- CT via coverage ---
    say("\n## CT via on L134")
    via_ok = False
    ct_xy = None
    for s in top.shapes(layout.layer(133, 0)).each():
        b = s.bbox()
        cx = 0.5 * (b.left + b.right) * dbu
        cy = 0.5 * (b.bottom + b.top) * dbu
        if abs(cx) < 5 and 28 < cy < 50:
            cov = (r134 & pya.Region(b)).area() / max(pya.Region(b).area(), 1)
            say(f"  CT via ({cx:.2f},{cy:.2f}) "
                f"{(b.right-b.left)*dbu:.2f}×{(b.top-b.bottom)*dbu:.2f} µm  "
                f"coverage={100*cov:.1f}%")
            via_ok = cov >= 0.999
            ct_xy = (cx, cy)
            break
    if not via_ok:
        say("FAIL: CT via missing or not fully on L134")

    # --- 2) R on winding conductor (L134 ∪ TM1), CT stub excluded ---
    # The CT TM1 stub is a tap off the mid; including it lets current leave
    # the winding and skews R(P–N). Subtract the stub (south |x|<6, y<100).
    say(f"\n## DC resistance L134∪TM1 minus CT stub "
        f"(unit sheet R, pitch={PITCH} µm)")
    attach = {}
    for s in top.shapes(layout.layer(133, 0)).each():
        b = s.bbox()
        cx = 0.5 * (b.left + b.right) * dbu
        cy = 0.5 * (b.bottom + b.top) * dbu
        if abs(cx) < 5 and 28 < cy < 50:
            # seed at the top edge of the via (P–N path mid sits there)
            attach["CT"] = (cx, b.top * dbu)
        elif cx < -15 and 40 < cy < 60:
            attach["P"] = (cx, cy)
        elif cx > 15 and 40 < cy < 60:
            attach["N"] = (cx, cy)
    say(f"  via landings: {attach}")
    if set(attach) != {"P", "N", "CT"}:
        say("FAIL: could not classify P/N/CT via landings")
        open(OUT, "w").write("\n".join(lines) + "\n")
        return 1

    stub = pya.Region(um_box(dbu, -6.0, 0.0, 6.0, 100.0))
    cond = r134 + (r126 - stub)
    cond.merge()
    mask, x0, y0 = mask_grid(cond, dbu, PITCH)
    nodes = {}
    for name, xy in attach.items():
        iy = int((xy[1] - y0) / PITCH)
        ix = int((xy[0] - x0) / PITCH)
        nodes[name] = nearest_true(mask, iy, ix)
        if nodes[name] is None:
            say(f"FAIL: {name} not on conductor grid")
            open(OUT, "w").write("\n".join(lines) + "\n")
            return 1

    r_pn = dijkstra(mask, nodes["P"], nodes["N"])
    r_pct = dijkstra(mask, nodes["P"], nodes["CT"])
    r_nct = dijkstra(mask, nodes["N"], nodes["CT"])
    say(f"  R(P–N)  = {r_pn}")
    say(f"  R(P–CT) = {r_pct}")
    say(f"  R(N–CT) = {r_nct}")

    r_ok = False
    if None in (r_pn, r_pct, r_nct):
        say("FAIL: open path between via landings")
    else:
        half = 0.5 * r_pn
        arms = abs(r_pct - r_nct) / (0.5 * (r_pct + r_nct)) * 100
        vp = abs(r_pct - half) / half * 100
        vn = abs(r_nct - half) / half * 100
        say(f"  |R(P–CT)−R(N–CT)|/mean = {arms:.2f}% (gate ≤ 2%)")
        say(f"  |R(P–CT)−R(P–N)/2|/half = {vp:.2f}%")
        say(f"  |R(N–CT)−R(P–N)/2|/half = {vn:.2f}%")
        r_ok = arms <= 2.0 and vp <= 2.0 and vn <= 2.0
        say("PASS: R match within 2%" if r_ok else "FAIL: R match > 2%")

    say("\n## Verdict")
    ok = tm1_ok and via_ok and r_ok
    say("ALL CHECKS PASS" if ok else "CHECKS FAILED — do not run EM")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write("\n".join(lines) + "\n")
    say(f"Wrote {OUT}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
