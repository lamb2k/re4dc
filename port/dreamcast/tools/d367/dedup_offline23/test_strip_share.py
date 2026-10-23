import struct
import unittest
import zlib
from offline_dedup import MARKER,Package
from strip_share import pack,validate


def repair(b):
    b=bytearray(b);struct.pack_into('<I',b,12,zlib.crc32(b[80:]));return bytes(b)


def fixture():
    # Ten different vertex/UV records use the exact same four strip bytes.
    b=bytearray(1024)
    struct.pack_into('<4s19I',b,0,b'R4IM',3,len(b),0,0,1,10,30,40,1,128,128,192,480,864,928,2,0,123,MARKER)
    struct.pack_into('<8I',b,80,0,0,960,992,992,0,0,0)
    struct.pack_into('<IIBBBBII4f',b,128,0,0,0,255,0,0,0,10,0,0,1,1)
    for i in range(10):
        struct.pack_into('<IIIHH6H',b,192+28*i,3*i,4*i,4,3,1,0,0,0,10,10,10)
        for k in range(3):struct.pack_into('<6H',b,480+12*(3*i+k),i,k,0,10+i,20+k,0x8123+i)
        b[864+4*i:868+4*i]=bytes([3,0,1,2])
    return repair(b)


class StripShareTests(unittest.TestCase):
    def test_exact_block_alias_and_idempotence(self):
        a=fixture();b,g,st=pack(a)
        self.assertEqual(st['duplicate_blocks'],9);self.assertEqual(st['allocation_saving'],32)
        self.assertIsNone(g);self.assertEqual(pack(b)[0],b)
        x,y=validate(a,b);self.assertEqual([l['corners'] for l in x.lets],[l['corners'] for l in y.lets])
        self.assertEqual(len({l['fs'] for l in y.lets}),1)

    def test_crc_repaired_lod_pointer_mutation_refused(self):
        a=fixture();b,_,_=pack(a);bad=bytearray(b)
        off=struct.unpack_from('<I',bad,88)[0];struct.pack_into('<I',bad,88,off+4)
        bad=repair(bad);Package(bad,True) # CRC and ordinary package parsing are valid.
        with self.assertRaisesRegex(ValueError,'LOD absolute offsets'):validate(a,bad)

    def test_unsupported_extension_and_changed_vertex_refused(self):
        a=fixture();bad=bytearray(a);struct.pack_into('<I',bad,100,128)
        with self.assertRaisesRegex(ValueError,'unsupported extra'):pack(repair(bad))
        b,_,_=pack(a);bad=bytearray(b);bad[480+6]^=1
        with self.assertRaisesRegex(ValueError,'vertex bytes'):validate(a,repair(bad))
