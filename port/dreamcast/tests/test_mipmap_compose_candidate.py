"""Overlapping compact/mip keys regenerate chains instead of dropping mips."""
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
for p in (ROOT/'tools',ROOT/'tools/d367',ROOT/'tools/d367/mipmap21'):
    sys.path.insert(0,str(p))
import compose_candidate as compose
import compact_native_vq
import convert_tpl as tpl
import mipmap_twiddled
import texpack
from test_compact_native_vq import raw


class ComposePacks(unittest.TestCase):
    def test_off_identity_and_shared_key_keeps_mips_with_original_base(self):
        before={(1,2):raw(),(3,4):raw(2),(5,6):raw(1)}
        compact=dict(before)
        world=dict(before)
        for key in ((1,2),(3,4)):
            compact[key]=compact_native_vq.compact(before[key],enabled=True)[0]
        for key in ((3,4),(5,6)):
            world[key]=mipmap_twiddled.add_mipmaps(before[key],enabled=True)[0]
        original=texpack.build(before)[0]
        coverage=dict(source_pack_sha256=compose.sha(original),normal_rows=[
            dict(key='%08x-%08x'%key,source_owned_lossless_vq_selection=key in ((1,2),(3,4)),
                 native_world_references=[dict(package='room-A')] if key in ((3,4),(5,6)) else [])
            for key in before])
        control,_,_,_=compose.compose(original,texpack.build(compact)[0],texpack.build(world)[0],coverage)
        self.assertEqual(control,original)
        _,report,_,after=compose.compose(original,texpack.build(compact)[0],texpack.build(world)[0],coverage,enabled=True,engine='python')
        self.assertEqual(report['overlapping_keys'],1)
        self.assertEqual(report['changed_keys'],3)
        self.assertEqual(after[(1,2)],compact[(1,2)])
        self.assertEqual(after[(5,6)],world[(5,6)])
        t=tpl.TEXTURE.unpack_from(after[(3,4)],48)
        self.assertEqual(t[7],tpl.PAYLOAD_VQ)
        self.assertTrue(t[6]&tpl.FLAG_MIPMAP)
        r=report['per_room']['room-A']
        self.assertEqual(r['composed']['mipmapped_keys'],2)
        self.assertGreater(r['composed']['ui_vram_page_retry_upper_request_bytes'],r['composed']['plain_alloc32_bytes'])

    def test_source_coverage_hash_and_key_namespace_refuse(self):
        original=texpack.build({(1,2):raw()})[0]
        with self.assertRaises(ValueError):
            compose.compose(original,original,original,dict(source_pack_sha256='bad'))
        other=texpack.build({(3,4):raw()})[0]
        with self.assertRaises(ValueError):
            compose.compose(original,other,original,dict(source_pack_sha256=compose.sha(original)))


if __name__=='__main__':unittest.main()
