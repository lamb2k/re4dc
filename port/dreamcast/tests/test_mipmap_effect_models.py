"""Efm model-table numeric IDs never substitute for image-table IDs."""
import copy,hashlib,pathlib,struct,sys,unittest
from unittest import mock
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/d367/mipmap21'))
import effect_model_consumers as models
import effect_model_candidate as candidate
import texpack
import test_mipmap_vq as vf


def source():
    data=bytearray(256)
    struct.pack_into('<12I',data,0,11,0,0,0,0,48,0,0,0,0,0,64)
    struct.pack_into('<IHHI',data,48,1,37,0,0)
    struct.pack_into('<II',data,64,1,16)
    struct.pack_into('<5I',data,80,0,20,80,0,0)
    return data


def material_model(image=3):
    data=bytearray(256)
    for off,value in ((0,64),(16,160),(20,176),(28,192),(32,0),(36,4),(48,96),(52,128),(60,0x20010801)):
        struct.pack_into('<I',data,off,value)
    data[24:26]=bytes((1,1));struct.pack_into('<H',data,26,1);struct.pack_into('<2H',data,56,1,1)
    for i,uv in enumerate(((0,0),(32768,0),(0,32768),(32768,32768))):struct.pack_into('<2H',data,160+4*i,*uv)
    data[204]=image;struct.pack_into('<I',data,216,32);struct.pack_into('>BH',data,224,0x80,4)
    for i in range(4):struct.pack_into('>3H',data,227+6*i,0,0,i)
    return data


class EffectModelBindings(unittest.TestCase):
    def read(self,data):return models.effect_models(data,dict(off=0,end=len(data),index=5))
    def test_existing_five_word_codec_resolves_model_and_TPL_in_distinct_namespace(self):
        row=self.read(source())[0]
        self.assertEqual((row['model_index'],row['model_entry_offset'],row['model_offset'],row['tpl_offset']),(37,80,100,160))
        self.assertEqual(row['sequence_references'],[])
    def test_bad_counts_targets_and_entry_overlap_are_refused(self):
        for at,value in ((64,2),(68,252),(84,0),(88,4),(88,300)):
            bad=source();struct.pack_into('<I',bad,at,value)
            with self.assertRaises(ValueError):self.read(bad)
    def test_existing_layout_and_primitive_codecs_prove_actual_TPL_index_and_full_UV_use(self):
        row=models.model_materials(material_model(),texture_count=4)[0]
        self.assertEqual((row['texture_index'],row['triangles'],row['samples_texture']),(3,2,True))
        self.assertEqual(row['UV_bounds'],dict(u_min=0,u_max=1,v_min=0,v_max=1))
        self.assertFalse(models.model_materials(material_model(255),texture_count=0)[0]['samples_texture'])
    def test_bad_material_UV_and_primitive_inputs_are_refused(self):
        with self.assertRaises(ValueError):models.model_materials(material_model(),texture_count=3)
        for off,value,fmt in ((224,1,'<B'),(231,100,'>H'),(216,1000,'<I')):
            bad=material_model();struct.pack_into(fmt,bad,off,value)
            with self.assertRaises(ValueError):models.model_materials(bad,texture_count=4)

    def test_empty_ID_table_does_not_dereference_an_absent_data_table(self):
        data=source();struct.pack_into('<I',data,48,0);struct.pack_into('<I',data,44,0)
        self.assertEqual(self.read(data),[])

    def test_no_model_table_keeps_empty_binding_without_reading_the_header_as_a_table(self):
        data=source();struct.pack_into('<I',data,20,0)
        self.assertEqual(self.read(data),[])


def masked_body():
    model=material_model(0);model[203]=4;model[206]=1
    tpl=bytearray(192);struct.pack_into('<3I',tpl,0,models.convert_tpl.TPL_MAGIC,2,12)
    for i in range(2):
        header=28+i*36;pixels=128+i*32
        struct.pack_into('<2I',tpl,12+i*8,header,0)
        struct.pack_into('<2H7I',tpl,header,8,8,14,pixels,1,1,1,1,0)
        tpl[pixels:pixels+32]=bytes([i+1])*32
    return model+tpl


