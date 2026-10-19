#!/usr/bin/env python3
"""I009 source-UV-localized static core highlight; user look approval required.

Usage: bake_garrador_core_localized.py <original-core-conversion> <new-directory>
The original full core geometry/UVs are read to localize a colour bake. No
geometry, source facts, normals, animation, attachment or runtime code changes.
AUX_OBJ_NATIVE remains off in chapter recipes pending the user's still choice.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ps2_cast import gutter_texture, texture_key  # noqa: E402


def bake(source, output):
    source, output = Path(source), Path(output)
    val = json.loads((source / "validation.json").read_text())
    tex = val["texture"]
    if (tex["tpl_arc"] != "0x228" or tex["used"] != [0]
            or tex["atlas"] != [256, 128] or not tex["opaque"]
            or texture_key(source / "atlas.png") != "87069266-e5d19f12"):
        raise ValueError("requires retained original full Garrador core")
    mesh_path = source / "mesh.json"
    if hashlib.sha256(mesh_path.read_bytes()).hexdigest() != (
            "28a4ee49b8ef2965735e8486de4a020684a1de8917c3309e8b6c9f071b0a28fb"):
        raise ValueError("source geometry identity differs")
    output.mkdir(parents=True, exist_ok=False)
    mesh = json.loads(mesh_path.read_text())
    atlas = np.array(Image.open(source / "atlas.png").convert("RGBA"))
    ah, aw = atlas.shape[:2]
    positions = np.array(mesh["positions_mm"])
    mask = np.ones((ah, aw), dtype=float)
    hits = np.zeros((ah, aw), dtype=np.int32)
    for tri in mesh["triangles"]:
        ids = [c["vertex"] for c in tri["corners"]]
        xyz = positions[ids]
        uv = np.array([c["uv"] for c in tri["corners"]]) * [aw, ah]
        matrix = np.vstack([uv.T, np.ones(3)])
        if abs(np.linalg.det(matrix)) < 1e-8:
            continue
        inverse = np.linalg.inv(matrix)
        central = all(sum(w for b, w in mesh["weights"][i] if b == 1) > .5
                      for i in ids)
        for y in range(max(0, int(np.floor(uv[:, 1].min()))),
                       min(ah - 1, int(np.ceil(uv[:, 1].max()))) + 1):
            for x in range(max(0, int(np.floor(uv[:, 0].min()))),
                           min(aw - 1, int(np.ceil(uv[:, 0].max()))) + 1):
                bary = inverse @ np.array([x + .5, y + .5, 1.])
                if bary.min() < -.000001:
                    continue
                point = bary @ xyz
                intensity = float(np.exp(-((point[0] / 85.) ** 2
                                  + ((point[1] + 65.) / 48.) ** 2))) if central else 0.
                # Shared chart uses must all permit the same colour change.
                mask[y, x] = min(mask[y, x], intensity)
                hits[y, x] += 1
    mask[hits == 0] = 0
    mask = np.asarray(Image.fromarray(np.rint(mask * 255).astype(np.uint8))
                      .filter(ImageFilter.MaxFilter(3))).astype(float) / 255.
    x, y, w, h = tex["cells"]["0"]
    rgb = atlas[y:y + h, x:x + w, :3].astype(float) / 255.
    strength = .93 * mask[y:y + h, x:x + w]
    tint = np.array([1., 64 / 255., 8 / 255.])
    colour = np.rint(255 * (1 - (1 - rgb)
                           * (1 - strength[:, :, None] * tint)))
    colour = colour.clip(0, 255).astype(np.uint8)
    result = atlas.copy()
    result[y:y + h, x:x + w, :3] = colour
    rgba = np.concatenate([colour, np.full((h, w, 1), 255,
                                          dtype=np.uint8)], axis=2)
    gutter = val["atlas_wrap_gutters"]["0"]
    encoded, padding = gutter_texture(rgba.tobytes(), w, h,
                                      gutter["uv_bounds"], gutter["wrap"])
    if list(padding) != list(gutter["padding"]):
        raise ValueError("original gutter layout changed")
    left, top, right, bottom = padding
    result[y - top:y + h + bottom, x - left:x + w + right] = (
        np.frombuffer(encoded, dtype=np.uint8).reshape(
            h + top + bottom, w + left + right, 4))
    if not np.array_equal(result[:, :, 3], atlas[:, :, 3]):
        raise ValueError("original alpha changed")
    target = output / "atlas-baked.png"
    Image.fromarray(result).save(target)
    Image.fromarray(np.rint(mask * 255).astype(np.uint8)).save(
        output / "highlight-UV-mask.png")
    report = {
        "status": "USER LOOK PENDING; broad v1 withdrawn",
        "new_key": texture_key(target),
        "baked_atlas_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "localization": "Original bone1 central surface; rest x/y Gaussian (0,-65), scales85/48mm; min across chart uses; one pixel filtering dilation",
        "formula": ".93*mask screen blend of original RGB with [1,64/255,8/255]",
        "scope": "Static authored approximation; dynamic GC specular not reproduced",
    }
    (output / "bake.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(bake(args.source, args.output), indent=2))
