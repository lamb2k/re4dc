"""Effect/UI shared format and exact compact source record reconstruction."""
import pathlib
import struct
import sys
import unittest
import zlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tools/d367/mipmap21'))
import compact_effect_records as compact
import effect_consumers as effect


def record(parts=254,kind=0,ident=0,texture=0x31):
    raw=bytearray(300);raw[0:4]=bytes((1,ident,texture,0));raw[7]=parts;raw[264]=kind
    struct.pack_into('<I',raw,8,1);struct.pack_into('<2f',raw,136,10,20)
    return bytes(raw)


class SourceEffectConsumers(unittest.TestCase):
    def test_emitter_and_jitter_wrapper_preserve_sampler_but_reflection_is_held(self):
        r=dict(kind=1,generator_id=0,sprite_id=0,screen_parts=False,tool_flags=0,shimmer_type=0)
        self.assertEqual(effect.record_sampling(r,{0}),'hold-generator')
        self.assertEqual(effect.record_sampling(r,{0},extended=True),'common-world-sprite-emitter00')
        r['generator_id']=2
        self.assertEqual(effect.record_sampling(r,{0},extended=True),'hold-generator')
        r.update(kind=0,sprite_id=11)
        self.assertEqual(effect.record_sampling(r,{0},extended=True),'common-world-sprite')
        r['sprite_id']=0x11
        self.assertEqual(effect.record_sampling(r,{0},extended=True),'no-record-texture-sampling')
        r['sprite_id']=0x4c
        self.assertEqual(effect.record_sampling(r,{0},extended=True),'hold-custom-renderer')
        r.update(sprite_id=0,tool_flags=0x2000)
        self.assertEqual(effect.record_sampling(r,{0},extended=True),'hold-RTT-shimmer-or-negative')

    def test_version3_path_emitter_preserves_sampling_and_EST_trigger_does_not_sample(self):
        r=dict(kind=1,generator_id=2,sprite_id=0,screen_parts=False,tool_flags=0,shimmer_type=0)
        self.assertEqual(effect.record_sampling(r,{0},contract_version=2),'hold-generator')
        self.assertEqual(effect.record_sampling(r,{0},contract_version=3),'common-world-sprite-emitter02')
        for field,value,expected in (('screen_parts',True,'hold-screen'),('tool_flags',0x2000,'hold-RTT-shimmer-or-negative'),
                ('shimmer_type',1,'hold-RTT-shimmer-or-negative'),('generator_id',9,'hold-generator')):
            bad=dict(r);bad[field]=value
            self.assertEqual(effect.record_sampling(bad,{0},contract_version=3),expected)
        r.update(kind=0,sprite_id=0x0c)
        self.assertEqual(effect.record_sampling(r,{0},contract_version=2),'hold-custom-renderer')
        self.assertEqual(effect.record_sampling(r,{0},contract_version=3),'no-record-texture-sampling')
        r['sprite_id']=0x4c
        self.assertEqual(effect.record_sampling(r,{0},contract_version=3),'hold-custom-renderer')
        with self.assertRaises(ValueError):effect.record_sampling(r,{0},contract_version=4)

    def test_raw_world_and_screen_records_remain_distinct(self):
        a,b=record(),record(parts=248)
        data=struct.pack('<H',2)+bytes(46)+a+b
        records=effect.sequence_records(data,0,len(data),{})
        self.assertEqual([r[2] for r in records],[a,b])
        self.assertFalse(any(r[1] for r in records))
        self.assertEqual([r[0] for r in records],[48,348])

    def test_compact_record_is_decoded_instead_of_read_as_300_raw_bytes(self):
        raw=record();packed=compact.pack_record(raw)
        head=struct.pack('<H',1)+bytes(46)
        data=head+struct.pack('<I',53)+packed
        data+=bytes((-len(data))%32)
        result=effect.sequence_records(data,0,len(data),{0:(len(data),1)})
        self.assertEqual(result,[(52,True,raw)])
        bad=bytearray(data);bad[-1]=1
        with self.assertRaises(ValueError):effect.sequence_records(bad,0,len(bad),{0:(len(bad),1)})
        with self.assertRaises(ValueError):effect.sequence_records(data[:-4],0,len(data)-4,{0:(len(data),1)})

    def test_eff_texture_without_sequence_is_not_an_effect_consumer_proof(self):
        blob=bytearray(128)
        struct.pack_into('<12I',blob,0,11,48,0,0,0,0,64,0,0,0,0,0)
        struct.pack_into('<IHHI',blob,48,1,0x87,0,0)
        struct.pack_into('<II',blob,64,1,16)
        parsed=effect.effect(blob,dict(off=0,end=128,index=39),{})
        self.assertEqual(parsed['textures'],[dict(texture_id=0x87,tpl_offset=80,records=[])])
        self.assertEqual(parsed['records'],0)

    def test_bad_compact_index_crc_and_sequence_ranges_are_refused(self):
        blob=bytearray(192);struct.pack_into('<I',blob,0,1)
        table=struct.pack('<3I',32,64,1)
        struct.pack_into('<8s6I',blob,128,b'R4ESQTBL',1,1,12,zlib.crc32(table)&0xffffffff,192,0)
        blob[160:172]=table;struct.pack_into('<H',blob,32,1)
        entries=[dict(off=128,end=192,tag=b'ESQ',index=4)]
        self.assertEqual(effect.compact_index(blob,entries),{32:(64,1)})
        blob[160]^=1
        with self.assertRaises(ValueError):effect.compact_index(blob,entries)

    def test_model_index_never_proves_an_image_binding_and_unknown_generator_stays_held(self):
        sprite=record(texture=0x31);model=record(ident=0xff,texture=0x31)
        unknown=bytearray(record(ident=0xff,texture=0x31,kind=1));unknown[265]=9
        def parse(values,separate=False):
            blob=bytearray(112+48+300*len(values))
            struct.pack_into('<12I',blob,0,11,48,64,0,0,0,80,0,96,0,0,0)
            struct.pack_into('<IHHI',blob,48,1,0x31,0,0)
            struct.pack_into('<IHHI',blob,64,1,7,0,0)
            struct.pack_into('<II',blob,80,1,16);struct.pack_into('<II',blob,96,1,16)
            struct.pack_into('<H',blob,112,len(values))
            blob[160:]=b''.join(values)
            return effect.effect(blob,dict(off=0,end=len(blob),index=5),{},separate_model_namespace=separate)
        legacy=parse([sprite,model]);split=parse([sprite,model],True)
        self.assertEqual(len(legacy['textures'][0]['records']),2)
        self.assertNotIn('effect_model_references',legacy)
        self.assertEqual([r['sprite_id'] for r in split['textures'][0]['records']],[0])
        self.assertEqual(split['effect_model_references'][0]['model_index'],0x31)
        held=parse([sprite,bytes(unknown)],True)
        self.assertEqual(len(held['textures'][0]['records']),2)
        self.assertEqual(len(held['unresolved_reference_namespaces']),1)
        self.assertFalse(held['effect_model_references'])
        for kind,generator,expected in ((0,0,'effect-model'),(1,0,'effect-model'),(1,2,'effect-model'),(1,9,'unresolved-generator-model-or-texture')):
            self.assertEqual(effect.record_reference_namespace(dict(kind=kind,generator_id=generator,sprite_id=0xfc)),expected)


    def test_special_reference_namespace_is_not_an_image_id(self):
        for ident in range(0xfc,0x100):
            for kind,generator,expected in ((0,0,'effect-model'),(1,0,'effect-model'),
                    (1,2,'effect-model'),(1,9,'unresolved-generator-model-or-texture')):
                with self.subTest(ident=ident,kind=kind,generator=generator):
                    r=dict(sprite_id=ident,kind=kind,generator_id=generator)
                    self.assertEqual(effect.record_reference_namespace(r),expected)
        for ident in (0,0x0b,0xfb):
            self.assertEqual(effect.record_reference_namespace(dict(sprite_id=ident,kind=1,generator_id=9)),
                             'effect-texture')


if __name__=='__main__':unittest.main()
