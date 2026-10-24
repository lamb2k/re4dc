"""Public synthetic R4IM/R4PW only; no frozen private bytes or extraction."""
from fractions import Fraction as Q
import contextlib
import io
import json
import struct
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import zlib
import strip_metadata as s

IDENTITY=(1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.)

def crc_mesh(m):struct.pack_into('<I',m,12,zlib.crc32(m[80:])&0xffffffff);return bytes(m)
def crc_policy(p):struct.pack_into('<I',p,20,zlib.crc32(p[32:])&0xffffffff);return bytes(p)

def fixture(strips=((0,1,2,3),),expected=((0,1,2),(3,2,1)),vertices=None,placements=None):
    vertices=vertices or ((0,0,3,0,0,65535),(2,0,3,1,0,65535),(0,2,3,0,1,65535),(2,2,3,1,1,65535),(9,9,9,7,7,65535))
    placements=placements or ((0,7,IDENTITY),)
    plain=b''.join(bytes((len(x),*x)) for x in strips);fs=(len(plain)+1)&~1
    stream=plain+b'\0'*(fs-len(plain))+struct.pack('<3H',2,0,3)+bytes((3,0,1,2))
    om,op,ol,ov=112,180,216,272;os_=ov+12*len(vertices);opal=(os_+len(stream)+3)&~3;opl=opal+4;oc=opl+8;olv=oc+20;total=olv+24
    m=bytearray(total);h=(b'R4IM',3,total,0,1,1,2,len(vertices),len(stream),1,om,op,ol,ov,os_,opal,2,0,0,0)
    struct.pack_into('<4s19I',m,0,*h);struct.pack_into('<8I',m,80,1,2,opl,oc,olv,0,0,0)
    struct.pack_into('<HBBHHIII12f',m,om,1,1,254,len(vertices),1,0,0,1,0,0,0,1,1,1,0,0,3,2,2,3)
    struct.pack_into('<IIBBBBII4f',m,op,0,32,5,255,0,0,0,2,0,0,1,1)
    struct.pack_into('<IIIHH6H',m,ol,0,0,len(plain),4,len(strips),0,0,3,2,2,3)
    struct.pack_into('<IIIHH6H',m,ol+28,0,fs,4,3,32769,0,0,3,2,2,3)
    for i,v in enumerate(vertices):struct.pack_into('<6H',m,ov+12*i,*v)
    m[os_:os_+len(stream)]=stream;struct.pack_into('<II',m,opl,0,1);struct.pack_into('<6HII',m,oc,0,0,3,2,2,3,0,2)
    struct.pack_into('<IIfIIf',m,olv,0,1,0.,1,1,1.);m=crc_mesh(m)
    p=bytearray(32+16+52*len(placements));struct.pack_into('<4s7I',p,0,b'R4PW',1,len(placements),1,1,0,0,0)
    struct.pack_into('<IIHH4B',p,32,0x12345678,0x87654321,128,128,0,2,5,0)
    ids=bytearray(256)
    for i,(mesh,field,affine) in enumerate(placements):struct.pack_into('<HH12f',p,48+52*i,mesh,field,*affine);ids[field]=254
    p=crc_policy(p);h,lod=s.header(m)
    def expected_target(pi=0,level=0):
        mesh,field,affine=placements[pi];physical=(pi,field,0,0,level,level);triangles=expected if level==0 else ((0,1,2),);pool=(0,1,2,3) if level==0 else (2,0,3)
        operands=struct.pack('<12f',*affine)+struct.pack('<6f',0,0,0,1,1,1);affsha=s.sha(operands);parents=[];records=[]
        for ordinal,tri in enumerate(triangles):
            xyz=tuple(tuple(Q(affine[4*i+3])+sum(Q(affine[4*i+k])*vertices[pool[j]][k] for k in range(3)) for i in range(3)) for j in tri)
            occ=(*physical,ordinal);records.append((occ,tri,affsha,xyz));parents.append(dict(occurrence=occ,indices=tri,affine_sha256=affsha,positions_exact=tuple(tuple(str(x) for x in v) for v in xyz)))
        return dict(rank=pi,physical=physical,authored_counts=(1,1),affine_operand_bytes_hex=operands.hex(),affine_sha256=affsha,parents=parents,original_target=dict(owner=254),source_binding_sha256='d'*64,original_inventory_sha256=s.digest(tuple(records),'d'*64))
    return m,p,bytes(ids),h,lod,expected_target

