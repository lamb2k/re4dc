#!/usr/bin/env python3
"""Opaque-world VQ colour recovery pilot (lane miprecover22, 2026-10-22).

For original base-only RGB565 VQ keys held by the mipfix22 gate for vq-colour, rebuild the mip chain with better
lower-level colours in UNUSED codebook slots (mipmap_compact_vq.add_mipmaps_original), keep every base-referenced
codeword, the base indices and decoded base texels exact, and requalify through 1x1 with the current gate
(mip_quality.audit). Accepted keys go into an add-on pack on top of the input pack; scoped descriptor rows are
rebound to the new descriptors. With no accepted keys the output pack equals the input pack (OFF identity).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "d367"))
sys.path.insert(0, str(TOOLS / "d367" / "mipmap21"))
import mipmap_compact_vq as cvq
import mipmap_vq as vq
import mip_quality as mq
import texpack
from vram.vq_pak import read_pak


def sha(b):
    return hashlib.sha256(b).hexdigest()


def r32(n):
    return (n + 31) // 32 * 32


def key_tuple(s):
    a, b = s.split("-")
    return int(a, 16), int(b, 16)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pack", type=Path, required=True)
    ap.add_argument("--room-select", type=Path, required=True)
    ap.add_argument("--quality-json", type=Path, required=True, help="mipfix22 v2 mip-quality.json (before levels)")
    ap.add_argument("--refs", type=Path, required=True, help="world material refs json.gz (consumers)")
    ap.add_argument("--source-map", type=Path, help="selected36-source-map.json (canonical36 consumers: rooms + refs)")
    ap.add_argument("--candidates", type=Path, default=HERE / "candidates.tsv")
    ap.add_argument("--set", choices=("pilot", "rest", "all"), default="pilot")
    ap.add_argument("--scoped-inc", nargs=2, action="append", default=[], metavar=("IN", "OUT"))
    ap.add_argument("--out-pack", type=Path)
    ap.add_argument("--ledger", type=Path, required=True)
    a = ap.parse_args()

    pack = a.pack.read_bytes()
    texpack.verify(pack)
    members = read_pak(pack)
    holds = mq.read_hold(a.room_select)
    before = {r["key"]: r for r in json.loads(a.quality_json.read_text())["rows"]}
    refs = json.loads(gzip.decompress(a.refs.read_bytes()))
    consumers = {}
    for r in refs:
        consumers.setdefault(r["key"], []).append(r)
    extra = {}
    if a.source_map:
        def walk(o):
            if isinstance(o, dict):
                if "scoped_key" in o and "rooms" in o:
                    extra[o["scoped_key"]] = o
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(json.loads(a.source_map.read_text()))
    rows = []
    for line in a.candidates.read_text().splitlines()[1:]:
        scoped, original, side, pilot = line.split("\t")
        if a.set == "pilot" and pilot != "1" or a.set == "rest" and pilot != "0":
            continue
        rows.append((scoped, original, int(side)))

    ledger, accepted = [], {}
    for scoped, original, side in rows:
        k = key_tuple(scoped)
        blob = members.get(k)
        prev = before.get(scoped, {})
        cons = consumers.get(original, []) + consumers.get(scoped, [])
        rooms = sorted({c["world"].split("/")[2] for c in cons})
        nref = len(cons)
        if scoped in extra:   # canonical36 source map: rooms + ref count, no per-ref rows
            rooms = sorted(set(rooms) | set(extra[scoped]["rooms"]))
            nref += extra[scoped].get("material_refs", 0)
        e = dict(scoped=scoped, original=original, side=side, hold_reason=prev.get("reasons"),
                 before_levels=[(l["side"], l.get("premultiplied_rgb_rmse"), l.get("mean_shift")) for l in prev.get("levels", [])],
                 consumers=dict(material_refs=nref, rooms=rooms,
                                render_pass=sorted({c["render_pass"] for c in cons}),
                                source_dims=sorted({"%dx%d" % (c["width"], c["height"]) for c in cons})),
                 minification_evidence=("opaque PS2 world material (render pass 0) on room geometry in %s; stored %dx%d "
                                        "from %s; per-view texel density not measured offline (room replay = lane mipmap22)"
                                        % (",".join(rooms) or "-", side, side, ",".join(sorted({"%dx%d" % (c["width"], c["height"]) for c in cons})) or "-")))
        e["source_sha256"] = sha(blob) if blob else None
        reject = None
        if blob is None:
            reject = "not in pack"
        elif scoped in holds:
            reject = "deliberate room hold (room-select.tsv)"
        elif not nref:
            reject = "no room/material consumer found (never minified in an active room)"
        native = vq.read_native_vq(blob) if blob else None
        if native is not None:
            used = len(set(native.base_indices))
            e["codebook_used"], e["codebook_free"] = used, 256 - used
            e["source_mipmapped"] = native.mipmapped
            if native.mipmapped:
                reject = reject or "already mipmapped in the input pack"
            if used == 256:
                reject = reject or "full codebook"
        if reject is None:
            off, rep = cvq.add_mipmaps_original(blob, enabled=False)
            assert off == blob, "OFF identity"
            out, rep = cvq.add_mipmaps_original(blob, enabled=True)
            res = mq.audit((k, out))
            _, qrow, _ = res
            e.update(output_sha256=sha(out), spare_vectors_added=rep["spare_vectors_added"],
                     reserved_vectors=rep["reserved_vectors"], unused_slots_changed=rep["unused_slots_changed"],
                     added_payload_bytes=rep["extra_payload_bytes"],
                     added_rounded_bytes=r32(rep["after_payload_bytes"]) - r32(rep["before_payload_bytes"]),
                     after_levels=[(l["side"], l.get("premultiplied_rgb_rmse"), l.get("mean_shift")) for l in qrow["levels"]],
                     gate_reasons=qrow["reasons"])
            # descriptors: everything but the mip flag and payload size unchanged; canonical CRC re-read
            n2 = vq.read_native_vq(out)
            same = (n2.texture[:5] == native.texture[:5] and n2.texture[7:] == native.texture[7:]
                    and n2.header[9:] == native.header[9:] and n2.crc_rule == "header")
            e["descriptors_ok_canonical_crc"] = same
            if qrow["verdict"] == "pass" and same:
                e["decision"] = "accept"
                accepted[k] = out
            else:
                e["decision"] = "hold"
                e["hold_why"] = ",".join(qrow["reasons"]) or "descriptor"
        else:
            e["decision"] = "hold"
            e["hold_why"] = reject
        ledger.append(e)
        print(scoped, e["decision"], e.get("hold_why", ""), e.get("added_rounded_bytes", ""), flush=True)

    summary = dict(input_pack_sha256=sha(pack), room_select_sha256=sha(a.room_select.read_bytes()),
                   quality_json_sha256=sha(a.quality_json.read_bytes()), set=a.set, keys=len(rows),
                   accepted=len(accepted), added_rounded_bytes=sum(e.get("added_rounded_bytes", 0) for e in ledger
                                                                 if e["decision"] == "accept"))
    if a.out_pack:
        new = dict(members)
        new.update(accepted)
        out, n = texpack.build(new)
        texpack.verify(out)
        same, _ = texpack.build(dict(members))
        summary.update(off_identity=sha(same) == sha(pack), out_pack_sha256=sha(out), out_members=n,
                       changed_members=sum(members[x] != new[x] for x in members))
        a.out_pack.write_bytes(out)
    summary["scoped_rebound"] = {}
    for src, dst in a.scoped_inc:
        text, n = mq.rebind(Path(src).read_text(), accepted)
        Path(dst).write_text(text)
        summary["scoped_rebound"][dst] = dict(rows=n, sha256=sha(text.encode()))
    a.ledger.write_text(json.dumps(dict(summary=summary, keys=ledger), indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
