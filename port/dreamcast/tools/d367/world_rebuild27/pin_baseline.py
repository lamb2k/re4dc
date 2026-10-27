#!/usr/bin/env python3
"""Pin the actual disc's full file identities and extract only the r101 inputs.

Private outputs are not suitable for Git. This changes neither source nor media.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess


def digest_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reference-manifest", type=Path)
    args = parser.parse_args()
    repo, track, out = args.repo.resolve(), args.track.resolve(), args.out.resolve()
    if out == repo or repo in out.parents:
        parser.error("Private output must be outside the code checkout")
    if out.exists():
        parser.error("Output already exists; preserve it and select a fresh directory")
    code = repo / "port/dreamcast/tools/d367/fullplay/fp_iso.py"
    spec = importlib.util.spec_from_file_location("fp_iso", code)
    iso = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(iso)
    tr = iso.Track(str(track), 45000)
    entries = iso.files(tr)
    names = [entry[0].lstrip("/") for entry in entries]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate disc file paths")
    out.mkdir(parents=True)
    full, extracted = {}, {}
    try:
        for name, extent, size in sorted(entries):
            relative = Path(name.lstrip("/"))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe disc path: " + name)
            data = tr.read_bytes(extent, size) if size else b""
            identity = {"size": size, "sha256": hashlib.sha256(data).hexdigest()}
            full[relative.as_posix()] = identity
            if relative.as_posix().startswith("dc/native/r101/") or relative.as_posix() == "1ST_READ.BIN":
                target = out / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write(data)
                if digest_file(target) != identity["sha256"]:
                    raise ValueError("Extracted data readback mismatch: " + name)
                extracted[relative.as_posix()] = identity
        if not any(name.startswith("dc/native/r101/") for name in extracted):
            raise ValueError("No actual r101 native files on this disc")
        reference = None
        if args.reference_manifest:
            expected = json.loads(args.reference_manifest.read_text())
            changed = [key for key in sorted(set(expected) | set(full)) if expected.get(key) != full.get(key)]
            if changed:
                raise ValueError("Disc differs from its reference manifest: " + repr(changed[:12]))
            reference = {"path": str(args.reference_manifest.resolve()), "sha256": digest_file(args.reference_manifest), "identical_files": len(full)}
        (out / "IP.BIN").write_bytes(tr.read(tr.base, 16))
        (out / "disc-files.json").write_text(json.dumps(full, indent=2, sort_keys=True) + "\n")
        recipe = repo / "port/dreamcast/tools/d367/rr/recipe.conf"
        packet = {
            "kind": "actual-disc-baseline-identity-only", "arm": "A", "room": "r101",
            "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source": {"repo": str(repo), "head": git(repo, "rev-parse", "HEAD"),
                       "dirty": git(repo, "status", "--porcelain"),
                       "recipe_sha256": digest_file(recipe), "reader_sha256": digest_file(code)},
            "track": {"path": str(track), "size": track.stat().st_size, "sha256": digest_file(track)},
            "manifest": {"sha256": digest_file(out / "disc-files.json"), "files": len(full)},
            "reference": reference, "extracted": extracted,
            "acceptance": {"source_identity": True, "target_run": False, "timing": False, "physical_console": False},
        }
        (out / "BASELINE.json").write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n")
        local = [p for p in out.rglob("*") if p.is_file()]
        (out / "SHA256SUMS").write_text("".join(digest_file(p) + "  " + p.relative_to(out).as_posix() + "\n" for p in sorted(local)))
        print(json.dumps({"out": str(out), "files": len(full), "extracted": extracted, "track_sha256": packet["track"]["sha256"]}, indent=2))
    finally:
        tr.f.close()


if __name__ == "__main__":
    main()