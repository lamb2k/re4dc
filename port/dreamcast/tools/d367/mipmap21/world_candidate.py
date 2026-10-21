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
import struct
import sys

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "d367"))
import mipmap_vq as mip
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


def select(pack, world):
    texpack.verify(pack)
    packages = read_pak(pack)
    rebuilt, _ = texpack.build(packages)
    if rebuilt != pack:
        raise ValueError("source pack is not byte-identical to canonical texpack.build")
    missing, supported, refused = [], [], []
    for key in sorted(world_keys(world)):
        name = "%08x-%08x" % key
        if key not in packages:
            missing.append(name)
            continue
        try:
            native = mip.read_native_vq(packages[key])
        except ValueError as error:
            refused.append(dict(key=name, reason=str(error)))
        else:
            supported.append((key, native))
    if missing:
        raise ValueError("world keys absent from normal packed winner namespace: " + ", ".join(missing))
    return packages, supported, refused


def build_candidate(pack, world, *, enabled=False, engine="auto"):
    packages, supported, refused = select(pack, world)
    new = dict(packages)
    rows = []
    for key, before in supported:
        after_blob, row = mip.add_mipmaps(packages[key], enabled=enabled, engine=engine)
        after = mip.read_native_vq(after_blob)
        row.update(key="%08x-%08x" % key,
                   before_alloc32=rounded(len(before.payload), 32),
                   after_alloc32=rounded(len(after.payload), 32),
                   before_archive_slot=rounded(len(packages[key]), 2048),
                   after_archive_slot=rounded(len(after_blob), 2048))
        # Independent of generated lower levels: preserve exact decoded base RGBA.
        if mip.decode_level(before, before.size) != mip.decode_level(after, after.size):
            raise ValueError("decoded source base changed for " + row["key"])
        new[key] = after_blob
        rows.append(row)
    candidate, count = texpack.build(new)
    texpack.verify(candidate)
    changed = {k for k in packages if packages[k] != new[k]}
    expected = {k for k, _ in supported if mip.read_native_vq(new[k]).mipmapped and enabled
                and not mip.read_native_vq(packages[k]).mipmapped}
    if changed != expected or (not enabled and candidate != pack):
        raise ValueError("candidate changed an unselected package or disabled output")
    report = dict(
        schema="re4dc-world-mipmap-candidate-1", candidate_only=True, enabled=bool(enabled),
        source_pack_sha256=sha(pack), candidate_pack_sha256=sha(candidate),
        source_pack_bytes=len(pack), candidate_pack_bytes=len(candidate),
        archive_extra_bytes=len(candidate) - len(pack), packages=count,
        world_keys=len(world_keys(world)), compatible_keys=len(supported),
        changed_keys=len(changed), unchanged_keys=count - len(changed),
        default_off_pack_exact=True,
        extra_payload_bytes=sum(r["extra_payload_bytes"] for r in rows),
        extra_alloc32_bytes=sum(r["after_alloc32"] - r["before_alloc32"] for r in rows),
        compatible=rows, other_formats=refused,
        limitations=[
            "Pack keys are global; shared keys change wherever this candidate pack is used.",
            "World references are not proof that every key draws in the selected camera.",
            "Allocation sums are request sizes, not measured peak or contiguous VRAM.",
            "No gameplay, frame time, rendered look, release or hardware acceptance.",
        ])
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--track", type=Path, required=True)
    ap.add_argument("--release-manifest", type=Path, required=True)
    ap.add_argument("--room", type=lambda x: int(x.removeprefix("r"), 16), required=True)
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
    sidecar = "dc/native/r%03x/ps2-world.r4pw" % args.room
    track = fp_iso.Track(str(args.track), args.lba)
    try:
        files = {path.lstrip("/"): (extent, size)
                 for path, extent, size in fp_iso.files(track)}
        pack = bound_input(track, files, manifest, "dc/tex.pak")
        world = bound_input(track, files, manifest, sidecar)
    finally:
        track.f.close()
    if shutil.disk_usage(args.output.parent).free < len(pack) * 3 + 512 * 1024 * 1024:
        raise ValueError("private output volume lacks the bounded candidate headroom")
    candidate, report, before, after = build_candidate(
        pack, world, enabled=args.generate, engine=args.engine)
    report.update(
        updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        room="r%03x" % args.room, track=str(args.track), raw_sectors=track.raw, lba=args.lba,
        manifest=str(args.release_manifest), manifest_sha256=sha(receipt),
        world_path=sidecar, world_sha256=sha(world), world_bytes=len(world),
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
