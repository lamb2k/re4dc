#!/usr/bin/env python3
"""I009 static Garrador core highlight candidate; requires user look approval.

Usage (Windows Python with numpy/Pillow):
  bake_garrador_core.py <original-ps2_cast-core-conversion> <new-output-directory>

Only the original source-derived core diffuse atlas is changed. Geometry, normal
lighting, UVs, skeleton, motions, source material facts and package rules remain
unchanged. This is an authored approximation of the GC orange/red highlight,
not an implementation of the GC dynamic specular stage. AUX_OBJ_NATIVE remains
off in chapter recipes until the user accepts a captured same-source comparison.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ps2_cast import gutter_texture, texture_key  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bake(source, output):
    source, output = Path(source), Path(output)
    validation = json.loads((source / "validation.json").read_text())
    texture = validation["texture"]
    if (texture["tpl_arc"] != "0x228" or texture["used"] != [0]
            or texture["atlas"] != [256, 128] or not texture["opaque"]
            or texture["key"] != "87069266-e5d19f12"):
        raise ValueError("requires the retained original full Garrador core atlas")
    atlas = source / "atlas.png"
    if texture_key(atlas) != texture["key"]:
        raise ValueError("source atlas identity differs")
    if output.resolve() == source.resolve():
        raise ValueError("output must be a new directory")
    output.mkdir(parents=True, exist_ok=False)
    pixels = np.array(Image.open(atlas).convert("RGBA"))
    x, y, width, height = texture["cells"]["0"]
    rgb = pixels[y:y + height, x:x + width, :3].astype(np.float64) / 255.0
    luminance = (rgb * np.array([.2126, .7152, .0722])).sum(axis=2)
    strength = .72 + .28 * luminance
    tint = np.array([1.0, 64 / 255., 8 / 255.])
    colour = np.rint(255 * (1 - (1 - rgb)
                           * (1 - strength[:, :, None] * tint)))
    colour = colour.clip(0, 255).astype(np.uint8)
    result = pixels.copy()
    result[y:y + height, x:x + width, :3] = colour
    rgba = np.concatenate([colour, np.full((height, width, 1), 255,
                                          dtype=np.uint8)], axis=2)
    gutter = validation["atlas_wrap_gutters"]["0"]
    encoded, padding = gutter_texture(rgba.tobytes(), width, height,
                                      gutter["uv_bounds"], gutter["wrap"])
    if list(padding) != list(gutter["padding"]):
        raise ValueError("source wrap gutter layout changed")
    left, top, right, bottom = padding
    result[y - top:y + height + bottom, x - left:x + width + right] = (
        np.frombuffer(encoded, dtype=np.uint8).reshape(
            height + top + bottom, width + left + right, 4))
    if not np.array_equal(result[:, :, 3], pixels[:, :, 3]):
        raise ValueError("source alpha changed")
    target = output / "atlas-baked.png"
    Image.fromarray(result).save(target)
    key = texture_key(target)
    if key == texture["key"]:
        raise ValueError("bake did not create a new content identity")
    report = {
        "status": "USER LOOK PENDING",
        "scope": "Authored static source-diffuse colour bake; dynamic GC specular is not reproduced.",
        "source_atlas_sha256": sha(atlas),
        "baked_atlas_sha256": sha(target),
        "source_key": texture["key"],
        "new_key": key,
        "formula": "s=.72+.28*Rec709(sourceRGB); screen blend source with s*[1,64/255,8/255]",
        "unchanged": "alpha,dimensions,cell,wrap gutters,geometry,normals,weights,UVs,source facts,14-part owner/motions",
        "changed_pixels": int(np.any(result != pixels, axis=2).sum()),
    }
    (output / "bake.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(bake(args.source, args.output), indent=2))
