#!/usr/bin/env python3
"""Public synthetic fixtures; real existing writers + malformed/semantic gates."""
import contextlib
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import formats as F
import scan as S

HERE=Path(__file__).resolve().parent
TOOLS=HERE.parents[1]
BASE_KNOBS={"ACTOR_PROBE_LIGHT":"2","ACTOR_LIGHT_FAST_ONLY":"0","ACTOR_LIGHT_CAP":"0",
            "LEON_LIGHT_HEADROOM":"0","LEON_SOURCE_LIGHT":"1","GIGANTE_LIGHTS":"0","STATUE_LIGHTS":"0","GANADO_LIT_TOGGLE":"0"}


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj)
    return obj


def actor_blob():
    b=bytearray(64)
    struct.pack_into("<4B6H4f",b,0,0xfe,3,0,0,1,0,10,15,0,0,0.,0.,0.,1.)
    struct.pack_into("<IHH",b,32,3|(3<<8)|(1<<20),0,0)
    for i in range(3):struct.pack_into("<3H",b,40+i*6,i,i,i)
    b[60:63]=bytes((0,1,130))
    return bytes(b)


def cast_arrays():
    return [b"".join(struct.pack("<4h",*v,0) for v in ((0,0,0),(16,0,0),(0,16,0))),
            struct.pack("<4h",0,0,16384,0)*3,
            b"".join(struct.pack("<2H",*uv) for uv in ((0,0),(32768,0),(0,32768))),
            actor_blob(),struct.pack("<4B3f",0,0,0,1,1.,0.,0.)]


def model_bin(vertex_color=True):
    # Original ModelData with LE CPU arrays and deliberately BE GX stream.
    b=bytearray(288)
    struct.pack_into("<I",b,0,64)
    struct.pack_into("<3I",b,12,128,144,160)
    b[24]=1;b[25]=1
    struct.pack_into("<H",b,26,1)
    struct.pack_into("<III",b,28,192,0xe0000000 if vertex_color else 0x20000000,1)
    b[40]=4
    struct.pack_into("<IIHHI",b,48,80,112,3,3,0x20010801)
    for i,v in enumerate(((0,0,0),(16,0,0),(0,16,0))):struct.pack_into("<4h",b,80+i*8,*v,0)
    b[112:124]=bytes((0,0,64,0))*3
    b[128:140]=bytes((127,255,0,255,255,255,255,123,25,25,25,255))
    for i,uv in enumerate(((0,0),(257,0),(0,257))):struct.pack_into("<2h",b,144+i*4,*uv)
    b[160:168]=bytes((0,0,0,1,255,0,0,0))
    b[203]=4;b[204]=0;b[206]=0;b[212]=127
    stream=bytes((0x90,0,3))+b"".join(struct.pack(">4H" if vertex_color else ">3H",*(
        (i,i,i,i) if vertex_color else (i,i,i))) for i in range(3))
    b[224:224+len(stream)]=stream
    struct.pack_into("<II",b,216,64,1)
    return bytes(b)


def tagged(bin_data):
    head=bytearray(32)
    struct.pack_into("<I",head,0,1);struct.pack_into("<I",head,16,32);head[20:24]=b"BIN\0"
    return bytes(head)+bin_data


def dar(bin_data):
    head=bytearray(1024);head[:32]=F.CONTAINER_MAGIC
    payload=tagged(bin_data)
    struct.pack_into("<4I",head,32,0,len(payload),0,1024)
    struct.pack_into("<I",head,64,0xffffffff)
    return bytes(head)+payload


def esl():
    b=bytearray(64)
    b[:4]=bytes((1,0x12,7,9))
    struct.pack_into("<IH",b,4,0x12345678,444)
    b[10:12]=bytes((3,4))
    struct.pack_into("<3h3hHh",b,12,-2,30,40,1,2,3,0x103,5)
    return bytes(b)


