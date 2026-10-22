#!/usr/bin/env python3
"""Advance the assessed r101 held-nine cohort; never write a whole texture pack.

The existing converter's exact packages are reused, with immutable scoped IDs.
All emitted representations/certificates are PROPOSED DATA, not active source.
"""
from pathlib import Path
import ctypes, hashlib, json, math, random, shutil, struct, sys, zlib

ROOT=Path('/root/probe/codex-texture-rect21/port/dreamcast')
RECT=ROOT/'tools/d367/texture_rect21'
sys.path[:0]=[str(ROOT/'tools'),str(RECT)]
import mipmap_vq as mip
import convert_tpl as tpl
import rectangular_vq as rect
import world_bindings as world

BASE=Path('/root/re4data/private/texture-rect21-current948-scoped17-20261021/tex.pak')
BASE_SHA='bbcef25f0090fa4004e03331a33c84f8f89fd3582704e4a08945a8f6a15d5026'
HELD=Path('/root/re4data/private/texture-rect21-r101-held9-20261021')
HELD_SHA='1b19e134ac4e18dbe85e250c7d327b3da5e3f980ce4637340c55a009d7e060cf'
COVERAGE=Path('/root/re4data/private/mipmap21-fullpack-core-pairs-coverage-20261021/coverage.json')
COVERAGE_SHA='f1c83ea0af2bcbe55a96ac01cd11090c3adbc3058482c0a37dacb3dcc1dea450'
EVID=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021')
ORACLE=EVID/'oracle-02/oracle.so'
ORACLE_SHA='9aa99db42201950e20a5cd7d9f83e038b319aa4d7eb3b19a27e61449abe5dc70'
INPUT=EVID/'native-bindings-01/inputs/dc/native/r101/ps2-world.r4pw'
WORLD_SHA='2c9deabbe0ba1972109fa02c203360562d98e637733b08c0ff10ae2992dacd54'
FILES=EVID/'image-plan-04/baseline-file-identities.json'
TRACK=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/feedback21-runtime-20261021/qa-aafc10f3-input/gdemu/track03.bin')
RUN_FLOOR=18*1024**3+64*1024**2
START_FLOOR=18*1024**3+128*1024**2
BUDGET=32*1024**2

def sha(b):return hashlib.sha256(b).hexdigest()
def key(s):return tuple(int(v,16) for v in s.split('-'))
def name(k):return '%08x-%08x'%k
def require(b,why):
    if not b:raise ValueError(why)
def hashed_file(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1024*1024):h.update(b)
    return h.hexdigest()
def fnv(b):
    h=2166136261
    for x in b:h=((h^x)*16777619)&0xffffffff
    return h
def scoped(k,package_sha):
    return struct.unpack('<II',hashlib.sha256(b'RE4DC_WORLD_RECT21_COMPACT_V1\0'+struct.pack('<II',*k)+bytes.fromhex(package_sha)).digest()[:8])

