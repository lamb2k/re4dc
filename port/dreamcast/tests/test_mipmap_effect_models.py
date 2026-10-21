"""Efm model-table numeric IDs never substitute for image-table IDs."""
import pathlib,struct,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/d367/mipmap21'))
import effect_model_consumers as models


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


if __name__=='__main__':unittest.main()
