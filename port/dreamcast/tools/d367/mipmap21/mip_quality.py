#!/usr/bin/env python3
"""Lower-mip quality gate for a texture pack (lane mipfix22, 2026-10-22).

For every member with a mip chain (VQ, twiddled 16-bit, PAL4, PAL8) it decodes each
level exactly as the PVR reads it (after quantization / VQ encoding) and checks:

* cutout coverage (textures whose base has alpha < 255): the share of texels at or
  above the render alpha threshold (PT_ALPHA_REF 128; ARGB1555 is binary) of the FINAL
  encoded level, on every level of side >= MIN_SIDE, must stay within coverage_tol of
  the base level's share (relative, so thin branch / leaf cards with a small share are
  judged against their own silhouette: r101 bare-tree branches thinned in game).
  Premultiplied box filtering followed by a fixed binary threshold turns 25 % into 0 %
  and 50-75 % into 100 %, which makes fences, leaves and hair vanish or fill in.
* VQ lower-level colour (all VQ chains: the kept codebook may lack the averaged
  colours): against the ideal premultiplied box-filtered base, per level of side >=
  MIN_SIDE, the compact-VQ metrics (premultiplied RGB RMSE) plus the mean colour shift.
  Fails above COLOUR_RMSE or MEAN_SHIFT.

A failing texture is HELD at its original representation: the mip chain is stripped
and the exact base (codebook + base indices, texels, or indices + palette) is kept,
with the canonical CRC. Every other member is byte-identical. Output: a TSV row per
mipped texture and, with --out-pack, the corrected pack.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
import re
import sys
import zlib
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "d367"))
import convert_tpl as tpl
import mipmap_vq as vq
import mipmap_twiddled as tw
import mipmap_pal4 as pal4
import compact_native_pal8 as pal8
import texpack
from vram.vq_pak import read_pak

ALPHA_REF = 128
MIN_SIDE = 4
COVERAGE_REL = 0.20   # a level may move coverage by 20 % of the base share (thin branches have small shares)
COVERAGE_ABS = 0.04   # ... or by 4 points, or by one texel of that level, whichever is larger


def coverage_tol(cov0, side):
    return max(COVERAGE_REL * cov0, COVERAGE_ABS, 1.0 / (side * side))
COLOUR_RMSE = 32.0
MEAN_SHIFT = 12.0

READERS = (
    ("vq", vq.read_native_vq, vq.decode_level, lambda n: n.codebook + n.base_indices),
    ("twiddled", tw.read_native_twiddled, tw.decode_level, lambda n: n.base_texels),
    ("pal4", pal4.read_native_pal4, pal4.decode_level, lambda n: n.base_indices + n.palette),
    ("pal8", pal8.read_native_pal8, pal8.decode_level, lambda n: n.base_indices + n.palette),
)


def identify(blob):
    for name, read, decode, base in READERS:
        try:
            return name, read(blob), decode, base
        except ValueError:
            continue
    return None


def coverage(pixels):
    return sum(p[3] >= ALPHA_REF for p in pixels) / len(pixels)


def premul(pixels):
    return [(p[0] * p[3] / 255, p[1] * p[3] / 255, p[2] * p[3] / 255, p[3]) for p in pixels]


def halve(pixels, side):
    out = []
    for y in range(0, side, 2):
        for x in range(0, side, 2):
            q = (pixels[y * side + x], pixels[y * side + x + 1],
                 pixels[(y + 1) * side + x], pixels[(y + 1) * side + x + 1])
            out.append(tuple(sum(p[c] for p in q) / 4 for c in range(4)))
    return out


def colour(ideal, level):
    n = len(level)
    rmse = math.sqrt(sum((a[c] - b[c]) ** 2 for a, b in zip(ideal, level) for c in range(3)) / (n * 3))
    shift = max(abs(sum(a[c] for a in ideal) - sum(b[c] for b in level)) / n for c in range(3))
    return rmse, shift


def strip(blob, native, base):
    """Base-only package: exact base payload, mip flag cleared, canonical CRC."""
    payload = base(native)
    h, t = list(native.header), list(native.texture)
    t[5], t[6] = len(payload), t[6] & ~tpl.FLAG_MIPMAP
    h[7] = len(payload)
    body = tpl.TEXTURE.pack(*t) + payload
    h[8] = zlib.crc32(body) & 0xffffffff
    return tpl.HEADER.pack(*h) + body


HOLD_KEYS: set = set()


def _init_hold(keys):
    HOLD_KEYS.update(keys)


def read_hold(path):
    """--hold-keys manifest: TSV with a 'key' column (crc-fnv hex), e.g. tools/d367/mipmap22/room-select.tsv."""
    keys = set()
    for line in Path(path).read_text().splitlines():
        if not line or line.startswith('#') or line.startswith('key\t'):
            continue
        keys.add(line.split('\t')[0].strip())
    return keys


def audit(item):
    key, blob = item
    found = identify(blob)
    if not found or not found[1].mipmapped:
        return None
    name, native, decode, base = found
    side = native.size
    base_px = decode(native, side)
    alpha = any(p[3] < 255 for p in base_px)
    cov0 = coverage(base_px)
    ideal = premul(base_px)
    row = dict(key="%08x-%08x" % key, format=name, pixel_format=native.texture[3], side=side,
               alpha=alpha, base_coverage=round(cov0, 4), levels=[])
    reasons = set()
    if row["key"] in HOLD_KEYS:   # lane mipmap22: per-room selection manifest (--hold-keys)
        reasons.add("room-select")
    s = side
    while s > 1:
        ideal = halve(ideal, s)
        s //= 2
        lvl = decode(native, s)
        entry = dict(side=s)
        if alpha:
            c = coverage(lvl)
            entry["coverage"] = round(c, 4)
            if s >= MIN_SIDE and abs(c - cov0) > coverage_tol(cov0, s):
                reasons.add("coverage")
        if name == "vq":
            rmse, shift = colour(ideal, premul(lvl))
            entry.update(premultiplied_rgb_rmse=round(rmse, 2), mean_shift=round(shift, 2))
            if s >= MIN_SIDE and (rmse > COLOUR_RMSE or shift > MEAN_SHIFT):
                reasons.add("vq-colour")
        row["levels"].append(entry)
    row["verdict"] = "held" if reasons else "pass"
    row["reasons"] = sorted(reasons)
    held = None
    if reasons:
        held = strip(blob, native, base)
        again = READERS[[r[0] for r in READERS].index(name)][1](held)
        if again.mipmapped or decode(again, side) != base_px:
            raise ValueError("held base changed for " + row["key"])
    return key, row, held


ROW = re.compile(r"\{0x([0-9a-fA-F]{8})U,0x([0-9a-fA-F]{8})U,(\d+)U,(\d+)U,\{(\d+)U,(\d+)U,(\d+)U,(\d+)U,(\d+)U,(\d+)U,0x([0-9a-fA-F]{8})U\}")


def rebind(text, held):
    """Rewrite rect21 scoped_representations rows whose key is held: the adapter
    admits only the exact stored descriptor (dims, format, flags, layout, bytes, CRC)."""
    n = 0

    def sub(m):
        nonlocal n
        key = (int(m[1], 16), int(m[2], 16))
        if key not in held:
            return m[0]
        h = tpl.HEADER.unpack_from(held[key])
        t = tpl.TEXTURE.unpack_from(held[key], 48)
        n += 1
        return (f"{{0x{m[1]}U,0x{m[2]}U,{m[3]}U,{m[4]}U,{{{t[1]}U,{t[2]}U,{t[3]}U,{t[6]}U,{t[7]}U,"
                f"{t[5]}U,0x{h[8]:08x}U}}")
    return ROW.sub(sub, text), n


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pack", type=Path)
    ap.add_argument("--tsv", type=Path, required=True)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--out-pack", type=Path)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--scoped-inc", nargs=2, action="append", default=[], metavar=("IN", "OUT"),
                    help="rewrite rect21 scoped rows of held keys")
    ap.add_argument("--hold-keys", type=Path, help="per-room selection manifest: hold these chains at their base")
    ap.add_argument("--original-pack", type=Path,
                    help="a held key that this (release) pack also carries gets that member back byte for byte (its "
                         "original representation, e.g. a converted PAL8 that needs an aligned palette block)")
    a = ap.parse_args()
    pack = a.pack.read_bytes()
    texpack.verify(pack)
    packages = read_pak(pack)
    hold = read_hold(a.hold_keys) if a.hold_keys else set()
    _init_hold(hold)
    with multiprocessing.Pool(a.jobs, initializer=_init_hold, initargs=(hold,)) as pool:
        results = [r for r in pool.imap_unordered(audit, sorted(packages.items()), chunksize=8) if r]
    results.sort(key=lambda r: r[0])
    new = dict(packages)
    original = {}
    if a.original_pack:
        opack = a.original_pack.read_bytes()
        texpack.verify(opack)
        original = read_pak(opack)
    restored = 0
    for key, row, held in results:
        if held is not None:
            if key in original:
                new[key] = original[key]
                row["restored_original"] = True
                restored += 1
            else:
                new[key] = held
    with a.tsv.open("w") as f:
        f.write("key\tformat\tside\talpha\tbase_coverage\tworst_coverage_delta\tworst_rgb_rmse\tworst_mean_shift\tverdict\treasons\n")
        for _, r, _ in results:
            chk = [l for l in r["levels"] if l["side"] >= MIN_SIDE]
            cd = max((abs(l["coverage"] - r["base_coverage"]) for l in chk if "coverage" in l), default=0)
            rm = max((l.get("premultiplied_rgb_rmse", 0) for l in chk), default=0)
            ms = max((l.get("mean_shift", 0) for l in chk), default=0)
            f.write(f"{r['key']}\t{r['format']}\t{r['side']}\t{int(r['alpha'])}\t{r['base_coverage']}\t"
                    f"{cd:.4f}\t{rm:.2f}\t{ms:.2f}\t{r['verdict']}\t{','.join(r['reasons']) or '-'}\n")
    counts = {}
    for _, r, _ in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        for reason in r["reasons"]:
            counts["held:" + reason] = counts.get("held:" + reason, 0) + 1
    counts["held:restored-original"] = restored
    summary = dict(source_pack_sha256=hashlib.sha256(pack).hexdigest(), members=len(packages),
                   mipped=len(results), counts=counts,
                   thresholds=dict(alpha_ref=ALPHA_REF, min_side=MIN_SIDE, coverage_rel=COVERAGE_REL, coverage_abs=COVERAGE_ABS,
                                   colour_rmse=COLOUR_RMSE, mean_shift=MEAN_SHIFT))
    if a.out_pack:
        out, n = texpack.build(new)
        texpack.verify(out)
        changed = sorted("%08x-%08x" % k for k in packages if packages[k] != new[k])
        a.out_pack.write_bytes(out)
        summary.update(out_pack_sha256=hashlib.sha256(out).hexdigest(), out_members=n,
                       changed_members=len(changed), out_bytes=len(out))
    held = {k: h for k, r, h in results if h is not None and not r.get("restored_original")}
    summary["scoped_rebound"] = {}
    for src, dst in a.scoped_inc:
        text, n = rebind(Path(src).read_text(), held)
        Path(dst).write_text(text)
        summary["scoped_rebound"][dst] = dict(rows=n, sha256=hashlib.sha256(text.encode()).hexdigest())
    if a.json:
        a.json.write_text(json.dumps(dict(summary=summary, rows=[r for _, r, _ in results]), indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
