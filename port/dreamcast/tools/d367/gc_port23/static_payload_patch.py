"""Prepare the narrow shared-file patch; never edits native_static.cpp itself."""
from pathlib import Path
import difflib

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[2] / 'game/platform/native_static.cpp'


def patched(source):
    def once(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('static bridge source drift: '+old[:90])
        source = source.replace(old, new, 1)

    once('#include "../world_scratch.h"', '''#include "../world_scratch.h"
#include "include/gc_asset_payloads.h"
#if RE4DC_GC_ASSET_GATE
#define RE4DC_GCAP_FIELD re4dc_gcasset::PayloadProof asset_proof;
#define RE4DC_GCAP_RETIRE(v) re4dc_gcasset::payload_retire((v).asset_proof)
#define RE4DC_GCAP_CAPTURE(v,b,n,l,s) do{if(re4dc_gcasset::ensure_disc_catalog()) \\
    (void)re4dc_gcasset::payload_capture((v).asset_proof,&(v),b,n,l,s); \\
    else re4dc_gcasset::payload_retire((v).asset_proof);}while(0)
#define RE4DC_GCAP_SCOPE(v,m,i) re4dc_gcasset::PayloadScope gcasset_payload_scope((v).asset_proof,&(v),m,i)
#else
#define RE4DC_GCAP_FIELD
#define RE4DC_GCAP_RETIRE(...) ((void)0)
#define RE4DC_GCAP_CAPTURE(...) ((void)0)
#define RE4DC_GCAP_SCOPE(...) ((void)0)
#endif''')
    for name in ('View', 'MeshView', 'Ps2World'):
        once('struct '+name+' {', 'struct '+name+' {\n    RE4DC_GCAP_FIELD')
    for name in ('View', 'MeshView'):
        once('void retire('+name+'& v){', 'void retire('+name+'& v){\n    RE4DC_GCAP_RETIRE(v);')
    once('    v.storage=storage;\n    if(!v.package.adopt(storage,size)',
         '    RE4DC_GCAP_CAPTURE(v,storage,size,nullptr,0);\n    v.storage=storage;\n    if(!v.package.adopt(storage,size)')
    once('        re4dc_static_free(storage);v.storage=nullptr;v.bytes=0;v.package.close();',
         '        RE4DC_GCAP_RETIRE(v);\n        re4dc_static_free(storage);v.storage=nullptr;v.bytes=0;v.package.close();')
    once('#if RE4DC_SCENERY_ENCODING\n    if(!re4dc::room::adopt_by_encoding',
         '    RE4DC_GCAP_CAPTURE(v,storage,size,nullptr,0);\n#if RE4DC_SCENERY_ENCODING\n    if(!re4dc::room::adopt_by_encoding')
    once('        re4dc_log("native mesh: %s rejected: %s\\n",path,v.package.error());\n        re4dc_static_free(storage);',
         '        re4dc_log("native mesh: %s rejected: %s\\n",path,v.package.error());\n        RE4DC_GCAP_RETIRE(v);\n        re4dc_static_free(storage);')
    once('    if(!v.package.valid() || e->mesh>=v.package.header().mesh_count){++stats.stale_bindings;return 0;}\n    const auto& mesh=',
         '    if(!v.package.valid() || e->mesh>=v.package.header().mesh_count){++stats.stale_bindings;return 0;}\n    RE4DC_GCAP_SCOPE(v,p.model,p.info);\n    const auto& mesh=')
    once('struct ImpostorQuad { const re4dc::room::MeshImpostor* record;',
         '''struct ImpostorQuad {
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::PayloadQuadUse asset_use{};
#endif
    const re4dc::room::MeshImpostor* record;''')
    old='    q.record=r;q.cell=std::uint16_t(cell);q.fog=p.source_key[2]?1:0;q.argb=impostor_color(v,mesh,*r);'
    if source.count(old)!=2:
        raise ValueError('Expected two exact impostor/tree-quad owner capture sites')
    source=source.replace(old,old+'''
#if RE4DC_GC_ASSET_GATE
    q.asset_use={&v.asset_proof,v.asset_proof.serial,re4dc_gcasset::source_use.mask?re4dc_gcasset::source_use.mask:1U<<re4dc_gcasset::SourceGeometry};
#endif''')
    once('        auto* out=static_cast<pvr_vertex_t*>(packet.vertices);unsigned used=0;',
         '''        auto* out=static_cast<pvr_vertex_t*>(packet.vertices);unsigned used=0;
#if RE4DC_GC_ASSET_GATE
        re4dc_gcasset::PayloadQuadUse asset_uses[kImpostorQuads];unsigned asset_count=0;
#endif''')
    once('            used+=4;\n        }\n        if(bound){re4dc_model_packet_commit(used);++impostor_stats[3];}',
         '''            used+=4;
#if RE4DC_GC_ASSET_GATE
            asset_uses[asset_count++]=q.asset_use;
#endif
        }
        if(bound){
#if RE4DC_GC_ASSET_GATE
            const re4dc_gcasset::PayloadQuadBatch asset_batch{asset_uses,asset_count,packet.vertices,used};
            re4dc_gcasset::PayloadQuadScope asset_scope(asset_batch);
#endif
            re4dc_model_packet_commit(used);++impostor_stats[3];}''')
    once('    Binding& b=*at.binding;View& v=*at.view;',
         '    Binding& b=*at.binding;View& v=*at.view;\n    RE4DC_GCAP_SCOPE(v,p.model,p.info);')
    once('    if(ok && !ps2w.package.adopt(s,msize,true,true))',
         '    if(ok){RE4DC_GCAP_CAPTURE(ps2w,s,msize,s+mbytes,psize);}\n    if(ok && !ps2w.package.adopt(s,msize,true,true))')
    once('        ps2w.package.close();if(s)re4dc_static_free(s);',
         '        RE4DC_GCAP_RETIRE(ps2w);\n        ps2w.package.close();if(s)re4dc_static_free(s);')
    once('int ps2_pass(unsigned pass,float zfar){',
         'int ps2_pass(unsigned pass,float zfar){\n    RE4DC_GCAP_SCOPE(ps2w,nullptr,nullptr);')
    # These are two distinct pre-overwrite/free boundaries. Room/movie loan
    # guards stay ahead of the successful retirement, as in the source owner.
    once('    ps2w.package.close();ps2w.parts=nullptr;',
         '    RE4DC_GCAP_RETIRE(ps2w);\n    ps2w.package.close();ps2w.parts=nullptr;')
    once('    ps2w.package.close();\n    if(ps2w.storage)re4dc_static_free(ps2w.storage);',
         '    RE4DC_GCAP_RETIRE(ps2w);\n    ps2w.package.close();\n    if(ps2w.storage)re4dc_static_free(ps2w.storage);')
    once('    if(!ps2w.package.adopt(data,files.mesh,true,true))return false;',
         '''    RE4DC_GCAP_CAPTURE(ps2w,data,files.mesh,data+mb,files.side);
#if RE4DC_GC_ASSET_GATE
    struct GcAssetReloadProof {
        bool committed=false;
        ~GcAssetReloadProof(){if(!committed)RE4DC_GCAP_RETIRE(ps2w);}
    } asset_reload;
#endif
    if(!ps2w.package.adopt(data,files.mesh,true,true))return false;''')
    # Cover every post-capture refusal with one local diagnostic cleanup guard.
    # Revoke before the very first overwrite, including failed/partial reads.
    start=source.index('bool ps2_movie_reload(){')
    end=source.index('bool ps2_movie_dyn_valid(){',start)
    reload=source[start:end]
    if reload.count('    Re4dcIoScope io;')!=1 or not reload.endswith('    return true;\n}\n'):
        raise ValueError('movie reload cleanup boundary changed')
    reload=reload.replace('    Re4dcIoScope io;', '    RE4DC_GCAP_RETIRE(ps2w);\n    Re4dcIoScope io;',1)
    reload=reload[:-len('    return true;\n}\n')]+'''#if RE4DC_GC_ASSET_GATE
    asset_reload.committed=true;
#endif
    return true;
}
'''
    source=source[:start]+reload+source[end:]
    return source


def patch(source):
    return ''.join(difflib.unified_diff(source.splitlines(True), patched(source).splitlines(True),
        fromfile='a/port/dreamcast/game/platform/native_static.cpp',
        tofile='b/port/dreamcast/game/platform/native_static.cpp'))


if __name__ == '__main__':
    destination = HERE / 'static-payload-hooks.patch'
    destination.write_text(patch(SOURCE.read_text()))
    print(destination)