class EffectModelSelection(unittest.TestCase):
    def test_actual_alpha_material_requires_distinct_source_pair_not_color_key(self):
        rows=models.masked_material_bindings(masked_body(),dict(model_offset=0,tpl_offset=256))
        self.assertEqual(len(rows),1);r=rows[0]
        self.assertEqual((r['material']['material_flags'],r['material']['alpha_texture_index']),(4,1))
        self.assertNotEqual(r['color']['key'],r['mask']['key'])
        self.assertNotIn(r['pair_key'],(r['color']['key'],r['mask']['key']))
        self.assertEqual((r['color']['wrap_s'],r['mask']['wrap_s']),(1,1))
    def test_bad_alpha_descriptor_palette_and_wrapping_are_not_ordinary_model_candidates(self):
        for offset,value in ((206,2),(268,1),(284,255),(256+28+12,0)):
            body=masked_body();body[offset]=value
            with self.assertRaises(ValueError):models.masked_material_bindings(body,dict(model_offset=0,tpl_offset=256))
    def test_record_target_overrides_and_compact_sources_stay_held(self):
        raw=bytearray(300);raw[1]=255;raw[2]=37
        def rec(b):return dict(compact=False,sprite_id=255,kind=0,screen_parts=False,reference_namespace='effect-model',record_offset=0,record_sha256=hashlib.sha256(b).hexdigest(),model_index=37)
        self.assertIsNone(candidate.record_hold(raw,rec(raw)))
        for off in (0xd0,0xfe):
            bad=raw.copy();bad[off]=1
            self.assertEqual(candidate.record_hold(bad,rec(bad)),'render-target-or-motion-override')
        record=rec(raw);record['compact']=True
        self.assertEqual(candidate.record_hold(raw,record),'unsupported-model-record-path')
        with self.assertRaises(ValueError):candidate.record_hold(raw,dict(rec(raw),record_sha256='bad'))
    def test_complete_alias_group_is_required_even_when_one_local_model_passes(self):
        a=dict(path='one',tpl_offset=80);b=dict(path='two',tpl_offset=120)
        cov=dict(source_pack_sha256='pack',normal_rows=[dict(key='key',source_references=[a,b])])
        local=lambda refs:dict(source_pack_sha256='pack',rows=[dict(key='key',decision='local-world-obj04-original-VQ-proof',source_references=refs)])
        self.assertEqual(candidate.compose_alias_policy([local([a])],cov)['rows'],[])
        group=candidate.compose_alias_policy([local([a]),local([b])],cov)['rows']
        self.assertEqual(len(group),1);self.assertEqual(group[0]['source_references'],[a,b])
    def test_off_exact_original_VQ_base_retained_and_selected_ancestor_not_overwritten(self):
        blob=vf.native(8,fmt=2);source=texpack.build({(1,2):blob})[0];digest=candidate.sha(source)
        ref=dict(key='00000001-00000002',package_sha256=candidate.sha(blob),source_references=[],native_world_references=[],native_registry_references=[],derived_pair_references=[])
        cov=dict(source_pack_sha256=digest,normal_rows=[ref]);row=dict(ref,decision='source-world-obj04-original-VQ-candidate')
        policy=dict(source_pack_sha256=digest,rows=[row],limits=[])
        off,_,_,_=candidate.build(source,source,cov,policy);self.assertEqual(off,source)
        on,_,before,after=candidate.build(source,source,cov,policy,enabled=True)
        old,new=map(candidate.vq.read_native_vq,(before[(1,2)],after[(1,2)]))
        self.assertEqual(old.codebook,new.codebook);self.assertEqual(old.base_indices,new.base_indices)
        with self.assertRaises(ValueError):candidate.build(source,on,cov,policy,enabled=True)
        cov=copy.deepcopy(cov);cov['normal_rows'][0]['native_registry_references']=[{}]
        with self.assertRaises(ValueError):candidate.build(source,source,cov,policy,enabled=True)


if __name__=='__main__':unittest.main()
