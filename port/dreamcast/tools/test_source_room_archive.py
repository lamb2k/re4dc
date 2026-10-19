"""Asset-free guards for explicit original room sources; no runtime policy changes."""
from pathlib import Path
import copy
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

T = Path(__file__).resolve().parent
sys.path[:0] = [str(T), str(T.parents[2] / 'tools')]
from source_room_archive import (KIND, TaggedRoomArchive, room_name, source_pins,
                                 room_origin, prove_room_decoding, digest)


def bare(endian='>'):
    return struct.pack(endian + '4I2I', 2, 0, 0, 0, 32, 40) + b'BIN\0TPL\0' + b'original' + b'textures'

class RoomSources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'r226.arc'
        self.path.write_bytes(bare())
        self.c = dict(cache='original/r226.das', bytes=4, sha256='a'*64, decoding='room_smd.decode_das')
        self.audit = dict(source_archive_kind=KIND, source_room='r226', source_container=self.c)
        self.src = dict(source_archive_kind=KIND, source_room='r226', source_archive='r226', source_container=copy.deepcopy(self.c))
    def tearDown(self):
        self.tmp.cleanup()
    def test_exact_original_entries(self):
        a = TaggedRoomArchive(self.path, 'r226')
        self.assertEqual([(x.arc_no, x.tag, x.data) for x in a.entries()], [(4,'BIN',b'original'),(5,'TPL',b'textures')])
    def test_reject_little_endian_converted_room(self):
        self.path.write_bytes(bare('<'))
        with self.assertRaises(ValueError): TaggedRoomArchive(self.path,'r226')
    def test_reject_header_overlap(self):
        d=bytearray(bare());struct.pack_into('>I',d,16,16);self.path.write_bytes(d)
        with self.assertRaises(ValueError): TaggedRoomArchive(self.path,'r226')
    def test_reject_entry_past_end(self):
        d=bytearray(bare());struct.pack_into('>I',d,20,500);self.path.write_bytes(d)
        with self.assertRaises(ValueError): TaggedRoomArchive(self.path,'r226')
    def test_preserve_source_duplicate_ordinals(self):
        d=bytearray(bare());struct.pack_into('>I',d,20,32);self.path.write_bytes(d)
        a=TaggedRoomArchive(self.path,'r226');self.assertEqual(a.entry(0).data,a.entry(1).data)
        self.assertEqual([x.index for x in a.entries()],[0,1])
    def test_reject_ordinal_wrap_or_negative(self):
        a=TaggedRoomArchive(self.path,'r226')
        for x in [-1,2,True]:
            with self.subTest(x=x),self.assertRaises(ValueError):a.entry(x)
    def test_reject_implicit_enemy_or_noncanonical_room(self):
        for x in ['em37','R226','r226/../em37',None]:
            with self.subTest(x=x),self.assertRaises(ValueError):room_name(x)
    def test_require_all_original_digest_pins(self):
        p=dict(ps2_sha256='a'*64,gc_container_sha256='b'*64,gc_archive_sha256='c'*64)
        self.assertEqual(source_pins(p),p)
        for q in [dict(p,extra='d'*64),{k:v for k,v in p.items() if k!='gc_container_sha256'},dict(p,ps2_sha256='wrong')]:
            with self.assertRaises(ValueError):source_pins(q)
    def test_exact_source_origin(self):
        self.assertEqual(room_origin(self.audit,self.src,'r226'),('r226',self.c))
    def test_reject_source_room_or_kind_alias(self):
        for key,value in [('source_room','r225'),('source_archive','em37'),('source_archive_kind','enemy-drs')]:
            src=copy.deepcopy(self.src);src[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):room_origin(self.audit,src,'r226')
    def test_reject_container_identity_mismatch(self):
        src=copy.deepcopy(self.src);src['source_container']['sha256']='b'*64
        with self.assertRaises(ValueError):room_origin(self.audit,src,'r226')
    def test_reject_missing_or_unproved_decoding(self):
        for key,value in [('bytes',True),('decoding','unproved decoder'),('sha256','bad')]:
            a=copy.deepcopy(self.audit);s=copy.deepcopy(self.src);a['source_container'][key]=value;s['source_container'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):room_origin(a,s,'r226')
    def test_original_container_link_is_byte_exact(self):
        p=Path(self.tmp.name)/'r226.das';p.write_bytes(b'DAS!');c=dict(bytes=4,sha256=digest(b'DAS!'))
        with patch('room_smd.decode_das',return_value=bare()):prove_room_decoding(p,self.path,c)
        with patch('room_smd.decode_das',return_value=bare()+b'changed'):
            with self.assertRaises(ValueError):prove_room_decoding(p,self.path,c)
        p.write_bytes(b'fail')
        with self.assertRaises(ValueError):prove_room_decoding(p,self.path,c)

if __name__ == '__main__':
    unittest.main()