class Controls(unittest.TestCase):
    def extract(self,f,t=None):
        m,p,ids,h,lod,make=f;t=[make()] if t is None else t;allow=tuple((x['rank'],*x['physical'],len(x['parents'])) for x in t)
        return s.extract(m,p,p,ids,dict(targets=t),allow,time.monotonic()+30)
    def test_plain_exact_restart_parity_and_full_inventory(self):
        f=fixture();row=self.extract(f)['targets'][0]
        self.assertEqual([x['indices'] for x in row['originals']],[(0,1,2),(3,2,1)])
        self.assertEqual(row['originals'][1]['native_cyclic_indices'],(2,1,3));self.assertEqual(row['originals'][1]['strip_position'],(0,1,True))
        self.assertEqual(row['source_bytes']['strip_stream'],5);self.assertEqual(len(bytes.fromhex(row['affine72_bytes'])),72)
        self.assertEqual(row['optional_strip_groups'],None);self.assertIsNone(row['current_transform_corners']);self.assertIsNone(row['modelled_ms'])
    def test_indexed_pool_offsets_separate_from_strip_bytes(self):
        f=fixture();row=self.extract(f,[f[-1](level=1)])['targets'][0]
        self.assertTrue(row['indexed']);self.assertEqual(row['pool_offsets'],(2,0,3));self.assertEqual([x['global_pool'] for x in row['corners']],[2,0,3])
        self.assertEqual(row['source_bytes']['pool_offset_table'],6);self.assertEqual(row['source_bytes']['strip_stream'],4)
    def test_restarts_reset_parity_and_degenerate_connectors_are_never_omitted(self):
        f=fixture(((0,1,2),(1,2,3)),((0,1,2),(1,2,3)));r=self.extract(f)['targets'][0]
        self.assertEqual(len(r['strips']),2);self.assertEqual([x['strip_position'] for x in r['originals']],[(0,0,False),(1,0,False)])
        f=fixture(((0,1,1,2,3),),((0,1,1),(2,1,1),(1,2,3)));r=self.extract(f)['targets'][0]
        self.assertEqual(len(r['originals']),3);self.assertEqual([x['repeated_index_degenerate'] for x in r['originals']],[True,True,False])
    def test_attribute_seams_and_shared_placements_are_not_welded(self):
        vs=((0,0,3,0,0,65535),(0,0,3,99,1,1234),(0,2,3,0,1,65535),(2,2,3,1,1,65535))
        f=fixture(vertices=vs);r=self.extract(f)['targets'][0];self.assertNotEqual(r['corners'][0]['bytes'],r['corners'][1]['bytes']);self.assertEqual(r['corners'][0]['quantized'][:3],r['corners'][1]['quantized'][:3])
        moved=list(IDENTITY);moved[3]=10.;f=fixture(placements=((0,7,IDENTITY),(0,8,tuple(moved))));r=self.extract(f,[f[-1](0),f[-1](1)])
        self.assertEqual(r['target_count'],2);self.assertNotEqual(r['targets'][0]['affine_sha256'],r['targets'][1]['affine_sha256']);self.assertEqual(r['targets'][0]['meshlet_bytes'],r['targets'][1]['meshlet_bytes'])
    def test_winding_missing_duplicate_affine_owner_and_material_correspondence(self):
        f=fixture();base=f[-1]()
        import copy
        for kind in ('winding','missing','duplicate','affine','position','owner','digest','lod'):
            t=copy.deepcopy(base)
            if kind=='winding':t['parents'][1]['indices']=(1,2,3)
            if kind=='missing':t['parents']=t['parents'][:-1]
            if kind=='duplicate':t['parents'][1]=t['parents'][0]
            if kind=='affine':t['affine_sha256']='0'*64
            if kind=='position':t['parents'][0]['positions_exact']=(('99','0','3'),)*3
            if kind=='owner':t['original_target']['owner']=255
            if kind=='digest':t['original_inventory_sha256']='0'*64
            if kind=='lod':t['authored_counts']=(2,0)
            with self.subTest(kind=kind),self.assertRaises(s.Refuse):self.extract(f,[t])
        row=self.extract(f)['targets'][0];self.assertEqual(row['material']['crc'],0x12345678);self.assertEqual(row['material']['cull'],2);self.assertEqual(row['material']['runtime_header_commit'],'UNQUALIFIED')
    def test_extent_overflow_strip_bounds_and_crosspart_indexed_reference(self):
        f=fixture();m,p,ids,h,lod,make=f
        for kind in ('extent','length','index','pool','version','encoded'):
            b=bytearray(m)
            if kind=='extent':struct.pack_into('<I',b,h[12]+4,0xfffffff0)
            if kind=='length':b[h[14]]=255
            if kind=='index':b[h[14]+1]=4
            if kind=='pool':struct.pack_into('<H',b,h[14]+6,4)
            if kind=='version':struct.pack_into('<I',b,4,2)
            if kind=='encoded':struct.pack_into('<I',b,76,0x334f4453)
            b=crc_mesh(b);target=make(level=1) if kind in ('pool','version') else make()
            with self.subTest(kind=kind),self.assertRaises(s.Refuse):self.extract((b,p,ids,h,lod,make),[target])
        bad=bytearray(m);bad[-1]^=1
        with self.assertRaisesRegex(s.Refuse,'MESH_CRC'):self.extract((bytes(bad),p,ids,h,lod,make))
    def test_foreign_pool_alias_with_identical_positions_still_refuses(self):
        vertices=((0,0,3,0,0,65535),(2,0,3,1,0,65535),(0,2,3,0,1,65535),(2,2,3,1,1,65535),(0,2,3,77,77,1234))
        f=fixture(vertices=vertices);m,p,ids,h,lod,make=f;b=bytearray(m)
        # Foreign vertex4 has vertex2's position, so position/digest checks alone
        # cannot establish this part's backing/attribute identity.
        struct.pack_into('<H',b,h[14]+6,4);b=crc_mesh(b)
        with self.assertRaisesRegex(s.Refuse,'PART_VERTEX_POOL_IDENTITY'):self.extract((b,p,ids,h,lod,make),[make(level=1)])
    def sg(self,f,records):
        m,p,ids,h,lod,make=f;ph=s.policy_header(p,h);payload=b''.join(struct.pack('<8H',*g) for g in records)*h[6]
        return struct.pack('<4s7I',b'R4SG',1,h[6],len(records),h[3],len(m),ph[5],zlib.crc32(payload)&0xffffffff)+payload
    def test_sg_strict_boundaries_enclosure_and_empty_group_semantics(self):
        f=fixture();m,p,ids,h,lod,make=f;d=s.decode(m,h,0,((0,4),));ph=s.policy_header(p,h)
        good=(0,0,3,2,2,3,5,3<<8);empty=(9,9,9,0,0,0,5,65535)
        groups=s.parse_sg(self.sg(f,(good,empty)),h,ph[5],d,0);self.assertTrue(groups[1]['empty'])
        variants=((0,0,3,2,2,3,4,3<<8),(0,0,3,2,2,3,5,2<<8),(1,0,3,2,2,3,5,3<<8),(0,0,3,2,2,3,0,0))
        for record in variants:
            with self.subTest(record=record),self.assertRaises(s.Refuse):s.parse_sg(self.sg(f,(record,)),h,ph[5],d,0)
        bad=bytearray(self.sg(f,(good,)));bad[-1]^=1
        with self.assertRaisesRegex(s.Refuse,'SG_HEADER'):s.parse_sg(bytes(bad),h,ph[5],d,0)
    def test_malformed_policy_identity_crc_and_material_refuses(self):
        f=fixture();m,p,ids,h,lod,make=f
        for kind in ('crc','field','affine','material'):
            b=bytearray(p)
            if kind=='crc':b[-1]^=1
            if kind=='field':struct.pack_into('<H',b,50,8)
            if kind=='affine':struct.pack_into('<f',b,48+4+12,4.)
            if kind=='material':b[32+12]=3
            if kind!='crc':b=bytearray(crc_policy(b))
            with self.subTest(kind=kind),self.assertRaises(s.Refuse):self.extract((m,bytes(b),ids,h,lod,make))
    def test_whole_caps_no_truncation_and_deadline(self):
        f=fixture()
        with patch.dict(s.LIMITS,corner_records=3):
            with self.assertRaisesRegex(s.Refuse,'WHOLE_TARGET_RECORD_CAP'):self.extract(f)
        with self.assertRaisesRegex(s.Refuse,'COMPUTE_DEADLINE'):s.extract(f[0],f[1],f[1],f[2],dict(targets=[f[-1]()]),((0,0,7,0,0,0,0,2),),0)
        with self.assertRaises(s.Refuse):s.extent(0xfffffff0,100,28,392,112)
    def test_inventory_digest_matches_frozen_serializer_shape_not_subset(self):
        binding='d'*64;record=(((0,7,0,0,0,0,0),(0,1,2),'a'*64,((Q(0),Q(0),Q(3)),(Q(2),Q(0),Q(3)),(Q(0),Q(2),Q(3)))),)
        expected_record=[[0,7,0,0,0,0,0],[0,1,2],'a'*64,[['0','0','3'],['2','0','3'],['0','2','3']]]
        expected=json.dumps([binding,[expected_record]],separators=(',',':')).encode()
        self.assertEqual(s.digest(record,binding),s.sha(expected))
    def test_signature_runs_are_existing_windows_not_emitted_strips(self):
        row=self.extract(fixture())['targets'][0]
        groups=dict(groups=[dict(mask=0,ordinals=[0],original_oriented_indices=[(0,1,2)]),dict(mask=2,ordinals=[1],original_oriented_indices=[(3,2,1)])])
        r=s.signature_runs(row,groups,3)
        self.assertEqual(r['signature_run_count'],2);self.assertEqual(r['boundaries_inside_existing_strips'],1)
        self.assertEqual(r['source_corner_window_references'],6)
        self.assertEqual([x['source_corner_window'] for x in r['source_strip_signature_runs']],[(0,1,2),(1,2,3)])
        self.assertTrue(r['source_strip_signature_runs'][1]['source_start_parity'])
        self.assertIsNone(r['source_strip_signature_runs'][1]['emitted_representation'])
        self.assertEqual(r['domains'][1]['mixed_source_strips'],1);self.assertEqual(r['domains'][1]['exclusive_covered_local_slots'],(3,))
        self.assertIsNone(r['domains'][1]['actual_transform_delta'])
        import copy
        for kind in ('missing','duplicate','winding','forbidden','empty'):
            bad=copy.deepcopy(groups)
            if kind=='missing':bad['groups']=bad['groups'][:-1]
            if kind=='duplicate':bad['groups'][1]['ordinals']=[0]
            if kind=='winding':bad['groups'][1]['original_oriented_indices']=[(1,2,3)]
            if kind=='forbidden':bad['groups'][1]['mask']=4
            if kind=='empty':bad['groups'].append(dict(mask=1,ordinals=[],original_oriented_indices=[]))
            with self.subTest(kind=kind),self.assertRaises(s.Refuse):s.signature_runs(row,bad,3)
    def test_source_backing_bytes_distinct_from_physical_references(self):
        moved=list(IDENTITY);moved[3]=10.;f=fixture(placements=((0,7,IDENTITY),(0,8,tuple(moved))))
        r=self.extract(f,[f[-1](0),f[-1](1)]);storage=r['selected_source_storage']
        self.assertEqual(storage['unique_strip_stream_bytes'],5);self.assertEqual(storage['unique_compact_vertex_bytes'],48)
        self.assertEqual(storage['physical_compact_corner_reference_bytes'],96);self.assertEqual(storage['unique_meshlet_header_bytes'],28)
        self.assertIsNone(storage['new_runtime_representation'])
        self.assertEqual(s.union_bytes(((10,20),(15,25),(25,25),(10,20))),15)
    def test_fixed_input_total_and_authentication_match_plan_without_private_reads(self):
        self.assertEqual(len(s.ALLOWLIST),25);self.assertEqual(sum(x[-1] for x in s.ALLOWLIST),889)
        self.assertEqual(sum(x[1] for x in s.RAW.values()),12376296);self.assertLess(sum(x[1] for x in s.RAW.values()),s.LIMITS['input_bytes'])
        self.assertEqual(s.RAW['coverage'][2],'3de238f0ab60d055e22bfc68e7ef3a32aac813751ad5941487ceab37068c2037')
        self.assertEqual(s.RAW['prepared'][1],4891119)
        with patch.object(s,'read_pin',side_effect=AssertionError('private read')):
            with self.assertRaisesRegex(s.Refuse,'FROZEN_COMPLETE_COVERAGE'):s.attach_coverage({},dict(source='OLD'),{})
    def test_pinned_reader_refuses_symlinks_size_drift_and_mismatched_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);p=d/'input';p.write_bytes(b'PUBLIC');pin=(str(p),6,s.sha(b'PUBLIC'))
            self.assertEqual(s.read_pin(pin),b'PUBLIC')
            import os
            actual_read=os.read;changed=False
            def change_stamp(fd,n):
                nonlocal changed
                block=actual_read(fd,n)
                if not changed:
                    before=p.stat();os.utime(p,ns=(before.st_atime_ns,before.st_mtime_ns+1000000));changed=True
                return block
            with patch.object(s.os,'read',side_effect=change_stamp):
                with self.assertRaisesRegex(s.Refuse,'PIN_BYTES_OR_STAMP_CHANGED'):s.read_pin(pin)
            for wrong in ((str(p),5,pin[2]),(str(p),6,'0'*64)):
                with self.assertRaises(s.Refuse):s.read_pin(wrong)
            link=d/'alias';link.symlink_to(p)
            with self.assertRaises(OSError):s.read_pin((str(link),6,pin[2]))
    def test_default_and_missing_grant_never_read_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);argv=['tool','--repo',str(d/'repo'),'--expected-source','1'*40,'--out',str(d/'out')]
            with patch.object(sys,'argv',argv),patch.object(s,'own_sources',return_value={}),patch.object(s,'read_pin',side_effect=AssertionError('private read')),contextlib.redirect_stdout(io.StringIO()):s.main()
            r=json.loads((d/'out/report.json').read_bytes());self.assertEqual(r['private_input_reads'],0);self.assertEqual(r['classification'],'HELD_SOURCE_ONLY_ZERO_PRIVATE_READS')
            argv[-1]=str(d/'execute')
            with patch.object(sys,'argv',argv+['--execute']),patch.object(s,'own_sources',return_value={}),patch.object(s,'read_pin',side_effect=AssertionError('private read')):
                with self.assertRaisesRegex(s.Refuse,'NEW_ROOT_GRANT'):s.main()
    def test_root_grant_exact_inputs_scope_caps_paths_only_public_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);review=d/'review';review.write_bytes(b'PUBLIC REVIEW FIXTURE');grant=d/'grant'
            args=types.SimpleNamespace(expected_source='1'*40,review=review,review_sha256=s.sha(review.read_bytes()),grant=grant,grant_sha256=None,out=d/'out')
            value=json.loads(json.dumps(s.grant_binding(args.expected_source,args.review_sha256,args.out)))
            for kind in ('profile','path','caps','input','roster'):
                v=json.loads(json.dumps(value))
                if kind=='profile':v['profile']='OLD'
                if kind=='path':v['output']=str(d/'foreign')
                if kind=='caps':v['limits']['strips']+=1
                if kind=='input':v['raw_inputs']['mesh'][2]='0'*64
                if kind=='roster':v['allowlist']=v['allowlist'][:-1]
                grant.write_text(json.dumps(v));args.grant_sha256=s.sha(grant.read_bytes())
                with self.assertRaises(s.Refuse):s.authorize(args)
            grant.write_text(json.dumps(value));args.grant_sha256=s.sha(grant.read_bytes());s.authorize(args)

if __name__=='__main__':unittest.main()
