"""Native/VQ full-frame candidates obey shared/UI/source consumer contracts."""
import copy
import pathlib
import sys
import struct
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tools/d367/mipmap21'))
import compact_native_vq
import effect_policy
import generic_effect_candidate as generic
import mipmap_vq as vq
import texpack
import test_mipmap_twiddled as tw
import test_mipmap_vq as vf


class GenericEffects(unittest.TestCase):
    def setUp(self):
        # The repeated base has a real exact VQ byte win.
        self.source={(1,2):tw.from_words([0xffff]*(64*64),64,fmt=2),
                     (3,4):vf.native(8,fmt=2),(5,6):tw.native(8,fmt=2)}
        self.original=texpack.build(self.source)[0];base=dict(self.source)
        base[(1,2)]=compact_native_vq.compact(self.source[(1,2)],enabled=True)[0]
        self.base=texpack.build(base)[0]
        self.coverage=dict(source_pack_sha256=generic.sha(self.original),normal_rows=[])
        self.policy=dict(source_pack_sha256=generic.sha(self.original),common_sprite_ids=[0],
            source_files=dict(fixture=dict(retained=True,parsed=True,sha256='source')),rows=[])
        for key,blob in self.source.items():
            name='%08x-%08x'%key;t=generic.tpl.TEXTURE.unpack_from(blob,48)
            self.coverage['normal_rows'].append(dict(key=name,package_sha256=generic.sha(blob),
                material='source',width=t[1],height=t[2],native_format=t[3],
                source_references=[dict(owner_category='effect',path='fixture',arc_index=0,tpl_offset=80,file_sha256='source')],native_world_references=[],native_registry_references=[]))
            rec=dict(kind=0,sprite_id=0,screen_parts=False,tool_flags=0,shimmer_type=0,generator_id=0)
            self.policy['rows'].append(dict(key=name,package_sha256=generic.sha(blob),
                decision='world-common-sprite-source-candidate',direct_ID_UI_consumers=[],reasons=[],
                source_bindings=[dict(source_path='fixture',source_sha256='source',archive_entry=0,tpl_offset=80,records=[rec])]))

    def test_off_exact_then_original_vq_native_and_compact_base_keep_exact_original_bases(self):
        off,_,_,_=generic.build(self.original,self.base,self.coverage,self.policy)
        self.assertEqual(off,self.base)
        _,report,before,after=generic.build(self.original,self.base,self.coverage,self.policy,enabled=True,engine='python')
        self.assertEqual(report['family_counts'],{'compact-base-VQ':1,'original-VQ':1,'original-native16':1})
        for key,blob in self.source.items():
            st=generic.tpl.TEXTURE.unpack_from(blob,48);at=generic.tpl.TEXTURE.unpack_from(after[key],48)
            src=vq.read_native_vq(blob) if st[7]==2 else tw.mip.read_native_twiddled(blob)
            dst=vq.read_native_vq(after[key]) if at[7]==2 else tw.mip.read_native_twiddled(after[key])
            self.assertEqual((vq if st[7]==2 else tw.mip).decode_level(src,src.size),
                             (vq if at[7]==2 else tw.mip).decode_level(dst,dst.size))
        self.assertEqual(vq.read_native_vq(before[(3,4)]).codebook,vq.read_native_vq(after[(3,4)]).codebook)

    def test_shared_native_alias_and_forged_source_policy_are_refused(self):
        coverage=copy.deepcopy(self.coverage);coverage['normal_rows'][0]['native_world_references']=[{}]
        with self.assertRaises(ValueError):generic.build(self.original,self.base,coverage,self.policy,enabled=True)
        policy=copy.deepcopy(self.policy);policy['source_files']['fixture']['sha256']='bad'
        with self.assertRaises(ValueError):generic.build(self.original,self.base,self.coverage,policy,enabled=True)
        policy=copy.deepcopy(self.policy);policy['sampling_contract_version']=3
        with self.assertRaises(ValueError):generic.build(self.original,self.base,self.coverage,policy,enabled=True)

    def test_valid_fixture_outputs_match_pre_fix_pack_identities(self):
        # Captured from exact 9f6a25c6 predecessor with this complete source policy.
        for enabled,digest in ((False,'2ab1d4be9208b09b4e0e7b54724afe24ae1138b8fdb132067f81f7de2ceccb97'),
                (True,'ac52d7c358b546e9bfd17f5df0667515710c3130ad3884f21093d1d8289682d9')):
            out,_,_,_=generic.build(self.original,self.base,self.coverage,self.policy,enabled=enabled,engine='python')
            self.assertEqual(generic.sha(out),digest)

    def test_two_complete_distinct_bindings_are_still_accepted(self):
        coverage=copy.deepcopy(self.coverage);policy=copy.deepcopy(self.policy)
        coverage['normal_rows'][0]['source_references'].append(dict(
            owner_category='effect',path='second',arc_index=4,tpl_offset=88,file_sha256='second-source'))
        binding=copy.deepcopy(policy['rows'][0]['source_bindings'][0])
        binding.update(source_path='second',source_sha256='second-source',archive_entry=4,tpl_offset=88)
        policy['rows'][0]['source_bindings'].append(binding)
        policy['source_files']['second']=dict(retained=True,parsed=True,sha256='second-source')
        out,report,_,_=generic.build(self.original,self.base,coverage,policy,enabled=True,engine='python')
        self.assertEqual(report['selected_frames'],3)
        self.assertEqual(generic.sha(out),'ac52d7c358b546e9bfd17f5df0667515710c3130ad3884f21093d1d8289682d9')

    def test_fresh_source_policy_separates_same_numeric_model_id_and_holds_unknown(self):
        def source(ident,with_sprite):
            ids=([0] if with_sprite else [])+[ident]
            block=bytearray(160+300*len(ids))
            struct.pack_into('<12I',block,0,11,48,64,0,0,0,80,0,96,0,0,0)
            struct.pack_into('<IHHI',block,48,1,0x31,0,0)
            struct.pack_into('<IHHI',block,64,1,7,0,0)
            struct.pack_into('<II',block,80,1,16);struct.pack_into('<II',block,96,1,16)
            struct.pack_into('<H',block,112,len(ids))
            for i,value in enumerate(ids):
                at=160+300*i;block[at+1]=value;block[at+2]=0x31;block[at+7]=254
                if value==0xff: block[at+264]=1;block[at+265]=9
            return struct.pack('<6I',1,0,0,0,24,int.from_bytes(b'EFF\0','little'))+block
        for ident,with_sprite,decision in ((0xfc,True,'world-common-sprite-source-candidate'),
                (0xfc,False,'hold-unresolved-consumer'),(0xff,True,'hold-custom-or-generator-effect')):
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);(root/'em').mkdir();(root/'src/game').mkdir(parents=True)
                blob=source(ident,with_sprite);(root/'em/fx.drs').write_bytes(blob)
                (root/'src/game/esp_app.cpp').write_text('EspFuncTblSet(0x00, 0, EspCommonTrans);')
                coverage=copy.deepcopy(self.coverage);coverage['normal_rows']=coverage['normal_rows'][:1]
                coverage['normal_rows'][0]['source_references']=[dict(owner_category='effect',path='em/fx.drs',
                    arc_index=4,tpl_offset=120,file_sha256=generic.sha(blob))]
                manifest={'em/fx.drs':dict(sha256=generic.sha(blob),size=len(blob))}
                policy=generic.source_policy(coverage,manifest,root,root)
                self.assertEqual(policy['rows'][0]['decision'],decision)
                if ident==0xfc and with_sprite:
                    self.assertEqual([r['sprite_id'] for r in policy['rows'][0]['source_bindings'][0]['records']],[0])

    def test_omitted_duplicate_or_changed_original_bindings_are_refused(self):
        for change in ('omitted','duplicate','slot','tpl'):
            coverage=copy.deepcopy(self.coverage);policy=copy.deepcopy(self.policy)
            if change=='omitted':
                coverage['normal_rows'][0]['source_references'].append(dict(
                    owner_category='effect',path='second',arc_index=0,tpl_offset=80,file_sha256='source'))
            elif change=='duplicate':
                policy['rows'][0]['source_bindings']*=2
            else:
                policy['rows'][0]['source_bindings'][0]['archive_entry' if change=='slot' else 'tpl_offset']+=1
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'omits or duplicates'):
                generic.build(self.original,self.base,coverage,policy,enabled=True)

    def test_fixed_UI_identity_cannot_be_hidden_by_empty_policy_claim(self):
        for path,slot in effect_policy.ID_UI:
            coverage=copy.deepcopy(self.coverage);policy=copy.deepcopy(self.policy)
            coverage['normal_rows'][0]['source_references'][0].update(path=path,arc_index=slot)
            policy['rows'][0]['source_bindings'][0].update(source_path=path,archive_entry=slot)
            policy['source_files'][path]=dict(retained=True,parsed=True,sha256='source')
            with self.subTest(path=path,slot=slot),self.assertRaisesRegex(ValueError,'fixed-ID UI'):
                generic.build(self.original,self.base,coverage,policy,enabled=True)

    def test_model_and_unresolved_namespaces_cannot_be_forged_as_common_sprites(self):
        for ident in range(0xfc,0x100):
            for kind,generator in ((0,0),(1,0),(1,2),(1,9)):
                policy=copy.deepcopy(self.policy);policy['common_sprite_ids'].append(ident)
                policy['rows'][0]['source_bindings'][0]['records'][0].update(
                    sprite_id=ident,kind=kind,generator_id=generator)
                with self.subTest(ident=ident,kind=kind,generator=generator),self.assertRaisesRegex(ValueError,'namespace'):
                    generic.build(self.original,self.base,self.coverage,policy,enabled=True)

    def test_eff_ui_slot_is_held_even_with_a_forged_world_record(self):
        rec=dict(kind=0,sprite_id=0,screen_parts=False,tool_flags=0,shimmer_type=0,generator_id=0)
        frame=dict(key='key',package_sha256='tex',source_refs=[dict(path='etc/core.das',arc_index=29,tpl_offset=80,file_sha256='source')])
        parsed={'etc/core.das':dict(effects=[dict(archive_entry=29,textures=[dict(tpl_offset=80,texture_id=7,records=[rec])])])}
        result=effect_policy.classify(frame,parsed,{'etc/core.das':dict(sha256='source')},{0})
        self.assertEqual(result['decision'],'hold-fixed-ID-UI')


if __name__=='__main__':unittest.main()
