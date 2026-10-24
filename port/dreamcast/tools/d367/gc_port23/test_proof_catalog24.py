#!/usr/bin/env python3
"""RAM-only selected-source/proof/allowance controls; all fixture bytes authored here."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import proof_catalog24 as p

K1, K2 = '00000001-00000002', '00000003-00000004'

class CatalogProofTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gc-proof24-',dir='/dev/shm')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name);self.store=self.root/'store';self.store.mkdir()
        self.payloads=[b'RE4DCTX\0header-PS2-name-pixels',b'RE4DCTX\0header-local-conversion']
        a,b=self.payloads;offset=64
        pak=struct.pack('<8s4I',b'RE4PAK1\0',1,2,24,64)+struct.pack('<4I',1,2,64,len(a))+struct.pack('<4I',3,4,64+len(a),len(b))
        pak+=bytes(64-len(pak))+a+b
        self.pack=self.store/'tex.pak';self.pack.write_bytes(pak)
        self.manifest={'dc/tex.pak':{'size':len(pak),'sha256':p.digest(pak)}}
        self.selection={'schema':1,'manifest_sha256':p.digest(p.encode(self.manifest)),'providers':[{'provider':'texpak','asset':'dc/tex.pak','path':str(self.pack)}]}
        self.evidence=self.store/'review.txt';self.evidence.write_text('Exact original pixel chain independently reviewed.\n')
    def ref(self,path):return {'path':str(path),'sha256':p.digest(path.read_bytes())}
    def generate(self,proof=None,baseline=None,requested=None,proposals=None):
        return p.generate(p.encode(self.selection),p.encode(self.manifest),[self.store],*[p.encode(x) if x is not None else None for x in [proof,baseline,requested,proposals]])
    def proof(self):
        return {'schema':1,'selection_sha256':p.digest(p.encode(self.selection)),'entries':[{'kind':'texture','id':K1,'sha256':p.digest(self.payloads[0]),'provenance':'ps2','owner':'independent-review','reason':'Exact payload origin chain reviewed','reviewed':True,'chain':[self.ref(self.evidence)]}]}
    def allowance(self,room='0100',identity=K1,sha=None):
        return {'room':room,'kind':'texture','id':identity,'sha256':sha or p.digest(self.payloads[0]),'provenance':'unknown','reason':'Historical exact load only','owner':'gc-port23','evidence':'Pinned old audit; no emitted-use claim'}
    def envelope(self,*rows):return {'schema':1,'entries':list(rows)}
    def file_provider(self,asset,raw,kind,identity=None):
        path=self.store/Path(asset).name;path.write_bytes(raw)
        sha=p.digest(raw);self.manifest[asset]={'size':len(raw),'sha256':sha}
        row={'provider':'file','asset':asset,'path':str(path),'kind':kind,'id':identity or sha[:40]}
        self.selection['providers'].append(row);self.selection['manifest_sha256']=p.digest(p.encode(self.manifest));return path,row
    def test_actual_full_members_determinism_sorted_and_header_identity(self):
        a=self.generate();self.selection['providers'].reverse();b=self.generate()
        self.assertEqual(a,b)
        self.assertEqual(a['report.json']['origins']['unknown'],2)
        self.assertEqual(a['catalog.json']['entries'][0]['sha256'],p.digest(self.payloads[0]))
        self.assertNotEqual(p.digest(self.payloads[0]),p.digest(b'pixels'))
        blob=a['gc-assets.idx'];reader=p.idx.Reader(lambda o,n:blob[o:o+n],len(blob),bytes.fromhex(a['report.json']['index_sha256']))
        self.assertIsNotNone(reader.lookup('texture',K1,bytes.fromhex(p.digest(self.payloads[0]))))
        self.assertEqual(a['allowlist.json']['entries'],[])
        self.assertFalse(a['report.json']['emission_or_coverage_or_gate_pass'])
    def test_positive_requires_pinned_selection_and_reviewed_complete_receipt(self):
        docs=self.generate(self.proof());self.assertEqual(docs['catalog.json']['entries'][0]['provenance'],'ps2')
        self.assertEqual(docs['catalog.json']['entries'][1]['provenance'],'unknown')
        self.assertEqual(docs['report.json']['production_pin_unchanged'],0)
    def test_no_name_conversion_or_boundary_provenance_inference(self):
        path,row=self.file_provider('dc/ps2-looking.bin',b'original exact model bytes','model')
        docs=self.generate();self.assertTrue(all(x['provenance']=='unknown' for x in docs['catalog.json']['entries']))
    def test_wrong_proof_payload_selection_review_and_outside_identity(self):
        for field,value in [('sha256','a'*64),('id',K2),('reviewed',False),('chain',[]),('provenance','PS2-native')]:
            q=self.proof();q['entries'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.generate(q)
        q=self.proof();q['selection_sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'selection'):self.generate(q)
    def test_receipt_digest_swap_and_duplicate_or_escape_rejected(self):
        q=self.proof();self.evidence.write_text('different evidence body')
        with self.assertRaisesRegex(ValueError,'digest'):self.generate(q)
        q=self.proof();q['entries']*=2
        with self.assertRaisesRegex(ValueError,'duplicate'):self.generate(q)
        outside=self.root/'outside';outside.write_text('outside')
        q=self.proof();q['entries'][0]['chain']=[self.ref(outside)]
        with self.assertRaisesRegex(ValueError,'outside'):self.generate(q)
    def test_source_digest_and_manifest_selection_swap(self):
        self.pack.write_bytes(self.pack.read_bytes()[:-1]+b'!')
        with self.assertRaisesRegex(ValueError,'digest'):self.generate()
        self.selection['manifest_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'manifest'):self.generate()
    def test_unknown_texture_key_revisions_do_not_gain_old_allowance(self):
        old=self.allowance();self.file_provider('dc/tex/'+K1+'.re4tex',b'RE4DCTX\0loose-different', 'texture',K1)
        docs=self.generate(baseline=self.envelope(old));self.assertEqual(len(docs['catalog.json']['entries']),3)
        self.assertEqual(docs['allowlist.json']['entries'],[old])
        loose=next(x for x in docs['catalog.json']['entries'] if x['sha256']==p.digest(b'RE4DCTX\0loose-different'))
        self.assertEqual(loose['provenance'],'unknown');self.assertNotEqual(loose['sha256'],old['sha256'])
    def test_accepted_rows_only_shrink_and_all_metadata_preserved(self):
        a=self.allowance();b=self.allowance('0111')
        ceiling=self.envelope(a,b)
        self.assertEqual(self.generate(baseline=ceiling,requested=self.envelope(a))['allowlist.json']['entries'],[a])
        for field,value in [('room','0112'),('owner','other'),('reason','new reason'),('evidence','new evidence'),('sha256','1'*64),('provenance','gc')]:
            q=dict(a);q[field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'growth|change'):
                self.generate(baseline=ceiling,requested=self.envelope(q))
        with self.assertRaisesRegex(ValueError,'growth'):
            self.generate(requested=self.envelope(a))
    def test_absent_other_consumer_ceiling_row_is_pruned_not_rewritten(self):
        a=self.allowance();other=dict(a,kind='sound-mram',id='old-exact-bank')
        docs=self.generate(baseline=self.envelope(a,other))
        self.assertEqual(docs['allowlist.json']['entries'],[a])
    def test_provider_order_does_not_change_index(self):
        self.file_provider('dc/tex/'+K1+'.re4tex',b'RE4DCTX\0loose-extra','texture',K1)
        a=self.generate();self.selection['providers'].reverse();b=self.generate()
        self.assertEqual(a['gc-assets.idx'],b['gc-assets.idx'])
    def test_proposals_remain_unapproved_and_do_not_authorize_new_use(self):
        a=self.allowance();docs=self.generate(proposals=self.envelope(a))
        self.assertEqual(docs['allowlist.json']['entries'],[])
        self.assertEqual(docs['unapproved-proposals.json']['entries'],[a])
        self.assertEqual(docs['report.json']['unapproved_proposals'],1)
    def test_positive_origin_only_removes_exact_existing_exception(self):
        a=self.allowance();b=self.allowance(identity=K2,sha=p.digest(self.payloads[1]))
        docs=self.generate(self.proof(),self.envelope(a,b))
        self.assertEqual(docs['allowlist.json']['entries'],[b])
    def test_room_patterns_duplicates_and_bad_scope_rejected(self):
        for room in ['*','r100','0100,0111']:
            with self.subTest(room=room),self.assertRaises(ValueError):self.generate(baseline=self.envelope(self.allowance(room)))
        a=self.allowance()
        with self.assertRaisesRegex(ValueError,'duplicate'):self.generate(baseline=self.envelope(a,a))
    def test_motion_original_span_prefix_boundary_not_positive_origin(self):
        raw=b'HEADERoriginal-FCV-exact-tailREL';path,row=self.file_provider('pl/pl08.drs',raw,'motion')
        offset=6;length=18;span=raw[offset:offset+length];self.selection['providers'][-1]={'provider':'span','asset':row['asset'],'path':str(path),'kind':'motion','id':p.digest(span)[:40],'offset':offset,'bytes':length,'sha256':p.digest(span),'boundary':self.ref(self.evidence)}
        docs=self.generate();motion=next(x for x in docs['catalog.json']['entries'] if x['kind']=='motion')
        self.assertEqual(motion['sha256'],p.digest(span));self.assertEqual(motion['provenance'],'unknown')
        self.selection['providers'][-1]['offset']+=1
        with self.assertRaisesRegex(ValueError,'span mismatch'):self.generate()
    def test_model_prefix_wrong_span_kind_and_bounds(self):
        path,row=self.file_provider('em/em12.drs',b'raw original model','model','f'*40)
        with self.assertRaisesRegex(ValueError,'prefix'):self.generate()
        row.update(provider='span',kind='geometry',offset=0,bytes=4,sha256=p.digest(b'raw '),boundary=self.ref(self.evidence))
        with self.assertRaisesRegex(ValueError,'span kind'):self.generate()
        row.update(kind='model',offset=-1)
        with self.assertRaisesRegex(ValueError,'span bounds'):self.generate()
    def test_file_provider_containment_and_programme_refusal(self):
        outside=self.root/'outside.pak';outside.write_bytes(self.pack.read_bytes());self.selection['providers'][0]['path']=str(outside)
        with self.assertRaisesRegex(ValueError,'outside'):self.generate()
        self.selection['providers'][0]['path']=str(self.pack);self.selection['providers'][0]['asset']='1ST_READ.BIN'
        self.manifest['1ST_READ.BIN']=self.manifest['dc/tex.pak'];self.selection['manifest_sha256']=p.digest(p.encode(self.manifest))
        with self.assertRaisesRegex(ValueError,'outside selected'):self.generate()
    def test_pack_overlap_capacity_and_duplicate_provider(self):
        self.selection['providers']*=2
        with self.assertRaisesRegex(ValueError,'duplicate provider'):self.generate()
        self.selection['providers']=self.selection['providers'][:1]
        with mock.patch.object(p.idx,'MAX_RECORDS',1):
            with self.assertRaisesRegex(ValueError,'capacity'):self.generate()
        raw=bytearray(self.pack.read_bytes());struct.pack_into('<I',raw,48,64);self.pack.write_bytes(raw);self.manifest['dc/tex.pak']['sha256']=p.digest(raw);self.selection['manifest_sha256']=p.digest(p.encode(self.manifest))
        with self.assertRaisesRegex(ValueError,'overlapping'):self.generate()
    def test_mid_read_same_size_mutation_and_identical_path_replacement(self):
        original=self.pack.read_bytes();real=p.span_hash
        for replace in [False,True]:
            self.pack.write_bytes(original);called=False
            def changing(fp,offset,size):
                nonlocal called
                result=real(fp,offset,size)
                if not called:
                    called=True
                    if replace:
                        q=self.store/'new.pak';q.write_bytes(original);q.replace(self.pack)
                    else:self.pack.write_bytes(original[:-1]+b'!')
                return result
            with mock.patch.object(p,'span_hash',changing),self.assertRaisesRegex(ValueError,'mutated|replaced'):
                self.generate()
    def test_duplicate_json_unknown_provider_and_path_escape(self):
        with self.assertRaisesRegex(ValueError,'duplicate JSON'):p.read_manifest(b'{"x":1,"x":2}')
        self.selection['providers'][0]['provider']='learn-new-log'
        with self.assertRaisesRegex(ValueError,'unsupported'):self.generate()
        with self.assertRaisesRegex(ValueError,'unsafe'):p.source_name('../escape')
    def test_cli_validates_before_allocating_new_output(self):
        args=[sys.executable,'-B',str(Path(p.__file__))]
        for name,doc in [('selection',self.selection),('manifest',self.manifest)]:
            path=self.root/(name+'.json');path.write_bytes(p.encode(doc));args+=['--'+name,str(path),'--'+name+'-sha256',p.digest(path.read_bytes())]
        output=self.root/'output';args+=['--store-root',str(self.store),'--out-dir',str(output)]
        good=subprocess.run(args,capture_output=True,text=True,timeout=30);self.assertEqual(good.returncode,0,good.stderr)
        self.assertEqual((output/'gc-assets.idx').read_bytes(),self.generate()['gc-assets.idx'])
        before={x.name:x.read_bytes() for x in output.iterdir()};self.assertNotEqual(subprocess.run(args,capture_output=True,timeout=30).returncode,0);self.assertEqual(before,{x.name:x.read_bytes() for x in output.iterdir()})
        output2=self.root/'failure';args[-1]=str(output2);self.pack.write_bytes(b'invalid')
        self.assertNotEqual(subprocess.run(args,capture_output=True,timeout=30).returncode,0);self.assertFalse(output2.exists())

if __name__=='__main__':unittest.main(verbosity=2)