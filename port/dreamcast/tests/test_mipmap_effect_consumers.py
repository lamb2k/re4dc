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


if __name__=='__main__':unittest.main()
