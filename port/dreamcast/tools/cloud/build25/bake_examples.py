#!/usr/bin/env python3
"""Write and bake tiny synthetic Leon/em12 mesh/rig examples (no game data)."""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path

import character_light_bake as bake


def fixture(name="leon"):
    """PS2 exchange schema, hand-authored planes; not extracted character art."""
    if name not in ("leon", "em12"):
        raise ValueError("expected leon or em12")
    identity = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]
    bones = [{"id": 0, "parent": -1, "rest": deepcopy(identity), "capture": deepcopy(identity)},
             {"id": 1, "parent": 0, "rest": deepcopy(identity), "capture": deepcopy(identity)}]
    source = {"schema": "re4dc-synthetic-rig-1", "synthetic_fixture": True,
              "name": name, "bones": bones,
              "note": "Hand-authored validation planes, not a PS2 extract or a likeness of the character."}
    source_raw = bake.encoded(source)
    # A small upward-facing receiver below a large roof. Leon's roof uses
    # info 7 to show how the owner excludes alpha hair cards from AO.
    roof_info = 7 if name == "leon" else 1
    positions = [[-1, 0, -1], [1, 0, -1], [0, 0, 1],
                 [-100, 10, -100], [100, 10, -100], [100, 10, 100], [-100, 10, 100]]

    def triangle(info, vertices, normal):
        return {"source_info": info, "corners": [
            {"vertex": vertex, "normal": list(normal), "uv": [float(i == 1), float(i == 2)]}
            for i, vertex in enumerate(vertices)]}

    mesh = {"schema": "re4dc-approved-render-mesh-1", "mesh": f"synthetic-{name}-bindpose",
            "source_sha256": bake.digest(source_raw), "bones": bones,
            "positions_mm": positions,
            "weights": [[[0, 1.0]], [[0, 0.25], [1, 0.75]], [[0, 0.5], [1, 0.5]],
                        [[1, 1.0]], [[1, 1.0]], [[1, 1.0]], [[1, 1.0]]],
            "triangles": [triangle(0, [0, 2, 1], [0, 1, 0]),
                          triangle(roof_info, [3, 4, 5], [0, -1, 0]),
                          triangle(roof_info, [3, 5, 6], [0, -1, 0])],
            "policy": "Synthetic fixture of the PS2 converter exchange schema; no game asset."}
    # Authored RGB and alpha must remain independent; the bake may change RGB
    # but the pack adapter must carry this alpha 93 without replacement.
    mesh["triangles"][0]["corners"][0]["colour_rgba8"] = [200, 150, 100, 93]
    settings = dict(bake.DEFAULT_SETTINGS)
    settings["ambient_rgb"] = [0.5, 0.45, 0.4]
    settings["directional_lights"] = [{"toward_light": [0, 1, 0], "rgb": [0.5, 0.55, 0.6]}]
    settings["exclude_occluder_infos"] = [7] if name == "leon" else []
    return bake.encoded(mesh), source_raw, bake.encoded(settings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    for name in ("leon", "em12"):
        mesh, source, settings = fixture(name)
        folder = args.output / name
        folder.mkdir()
        for file_name, data in (("mesh.json", mesh), ("source.json", source), ("settings.json", settings)):
            (folder / file_name).write_bytes(data)
        baked = folder / "baked"
        baked.mkdir()
        for file_name, data in bake.bake(mesh, source, settings).items():
            (baked / file_name).write_bytes(data)
        report = bake.verify_dataset(baked)
        print(f"{name}: PASS, {report['corners']} corners, {report['palette_colours']} palette colours, "
              f"AO={report['ao_range']}, synthetic only")


if __name__ == "__main__":
    main()
