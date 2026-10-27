#!/usr/bin/env python3
"""Prepare one fresh, private arm from the pinned disc tree using hard links.

Only its render mesh and strip-group sidecar may change. Whole policy, IDs,
texture classification and room data must remain identical to the reference.
Disc mastering subsequently checks every staged file against the reference
manifest, allowing only those two data paths plus the matched diagnostic binary.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    if out.exists() or source == out or source in out.parents or out in source.parents:
        parser.error("Source and a fresh output must be disjoint")
    relative = Path("dc/native/r101")
    fixed = ("ps2-world.r4pw", "ps2-world.ids", "ps2-world.r4tc", "room.r4rc")
    changed = ("ps2-world.re4mesh", "ps2-world.r4sg")
    candidate = args.candidate.resolve() if args.candidate else None
    if candidate:
        for name in fixed:
            if sha(candidate / name) != sha(source / relative / name):
                raise ValueError("Candidate changed fixed policy/ownership/room input: " + name)
        for name in changed:
            if not (candidate / name).is_file():
                raise ValueError("Candidate file missing: " + name)
    shutil.copytree(source, out, copy_function=os.link)
    replacements = {}
    for name in changed if candidate else ():
        target = out / relative / name
        # Unlink this new arm's link before writing. Its baseline inode is shared.
        target.unlink()
        shutil.copyfile(candidate / name, target)
        replacements[(relative / name).as_posix()] = {"sha256": sha(target), "size": target.stat().st_size}
    for name in fixed:
        if sha(out / relative / name) != sha(source / relative / name):
            raise AssertionError("Fixed file changed after preparation")
    receipt = {"source": str(source), "out": str(out), "candidate": str(candidate) if candidate else None,
               "replacements": replacements, "scope": "private input preparation only; mastering and runtime gates pending"}
    # Keep metadata beside the tree: it is not game data to be mastered.
    record = out.with_name(out.name + "-preparation.json")
    with record.open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
