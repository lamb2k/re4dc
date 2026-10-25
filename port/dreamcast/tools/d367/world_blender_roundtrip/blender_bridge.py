#!/usr/bin/env python3
"""Run inside pinned Blender: import/export an identity scene. No bpy dependency on host."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package as codec
import sidecars

PIN_VERSION = (4,4,3)
PIN_HASH = '802179c51ccc'
ROOT = 'R4IM.identity'
POINT_ATTRIBUTES = ('r4_qx','r4_qy','r4_qz','r4_qu','r4_qv','r4_argb1555','r4_vertex_id')


def js(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def check(ok, why):
    codec.require(ok, 'scene: '+why)


def exact(values, expected, why):
    check(len(values) == len(expected) and all(codec.float_bits(a) == codec.float_bits(b)
          for a,b in zip(values,expected)), why)


def scene_xyz(v):
    # Proper rotation (det+1), millimetres -> metres. Winding is unchanged.
    return tuple(codec.f32(x) for x in (v[0]/1000,-v[2]/1000,v[1]/1000))


def transform(v, place):
    if place is None:
        return v
    a = place[2:]
    return [sum(a[4*r+c]*v[c] for c in range(3))+a[4*r+3] for r in range(3)]


def position(doc, mi, vi, place):
    m,v = doc['meshes'][mi],doc['vertices'][vi]
    local = [m[8+a]+m[11+a]*v[a] for a in range(3)]
    return scene_xyz(transform(local,place))


def uv(doc, pi, vi):
    p,v = doc['parts'][pi],doc['vertices'][vi]
    return (codec.f32(p[8]+p[10]*v[3]), codec.f32(1-(p[9]+p[11]*v[4])))


def color(argb):
    return tuple(codec.f32(x) for x in ((argb>>10&31)/31,(argb>>5&31)/31,
                                       (argb&31)/31,1.0 if argb&0x8000 else 0.0))


def properties(obj, expected):
    check(set(obj.keys()) == set(expected), obj.name+' custom-property inventory')
    for k,v in expected.items():
        check(obj[k] == v, obj.name+' property '+k)


def meta(kind, record, extra=None):
    return dict(r4_kind=kind,r4_record=js(record),**(extra or {}))


def add_object(bpy, collection, name, data, props):
    ob = bpy.data.objects.new(name,data)
    collection.objects.link(ob)
    for k,v in props.items():
        ob[k] = v
    return ob


def mesh_data(bpy, name, coords, faces, edges=()):
    me = bpy.data.meshes.new(name)
    # No validate/triangulate/weld/decimate or modifier may repair the input.
    me.from_pydata(coords,list(edges),faces)
    me.update()
    return me


def identity_object(ob, collection, props, mesh=False, hidden=False):
    properties(ob,props)
    check(ob.type == ('MESH' if mesh else 'EMPTY') and ob.parent is None and
          not ob.modifiers and not ob.constraints and ob.animation_data is None,
          ob.name+' type/parent/modifier/constraint/animation')
    exact([x for r in ob.matrix_basis for x in r],
          [float(i//4 == i%4) for i in range(16)],ob.name+' object transform')
    check(list(ob.users_collection) == [collection], ob.name+' collection')
    check(ob.hide_render == hidden and ob.hide_viewport == hidden and not ob.hide_get(),
          ob.name+' visibility')
    if mesh:
        check(ob.data.shape_keys is None and ob.data.animation_data is None and
              ob.data.library is None and not ob.data.keys(),ob.name+' shape keys/animation/library/properties')


def material(bpy, pi, record):
    m = bpy.data.materials.new('material.%06d'%pi)
    m.diffuse_color=(0.8,0.8,0.8,1.0); m.metallic=0.0; m.roughness=0.5
    m.use_nodes = True
    m.node_tree.nodes.clear()
    vc = m.node_tree.nodes.new('ShaderNodeVertexColor'); vc.name='prelit'; vc.layer_name='prelit'
    em = m.node_tree.nodes.new('ShaderNodeEmission'); em.name='emission'
    em.inputs['Color'].default_value=(1,1,1,1); em.inputs['Strength'].default_value=1
    out = m.node_tree.nodes.new('ShaderNodeOutputMaterial'); out.name='output'
    m.node_tree.links.new(vc.outputs['Color'],em.inputs['Color'])
    m.node_tree.links.new(em.outputs[0],out.inputs['Surface'])
    for k,v in meta('material',record).items():
        m[k]=v
    return m


def rna_values(value):
    """Freeze editable scalar/vector settings; pointers are checked explicitly."""
    result={}
    for prop in value.bl_rna.properties:
        key=prop.identifier
        if prop.is_readonly or prop.type in ('POINTER','COLLECTION') or key in (
                'name','name_full','select','location','width','height'):
            continue
        item=getattr(value,key)
        if isinstance(item,(bool,int,float,str)):
            result[key]=item
        else:
            try:result[key]=list(item)
            except TypeError:continue
    return result


def material_signature(m):
    return dict(material=rna_values(m),nodes={n.name:dict(settings=rna_values(n),
        inputs={s.name:rna_values(s) for s in n.inputs},outputs={s.name:rna_values(s) for s in n.outputs})
        for n in m.node_tree.nodes})


def check_material(bpy,m, record):
    properties(m,meta('material',record))
    check(m.use_nodes and m.animation_data is None and m.library is None, m.name+' material state')
    exact(m.diffuse_color,[0.8,0.8,0.8,1.0],m.name+' display color')
    exact([m.metallic,m.roughness],[0.0,0.5],m.name+' display shading')
    check(not m.use_backface_culling,m.name+' culling preview')
    nodes = m.node_tree.nodes
    check({n.name:n.bl_idname for n in nodes} == {'prelit':'ShaderNodeVertexColor',
          'emission':'ShaderNodeEmission','output':'ShaderNodeOutputMaterial'},m.name+' node inventory')
    check(not any(n.mute for n in nodes) and nodes['prelit'].layer_name == 'prelit' and
          nodes['output'].is_active_output and nodes['output'].target == 'ALL',m.name+' node fields')
    check(sorted((l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name)
                 for l in m.node_tree.links) == [('emission','Emission','output','Surface'),
                 ('prelit','Color','emission','Color')],m.name+' links')
    exact(nodes['emission'].inputs['Color'].default_value,[1,1,1,1],m.name+' emission color')
    exact([nodes['emission'].inputs['Strength'].default_value],[1],m.name+' emission strength')
    exact(nodes['output'].inputs['Displacement'].default_value,[0,0,0],m.name+' displacement')
    check(m.node_tree.animation_data is None,m.name+' node animation')
    reference=material(bpy,0,record)
    try:
        check(material_signature(m)==material_signature(reference),m.name+' material/node/socket settings')
    finally:
        bpy.data.materials.remove(reference)


def draws(doc):
    own = codec.owners(doc)
    for ji in range(len(doc['meshlets'])):
        mi = own[ji][0]
        instances = [(i,p) for i,p in enumerate(doc['placements']) if p[0] == mi]
        # A source mesh without a placement still needs representation/validation.
        for index,place in instances or [(-1,None)]:
            name='draw.%06d.%06d'%(index+1,ji)
            yield name,ji,index,place,own[ji]


def draw_props(doc, ji, index, owner):
    return meta('draw',doc['meshlets'][ji],dict(r4_owner=js(owner),r4_placement=index,
        r4_commands=js(doc['commands'][ji])))


def placement_points(place):
    # Four explicit affine basis points preserve shear/reflection. Blender object
    # TRS decomposition cannot retain every source 3x4 matrix, so no such roundoff
    # is allowed to become an authoritative placement record.
    return [scene_xyz(transform(v,place)) for v in ((0,0,0),(1000,0,0),(0,1000,0),(0,0,1000))]


def build_scene(bpy,doc,files):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene; scene.name=ROOT
    scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1.0
    scene['r4_schema']=codec.SCHEMA; scene['r4_sources']=js(sidecars.hashes(files))
    scene['r4_aux']=js({k:doc[k] for k in ('palette','classes','rules','part_lods')})
    collection=bpy.data.collections.new(ROOT); scene.collection.children.link(collection)
    for table,kind in (('meshes','mesh'),('parts','part'),('clusters','cluster'),('levels','level')):
        for i,record in enumerate(doc[table]):
            add_object(bpy,collection,'%s.%06d'%(kind,i),None,meta(kind,record))
    mats=[material(bpy,i,r) for i,r in enumerate(doc['materials'])]
    for i,p in enumerate(doc['placements']):
        name='placement.%06d'%i
        me=mesh_data(bpy,name,placement_points(p),[],[(0,1),(0,2),(0,3)])
        ob=add_object(bpy,collection,name,me,meta('placement',p))
        ob.hide_render=True; ob.hide_viewport=True
    for name,ji,index,place,owner in draws(doc):
        mi,pi,ci,li,lod=owner
        ids=codec.local_vertices(doc,ji); faces=codec.triangles(doc,ji)
        me=mesh_data(bpy,name,[position(doc,mi,vi,place) for vi in ids],faces)
        ob=add_object(bpy,collection,name,me,draw_props(doc,ji,index,owner))
        ob.hide_render=bool(lod); ob.hide_viewport=bool(lod)
        me.materials.append(mats[pi])
        for ai,attr in enumerate(POINT_ATTRIBUTES):
            data=me.attributes.new(attr,'INT','POINT').data
            data.foreach_set('value',[vi if ai==6 else doc['vertices'][vi][ai] for vi in ids])
        me.uv_layers.new(name='uv'); me.color_attributes.new(name='prelit',type='FLOAT_COLOR',domain='CORNER')
        # Adding an attribute can invalidate RNA references to another layer.
        layer=me.uv_layers['uv']; cols=me.color_attributes['prelit']
        for loop in me.loops:
            vi=ids[loop.vertex_index]
            layer.data[loop.index].uv=uv(doc,pi,vi)
            cols.data[loop.index].color=color(doc['vertices'][vi][5])
    return scene


def validate_scene(bpy,doc,files):
    scene=bpy.context.scene
    check(len(bpy.data.scenes)==1 and scene.name==ROOT,'scene inventory')
    properties(scene,dict(r4_schema=codec.SCHEMA,r4_sources=js(sidecars.hashes(files)),
        r4_aux=js({k:doc[k] for k in ('palette','classes','rules','part_lods')})))
    check(scene.unit_settings.system=='METRIC' and scene.unit_settings.scale_length==1.0,'units')
    check(len(bpy.data.collections)==1 and list(scene.collection.objects)==[],'collection inventory')
    collection=bpy.data.collections.get(ROOT)
    check(collection is not None and list(scene.collection.children)==[collection] and
          not collection.hide_render and not collection.hide_viewport,'root collection')
    check(not bpy.data.images and not bpy.data.node_groups and not bpy.data.actions,'image/node-group/action additions')
    expected=set(); mesh_names=set(); out=codec.clone(doc)
    for table,kind in (('meshes','mesh'),('parts','part'),('clusters','cluster'),('levels','level')):
        for i,record in enumerate(doc[table]):
            name='%s.%06d'%(kind,i); expected.add(name)
            ob=bpy.data.objects.get(name); check(ob is not None,'missing '+name)
            identity_object(ob,collection,meta(kind,record))
            out[table][i]=json.loads(ob['r4_record'])
    check({m.name for m in bpy.data.materials} == {'material.%06d'%i for i in range(len(doc['materials']))},'material inventory')
    for i,r in enumerate(doc['materials']):
        m=bpy.data.materials['material.%06d'%i]; check_material(bpy,m,r)
        out['materials'][i]=json.loads(m['r4_record'])
    for i,p in enumerate(doc['placements']):
        name='placement.%06d'%i; expected.add(name); mesh_names.add(name)
        ob=bpy.data.objects.get(name); check(ob is not None,'missing '+name)
        identity_object(ob,collection,meta('placement',p),True,True)
        me=ob.data; check(me.name==name and len(me.vertices)==4 and not me.polygons and
            len(me.edges)==3 and not me.materials and not me.uv_layers and not me.color_attributes,name+' basis topology')
        check(set(a.name for a in me.attributes if not a.is_internal)<={'position','sharp_face'},name+' basis attributes')
        check([list(e.vertices) for e in me.edges]==[[0,1],[0,2],[0,3]],name+' basis edges')
        for v,want in zip(me.vertices,placement_points(p)):
            exact(v.co,want,name+' affine basis')
        out['placements'][i]=json.loads(ob['r4_record'])
    vertices={}
    for name,ji,index,place,owner in draws(doc):
        expected.add(name); mesh_names.add(name)
        mi,pi,ci,li,lod=owner
        ob=bpy.data.objects.get(name); check(ob is not None,'missing '+name)
        identity_object(ob,collection,draw_props(doc,ji,index,owner),True,bool(lod))
        me=ob.data; ids=codec.local_vertices(doc,ji); faces=codec.triangles(doc,ji)
        check(me.name==name and len(me.vertices)==len(ids) and len(me.polygons)==len(faces) and
              len(me.loops)==3*len(faces),name+' topology counts')
        check(list(me.materials)==[bpy.data.materials['material.%06d'%pi]],name+' material assignment')
        check([u.name for u in me.uv_layers]==['uv'] and
              [(c.name,c.data_type,c.domain) for c in me.color_attributes]==[('prelit','FLOAT_COLOR','CORNER')],name+' UV/color layers')
        check(set(a.name for a in me.attributes if not a.is_internal) ==
              set(POINT_ATTRIBUTES)|{'uv','prelit','position','sharp_face'},name+' attribute inventory')
        check(not me.has_custom_normals,name+' custom normals')
        for attr in POINT_ATTRIBUTES:
            check(me.attributes[attr].data_type=='INT' and me.attributes[attr].domain=='POINT',name+' quantization attribute type')
        edge_set=set()
        for poly,face in zip(me.polygons,faces):
            check(list(poly.vertices)==face and poly.material_index==0 and not poly.use_smooth,
                  name+' triangle winding/order/material/smoothing')
            edge_set.update(tuple(sorted((face[k],face[(k+1)%3]))) for k in range(3)
                            if face[k] != face[(k+1)%3])
        check({tuple(sorted(e.vertices)) for e in me.edges} == edge_set and len(me.edges)==len(edge_set),name+' edges')
        for local,vi in enumerate(ids):
            q=[me.attributes[a].data[local].value for a in POINT_ATTRIBUTES]
            check(q == doc['vertices'][vi]+[vi],name+' raw quantization/source vertex')
            exact(me.vertices[local].co,position(doc,mi,vi,place),name+' position')
            if vi in vertices:
                check(vertices[vi]==q[:6],name+' shared pool disagreement')
            vertices[vi]=q[:6]
        for loop in me.loops:
            vi=ids[loop.vertex_index]
            exact(me.uv_layers['uv'].data[loop.index].uv,uv(doc,pi,vi),name+' UV')
            exact(me.color_attributes['prelit'].data[loop.index].color,color(doc['vertices'][vi][5]),name+' prelit color')
        out['meshlets'][ji]=json.loads(ob['r4_record'])
        out['commands'][ji]=json.loads(ob['r4_commands'])
    check(set(bpy.data.objects.keys())==expected,'object additions/deletions/renames')
    check(set(bpy.data.meshes.keys())==mesh_names,'mesh additions/deletions/renames')
    check(set(vertices)==set(range(len(doc['vertices']))),'source pool coverage')
    out['vertices']=[vertices[i] for i in range(len(vertices))]
    out.update(json.loads(scene['r4_aux']))
    return out


def load_bundle(folder):
    files=sidecars.inventory(folder)
    doc=codec.decode(files['ps2-world.re4mesh'],files['ps2-world.r4pw'])
    sidecars.rebuild(files,doc,codec.serialize_mesh(doc),codec.serialize_policy(doc))
    return doc,files


def main():
    import bpy
    check(bpy.app.version==PIN_VERSION and bpy.app.build_hash.decode()==PIN_HASH,'requires Blender4.4.3 hash802179c51ccc')
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=('import','export'))
    ap.add_argument('--source',required=True,type=Path)
    ap.add_argument('--blend',required=True,type=Path)
    ap.add_argument('--out',type=Path)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    doc,files=load_bundle(args.source)
    if args.action=='import':
        check(not args.blend.exists(),'refuse to overwrite blend')
        build_scene(bpy,doc,files)
        validate_scene(bpy,doc,files)
        args.blend.parent.mkdir(parents=True,exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend),check_existing=False)
    else:
        check(args.out is not None and not args.out.exists(),'new output directory required')
        bpy.ops.wm.open_mainfile(filepath=str(args.blend),load_ui=False,use_scripts=False)
        rebuilt=validate_scene(bpy,doc,files)
        result=sidecars.rebuild(files,rebuilt,codec.serialize_mesh(rebuilt),codec.serialize_policy(rebuilt))
        # Validation is complete before creating any destination. Write to a
        # sibling staging directory and publish it with one rename.
        import tempfile,shutil
        args.out.parent.mkdir(parents=True,exist_ok=True)
        staging=Path(tempfile.mkdtemp(prefix=args.out.name+'.tmp-',dir=args.out.parent))
        try:
            for name,blob in result.items():
                (staging/name).write_bytes(blob)
            staging.rename(args.out)
        finally:
            if staging.exists(): shutil.rmtree(staging)
    print('BUILD11_IDENTITY_OK '+args.action+' '+js(sidecars.hashes(files)))


if __name__=='__main__':
    main()
