"""Known full-frame FX only; shared other consumers and rectangles are held."""
import copy
import pathlib
import sys
import unittest
import zlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
for p in (ROOT/'tools',ROOT/'tools/d367',ROOT/'tools/d367/mipmap21'):
    sys.path.insert(0,str(p))
import compact_native_vq
import convert_tpl as tpl
import fx_candidate as fx
import mipmap_pal4 as pal4
import mipmap_vq as vq
import texpack
from test_mipmap_pal4 import package


def frame(side,cover=True):
    blob=package(side);h,t=list(tpl.HEADER.unpack_from(blob)),list(tpl.TEXTURE.unpack_from(blob,48))
    t[0]=b'ps2-source'.ljust(64,b'\0')
    h[10]=0x80000000|side|side<<11 if cover else 0
    body=tpl.TEXTURE.pack(*t)+blob[144:];h[8]=zlib.crc32(body)&0xffffffff
    return tpl.HEADER.pack(*h)+body


class EffectMipSelection(unittest.TestCase):
    def setUp(self):
        self.source={(1,2):frame(8),(3,4):frame(128),(5,6):frame(8)}
        self.original=texpack.build(self.source)[0]
        self.base=dict(self.source)
        self.base[(3,4)]=compact_native_vq.compact(self.source[(3,4)],enabled=True)[0]
        self.base_pack=texpack.build(self.base)[0]
        self.coverage=dict(source_pack_sha256=fx.sha(self.original),normal_rows=[])
        self.proofs={}
        for key,blob in self.source.items():
            name='%08x-%08x'%key;side=tpl.TEXTURE.unpack_from(blob,48)[1]
            refs=[dict(owner_category='effect')]
            if key==(5,6):refs.append(dict(owner_category='other-source'))
            self.coverage['normal_rows'].append(dict(key=name,material='ps2-source',width=side,height=side,source_references=refs))
            self.proofs[name]=dict(sha256=fx.sha(blob),frames=[dict(room='r100')])

    def test_off_selected_base_identity_then_palette_and_compact_vq_mips_only(self):
        control,_,_,_=fx.build_candidate(self.original,self.base_pack,self.coverage,self.proofs)
        self.assertEqual(control,self.base_pack)
        result,report,before,after=fx.build_candidate(self.original,self.base_pack,self.coverage,self.proofs,enabled=True,engine='python')
        self.assertEqual(report['changed_from_base'],2)
        self.assertEqual(report['family_counts'],{'compact-PAL4':1,'existing-lossless-VQ-base':1})
        self.assertEqual(after[(5,6)],before[(5,6)])
        small=pal4.read_native_pal4(after[(1,2)]);large=vq.read_native_vq(after[(3,4)])
        self.assertTrue(small.mipmapped and large.mipmapped)
        self.assertEqual(small.base_indices,pal4.read_native_pal4(before[(1,2)]).base_indices)
        self.assertEqual(small.palette,pal4.read_native_pal4(before[(1,2)]).palette)
        self.assertEqual(vq.decode_level(large,128),vq.decode_level(vq.read_native_vq(before[(3,4)]),128))
        texpack.verify(result)

    def test_wrong_library_hash_is_refused_and_non_effect_reference_is_held(self):
        proof=copy.deepcopy(self.proofs);proof['00000001-00000002']['sha256']='bad'
        with self.assertRaises(ValueError):fx.build_candidate(self.original,self.base_pack,self.coverage,proof,enabled=True)
        _,report,_,_=fx.build_candidate(self.original,self.base_pack,self.coverage,self.proofs)
        self.assertEqual(report['held'][0]['reason'],'shared-non-effect-consumer-sampling-open')


if __name__=='__main__':unittest.main()
