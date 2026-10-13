#!/usr/bin/env python3
"""Prepare source-selected room material pairs without modifying fixtures or packs.

Discover exact BIN/TPL bindings in ITM tables, local SMD placements and EFF
models. Top-level bindings require an explicit archive-index pair and a source
code witness. Runtime pair-missing lines add further exact observed bindings.
Unknown external/common/named-model bindings remain explicit coverage gaps.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile
import struct
import sys

import prepare_native_ui as native
from convert_tpl import parse_tpl
from fit_ps2_world_textures import metadata, sha, sha_bytes, write_json, world_registry
from room_smd import CONTAINER_MAGIC, decode_das, tagged_entries

PAIR_LINE = re.compile(r"native UI: pair missing ([0-9a-f]{8}-[0-9a-f]{8}) color=([0-9a-f]{8}-[0-9a-f]{8}) mask=([0-9a-f]{8}-[0-9a-f]{8}) (\d+)x(\d+)")
ENTER = re.compile(r"warp: room enter ([0-9a-fA-F]+)\b")


def u32(blob, at):
    if at < 0 or at + 4 > len(blob):
        raise ValueError("word outside source resource")
    return struct.unpack_from(">I", blob, at)[0]


def bounded(blob, start, end):
    if start < 0 or end <= start or end > len(blob):
        raise ValueError("resource outside source container")
    return blob[start:end]


def offset_table(blob, base, count=None, limit=None):
    limit = len(blob) if limit is None else limit
    explicit_count = count is not None
    if count is None:
        count = u32(blob, base)
    head = 0 if explicit_count else 4
    if count < 0 or count > 65536 or base + head + 4 * count > limit:
        raise ValueError("invalid source offset table")
    starts = [base + u32(blob, base + head + 4 * i) for i in range(count)]
    minimum = base + head + 4 * count
    if any(x < minimum or x >= limit for x in starts):
        raise ValueError("source resource overlaps table or exceeds region")
    cuts = sorted(set(starts + [limit]))
    return [bounded(blob, start, next(x for x in cuts if x > start)) for start in starts]


def material_indices(blob):
    """Bounded source ModelData part headers; geometry and indices are unchanged."""
    if len(blob) < 64 or u32(blob, 60) not in (0x20010801, 0x20030818):
        raise ValueError("unsupported source ModelData")
    count = struct.unpack_from(">H", blob, 26)[0]
    cursor = u32(blob, 28)
    if count and cursor < 64:
        raise ValueError("part list overlaps ModelData header")
    found = []
    for part in range(count):
        header = bounded(blob, cursor, cursor + 32)
        end = cursor + 32 + u32(header, 24)
        bounded(blob, cursor, end)
        flags, color, mask = header[11], header[12], header[14]
        if flags & 4:
            found.append((part, color, mask))
        cursor = end
    return found


class Scanner:
    def __init__(self):
        self.pairs = {}
        self.gaps = []
        self.bindings = 0

    def add(self, color, mask, evidence, dimensions=None):
        key = native.material_pair_identity(color, mask)
        old = self.pairs.setdefault(key, dict(key=key, color=color, mask=mask,
                                             dimensions=dimensions, evidence=[]))
        if (old["color"], old["mask"]) != (color, mask):
            raise ValueError("pair identity collision")
        if old["dimensions"] and dimensions and old["dimensions"] != dimensions:
            raise ValueError("pair dimensions disagree")
        if dimensions:
            old["dimensions"] = dimensions
        old["evidence"].append(evidence)

    def bind(self, model, palette, context):
        images = parse_tpl(palette)
        self.bindings += 1
        for part, color, mask in material_indices(model):
            if color >= len(images) or mask >= len(images):
                raise ValueError(context + ": material index outside selected TPL")
            c, m = images[color], images[mask]
            if (c.width, c.height) != (m.width, m.height):
                raise ValueError(context + ": separate mask dimensions differ")
            ck, _ = native.image_identity(c)
            mk, _ = native.image_identity(m)
            self.add(ck, mk, dict(kind="source_binding", context=context,
                     part=part, color_image=color, mask_image=mask),
                     [c.width, c.height])

    def itm(self, blob, context):
        if u32(blob, 0) != 3:
            raise ValueError(context + ": unsupported ITM version")
        ids, models, palettes = [u32(blob, x) for x in (4, 8, 12)]
        bases = sorted([ids, models, palettes])
        if len(set(bases)) != 3 or bases[0] < 16:
            raise ValueError("invalid ITM resource tables")
        limits = dict(zip(bases, bases[1:] + [len(blob)]))
        count = u32(blob, ids)
        if ids + 4 + 8 * count > limits[ids]:
            raise ValueError("ITM identity table exceeds region")
        if u32(blob, models) != count or u32(blob, palettes) != count:
            raise ValueError("ITM resource counts disagree")
        bins = offset_table(blob, models, limit=limits[models])
        tpls = offset_table(blob, palettes, limit=limits[palettes])
        for i, (model, palette) in enumerate(zip(bins, tpls)):
            ident = struct.unpack_from(">H", blob, ids + 4 + i * 8)[0]
            self.bind(model, palette, context + "/item%d/id%02x" % (i, ident))

    def smd(self, blob, context):
        if len(blob) < 16:
            raise ValueError("truncated SMD")
        count = struct.unpack_from(">H", blob, 2)[0]
        bt, tt, mt = [u32(blob, x) for x in (4, 8, 12)]
        work = 20 + 4 * u32(blob, 16) if blob[1] & 1 else 16
        if work + 72 * count > len(blob):
            raise ValueError("SMD placement table exceeds resource")
        refs = set()
        common = 0
        for i in range(count):
            p = work + 72 * i
            b, t = blob[p + 36:p + 38]
            flags = u32(blob, p + 68)
            if flags & 0x10:
                common += 1
            elif b != 255 and t != 255:
                refs.add((b, t))
        if common:
            self.gaps.append(dict(context=context, reason="common SMD bindings external", records=common))
        if not refs:
            return
        tables = [x for x in (bt, tt, mt) if x]
        def limit(base):
            return min([x for x in tables if x > base] + [len(blob)])
        bins = offset_table(blob, bt, max(b for b, _ in refs) + 1, limit(bt))
        tpls = offset_table(blob, tt, max(t for _, t in refs) + 1, limit(tt))
        for b, t in sorted(refs):
            self.bind(bins[b], tpls[t], context + "/BIN%d:TPL%d" % (b, t))

    def eff(self, blob, context):
        if u32(blob, 0) != 11:
            raise ValueError("unsupported EFF version")
        headers = [u32(blob, i * 4) for i in range(12)]
        ids, table = headers[5], headers[11]
        if not ids or not u32(blob, ids):
            return
        if not table:
            raise ValueError("EFF model table missing")
        entries = offset_table(blob, table)
        if len(entries) != u32(blob, ids):
            raise ValueError("EFF model counts disagree")
        for i, entry in enumerate(entries):
            offsets = [u32(entry, x) for x in (4, 8, 12, 16)]
            model, palette = offsets[:2]
            if not model or not palette:
                raise ValueError("EFF model or TPL missing")
            cuts = sorted(set([x for x in offsets if x] + [len(entry)]))
            self.bind(bounded(entry, model, next(x for x in cuts if x > model)),
                      bounded(entry, palette, next(x for x in cuts if x > palette)),
                      context + "/efm%d" % i)

    def etm(self, blob, context):
        cursor = 32
        unbound = []
        for _ in range(u32(blob, 0)):
            size = u32(blob, cursor)
            if size < 64:
                raise ValueError("ETM member smaller than header")
            entry = bounded(blob, cursor, cursor + size)
            name = entry[32:64].split(b"\0", 1)[0].decode("ascii")
            if name.endswith(".eff"):
                self.eff(entry[64:], context + "/" + name)
            elif name.endswith(".bin"):
                if material_indices(entry[64:]):
                    unbound.append(name)
            cursor += size
        if unbound:
            self.gaps.append(dict(context=context, reason="named ETM BIN/TPL selection requires source or runtime witness", models=unbound))

    def archive(self, blob, context, top_bindings=()):
        entries = tagged_entries(blob, ">")
        handlers = {b"ITM\0": self.itm, b"SMD\0": self.smd,
                    b"EFF\0": self.eff, b"ETM\0": self.etm}
        for i, (tag, start, end) in enumerate(entries):
            if tag in handlers:
                handlers[tag](bounded(blob, start, end), context + "#%d" % i)
            elif tag == b"BIN\0" and material_indices(bounded(blob, start, end)):
                if not any(b == i for b, _ in top_bindings):
                    self.gaps.append(dict(context=context + "#%d" % i,
                        reason="top-level masked BIN needs explicit source BIN/TPL binding"))
        for b, t in top_bindings:
            if not (0 <= b < len(entries) and 0 <= t < len(entries)):
                raise ValueError("top-level binding outside archive")
            if entries[b][0] != b"BIN\0" or entries[t][0] != b"TPL\0":
                raise ValueError("top-level binding tags are not BIN/TPL")
            self.bind(bounded(blob, *entries[b][1:]), bounded(blob, *entries[t][1:]),
                      context + "#%d:#%d" % (b, t))

    def logs(self, paths, room):
        for path in paths:
            active = None
            for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
                enter = ENTER.search(line)
                if enter:
                    active = int(enter[1], 16)
                match = PAIR_LINE.search(line)
                if not match or active != int(room[1:], 16):
                    continue
                key, color, mask, width, height = match.groups()
                if native.material_pair_identity(color, mask) != key:
                    raise ValueError("logged pair identity mismatch")
                self.add(color, mask, dict(kind="runtime_missing_pair", path=str(path),
                         line=number, text=line), [int(width), int(height)])


def select_missing(rows, fixture_path, room=None):
    """Preserve existing valid winners; emit only dependencies with no winner."""
    sys.path.insert(0, str(Path(__file__).resolve().parent / "d367"))
    import texpack
    fixture_bytes = fixture_path.read_bytes()
    fixture = json.loads(fixture_bytes)
    fixture_room = fixture.get("provenance", {}).get("cx_room", {}).get("room")
    if fixture_room is None:
        fixture_room = fixture.get("cx_room", {}).get("room")
    if room is not None and fixture_room != room:
        raise ValueError("fixture room differs from source room")
    path = Path(fixture["replace"]["dc/tex.pak"])
    if "dc/tex.pak" in fixture.get("remove", []):
        raise ValueError("fixture removes its texture pack")
    before = path.stat()
    blob = path.read_bytes()
    count, _ = texpack.verify(blob)
    index = {"%08x-%08x" % struct.unpack_from("<2I", blob, 2048 + i * 16):
             struct.unpack_from("<2I", blob, 2048 + i * 16 + 8) for i in range(count)}
    replace, selections = {}, []
    for row in rows:
        dp, key = row["disc_path"], row["key"]
        member = index.get(key)
        selected = None
        origin = None
        if member:
            off, size = member
            selected = blob[off:off + size]
            origin = "pack"
        elif dp in fixture["replace"] and dp not in fixture.get("remove", []):
            selected = Path(fixture["replace"][dp]).read_bytes()
            origin = "loose"
        record = dict(key=key, existing_origin=origin)
        if selected is None:
            replace[dp] = row["chosen"]["path"]
            record["status"] = "MISSING_PREPARED"
        else:
            chosen = row["chosen"]
            why, _ = world_registry.tex_package_error(selected, chosen["width"], chosen["height"])
            if why:
                raise ValueError("existing winning package invalid %s: %s" % (key, why))
            record.update(status="EXISTING_VALID_PACKAGE_UNCHANGED",
                          selected_sha256=sha_bytes(selected),
                          render_equal=selected[112:] == Path(chosen["path"]).read_bytes()[112:])
        selections.append(record)
    after = path.stat()
    if fixture_path.read_bytes() != fixture_bytes or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("fixture or pack changed during audit")
    return replace, dict(fixture=str(fixture_path.resolve()), fixture_sha256=sha_bytes(fixture_bytes),
                        pack=str(path), pack_sha256=sha_bytes(blob), selections=selections,
                        note="Existing valid packages kept without claiming equivalence when render_equal is false.")


def prepare(source_root, file, room, output, logs=(), top_bindings=(), binding_sources=(), fixture=None, extra_files=()):
    rel = Path(file)
    if rel.is_absolute() or ".." in rel.parts or not re.fullmatch(r"r[0-9a-f]{3}", room):
        raise ValueError("invalid source file or room")
    if top_bindings and not binding_sources:
        raise ValueError("top-level bindings require --binding-source code witness")
    source = source_root / rel
    before = sha(source)
    blob = source.read_bytes()
    arc = decode_das(blob) if blob.startswith(CONTAINER_MAGIC) else blob
    scanner = Scanner()
    scanner.archive(arc, file, top_bindings)
    scanner.logs(logs, room)
    output.mkdir(parents=True, exist_ok=False)
    pairs = sorted(scanner.pairs.values(), key=lambda row: row["key"])
    sources = {file: source}
    for name, path in extra_files:
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or name in sources:
            raise ValueError("invalid or duplicate extra source alias")
        sources[name] = Path(path)
    source_pins = {name: dict(path=str(path.resolve()), sha256=sha(path)) for name, path in sources.items()}
    if extra_files and pairs:
        with tempfile.TemporaryDirectory(prefix="re4dc-pairs-") as temp:
            combined = Path(temp)
            for name, path in sources.items():
                target = combined / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
            reports = native.prepare_model_pairs(combined, list(sources), pairs, output / "pairs")
    else:
        reports = native.prepare_model_pairs(source_root, [file], pairs, output / "pairs") if pairs else []
    if any(sha(sources[name]) != pin["sha256"] for name, pin in source_pins.items()):
        raise ValueError("source archive changed during generation")
    rows = []
    for generated in reports:
        request = scanner.pairs[generated["key"]]
        package = metadata(output / "pairs" / (generated["key"] + ".re4tex"))
        if [package["width"], package["height"]] != request["dimensions"]:
            raise ValueError("generated pair dimensions disagree with source/log")
        rows.append(dict(**generated, chosen=package, evidence=request["evidence"],
                         disc_path="dc/tex/%s/%s.re4tex" % (generated["key"][0], generated["key"])))
    if sha(source) != before:
        raise ValueError("source archive changed during generation")
    report = dict(schema="re4dc-composite-pair-staging/2", room=room,
        source=dict(path=str(source.resolve()), sha256=before, bytes=len(blob)),
        source_archives=source_pins,
        binding_sources=[dict(path=str(p.resolve()), sha256=sha(p)) for p in binding_sources],
        logs=[dict(path=str(p.resolve()), sha256=sha(p)) for p in logs],
        replace={row["disc_path"]:row["chosen"]["path"] for row in rows},
        pairs=rows, bindings_scanned=scanner.bindings, coverage_gaps=scanner.gaps,
        coverage="SUPPORTED_ROOM_BINDINGS_SCANNED; remaining bindings explicit, not universal scene completeness",
        coverage_exclusions=["External actor/core/weapon archives are image sources only when explicitly supplied; their model bindings are not statically scanned.",
                             "Cross-file/common SMD and named/top-level model bindings require a source or runtime witness.",
                             "Runtime palette changes, dynamically selected resources, and room/view paths not observed are not universal coverage."],
        package_validation="PASS" if all(row["chosen"]["runtime_parser"] == "PASS" for row in rows) else "FAIL",
        source_tool_sha256=sha(Path(native.__file__)),
        helper_sha256=sha(Path(__file__)),
        scope="Source-selected GC material composites. Not a PS2 provenance claim. No fixture or pack edits.",
        acceptance="STATIC_PACKAGE_VALIDATION_ONLY; selected pack/loose bytes and runtime TEX_CHECK still required")
    if fixture:
        report["replace"], report["fixture_selection"] = select_missing(rows, fixture, room)
    write_json(output / "supplemental-staging.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--room", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path, action="append", default=[])
    parser.add_argument("--fixture", type=Path, help="Only supplement pairs missing from this exact pack/loose selection")
    parser.add_argument("--extra-file", action="append", default=[], help="RELATIVE=ABSOLUTE source archive for observed external pairs")
    parser.add_argument("--top-binding", action="append", default=[], help="zero-based BIN:TPL archive indices")
    parser.add_argument("--binding-source", type=Path, action="append", default=[], help="source code witness for explicit bindings")
    args = parser.parse_args(argv)
    bindings = [tuple(int(x, 0) for x in item.split(":")) for item in args.top_binding]
    if any(len(x) != 2 for x in bindings):
        parser.error("--top-binding requires BIN:TPL")
    report = prepare(args.source_root, args.file, args.room, args.output,
                     args.log, bindings, args.binding_source, args.fixture,
                     [(name, Path(path)) for name, path in (item.split("=", 1) for item in args.extra_file)])
    print("%s: %d pairs, %d explicit bindings, %d room binding gaps (scope exclusions apply) -> %s" %
          (args.room, len(report["pairs"]), report["bindings_scanned"],
           len(report["coverage_gaps"]), args.output / "supplemental-staging.json"))
    return 0 if report["package_validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
