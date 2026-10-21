#!/usr/bin/env python3
"""Seal a plan-only B/C rectangle comparison from existing frozen inputs; no images or guests."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

SOURCE='004cf224674fa60cf08dc10e641c723de238a0fd'
PROGRAM='a58579b87da0c45267cb93efe29feea2438da9ddab62d0fe31c47a1c6ff32c71'
ELF='e08c9abc8f6bb44bb2a94642fc9a2e664d22039659cea7fcce311cb9989d7433'
BASE='e19cfc464e789e97ca96864adfc2a4cd44443a9f4775bebd842c3e184a65559b'
PACK='bbcef25f0090fa4004e03331a33c84f8f89fd3582704e4a08945a8f6a15d5026'
MANIFEST='b2dc69e1d1ee705ded6604b13f0649313c69378ac09f7945035c4ada95e1cfbe'
REQUIRED=['CAST_MIPMAP','TEX_TWIDDLED_MIPMAP','TEX_PAL4_ALPHA','TEX_PAL4_MIPMAP','TEX_PAL8_ALPHA','TEX_PAL8_MIPMAP','WORLD_RECT21','PS2_WORLD_DRAW','PS2_WORLD_MESH','MESH_DIRECT']


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1<<20),b''):h.update(part)
    return h.hexdigest()


def identity(path):return {'size':Path(path).stat().st_size,'sha256':sha(path)}

def load(path):return json.loads(Path(path).read_text())

def write(path,data):
    with Path(path).open('x') as out:json.dump(data,out,indent=2,sort_keys=True);out.write('\n')


def sidecar_proof(original,candidate,changes):
    if len(original)!=len(candidate):raise ValueError('sidecar extent changed')
    allowed=set(range(20,24));parts=[]
    for row in changes:
        at=32+row['part']*16
        old=tuple(int(v,16) for v in row['original_key'].split('-'))
        new=tuple(int(v,16) for v in row['scoped_key'].split('-'))
        if struct.unpack_from('<II',original,at)!=old or struct.unpack_from('<II',candidate,at)!=new:raise ValueError('sidecar key row differs')
        if original[at+8:at+16]!=candidate[at+8:at+16]:raise ValueError('logical/material fields changed')
        allowed.update(range(at,at+8));parts.append(row['part'])
    unexpected=[i for i,(a,b) in enumerate(zip(original,candidate)) if a!=b and i not in allowed]
    if unexpected:raise ValueError('unexpected geometry/material/placement byte change')
    if struct.unpack_from('<I',candidate,20)[0]!=zlib.crc32(candidate[32:])&0xffffffff:raise ValueError('candidate R4PW CRC mismatch')
    return {'changed_parts':parts,'only_selected_key_words_and_body_crc_changed':True,'all_other_bytes_exact':True}


def select_symbol(rows,name,size=None):
    found=[r for r in rows if r['name']==name and (size is None or r['size']==size)]
    if len(found)!=1:raise ValueError('ambiguous/missing symbol '+name+'; use actual type size/source provenance')
    return found[0]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['program-root','pair','data','base-pack','scoped-receipt','original-inputs','baseline-manifest','dwarf','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--nm',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-nm')
    a=p.parse_args()
    if a.out.exists():raise SystemExit('preserve existing metadata output')
    pair=load(a.pair);on=pair['arms']['on'];qual=load(a.data/'qualification.json');scoped=load(a.scoped_receipt)
    if pair['source']!=SOURCE or on['program_sha256']!=PROGRAM or on['elf_sha256']!=ELF:raise ValueError('unexpected frozen program receipt')
    program_files={}
    for expected in on['files']:
        file=a.program_root/Path(expected['path']).name;actual=identity(file)
        if actual!={'size':expected['bytes'],'sha256':expected['sha256']}:raise ValueError('actual program/overlay differs '+str(file))
        program_files[file.name]=actual
    if len([n for n in program_files if n.endswith('.ovl')])!=14:raise ValueError('expected all14 overlays')
    if sha(a.program_root/'re4dc-game.elf')!=ELF:raise ValueError('actual ELF differs')
    values={}
    for line in (a.program_root/'resolved-knobs.txt').read_text().splitlines():
        if '=' in line and not line.startswith('#'):key,value=line.split('=',1);values[key]=value
    if any(values.get(k)!='1' for k in REQUIRED):raise ValueError('required format/consumer knob absent')
    if values.get('ALIVE_CAP')!='4' or values.get('ANIMALS_OFF')!='1' or values.get('SKIN_SH4ZAM')!='0':raise ValueError('gameplay or skin control changed')
    if values.get('SS_WINDOW_HOLD_RESTORE','0')!='0':raise ValueError('negative window restoration candidate must stay disabled')
    if sha(a.base_pack)!=BASE or sha(a.data/'tex.pak')!=PACK or sha(a.data/'SHA256SUMS')!=MANIFEST:raise ValueError('actual frozen data differs')
    if qual['base_pack_sha256']!=BASE or qual['candidate_pack_sha256']!=PACK or qual['base_members_preserved_exact']!=6501:raise ValueError('data qualification differs')
    a.out.mkdir(parents=True,exist_ok=False)
    baseline=load(a.baseline_manifest)['files'];B=dict(baseline);C=dict(baseline)
    for name,record in program_files.items():
        path='1ST_READ.BIN' if name=='program.bin' else 'dc/'+name
        B[path]=record;C[path]=record
    B['dc/tex.pak']=identity(a.base_pack);C['dc/tex.pak']=identity(a.data/'tex.pak')
    worlds=[]
    bypath={row['path']:row for row in scoped['worlds']}
    for row in qual['sidecars']:
        path=row['path'];old=a.original_inputs/path;new=a.data/path
        if sha(old)!=row['source_sha256'] or sha(new)!=row['output_sha256']:raise ValueError('sidecar identity differs')
        proof=sidecar_proof(old.read_bytes(),new.read_bytes(),bypath[path]['changed_parts'])
        B[path]=identity(old);C[path]=identity(new);worlds.append({'path':path,'baseline':B[path],'candidate':C[path],**proof})
    changed=sorted(k for k in set(B)|set(C) if B.get(k)!=C.get(k))
    expected=['dc/tex.pak']+sorted(row['path'] for row in worlds)
    if changed!=sorted(expected):raise ValueError('unexpected B/C staged file difference')
    nm=subprocess.check_output([a.nm,'-S','-n',str(a.program_root/'re4dc-game.elf')],text=True)
    symbols=[]
    for line in nm.splitlines():
        parts=line.split()
        if len(parts)==4:
            symbols.append({'address':int(parts[0],16),'size':int(parts[1],16),'kind':parts[2],'name':parts[3]})
    types=load(a.dwarf)['types'];stride=types['Entry']['size'];slots=int(values['TEX_SLOTS'])
    entry_name='__ZN12_GLOBAL__N_1L7entriesE'
    selected={'native_ui_entries':select_symbol(symbols,entry_name,stride*slots)}
    wanted=['_pG','_pPL','_CamCtrl','_re4dc_logbuf','_re4dc_log_head','_re4dc_stage',
            '__ZN12_GLOBAL__N_1L11m_tot_readsE','__ZN12_GLOBAL__N_1L11m_tot_bytesE','__ZN12_GLOBAL__N_1L11m_tot_blockE',
            '__ZN12_GLOBAL__N_1L13model_packetsE','__ZN12_GLOBAL__N_1L10model_usedE',
            '__ZN12_GLOBAL__N_1L13model_pendingE','__ZN12_GLOBAL__N_1L11vram_budgetE',
            '__ZN12_GLOBAL__N_1L12vram_retriesE','__ZN12_GLOBAL__N_1L12vram_rejectsE','_pvr_state']
    wanted+=['__ZN12_GLOBAL__N_1L11direct_openE','__ZN12_GLOBAL__N_1L12model_handleE',
             '__ZN12_GLOBAL__N_1L5frameE','__ZN12_GLOBAL__N_1L15frame_pvr_bytesE','__ZN12_GLOBAL__N_1L15frame_pvr_callsE']
    for name in wanted:selected[name]=select_symbol(symbols,name)
    result={'schema':1,'status':'PLAN_ONLY_NO_STAGE_OR_GUEST','source':SOURCE,'program':PROGRAM,'elf':ELF,
            'actual_program_files':program_files,'resolved_knobs':{k:values.get(k) for k in REQUIRED+['ALIVE_CAP','ALIVE_CAP_N','ANIMALS_OFF','SKIN_SH4ZAM','GAME_SH4ZAM','SS_WINDOW_HOLD_RESTORE','DISC_READ_METER','PHASE_METER','GAME_TICK_LOG','TEX_SLOTS']},
            'historical_A':'Original QAac52 baseline is context only; never label totalA/C as17rect savings',
            'B':{'scope':'current948 pipeline control, original sidecars','pack':B['dc/tex.pak']},
            'C':{'scope':'same948 plus17scoped candidate, selected key-only sidecars','pack':C['dc/tex.pak']},
            'B_C_difference_files':changed,'worlds':worlds,'selected':scoped['selected'],
            'key_overlap_source_budget':{'selected_original_rounded':69632,'selected_candidate_rounded':58208,'possible_both_rounded':127840,'target_allocation_or_saving':False},
            'symbols':selected,'native_ui_entry_symbol_candidates':[r for r in symbols if r['name']==entry_name],
            'native_ui_entry_stride':stride,'native_ui_entry_count':slots,'native_ui_layout_sha256':sha(a.dwarf),
            'input_receipts':{'pair':sha(a.pair),'data_qualification':sha(a.data/'qualification.json'),'data_manifest':sha(a.data/'SHA256SUMS'),'scoped':sha(a.scoped_receipt)},
            'limitations':['No image identities exist until authorized staging; expected manifests are file-level requirements only.','Texture residency/cached header does not prove final PVR draw submission.','Both arms require independently cold-created own-image checkpoints; no state transfer even with the same program.','Full RAM/VRAM attribution and selected-frame drive deltas require target observation.']}
    write(a.out/'plan-inputs.json',result);write(a.out/'expected-files-B.json',B);write(a.out/'expected-files-C.json',C)
    print(json.dumps({'changed_files':changed,'program_files':len(program_files),'entry_stride':stride,'entry_count':slots,'source_bytes_written':sum(f.stat().st_size for f in a.out.rglob('*') if f.is_file())}))

if __name__=='__main__':main()
