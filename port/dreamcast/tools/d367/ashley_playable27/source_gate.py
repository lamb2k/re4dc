#!/usr/bin/env python3
"""Audit private playable conversions against original PS2 triangles and texels.

Windows Python with numpy/Pillow: source_gate.py PRIVATE_ROOT
The synthetic conversion poses are diagnostics, not gameplay/look acceptance.
"""
import collections
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import ps2_playable_ashley as play
import rig_header
import numpy as np
from PIL import Image


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def corner(p, n, w, uv):
    return (tuple(round(float(x), 4) for x in p), tuple(round(float(x), 6) for x in n),
            tuple((int(b), round(float(v), 6)) for b, v in sorted(w)),
            tuple(round(float(x), 9) for x in uv))


def audit(root):
    pc = play.ash.pc
    dat, drs = root/'inputs/pl01.dat', root/'inputs/pl01.drs'
    assert sha(dat) == '6799931bf25a9e53321bef1bcce737c156cb396d29fd7fc4c3436edb59725427'
    assert sha(drs) == '7dbffe5a7111f53dd20b491308bdaaca15cf7aab483e3a4866af8824020bb529'
    ps2 = {i:(tag, b) for i, tag, b in pc.pb.dat_entries(dat.read_bytes())}
    ptd = pc.load_module('ps2_tpl_decode', pc.WA/'from-main/ps2-trees/tools/ps2_tpl_decode.py')
    rows=[]
    for right in ('normal', 'r20e'):
        for left in ('open', 'closed'):
            profile=play.profile(right,left)
            out=root/f'conv-{right[0]}-{left[0]}'
            source=json.loads((out/'source.json').read_text())
            mesh=json.loads((out/'mesh.json').read_text())
            val=json.loads((out/'validation.json').read_text())
            assert source['source_archive']=='pl01' and source['source_model_id']==0
            assert source['name']==profile['preset']
            assert [(i['role'],i['source_bin_arc'],i['source_tpl_arc']) for i in source['infos']]==profile['sections']
            assert source['source_archive_sha256']==sha(drs) and source['ps2_archive_sha256']==sha(dat)
            assert val['weights']['folded_cloth_links']==[] and val['weights']['corners_truncated_to_3']==0
            assert val['zero_normals_replaced_by_face_normal']==0
            assert len(source['bones'])==141 and len(source['draw_slots'])==45
            atlas=Image.open(out/'atlas-rgba.png').convert('RGBA')
            aw,ah=atlas.size
            images=[]
            offsets={}
            for tpl in sorted({x[2] for x in profile['ps2_sources']}):
                offsets[tpl]=len(images)
                raw=pc.ps2_entry(ps2,tpl,'TPL')
                for entry in ptd.parse_tpl(raw)['entries']:
                    w,h,rgba,_=ptd.decode(raw,entry)
                    images.append((w,h,bytes(rgba)))
            for image in val['texture']['used']:
                x,y,w,h=val['texture']['cells'][str(image)]
                iw,ih,rgba=images[image]
                assert (w,h)==(iw,ih) and atlas.crop((x,y,x+w,y+h)).tobytes()==rgba
            expected=collections.Counter()
            degenerate=0
            for arc,mats,tpl,_ in profile['ps2_sources']:
                model=pc.pb.parse_bin(pc.ps2_entry(ps2,arc,'BIN'))
                for material,cs in pc.pb.triangles(model):
                    if material not in mats:continue
                    p=np.asarray([c['p'] for c in cs])
                    if not np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0])):
                        degenerate+=1;continue
                    image=offsets[tpl]+model.materials[material]['diffuse']
                    x,y,w,h=val['texture']['cells'][str(image)]
                    corners=[]
                    for c in cs:
                        u,v=[min(256,max(0,z)) for z in c['raw']['uv']]
                        weights=play.ash.rig_weights(c['w']).items()
                        corners.append(corner(c['p'],c['n'],weights,[(x+u*w/256)/aw,(y+v*h/256)/ah]))
                    expected[tuple(sorted(corners))]+=1
            actual=collections.Counter()
            slots=source['draw_slots']
            for t in mesh['triangles']:
                cs=[]
                for c in t['corners']:
                    v=c['vertex']
                    cs.append(corner(mesh['positions_mm'][v],c['normal'],
                        [(slots[b],w) for b,w in mesh['weights'][v]],c['uv']))
                actual[tuple(sorted(cs))]+=1
            if expected!=actual:
                raise AssertionError((str(out),'PS2 triangle/corner multiset differs',
                    next(iter(expected-actual),None),next(iter(actual-expected),None)))
            rig_header.generate(root/'source-gate-header',[out])
            rows.append(dict(name=profile['preset'],triangles=sum(actual.values()),
                degenerate_source_triangles=degenerate,draw_slots=len(slots),
                ps2_triangle_position_normal_weight_uv_multiset_exact=True,
                ps2_atlas_texels_and_alpha_exact=True,source_sha256=sha(out/'source.json'),
                mesh_sha256=sha(out/'mesh.json'),poses=val['sections'][0]['posed_ps2_to_gc_mm']['poses']))
    # Header authoring rejects another archive and altered role contracts, rather
    # than allowing model0/141/7 alone to request the player adapter.
    original=json.loads((root/'conv-n-o/source.json').read_text())
    negatives=[]
    for name,mutate in [('partner-archive',lambda s:s.update(source_archive='pl11')),
                        ('leon-owner',lambda s:s.update(source_model_id=3)),
                        ('partner-face-tpl',lambda s:s['infos'][1].update(source_tpl_arc=11)),
                        ('foreign-hand',lambda s:s['infos'][5].update(source_bin_arc=12)),
                        ('duplicate-slot',lambda s:s['draw_slots'].__setitem__(1,s['draw_slots'][0]))]:
        s=json.loads(json.dumps(original));mutate(s)
        d=root/'source-gate-negatives'/name;d.mkdir(parents=True,exist_ok=True)
        (d/'source.json').write_text(json.dumps(s))
        try:rig_header.generate(d/'header',[d])
        except ValueError:negatives.append(name)
        else:raise AssertionError(f'Header accepted {name}')
    report=dict(inputs={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in (dat,drs)},
                conversions=rows,header_refusals=negatives,
                scope='Full PS2 render inputs and existing solver adapter; no live gameplay/look qualification')
    (root/'source-gate.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    audit(Path(sys.argv[1]))
