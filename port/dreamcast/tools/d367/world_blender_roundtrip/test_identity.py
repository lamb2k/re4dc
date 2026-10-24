#!/usr/bin/env python3
"""Host structural/stale dependency controls; real Blender controls are separate."""
from copy import deepcopy
from pathlib import Path
import struct
import tempfile
import unittest

import fixtures
import package as p
import sidecars


def check(files):
    d=p.decode(files['ps2-world.re4mesh'],files['ps2-world.r4pw'])
    return sidecars.rebuild(files,d,p.serialize_mesh(d),p.serialize_policy(d))


def patch(files,name,offset,fmt,value,repair=None):
    result=dict(files);b=bytearray(result[name]);struct.pack_into(fmt,b,offset,value)
    if repair=='mesh':struct.pack_into('<I',b,12,p.crc(b[80:]))
    if repair=='policy':struct.pack_into('<I',b,20,p.crc(b[32:]))
    if repair=='room':struct.pack_into('<I',b,48,p.crc(b[64:]))
    if repair=='groups':struct.pack_into('<I',b,28,p.crc(b[32:]))
    result[name]=bytes(b);return result


class IdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.files=fixtures.complete_files()

    def test_all_known_companions_rebuilt_identically(self):
        self.assertEqual(check(self.files),self.files)

    def test_legacy_VIS_OCCL_records(self):
        f=fixtures.complete_files(True);self.assertEqual(check(f),f)

    def test_existing_converter_output(self):
        f=fixtures.converter_files();self.assertEqual(check(f),f)

    def test_every_file_is_reconstructed_not_source_blob_returned(self):
        d=p.decode(self.files['ps2-world.re4mesh'],self.files['ps2-world.r4pw'])
        d['vertices'][0][0]+=1
        self.assertNotEqual(p.serialize_mesh(d),self.files['ps2-world.re4mesh'])
        with self.assertRaisesRegex(ValueError,'unchanged geometry'):
            sidecars.rebuild(self.files,d,p.serialize_mesh(d),p.serialize_policy(d))

    def test_corrupt_and_unsupported_world_fields(self):
        f=self.files;h=p.crb.HEADER.unpack_from(f['ps2-world.re4mesh'])
        cases=[('crc',len(f['ps2-world.re4mesh'])-1,'B',1,None),
            ('version',4,'I',2,'mesh'),('normal encoding',64,'I',1,'mesh'),
            ('extension',68,'I',128,'mesh'),('dedup marker',76,'I',0x334f4453,'mesh'),
            ('runtime tables',108,'I',128,'mesh'),('NaN grid',h[10]+20,'f',float('nan'),'mesh'),
            ('zero step',h[10]+32,'f',0,'mesh'),('bad part state',h[11]+11,'B',1,'mesh'),
            ('UV scale',h[11]+28,'f',0,'mesh'),('bad strip index',h[14]+1,'B',255,'mesh'),
            ('bad strip length',h[14],'B',2,'mesh'),('bad meshlet count',h[12]+12,'H',257,'mesh'),
            ('nonzero padding',112,'B',1,'mesh'),('bad class',p.crb.LOD_HEADER.unpack_from(f['ps2-world.re4mesh'],80)[5],'B',8,'mesh')]
        for label,offset,fmt,value,repair in cases:
            with self.subTest(label=label),self.assertRaises(ValueError):
                check(patch(f,'ps2-world.re4mesh',offset,'<'+fmt,value,repair))

    def test_corrupt_policy(self):
        cases=[('crc',20,'I',0,None),('pass',44,'B',3,'policy'),('cull',45,'B',3,'policy'),
               ('width',40,'H',0,'policy'),('reserved',24,'I',1,'policy'),
               ('placement mesh',80,'H',99,'policy'),('affine inf',84,'f',float('inf'),'policy')]
        for label,offset,fmt,value,repair in cases:
            with self.subTest(label=label),self.assertRaises(ValueError):
                check(patch(self.files,'ps2-world.r4pw',offset,'<'+fmt,value,repair))

    def test_stale_each_companion(self):
        for name,offset in [('ps2-world.ids',12),('ps2-world.r4tc',16),('ps2-world.r4sg',16),
                ('ps2-world.pvs',8),('interior.cell',8),('ps2-world.occl',8)]:
            with self.subTest(name=name),self.assertRaises(ValueError):
                check(patch(self.files,name,offset,'<I',0))

    def test_companion_internal_controls(self):
        for name,offset,fmt,value,repair in [
            ('ps2-world.ids',31,'B',1,None),('ps2-world.r4tc',8,'I',99,None),
            ('ps2-world.r4tc',20,'I',0,None),('ps2-world.r4sg',32,'H',99,'groups'),
            ('ps2-world.r4sg',44,'H',2,'groups'),('ps2-world.pvs',20,'I',99,None),
            ('ps2-world.pvs',64,'H',10,None),('ps2-world.pvs',72,'B',255,None),
            ('interior.cell',56,'H',1,None),('ps2-world.occl',20,'I',1,None),
            ('far-shell.fsh',24,'I',0,None),('far-shell.fsh',4,'I',3,None),
            ('room.r4rc',48,'I',0,None),('room.r4rc',64,'4s',b'FAKE','room'),
            ('room.r4rc',72,'I',1,'room')]:
            with self.subTest(name=name,offset=offset),self.assertRaises(ValueError):
                check(patch(self.files,name,offset,'<'+fmt,value,repair))

    def test_stale_builder_report(self):
        import json
        files=dict(self.files);r=json.loads(files['ps2-world.json']);r['re4mesh_sha256']='0'*64
        files['ps2-world.json']=json.dumps(r,indent=1).encode()
        with self.assertRaisesRegex(ValueError,'stale builder report'):check(files)

    def test_every_room_dependency_stale(self):
        b=self.files['room.r4rc'];n=struct.unpack_from('<I',b,12)[0]
        offsets={}
        for i in range(n):
            tag,_,_,off,*_=struct.unpack_from('<4sHHIIIIII',b,64+32*i);offsets[tag]=off
        for tag,rel in [(b'SRCB',8),(b'VIS\0',16),(b'OCCL',12),(b'SCNK',8),
                         (b'SCDD',0),(b'SCCN',0),(b'SCPS',0)]:
            with self.subTest(tag=tag),self.assertRaises(ValueError):
                check(patch(self.files,'room.r4rc',offsets[tag]+rel,'<I',0,'room'))

    def test_unknown_and_unsupported_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)/'bundle';fixtures.write(d,self.files)
            for name in ('new-proof.bin','ps2-world.re4mesh.dd3'):
                f=d/name;f.write_bytes(b'unknown')
                with self.subTest(name=name),self.assertRaises(ValueError):sidecars.inventory(d)
                f.unlink()
            (d/'alias').symlink_to(d/'ps2-world.ids')
            with self.assertRaises(ValueError):sidecars.inventory(d)


if __name__=='__main__':unittest.main()
