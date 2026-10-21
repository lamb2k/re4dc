#!/usr/bin/env python3
"""Private, receipt-bound pack candidate for explicitly selected lossless VQ keys.

No disc extraction, source disc mutation, game build or runtime/default change.
Selection policy and source-owner evidence are separate from format feasibility.
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
import shutil
import sys

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "d367"))
import compact_native_vq as compact
import texpack
from fullplay import fp_iso
from vram.vq_pak import read_pak
from world_candidate import bound_input, rounded, sha


def build_candidate(pack, selection, *, enabled=False):
    texpack.verify(pack)
    before = read_pak(pack)
    if texpack.build(before)[0] != pack:
        raise ValueError("source pack does not have a byte-exact canonical control")
    if selection.get("schema") != "re4dc-lossless-vq-selection-1" or selection.get("source_pack_sha256") != sha(pack):
        raise ValueError("selection is not bound to this source pack")
    rows, keys = [], set()
    after = dict(before)
    for proof in selection.get("keys", []):
        name = proof["key"]
        try:
            c, f = name.split("-")
            key = (int(c, 16), int(f, 16))
        except (ValueError, AttributeError):
            raise ValueError("invalid selected native key") from None
        if len(c) != 8 or len(f) != 8 or key in keys or key not in before:
            raise ValueError("duplicate, malformed or absent selected key: " + name)
        keys.add(key)
        if sha(before[key]) != proof["package_sha256"] or not proof.get("owner_evidence"):
            raise ValueError("selected package hash or explicit owner evidence is missing: " + name)
        after[key], row = compact.compact(before[key], enabled=enabled)
        if enabled and not row["changed"]:
            raise ValueError("selected key is not a smaller lossless VQ candidate: " + name)
        row.update(key=name, owner_evidence=proof["owner_evidence"],
            before_archive_slot=rounded(len(before[key]), 2048),
            after_archive_slot=rounded(len(after[key]), 2048))
        rows.append(row)
    if not keys:
        raise ValueError("empty selection")
    candidate, count = texpack.build(after)
    texpack.verify(candidate)
    changed = {k for k in before if before[k] != after[k]}
    if changed != (keys if enabled else set()) or (not enabled and candidate != pack):
        raise ValueError("unselected member changed or disabled output differs")
    report = dict(schema="re4dc-lossless-vq-candidate-1", candidate_only=True,
        enabled=bool(enabled), source_pack_sha256=sha(pack), candidate_pack_sha256=sha(candidate),
        source_pack_bytes=len(pack), candidate_pack_bytes=len(candidate),
        saved_archive_bytes=len(pack)-len(candidate), packages=count,
        selected_keys=len(keys), changed_keys=len(changed), unchanged_keys=count-len(changed),
        default_off_pack_exact=True, required_runtime_changes=False,
        saved_payload_bytes=sum(r["saved_payload_bytes"] for r in rows),
        saved_alloc32_bytes=sum(r["saved_alloc32_bytes"] for r in rows),
        converted=rows, selection_scope=selection.get("scope"),
        limitations=["Global pack keys are shared wherever referenced.",
            "Payload and 32-byte request inventories are not measured peak VRAM.",
            "No hardware timing, gameplay, release or rendered-look acceptance."],
        members=[dict(key="%08x-%08x" % key, before_sha256=sha(before[key]),
            after_sha256=sha(after[key]), changed=before[key]!=after[key]) for key in sorted(before)])
    return candidate, report, before, after


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--track", type=Path)
    source.add_argument("--source-pack", type=Path,
                        help="exact pack file; must still match the bound release receipt")
    ap.add_argument("--release-manifest", type=Path, required=True)
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--lba", type=int, default=45000)
    args = ap.parse_args(argv)
    if args.output.exists() or not args.output.parent.is_dir():
        ap.error("output must be a new directory under an existing private parent")
    manifest_bytes, selection_bytes = args.release_manifest.read_bytes(), args.selection.read_bytes()
    manifest, selection = json.loads(manifest_bytes), json.loads(selection_bytes)
    if args.source_pack is not None:
        pack = args.source_pack.read_bytes()
        expected = manifest["dc/tex.pak"]
        if len(pack) != expected["size"] or sha(pack) != expected["sha256"]:
            raise ValueError("source pack size/SHA-256 differs from the bound release receipt")
    else:
        track = fp_iso.Track(str(args.track), args.lba)
        try:
            files = {p.lstrip("/"): (o, n) for p, o, n in fp_iso.files(track)}
            pack = bound_input(track, files, manifest, "dc/tex.pak")
        finally:
            track.f.close()
    if shutil.disk_usage(args.output.parent).free < 3*len(pack)+512*1024*1024:
        raise ValueError("insufficient private candidate headroom")
    candidate, report, before, after = build_candidate(pack, selection, enabled=args.generate)
    report.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        track=str(args.track) if args.track is not None else None,
        source_pack_path=str(args.source_pack) if args.source_pack is not None else None,
        raw_sectors=track.raw if args.track is not None else None, lba=args.lba,
        manifest=str(args.release_manifest), manifest_sha256=sha(manifest_bytes),
        selection_sha256=sha(selection_bytes), tool_sha256=sha(Path(__file__).read_bytes()),
        generator_sha256=sha((TOOLS / "compact_native_vq.py").read_bytes()))
    args.output.mkdir()
    outputs = {}
    def write(path, blob):
        with path.open("xb") as f:
            f.write(blob)
        outputs[path.relative_to(args.output).as_posix()] = dict(size=len(blob), sha256=sha(blob))
    write(args.output / "tex.pak", candidate)
    write(args.output / "selection.json", selection_bytes)
    for label, packages in (("source-packages", before), ("vq-packages", after)):
        (args.output / label).mkdir()
        for key in sorted(k for k in before if before[k] != after[k]):
            write(args.output / label / ("%08x-%08x.re4tex" % key), packages[key])
    write(args.output / "candidate.json", (json.dumps(report, indent=2)+"\n").encode())
    write(args.output / "outputs.json", (json.dumps(outputs, indent=2)+"\n").encode())
    (args.output / "SHA256SUMS").write_text("".join(
        "%s  %s\n" % (r["sha256"], p) for p, r in sorted(outputs.items())), encoding="ascii")
    print(json.dumps({k: report[k] for k in ("changed_keys", "unchanged_keys",
        "saved_payload_bytes", "saved_alloc32_bytes", "saved_archive_bytes", "candidate_pack_sha256")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
