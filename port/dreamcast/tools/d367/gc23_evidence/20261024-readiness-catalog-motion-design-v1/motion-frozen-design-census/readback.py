"""Read-only frozen-source facts, not an implementation or test of Motion coverage."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/root/work/lanes/gc-catalog24')
OUT = Path(__file__).resolve().parent
HEAD = 'a132648e8199b50a5ac51cec4d339fe7dbc60135'
BASE = '1d63cffe3a232c402418f2f2d919e7abae476957'
P = 'port/dreamcast/game/'
PL = P + 'platform/'
I = PL + 'include/'
MARKERS = {
    I+'gc_asset_members.h': ['struct SourceUse', 'struct ReplayUse', 'struct SourceScope'],
    I+'gc_asset_actor.h': ['struct ActorSourceScope', 'struct ActorMainSourceScope', 'void accepted()'],
    I+'gc_asset_actor_select.inc': ['gcasset_actor_current_select', 're4dc_gcasset_actor_select', 're4dc_gcasset_actor_main_select'],
    I+'gc_asset_static_source.inc': ['struct GcStaticSourceScope'],
    PL+'gc_asset_members.cpp': ['void member_accept'],
    PL+'gc_asset_payloads.cpp': ['void payload_accept', 'bool payload_quads_accept'],
    PL+'gc_asset_gate.cpp': ['void unresolved', 'void emitted_checked', 'void end('],
    I+'gc_asset_gate.h': ['enum Consumer', 'constexpr unsigned Required'],
    PL+'native_actor_fast.cpp': ['struct SkinEntry', 'struct Frame', 'Frame* prepare_frame', 'void skin_position_matrix',
        're4dc_actor_skin_register(', 're4dc_actor_materialize(', 're4dc_actor_materialize_lazy(',
        'int re4dc_actor_submit(', 'void one_close(', 'Frame& one_frame(', 'int one_chunk_core(',
        'if(e.slots)gcasset_actor_scope.accepted();', 'unsigned re4dc_actor_submit_chunks('],
    I+'native_actor_owner_pool.inc': ['SkinEntry'],
    I+'native_actor_owner_runs.inc': ['int re4dc_actor_submit_owned_runs(', 'okay=one_chunk(*part,window)==1;', 're4dc_model_packet_abort();return -1;'],
    PL+'native_actor.cpp': ['struct Prepared', 'bool same_positions(', 're4dc_model_packet_commit(e.used);'],
    PL+'native_model.cpp': ['struct PreparedModelBatch', 're4dc_model_packet_commit(used);', 'void re4dc_model_submit(', 're4dc_model_packet_commit(b.used);'],
    PL+'native_ui.cpp': ['void gcasset_model_prepare(', 'void gcasset_model_accept(', 'struct DeferredPart',
        'void gcasset_flush()', 'void re4dc_model_packet_commit(', 'static void model_direct_account(',
        're4dc_leon_direct_switch(', 'int re4dc_ui_mv_send(', 'int re4dc_model_pt_begin(',
        'int re4dc_model_defer_part(', 'ReplayScope gcasset_replay_scope', 'void movie_draw()'],
    PL+'native_static.cpp': ['struct ImpostorQuad', 'void re4dc_static_flush_impostors()', 'int re4dc_static_submit(',
        'namespace dyn {', 'unsigned query(', 'struct ChunkPart', 'Queued emitters borrow its cull'],
    PL+'far_shell.inc': ['int re4dc_far_shell_draw(', 'const Vert* src = st.verts', 're4dc_model_direct_end(slots);'],
    PL+'native_ps2_world.cpp': ['class WorldDraw', 're4dc_model_packet_commit(used);'],
    P+'model_bridge.cpp': ['int re4dc_actor_model_prelit(', 'void flush(){', 'p.static_geometry=rigid', 'memcpy(p.modelview,mv'],
    P+'coarse_actor.cpp': ['int re4dc_coarse_leon(', 're4dc_actor_skin_register(', 're4dc_actor_submit_chunks('],
    P+'coarse_ganado.cpp': ['re4dc_actor_skin_register(', 're4dc_actor_submit(&p)'],
    P+'coarse_ganado_cast.cpp': ['re4dc_actor_skin_register(', 're4dc_actor_submit_chunks(', 're4dc_actor_submit(&p)'],
    P+'coarse_actor_transaction.inc': ['p.palettes(m,p,palettes)', 'r->part[order].mv,mv', 'RE4DC_ACTOR_SUBMIT_OWNED(', 'ice_result=re4dc_actor_submit_owned_runs'],
    P+'coarse_actor_owner_leon.inc': ['int owner_leon_palettes(', 'skin_jobs[u]={&parts[b]->mat', 'leon_hand_pick('],
    P+'coarse_actor_owner_ganado.inc': ['PSMTXInverse(m->pParts->mat', 'registry'],
    P+'coarse_actor_owner_pl08.inc': ['PSMTXInverse(m->pParts->mat'],
    P+'coarse_actor_owner_registry.inc': ['PSMTXInverse(m->pParts->mat', 'registry_jobs[u]={&registry_bound->parts[b]->mat'],
    P+'coarse_actor_leon_hands.inc': ['slot', 'skin'],
    P+'coarse_actor_atlas_split.inc': ['struct Cache', 'int re4dc_atlas_apply(', 'int re4dc_atlas_project('],
    P+'coarse_world.cpp': ['re4dc_model_pt_begin(', 're4dc_model_packet_commit(used);'],
    P+'mv_shadow.cpp': ['re4dc_ui_mv_send(g_buf', 'memcpy(M, &pG->Cam.v_mat'],
    P+'blob_shadow.cpp': ['root joint', 're4dc'],
    'src/game/trans.cpp': ['static void invisInfoModelview(', 'int re4dc_skin_defer(', 'int re4dc_skin_defer_lazy(', 'struct SkinLazyHead', 'static int skinDeferPending('],
    'src/game/motion.cpp': ['void MotionSetCore(', 'void MotionMoveCore(', 'void MotionGetSpeed(', 'void MotionGetPosition('],
    'src/game/cam_motion.cpp': ['CameraMotion::CameraMotion(', 'void CameraMotion::move()', 'param.pos = pos;', 'param.fovy ='],
    'src/game/camera.cpp': ['void CameraMove()', 'pG->Cam = CamCtrl.camera;', 'pG->Cam = *(Camera*) CamCtrl.m_pExtraCamera;'],
    P+'gc_asset_gate.mk': ['GC_ASSET_GATE ?= 0', 'GC_ASSET_GATE requires PVR_STREAM=1'],
}

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def check(texts):
    """Independent negative facts about the current source, NOT a future detector."""
    gate = texts[PL+'gc_asset_gate.cpp']
    members = texts[PL+'gc_asset_members.cpp']
    payloads = texts[PL+'gc_asset_payloads.cpp']
    actor = texts[PL+'native_actor_fast.cpp']
    ui = texts[PL+'native_ui.cpp']
    bridge = texts[P+'model_bridge.cpp']
    motion_guard = gate.find('if(consumer==Motion){unresolved(Motion,"motion-unwired");return;}', gate.index('void emitted_checked'))
    facts = {
        'Motion-currently-refuses-before-catalog': 0 <= motion_guard < gate.index('++emissions[consumer]', gate.index('void emitted_checked')),
        'member-mask-geometry-weapon-only': 'const unsigned allowed=(1U<<SourceGeometry)|(1U<<Weapon);' in members,
        'payload-mask-geometry-weapon-only': 'const unsigned allowed=(1U<<SourceGeometry)|(1U<<Weapon);' in payloads,
        'quad-batch-is-independent-early-return': 'if(re4dc_gcasset::payload_quads_accept(vertices,count))return;' in ui,
        'actual-perchunk-accept-before-window-close': 'if(e.slots)gcasset_actor_scope.accepted();' in actor,
        'actual-queue-replay-frozen-geometry-not-Motion': 'ReplayScope gcasset_replay_scope(deferred_first->asset_serial,deferred_first->asset_mask,deferred_first->asset_payload)' in ui,
        'prelit-hint-explicitly-null-motion-not-proof': 'return !m->pMotion && !info->pData->shapeOfs && !(info->be_flag&2);' in bridge,
        'actor-palette-consumes-current-bone-matrix': 'const float* P = f.palette + i * 12;' in actor,
    }
    if not all(facts.values()):
        raise AssertionError({k:v for k,v in facts.items() if not v})
    return facts

def main():
    observed_head = git('rev-parse', 'HEAD').decode().strip()
    subprocess.check_call(['git','-C',str(ROOT),'merge-base','--is-ancestor',HEAD,observed_head])
    assert not git('status', '--porcelain'), 'author source must stay frozen and clean'
    texts, pins = {}, []
    for path, markers in MARKERS.items():
        raw = (ROOT/path).read_bytes()
        assert raw == git('show', HEAD+':'+path), path
        text = raw.decode('utf-8')
        texts[path] = text
        anchors = {}
        for marker in markers:
            found = [n for n,line in enumerate(text.splitlines(),1) if marker in line]
            assert found, (path,marker)
            anchors[marker] = found
        before = git('show', BASE+':'+path)
        pins.append({'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                     'same_as_1d63':before==raw,'anchors':anchors})
    facts = check(texts)
    mutations = [
        (PL+'gc_asset_gate.cpp','if(consumer==Motion){unresolved(Motion,"motion-unwired");return;}','if(consumer==Motion){}'),
        (PL+'gc_asset_members.cpp','const unsigned allowed=(1U<<SourceGeometry)|(1U<<Weapon);','const unsigned allowed=0x3ff;'),
        (PL+'gc_asset_payloads.cpp','const unsigned allowed=(1U<<SourceGeometry)|(1U<<Weapon);','const unsigned allowed=0x3ff;'),
        (PL+'native_ui.cpp','if(re4dc_gcasset::payload_quads_accept(vertices,count))return;','/* removed quad path */'),
        (PL+'native_actor_fast.cpp','if(e.slots)gcasset_actor_scope.accepted();','/* last context only */'),
        (PL+'native_ui.cpp','ReplayScope gcasset_replay_scope(deferred_first->asset_serial,deferred_first->asset_mask,deferred_first->asset_payload)','ReplayScope gcasset_replay_scope(0,0,nullptr)'),
        (P+'model_bridge.cpp','return !m->pMotion && !info->pData->shapeOfs && !(info->be_flag&2);','return false;'),
        (PL+'native_actor_fast.cpp','const float* P = f.palette + i * 12;','const float* P = nullptr;'),
    ]
    defeated = []
    for path,old,new in mutations:
        altered = dict(texts);assert old in altered[path]
        altered[path] = altered[path].replace(old,new)
        try: check(altered)
        except AssertionError: defeated.append({'file':path,'changed_fact':old})
        else: raise AssertionError(('readback-control-did-not-detect-change',path,old))
    result = {'status':'READBACK_PASS_DESIGN_ONLY','source_head':HEAD,'comparison_base':BASE,
        'observed_tree_head':observed_head,'audited_files_match_frozen_source':True,
        'source_files':pins,'source_facts':facts,'readback_mutations_detected':defeated,
        'runtime_detector_implemented':False,'Motion_positive_receipt':False,
        'Motion_coverage':False,'new_runtime_allocation_bytes':0,
        'limits':'source reads and host string mutations only; no SDK/build/guest/assets/catalog IO',
        'warning':'Mutation controls validate recorded SOURCE FACTS, not the unimplemented detector.'}
    (OUT/'SOURCE-READBACK.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'files':len(pins),'facts':len(facts),'mutations_detected':len(defeated),'changed_from_1d63':[x['path'] for x in pins if not x['same_as_1d63']]}))

if __name__ == '__main__': main()
