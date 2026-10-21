"""Owner evidence is separate from format eligibility and packed/loose winners."""
import copy
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/d367"))
sys.path.insert(0, str(ROOT / "tools/d367/mipmap21"))
import source_coverage as coverage
import texpack
from test_compact_native_vq import raw


class WholePackPolicy(unittest.TestCase):
    def setUp(self):
        self.pack = texpack.build({(1,2):raw(),(3,4):raw(2)})[0]
        selected = dict(path="ss/f001.tpl",size=512,sha256="source-file-sha256")
        self.receipt = {"ss/f001.tpl":dict(size=512,sha256=selected["sha256"]),
            "dc/tex.pak":dict(size=len(self.pack),sha256=coverage.sha(self.pack))}
        ref = dict(owner_category="ui-font-source",path="ss/f001.tpl",file_sha256=selected["sha256"],
            active_body_offset=0,header_offset=20,tpl_offset=0)
        self.probe = dict(schema="re4dc-source-owner-probe-1",source_pack_sha256=coverage.sha(self.pack),
            selected_files=[dict(selected,active_bytes=512)],references={"00000001-00000002":[ref]})
        normal=[]
        for at,key,fmt in ((0,"00000001-00000002",0),(1,"00000003-00000004",2)):
            normal.append(dict(key=key,container="dc/tex.pak:%d"%at,width=64,height=64,
                format=fmt,payload_bytes=8192,flags=0 if fmt==0 else 1,payload=1))
        # raw() marks binary-alpha fmt1 and partial-alpha fmt2 consistently.
        normal[1]["flags"] = 1
        self.census=dict(selected_files=[selected],textures=normal,world_keys={},registry_keys={})

    def test_all_keys_covered_but_unknown_owners_not_selected_and_fonts_keep_no_mips(self):
        report, selection = coverage.coverage(self.pack,self.census,self.probe,self.receipt)
        self.assertEqual(report["normal_packed_winners"],2)
        self.assertEqual(report["lossless_vq_format_opportunities"],2)
        self.assertEqual(report["source_owned_lossless_vq_keys"],1)
        self.assertEqual(report["owner_unclassified_keys"],1)
        self.assertEqual(selection["keys"][0]["key"],"00000001-00000002")
        self.assertIn("no-automatic-mips",report["normal_rows"][0]["mip_policy"])
        self.assertEqual(report["normal_rows"][1]["mip_policy"],"owner-and-sampling-policy-open")

    def test_source_bounds_hash_or_descriptor_mismatch_refuses_instead_of_inventing_owner(self):
        for kind in ("size","hash","range","descriptor","pack"):
            census,probe,receipt=map(copy.deepcopy,(self.census,self.probe,self.receipt))
            if kind=="size":probe["selected_files"][0]["size"]+=1
            if kind=="hash":probe["references"]["00000001-00000002"][0]["file_sha256"]="bad"
            if kind=="range":probe["references"]["00000001-00000002"][0]["header_offset"]=500
            if kind=="descriptor":census["textures"][0]["format"]=2
            if kind=="pack":receipt["dc/tex.pak"]["sha256"]="bad"
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                coverage.coverage(self.pack,census,probe,receipt)

    def test_loose_duplicates_and_quality_rows_stay_separate_from_packed_count(self):
        census=copy.deepcopy(self.census)
        census["textures"] += [dict(key="00000001-00000002",container="dc/tex/00000001-00000002.re4tex"),
                               dict(key="00000005-00000006",container="dc/texlow/00000005-00000006.re4tex")]
        report,_=coverage.coverage(self.pack,census,self.probe,self.receipt)
        self.assertEqual(report["normal_packed_winners"],2)
        self.assertEqual(report["stored_loose_descriptors"],2)
        self.assertEqual([r["winner_scope"] for r in report["loose_and_quality_rows"]],
                         ["normal-pack-wins","conditional-standard-quality-texlow"])

    def test_runtime_pair_identity_needs_same_tpl_and_dimensions_not_just_a_label(self):
        colour,mask='00000001-00000002','00000003-00000004'
        key=coverage.material_pair_identity(colour,mask)
        normal={key:dict(material='source-pair')}
        a=dict(path='st1/r100.arc',tpl_offset=128,width=64,height=64,owner_category='world-source')
        b=dict(a)
        probe=dict(references={colour:[a],mask:[b]})
        refs=coverage.pair_references(normal,probe,inventory_pairs=[])
        self.assertEqual(refs[key][0]['colour'],colour)
        self.assertEqual(refs[key][0]['mask'],mask)
        self.assertEqual(refs[key][0]['owner_categories'],['world-source'])
        b['height']=32
        self.assertEqual(coverage.pair_references(normal,probe,inventory_pairs=[]),{})
        b['height']=64;b['tpl_offset']=256
        self.assertEqual(coverage.pair_references(normal,probe,inventory_pairs=[]),{})

    def test_explicit_inventory_pairs_allow_different_source_tables_but_equal_dimensions(self):
        colour,mask='00000001-00000002','00000003-00000004'
        key=coverage.material_pair_identity(colour,mask)
        normal={key:dict(material='source-pair')}
        a=dict(path='ss/item/a.tpl',tpl_offset=0,width=64,height=64,owner_category='ui-inventory-model-or-image')
        b=dict(a,path='ss/eng/ss_pzzl.dat',tpl_offset=128)
        probe=dict(references={colour:[a],mask:[b]})
        refs=coverage.pair_references(normal,probe,inventory_pairs=[dict(color=colour,mask=mask)])
        self.assertEqual(refs[key][0]['method'],'explicit-source-selected-inventory-pair')
        self.assertEqual(refs[key][0]['owner_categories'],['ui-inventory-model-or-image'])
        b['width']=32
        self.assertEqual(coverage.pair_references(normal,probe,inventory_pairs=[dict(color=colour,mask=mask)]),{})

    def test_core_archive_has_proved_common_owner_but_no_automatic_mips(self):
        census,probe,receipt=map(copy.deepcopy,(self.census,self.probe,self.receipt))
        for data in (census,probe):data['selected_files'][0]['path']='etc/core.das'
        receipt['etc/core.das']=receipt.pop('ss/f001.tpl')
        ref=probe['references']['00000001-00000002'][0]
        ref['path'],ref['owner_category']='etc/core.das','other-source'
        report,selected=coverage.coverage(self.pack,census,probe,receipt)
        row=report['normal_rows'][0]
        self.assertIn('core-common-source',row['owner_categories'])
        self.assertTrue(row['source_owned_lossless_vq_selection'])
        self.assertIn('no-automatic-mips',row['mip_policy'])
        self.assertEqual(len(selected['keys']),1)


if __name__=="__main__":
    unittest.main()
