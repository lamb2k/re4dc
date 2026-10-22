"""Mutation tests for the narrowly bounded data-only dependency preparer."""
import copy
import hashlib
import struct
import unittest
import zlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import coupled_sidecars as C


def texture(w, h, flags, size, fmt=0, material=b'PS2 test'):
    payload = bytes(size)
    desc = struct.pack('<64s8I', material, w, h, fmt, 144, size, flags, 2, 0)
    return struct.pack('<8s10I', b'RE4DCTX\0', 2, 48, 96, 1, 48, 144, size,
                       zlib.crc32(payload), 1, 0) + desc + payload


def world(parts, placement=None):
    placement = placement or struct.pack('<HH12f', 0, 0, 1,0,0,0, 0,1,0,0, 0,0,1,0)
    body = b''.join(struct.pack('<IIHH4B', *p) for p in parts) + placement
    return struct.pack('<4s7I', b'R4PW', 1, 1, len(parts), 1, zlib.crc32(body), 0, 0) + body


class Coupled(unittest.TestCase):
    def setUp(self):
        self.old = texture(128,64,0,4096)
        self.new = texture(64,64,4,3414)
        self.parts = [(1,2,128,64,0,0,1,0), (3,4,16,16,2,0,1,0)]
        self.before = world(self.parts)
        after = [(5,6,*self.parts[0][2:]), self.parts[1]]
        self.after = world(after)
        crc = struct.unpack_from('<I',self.before,20)[0]
        self.ids = struct.pack('<4s3I',b'R4ID',1,1,crc)+bytes(16)
        self.classes = struct.pack('<4s5I',b'R4TC',1,1,2,crc,zlib.crc32(bytes([1,8])))+bytes([1,8,0,0])
        # Opaque synthetic geometry bytes: only the immutability/header contract
        # is exercised here; target mesh validity remains the existing image gate.
        body = bytes(32)
        self.mesh = struct.pack('<4s19I',b'R4IM',3,112,zlib.crc32(body),1,2,*([0]*14))+body
        self.spec = dict(original_key='00000001-00000002',scoped_key='00000005-00000006',
                         source_sha256=C.digest(self.old),candidate_sha256=C.digest(self.new),
                         candidate_crc32=struct.unpack_from('<I',self.new,36)[0])
        self.args = dict(old_world=self.before,new_world=self.after,old_ids=self.ids,old_classes=self.classes,
                         old_mesh=self.mesh,new_mesh=self.mesh,
                         old_textures={'00000001-00000002':self.old,'00000003-00000004':b'unchanged'},
                         new_textures={'00000005-00000006':self.new,'00000003-00000004':b'unchanged'},
                         selected=[self.spec],expected_mesh_sha256=C.digest(self.mesh),
                         expected_originals={k:C.digest(v)for k,v in [('world',self.before),('ids',self.ids),('classes',self.classes)]})

    def test_only_four_byte_header_fields(self):
        result,proof=C.prepare(**self.args)
        self.assertLessEqual(set(C.changes(self.ids,result['ids'])),set(range(12,16)))
        self.assertLessEqual(set(C.changes(self.classes,result['classes'])),set(range(16,20)))
        self.assertEqual(result['ids'][16:],self.ids[16:])
        self.assertEqual(result['classes'][20:],self.classes[20:])
        self.assertEqual(struct.unpack_from('<I',result['ids'],12)[0],C.world(self.after)[0][5])
        self.assertEqual(struct.unpack_from('<I',result['classes'],16)[0],C.world(self.after)[0][5])
        self.assertFalse(proof['full_equivalence'])

    def test_identical_control_is_byte_exact(self):
        self.args.update(new_world=self.before,new_textures=self.args['old_textures'],selected=[])
        result,_=C.prepare(**self.args)
        self.assertEqual(result,dict(ids=self.ids,classes=self.classes))

    def test_geometry_change_rejected(self):
        self.args['new_mesh']=self.mesh[:-1]+b'x'
        with self.assertRaisesRegex(ValueError,'geometry identity'):C.prepare(**self.args)

    def test_geometry_pin_rejected(self):
        self.args['expected_mesh_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'geometry identity'):C.prepare(**self.args)

    def test_placement_change_rejected(self):
        self.args['new_world']=world([(5,6,*self.parts[0][2:]),self.parts[1]],bytes(52))
        with self.assertRaisesRegex(ValueError,'placements'):C.prepare(**self.args)

    def test_pass_or_logical_dimension_change_rejected(self):
        for field,value in [(2,64),(4,1),(7,1)]:
            p=list((5,6,*self.parts[0][2:]));p[field]=value
            self.args['new_world']=world([p,self.parts[1]])
            with self.assertRaisesRegex(ValueError,'part material'):C.prepare(**self.args)

    def test_unlisted_key_rejected(self):
        self.args['selected']=[]
        with self.assertRaisesRegex(ValueError,'unqualified key'):C.prepare(**self.args)

    def test_package_identity_change_rejected(self):
        self.args['new_textures']['00000005-00000006']=self.new[:-1]+b'x'
        with self.assertRaisesRegex(ValueError,'identity changed'):C.prepare(**self.args)

    def test_changed_unselected_texture_rejected(self):
        self.args['new_textures']['00000003-00000004']=b'changed'
        with self.assertRaisesRegex(ValueError,'unchanged-part texture'):C.prepare(**self.args)

    def test_missing_unselected_texture_rejected(self):
        del self.args['new_textures']['00000003-00000004']
        with self.assertRaisesRegex(ValueError,'unchanged-part texture'):C.prepare(**self.args)

    def test_nonopaque_layout_rejected_even_if_repinned(self):
        altered=texture(64,64,4,3414,fmt=1)
        self.args['new_textures']['00000005-00000006']=altered
        self.spec['candidate_sha256']=C.digest(altered)
        with self.assertRaisesRegex(ValueError,'RGB565'):C.prepare(**self.args)

    def test_wrong_ids_binding_rejected(self):
        self.args['old_ids']=self.ids[:12]+bytes(4)+self.ids[16:]
        with self.assertRaisesRegex(ValueError,'original sidecar identity'):C.prepare(**self.args)

    def test_wrong_class_binding_rejected(self):
        self.args['old_classes']=self.classes[:16]+bytes(4)+self.classes[20:]
        with self.assertRaisesRegex(ValueError,'original sidecar identity'):C.prepare(**self.args)

    def test_class_payload_corruption_rejected(self):
        self.args['old_classes']=self.classes[:-3]+bytes([7,0,0])
        self.args['expected_originals']['classes']=C.digest(self.args['old_classes'])
        with self.assertRaisesRegex(ValueError,'class CRC'):C.prepare(**self.args)

    def test_changed_part_class_semantics_rejected(self):
        cls=bytes([4,8])
        self.args['old_classes']=self.classes[:20]+struct.pack('<I',zlib.crc32(cls))+cls+bytes(2)
        self.args['expected_originals']['classes']=C.digest(self.args['old_classes'])
        with self.assertRaisesRegex(ValueError,'class semantics'):C.prepare(**self.args)

    def test_world_crc_corruption_rejected(self):
        self.args['new_world']=self.after[:-1]+b'x'
        with self.assertRaisesRegex(ValueError,'world CRC'):C.prepare(**self.args)

    def test_duplicate_mapping_rejected(self):
        self.args['selected']=[self.spec,self.spec]
        with self.assertRaisesRegex(ValueError,'duplicate original'):C.prepare(**self.args)

    def test_texture_slot_zero_is_valid(self):
        p=list(self.parts[0]);p[6]=0
        before=world([p,self.parts[1]])
        after=world([(5,6,*p[2:]),self.parts[1]])
        crc=C.world(before)[0][5]
        self.args.update(old_world=before,new_world=after,
                         old_ids=self.ids[:12]+struct.pack('<I',crc)+self.ids[16:],
                         old_classes=self.classes[:16]+struct.pack('<I',crc)+self.classes[20:])
        self.args['expected_originals']={k:C.digest(v)for k,v in [('world',before),('ids',self.args['old_ids']),('classes',self.args['old_classes'])]}
        result,proof=C.prepare(**self.args)
        self.assertEqual(proof['changed_parts'],[0])

if __name__=='__main__':unittest.main()
