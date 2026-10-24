#!/usr/bin/env python3
"""Host semantic/admission tests; private game data is optional and never checked in."""
import struct
import unittest
import zlib
from offline_dedup import MARKER, Package, convert, validate_pair


def fixture():
    # Deliberate UV/colour seams, a repeat read by a later isolated group, and strip winding.
    c=[(10,20,30,4,5,0xffff),(40,50,60,6,7,0x8123),
       (10,20,30,8,9,0x9234),(70,80,90,10,11,0xa345),
       (40,50,60,12,13,0xb456)]
    strips=bytes([3,0,1,2,3,2,3,4]);n=len(c)
    let=struct.pack('<IIIHH6H',0,0,len(strips),n,2,10,20,30,70,80,90)
    vert=b''.join(struct.pack('<6H',*v) for v in c)
    part=struct.pack('<IIBBBBII4f',0,0,0,255,0,0,0,1,0,0,1,1)
    plod=176+12*n+len(strips)+4
    lod=struct.pack('<8I',0,0,plod,plod+8,plod+8,0,0,0)
    body=lod+part+let+vert+strips+bytes(4)+bytes(8)
    h=struct.pack('<4s19I',b'R4IM',3,80+len(body),zlib.crc32(body),0,1,1,n,len(strips),1,
                  112,112,148,176,176+12*n,176+12*n+len(strips),2,0,0,0)
    mesh=h+body
    recs=struct.pack('<8H',10,20,30,40,50,60,4,0|(2<<8))+struct.pack('<8H',10,20,30,70,80,90,8,2|(4<<8))
    sg=struct.pack('<4s7I',b'R4SG',1,1,2,zlib.crc32(body),len(mesh),123,zlib.crc32(recs))+recs
    return mesh,sg


def repair_crc(data):
    d=bytearray(data);struct.pack_into('<I',d,12,zlib.crc32(d[80:]));return bytes(d)


class OfflineTests(unittest.TestCase):
    def test_ordered_corner_seams_and_group_priming(self):
        a,sg=fixture();b,g,st=convert(a,sg);validate_pair(a,b,g)
        self.assertEqual(st['repeats'],2)
        self.assertEqual(len(a),len(b));self.assertEqual(len(sg),len(g))
        self.assertEqual(convert(a,sg),(b,g,st))
        p=Package(b,True);l=p.lets[0]
        self.assertEqual(l['corners'][3][3:],(8,9,0x9234))
        self.assertEqual(l['corners'][4][3:],(12,13,0xb456))
        # The second group's originals are repeat0, unique2, repeat1: firsts0..2 must be primed.
        self.assertEqual(struct.unpack_from('<H',g,32+16+14)[0],0|(2<<8))

    def test_default_reader_and_unknown_marker_refuse(self):
        a,sg=fixture();b,_,_=convert(a,sg)
        with self.assertRaises(ValueError):Package(b)
        d=bytearray(b);struct.pack_into('<I',d,76,MARKER^1)
        with self.assertRaises(ValueError):Package(d,True)

    def test_bad_repeat_source_tag_and_count_refuse(self):
        a,sg=fixture();b,_,_=convert(a,sg);p=Package(b,True);l=p.lets[0]
        for offset,value in ((p.h[13]+12*3,3),(p.h[13]+12*3+2,0),(l['offset']+14,5<<7|2)):
            with self.subTest(offset=offset):
                d=bytearray(b);struct.pack_into('<H',d,offset,value)
                with self.assertRaises(ValueError):Package(repair_crc(d),True)

    def test_bad_crc_and_stale_groups_refuse(self):
        a,sg=fixture();d=bytearray(a);d[-1]^=1
        with self.assertRaises(ValueError):convert(d,sg)
        d=bytearray(sg);d[16]^=1
        with self.assertRaises(ValueError):convert(a,d)

    def test_equal_size_foreign_source_refused(self):
        a,sg=fixture();b,_,_=convert(a,sg);p=Package(a)
        wrong=bytearray(a);wrong[p.h[13]]^=1;wrong=repair_crc(wrong)
        self.assertEqual(len(wrong),len(a))
        with self.assertRaises(ValueError):validate_pair(wrong,b)

    def test_source_chains_cannot_be_encoded(self):
        a,sg=fixture();b,_,_=convert(a,sg);p=Package(b,True)
        d=bytearray(b);struct.pack_into('<H',d,p.h[13]+12*4,3)
        with self.assertRaises(ValueError):Package(repair_crc(d),True)


if __name__=='__main__':unittest.main()