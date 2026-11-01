#!/usr/bin/env python3
"""Stage a checked WP29 cell into an existing matching package fixture.

No game data is copied by this tool. The output references the owner's local
files. Without --barn-portals29=1 it reads and writes nothing.
"""
import argparse
import json
from pathlib import Path
import struct
import sys

import barn_portals29 as B


def graft(fixture, directory, cell_path):
    cell = cell_path.read_bytes()
    summary = B.verify_cell(cell)
    room = summary["room"]
    prefix = f"dc/native/r{room:03x}/"
    replacements = fixture.get("replace")
    B.require(isinstance(replacements, dict), "fixture needs replace mapping")
    normalized = {}
    for key, source in replacements.items():
        B.require(isinstance(key, str) and isinstance(source, str), "fixture replacements must be paths")
        path = Path(source)
        normalized[key] = str(path.resolve() if path.is_absolute() else (directory / path).resolve())
    B.require(all(prefix + name in normalized for name in ("ps2-world.re4mesh", "ps2-world.r4pw")),
              "fixture must explicitly stage both matching mesh and policy")
    mesh = Path(normalized[prefix + "ps2-world.re4mesh"]).read_bytes()
    policy = Path(normalized[prefix + "ps2-world.r4pw"]).read_bytes()
    B.codec().decode(mesh, policy, preserve_index_layout=True)
    B.require((len(mesh), struct.unpack_from("<I", mesh, 12)[0], struct.unpack_from("<I", policy, 20)[0]) ==
              (summary["mesh_bytes"], summary["mesh_crc"], summary["policy_crc"]), "fixture package differs from the WP29 proof")
    cell_key = prefix + "interior.cell"
    normalized[cell_key] = str(cell_path.resolve())
    return dict(fixture, replace=normalized, remove=[key for key in (fixture.get("remove") or []) if key != cell_key])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--barn-portals29", type=int, choices=(0, 1), default=0)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--cell", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if not args.barn_portals29:
        print("barn-portals29=0: no fixture read or written")
        return 0
    if any(v is None for v in (args.fixture, args.cell, args.out)):
        parser.error("enabled graft requires --fixture, --cell and --out")
    try:
        B.require(not args.out.exists(), "output already exists; use a fresh fixture path")
        output = graft(json.loads(args.fixture.read_text()), args.fixture.resolve().parent, args.cell)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(output, indent=2) + "\n")
        print(str(args.out))
        return 0
    except (ValueError, OSError, struct.error, KeyError, TypeError) as exc:
        print("barn-portals29 graft refused: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
