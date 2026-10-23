#!/usr/bin/env python3
"""Actor10395 ON/memory stage only; exact programme/overlays/private room; no guest."""
from pathlib import Path
import contracts as coverage_contract
import virtual_base
import argparse, datetime, hashlib, importlib.util, json, os, re, shutil, struct, subprocess, time, sys, contextlib, zlib

HERE=Path(__file__).resolve().parent

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
PVS=HERE.parent.parent/'pvs23'
h=module(PVS/'package-final.py','actor_pack_helpers')
native=module(PVS/'prepare-native-base.py','actor_native_helpers')
ADAPTER=HERE.parent/'material-census23-run'
SOURCE=coverage_contract.SOURCE
TREE=Path('/root/probe/codex-actor-visibility23-eligibility-witness-integration')
TREE_LEASE=Path('/root/probe/lanes/actor-visibility23-eligibility-witness-integration/tree.lock')
WORK=Path('/root/probe/lanes/actor-material-census23-staging')
CENSUS=coverage_contract.CENSUS
CROOT=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/pvs23-20261022')

def source_git(*args):return subprocess.check_output(['git','-C',str(TREE),*args],text=True).strip()

def adapter_validator():
    # These reviewed modules perform no process/emulator work at import. Only
    # native_path is adapted to the host's WSL spelling; validation is unchanged.
    sys.path.insert(0,str(ADAPTER))
    import binding_helpers
    binding_helpers.native_path=local
    validator=module(ADAPTER/'validate_bindings.py','actor_stage_adapter')
    validator.FINAL_SOURCE=SOURCE # Exact material-route source; validator also requires witness1.
    return validator


def elf_raw_proof(elf_path,raw_path,ELF):
    data=elf_path.read_bytes();elf=ELF(data)
    alloc=sorted([x for x in elf.sections if x['flags']&2 and x['type']!=8 and x['size'] and x['name']!='.stack'],key=lambda x:x['address'])
    assert alloc
    low=min(x['address']for x in alloc);high=max(x['address']+x['size']for x in alloc)
    assert 0x8c000000<=low<high<=0x8d000000
    rebuilt=bytearray(high-low);end=low
    for section in alloc:
        address,size,offset=section['address'],section['size'],section['offset']
        assert address>=end and 0<=offset<=len(data)-size,'Overlapping/truncated ELF raw section'
        rebuilt[address-low:address-low+size]=data[offset:offset+size];end=address+size
    raw=raw_path.read_bytes();assert bytes(rebuilt)==raw,'Unscrambled GD-ROM programme differs from actual ELF initialized sections'
    return dict(image_format='unscrambled-gdrom',elf_sha256=hashlib.sha256(data).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest(),
      address_low=hex(low),address_high=hex(high),bytes=len(rebuilt),exact_allocated_initialized_sections_equal=True,excluded_NOBITS=True,
      excluded_stack=True,byte_order='little-endian',gap_fill=0,sections=[dict(name=x['name'],address=hex(x['address']),size=x['size'],file_offset=x['offset'],flags=x['flags'],type=x['type'])for x in alloc])


def local(value):
    text=re.sub('/+','/',str(value).replace('\\','/'))
    if re.match(r'(?i)^C:/',text):text='/mnt/c/'+text[3:]
    elif text.lower().startswith('/wsl.localhost/ubuntu-24.04/'):
        text='/'+text[len('/wsl.localhost/Ubuntu-24.04/'):]
    elif text.lower().startswith('/wsl$/ubuntu-24.04/'):
        text='/'+text[len('/wsl$/Ubuntu-24.04/'):]
    return h.canonical(text)
def windows(value):
    p=h.canonical(value);s=str(p)
    if s.startswith('/mnt/c/'):return 'C:'+chr(92)+s[7:].replace('/',chr(92))
    assert s.startswith(('/root/','/opt/'))
    return '\\\\wsl.localhost\\Ubuntu-24.04'+s.replace('/','\\')
def canonical_record(row):
    result=dict(row);result['path']=windows(local(row['path']));return result

