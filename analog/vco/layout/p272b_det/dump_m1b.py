#!/usr/bin/env python3
"""Dump M1.b DRC items for bias_pd."""
import os
import pya

HERE = os.path.dirname(os.path.abspath(__file__))
drc = os.path.join(HERE, "out", "drc_bias_pd")
cands = []
for root, _, files in os.walk(drc):
    for f in files:
        if f.endswith(".lyrdb"):
            cands.append(os.path.join(root, f))
print("lyrdb:", cands)
path = [p for p in cands if "full" in p][0] if cands else None
if path is None:
    raise SystemExit("no lyrdb")
print("using", path)
rdb = pya.ReportDatabase()
rdb.load(path)
print("categories:", [c.name() for c in rdb.each_category()])
for cat in rdb.each_category():
    name = cat.name()
    if "M1.b" not in name and not (name.startswith("M1") and name.endswith(".b")):
        # also match nested
        if "M1.b" not in name:
            continue
    n = cat.num_items()
    print(f"CAT {name}: {n} items")
    i = 0
    for item in rdb.each_item_per_category(cat.rdb_id()):
        vals = []
        for v in item.each_value():
            vals.append(repr(v))
        print(f"  item{i}: {vals[:6]}")
        i += 1
        if i >= 20:
            print("  ...")
            break

# Also scan flattened M1 for near-miss gaps 0.01..0.17 um
ly = pya.Layout()
ly.read(os.path.join(HERE, "out", "bias_pd.gds"))
top = ly.top_cell()
m1 = ly.layer(pya.LayerInfo(8, 0))  # Metal1 drawing — confirm
# try common SG13 Metal1
for li in ly.layer_indexes():
    info = ly.get_info(li)
    if info.name and "Metal1" in info.name and info.datatype == 0:
        m1 = li
        print("using layer", info)
        break
region = pya.Region(top.begin_shapes_rec(m1))
merged = region.merged()
boxes = []
for p in merged.each():
    b = p.bbox()
    boxes.append((b.left * ly.dbu, b.bottom * ly.dbu, b.right * ly.dbu, b.top * ly.dbu))
print(f"merged M1 polygons: {len(boxes)}")
# pairwise spacing for near violations
hits = []
for i, a in enumerate(boxes):
    for j, b in enumerate(boxes):
        if j <= i:
            continue
        # horizontal gap
        if a[3] > b[1] and b[3] > a[1]:  # y overlap
            if a[2] < b[0]:
                gap = b[0] - a[2]
            elif b[2] < a[0]:
                gap = a[0] - b[2]
            else:
                gap = 0.0  # overlap/touch
            if 0.001 < gap < 0.18:
                hits.append(("x", gap, a, b))
        if a[2] > b[0] and b[2] > a[0]:  # x overlap
            if a[3] < b[1]:
                gap = b[1] - a[3]
            elif b[3] < a[1]:
                gap = a[1] - b[3]
            else:
                gap = 0.0
            if 0.001 < gap < 0.18:
                hits.append(("y", gap, a, b))
print(f"near-miss M1 gaps (<0.18): {len(hits)}")
for h in hits[:15]:
    print(f"  {h[0]}-gap={h[1]*1000:.1f}nm A={h[2]} B={h[3]}")
