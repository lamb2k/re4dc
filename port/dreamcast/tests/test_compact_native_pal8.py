"""Exact palette family preserves every existing native mip, including alpha."""
import ctypes
import os
import pathlib
import sys
import unittest
import zlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import compact_native_pal8 as pal8
import mipmap_twiddled as tw
import test_mipmap_twiddled as fixture


def source(side=64,gray=True):
    if gray:
        words=[((y&15)<<12)|((x&15)*0x111) for y in range(side) for x in range(side)]
    else:
        palette=[0xf000|((i&3)<<8)|(((i>>2)&3)<<4)|((i>>4)&3) for i in range(64)]
        words=[palette[(x+y*3)%64] for y in range(side) for x in range(side)]
    return fixture.from_words(words,side,fmt=2)


class ExactPal8Data(unittest.TestCase):
    def test_off_exact_then_base_and_existing_native_mip_chain_are_lossless(self):
        for gray in (False,True):
            original=source(gray=gray)
            for blob in (original,tw.add_mipmaps(original,enabled=True,engine='python')[0]):
                self.assertEqual(pal8.compact(blob)[0],blob)
                result,report=pal8.compact(blob,enabled=True)
                self.assertTrue(report['changed'])
                a,b=tw.read_native_twiddled(blob),pal8.read_native_pal8(result)
                self.assertEqual(a.header[9:],b.header[9:])
                self.assertEqual(a.texture[:3],b.texture[:3])
                self.assertEqual(a.texture[6],b.texture[6])
                self.assertLess(len(b.payload),len(a.payload))
                levels=range(a.size.bit_length()) if a.mipmapped else [a.size.bit_length()-1]
                for i in levels:self.assertEqual(tw.decode_level(a,1<<i),pal8.decode_level(b,1<<i))

    def test_grayscale_frames_and_mips_share_one_canonical_palette(self):
        base=source()
        native_mips=tw.add_mipmaps(base,enabled=True,engine='python')[0]
        a,b=(pal8.read_native_pal8(pal8.compact(x,enabled=True)[0]) for x in (base,native_mips))
        self.assertEqual(a.palette,b.palette)
        self.assertEqual(len(a.palette),512)
        self.assertEqual(pal8.decode_words(b,1),[tw.decode_level(tw.read_native_twiddled(native_mips),1)[0][3]//17<<12 |
            tw.decode_level(tw.read_native_twiddled(native_mips),1)[0][0]//17*0x111])

    def test_pal4_preference_palette_overhead_and_more_than256_colors_do_not_convert(self):
        low=fixture.from_words([i%16*0x1111 for i in range(64*64)],64,fmt=2)
        many=fixture.from_words([i&0xffff for i in range(64*64)],64,fmt=2)
        small=source(16)
        for blob,reason in ((low,'prefer-existing-PAL4'),(many,'too-many-colors'),(small,'no-payload-request-win')):
            result,report=pal8.compact(blob,enabled=True)
            self.assertEqual(result,blob);self.assertEqual(report['reason'],reason)

    def test_both_crc_conventions_survive_and_malformed_palette_is_refused(self):
        original=source()
        h=list(pal8.tpl.HEADER.unpack_from(original));h[8]=zlib.crc32(original[144:])&0xffffffff
        for blob in (original,pal8.tpl.HEADER.pack(*h)+original[48:]):
            result,report=pal8.compact(blob,enabled=True);self.assertTrue(report['changed'])
            n=pal8.read_native_pal8(result)
            self.assertEqual(n.crc_rule,tw.read_native_twiddled(blob).crc_rule)
            for broken in (result[:-1],result[:144]+bytes([result[144]^1])+result[145:]):
                with self.assertRaises(ValueError):pal8.read_native_pal8(broken)
        rgb=fixture.from_words([i for i in range(64*64)],64,fmt=0)
        with self.assertRaises(ValueError):pal8.compact(rgb,enabled=True)

    @unittest.skipUnless(os.environ.get('MIPMAP_PVRTEX_ORACLE_PAL8'),'independent decoder optional')
    def test_pinned_decoder_reads_every_level_including_fourth_index_1x1(self):
        lib=ctypes.CDLL(os.environ['MIPMAP_PVRTEX_ORACLE_PAL8']);fn=lib.mipmap_oracle_decode_pal8
        fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
        fn.restype=ctypes.c_int
        for side in (32,64,256):
            for mip in (False,True):
                original=source(side)
                if mip:original=tw.add_mipmaps(original,enabled=True,engine='python')[0]
                result,report=pal8.compact(original,enabled=True);self.assertTrue(report['changed'])
                n=pal8.read_native_pal8(result)
                for level in (range(side.bit_length()) if mip else [side.bit_length()-1]):
                    size=1<<level;out=ctypes.create_string_buffer(size*size*4)
                    self.assertEqual(fn(n.payload,len(n.payload),side,mip,level,out,len(out)),len(out))
                    self.assertEqual(out.raw,bytes(c for p in pal8.decode_level(n,size) for c in p))


if __name__=='__main__':unittest.main()
