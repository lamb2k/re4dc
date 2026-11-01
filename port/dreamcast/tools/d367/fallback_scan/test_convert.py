#!/usr/bin/env python3
"""Synthetic ModelData conversion and actual renderer-body admission controls."""
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import convert


def fixture(triangles=32, capacity=2048):
    """Hand-authored triangle stream; no extracted/model data."""
    data=bytearray(256+capacity)
    struct.pack_into("<I",data,0,64)
    struct.pack_into("<III",data,12,144,160,176)
    data[24:26]=bytes([1,1])
    struct.pack_into("<HIII",data,26,1,224,0xa0000000,1)
    data[40]=4
    struct.pack_into("<IIHHI",data,48,96,128,3,3,0x20010801)
    data[64:68]=bytes([0,255,0,0])
    for i,p in enumerate(((0,0,0,0),(16,0,0,0),(0,16,0,0))):
        struct.pack_into("<4h",data,96+8*i,*p)
    for i,n in enumerate(((0,0,64,0),(0,64,0,0),(64,0,0,0))):
        struct.pack_into("<3bB",data,128+4*i,*n)
    for i,c in enumerate(((255,100,80,73),(80,255,100,93),(100,80,255,151))):
        data[144+4*i:148+4*i]=bytes(c)
    for i,uv in enumerate(((0,0),(256,0),(0,256))):
        struct.pack_into("<2h",data,160+4*i,*uv)
    data[176:184]=bytes([0,0,0,1,255,0,0,0])
    struct.pack_into("<II",data,224+24,capacity,triangles)
    stream=bytearray([0x90])+struct.pack(">H",triangles*3)
    for _ in range(triangles):
        for i in range(3):
            stream.extend(struct.pack(">4H",i,i,i,i))
    if len(stream)>capacity:
        raise ValueError("fixture capacity")
    data[256:256+len(stream)]=stream
    data=bytes(data)
    context=dict(schema=convert.SCHEMA,source_sha256=convert.sha(data),source_kind="PS2-converted-ModelData",
        ownership="source-model",provenance="hand-authored synthetic fixture, no game data",
        pose_space="source-normal-space",parts=[dict(index=0,static_vertex_colors=True,
        normal_matrices=[convert.IDENTITY],render=dict(blend=0,alpha_state=73,material_animation=False),
        lighting=dict(enabled=True,ambient_vertex=False,material_vertex=False,diffuse=2,
        ambient_rgb=[64,64,64],material_rgb=[128,128,128],tev_scale=1,
        actor_probe_mode=2,model_id=0x12,leon_marker=False,basis_valid=True,probe_valid=True,
        headroom_half=False,ganado_lit_toggle=False,ganado_mode=0,
        directional_lights=[dict(direction=[0,0,1],color_rgb=[64,64,64])]))])
    return data,context


def raw(context):
    return json.dumps(context,sort_keys=True).encode()


def decoded_triangles(stream):
    h=struct.unpack_from("<4B6H4f",stream)
    rs=3+bool(h[2]&1)+bool(h[2]&2)
    out=[]
    for i in range(h[4]):
        counts,first,idx=struct.unpack_from("<IHH",stream,32+8*i)
        nv,ni=counts&255,counts>>8&4095
        rows=[]
        for j in range(nv):
            r=struct.unpack_from("<"+"H"*rs,stream,h[6]*4+(first+j)*rs*2)
            rows.append(tuple(r[:3])+(r[3] if h[2]&1 else h[5],))
        strip=[]
        for b in stream[h[7]*4+idx:h[7]*4+idx+ni]:
            strip.append(rows[b&127])
            if b&128:
                for j in range(2,len(strip)):
                    out.append((strip[j-1],strip[j-2],strip[j]) if j&1 else tuple(strip[j-2:j+1]))
                strip=[]
        if strip:
            raise AssertionError("unterminated strip")
    return out


