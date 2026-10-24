import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import zlib

import prepare_pair as p

class PairControls(unittest.TestCase):
    def materials(self):
        return [dict(flag=4, diffuse=0, opacity=1, raw='proof')]

    def test_explicit_material(self):
        self.assertEqual(p.check_materials(self.materials()), 'proof')

    def test_wrong_owner_recipe_refused(self):
        for key, value in [('flag',5),('diffuse',2),('opacity',0)]:
            m=self.materials();m[0][key]=value
            with self.assertRaises(ValueError):p.check_materials(m)
        for m in ([], self.materials()*2):
            with self.assertRaises(ValueError):p.check_materials(m)

    def test_authored_opacity_intensity_not_palette_alpha(self):
        c=bytes([0x12,0x34,0x56,0])*16384
        m=bytes([0xf0,0xf0,0xf0,0])*16384
        self.assertEqual(p.compose(c,m,128,128)[0],(0x12,0x34,0x56,255))
        self.assertEqual(p.compose(c,bytes([0,0,0,255])*16384,128,128)[0][3],0)

    def test_bad_mask_and_shape_refused(self):
        c=bytes(65536)
        for m in (bytes([16,32,16,255])*16384,bytes([15,15,15,255])*16384,c[:-4]):
            with self.assertRaises(ValueError):p.compose(c,m,128,128)
        with self.assertRaises(ValueError):p.compose(c,c,256,64)

    def test_native_encoder_exact_words_crc_and_no_gc_decoder(self):
        pix=[(0x12,0x34,0x56,0x78)]*16384
        with mock.patch.object(p.ct,'decode_image',side_effect=AssertionError('GC decode forbidden')):
            blob,meta=p.encode(pix)
        h=p.ct.HEADER.unpack_from(blob)
        row=p.ct.TEXTURE.unpack_from(blob,h[5])
        self.assertEqual((len(blob),row[1],row[2],row[3],row[5],row[7]),(32912,128,128,2,32768,1))
        self.assertEqual(zlib.crc32(blob[h[2]:])&0xffffffff,h[8])
        self.assertEqual(set(struct.unpack('<16384H',blob[row[4]:])),{0x7135})
        self.assertEqual(p.ct.canonical_native_crc(blob),blob)

    def test_wrong_pixel_count_refused(self):
        with self.assertRaises(ValueError):p.encode([])

    def test_wrong_member_fails_before_parse(self):
        with mock.patch.object(p.pb,'dat_entries',side_effect=AssertionError('must not parse')):
            with self.assertRaisesRegex(ValueError,'identity'):p.audit(bytes(p.DAT_SIZE))

    def test_pair_token_contract(self):
        self.assertEqual(p.material_pair_identity(p.COLOR,p.MASK),p.KEY)
        self.assertNotEqual(p.material_pair_identity(p.MASK,p.COLOR),p.KEY)

    def test_no_option_is_read_only_and_existing_destination_refused(self):
        fake=(dict(package={},production_enabled=False),b'payload',[bytes(65536)]*2,[(0,0,0,0)]*16384)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'existing';out.mkdir();sentinel=out/'preserve';sentinel.write_bytes(b'unchanged')
            with mock.patch.object(p.pb,'afs_index',return_value={'em35.dat':(123,p.DAT_SIZE)}), \
                 mock.patch.object(p.pb,'afs_read',return_value=b''),mock.patch.object(p,'audit',return_value=fake), \
                 contextlib.redirect_stdout(io.StringIO()):
                p.main(['--ps2-iso',d])
                self.assertEqual(sorted(x.name for x in Path(d).iterdir()),['existing'])
                with self.assertRaises(FileExistsError):p.main(['--ps2-iso',d,'--prepare-private',str(out)])
            self.assertEqual(sentinel.read_bytes(),b'unchanged')

if __name__=='__main__':unittest.main()
