"""Unused-vector mip composition keeps the exact compact base and alpha."""
import ctypes
import os
import pathlib
import struct
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import compact_native_vq as compact
import mipmap_compact_vq as composed
import mipmap_twiddled as twiddled
import mipmap_vq as vq
import convert_tpl as tpl
from test_mipmap_twiddled import from_words
from test_mipmap_pal4 import package as palette_package
import mipmap_pal4


def pair(fmt=0,full=False):
    if full:
        words=[0xf000|((x//2+y//2*32)%256<<4)|((x//2+y//2*32)*7&15)
               for y in range(64) for x in range(64)]
    else:
        pack=(tpl._pack_565,tpl._pack_1555,tpl._pack_4444)[fmt]
        a,b=pack((255,17,51,255)),pack((0,119,255,0))
        words=[a if (x^y)&1 else b for y in range(64) for x in range(64)]
    source=from_words(words,64,fmt)
    base,report=compact.compact(source,enabled=True)
    assert report['changed']
    reference,_=twiddled.add_mipmaps(source,enabled=True)
    return base,reference


class CompactMips(unittest.TestCase):
    def test_off_identity_and_exact_all_levels_when_spare_dictionary_fits(self):
        for fmt in range(3):
            base,reference=pair(fmt)
            self.assertEqual(composed.add_mipmaps(base,reference)[0],base)
            result,report=composed.add_mipmaps(base,reference,enabled=True,engine='python')
            a,b=vq.read_native_vq(base),vq.read_native_vq(result)
            self.assertEqual(a.base_indices,b.base_indices)
            for index in set(a.base_indices):
                self.assertEqual(a.codebook[index*8:index*8+8],b.codebook[index*8:index*8+8])
            self.assertEqual(a.texture[:5],b.texture[:5])
            self.assertEqual(a.texture[6]|4,b.texture[6])
            self.assertEqual(a.header[9:],b.header[9:])
            self.assertTrue(report['exact_all_reference_levels'])
            self.assertTrue(all(r['alpha_rmse']==0 for r in report['lower_level_quality']))

    def test_full_base_dictionary_remains_exact_and_reports_lower_level_error(self):
        base,reference=pair(2,full=True)
        self.assertEqual(len(set(vq.read_native_vq(base).base_indices)),256)
        result,report=composed.add_mipmaps(base,reference,enabled=True,engine='python')
        self.assertEqual(vq.read_native_vq(base).codebook,vq.read_native_vq(result).codebook)
        self.assertEqual(report['unused_slots_changed'],0)
        self.assertFalse(report['exact_all_reference_levels'])
        self.assertTrue(report['lower_level_quality'][-1]['exact_rgba'])

    def test_different_reference_base_or_identity_is_refused(self):
        base,reference=pair()
        other,_=pair(1)
        with self.assertRaises(ValueError):composed.add_mipmaps(other,reference,enabled=True)
        source=from_words([0]*4096,64)
        wrong,_=twiddled.add_mipmaps(source,enabled=True)
        with self.assertRaises(ValueError):composed.add_mipmaps(base,wrong,enabled=True)
        with self.assertRaises(ValueError):composed.add_mipmaps(base,source,enabled=True)

    def test_palette_reference_keeps_native_alpha_base_and_mip_target_words(self):
        source=palette_package(128)
        base,report=compact.compact(source,enabled=True)
        self.assertTrue(report['changed'])
        reference,_=mipmap_pal4.add_mipmaps(source,enabled=True,engine='python')
        result,proof=composed.add_mipmaps(base,reference,enabled=True,engine='python')
        a,b=vq.read_native_vq(base),vq.read_native_vq(result)
        self.assertEqual(vq.decode_level(a,128),vq.decode_level(b,128))
        ref=mipmap_pal4.read_native_pal4(reference)
        self.assertEqual(composed.reference_words(ref,1),(struct.unpack('<16H',ref.palette)[ref.payload[1]>>4],))
        self.assertEqual(a.base_indices,b.base_indices)
        self.assertEqual(b.texture[3],tpl.FORMAT_ARGB4444)
        self.assertEqual(a.texture[6]|4,b.texture[6])
        self.assertEqual(a.header[9:],b.header[9:])

    @unittest.skipUnless(os.environ.get('MIPMAP_PVRTEX_ORACLE'),'independent decoder optional')
    def test_actual_pvrtex_decodes_every_rebuilt_level_and_base(self):
        lib=ctypes.CDLL(os.environ['MIPMAP_PVRTEX_ORACLE'])
        fn=lib.mipmap_oracle_decode
        fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,
                     ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
        fn.restype=ctypes.c_int
        for fmt in range(3):
            source,reference=pair(fmt)
            blob,_=composed.add_mipmaps(source,reference,enabled=True,engine='python')
            n=vq.read_native_vq(blob)
            for level in range(7):
                side=1<<level;out=ctypes.create_string_buffer(side*side*4)
                self.assertEqual(fn(n.payload,len(n.payload),fmt,64,1,level,out,len(out)),len(out))
                self.assertEqual(out.raw,bytes(c for p in vq.decode_level(n,side) for c in p))


if __name__=='__main__':unittest.main()
