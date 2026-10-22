#!/usr/bin/env python3
"""Prepare an immutable atlas target activation plan; never build, stage or run."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess

ATLAS_RUNTIME='e345473b905e3b2a9a353988996303cfca211b85'
ATLAS_GUARD='0690cc6eda4372efae36d65da5e27445f692312a'
INTEGRATION='892c10ddeadcfcc0bb55bcf53c9b4ac25fd035e8'
RETAINED='6f9d31b0e00497a75fdd7e25bb04f92305103087'
KEYS={'3662c0aa-c9e71c00':'53d54083dbcb1f00570e531bc01f26625aee8c22bb53267baea0d38a01f3553f',
      'fefdf580-f15c1f47':'f57bf6b0990d086c2a158047e382734f5ca275fb949b6067ba2f6172d81e33a7'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity(p):return dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=sha(p))
def dump(p,row):p.write_text(json.dumps(row,indent=2)+'\n')
def seal(root):
    p=root/'SHA256SUMS'
    p.write_text(''.join(sha(f)+'  '+f.relative_to(root).as_posix()+'\n' for f in sorted(root.rglob('*')) if f.is_file()))
def verify(root,expected):
    if sha(root/'SHA256SUMS')!=expected:raise ValueError('seal changed: '+str(root))
    for line in (root/'SHA256SUMS').read_text().splitlines():
        digest,name=line.split('  ',1)
        if sha(root/name)!=digest:raise ValueError('sealed file changed: '+str(root/name))
def git_blob(repo,ref,name):return subprocess.check_output(['git','show',ref+':'+name],cwd=repo)
def knobs(p):return dict(line.split('=',1) for line in p.read_text().splitlines() if '=' in line and not line.startswith('#'))
def hand_cases(consumer):
    data=(consumer/'inputs/leon_hands_pl00.re4hp').read_bytes();h=struct.unpack_from('<8I',data)
    rows=[struct.unpack_from('<BB3HI',data,32+i*12) for i in range(h[1]>>16)]
    bo=32+len(rows)*12;nb=h[2]&65535
    blobs=[struct.unpack_from('<BB11H',data,bo+i*24) for i in range(nb)]
    sources=[struct.unpack_from('<BBH',data,bo+nb*24+i*4) for i in range(h[2]>>16)]
    result=[]
    for i,b in enumerate(blobs):
        refs=[]
        for wep,arc,blob in sources:
            if blob==i:refs.append(dict(archive='pl0e' if wep==0x8e else 'pl0f' if wep==0x8f else f'wep{wep:02d}',archive_number=wep,arc=arc))
        keys=[dict(positions=r[2],normals=r[3],palette=r[4],vertex_hash=r[5]) for r in rows if r[1]==i]
        at=b[12]*32;parts={}
        for name,n in zip(('positions','normals','uv','stream','weights'),b[6:11]):
            blob=data[at:at+n];parts[name]=dict(bytes=n,sha256=hashlib.sha256(blob).hexdigest());at+=(n+31)&~31
        player_selector=(dict(arc=0x12,callback='cPlLeon::setRightHand(0)') if b[0]==5 and b[1]&2 else dict(arc=0x14,callback='cPlLeon::setLeftHand(0)') if b[0]==6 and b[1]&2 else dict(arc=0x16,callback='cPlLeon::setLeftHand(2)') if b[0]==6 and b[1]&4 else None)
        result.append(dict(blob=i,player_selector_from_pack_flags=player_selector,source_role=b[0],side='right' if b[0]==5 else 'left',flags=b[1],
            flag_meaning=[name for bit,name in ((1,'standard'),(2,'home'),(4,'alternate_hint')) if b[1]&bit],
            triangles=b[5],runtime_keys=keys,archive_selectors=refs,arrays=parts))
    if len(result)!=17 or len(sources)!=45:raise ValueError('selected hand directory changed')
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('repo','private-root','qa-root','rectangle-receipt','out'):ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists():raise ValueError('preserve existing activation plan')
    runtime=a.private_root/'runtime-v2';consumer=a.private_root/'consumers-v2'
    verify(runtime,'848305324671eea4497a759bfd3c5f0d355bc463df984d630b6504bc7638e6fc')
    verify(consumer,'6adc079fb9b5559f749acf272443b26ce63154c5e0ff322f14f846cd8513e9c6')
    for key,digest in KEYS.items():
        if sha(runtime/'tex'/(key+'.re4tex'))!=digest:raise ValueError('atlas texture changed')
    shared=('coarse_actor_geometry_once.inc','coarse_actor_owner_registry.inc','native_model_registry.mk','ps2leon.mk','coarse_actor_owner_leon.inc','coarse_actor_owner_pl08.inc')
    source=[]
    for name in shared:
        path='port/dreamcast/game/'+name
        old=git_blob(a.repo,INTEGRATION,path);pre=git_blob(a.repo,'fbb93da64',path)
        if old!=pre:raise ValueError('integration892 prerequisite source changed: '+name)
        source.append(dict(path=path,integration892_sha256=hashlib.sha256(old).hexdigest(),pre_hook_exact=True))
    rect=json.loads(a.rectangle_receipt.read_text());rect_keys=[r['scoped_key'] for r in rect['selected']]
    if len(rect_keys)!=17 or len(set(rect_keys))!=17 or set(rect_keys)&set(KEYS):raise ValueError('rectangle namespace collision')
    if not set(KEYS)<=set(rect['reserved_atlas_keys']):raise ValueError('rectangle omitted atlas reservations')
    controls={};candidate_data={}
    for name in ('default-off','qa-control','combined'):
        d=a.qa_root/'builds'/name;r=json.loads((d/'receipt.json').read_text())
        if r['source']!=RETAINED:raise ValueError('retained control source changed')
        files={}
        for file,row in r['files'].items():
            p=d/file
            if sha(p)!=row['sha256'] or p.stat().st_size!=row['bytes']:raise ValueError('control artifact changed: '+str(p))
            files[file]=identity(p)
        if len([n for n in files if n.endswith('.ovl')])!=14:raise ValueError('control overlay count')
        if sha(d/'candidate.txt')!=r['candidate_sha256'] or sha(d/'resolved-knobs.txt')!=r['resolved_sha256']:raise ValueError('recipe changed')
        if sha(d/'re4dc-game.elf')!=r['elf_sha256']:raise ValueError('retained ELF changed')
        controls[name]=dict(source=RETAINED,receipt=identity(d/'receipt.json'),candidate=identity(d/'candidate.txt'),
            resolved=identity(d/'resolved-knobs.txt'),elf=identity(d/'re4dc-game.elf'),files=files)
        candidate_data[name]=knobs(d/'resolved-knobs.txt')
    selected=candidate_data['combined']
    for name,value in dict(PS2_LEON='1',ACTOR_PL08='1',ACTOR_PL08_PACK='1',LEON_LOD='0',LEON_HAND_PACK='1',LEON_HEADLESS='1',GAME_SH4ZAM='1',SKIN_SH4ZAM='0',PAUSE_NATIVE_PRESENTATION='1',QA_MENU='1').items():
        if selected.get(name)!=value:raise ValueError('selected recipe mismatch: '+name)
    if selected.get('SS_WINDOW_HOLD_RESTORE','0')!='0':raise ValueError('negative window candidate must stay off')
    hair=Path(selected['PS2_LEON_DIR'])/'ps2leon_hair_runs.h';text=hair.read_text()
    hair_count=int(re.search(r'run_count=(\d+)',text).group(1));mask=int(re.search(r'material_mask=(\d+)',text).group(1))
    if (hair_count,mask)!=(1,2):raise ValueError('actual recipe hair shape changed')
    cases=[dict(case='standard',appearance=0x100,role=1,roles=8,original_runs=7+hair_count,new_runs=15+hair_count,materials=3,source_triangles=905,isolated_triangles=43,new_geometry_ids=[127,135],hand_roles={'right':5,'left':6},entry='Fresh normal New Game or approved cold QA start; verify actual appearance.'),
           dict(case='pl08',appearance=0x108,role=0,roles=9,original_runs=8+hair_count,new_runs=20+hair_count,materials=3,source_triangles=2890,isolated_triangles=278,new_geometry_ids=[136,148],hand_roles={'right':5,'left':6},entry='Fresh approved cold pl08 fixture/natural costume owner; do not restore a different-program state.'),
           dict(case='headless-pl08',appearance=0x109,role=0,roles=7,original_runs=7,new_runs=19,materials=2,source_triangles=2890,isolated_triangles=278,new_geometry_ids=[136,148],hand_roles={'right':4,'left':5},neck_triangles=37,entry='Original fatal head-loss outcome in its own candidate lineage. Preserve damage/death and normal Continue.'),
           dict(case='flying-head',appearance=0x10a,roles=1,original_runs=2,new_runs=2,materials=2,new_geometry_ids=[],isolated_triangles=0,entry='Original flying object from the same authentic head-loss event; face1045/hair682 stay unchanged.')]
    hands=hand_cases(consumer);dynamic=[]
    for c in cases[:3]:
        for h in hands:dynamic.append(dict(case=c['case']+'-hand-'+str(h['blob']),appearance=c['appearance'],blob=h['blob'],side=h['side'],current_role=c['hand_roles'][h['side']],source_immutable_id=h['source_role']+1,body_geometry_ids=c['new_geometry_ids'],expected_plan_runs=c['new_runs'],target_status='NOT_RUN',target_reachability='UNVERIFIED: validate natural source selector before target execution; headless uses only naturally selected fatal-pose hands, with no post-death equip.',host_source_gate='17 exact original blobs per appearance already passed',trigger='Use normal equip/action only when its exact source selector is available; bind actual current slot/signature after asynchronous read lands. No synthetic hand/state writes.'))
    namespace=dict(integration_source=INTEGRATION,actual_preprocessed_tu=identity(Path('/root/probe/texture-atlas21-checks/object-v2-stack/on/coarse_actor.ii')),actual_compile_inputs=identity(a.private_root/'runtime-receipts-v1/object/on/compile-inputs.json'),source_byte_checks=source,actual_qa_flags=dict((k,selected[k]) for k in ('ACTOR_PL08','ACTOR_PL08_PACK','LEON_HEADLESS','LEON_HAND_PACK','NATIVE_MODEL_REGISTRY','ACTOR_GANADO_PS2_STUMP')),
        actual_generated_hair_header=identity(hair),registry_geometry=64,registry_ids=[56,119],pl08_source_ids=[120,122],neck_id=123,flying_head_ids=[124,126],new_standard_ids=[127,135],new_pl08_headless_ids=[136,148],new_table_count=148,
        provenance='Current QA object-v2-stack preprocessed TU + exact integration892 source equality; numeric ranges require recomputation for any changed registry/hand configuration.',texture_keys=KEYS,rectangle_keys=rect_keys,rectangle_receipt=identity(a.rectangle_receipt),disjoint=True)
    plan=dict(generator=identity(Path(__file__)),source_hand_callbacks=identity(a.repo/'src/game/pl_leon.cpp'),schema='re4dc-atlas-target-plan-1',execution='PLAN_ONLY: no build, stage, guest, source state mutation or release',runtime_source=ATLAS_RUNTIME,make_guard_source=ATLAS_GUARD,final_combined_source=None,
        required_freeze='Root must select and record the exact combined source before activation. If any other component changes, rebuild matching OFF first; archival controls are not substitutes for a new frozen baseline.',
        runtime_assets=dict(header=identity(runtime/'leon_atlas_split_data.h'),textures=[identity(runtime/'tex'/(k+'.re4tex')) for k in KEYS],runtime_seal=identity(runtime/'SHA256SUMS'),hand_package=identity(consumer/'inputs/leon_hands_pl00.re4hp'),neck_header=identity(consumer/'inputs/ps2leon_neck.h'),player_archives=[identity(consumer/'inputs'/n) for n in ('pl00.drs','pl08.drs')]),
        retained_controls=controls,namespace=namespace,appearance_cases=cases,hand_blobs=hands,dynamic_cases=dynamic,
        activation=dict(atlas_only_off=['LEON_ATLAS_SPLIT=0'],atlas_only_on=['LEON_ATLAS_SPLIT=1','LEON_ATLAS_SPLIT_DIR='+str(runtime)],other_knobs='Preserve the exact frozen control recipe, including GAME_SH4ZAM1/SKIN_SH4ZAM0 and SS_WINDOW_HOLD_RESTORE0. No production recipe edit.',texture_pack='Append the two atlas keys without replacing original atlas/normal members. Rectangle17+atlas2 must be disjoint; consumers need their separate reviewed replacement allowlist.',off_equality='Before any ON run, complete new-source OFF raw program and all14 overlays must equal the same frozen control, with exact loadable ELF bytes and unchanged relevant assets. A changed other component requires its own paired control.',states='Cold boot every changed program. Continue only exact same-program unedited owned state lineage; never restore QA, castle or benchmark states from a different program.',screenshots='Every meaningful target checkpoint/failure: PNG plus source commit, raw/ELF/overlay/assets, room/source-frame interval, action, health and outcome. No target acceptance yet.'),
        minimum_gates=dict(disk_preflight_bytes=18*1024**3+128*1024**2,disk_runtime_bytes=18*1024**3+64*1024**2,current_source_output_limit_bytes=10*1024**2,full_build='ROOT_DISK_RESERVATION_REQUIRED; no full-image execution in this plan',guest='Owned PID, actual lifetime <=50s; use qualified47.5s outer/41s inner supervisor, global16/per-lane2 subject to current host capacity.',
            image_memory='Report exact final text/rodata/data/BSS/arena/CHAR_DATA_BLOCK rounding and heap4 free/largest. Current object-only delta46734 text+rodata/3808 BSS is not final linked fit.',stack='Bind actual executing thread stack bounds; audit real simultaneous caller chain using fresh SH4 .su/disassembly, including factory3936, atlas_capability1772, project1844, bind1848, source_layout116 as applicable, never add mutually exclusive phases. Prove high-water/canary headroom on target. No existing cumulative stack acceptance.',
            kos='Pass existing48KiB squeeze fight/call/leave/door/s30 checks at the frozen recipe; no new allocation/owner/texture refusal. Existing Continue3840/7936 headroom and fragmentation remain OPEN.',vram='Original atlas remains used; each tile7510 payload/7520 rounded, file7654. Capture pinned/dynamic/free/largest, zero refusal/no-contiguous failure, actual reload/read traffic after preload; no byte-count FPS inference.',
            lifecycle=['ordinary inventory/examine return','OPTIONS return/move','movie natural EOF/skip and radio','death/headless/flying head/Continue','pl08 unpublish/re-publish including same address','room leave/reset/New Game'],
            strict='Required source decisions/geometry/order/skin material state equal on matched scenes; exact cold/body UV proof does not replace complete logic/target checks.',look_and_timing='Actual matched scene/camera/frame windows, material lease/key/plan counts and before/after screenshots; Flycast and model costs labelled separately from physical Dreamcast.'),
        target_acceptance=False,physical_dreamcast_acceptance=False)
    a.out.mkdir(parents=True)
    for name in controls:
        dest=a.out/'recipe-inputs'/name;dest.mkdir(parents=True)
        for file in ('candidate.txt','resolved-knobs.txt','receipt.json'):shutil.copy2(a.qa_root/'builds'/name/file,dest/file)
    dump(a.out/'activation-manifest.json',plan)
    dump(a.out/'geometry-and-key-reservations.json',namespace)
    for arm in ('off','on'):(a.out/('atlas-'+arm+'-overlay.txt')).write_text('\n'.join(plan['activation']['atlas_only_'+arm])+'\n')
    rows=['# Atlas target activation plan','', 'Plan only; no target build/stage/guest has run.','', '| Case | Appearance | Body role | Actual current recipe runs OFF -> ON | Materials ON |', '|---|---:|---:|---:|---:|']
    for c in cases:rows.append('| '+c['case']+' | '+hex(c['appearance'])+' | '+str(c.get('role','unchanged'))+' | '+str(c['original_runs'])+' -> '+str(c['new_runs'])+' | '+str(c['materials'])+' |')
    rows+=['','These current PS2_LEON1 counts use the pinned one-run hair header. The earlier','17/22 source tests reserve two hair runs conservatively; headless remains19.','All51 host hand combinations pass; natural target reachability remains unverified.',
                'Their exact17 blobs/source selectors and runtime keys are recorded; headless','hands must arise from the fatal pose; no post-death equip is proposed.','', 'The historical combined control is rawce080eb290/ELF0d6dcf6f at source6f9d31b0e.','A changed atlas program needs its own cold lineage and symbols. Root must freeze','the complete combined source and an exact matching OFF control before activation.','', 'Full program/overlay, final link/squeeze/stack, actual material/texture leases,','lifecycle/read/VRAM, look screenshots, matched timing and physical-console gates','remain open. No production recipe, release, SD or third-party action is proposed.']
    (a.out/'ACTIVATION.md').write_text('\n'.join(rows)+'\n')
    seal(a.out)
    print(json.dumps(dict(appearance_cases=len(cases),dynamic_hand_cases=len(dynamic),actual_enabled_runs=[c['new_runs'] for c in cases[:3]],rectangle_keys=17,texture_namespace_disjoint=True,manifest_sha256=sha(a.out/'activation-manifest.json'),seal_sha256=sha(a.out/'SHA256SUMS'),bytes=sum(p.stat().st_size for p in a.out.rglob('*') if p.is_file()),executed=False)))
if __name__=='__main__':main()