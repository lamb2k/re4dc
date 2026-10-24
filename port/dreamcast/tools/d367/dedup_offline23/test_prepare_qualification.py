import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib
import prepare_qualification as q
from test_strip_share import fixture
from strip_share import pack


def pair():
    legacy=bytearray(fixture());original=bytearray(legacy)
    struct.pack_into('<II',original,72,0,0)
    struct.pack_into('<I',legacy,72,struct.unpack_from('<I',original,12)[0])
    compact,_,_=pack(bytes(legacy))
    return bytes(original),bytes(legacy),compact


class QualificationVariantTests(unittest.TestCase):
    def test_legacy_default_and_compact_physical_extent(self):
        original,legacy,compact=pair()
        a=q.source_identity(original,legacy);b=q.source_identity(original,compact,True)
        self.assertEqual(a['resolved_source_bytes'],len(original))
        self.assertEqual(b['resolved_source_bytes'],len(original))
        self.assertLess(b['alternate_physical_bytes'],b['original_bytes'])
        specs,manifest=q.alternate_specs(Path('/any-private-root'))
        self.assertIsNone(manifest);self.assertEqual(len(specs),4)
        self.assertTrue(all('-linear' in str(p) for *_,p in specs))

    def test_repaired_extent_and_source_certificate_negative(self):
        original,_,compact=pair()
        for extent in (0,len(compact)-1,len(original)+32):
            bad=bytearray(compact);struct.pack_into('<I',bad,68,extent)
            # A valid new body CRC cannot authorize a foreign header extent.
            struct.pack_into('<I',bad,12,zlib.crc32(bad[80:]))
            with self.subTest(extent=extent):
                with self.assertRaisesRegex(ValueError,'Source extent'):q.source_identity(original,bytes(bad),True)
        bad=bytearray(compact);bad[72]^=1
        with self.assertRaisesRegex(ValueError,'Source certificate'):q.source_identity(original,bytes(bad),True)

    def test_frozen_manifest_pin_negative(self):
        raw=q.STRIP_MANIFEST.read_bytes();doc=json.loads(raw)
        # Syntactically valid but different declared file pin is refused before
        # the planner can trust it or emit staging commands.
        doc['variants'][0]['files']['ps2-dd3.re4mesh']['sha256']='0'*64
        with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
            p=Path(d)/'pins.json';p.write_text(json.dumps(doc))
            with patch.object(q,'STRIP_MANIFEST',p):
                with self.assertRaisesRegex(ValueError,'manifest pin'):q.alternate_specs(Path('/unused'),True)