def texture(pal=False):
    payload=bytes(64//2+32) if pal else bytes(128)
    desc=struct.pack("<64s8I",b"synthetic",8,8,4 if pal else 1,144,len(payload),0,1,0)
    body=desc+payload
    return struct.pack("<8s10I",b"RE4DCTX\0",2,48,96,1,48,144,len(payload),F.crc(body),1,0)+body


def registry(out):
    mr=module("fallback29_existing_registry",HERE.parent/"model_registry.py")
    p,n,u,g,w=cast_arrays()
    c=dict(source_info=0,position_count=3,normal_count=3,palette_count=1,triangles=1,skin_bytes=40,
        positions=p,normals=n,uv=u,stream=g,weights=[((0,0,0),1,[1.,0.,0.])],texture="t")
    s=dict(role=0,bin=4,tpl=5)
    r=dict(name="fixture-enemy",appearance=0x200,model_id=0x21,bones=1,sections=[s],chunks=[c],parents=[-1],
        bind=[[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.]],position_shift=4,archive="synthetic")
    f=dict(header=[0,4,1,3,3,1,1,0,1,0x20010801],positions=mr.digest(p),normals=mr.digest(n),weights=mr.digest(w),
        uv=mr.digest(u),parts=[("00000000ff0000000000ff0000",32,1,1,2)],normalized=(288,1,2))
    t=dict(textures=[dict(key=(1,2),whf=(8,8,1),sampler=(0,0,0,0,0,0,0,0),palette=None)])
    mr.write_package(str(out),0x103,{},[r],{"t":(1,2,8,8)},["t"],{("synthetic",4):f},{("synthetic",5):t},
                     [("synthetic",4)])
    return (out/"package/r103/registry.re4nmr").read_bytes()


def glod(out):
    gp=module("fallback29_existing_glod",HERE.parent/"leonlod/glod_pack.py")
    arrays=cast_arrays()
    lines=['static const char* appearance_names[1] = {"synthetic"};','static constexpr unsigned skin_stream_bytes=160;']
    for role in range(4):
        prefix=f"a0_i{role}"
        for k,b in zip(("pos","nrm","uv","gx"),arrays[:4]):
            lines.append(f'alignas(32) static unsigned char {prefix}_{k}[] = {{'+','.join(map(str,b))+'};')
        lines.append(f'static const Weight {prefix}_weights[] = {{\n{{{{0,0,0}},1,{{1.0,0.0,0.0}}}}\n}};')
        lines.append('{'+f'{role},3,3,1,1,64,{prefix}_pos,{prefix}_nrm,{prefix}_uv,{prefix}_gx,{prefix}_weights'+'}')
    header=out/"ganado_runtime.h";header.write_text('\n'.join(lines))
    path=out/"ganado.re4gl"
    with contextlib.redirect_stdout(io.StringIO()):gp.pack(path,header,['today=bundle'])
    return path.read_bytes(),header.read_bytes()


def world():
    folder=HERE.parent/"world_blender_roundtrip"
    sys.path.insert(0,str(folder))
    previous=sys.modules.get("package")
    try:
        # The existing fixtures import their sibling as `package`; our archive
        # CLI has the same basename. Isolate that import during discovery.
        sys.modules["package"]=module("fallback29_existing_world_package",folder/"package.py")
        fixture=module("fallback29_existing_world_fixtures",folder/"fixtures.py")
        files=fixture.basic_files()
    finally:
        sys.path.remove(str(folder))
        if previous is None:sys.modules.pop("package",None)
        else:sys.modules["package"]=previous
    return files["ps2-world.re4mesh"],files["ps2-world.r4pw"]


def make_tree(root):
    tree=root/"disc";(tree/"st1").mkdir(parents=True)
    (tree/"st1/r103.dar").write_bytes(dar(model_bin()))
    (tree/"dc/native/r103").mkdir(parents=True)
    mesh,side=world()
    (tree/"dc/native/r103/ps2-world.re4mesh").write_bytes(mesh)
    (tree/"dc/native/r103/ps2-world.r4pw").write_bytes(side)
    pack=module("fallback29_existing_texpack",HERE.parent/"texpack.py")
    textures={(0x11223344+i,0x99aabbcc-i):texture(i==0) for i in range(3)}
    (tree/"dc/tex.pak").write_bytes(pack.build(textures)[0])
    resident=struct.pack("<4H2I",0x103,8,8,1,0x11223344,0x99aabbcc)+bytes(496)
    (tree/"dc/resident.bin").write_bytes(resident)
    return tree


class ScannerTests(unittest.TestCase):
    def test_model_native_endian_and_material(self):
        m=F.parse_model_bin(model_bin())
        p=m['parts'][0]
        self.assertEqual(p['vertices'],3);self.assertEqual(p['triangles'],1)
        self.assertEqual(p['primitive_records'][0]['records'],[(0,0,0,0),(1,1,1,1),(2,2,2,2)])
        self.assertEqual(p['material_flags'],4);self.assertEqual(p['uv_excess'],1)

    def test_uv_significant_bits_drop_trailing_zero(self):
        self.assertEqual(F.excess_bits([0,256,32768,-32768]),0)
        self.assertEqual(F.excess_bits([257]),1)
        self.assertEqual(F.excess_bits([65535]),8)

    def test_uv32_uses_resolved_native_actor_uv16_recipe(self):
        m=F.parse_model_bin(model_bin());p=m['parts'][0]
        p.update(texture_width=8,texture_height=8)
        ctx={'render':{'uv_offset':[0,0]}}
        for value,expected in (('0','predicted'),('1','clear'),(None,'unknown')):
            knobs=dict(BASE_KNOBS)
            if value is not None:knobs['NATIVE_ACTOR_UV16']=value
            with self.subTest(recipe=value):
                row=next(r for r in S.classify_part(m,p,ctx,knobs,{}) if r['reason']=='a_uv32')
                self.assertEqual(row['status'],expected)
                self.assertEqual(row['knob'],'NATIVE_ACTOR_UV16')
                self.assertEqual(row['recipe_value'],value if value is not None else 'unknown')

    def test_model_bounds_refusal(self):
        for offset,value in ((48,999999),(28,32),(16,999999)):
            b=bytearray(model_bin());struct.pack_into('<I',b,offset,value)
            with self.subTest(offset=offset),self.assertRaises(F.Invalid):F.parse_model_bin(bytes(b))
        with self.assertRaises(F.Invalid):F.parse_model_bin(model_bin()[:-1])

    def test_gx_bad_indices_and_counts_refused(self):
        for offset,raw in ((227,b'\xff\xff'),(225,b'\xff\xff'),(224,b'\xff')):
            b=bytearray(model_bin());b[offset:offset+len(raw)]=raw
            with self.subTest(offset=offset),self.assertRaises(F.Invalid):F.parse_model_bin(bytes(b))

    def test_native_dar_identifies_archive_slot(self):
        x=F.parse_room_archive(dar(model_bin()),'st1/r103.dar')
        self.assertEqual(x['models'][0]['key'],'st1/r103.dar/DVD[0]/ARC[0x4]')
        self.assertEqual(x['models'][0]['parts'][0]['offset'],192)
        m=x['models'][0]
        self.assertEqual((m['source_offset'],m['source_length']),(1056,288))
        self.assertEqual(F.sha(dar(model_bin())[m['source_offset']:m['source_offset']+m['source_length']]),m['source_sha256'])

    def test_native_esl_spawn_candidates(self):
        r=F.parse_esl(esl(),'etc/emleon00.esl')[0]
        self.assertEqual((r['enemy_id'],r['room'],r['type'],r['hp']),(0x12,0x103,7,444))
        self.assertEqual(r['position'],[-20,300,400])
        self.assertEqual(r['status'],'inventory')
        for data in (b'',esl()[:-1],bytes(0x2020)):
            with self.assertRaises(F.Invalid):F.parse_esl(data)

    def test_native_esl_does_not_bind_enemy_archive(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'etc').mkdir();(root/'em').mkdir()
            (root/'etc/emleon00.esl').write_bytes(esl())
            (root/'em/em12.drs').write_bytes(dar(model_bin()))
            r=S.scan_tree(root,['r103'])
            self.assertEqual(len(r['spawn_inventory']),1)
            self.assertEqual(r['spawn_inventory'][0]['room'],'r103')
            self.assertEqual({x['room'] for x in r['rows']},{'unassigned'})

    def test_bad_archive_offset_is_not_scanned(self):
        b=bytearray(dar(model_bin()));struct.pack_into('<I',b,1024+16,0)
        with self.assertRaises(F.Invalid):F.parse_room_archive(bytes(b))

    def test_existing_registry_writer(self):
        with tempfile.TemporaryDirectory() as td:
            data=registry(Path(td));x=F.parse_registry(data)
        self.assertEqual(x['room'],0x103)
        self.assertEqual(x['models'][0]['name'],'fixture-enemy')
        self.assertEqual(x['models'][0]['parts'][0]['vertices'],3)

    def test_registry_hash_cannot_hide_changed_geometry(self):
        with tempfile.TemporaryDirectory() as td:data=bytearray(registry(Path(td)))
        # Change geometry digest, then repair only the outer package digests.
        geom_at=struct.unpack_from('<I',data,64+2*16+4)[0]
        data[geom_at+52]^=1
        struct.pack_into('<II',data,36,F.crc(data[64:]),F.fnv(data[64:]))
        struct.pack_into('<I',data,44,0);struct.pack_into('<I',data,44,F.crc(data[:64]))
        with self.assertRaisesRegex(F.Invalid,'geometry digest'):F.parse_registry(bytes(data))

    def test_existing_pl08_writer(self):
        writer=module('fallback29_existing_pl08',HERE.parent/'pl08_pack.py')
        arrays={};chunks=[]
        for i in range(3):
            names=[]
            for kind,b in zip(('pos','nrm','uv','gx','w'),cast_arrays()):
                name=f'c{i}_{kind}';names.append(name);arrays[name]=b
            chunks.append(dict(source_info=i,position_count=3,normal_count=3,palette_count=1,triangles=1,
                               stream_bytes=64,arrays=names))
        data=writer.build(arrays,chunks)[0]
        x=F.parse_pl08(data)
        self.assertEqual([p['index'] for p in x['parts']],[0,1,8])
        with self.assertRaises(F.Invalid):F.parse_pl08(data[:-1])

    def test_existing_glod_writer_and_compiled_header(self):
        with tempfile.TemporaryDirectory() as td:data,header=glod(Path(td))
        x=F.parse_glod(data)
        self.assertEqual((x['levels'],x['appearances']),(1,1))
        self.assertEqual(len(x['models'][0]['parts']),2)
        self.assertEqual(len(F.parse_compiled_header(header,'cast.h')['parts']),4)

    def test_glod_bad_hash(self):
        with tempfile.TemporaryDirectory() as td:data,_=glod(Path(td))
        with self.assertRaises(F.Invalid):F.parse_glod(data[:-1])

    def test_existing_world_identity_fixture(self):
        mesh,side=world();x=F.parse_world(mesh,side)
        self.assertEqual((x['parts'],x['meshlets'],x['placements']),(3,6,3))
        self.assertEqual([p['vertices'] for m in x['models'] for p in m['parts']],[5,5,5])

    def test_world_checksum_and_unsupported_extensions_refused(self):
        mesh,side=world();b=bytearray(mesh);b[-1]^=1
        with self.assertRaises(F.Invalid):F.parse_world(bytes(b),side)
        b=bytearray(mesh);struct.pack_into('<I',b,68,1)
        with self.assertRaises(F.Invalid):F.parse_world(bytes(b),side)

    def test_world_physical_variants_use_existing_writers(self):
        # The minimal Build12 fixture is accepted by each existing owning codec.
        world()  # Existing codec makes convert_room_bins importable.
        fixture=module('fallback29_variant_fixture',TOOLS/'cloud/build12/fixtures.py')
        variants=module('fallback29_variant_writer',TOOLS/'scenery_data_variants.py')
        split=module('fallback29_split_writer',TOOLS/'scenery_record_split.py')
        dedup=module('fallback29_dedup_writer',HERE.parent/'dedup_offline23/offline_dedup.py')
        mesh,side=fixture.capacity(2)
        for kind,label in (('local-indexed','SLI1'),('direct-strips','SDS1')):
            output,_,_=variants.convert(mesh,kind,side)
            result=F.parse_world(output,side)
            self.assertEqual(result['layout'],label)
            self.assertEqual(result['meshlets'],2)
            self.assertEqual(result['lineage']['source_crc'],struct.unpack_from('<I',mesh,12)[0])
        output=split.split_package(mesh)
        self.assertEqual(F.parse_world(output,side)['layout'],'R4IM-v4-split')
        # Give the first source meshlet one shared position and require SDO3
        # decoding before ordinary geometry/bounds validation.
        changed=bytearray(mesh);vo=struct.unpack_from('<I',changed,52)[0]
        changed[vo+12:vo+18]=changed[vo:vo+6]
        struct.pack_into('<I',changed,12,F.crc(changed[80:]))
        output,_,_=dedup.convert(bytes(changed))
        result=F.parse_world(output,side)
        self.assertEqual(result['layout'],'SDO3')
        self.assertEqual(result['models'][0]['parts'][0]['meshlets'][0]['stored_position_repeats'],1)

    def test_world_variant_policy_and_source_binding(self):
        world()
        fixture=module('fallback29_variant_fixture_binding',TOOLS/'cloud/build12/fixtures.py')
        variants=module('fallback29_variant_writer_binding',TOOLS/'scenery_data_variants.py')
        mesh,side=fixture.capacity(1)
        output,_,_=variants.convert(mesh,'local-indexed',side)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);folder=root/'dc/native/r103';folder.mkdir(parents=True)
            (folder/'ps2-world.re4mesh').write_bytes(mesh);(folder/'ps2-world.r4pw').write_bytes(side)
            (folder/'ps2-sli1.re4mesh').write_bytes(output)
            result=S.scan_tree(root,['r103'])
            self.assertEqual(result['models'],2)
            self.assertEqual(result['status'],'SCANNED')
            bad=bytearray(output);struct.pack_into('<I',bad,72,0)
            (folder/'ps2-sli1.re4mesh').write_bytes(bad)
            result=S.scan_tree(root,['r103'])
            self.assertEqual(result['status'],'INCOMPLETE')
            self.assertTrue(any('source CRC/extent mismatch' in c['message'] for c in result['coverage']))

    def test_texpack_existing_writer_palette_and_missing(self):
        writer=module('fallback29_existing_texpack2',HERE.parent/'texpack.py')
        data=writer.build({(1,2):texture(True),(3,4):texture()})[0]
        self.assertTrue(F.parse_texpak(data)['00000001-00000002']['entries'][0]['palette'])
        b=bytearray(data);b[-2048+144]^=1
        with self.assertRaises(F.Invalid):F.parse_texpak(bytes(b))

    def test_resident_duplicates_and_padding_refused(self):
        row=struct.pack('<4H2I',0x103,8,8,1,1,2)
        self.assertEqual(F.parse_resident(row+bytes(496))[0]['room'],0x103)
        for b in (row+row+bytes(480),bytes(16)+row+bytes(480),row):
            with self.subTest(size=len(b)),self.assertRaises(F.Invalid):F.parse_resident(b)

    def test_missing_lighting_remains_unknown(self):
        m=F.parse_model_bin(model_bin());rows=S.classify_part(m,m['parts'][0],{}, {}, {})
        d={r['reason']:r for r in rows}
        self.assertEqual(d['a_lit_scale']['status'],'unknown')
        self.assertEqual(d['a_probe_miss']['status'],'unknown')
        self.assertEqual(d['a_lit_exact']['status'],'unknown')
        self.assertEqual(d['a_vertex_colors']['status'],'static')

    def test_probe_decline_does_not_imply_exact(self):
        m=F.parse_model_bin(model_bin());m['model_id']=0x37
        ctx=dict(lighting=dict(enabled=True,ambient_vertex=False,material_vertex=False,diffuse=2,material_rgb=[255]*3,
            tev_scale=1,leon_marker=False,basis_valid=True,probe_valid=True,significant_lights=1))
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],ctx,BASE_KNOBS, {})}
        self.assertEqual(d['a_probe_miss']['status'],'predicted')
        self.assertEqual(d['a_lit_scale']['status'],'clear')
        self.assertNotEqual(d['a_lit_exact']['status'],'predicted')

    def test_object_id_does_not_impersonate_ganado_id(self):
        m=F.parse_model_bin(model_bin())
        ctx=dict(model_id=0x12,model_kind=1,lighting=dict(enabled=True,ambient_vertex=False,material_vertex=False,
            diffuse=2,material_rgb=[255]*3,tev_scale=1,leon_marker=False,basis_valid=True,probe_valid=True))
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],ctx,BASE_KNOBS,{})}
        self.assertEqual(d['a_probe_miss']['status'],'predicted')
        ctx['model_kind']=0
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],ctx,BASE_KNOBS,{})}
        self.assertEqual(d['a_probe_miss']['status'],'clear')

    def test_probe_unknown_recipe_and_leon_precedence(self):
        m=F.parse_model_bin(model_bin())
        ctx=dict(model_id=0x12,lighting=dict(enabled=True,ambient_vertex=False,material_vertex=False,
            diffuse=2,material_rgb=[255]*3,tev_scale=1,leon_marker=True,basis_valid=True,probe_valid=True,ganado_mode=0))
        unknown=dict(BASE_KNOBS);unknown.pop('ACTOR_PROBE_LIGHT')
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],ctx,unknown,{})}
        self.assertEqual(d['a_probe_miss']['status'],'unknown')
        self.assertEqual(d['a_lit_exact']['status'],'unknown')
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],ctx,dict(BASE_KNOBS,GANADO_LIT_TOGGLE='1'),{})}
        self.assertEqual(d['a_probe_miss']['status'],'clear')
        ctx['lighting']['leon_marker']=False
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],ctx,BASE_KNOBS,{})}
        self.assertEqual(d['a_probe_miss']['status'],'clear')
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],ctx,dict(BASE_KNOBS,GANADO_LIT_TOGGLE='1'),{})}
        self.assertEqual(d['a_probe_miss']['status'],'predicted')

    def test_low_scale_both_predicates_but_vertex_precedes_scale(self):
        m=F.parse_model_bin(model_bin());m['model_id']=0x12
        l=dict(enabled=True,ambient_vertex=False,material_vertex=False,diffuse=2,material_rgb=[128,255,255],
               tev_scale=1,leon_marker=False,basis_valid=True,probe_valid=True)
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],{'lighting':l},BASE_KNOBS, {})}
        self.assertEqual(d['a_lit_scale']['status'],'predicted');self.assertEqual(d['a_lit_exact']['status'],'predicted')
        l['ambient_vertex']=True
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],{'lighting':l},BASE_KNOBS, {})}
        self.assertEqual(d['a_lit_scale']['status'],'clear');self.assertEqual(d['a_lit_colour']['status'],'predicted')

    def test_offline_tag_alone_does_not_prove_admission(self):
        m=F.parse_model_bin(model_bin());p=m['parts'][0];p['bake']={'fallback29':True}
        l=dict(enabled=True,ambient_vertex=False,material_vertex=False,diffuse=2,material_rgb=[128,255,255],
               tev_scale=1,leon_marker=False)
        d={r['reason']:r for r in S.classify_part(m,p,{'lighting':l},dict(BASE_KNOBS,FALLBACK_SCAN29='1'),{})}
        self.assertEqual(d['offline_light29']['status'],'candidate')
        self.assertEqual(d['a_lit_scale']['status'],'candidate')
        self.assertEqual(d['a_lit_exact']['status'],'candidate')

    def test_missing_recipe_keeps_proven_material_condition_conditional(self):
        m=F.parse_model_bin(model_bin())
        l=dict(enabled=True,ambient_vertex=False,material_vertex=False,diffuse=1,material_rgb=[255]*3,
               tev_scale=1,leon_marker=False)
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],{'lighting':l},{},{})}
        self.assertEqual(d['a_lit_scale']['status'],'candidate')
        self.assertEqual(d['a_probe_miss']['status'],'candidate')

    def test_non_leon_singular_basis_is_not_generic_basis_rejection(self):
        m=F.parse_model_bin(model_bin())
        l=dict(enabled=True,ambient_vertex=False,material_vertex=False,diffuse=2,material_rgb=[255]*3,
               tev_scale=1,leon_marker=False,basis_valid=False,significant_lights=1)
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],{'lighting':l},dict(BASE_KNOBS,ACTOR_PROBE_LIGHT='0'),{})}
        self.assertEqual(d['a_lit_basis']['status'],'clear')
        self.assertEqual(d['a_lit_exact']['status'],'clear')

    def test_chunk_records_use_adjacent_positions_and_distinct_normals(self):
        b=bytearray(actor_blob());struct.pack_into('<H',b,46,0)
        parsed=F.parse_actor_blob(bytes(b),3,3,3)
        self.assertFalse(parsed['meshlets'][0]['chunk_unique'])
        self.assertTrue(parsed['meshlets'][0]['chunk_normal_unique'])
        m=F.parse_model_bin(model_bin());p=m['parts'][0];p.update(parsed)
        d={r['reason']:r for r in S.classify_part(m,p,{},dict(BASE_KNOBS,CHAR_CHUNK='1'),{})}
        self.assertEqual(d['a_chunk_unique']['status'],'clear')
        self.assertEqual(d['a_chunk_nuniq']['status'],'candidate')
        self.assertEqual(d['a_chunk_nuniq']['vertices'],3)
        d={r['reason']:r for r in S.classify_part(m,p,{'render':{'alpha_state':511}},dict(BASE_KNOBS,CHAR_CHUNK='1'),{})}
        self.assertEqual(d['a_chunk_nuniq']['status'],'inert')
        self.assertEqual(d['a_chunk_alpha']['status'],'candidate')

    def test_fast_only_does_not_claim_exact(self):
        m=F.parse_model_bin(model_bin())
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],{}, {'ACTOR_LIGHT_FAST_ONLY':'1'}, {})}
        self.assertEqual(d['a_lit_scale']['status'],'inert');self.assertEqual(d['a_lit_exact']['status'],'clear')
        ctx={'render':{'flat':True,'alpha_state':511}}
        d={r['reason']:r for r in S.classify_part(m,m['parts'][0],ctx,
            {'ACTOR_LIGHT_FAST_ONLY':'1','ACTOR_BYTES_LEAN':'0'}, {})}
        self.assertEqual(d['a_flat_rewrite']['status'],'inert')

    def test_leon_toggle_constant_bypasses_probe_and_generic(self):
        m=F.parse_model_bin(model_bin())
        ctx=dict(lighting=dict(enabled=True,ambient_vertex=False,material_vertex=False,diffuse=1,
            material_rgb=[128]*3,tev_scale=1,leon_marker=True,basis_valid=True,probe_valid=True))
        knobs=dict(BASE_KNOBS,LEON_LIGHT_TOGGLE='1')
        rows=lambda:{r['reason']:r for r in S.classify_part(m,m['parts'][0],ctx,knobs,{})}
        d=rows()
        self.assertEqual(d['a_lit_scale']['status'],'candidate')
        self.assertEqual(d['a_probe_miss']['status'],'candidate')
        self.assertEqual(d['a_lit_exact']['status'],'candidate')
        for mode in (0,3):
            ctx['lighting']['leon_mode']=mode;d=rows()
            for reason in ('a_lit_scale','a_lit_colour','a_probe_miss','a_lit_fourth','a_lit_basis','a_lit_exact'):
                self.assertEqual(d[reason]['status'],'inert')
        ctx['lighting']['leon_mode']=2;d=rows()
        self.assertEqual(d['a_lit_scale']['status'],'predicted')
        self.assertEqual(d['a_probe_miss']['status'],'predicted')
        ctx['lighting']['leon_mode']=0;knobs.pop('ACTOR_PROBE_LIGHT');d=rows()
        self.assertEqual(d['a_lit_scale']['status'],'candidate')
        self.assertEqual(d['a_probe_miss']['status'],'candidate')

    def test_full_scan_preserves_inputs_and_determinism(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);tree=make_tree(root)
            before={p.relative_to(tree).as_posix():F.sha(p.read_bytes()) for p in tree.rglob('*') if p.is_file()}
            for name in ('one','two'):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(S.main([str(tree),'--out',str(root/name),'--rooms','r103','--strict']),0)
            for path in (root/'one').iterdir():self.assertEqual(path.read_bytes(),(root/'two'/path.name).read_bytes())
            after={p.relative_to(tree).as_posix():F.sha(p.read_bytes()) for p in tree.rglob('*') if p.is_file()}
            self.assertEqual(before,after)
            report=json.loads((root/'one/report.json').read_text())
            self.assertEqual(report['models'],3);self.assertEqual(report['textures'],3)

    def test_hash_bound_context_and_stale_context_refusal(self):
        with tempfile.TemporaryDirectory() as td:
            tree=make_tree(Path(td));a=S.scan_tree(tree,['r103']);ctx=a['context_template']
            dar=next(s for s in ctx['sources'] if s['path'].endswith('.dar'))
            part=dar['models'][0]['parts'][0]
            part['lighting']={'enabled':True,'ambient_vertex':False,'material_vertex':False,'diffuse':2,
                              'material_rgb':[100,255,255],'tev_scale':1,'leon_marker':False}
            result=S.scan_tree(tree,['r103'],BASE_KNOBS,ctx)
            row=next(r for r in result['rows'] if r['source'].endswith('.dar') and r['reason']=='a_lit_scale')
            self.assertEqual(row['status'],'predicted')
            dar['sha256']='0'*64
            with self.assertRaisesRegex(F.Invalid,'stale context'):S.scan_tree(tree,['r103'],context=ctx)

    def test_bad_context_types_are_rejected(self):
        for key,val in (('enabled',1),('tev_scale',float('nan')),('material_rgb',[256,0,0]),('significant_lights',9)):
            c=dict(schema=S.CONTEXT_SCHEMA,sources=[dict(path='x',sha256='0'*64,models=[dict(key='m',parts=[dict(
                index=0,lighting={key:val})])])])
            with self.subTest(key=key),self.assertRaises(F.Invalid):S.validate_context(c)

    def test_unassigned_global_actor_not_assumed_in_every_room(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'em').mkdir();(root/'em/em12.drs').write_bytes(dar(model_bin()))
            result=S.scan_tree(root,['r103'])
            self.assertEqual({r['room'] for r in result['rows']},{'unassigned'})
            self.assertEqual(result['status'],'INCOMPLETE')

    def test_missing_package_strict_exit(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);tree=make_tree(root);(tree/'dc/native/r103/ps2-world.r4pw').unlink()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(S.main([str(tree),'--out',str(root/'out'),'--rooms','r103','--strict']),1)
            cov=(root/'out/coverage.tsv').read_text()
            self.assertIn('missing matching R4PW',cov)

    def test_symlink_escape_and_output_overlap_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);tree=make_tree(root);outside=root/'outside.bin';outside.write_bytes(model_bin())
            (tree/'outside.bin').symlink_to(outside)
            with self.assertRaisesRegex(F.Invalid,'symlink escapes'):S.scan_tree(tree,['r103'])
            with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(S.main([str(tree),'--out',str(tree/'out')]),2)

    def test_unknown_reasons_not_added_to_resolved_ranking(self):
        with tempfile.TemporaryDirectory() as td:
            tree=make_tree(Path(td));result=S.scan_tree(tree,['r103'])
            ranked=S.aggregate(result['rows'],('room',))
            self.assertNotIn('a_lit_scale',{r['reason'] for r in ranked})
            self.assertTrue(any(r['reason']=='a_lit_scale' and r['status']=='unknown' for r in result['rows']))


if __name__=='__main__':unittest.main()
