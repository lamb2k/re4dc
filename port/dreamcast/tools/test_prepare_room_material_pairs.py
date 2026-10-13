#!/usr/bin/env python3
"""Focused source-binding, bounds and log-room tests; no private assets."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import prepare_room_material_pairs as pairs
from prepare_native_ui import material_pair_identity
from test_fit_ps2_world_textures import package
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "d367"))
import texpack


def table(bodies):
    out = bytearray(4 + 4 * len(bodies))
    struct.pack_into(">I", out, 0, len(bodies))
    for i, body in enumerate(bodies):
        struct.pack_into(">I", out, 4 + i * 4, len(out))
        out.extend(body)
    return bytes(out)


def itm(models, palettes):
    ids = struct.pack(">I", len(models)) + b"".join(struct.pack(">HHI", i, 0, 0) for i in range(len(models)))
    mb, tb = table(models), table(palettes)
    return struct.pack(">4I", 3, 16, 16 + len(ids), 16 + len(ids) + len(mb)) + ids + mb + tb


class PairTests(unittest.TestCase):
    def test_itm_binds_matching_table_slots_not_cross_product(self):
        scanner = pairs.Scanner()
        with patch.object(scanner, "bind") as bind:
            scanner.itm(itm([b"model-A", b"model-B"], [b"palette-Z", b"palette-Y"]), "fixture")
        self.assertEqual([(c.args[0], c.args[1]) for c in bind.call_args_list],
                         [(b"model-A", b"palette-Z"), (b"model-B", b"palette-Y")])

    def test_itm_rejects_inconsistent_counts_and_offsets(self):
        source = bytearray(itm([b"model"], [b"palette"]))
        palette_table = pairs.u32(source, 12)
        struct.pack_into(">I", source, palette_table, 2)
        with self.assertRaisesRegex(ValueError, "counts disagree"):
            pairs.Scanner().itm(source, "fixture")
        with self.assertRaisesRegex(ValueError, "overlaps table"):
            pairs.offset_table(struct.pack(">2I", 1, 0), 0)

    def test_material_headers_advance_over_each_gx_payload(self):
        blob = bytearray(64 + 36 + 32)
        struct.pack_into(">H", blob, 26, 2)
        struct.pack_into(">I", blob, 28, 64)
        struct.pack_into(">I", blob, 60, 0x20030818)
        blob[75], blob[76], blob[78] = 4, 3, 6
        struct.pack_into(">I", blob, 88, 4)
        blob[111], blob[112], blob[114] = 4, 7, 8
        self.assertEqual(pairs.material_indices(blob), [(0, 3, 6), (1, 7, 8)])
        struct.pack_into(">I", blob, 88, 999999)
        with self.assertRaisesRegex(ValueError, "outside source"):
            pairs.material_indices(blob)

    def test_smd_reuses_model_with_its_actual_selected_tpl(self):
        # Two placements share BIN0 but select different palettes.
        work = bytearray(144)
        work[36:40] = bytes([0, 1, 255, 1])
        work[108:112] = bytes([0, 0, 255, 2])
        bm = struct.pack(">I", 4) + b"model"
        tp = struct.pack(">2I", 8, 10) + b"AZ"
        tp += b"BY"
        # Second palette starts at offset10, so the first is AZ and second BY.
        blob = struct.pack(">BBH3I", 0, 0, 2, 160, 160 + len(bm), 0) + work + bm + tp
        scanner = pairs.Scanner()
        with patch.object(scanner, "bind") as bind:
            scanner.smd(blob, "smd")
        self.assertEqual([(c.args[0], c.args[1]) for c in bind.call_args_list],
                         [(b"model", b"AZ"), (b"model", b"BY")])

    def test_logged_pair_requires_matching_active_room(self):
        color, mask = "90ae2fb7-a311436a", "86ac6830-98755031"
        key = material_pair_identity(color, mask)
        line = f"native UI: pair missing {key} color={color} mask={mask} 64x64"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log"
            path.write_text(line + "\nwarp: room enter 10c (#1)\n" + line + "\nwarp: room enter 11e (#2)\n" + line)
            scanner = pairs.Scanner()
            scanner.logs([path], "r11e")
            self.assertEqual(len(scanner.pairs[key]["evidence"]), 1)
            self.assertEqual(scanner.pairs[key]["evidence"][0]["line"], 5)
            path.write_text("warp: room enter 11e (#1)\n" + line.replace(key, "00000000-00000000"))
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                scanner.logs([path], "r11e")

    def test_logged_dimensions_cannot_conflict_for_one_identity(self):
        scanner = pairs.Scanner()
        scanner.add("90ae2fb7-a311436a", "86ac6830-98755031", {}, [64, 64])
        with self.assertRaisesRegex(ValueError, "dimensions disagree"):
            scanner.add("90ae2fb7-a311436a", "86ac6830-98755031", {}, [32, 32])

    def test_existing_packed_winner_does_not_get_loose_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = package(8, 8, 0, 0, 1, bytes(128))
            second = package(8, 8, 0, 0, 1, bytes([1]) * 128)
            candidate = root / "candidate.re4tex"; candidate.write_bytes(second)
            pack = root / "tex.pak"; pack.write_bytes(texpack.build({(1, 2): first})[0])
            key = "00000001-00000002"; dp = f"dc/tex/0/{key}.re4tex"
            fixture = root / "fixture.json"
            fixture.write_text(json.dumps({"replace":{"dc/tex.pak":str(pack),dp:str(candidate)}}))
            chosen = pairs.metadata(candidate)
            replace, report = pairs.select_missing([dict(key=key,disc_path=dp,chosen=chosen)], fixture)
            self.assertEqual(replace, {})
            self.assertEqual(report["selections"][0]["existing_origin"], "pack")
            self.assertFalse(report["selections"][0]["render_equal"])
            with self.assertRaisesRegex(ValueError, "fixture room differs"):
                pairs.select_missing([], fixture, "r11e")


if __name__ == "__main__":
    unittest.main()
