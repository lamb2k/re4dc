#!/usr/bin/env python3
"""Relocate sealed original PS2 atlas cells without changing source geometry.

Windows Python with the existing ps2_cast dependencies. Creates a new private
candidate; native checks/finish/registry admission and animated look stay separate.
The explicit contract selects input hashes. No runtime or converter default changes.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
from PIL import Image
import ps2_cast as pc


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_forms(root, contract):
    """All input bytes must match the sealed selection before creating output."""
    if contract.get('schema') != 'boss18-common-source-atlas-1' or len(contract['forms']) != 2:
        raise ValueError('expected the explicit two-form source contract')
    archive = root / contract['archive']
    if sha(archive) != contract['archive_sha256']:
        raise ValueError('original PS2 archive hash changed')
    entries = {i:(tag, data) for i, tag, data in pc.pb.dat_entries(archive.read_bytes())}
    forms = []
    required = {'source.json','source-bindings.json','mesh.json','validation.json',
                'atlas.png','manifest.json','runtime/castmodel_runtime.h'}
    for selection in contract['forms']:
        if set(selection) != {'path','files'} or set(selection['files']) != required:
            raise ValueError('the source selection must pin every required original input')
        source = root / selection['path']
        for file, digest in selection['files'].items():
            if sha(source / file) != digest:
                raise ValueError('sealed original input changed: ' + selection['path'] + '/' + file)
        value = dict(path=source, selection=selection)
        for key, file in (('validation','validation.json'),('source','source.json'),
                          ('mesh','mesh.json'),('bindings','source-bindings.json')):
            value[key] = json.loads((source / file).read_text(encoding='utf-8'))
        if not value['validation']['texture']['opaque'] or value['validation']['winding_flipped']:
            raise ValueError('this source candidate requires opaque, original-winding forms')
        if value['source']['ps2_archive_sha256'] != contract['archive_sha256']:
            raise ValueError('source form names another original PS2 archive')
        value['atlas'] = Image.open(source / 'atlas.png').convert('RGBA')
        manifest = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
        if (list(value['atlas'].size) != value['validation']['texture']['atlas'] or
            value['mesh']['source_sha256'] != selection['files']['source.json'] or
            manifest['levels']['conservative']['header_sha256'] != selection['files']['runtime/castmodel_runtime.h']):
            raise ValueError('sealed source/mesh/atlas/native manifest identities disagree')
        forms.append(value)
    return forms, entries


def plan_cells(forms):
    """Share only byte-identical original TPL images including sampler gutters."""
    tiles = {}
    for form in forms:
        validation = form['validation']; texture = validation['texture']
        bases = sorted((base, int(tpl, 16)) for tpl, base in texture['image_bases'].items())
        local = {}
        for image in texture['used']:
            base, tpl = max(row for row in bases if row[0] <= image)
            key = (form['source']['source_archive'], tpl, image - base)
            gutter = validation['atlas_wrap_gutters'][str(image)]
            x, y, w, h = texture['cells'][str(image)]
            left, top, right, bottom = gutter['padding']
            if (min(left,top,right,bottom) < 0 or min(x-left,y-top) < 0 or
                x+w+right > form['atlas'].width or y+h+bottom > form['atlas'].height):
                raise ValueError('source gutter rectangle escapes the original atlas')
            pixels = form['atlas'].crop((x-left, y-top, x+w+right, y+h+bottom))
            if pixels.size != (w+left+right, h+top+bottom):
                raise ValueError('source gutter dimensions changed')
            evidence = dict(size=list(pixels.size), padding=gutter['padding'], wrap=gutter['wrap'],
                            uv_bounds=gutter['uv_bounds'], inner=[w,h],
                            pixels_sha256=hashlib.sha256(pixels.tobytes()).hexdigest())
            if key in tiles:
                if evidence != tiles[key]['evidence']:
                    raise ValueError('shared source TPL image/gutter differs: ' + str(key))
            else:
                tiles[key] = dict(pixels=pixels, evidence=evidence)
            local[image] = key
        form['image_keys'] = local
    keys = sorted(tiles)
    rectangles, size = pc.pack_atlas([(i, *tiles[key]['pixels'].size) for i, key in enumerate(keys)])
    if max(size) > 1024:
        raise ValueError('candidate exceeds the existing 1024 texture size used by these source inputs')
    atlas = Image.new('RGBA', size, (0,0,0,255))
    for i, key in enumerate(keys):
        x, y, _, _ = rectangles[i]
        atlas.paste(tiles[key]['pixels'], (x,y))
        left, top, _, _ = tiles[key]['evidence']['padding']
        w, h = tiles[key]['evidence']['inner']
        tiles[key]['cell'] = [x+left,y+top,w,h]
    return atlas, tiles


def relocate_mesh(form, entries, cells, size):
    """Re-read original PS2 corner order/raw UVs; preserve all other mesh fields."""
    mesh = copy.deepcopy(form['mesh']); validation = form['validation']
    texture = validation['texture']; aw, ah = texture['atlas']; nw, nh = size
    bases = {int(tpl,16):base for tpl,base in texture['image_bases'].items()}
    cursor = 0
    for info, binding in enumerate(form['bindings']):
        tag, raw = entries[binding['bin'] - 4]
        if tag != 'BIN':
            raise ValueError('source section is not an original BIN')
        model = pc.pb.parse_bin(raw)
        for material, corners in pc.pb.triangles(model):
            a, b, c = (np.asarray(q['p']) for q in corners)
            normal = np.cross(b-a,c-a); length = np.linalg.norm(normal)
            if not length:
                continue
            normal /= length
            triangle = mesh['triangles'][cursor]
            if triangle['source_info'] != info:
                raise ValueError('source triangle order differs')
            image = bases[binding['tpl']] + model.materials[material]['diffuse']
            ox, oy, ow, oh = texture['cells'][str(image)]
            nx, ny, w, h = cells[image]
            if [ow,oh] != [w,h]:
                raise ValueError('source image was resized')
            for original, corner in zip(corners, triangle['corners']):
                vertex = corner['vertex']; u, v = original['raw']['uv']
                expected_normal = tuple(original['n']) if any(original['n']) else tuple(normal)
                expected_weights = sorted((bone,float(weight)) for bone,weight in original['w'] if weight > 0)
                if (tuple(round(x,5) for x in mesh['positions_mm'][vertex]) != tuple(round(x,5) for x in original['p']) or
                    sorted(map(tuple,mesh['weights'][vertex])) != expected_weights or
                    tuple(corner['normal']) != expected_normal or
                    tuple(corner['uv']) != ((ox+u*ow/256.)/aw,(oy+v*oh/256.)/ah)):
                    raise ValueError('original source corner/weight/normal/UV identity differs')
                corner['uv'] = [(nx+u*w/256.)/nw,(ny+v*h/256.)/nh]
            cursor += 1
    if cursor != len(mesh['triangles']):
        raise ValueError('source triangle coverage differs')
    # Restore only UVs in the copy: everything else must equal the sealed mesh.
    control = copy.deepcopy(mesh)
    for old, new in zip(form['mesh']['triangles'],control['triangles']):
        for a, b in zip(old['corners'],new['corners']):
            b['uv'] = a['uv']
    if control != form['mesh']:
        raise ValueError('a non-UV source field changed')
    return mesh, cursor


def generate(root, contract, output):
    forms, entries = load_forms(root, contract)
    if not output.resolve().is_relative_to(root.resolve()) or any(
            output.resolve().is_relative_to(form['path'].resolve()) for form in forms):
        raise ValueError('candidate output must stay in the private source set outside original inputs')
    atlas, tiles = plan_cells(forms)
    if output.exists():
        raise ValueError('new private output required; no existing candidate is overwritten')
    output.mkdir(parents=True)
    packer = pc.load_module('pack_coarse_actor', pc.PROTO/'tools/pack_coarse_actor.py')
    report = dict(schema='boss18-common-source-atlas-result-1', input_contract=contract,
                  atlas_size=list(atlas.size), tiles=[dict(key=list(key),cell=row['cell'],**row['evidence'])
                                                     for key,row in sorted(tiles.items())], forms=[])
    for form in forms:
        name = form['path'].name; dest = output/name; dest.mkdir()
        for file in ('source.json','source-bindings.json','manifest.json'):
            shutil.copy2(form['path']/file,dest/file)
            if sha(dest/file) != form['selection']['files'][file] or sha(form['path']/file) != form['selection']['files'][file]:
                raise ValueError('original source changed during copy')
        cells = {image:tiles[key]['cell'] for image,key in form['image_keys'].items()}
        mesh, count = relocate_mesh(form,entries,cells,atlas.size)
        (dest/'mesh.json').write_text(json.dumps(mesh),encoding='utf-8')
        atlas.save(dest/'atlas.png')
        validation = copy.deepcopy(form['validation'])
        validation['texture']['atlas'] = list(atlas.size)
        validation['texture']['cells'] = {str(image):value for image,value in cells.items()}
        validation['texture']['key'] = pc.texture_key(dest/'atlas.png')
        packer.pack(dest/'mesh.json',dest/'source.json',dest/'native','castmodel')
        pc.host_fixture(dest/'native',form['source'],ordered=True)
        native = json.loads((dest/'native/native-report.json').read_text())
        if native['triangles'] != count:
            raise ValueError('native source triangle count changed')
        validation['native'] = {key:value for key,value in native.items() if key != 'chunks'}
        validation['native']['chunks'] = [{key:value for key,value in chunk.items() if key != 'palette_weights'}
                                           for chunk in native['chunks']]
        proof = dict(scope='Lossless original atlas cell relocation only; no actual animated/look/runtime acceptance',
                     source_form=form['selection'],source_triangles=count,source_bones=len(form['source']['bones']),
                     original_non_UV_mesh_fields_exact=True,original_source_and_bindings_byte_identical=True,
                     original_oriented_corner_weights_normals_and_raw_material_UVs_exact=True,
                     atlas_sha256=sha(dest/'atlas.png'),native_checks='PENDING unchanged512KiB3poses/GXVERIFY/VQ/target admission')
        validation['shared_source_atlas'] = proof
        (dest/'validation.json').write_text(json.dumps(validation,indent=1)+'\n',encoding='utf-8')
        (dest/'shared-atlas-proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
        report['forms'].append(dict(name=name,**proof))
        print('Prepared original full source',name,count,'triangles,127owner; no reduction',flush=True)
    (output/'shared-atlas-proof.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Common original atlas',atlas.size,len(tiles),'tiles; native/fit/runtime checks remain separate',flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding='utf-8'))
    generate(args.source_root,contract,args.out)


if __name__ == '__main__':
    main()