class Conversion(unittest.TestCase):
    def test_absent_zero_do_not_parse_or_normalize(self):
        source=b"arbitrary opaque bytes\x00\xff"
        for kwargs in ({},{"fold_light_scale":False,"bake_probe_decline":False}):
            result,receipt=convert.convert(source,b"not JSON",**kwargs)
            self.assertEqual(source,result)
            self.assertFalse(receipt["changed"])

    def test_actual_stream_topology_and_all_nonstream_bytes(self):
        data,context=fixture()
        out,receipt=convert.convert(data,raw(context),fold_light_scale=True)
        before=convert.parse_model_bin(data)
        triangles=convert.source_triangles(data,before["parts"][0],True)
        self.assertEqual(triangles,decoded_triangles(out[256:]))
        self.assertEqual(data[:256],out[:256])
        self.assertEqual(len(data),len(out))
        self.assertEqual(out[256:258],b"\xfe\x03")
        self.assertEqual(receipt["parts"][0]["resident_delta_bytes"],0)
        self.assertEqual(convert.convert(data,raw(context),True)[0],out)

    def test_quad_strip_degenerates_and_meshlet_split_keep_order(self):
        data,context=fixture(triangles=400,capacity=16384)
        data=bytearray(data)
        stream=bytearray()
        for opcode,indices in ((0x80,[0,1,2,0]),(0x98,[0,1,2,2,1,0,0,1,2]),(0x90,[0,1,2]*400)):
            stream.extend(bytes([opcode])+struct.pack(">H",len(indices)))
            for i in indices: stream.extend(struct.pack(">4H",i,i,i,i))
        data[256:]=stream+bytes(len(data)-256-len(stream))
        struct.pack_into("<I",data,252,409)
        context["source_sha256"]=convert.sha(data)
        out,receipt=convert.convert(bytes(data),raw(context),True)
        model=convert.parse_model_bin(data)
        self.assertEqual(convert.source_triangles(data,model["parts"][0],True),decoded_triangles(out[256:]))
        self.assertEqual(data[:256],out[:256])
        self.assertEqual(receipt["parts"][0]["triangles"],409)
        self.assertGreater(receipt["parts"][0]["meshlets"],1)

    def test_constant_ci_and_unsigned_uv_record_layouts(self):
        for signed in (False,True):
            data,context=fixture()
            data=bytearray(data)
            struct.pack_into("<I",data,32,0xa0000000 if signed else 0x20000000)
            stream=bytearray([0x90])+struct.pack(">H",96)
            for _ in range(32):
                for i in range(3):stream.extend(struct.pack(">4H",i,i,2,i) if signed else struct.pack(">3H",i,i,i))
            data[256:]=stream+bytes(len(data)-256-len(stream))
            context["source_sha256"]=convert.sha(data)
            out,_=convert.convert(bytes(data),raw(context),True)
            h=struct.unpack_from("<4B6H4f",out,256)
            self.assertEqual(h[2]&1,0)
            self.assertEqual(h[5],2 if signed else 0)
            self.assertEqual(decoded_triangles(out[256:]),convert.source_triangles(data,convert.parse_model_bin(data)["parts"][0],signed))

    def test_independent_flag_selection(self):
        data,context=fixture()
        context["parts"][0]["lighting"].update(material_rgb=[255,255,255],model_id=0x41)
        no,_=convert.convert(data,raw(context),fold_light_scale=True)
        yes,receipt=convert.convert(data,raw(context),bake_probe_decline=True)
        self.assertEqual(data,no)
        self.assertNotEqual(data,yes)
        self.assertEqual(receipt["parts"][0]["flags"],2)

    def test_vertex_colours_baked_alpha_stays_in_source(self):
        data,context=fixture()
        context["parts"][0]["lighting"].update(ambient_vertex=True,material_vertex=True)
        out,_=convert.convert(data,raw(context),bake_probe_decline=True)
        self.assertEqual(data[144:156],out[144:156])
        self.assertEqual(decoded_triangles(out[256:])[0],((0,0,0,0),(1,1,1,1),(2,2,2,2)))
        h=struct.unpack_from("<4B6H4f",out,256)
        words=[struct.unpack_from("<H",out,256+h[6]*4+i*10+8)[0] for i in range(3)]
        self.assertEqual(len(set(words)),3)

    def test_old_bake_marker_cannot_collide(self):
        self.assertEqual(convert.STATE&1,0)
        self.assertNotEqual(convert.STATE,0)
        self.assertNotIn(convert.FLAGS|1,(0,1))

    def test_refuse_unsafe_contexts(self):
        data,context=fixture()
        mutations=[
            lambda c:c.update(source_sha256="0"*64),
            lambda c:c.update(ownership="registry"),
            lambda c:c["parts"][0].update(static_vertex_colors=False),
            lambda c:c["parts"][0]["render"].update(alpha_state=256),
            lambda c:c["parts"][0]["render"].update(blend=1),
            lambda c:c["parts"][0]["render"].update(material_animation=True),
            lambda c:c["parts"][0].update(normal_matrices=[]),
            lambda c:c["parts"][0]["lighting"].update(tev_scale=float("nan")),
            lambda c:c["parts"][0]["lighting"].update(material_rgb=[0,128,128]),
            lambda c:c["parts"][0]["lighting"].update(leon_marker=True),
            lambda c:c["parts"][0]["lighting"].update(headroom_half=True),
            lambda c:c["parts"][0].update(render=[]),
            lambda c:c["parts"][0].update(lighting=[]),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                c=copy.deepcopy(context);mutation(c)
                with self.assertRaises(ValueError):
                    convert.convert(data,raw(c),True,True)

    def test_refuse_capacity_and_material_and_alias(self):
        data,context=fixture(triangles=1,capacity=32)
        with self.assertRaisesRegex(ValueError,"does not fit"):
            convert.convert(data,raw(context),True)
        for field,value in ((235,4),(44,1),(48,256),(40,31)):
            data,context=fixture()
            d=bytearray(data)
            if field in (235,40):d[field]=value
            else:struct.pack_into("<I",d,field,value)
            context["source_sha256"]=convert.sha(d)
            with self.assertRaises(ValueError):convert.convert(bytes(d),raw(context),True)

    def test_probe_basis_and_ganado_toggle_match_runtime_order(self):
        _,context=fixture()
        light=context["parts"][0]["lighting"]
        light.update(material_rgb=[255,255,255],basis_valid=False)
        self.assertEqual(convert.triggers(light),(False,False))  # non-Leon has no inverse-basis test
        light.update(ganado_lit_toggle=True,ganado_mode=0)
        self.assertEqual(convert.triggers(light),(False,True))
        light.update(ganado_mode=1)
        self.assertEqual(convert.triggers(light),(False,False))

    def test_cli_off_and_refusal_never_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);src=td/"source.bin";dst=td/"copy.bin"
            src.write_bytes(b"opaque\x00\xff")
            tool=str(Path(convert.__file__))
            run=subprocess.run([sys.executable,"-B",tool,str(src),str(dst),"--fold-light-scale=0"],capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(src.read_bytes(),dst.read_bytes())
            run=subprocess.run([sys.executable,"-B",tool,str(src),str(dst)],capture_output=True)
            self.assertEqual(run.returncode,2)
            self.assertEqual(src.read_bytes(),dst.read_bytes())


if __name__=="__main__":
    unittest.main()
