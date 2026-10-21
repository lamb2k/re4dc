"""Only bound canonical source-qualified mip chains enter the PAL8 composition."""
import copy
import json
import pathlib
import sys
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/d367'),str(ROOT/'tools/d367/mipmap21')]
import pal8_candidate as c
import texpack
import mipmap_twiddled as tw
import compact_native_pal8 as pal8
from test_compact_native_pal8 import source


def inputs():
    original={};before={};covrows=[];polrows=[]
    for i in range(1,7):
        key=(i,i);name='%08x-%08x'%key
        original[key]=source(32 if i!=2 else 64,gray=i!=6)
        before[key]=tw.add_mipmaps(original[key],enabled=True)[0]
        covrows.append(dict(key=name,package_sha256=c.sha(original[key]),
            native_world_references=[] if i in (2,5) else [dict(package='dc/native/r100/ps2-world.r4pw',part=i)],
            source_references=[dict(path='st1/r105.arc',owner_category='effect')] if i==2 else []))
        polrows.append(dict(key=name,original_package_sha256=c.sha(original[key]),candidate_package_sha256=c.sha(before[key]),
            native_world_selected=i in (1,3,4,6),generic_effect_candidate=i==2,
            source_proven_fixed_ID_UI=i==3,separate_actor_candidate=dict(owner='separate actor lane') if i==4 else None))
    a=texpack.build(original)[0];b=texpack.build(before)[0]
    cov=dict(source_pack_sha256=c.sha(a),normal_rows=covrows)
    pol=dict(source_pack_sha256=c.sha(a),selected_candidate_pack_sha256=c.sha(b),normal_rows=polrows)
    return a,b,cov,pol


class CanonicalComposition(unittest.TestCase):
    def test_default_off_pack_and_every_member_are_exact(self):
        a,b,cov,pol=inputs();result,report,before,after=c.build(a,b,cov,pol)
        self.assertEqual(result,b);self.assertEqual(before,after)
        self.assertEqual(report['changed_from_base'],0);self.assertEqual(report['canonical_palettes'],0)

    def test_enabled_exact_levels_and_unrelated_members_with_one_shared_palette(self):
        a,b,cov,pol=inputs();result,r,before,after=c.build(a,b,cov,pol,enabled=True)
        self.assertEqual(r['changed_from_base'],2);self.assertEqual(r['unchanged_from_base'],4)
        self.assertEqual(r['canonical_palettes'],1);self.assertEqual(r['aligned_PAL4_slots'],16)
        self.assertLess(len(result),len(b))
        for key in before:
            if key[0] not in (1,2):self.assertEqual(before[key],after[key]);continue
            n,p=tw.read_native_twiddled(before[key]),pal8.read_native_pal8(after[key])
            self.assertEqual(n.header[9:],p.header[9:]);self.assertEqual(n.texture[:3],p.texture[:3])
            self.assertEqual(n.texture[6],p.texture[6])
            for level in range(n.size.bit_length()):self.assertEqual(tw.decode_level(n,1<<level),pal8.decode_level(p,1<<level))
        self.assertEqual(r['held']['UI-or-separate-actor-owner'],2)
        self.assertEqual(r['held']['independent-color-palette-kept-native'],1)
        self.assertEqual(r['held']['not-in-already-qualified-cohort'],1)

    def test_a_qualified_flag_without_its_source_owner_binding_stays_held(self):
        a,b,cov,pol=inputs();cov['normal_rows'][0]['native_world_references']=[]
        result,r,before,after=c.build(a,b,cov,pol,enabled=True)
        self.assertEqual(before[(1,1)],after[(1,1)])
        self.assertEqual(r['changed_from_base'],1)
        self.assertEqual(r['held']['missing-source-owner-binding'],1)

    def test_wrong_pack_namespace_or_member_hash_is_refused(self):
        a,b,cov,pol=inputs()
        variants=[]
        x=copy.deepcopy(pol);x['selected_candidate_pack_sha256']='wrong';variants.append((a,b,cov,x))
        x=copy.deepcopy(pol);x['normal_rows'][0]['candidate_package_sha256']='wrong';variants.append((a,b,cov,x))
        x=copy.deepcopy(cov);x['normal_rows'].pop();variants.append((a,b,x,pol))
        for args in variants:
            with self.assertRaises(ValueError):c.build(*args,enabled=True)


if __name__=='__main__':unittest.main()
