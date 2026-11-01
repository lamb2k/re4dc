"""TEX_PAL32 (colour27): ARGB8888 palette tails on PAL4 / PAL8 packages; knob-off object identity."""
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import convert_tpl as TPL
from test_pal4_alpha import FIXTURE
from test_mipmap_pal4 import stubs

PAL32 = 1 << 3


def pal4(palette32=None, palette16=None, flags=0):
    """One 8x8 PAL4 twiddled package: 32 index bytes, then the palette tail (16 ARGB8888 or ARGB4444 words)."""
    payload = bytes([0x10, 0x32, 0x54, 0x76, 0x98, 0xba, 0xdc, 0xfe]) * 4
    payload += struct.pack('<16I', *palette32) if palette32 is not None else struct.pack('<16H', *palette16)
    start = 48 + 96
    desc = TPL.TEXTURE.pack(b'material0', 8, 8, 4, start, len(payload), flags, 1, 0)
    body = desc + payload
    return TPL.HEADER.pack(TPL.MAGIC, 2, 48, 96, 1, 48, start, len(payload), zlib.crc32(body) & 0xffffffff, 1, 0) + body


MAIN = r'''
int main(int argc,char** argv){
    const std::string root=argv[1];reserved_count=8;
    for(unsigned i=0;i<1024;++i)palette[i]=0x12345678U+i;
    auto p32=read_bytes(root+"/p32");Package p;
#if !RE4DC_TEX_PAL32
    assert(!p.adopt(p32.data(),p32.size()));return 0;
#else
    assert(initialize_palettes(0xff));
    Package a,b,c;
    assert(a.open_streamed((root+"/p32").c_str()));inflight=true;assert(a.upload());
    const unsigned bank=a.textures()[0].reserved_0-1;assert(bank>=8 && bank<64);
    const auto* w=(const unsigned*)((const unsigned char*)a.pvr_texture(0)+a.textures()[0].data_size-64);
    for(unsigned k=0;k<16;++k)assert(palette[bank*16+k]==w[k]);
    // The same ARGB8888 words share the bank; a 4444 palette with the same leading bytes never does.
    unsigned writes=palette_writes;
    assert(b.open_streamed((root+"/p32").c_str()));inflight=true;assert(b.upload());
    assert(b.textures()[0].reserved_0==bank+1 && palette_writes==writes);
    assert(c.open_streamed((root+"/p16").c_str()));inflight=true;assert(c.upload());
    assert(c.textures()[0].reserved_0!=bank+1);
    const unsigned bank16=c.textures()[0].reserved_0-1;
    const auto* h=(const unsigned short*)((const unsigned char*)c.pvr_texture(0)+c.textures()[0].data_size-32);
    for(unsigned k=0;k<16;++k)assert(palette[bank16*16+k]==expected_color(h[k],true));
    close_checked(c);close_checked(b);close_checked(a);
    // A flag without the wider tail (or the tail without the flag) is refused.
    for(const char* name:{"flag16","tail32"}){auto bad=read_bytes(root+"/"+name);assert(!p.adopt(bad.data(),bad.size()));}
    assert(!allocs && !open_files);return 0;
#endif
}
'''

FLAGS = ['-DRE4DC_STORAGE_BOUNCE_BYTES=16384', '-DRE4DC_PVR_PIPELINE=1', '-DRE4DC_TEX_PAL4_ALPHA=1',
         '-DRE4DC_TREE_IMPOSTOR=1', '-DRE4DC_CAST_MIPMAP=1', '-DRE4DC_TEX_PAL4_MIPMAP=1', '-DRE4DC_TEX_PAL8_ALPHA=1',
         '-DRE4DC_TEX_PAL8_MIPMAP=1', '-DRE4DC_TEX_TWIDDLED_MIPMAP=1', '-DRE4DC_TEX_PACK=1',
         '-DRE4DC_TEX_PACK_WINDOW=1', '-DRE4DC_TEX_RESIDENT=1']


@unittest.skipUnless(shutil.which('g++'), 'host compiler required')
class Pal32(unittest.TestCase):
    def test_runtime_admission_banks_and_sharing(self):
        words32 = [0x00000000, 0x01020304, 0x7f102030, 0xff0a0b0c] + [0x80000000 | (k * 0x010101) for k in range(4, 16)]
        lo16 = [w & 0xffff for w in words32]
        with tempfile.TemporaryDirectory() as directory:
            d = pathlib.Path(directory); stubs(d)
            with (d / 'dc/pvr.h').open('a') as f:
                f.write('\n#define PVR_TXRFMT_PAL8BPP (6U<<27)\n#define PVR_TXRFMT_8BPP_PAL(bank) ((bank)<<25)\n')
            (d / 'reader.cpp').write_text(FIXTURE[:FIXTURE.index('int main(')] + MAIN)
            cases = dict(p32=pal4(words32, flags=PAL32), p16=pal4(palette16=lo16),
                         flag16=pal4(palette16=lo16, flags=PAL32), tail32=pal4(words32))
            for name, blob in cases.items():
                (d / name).write_bytes(blob)
            for on in (0, 1):
                exe = d / ('reader%d' % on)
                cmd = ['g++', '-std=c++17', *FLAGS, '-DRE4DC_TEX_PAL32=%d' % on, '-fsanitize=address,undefined',
                       '-I' + str(d), '-I' + str(ROOT / 'room'), str(d / 'reader.cpp'),
                       str(ROOT / 'room/texture_package.cpp'), str(ROOT / 'room/room_storage.cpp'), '-o', str(exe)]
                built = subprocess.run(cmd, capture_output=True, text=True)
                self.assertEqual(built.returncode, 0, built.stderr)
                ran = subprocess.run([str(exe), str(d)], capture_output=True, text=True)
                self.assertEqual(ran.returncode, 0, 'TEX_PAL32=%d\n%s' % (on, ran.stderr))

    def test_default_off_object_identical_to_head(self):
        with tempfile.TemporaryDirectory() as directory:
            d = pathlib.Path(directory); stubs(d)
            with (d / 'dc/pvr.h').open('a') as f:
                f.write('\n#define PVR_TXRFMT_PAL8BPP (6U<<27)\n#define PVR_TXRFMT_8BPP_PAL(bank) ((bank)<<25)\n')
            head = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:port/dreamcast/room/texture_package.cpp'])
            hhead = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:port/dreamcast/room/texture_package.hpp'])
            results = []
            for label, cpp, hpp in (('control', head, hhead), ('current', (ROOT / 'room/texture_package.cpp').read_bytes(),
                                                              (ROOT / 'room/texture_package.hpp').read_bytes())):
                q = d / label; q.mkdir(); (q / 'texture_package.cpp').write_bytes(cpp); (q / 'texture_package.hpp').write_bytes(hpp)
                for name in ('room_storage.hpp',):
                    (q / name).write_bytes((ROOT / 'room' / name).read_bytes())
                obj = q / 'package.o'
                cmd = ['g++', '-std=c++17', '-O2', '-g0', '-frandom-seed=pal32', *FLAGS, '-I' + str(q), '-I' + str(d),
                       '-I' + str(ROOT / 'room'), '-c', str(q / 'texture_package.cpp'), '-o', str(obj)]
                subprocess.run(cmd, capture_output=True, check=True); results.append(obj.read_bytes())
            self.assertEqual(*results)


if __name__ == '__main__':
    unittest.main()
