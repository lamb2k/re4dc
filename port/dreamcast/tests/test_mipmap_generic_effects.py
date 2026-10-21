"""Native/VQ full-frame candidates obey shared/UI/source consumer contracts."""
import copy
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tools/d367/mipmap21'))
import compact_native_vq
import compact_native_pal8 as pal8
import test_compact_native_pal8 as palette_fixture
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
        policy=copy.deepcopy(self.policy);policy['sampling_contract_version']=4
        with self.assertRaises(ValueError):generic.build(self.original,self.base,self.coverage,policy,enabled=True)

    def one(self,blob):
        key=(9,10);name='%08x-%08x'%key;source=texpack.build({key:blob})[0]
        coverage=copy.deepcopy(self.coverage);policy=copy.deepcopy(self.policy)
        coverage['source_pack_sha256']=policy['source_pack_sha256']=generic.sha(source)
        coverage['normal_rows']=coverage['normal_rows'][2:];policy['rows']=policy['rows'][2:]
        row=coverage['normal_rows'][0];t=generic.tpl.TEXTURE.unpack_from(blob,48)
        row.update(key=name,package_sha256=generic.sha(blob),width=t[1],height=t[2],native_format=t[3])
        policy['rows'][0].update(key=name,package_sha256=generic.sha(blob))
        return key,source,coverage,policy

    def test_contract3_accepts_reviewed_path_emitter_and_contract2_stays_rejected(self):
        policy=copy.deepcopy(self.policy);rec=policy['rows'][0]['source_bindings'][0]['records'][0]
        rec.update(kind=1,generator_id=2)
        with self.assertRaises(ValueError):generic.build(self.original,self.base,self.coverage,policy,enabled=True)
        policy['sampling_contract_version']=3
        _,report,_,_=generic.build(self.original,self.base,self.coverage,policy,enabled=True,engine='python')
        self.assertEqual(report['selected_frames'],3)

    def test_missing_original_binding_and_disguised_fixed_UI_consumer_are_refused(self):
        coverage=copy.deepcopy(self.coverage)
        coverage['normal_rows'][0]['source_references'].append(dict(owner_category='effect',path='second',arc_index=0,tpl_offset=80,file_sha256='source'))
        with self.assertRaises(ValueError):generic.build(self.original,self.base,coverage,self.policy,enabled=True)
        coverage=copy.deepcopy(self.coverage);policy=copy.deepcopy(self.policy)
        coverage['normal_rows'][0]['source_references'][0].update(path='etc/core.das',arc_index=29)
        policy['rows'][0]['source_bindings'][0].update(source_path='etc/core.das',archive_entry=29)
        policy['source_files']['etc/core.das']=dict(retained=True,parsed=True,sha256='source')
        with self.assertRaises(ValueError):generic.build(self.original,self.base,coverage,policy,enabled=True)

    def test_opt_in_canonical_PAL8_chain_preserves_base_and_uses_less_than_original_native_base(self):
        key,source,coverage,policy=self.one(palette_fixture.source(32))
        off,_,_,_=generic.build(source,source,coverage,policy,canonical_pal8=True,engine='python')
        self.assertEqual(off,source)
        _,report,_,after=generic.build(source,source,coverage,policy,enabled=True,canonical_pal8=True,engine='python')
        self.assertEqual(report['family_counts'],{'canonical-PAL8-native16':1})
        compact=pal8.read_native_pal8(after[key]);original=tw.mip.read_native_twiddled(generic._read(source)[key])
        self.assertEqual(pal8.decode_level(compact,32),tw.mip.decode_level(original,32))
        self.assertEqual(len(compact.payload),1880);self.assertLess(len(compact.payload),len(original.payload))
        self.assertIn('TEX_PAL8_MIPMAP=1',report['required_build_knobs'])
        _,legacy,_,legacy_after=generic.build(source,source,coverage,policy,enabled=True,engine='python')
        self.assertEqual(legacy['family_counts'],{'original-native16':1})
        self.assertEqual(generic.tpl.TEXTURE.unpack_from(legacy_after[key],48)[3],2)

    def test_palette_option_does_not_fall_back_to_larger_chain_or_new_color_palette(self):
        for blob in (palette_fixture.source(16),palette_fixture.source(32,gray=False)):
            _,source,coverage,policy=self.one(blob)
            out,report,_,_=generic.build(source,source,coverage,policy,enabled=True,canonical_pal8=True,engine='python')
            self.assertEqual(out,source);self.assertEqual(report['selected_frames'],0)
            self.assertEqual(report['held'][0]['decision'],'hold-no-canonical-PAL8-base-win')

    def test_eff_ui_slot_is_held_even_with_a_forged_world_record(self):
        rec=dict(kind=0,sprite_id=0,screen_parts=False,tool_flags=0,shimmer_type=0,generator_id=0)
        frame=dict(key='key',package_sha256='tex',source_refs=[dict(path='etc/core.das',arc_index=29,tpl_offset=80,file_sha256='source')])
        parsed={'etc/core.das':dict(effects=[dict(archive_entry=29,textures=[dict(tpl_offset=80,texture_id=7,records=[rec])])])}
        result=effect_policy.classify(frame,parsed,{'etc/core.das':dict(sha256='source')},{0})
        self.assertEqual(result['decision'],'hold-fixed-ID-UI')


if __name__=='__main__':unittest.main()
