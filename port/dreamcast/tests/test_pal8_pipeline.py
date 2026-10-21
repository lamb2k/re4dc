"""Explicit native format/mip validation and complete PAL8 payload accounting."""
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import convert_tpl as tpl
import compact_native_pal8 as pal8
import mipmap_twiddled as tw
import mipmap_pal4 as pal4
import mipmap_vq as vq
from assetpipe.texture import read_re4tex
from test_pal4_alpha import REGISTRY,mutate,synthetic
from test_compact_native_pal8 import source
from test_mipmap_pal4 import package as palette4
from test_mipmap_vq import native as vector_source


ALL=dict(pal4_alpha=True,cast_mipmap=True,twiddled_mipmap=True,pal4_mipmap=True,pal8_alpha=True,pal8_mipmap=True)


class PipelineFormats(unittest.TestCase):
    def test_each_family_requires_exact_explicit_admission_and_correct_chain_size(self):
        native=source();p4=palette4(64);p8=pal8.compact(native,enabled=True)[0]
        native_mips=tw.add_mipmaps(native,enabled=True)[0]
        v=vector_source(64)
        cases=[(native,{},{}),(v,{},{}),(synthetic(fmt=3),{},{}),
            (p4,dict(pal4_alpha=True),{}),
            (vq.add_mipmaps(v,enabled=True)[0],dict(cast_mipmap=True),{}),
            (native_mips,dict(cast_mipmap=True,twiddled_mipmap=True),dict(cast_mipmap=True)),
            (pal4.add_mipmaps(p4,enabled=True)[0],dict(pal4_alpha=True,cast_mipmap=True,pal4_mipmap=True),dict(pal4_alpha=True,cast_mipmap=True)),
            (p8,dict(pal4_alpha=True,pal8_alpha=True),dict(pal4_alpha=True)),
            (pal8.compact(native_mips,enabled=True)[0],dict(pal4_alpha=True,pal8_alpha=True,cast_mipmap=True,pal8_mipmap=True),dict(pal4_alpha=True,pal8_alpha=True,cast_mipmap=True))]
        for blob,allowed,denied in cases:
            w,h=tpl.TEXTURE.unpack_from(blob,48)[1:3]
            self.assertEqual(REGISTRY.tex_package_error(blob,w,h,**allowed),(None,'header'))
            self.assertEqual(REGISTRY.tex_package_error(blob,w,h,**ALL),(None,'header'))
            if allowed:self.assertIsNotNone(REGISTRY.tex_package_error(blob,w,h,**denied)[0])
            for bad in (blob[:-1],mutate(blob,8,1)):
                self.assertIsNotNone(REGISTRY.tex_package_error(bad,w,h,**ALL)[0])
        p8m=pal8.compact(native_mips,enabled=True)[0]
        for bad in (mutate(p8m,2,32),mutate(p8m,7,2),mutate(p8m,6,4|(1<<30))):
            self.assertIsNotNone(REGISTRY.tex_package_error(bad,64,64,**ALL)[0])

    def test_false_mip_flag_on_base_bytes_is_rejected_with_and_without_feature(self):
        for blob in (source(),vector_source(64),palette4(64),synthetic(fmt=3)):
            bad=mutate(blob,6,tpl.TEXTURE.unpack_from(blob,48)[6]|4)
            w,h=tpl.TEXTURE.unpack_from(blob,48)[1:3]
            self.assertIsNotNone(REGISTRY.tex_package_error(bad,w,h)[0])
            self.assertIsNotNone(REGISTRY.tex_package_error(bad,w,h,**ALL)[0])

    def test_descriptor_inventory_counts_PAL8_palette_and_all_existing_levels(self):
        base=source();chain=tw.add_mipmaps(base,enabled=True)[0]
        with tempfile.TemporaryDirectory() as directory:
            p=pathlib.Path(directory)/'fixture.re4tex'
            for blob in (base,chain):
                converted=pal8.compact(blob,enabled=True)[0];p.write_bytes(converted)
                stats=read_re4tex(p);t=tpl.TEXTURE.unpack_from(converted,48)
                self.assertEqual(stats['vram_bytes'],t[5]);self.assertEqual(stats['textures'][0]['data_bytes'],t[5])
                self.assertEqual(stats['textures'][0]['format'],'PAL8_ARGB4444')
                self.assertEqual(t[5],len(converted)-144)

    def test_selected_resolver_receipt_carries_explicit_features_without_promoting_loose(self):
        native=source();blob=pal8.compact(tw.add_mipmaps(native,enabled=True)[0],enabled=True)[0]
        resolver=lambda key:(blob,'one selected packed fixture')
        keys=[('00000001','00000002',64,64)]
        report=REGISTRY.check_textures(None,keys,None,resolver=resolver,**ALL)
        self.assertFalse(report['bad']);self.assertFalse(report['missing']);self.assertEqual(report['unique'],1)
        self.assertEqual(report['package_bytes'],len(blob))
        self.assertEqual(len(REGISTRY.check_textures(None,keys,None,resolver=resolver)['bad']),1)

    def test_existing_base_inventory_default_output_is_identical(self):
        old=subprocess.check_output(['git','-C',str(ROOT),'show','a6f05767b:port/dreamcast/tools/assetpipe/texture.py'])
        namespace={};exec(compile(old,'control-texture.py','exec'),namespace)
        with tempfile.TemporaryDirectory() as directory:
            p=pathlib.Path(directory)/'fixture.re4tex'
            for blob in (source(),vector_source(64),palette4(64)):
                p.write_bytes(blob);self.assertEqual(read_re4tex(p),namespace['read_re4tex'](p))

    def test_CLI_options_fail_closed_on_inconsistent_feature_sets_before_source_access(self):
        script=ROOT/'tools/d367/ps2world/world_registry.py'
        with tempfile.TemporaryDirectory() as directory:
            for args in (['--pal8-alpha'],['--pal8-mipmap'],['--twiddled-mipmap'],['--pal4-mipmap','--pal4-alpha']):
                p=subprocess.run([sys.executable,str(script),'--out',directory,*args],capture_output=True,text=True)
                self.assertEqual(p.returncode,2,p.stderr)
                self.assertIn('inconsistent native texture feature options',p.stderr)
                self.assertEqual(list(pathlib.Path(directory).iterdir()),[])


if __name__=='__main__':unittest.main()
