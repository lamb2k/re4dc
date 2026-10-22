#!/usr/bin/env python3
"""Private room-selected mip candidate from an exact retained release input.

Reads only tex.pak and the named world sidecar. Never changes the source disc.
No image mastering, staging, runtime defaults, gameplay or release actions.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import re
import struct
import sys

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "d367"))
import mipmap_vq as mip
import mipmap_twiddled as twiddled
import texpack
from fullplay import fp_iso
from vram.vq_pak import read_pak


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def rounded(n, alignment):
    return (n + alignment - 1) // alignment * alignment


def world_keys(blob):
    if len(blob) < 32:
        raise ValueError("world sidecar header is truncated")
    magic, version, _, count, _, _, _, _ = struct.unpack_from("<4s7I", blob)
    if magic != b"R4PW" or version != 1 or 32 + count * 16 > len(blob):
        raise ValueError("unsupported world sidecar or truncated parts")
    return {(a, b) for a, b, *_ in
            struct.iter_unpack("<IIHH4B", blob[32:32 + count * 16])}


def world_map(world):
    if isinstance(world, (bytes, bytearray)):
        return {"selected": world}
    if not isinstance(world, dict) or not world:
        raise ValueError("expected a named world-sidecar map")
    return world


def referenced_keys(world):
    return set().union(*(world_keys(b) for b in world_map(world).values()))


def select(pack, world, *, include_twiddled=False):
    texpack.verify(pack)
    packages = read_pak(pack)
    rebuilt, _ = texpack.build(packages)
    if rebuilt != pack:
        raise ValueError("source pack is not byte-identical to canonical texpack.build")
    missing, supported, refused = [], [], []
    for key in sorted(referenced_keys(world)):
        name = "%08x-%08x" % key
        if key not in packages:
            missing.append(name)
            continue
        try:
            native = mip.read_native_vq(packages[key])
        except ValueError as error:
            if include_twiddled:
                try:
                    native = twiddled.read_native_twiddled(packages[key])
                except ValueError as other:
                    refused.append(dict(key=name, reason=str(error), twiddled_reason=str(other)))
                else:
                    supported.append((key, native))
            else:
                refused.append(dict(key=name, reason=str(error)))
        else:
            supported.append((key, native))
    if missing:
        raise ValueError("world keys absent from normal packed winner namespace: " + ", ".join(missing))
    return packages, supported, refused


def build_candidate(pack, world, *, enabled=False, engine="auto", progress=None,
                    include_twiddled=False):
    packages, supported, refused = select(pack, world, include_twiddled=include_twiddled)
    new = dict(packages)
    rows = []
    for done, (key, before) in enumerate(supported, 1):
        generator = twiddled if before.texture[7] == 1 else mip
        after_blob, row = generator.add_mipmaps(packages[key], enabled=enabled, engine=engine)
        after = (twiddled.read_native_twiddled(after_blob) if generator is twiddled
                 else mip.read_native_vq(after_blob))
        row.update(key="%08x-%08x" % key, layout=before.texture[7],
                   before_alloc32=rounded(len(before.payload), 32),
                   after_alloc32=rounded(len(after.payload), 32),
                   before_archive_slot=rounded(len(packages[key]), 2048),
                   after_archive_slot=rounded(len(after_blob), 2048))
        # Independent of generated lower levels: preserve exact decoded base RGBA.
        if generator.decode_level(before, before.size) != generator.decode_level(after, after.size):
            raise ValueError("decoded source base changed for " + row["key"])
        new[key] = after_blob
        rows.append(row)
        if progress and (done % 32 == 0 or done == len(supported)):
            progress(done, len(supported))
    candidate, count = texpack.build(new)
    texpack.verify(candidate)
    changed = {k for k in packages if packages[k] != new[k]}
    # Selected packages may change two ways: a generated chain (inputs without mips),
    # or a checksum-only normalization of an already-mipmapped legacy-CRC input
    # (the exporters emit the canonical full-body CRC). Nothing else may change, and a
    # disabled build is byte-identical.
    selected = {k for k, _ in supported} if enabled else set()
    grown = {k for k, native in supported if enabled and not native.mipmapped}
    normalized = changed - grown
    if (not changed <= selected or not grown <= changed or
            any(new[k] != mip.tpl.canonical_native_crc(packages[k]) for k in normalized) or
            (not enabled and (changed or candidate != pack))):
        raise ValueError("candidate changed an unselected package or disabled output")
    report = dict(
        schema="re4dc-world-mipmap-candidate-1", candidate_only=True, enabled=bool(enabled),
        source_pack_sha256=sha(pack), candidate_pack_sha256=sha(candidate),
        source_pack_bytes=len(pack), candidate_pack_bytes=len(candidate),
        archive_extra_bytes=len(candidate) - len(pack), packages=count,
        world_keys=len(referenced_keys(world)), compatible_keys=len(supported),
        changed_keys=len(changed), unchanged_keys=count - len(changed),
        checksum_normalized_keys=len(normalized),
        default_off_pack_exact=True,
        extra_payload_bytes=sum(r["extra_payload_bytes"] for r in rows),
        extra_alloc32_bytes=sum(r["after_alloc32"] - r["before_alloc32"] for r in rows),
        compatible=rows, other_formats=refused, include_twiddled=bool(include_twiddled),
        required_build_knobs=(["CAST_MIPMAP=1"] +
            (["TEX_TWIDDLED_MIPMAP=1"] if include_twiddled else [])) if enabled else [],
        limitations=[
            "Pack keys are global; shared keys change wherever this candidate pack is used.",
            "World references are not proof that every key draws in the selected camera.",
            "Allocation sums are request sizes, not measured peak or contiguous VRAM.",
            "No gameplay, frame time, rendered look, release or hardware acceptance.",
        ])
    by_key = {r["key"]: r for r in rows}
    report["per_room"] = {}
    for name, sidecar in sorted(world_map(world).items()):
        keys = world_keys(sidecar)
        compatible = [by_key["%08x-%08x" % k] for k in sorted(keys)
                      if "%08x-%08x" % k in by_key]
        report["per_room"][name] = dict(
            world_keys=len(keys), compatible_keys=len(compatible),
            changed_keys=sum(r["changed"] for r in compatible),
            before_payload_bytes=sum(r["before_payload_bytes"] for r in compatible),
            after_payload_bytes=sum(r["after_payload_bytes"] for r in compatible),
            extra_payload_bytes=sum(r["extra_payload_bytes"] for r in compatible),
            before_alloc32_bytes=sum(r["before_alloc32"] for r in compatible),
            after_alloc32_bytes=sum(r["after_alloc32"] for r in compatible),
            extra_alloc32_bytes=sum(r["after_alloc32"]-r["before_alloc32"] for r in compatible),
            compatible_key_names=[r["key"] for r in compatible])
    report["per_room_sum_caution"] = (
        "Per-room eligible-key inventory sums, not simultaneous live residency or measured peaks; "
        "shared keys overlap rooms and must not be added as a global working set.")
    return candidate, report, packages, new


def bound_input(track, files, manifest, path):
    if path not in files or path not in manifest:
        raise ValueError("selected input absent from track or receipt: " + path)
    extent, size = files[path]
    expected = manifest[path]
    if expected["size"] != size:
        raise ValueError("selected input size mismatch: " + path)
    data = track.read_bytes(extent, size)
    if sha(data) != expected["sha256"]:
        raise ValueError("selected input SHA-256 mismatch: " + path)
    return data


def world_paths(manifest, room=None):
    if room is not None:
        return ["dc/native/r%03x/ps2-world.r4pw" % room]
    return sorted(path for path in manifest
                  if re.fullmatch(r"dc/native/r[0-9a-fA-F]{3}/ps2-world[.]r4pw", path))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--track", type=Path, required=True)
    ap.add_argument("--release-manifest", type=Path, required=True)
    selection = ap.add_mutually_exclusive_group(required=True)
    selection.add_argument("--room", type=lambda x: int(x.removeprefix("r"), 16))
    selection.add_argument("--all-worlds", action="store_true",
                           help="all named world sidecars in the bound release manifest")
    ap.add_argument("--progress", action="store_true", help="print bounded offline progress")
    ap.add_argument("--include-twiddled", action="store_true",
                    help="also select square16-bit twiddled keys; requires TEX_TWIDDLED_MIPMAP runtime")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--generate", action="store_true", help="opt in; default creates an exact control")
    ap.add_argument("--engine", choices=("auto", "python", "numpy"), default="auto")
    ap.add_argument("--lba", type=int, default=45000)
    args = ap.parse_args(argv)
    if args.output.exists():
        ap.error("output directory already exists; use a new private candidate path")
    if not args.output.parent.is_dir():
        ap.error("private output parent must already exist")
    receipt = args.release_manifest.read_bytes()
    manifest = json.loads(receipt)
    paths = world_paths(manifest, args.room)
    if not paths:
        raise ValueError("no named world sidecars in release manifest")
    track = fp_iso.Track(str(args.track), args.lba)
    try:
        files = {path.lstrip("/"): (extent, size)
                 for path, extent, size in fp_iso.files(track)}
        pack = bound_input(track, files, manifest, "dc/tex.pak")
        world = {path: bound_input(track, files, manifest, path) for path in paths}
    finally:
        track.f.close()
    if shutil.disk_usage(args.output.parent).free < len(pack) * 3 + 512 * 1024 * 1024:
        raise ValueError("private output volume lacks the bounded candidate headroom")
    progress = (lambda done, total: print("mipmap21: processed %d/%d compatible world keys" %
                (done, total), flush=True)) if args.progress else None
    candidate, report, before, after = build_candidate(
        pack, world, enabled=args.generate, engine=args.engine, progress=progress,
        include_twiddled=args.include_twiddled)
    report.update(
        updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        room="all-worlds" if args.all_worlds else "r%03x" % args.room,
        track=str(args.track), raw_sectors=track.raw, lba=args.lba,
        manifest=str(args.release_manifest), manifest_sha256=sha(receipt),
        world_inputs=[dict(path=path, sha256=sha(blob), size=len(blob))
                      for path, blob in sorted(world.items())],
        tool_sha256=sha(Path(__file__).read_bytes()),
        generator_sha256=sha((TOOLS / "mipmap_vq.py").read_bytes()))
    args.output.mkdir()
    outputs = {}
    def write(path, blob):
        with path.open("xb") as stream:
            stream.write(blob)
        outputs[path.relative_to(args.output).as_posix()] = dict(size=len(blob), sha256=sha(blob))
    write(args.output / "tex.pak", candidate)
    changed = [k for k in before if before[k] != after[k]]
    for label, data in (("source-packages", before), ("mip-packages", after)):
        (args.output / label).mkdir()
        for key in changed:
            write(args.output / label / ("%08x-%08x.re4tex" % key), data[key])
    # All archive member identities, including those untouched by this selection.
    report["members"] = [
        dict(key="%08x-%08x" % key, before_sha256=sha(before[key]),
             after_sha256=sha(after[key]), changed=before[key] != after[key])
        for key in sorted(before)]
    write(args.output / "candidate.json", (json.dumps(report, indent=2) + "\n").encode())
    write(args.output / "outputs.json", (json.dumps(outputs, indent=2) + "\n").encode())
    sums = "".join("%s  %s\n" % (v["sha256"], p) for p, v in sorted(outputs.items()))
    with (args.output / "SHA256SUMS").open("x", encoding="ascii") as stream:
        stream.write(sums)
    print(json.dumps({k: report[k] for k in (
        "room", "enabled", "compatible_keys", "changed_keys", "unchanged_keys",
        "extra_payload_bytes", "extra_alloc32_bytes", "archive_extra_bytes",
        "candidate_pack_sha256")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
