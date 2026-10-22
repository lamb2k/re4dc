import pathlib
import struct
import sys
import unittest
import zlib

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE / "tools" / "d367"))
sys.path.insert(0, str(HERE / "tools" / "d367" / "mipmap21"))
import convert_tpl as tpl
import mipmap_vq as vq
import mipmap_twiddled as tw
import mip_quality as mq
from test_mipmap_twiddled import from_words, native as tw_native


def vq_blocks(side=16):
    """Black/white block texture whose codebook has no grey: the reviewed defect."""
    words = [0x0000] * 4 + [0xffff] * 4 + [0x0000] * 4 * 254
    idx = bytes(((x + y) & 1) for y in range(side // 2) for x in range(side // 2))
    payload = struct.pack("<1024H", *words) + idx
    t = tpl.TEXTURE.pack(b"bw", side, side, 0, 144, len(payload), 0, 2, 0)
    crc = zlib.crc32(t + payload) & 0xffffffff
    return tpl.HEADER.pack(tpl.MAGIC, 2, 48, 96, 1, 48, 144, len(payload), crc, 1, 0) + t + payload


class Gate(unittest.TestCase):
    def test_quarter_coverage_cutout_is_held_with_exact_base(self):
        on, off = tpl._pack_1555((255, 255, 255, 255)), tpl._pack_1555((0, 0, 0, 0))
        words = [on if x % 2 == 0 and y % 2 == 0 else off for y in range(16) for x in range(16)]
        blob, _ = tw.add_mipmaps(from_words(words, 16, fmt=1), enabled=True)
        key, row, held = mq.audit(((1, 2), blob))
        self.assertEqual(row["base_coverage"], 0.25)
        self.assertEqual(row["levels"][0]["coverage"], 0.0)  # the fixed threshold erases it
        self.assertEqual(row["reasons"], ["coverage"])
        base = tw.read_native_twiddled(held)
        self.assertFalse(base.mipmapped)
        self.assertEqual(base.base_texels, tw.read_native_twiddled(blob).base_texels)
        self.assertEqual(base.crc_rule, "header")

    def test_original_vq_without_averaged_colour_is_held(self):
        blob, _ = vq.add_mipmaps(vq_blocks(), enabled=True, engine="python")
        _, row, held = mq.audit(((3, 4), blob))
        self.assertIn("vq-colour", row["reasons"])
        self.assertGreater(row["levels"][0]["mean_shift"], 60)
        n = vq.read_native_vq(held)
        self.assertFalse(n.mipmapped)
        self.assertEqual((n.codebook, n.base_indices), (vq.read_native_vq(blob).codebook, vq.read_native_vq(blob).base_indices))

    def test_scoped_rows_of_held_keys_are_rebound(self):
        blob, _ = vq.add_mipmaps(vq_blocks(), enabled=True, engine="python")
        _, _, held = mq.audit(((3, 4), blob))
        n = vq.read_native_vq(blob)
        row = "{0x00000003U,0x00000004U,32U,16U,{16U,16U,0U,%dU,2U,%dU,0x%08xU},1.0f,1.0f},\n" % (
            n.texture[6], n.texture[5], n.header[8])
        other = row.replace("0x00000003U", "0x00000009U")
        text, count = mq.rebind(row + other, {(3, 4): held})
        h = vq.read_native_vq(held)
        self.assertEqual(count, 1)
        self.assertIn("{16U,16U,0U,%dU,2U,%dU,0x%08xU}" % (h.texture[6], h.texture[5], h.header[8]), text)
        self.assertTrue(text.endswith(other))

    def test_smooth_opaque_chain_passes_and_base_only_is_skipped(self):
        words = [tpl._pack_565((x * 8, y * 8, 128, 255)) for y in range(16) for x in range(16)]
        blob, _ = tw.add_mipmaps(from_words(words, 16, fmt=0), enabled=True)
        _, row, held = mq.audit(((5, 6), blob))
        self.assertEqual((row["verdict"], held), ("pass", None))
        self.assertIsNone(mq.audit(((7, 8), tw_native(16))))


if __name__ == "__main__":
    unittest.main()