def pack_index(path):
    """Independent bounded raw index reader; keep payloads on the existing file."""
    with path.open('rb') as f:
        h=f.read(2048)
        require(h[:8]==b'RE4PAK1\0','pack magic')
        version,count,off,data,crc=struct.unpack_from('<5I',h,8)
        require(version==1 and 0<count<=8192 and off==2048,'pack header')
        require(data==2048+((count*16+2047)//2048)*2048,'pack index extent')
        ix=f.read(data-2048)
        require(zlib.crc32(ix)&0xffffffff==crc and not any(ix[count*16:]),'pack index CRC/padding')
        entries={};end=data;previous=None
        for c,v,at,n in struct.iter_unpack('<4I',ix[:count*16]):
            k=(c,v);require(previous is None or previous<k,'pack key order')
            require(at==end and n>=144 and at+n<=path.stat().st_size,'pack member extent')
            entries[k]=(at,n);previous=k;end=at+((n+2047)//2048)*2048
        require(end==path.stat().st_size,'pack final extent')
    return entries

def read_member(f,index,k):
    off,n=index[k];f.seek(off);b=f.read(n);require(len(b)==n and b[:8]==b'RE4DCTX\0','pack member short/magic');return b

def validate_pair(old,candidate,r):
    require(sha(old)==r['source_sha256'] and sha(candidate)==r['candidate_sha256'],'package identity')
    h=tpl.HEADER.unpack_from(old);t=tpl.TEXTURE.unpack_from(old,h[5]);n=mip.read_native_vq(candidate)
    require(h[:6]==(tpl.MAGIC,2,48,96,1,48) and t[1:4]==(256,128,0),'source layout')
    require(t[4:]==(144,10240,0,2,0) and len(old)==10384,'source payload/flags')
    require(h[8] in (zlib.crc32(old[48:])&0xffffffff,zlib.crc32(old[144:])&0xffffffff),'source CRC')
    require(n.size==128 and n.texture[1:4]==(128,128,0) and n.texture[4:]==(144,7510,4,2,0),'candidate descriptor')
    require(n.texture[0]==t[0] and n.header[8]==r['candidate_crc32'],'material/CRC')
    require(n.codebook==old[144:2192],'original VQ codebook changed')
    require(r['logical']==[256,128] and r['physical']==[128,128] and r['uv_scale']==[1.,1.],'representation')
    return n

def rebind(old,mapping):
    rows=world.inspect_sidecar(old);out=bytearray(old);changed=[]
    require(struct.unpack_from('<II',old,24)==(0,0),'world reserved')
    for r in rows:
        if r['key'] not in mapping:continue
        require([r['width'],r['height']]==[256,128] and r['render_pass']==0 and r['flags']==0,'bound material/alpha policy')
        at=32+16*r['part'];new=mapping[r['key']];struct.pack_into('<II',out,at,*new)
        changed.append(dict(part=r['part'],original_key=r['key'],scoped_key=name(new),logical=[256,128],render_pass=0,cull=r['cull'],texture=r['texture'],flags=r['flags']))
    require(changed,'empty selected room binding')
    struct.pack_into('<I',out,20,zlib.crc32(out[32:])&0xffffffff)
    validate_rebind(old,bytes(out),mapping)
    return bytes(out),changed

def validate_rebind(old,new,mapping):
    a=world.inspect_sidecar(old);b=world.inspect_sidecar(new)
    require(len(old)==len(new) and len(a)==len(b) and old[:20]==new[:20] and old[24:32]==new[24:32],'world header')
    require(old[32+16*len(a):]==new[32+16*len(b):],'placement changed')
    for x,y in zip(a,b):
        require(all(x[f]==y[f] for f in ['part','width','height','render_pass','cull','texture','flags']),'material/geometry changed')
        require(y['key']==name(mapping[x['key']]) if x['key'] in mapping else y['key']==x['key'],'unqualified key change')

def original_mesh():
    record=json.loads(FILES.read_text())['files']['/dc/native/r101/ps2-world.re4mesh']
    # Exact existing baseline cooked scene file avoids duplicating geometry.
    cooked=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/standalone-B-01/gdemu/track03.iso')
    if cooked.exists():
        with cooked.open('rb') as f:f.seek((record['extent']-45000)*2048);b=f.read(record['bytes'])
        from_path=cooked
    else:
        require(TRACK.exists(),'retained baseline track absent')
        out=bytearray()
        with TRACK.open('rb') as f:
            for i in range((record['bytes']+2047)//2048):
                f.seek((record['extent']+i-45000)*2352+16);out+=f.read(2048)
        b=bytes(out[:record['bytes']]);from_path=TRACK
    require(sha(b)==record['sha256'],'geometry identity')
    mh=struct.unpack_from('<4s19I',b)
    require(mh[:3]==(b'R4IM',3,len(b)) and zlib.crc32(b[80:])&0xffffffff==mh[3],'geometry CRC/header')
    return b,mh,dict(path='/dc/native/r101/ps2-world.re4mesh',source_track=str(from_path),**record)

def decode_proof(lib,old,n):
    decode=lib.rect_oracle_decode;decode.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
    call=lib.mipmap_oracle_decode;call.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
    out=(ctypes.c_ubyte*(256*128*4))();require(decode(old[144:],10240,0,256,128,out,len(out))==len(out),'original decoder')
    source=bytes(out);levels=[];alpha=0;decoded={}
    for level in range(8):
        side=1<<level;p=(ctypes.c_ubyte*(side*side*4))()
        require(call(n.payload,len(n.payload),0,128,1,level,p,len(p))==len(p),'mip oracle')
        actual=bytes(p);expected=bytes(c for px in mip.decode_level(n,side) for c in px)
        require(actual==expected,'independent mip pixels')
        require(all(x==255 for x in actual[3::4]),'nonopaque RGB565 mip')
        alpha+=len(actual)//4;decoded[side]=actual;levels.append(side)
    base=decoded[128];rng=random.Random(210101);coords=[(rng.uniform(-8,8),rng.uniform(-8,8)) for _ in range(256)]+[(u,v) for u in [-8,-1,-.5,0,.5,1,8] for v in [-8,-1,-.5,0,.5,1,8]]
    maximum_period_error=0.;wrong=0
    for u,v in coords:
        p=rect.sample(base,128,128,u,v);q=rect.sample(base,128,128,u+3,v-2)
        maximum_period_error=max(maximum_period_error,max(abs(x-y) for x,y in zip(p,q)))
        bad=rect.sample(base,128,128,u*2,v)
        wrong+=any(abs(x-y)>1e-7 for x,y in zip(p,bad))
    require(maximum_period_error<1e-7 and wrong>0,'repeat/normalized UV control')
    # Full-resolution RGB is a filtered approximation, never an exact-base claim.
    mse=0.;peak=0.
    for y in range(128):
        for x in range(256):
            p=source[(y*256+x)*4:(y*256+x+1)*4];q=rect.sample(base,128,128,(x+.5)/256,(y+.5)/128)
            mse+=sum((p[c]-q[c])**2 for c in range(3));peak=max(peak,max(abs(p[c]-q[c]) for c in range(3)))
    mse/=256*128*3
    edges={str(side):dict(left=sha(b''.join(p[y*side*4:(y*side+1)*4] for y in range(side))),top=sha(p[:side*4]),right=sha(b''.join(p[(y*side+side-1)*4:(y*side+side)*4] for y in range(side))),bottom=sha(p[-side*4:])) for side,p in decoded.items()}
    return dict(decoded_levels=levels,independent_decoded_texels=alpha,all_alpha_255=True,normalized_uv=[1.,1.],repeat_sampling_cases=len(coords),maximum_repeat_period_error=maximum_period_error,wrong_dimension_scale_negative_cases=wrong,source_base_exact=False,base_rgb_rmse=math.sqrt(mse),maximum_base_channel_error=peak,edge_pixel_hashes=edges,limits=['Repeat proves current native sampler periodicity, not original TPL wrap flags.','Full-resolution RGB is filtered/requantized; scene look needs target review.'])

def virtual_composition(base,index,added):
    keys=sorted(set(index)|set(added));count=len(keys);require(count==6527,'virtual member count')
    data_at=2048+((count*16+2047)//2048)*2048;at=data_at;records=[]
    for k in keys:
        n=len(added[k]) if k in added else index[k][1];records.append(struct.pack('<4I',*k,at,n));at+=((n+2047)//2048)*2048
    ix=b''.join(records);ix+=bytes(data_at-2048-len(ix));head=b'RE4PAK1\0'+struct.pack('<5I',1,count,2048,data_at,zlib.crc32(ix)&0xffffffff);head+=bytes(2048-len(head));h=hashlib.sha256(head+ix);members=[];mip_count=0
    with base.open('rb') as f:
        for k in keys:
            b=added[k] if k in added else read_member(f,index,k)
            h.update(b);h.update(bytes((-len(b))%2048));t=tpl.TEXTURE.unpack_from(b,48);mip_count+=bool(t[6]&4)
            members.append(dict(key=name(k),sha256=sha(b),bytes=len(b),kind='scoped-r101-nine' if k in added else 'base-preserved'))
    require(mip_count==974,'mip key count')
    return dict(base_pack_sha256=BASE_SHA,base_members_preserved_exact=len(index),candidate_members=count,base_mip_keys=965,candidate_mip_keys=mip_count,expected_pack_sha256=h.hexdigest(),expected_pack_bytes=at,archive_delta=at-base.stat().st_size,full_pack_written=False,members=members)

def main():
    require(len(sys.argv)==3,'usage: prepare_r101.py <new WSL output> <new C mirror>')
    out=Path(sys.argv[1]);mirror=Path(sys.argv[2]);require(not out.exists() and not mirror.exists(),'preserve output')
    require(shutil.disk_usage('/mnt/c').free>=START_FLOOR,'C start floor')
    require(hashed_file(BASE)==BASE_SHA and hashed_file(ORACLE)==ORACLE_SHA,'input pack/oracle pin')
    held_bytes=(HELD/'receipt.json').read_bytes();receipt=json.loads(held_bytes);require(sha(held_bytes)==HELD_SHA and len(receipt['selected'])==9 and receipt['independent_mip_decodes']==72,'existing assessed nine scope/identity')
    old_world=INPUT.read_bytes();require(sha(old_world)==WORLD_SHA,'original world pin')
    mesh,mh,mesh_proof=original_mesh();wh=struct.unpack_from('<4s7I',old_world);require(mh[4:6]==(wh[4],wh[3]),'world/mesh counts')
    index=pack_index(BASE);require(len(index)==6518,'selected base count')
    lib=ctypes.CDLL(str(ORACLE));mapping={};added={};selected=[]
    coverage_bytes=COVERAGE.read_bytes();require(sha(coverage_bytes)==COVERAGE_SHA,'existing loose/quality key coverage identity')
    occupied=set(index)|{key(r['key']) for r in json.loads(coverage_bytes)['loose_and_quality_rows']}|{(0x3662c0aa,0xc9e71c00),(0xfefdf580,0xf15c1f47)}
    dependencies={str(p):hashed_file(p) for p in [Path(__file__),RECT/'compact.py',RECT/'room_cohort.py',RECT/'rectangular_vq.py',RECT/'world_bindings.py',ROOT/'tools/mipmap_vq.py',ROOT/'tools/convert_tpl.py',ORACLE]}
    with BASE.open('rb') as f:
        for r in receipt['selected']:
            old=read_member(f,index,key(r['key']));candidate=(HELD/'packages'/(r['key']+'.re4tex')).read_bytes();n=validate_pair(old,candidate,r);new=scoped(key(r['key']),sha(candidate));require(new not in occupied,'immutable scoped key collision');occupied.add(new);mapping[r['key']]=new;added[new]=candidate
            proof=decode_proof(lib,old,n)
            require(abs(proof['base_rgb_rmse']-r['source_texel_center_rgb_rmse'])<1e-9,'preserved converter/base oracle')
            selected.append(dict(original_key=r['key'],scoped_key=name(new),source_sha256=sha(old),candidate_sha256=sha(candidate),candidate_crc32=n.header[8],logical=[256,128],physical=[128,128],native_format=0,flags=4,payload=2,payload_bytes=7510,source_payload_bytes=10240,rounded_original=10240,rounded_candidate=7520,codebook_exact=True,**proof))
    new_world,changed=rebind(old_world,mapping);require({c['original_key'] for c in changed}==set(mapping),'unbound selected key')
    composition=virtual_composition(BASE,index,added)
    cert=dict(room=0x101,world_bytes=len(new_world),placements=wh[2],parts=wh[3],meshes=wh[4],physical_body_crc=struct.unpack_from('<I',new_world,20)[0],physical_file_fnv=fnv(new_world),mesh_crc=mh[3],mesh_bytes=len(mesh),source_crc=wh[5],source_world_sha256=WORLD_SHA,candidate_world_sha256=sha(new_world),mesh_sha256=sha(mesh),changed_records=[r['part'] for r in changed],unchanged_placements=True,unchanged_geometry=True,unchanged_material_pass_cull_alpha=True)
    table=['// PROPOSED r101 nine. Not installed in the active guarded table.']
    for r in selected:
        c,v=key(r['scoped_key']);table.append('{0x%08xU,0x%08xU,256U,128U,{128U,128U,0U,4U,2U,7510U,0x%08xU},1.0f,1.0f},'%(c,v,r['candidate_crc32']))
    cert_line='{0x101U,%dU,%dU,%dU,%dU,0x%08xU,0x%08xU,0x%08xU,%dU,0x%08xU},\n'%(cert['world_bytes'],cert['placements'],cert['parts'],cert['meshes'],cert['physical_body_crc'],cert['physical_file_fnv'],cert['mesh_crc'],cert['mesh_bytes'],cert['source_crc'])
    report=dict(schema='re4dc-world-next21-r101-nine-2',scope='Prepared existing assessed conversion for integration; no active source, full pack, image, build or guest',source_baseline='892c10ddeadcfcc0bb55bcf53c9b4ac25fd035e8',source_pack_sha256=BASE_SHA,existing_held_receipt_sha256=sha(held_bytes),existing_loose_quality_coverage_sha256=sha(coverage_bytes),immutable_collision_check='All6518 current pack keys, existing loose/quality consumer keys, both reserved atlas keys, and all9 newly generated keys',existing_converter_packages_reused=True,selected=selected,changed_bindings=changed,certificate=cert,geometry=mesh_proof,dependency_sha256=dependencies,independent_decoded_levels=sum(len(r['decoded_levels']) for r in selected),source_rounded=sum(r['rounded_original'] for r in selected),candidate_rounded=sum(r['rounded_candidate'] for r in selected),request_delta=sum(r['rounded_candidate']-r['rounded_original'] for r in selected),limits=['All current6518 pack members, original6501, prior965 mip keys and scoped17 remain preserved.','These9 become prepared974 total only after composition; the current written pack remains965.','Existing WORLD_RECT21 active allowlist/provenance certificates still admit17; rectangle/main must review/install this delta under default-off guard and qualify matching program/data.','All coupled R4ID/R4TC/OCCL/R4SG/PVS consumers must use reviewed semantic-source mapping. No metadata CRC is forged or rewritten.','No all-key final draws, target look, residency, netVRAM savings, frame time, release or physical Dreamcast acceptance.'])
    files={'receipt.json':(json.dumps(report,indent=2)+'\n').encode(),'virtual-composition.json':(json.dumps(composition,indent=2)+'\n').encode(),'proposed_representations.inc':('\n'.join(table)+'\n').encode(),'proposed_provenance_certificate.inc':cert_line.encode(),'dc/native/r101/ps2-world.r4pw':new_world}
    files.update({'textures/'+name(k)+'.re4tex':b for k,b in added.items()})
    require(sum(map(len,files.values()))*2+2*1024**2<=BUDGET,'combined output bound')
    require(shutil.disk_usage('/mnt/c').free-sum(map(len,files.values()))*2>=RUN_FLOOR,'C runtime floor')
    for root in [out,mirror]:
        root.mkdir(parents=True)
        for p,b in files.items():
            target=root/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
        sums=''.join(sha(b)+'  '+p+'\n' for p,b in sorted(files.items()));(root/'SHA256SUMS').write_text(sums)
    require(all(hashed_file(out/p)==hashed_file(mirror/p)==sha(b) for p,b in files.items()),'mirror exact')
    require(all(hashed_file(Path(p))==h for p,h in dependencies.items()),'dependency changed during preparation')
    print(json.dumps(dict(prepared_keys=9,bindings=len(changed),independent_levels=72,current_written_mips=965,proposed_composed_mips=974,virtual_pack_sha256=composition['expected_pack_sha256'],logical_output_and_mirror_bytes=sum(p.stat().st_size for r in [out,mirror] for p in r.rglob('*') if p.is_file()),certificate=cert)))

if __name__=='__main__':main()