def appended_bytes(rows):return sum((row['size']+2047)//2048*2048 for row in rows.values())
def high_spans(disc):
    assert len(disc.trees)==2
    by_tree=[]
    for tree in disc.trees:
        mapping={}
        for name,rows in tree.files.items():
            assert rows and len({(r[2],r[3])for r in rows})==1
            mapping[name]=(rows[0][2],rows[0][3])
        by_tree.append(mapping)
    assert by_tree[0]==by_tree[1],'Primary/RR and Joliet file records differ'
    spans=sorted((ext,ext+n,name)for name,(ext,n)in disc.live.items()if ext>=45000)
    assert spans and spans[0][0]>=disc.meta_end and spans[-1][1]<=disc.t.end
    for left,right in zip(spans,spans[1:]):assert left[1]<=right[0],(left,right)
    for tree in disc.trees:
        for name,rows in tree.files.items():
            if rows[0][2]<45000:
                key=name.lstrip('/');assert key in native.SLOTS
                assert all(row[2]==native.SLOTS[key]and row[3]==8192 for row in rows)
    return len(spans)

PRIVATE_ROOT=Path(coverage_contract.BUILD_PRIVATE_ROOT)
ROOM_KEY='dc/native/r119/room.r4rc'
ROOM_SHA='9338bd8530b4f45b3c6e891e584f37cc81e93242c4eaec9a0a6bfd7abeb3d22c'
HEADER_SHA=coverage_contract.HEADER_SHA
BASE_INPUTS={
 'dc/native/r119/ps2-world.ids':dict(size=128,sha256='745d8e8be79e651c078b3850ae856721aa2f5a374a15b5acbb1136a7c1462cb6'),
 'dc/native/r119/ps2-world.r4pw':dict(size=7420,sha256='63b76c14a3a0cdc1fefb5d6b4daf56b38c80504d98bd686d2dfb8d74d42ba03b'),
 'dc/native/r119/ps2-world.re4mesh':dict(size=1058272,sha256='9dd036b326212d0052d7126f6aaea1c616a304f519933be103fe3c512a92eecd'),
 ROOM_KEY:dict(size=39968,sha256='7291b689c4a254c59dc2cad4ef4bf856d42487f00cac907fa4d79e5208ed2f64')}

def validate_base_binding(candidate,old_manifest,manifest_sha):
    binding=candidate['input_binding']
    assert local(binding['source'])==CROOT/'native-baf751e8'
    assert binding['manifest_sha256']==manifest_sha=='edaffab4dd90d72727bf9256e1c023d277e69e4dd60654162f475ca4d4ef2961'
    rows=binding['files'];assert len(rows)==4 and{r['name']for r in rows}==set(BASE_INPUTS)
    for row in rows:
        key=h.relpath(row['name']);assert h.normal(row)==BASE_INPUTS[key]==old_manifest[key]
        assert type(row['lba'])is int and row['lba']>=45000
    assert candidate['output_sha256']==ROOM_SHA and candidate['output_bytes']==40080
    assert set(candidate['preserved_sections_byte_identical'])=={'SRCB','GRID','SCDD'}
    return{row['name']:row for row in rows}

def room_sections(blob):
    assert len(blob)>=64 and blob[:4]==b'R4RC'
    n=struct.unpack_from('<I',blob,12)[0];assert 0<n<=64
    assert struct.unpack_from('<I',blob,16)[0]==len(blob)and len(blob)>=64+n*32
    assert zlib.crc32(blob[64:])==struct.unpack_from('<I',blob,48)[0]
    result={};spans=[]
    for i in range(n):
        row=struct.unpack_from('<4sHH6I',blob,64+i*32);tag=row[0].decode().rstrip(chr(0));offset,size=row[3:5]
        assert tag and tag not in result and offset>=64+n*32 and 0<=size<=len(blob)-offset
        result[tag]=blob[offset:offset+size];spans.append((offset,offset+size))
    for left,right in zip(sorted(spans),sorted(spans)[1:]):assert left[1]<=right[0]
    return result

def verify_room_delta(original,new,occl,header,candidate,r4pw):
    assert len(original)==39968 and hashlib.sha256(original).hexdigest()==BASE_INPUTS[ROOM_KEY]['sha256']
    assert len(new)==40080 and hashlib.sha256(new).hexdigest()==ROOM_SHA
    old=room_sections(original);current=room_sections(new);assert set(old)==set(current)=={'SRCB','GRID','SCDD','OCCL'}
    a=bytearray(original[:64]);b=bytearray(new[:64])
    for offset in(16,48):a[offset:offset+4]=b[offset:offset+4]=bytes(4)
    assert a==b,'Unrelated R4RC header bytes changed'
    for tag in('SRCB','GRID','SCDD'):assert old[tag]==current[tag],'Original room section changed: '+tag
    assert current['OCCL']==occl and len(occl)==1376
    assert zlib.crc32(occl)==0xc69f51d1
    assert hashlib.sha256(header).hexdigest()==HEADER_SHA
    assert re.search(rb'^#define ACTOR_VISIBILITY23_OCCL_CRC 0xc69f51d1U$',header,re.M)
    assert struct.unpack_from('<I',old['OCCL'],12)[0]==struct.unpack_from('<I',occl,12)[0]==int(candidate['runtime_logical_crc'],16)==0xfb5072f8
    assert len(r4pw)==BASE_INPUTS['dc/native/r119/ps2-world.r4pw']['size']
    assert hashlib.sha256(r4pw).hexdigest()==BASE_INPUTS['dc/native/r119/ps2-world.r4pw']['sha256']
    assert r4pw[:4]==b'R4PW'and struct.unpack_from('<I',r4pw,4)[0]==1
    assert zlib.crc32(r4pw[32:])==struct.unpack_from('<I',r4pw,20)[0]==int(candidate['physical_r4pw_crc'],16)==0xa79895c4
    return dict(original_room_sha256=BASE_INPUTS[ROOM_KEY]['sha256'],private_room_sha256=ROOM_SHA,certificate_header_sha256=HEADER_SHA,
      preserved_sections=['SRCB','GRID','SCDD'],occl_crc32='c69f51d1',runtime_logical_crc='fb5072f8',physical_r4pw_crc='a79895c4',scope='Exact private metadata bytes only; no live world/material/actor/pixel/cut acceptance.')

def private_contract(programme,private,old_manifest,manifest_sha,pin):
    assert private['source']==SOURCE and local(private['certificate_root'])==PRIVATE_ROOT
    assert private['copied_or_modified']is False and len(private['certificate_files'])==5 and len(private['sdk_files'])==210
    cert={local(row['path']).name:row for row in private['certificate_files']}
    assert set(cert)=={'room.r4rc','OCCL.bin','actor_visibility23_r119_certificate.h','candidate.json','geometry-proof.json'}
    for row in[*private['sdk_files'],*private['certificate_files']]:pin(row)
    for name,row in cert.items():assert local(row['path'])==PRIVATE_ROOT/name
    room=pin(programme['private_room_metadata']);assert room==PRIVATE_ROOT/'room.r4rc'
    assert programme['private_room_metadata']==cert['room.r4rc']and h.ident(room)==dict(size=40080,sha256=ROOM_SHA)
    assert cert['actor_visibility23_r119_certificate.h']['sha256']==HEADER_SHA
    allocation_path=pin(private['allocation_inputs']);allocation=json.loads(allocation_path.read_text())
    assert allocation['source']=='bea2d402ba06d41fb7b39946b5a9431a72f5b52a' and local(allocation['CERT'])==PRIVATE_ROOT and local(allocation['SDK'])==local(private['sdk_root'])
    for row in allocation['inputs']:pin(row)
    candidate=json.loads(pin(cert['candidate.json']).read_text());bindings=validate_base_binding(candidate,old_manifest,manifest_sha)
    knobs=dict(line.split('=',1)for line in pin(programme['resolved']).read_text().splitlines()if'='in line)
    assert local(knobs['ACTOR_VISIBILITY23_CERT'])==PRIVATE_ROOT and local(knobs['ACTOR_VISIBILITY23_SDK'])==local(private['sdk_root'])
    return room,cert,candidate,bindings


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('source','base-stage','base-stage-sha256','programme','programme-sha256','ownership-audit','ownership-audit-sha256','kos-receipt','kos-receipt-sha256','module-roster','module-roster-sha256','root-admission','root-admission-sha256','package-helper-sha256','native-helper-sha256','adapter-seal-sha256'):
        ap.add_argument('--'+name,required=True)
    ap.add_argument('--arm',choices=('on',),required=True)
    ap.add_argument('--run-id',default='q01');ap.add_argument('--execute',action='store_true')
    ap.add_argument('--package-review');ap.add_argument('--package-review-sha256')
    a=ap.parse_args()
    coverage_contract.require_final_bindings(a)
    if a.execute:coverage_contract.require_review(a.package_review,a.package_review_sha256)
    assert TREE_LEASE.is_file()
    with contextlib.ExitStack()as stack:
        tree_lease=stack.enter_context(TREE_LEASE.open('r+'));h.fcntl.flock(tree_lease,h.fcntl.LOCK_EX|h.fcntl.LOCK_NB)
        if a.execute:
            shared=stack.enter_context((h.WORK/'.pvs23-package.lock').open('a'));h.fcntl.flock(shared,h.fcntl.LOCK_EX|h.fcntl.LOCK_NB)
        return run(a)

def run(a):
    coverage_contract.require_final_bindings(a)
    assert a.source==SOURCE and a.run_id=='q01'
    assert h.sha(PVS/'package-final.py')==a.package_helper_sha256
    assert h.sha(PVS/'prepare-native-base.py')==a.native_helper_sha256
    stage_status='ACTOR23_TWIN_STAGED_NO_GUEST'
    assert h.union_bytes((HERE,CENSUS))<=8*1024**2,'Actor coverage package successor source/evidence cap'
    assert h.union_bytes(virtual_base.source_account_roots(WORK))<=8*1024**2,'Actor aggregate source/evidence cap'
    # Disk authority is checked before lengthy input readbacks, not invented here.
    admission_path=local(a.root_admission);admission=h.checked_json(admission_path,a.root_admission_sha256)
    assert admission['admitted']is True and not admission['errors']and admission['root_cap']==16*1024**3
    age=time.time()-datetime.datetime.fromisoformat(admission['utc'].replace('Z','+00:00')).timestamp()
    assert 0<=age<=60,'Fresh root disk admission required'
    inputs={str(admission_path):a.root_admission_sha256,str(CENSUS/'BINDINGS.json'):h.sha(CENSUS/'BINDINGS.json')}
    inputs.update(coverage_contract.verify_source_dependencies())
    def pin(row):
        path=local(row['path']);assert h.sha(path)==row['sha256'];inputs[str(path)]=row['sha256'];return path
    def read(path,digest):
        path=local(path);value=h.checked_json(path,digest);inputs[str(path)]=digest;return value
    base_stage=read(a.base_stage,a.base_stage_sha256)
    assert base_stage['status']=='PVS23_TWIN_STAGED_NO_GUEST'and re.fullmatch('[0-9a-f]{40}',base_stage['integration'])
    assert re.fullmatch('[0-9a-f]{40}',base_stage['source'])
    old_base=local(base_stage['base']);assert old_base==CROOT/'native-baf751e8/base'and base_stage['source']=='baf751e8e5d1ae26f64157ecb1018c159addd135'
    assert set(base_stage['members'])==native.MEMBERS
    h.compare(virtual_base.logical_inventory(h.inventory(old_base),base_stage['members']),base_stage['members'])
    virtual_binding=virtual_base.bind_inputs(pin)
    old_manifest_path=pin(base_stage['disc_manifest']);old_manifest=json.loads(old_manifest_path.read_text())
    old_assets_path=pin(base_stage['assets_manifest']);old_assets=json.loads(old_assets_path.read_text())
    h.compare(old_assets,old_manifest)
    old_extract_path=pin(base_stage['extraction_receipt']);old_extract=json.loads(old_extract_path.read_text())
    assert old_extract['extracted_from_iso']is True and old_extract['iso_sha256']==base_stage['members']['track03.iso']['sha256']
    assert old_extract['manifest_sha256']==base_stage['disc_manifest']['sha256']
    # Consume main's actual normalized wrappers; do not invent ownership clearance.
    stage_inputs=dict(programme_receipt=str(local(a.programme)),programme_receipt_sha256=a.programme_sha256)
    programme=read(a.programme,a.programme_sha256);integration=programme['integration']
    assert re.fullmatch('[0-9a-f]{40}',integration)
    stage_inputs['integration']=integration
    stage_inputs['arm']=a.arm
    assert programme['arm']==a.arm
    stage_inputs['private_inputs']=programme['private_inputs']
    for name in('ownership_audit','kos_receipt','module_roster'):
        path=local(getattr(a,name));digest=getattr(a,name+'_sha256');read(path,digest)
        if name in('kos_receipt','module_roster'):
            assert local(programme[name]['path'])==path and programme[name]['sha256']==digest
            stage_inputs[name]=canonical_record(programme[name])
        else:stage_inputs[name]=dict(path=str(path),sha256=digest)
    adapter_seal=read(CENSUS/'SOURCE-SEAL.json',a.adapter_seal_sha256)
    assert len(adapter_seal['files'])>=17 and 'fixtures.json'in adapter_seal['files']
    for name,row in adapter_seal['files'].items():
        path=CENSUS/h.relpath(name.replace(chr(92),'/'));assert h.ident(path)==h.normal(row);inputs[str(path)]=row['sha256']
    validator=adapter_validator()
    programme,syms=validator.current_programme(stage_inputs,a.source,inputs)
    validator.ownership_contract(stage_inputs,programme,a.source,inputs)
    files={name:pin(programme[name])for name in('elf','raw','resolved','syms_file','compile_receipt','source_seal')}
    # Metadata alone cannot select a boot encoding; derive the actual binary
    # from allocated initialized final ELF sections and compare every byte.
    assert programme.get('image_format')=='unscrambled-gdrom'
    normalizer=module(ADAPTER/'elf_image.py','actor_stage_elf_parser')
    raw_proof=elf_raw_proof(files['elf'],files['raw'],normalizer.ELF)
    assert programme['raw_ELF_evidence']==raw_proof
    compiled=json.loads(files['compile_receipt'].read_text())
    assert compiled['image_format']=='unscrambled-gdrom'and compiled['raw_ELF_evidence']==raw_proof
    rows=programme['overlays'];assert len(rows)==14
    assert {row['package_path']for row in rows}=={'dc/'+name for name in h.OVERLAYS}
    replacements={'1ST_READ.BIN':files['raw']}
    for row in rows:replacements[h.relpath(row['package_path'])]=pin(row)
    assert all(key in old_manifest and path.stat().st_size>0 for key,path in replacements.items())
    fixture_file,fixtures=coverage_contract.census_fixture_contract(pin)
    private=coverage_contract.normalized_actual_private(read(programme['private_inputs']['path'],programme['private_inputs']['sha256']),pin)
    assert programme['world_package_baseline']['manifest_sha256']==base_stage['disc_manifest']['sha256']
    private_room,certificate_files,candidate,base_bindings=private_contract(programme,private,old_manifest,base_stage['disc_manifest']['sha256'],pin)
    assert programme['world_package_baseline']==candidate['input_binding']
    replacements[ROOM_KEY]=private_room
    assert len(replacements)==16
    knobs=dict(line.split('=',1)for line in files['resolved'].read_text().splitlines()if'='in line)
    # Source10395's sparse checkout omits fp_iso. Reuse the exact retained
    # existing bytes, independently checked against the10395 commit blob below.
    helper=h.canonical(h.TREE/'port/dreamcast/tools/d367/fullplay/fp_iso.py')
    swap_path=h.canonical(TREE/'port/dreamcast/tools/swap-program.py')
    source_tools={helper:'port/dreamcast/tools/d367/fullplay/fp_iso.py',swap_path:'port/dreamcast/tools/swap-program.py'}
    assert source_git('rev-parse','HEAD')==a.source and source_git('status','--porcelain')==''
    tools={str(p):h.sha(p)for p in (Path(__file__).resolve(),HERE/'virtual_base.py',HERE/'contracts.py',PVS/'package-final.py',PVS/'prepare-native-base.py',helper,swap_path)}
    for path,relative in source_tools.items():
        assert h.sha(path)==hashlib.sha256(subprocess.check_output(['git','-C',str(TREE),'show',a.source+':'+relative])).hexdigest()
    fp=module(helper,'actor_fp_iso');swap=module(swap_path,'actor_swap')
    # Read only the four exact original r119 inputs. This is not extraction or
    # geometry regeneration; all hashes/LBAs bind the source certificate.
    with virtual_base.open_original_composite(fp,old_base/'track01-template.iso')as original:
        locations={name.lstrip('/'):(extent,size)for name,extent,size in fp.files(original)if name.lstrip('/')in BASE_INPUTS}
        assert set(locations)==set(BASE_INPUTS)
        original_bytes={}
        for key,row in base_bindings.items():
            assert locations[key]==(row['lba'],row['size'])
            data=original.read_bytes(*locations[key]);assert hashlib.sha256(data).hexdigest()==row['sha256'];original_bytes[key]=data
        private_proof=verify_room_delta(original_bytes[ROOM_KEY],private_room.read_bytes(),pin(certificate_files['OCCL.bin']).read_bytes(),
          pin(certificate_files['actor_visibility23_r119_certificate.h']).read_bytes(),candidate,original_bytes['dc/native/r119/ps2-world.r4pw'])
    target=dict(old_manifest);target.update({key:h.ident(path)for key,path in replacements.items()})
    payload_size=appended_bytes({key:h.ident(path)for key,path in replacements.items()})
    new_iso_bytes=base_stage['members']['track03.iso']['size']+payload_size
    assert new_iso_bytes//2048+45000<=swap.HD_END,'Appending programme/overlays exceeds native track extent'
    name='actor23-'+a.source[:8]+'-'+a.arm+'-'+a.run_id
    dest=h.canonical(CROOT/name);base=dest/'base';assert not dest.exists()
    manuals=tuple(Path('/mnt/c/Game Dev/Emulators').glob('RE4DC-QA23-PVS-*'))
    roots=(h.WORK,h.TREE,CROOT,*virtual_base.source_account_roots(WORK),*manuals)
    initial=h.union_bytes(roots)
    extra=new_iso_bytes+base_stage['members']['track01-template.iso']['size']+base_stage['members']['track02.raw']['size']+16*1024**2
    guest_reserve=admission['guest_peak'];assert guest_reserve==60*1024**2
    assert initial+extra+guest_reserve<=h.CAP,dict(current=initial,planned_extra=extra,guest_reserve=guest_reserve,cap=h.CAP)
    assert admission['projected_peak']+extra<=admission['root_cap'],'Root16GiB peak exceeded'
    assert shutil.disk_usage('/mnt/c').free>=h.FLOOR+extra
    plan=dict(kind='actor23-'+a.arm,adapter=str(ADAPTER),adapter_seal_sha256=a.adapter_seal_sha256,source=a.source,base_source=base_stage['source'],integration=integration,base=str(base),
      original_base=str(old_base),virtual_base=virtual_binding,programme_receipt_sha256=a.programme_sha256,new_iso_bytes=new_iso_bytes,
      appended_payload_bytes=payload_size,initial_owned_bytes=initial,projected_owned_bytes=initial+extra+guest_reserve,guest_reserve=guest_reserve,
      root_projected_bytes=admission['projected_peak']+extra,cap=h.CAP,floor=h.FLOOR,tools=tools,
      tool_source_paths={str(path):relative for path,relative in source_tools.items()},
      raw_ELF_evidence=raw_proof,private_room_proof=private_proof,execute=a.execute,scope='Actual programme/ISO stage only; no fake source, runtime, native review, guest or hardware acceptance.')
    if not a.execute:print(json.dumps(plan,indent=2));return
    # Only one new C-side ISO is allocated; no intermediate second full copy.
    assert TREE_LEASE.is_file()and WORK.is_dir()
    dest.mkdir();base.mkdir();receipt=dict(plan,status='STARTED',guest_started=False,peak_owned_bytes=initial)
    receipt_path=dest/'media-receipt.json';start=time.monotonic()
    def save():h.atomic(receipt_path,receipt)
    def guard():
        # No growing allocation occurs during manifest readback. Keep each asset
        # check O(1); the full shared census belongs at phase boundaries only.
        assert shutil.disk_usage('/mnt/c').free>=h.FLOOR
        assert time.monotonic()-start<1800,'Actor media wall cap'
        grown=sum(p.stat().st_size for p in base.iterdir()if p.is_file())
        assert grown<=extra,'Preallocated maximum exceeded'
    def boundary(label,remaining=0):
        guard();size=h.union_bytes(roots)
        assert size+guest_reserve+remaining<=h.CAP,('Aggregate3.5GiB phase cap',label,size,remaining)
        metadata=h.union_bytes(virtual_base.source_account_roots(WORK))+sum(p.stat().st_size for p in dest.iterdir()if p.is_file())
        metadata+=sum((base/name).stat().st_size for name in('base.json','track03.sha256')if(base/name).is_file())
        assert metadata<=8*1024**2,'Actor package source/evidence cap'
        receipt['peak_owned_bytes']=max(receipt['peak_owned_bytes'],size)
        receipt.setdefault('phase_census',[]).append(dict(phase=label,owned=size,remaining=remaining))
        save()

    def pins():
        assert source_git('rev-parse','HEAD')==a.source
        for path,digest in inputs.items():assert h.sha(path)==digest,'Pinned input changed: '+path
        for path,digest in tools.items():assert h.sha(path)==digest,'Tool changed: '+path
    save()
    try:
        boundary('before-copy',extra)
        for name in ('track01-template.iso','track02.raw'):
            with (old_base/name).open('rb')as reader,(base/name).open('xb')as writer:
                while block:=reader.read(4*1024**2):writer.write(block);guard()
            assert h.ident(base/name)==base_stage['members'][name]
        virtual_base.copy_original_iso(base/'track03.iso',base_stage['members']['track03.iso'],guard)
        assert h.ident(base/'track03.iso')==base_stage['members']['track03.iso']
        boundary('copy-complete',payload_size+16*1024**2)
        Composite=native.composite_type(fp);old_comp=Composite(str(base/'track03.iso'),str(base/'track01-template.iso'))
        try:h.compare(native.read_manifest(fp,old_comp,guard),old_manifest);native.assert_redirected(native.fixture_records(fp,old_comp))
        finally:old_comp.close()
        boundary('before-programme-mutation',payload_size+16*1024**2);pins()
        copied_before=h.sha(base/'track03.iso');track=swap.Track(base/'track03.iso',2048)
        try:
            disc=swap.Disc(track);assert disc.standard is False and len(disc.trees)==2
            assert {tr.joliet for tr in disc.trees}=={False,True}
            mutations=[]
            # Always append. Existing file payload and accepted base remain untouched.
            for key,path in sorted(replacements.items(),key=lambda kv:kv[0]=='1ST_READ.BIN'):
                iso_key='/'+key.lower();records=disc.recs(iso_key)
                assert len(records)==2 and len({(r[2],r[3])for r in records})==1
                assert all(len(tr.files.get(iso_key,[]))==1 for tr in disc.trees)
                blob=path.read_bytes();new_lba=disc.alloc(swap.nsec(len(blob)))
                before_records=records[:];disc.put(new_lba,blob);disc.point(iso_key,new_lba,len(blob));guard()
                assert all(r[2]==new_lba and r[3]==len(blob)for r in disc.recs(iso_key))
                assert track.read_blob(new_lba,len(blob))==blob
                mutations.append(dict(package_path=key,identity=h.ident(path),records_before=before_records,new_lba=new_lba))
            disc.finish()
            for tr in disc.trees:
                descriptor=track.user(tr.vd_lba)
                assert struct.unpack_from('<I',descriptor,80)[0]==track.sectors==struct.unpack_from('>I',descriptor,84)[0]
            checked=swap.Disc(track);high_count=high_spans(checked)
            boot=checked.recs('/1st_read.bin');assert all(ext+swap.nsec(size)==track.end for _,_,ext,size in boot)
        finally:track.f.close()
        assert (base/'track03.iso').stat().st_size==new_iso_bytes
        boundary('programme-appended',16*1024**2)
        comp=Composite(str(base/'track03.iso'),str(base/'track01-template.iso'))
        try:
            record_proof=native.fixture_records(fp,comp);native.assert_redirected(record_proof)
            actual=native.read_manifest(fp,comp,guard);h.compare(actual,target)
        finally:comp.close()
        boundary('readback-complete-before-metadata',16*1024**2);pins()
        iso_digest=h.sha(base/'track03.iso');meta=json.loads((old_base/'base.json').read_text())
        layout=dict(kind='twin',warp_lba=400,pad_lba=420,w11_lba=440,fixture_bytes=8192,
          gdi='3\n1 0 4 2048 track01.iso 0\n2 756 0 2352 track02.raw 0\n3 45000 4 2048 track03.iso 0\n')
        assert {k:meta.get(k)for k in layout}==layout
        meta['elf']=programme['elf']['path'];meta['tree']='not-extracted: exact16 appends over '+str(old_base)
        h.atomic(base/'base.json',meta);(base/'track03.sha256').write_text(iso_digest+'\n')
        assert set(p.name for p in base.iterdir())==native.MEMBERS
        h.atomic(dest/'assets-manifest.json',old_assets);h.atomic(dest/'disc-manifest.json',actual)
        extraction=dict(source=a.source,integration=integration,extracted_from_iso=True,iso_sha256=iso_digest,
             manifest_sha256=h.sha(dest/'disc-manifest.json'),composite_iso_readback=True,track01_sha256=h.sha(base/'track01-template.iso'),
             scope='Actual full composite ISO readback after exact16-file append; no extracted tree or guest.')
        h.atomic(dest/'extraction-receipt.json',extraction);pins()
        h.compare(virtual_base.logical_inventory(h.inventory(old_base),base_stage['members']),base_stage['members']);guard()
        members=h.inventory(base)
        stage=dict(status=stage_status,source=a.source,integration=integration,arm=a.arm,
          programme_receipt=windows(local(a.programme)),programme_receipt_sha256=a.programme_sha256,
          assets_manifest=dict(path=windows(dest/'assets-manifest.json'),sha256=h.sha(dest/'assets-manifest.json')),
          disc_manifest=dict(path=windows(dest/'disc-manifest.json'),sha256=h.sha(dest/'disc-manifest.json')),
          extraction_receipt=dict(path=windows(dest/'extraction-receipt.json'),sha256=h.sha(dest/'extraction-receipt.json')),
          fixtures=dict(path=windows(fixture_file),sha256=h.sha(fixture_file)),
          ownership_audit=canonical_record(dict(path=a.ownership_audit,sha256=a.ownership_audit_sha256)),
          kos_receipt=canonical_record(programme['kos_receipt']),
          module_roster=canonical_record(programme['module_roster']),
          private_inputs=programme['private_inputs'],private_room_metadata=programme['private_room_metadata'],
          base=windows(base),members=members,fixture_pins=fixtures,virtual_base=virtual_binding)
        h.atomic(dest/'stage-receipt.json',stage)
        receipt.update(status=stage_status,original_iso_sha256=copied_before,
          final_iso_sha256=iso_digest,mutations=mutations,fixture_record_proof=record_proof,high_live_files=high_count,
          stage_receipt_sha256=h.sha(dest/'stage-receipt.json'),members=members)
        boundary('final');save();print(json.dumps(dict(stage=windows(dest/'stage-receipt.json'),sha256=receipt['stage_receipt_sha256'],base=windows(base),scope=plan['scope']),indent=2))
    except BaseException as error:receipt.update(status='STOPPED_PRESERVED',error=repr(error));save();raise
    finally:pass # leases are held and released by main() around all validation/staging

if __name__=='__main__':main()
