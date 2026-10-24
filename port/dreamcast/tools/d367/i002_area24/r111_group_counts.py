"""Read-only r111 group30 counts; no geometry predicates or asset changes."""
import argparse,collections,hashlib,importlib.util,json,resource,struct,subprocess,tempfile,zlib
from pathlib import Path
SOURCE='78cbd962ee0d98dc700d0fb452500a16ac35b14c'
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def require(item):
 p=Path(item['path'])
 if pin(p)!=item:raise ValueError('Pinned private input changed '+str(p))
 return p

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2)
 if a.out.exists():raise ValueError('Fresh output required')
 migration=a.evidence/'r111-policy-migration-research.json';d=json.loads(migration.read_text());used={k:d['source_inputs'][k] for k in ('mesh','current_policy','original_policy','ids')}
 for item in used.values():require(item)
 ram=Path(tempfile.mkdtemp(prefix='i002-group24-',dir='/dev/shm'));data=subprocess.check_output(['git','-C',str(a.repo),'show','581482ed4274ac30e1c9da8ec92760e9b3f93354:port/dreamcast/tools/d367/interior_vis23/surface_mesh.py'])
 if hashlib.sha256(data).hexdigest()!='45e31e1ec7b728940ab7d89064fe955f2a77ba5171614343645c5718100908b9':raise ValueError('Reader mismatch')
 mod=ram/'surface_mesh.py';mod.write_bytes(data);spec=importlib.util.spec_from_file_location('r111_counts',mod);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 mesh=Path(used['mesh']['path']);policy=Path(used['current_policy']['path']);original=Path(used['original_policy']['path']);ids=Path(used['ids']['path']).read_bytes();p=m.Pkg(mesh,policy);op=m.Pkg(mesh,original);magic,version,n,crc=struct.unpack_from('<4sIII',ids)
 if (magic,version,n,crc)!=(b'R4ID',1,len(p.placements),op.sidecar_crc) or p.placements!=op.placements or zlib.crc32(p.m[80:])!=p.mesh_crc:raise ValueError('Package/IDs/affines/CRC')
 raw=policy.read_bytes()
 if zlib.crc32(raw[32:])!=p.sidecar_crc:raise ValueError('Policy CRC')
 owners=ids[16:16+n];rows=[];totals=collections.Counter();materials={}
 for pi,pl in enumerate(p.placements):
  if owners[pl['placement']]!=0x1e:continue
  meshrow=p.meshes[pl['mesh']];passes=collections.defaultdict(collections.Counter);clusters=0;parts=[]
  for part in range(meshrow['first_part'],meshrow['first_part']+meshrow['part_count']):
   meta=p.pmeta[part];fc,nc=p.plod[part];clusters+=nc;levellets=[];levels=[]
   for ci in range(fc,fc+nc):
    cl=p.clusters[ci];lv=[p.levels[cl['first_level']+k] for k in range(cl['level_count'])];levels.append(dict(cluster=ci,authored_counts=[x[1] for x in lv]));first,count,_=lv[0];levellets.extend(range(first,first+count))
   if len(levellets)!=len(set(levellets)):raise ValueError('Repeated LOD0 lets in part')
   entry=passes[meta['pass_']];entry['parts']+=1;entry['meshlets']+=len(levellets);entry['corners']+=sum(p.lets[i]['vc'] for i in levellets);entry['indexed_meshlets']+=sum(bool(p.lets[i]['sc']&32768) for i in levellets)
   materials[part]=dict(part=part,pass_=meta['pass_'],cull=meta['cull'],vertex_alpha=bool(raw[32+16*part+15]&1),texture_crc=f"{meta['crc']:08x}",texture_fnv=f"{meta['fnv']:08x}",logical_width=meta['w'],logical_height=meta['h'])
   parts.append(dict(part=part,pass_=meta['pass_'],lod0_meshlets=len(levellets),lod0_corners=sum(p.lets[i]['vc'] for i in levellets),clusters=levels))
  r=dict(placement=pi,field=pl['placement'],mesh=pl['mesh'],owner_id=30,group_occurrences=owners.count(30),dynamic_unique_slot_eligible=False,clusters=clusters,passes={str(k):dict(v) for k,v in sorted(passes.items())},parts=parts);rows.append(r)
  for k,v in passes.items():
   for key,value in v.items():totals[f'pass{k}_{key}']+=value
 if [r['placement'] for r in rows]!=list(range(57,70)):raise ValueError('Fixed source group namespace changed')
 # Independent direct offset census; no triangle coordinates or predicates.
 h=struct.unpack_from('<4s19I',p.m);ncl,nlv,opl,ocl,olv=struct.unpack_from('<5I',p.m,80);direct=collections.Counter();off=32+16*p.npart
 for pi in range(n):
  mi,field=struct.unpack_from('<HH',raw,off+52*pi)
  if owners[field]!=30:continue
  mr=struct.unpack_from('<HBBHHIII12f',p.m,h[10]+68*mi)
  for part in range(mr[6],mr[6]+mr[7]):
   pas=raw[32+16*part+12];fc,nc=struct.unpack_from('<II',p.m,opl+8*part);direct[f'pass{pas}_parts']+=1
   for ci in range(fc,fc+nc):
    firstlv,nlevels=struct.unpack_from('<II',p.m,ocl+20*ci+12);first,count=struct.unpack_from('<II',p.m,olv+12*firstlv)
    direct[f'pass{pas}_meshlets']+=count
    for li in range(first,first+count):
     vc,sc=struct.unpack_from('<HH',p.m,h[12]+28*li+12);direct[f'pass{pas}_corners']+=vc;direct[f'pass{pas}_indexed_meshlets']+=bool(sc&32768)
 if dict(direct)!=dict(totals):raise ValueError('Independent raw layout count mismatch')
 cam_receipt_path=a.evidence/'r111-fixture-source-proof/r111-cam-enclosure-receipt.json';cam_receipt=json.loads(cam_receipt_path.read_text());dar=Path(cam_receipt['dar'])
 if pin(dar)['sha256']!=cam_receipt['dar_sha256']:raise ValueError('Current DAR source drift')
 with dar.open('rb') as stream:stream.seek(cam_receipt['cam_absolute_offset']);cam=stream.read(cam_receipt['cam_bytes'])
 if hashlib.sha256(cam).hexdigest()!=cam_receipt['cam_sha256']:raise ValueError('Current CAM source drift')
 numcut,numarea,numlerp=struct.unpack_from('<3B',cam,4);cutbase=16+64*numarea
 allcuts=[cam[cutbase+52*i+1] for i in range(numcut)];area_cuts=[cam[struct.unpack_from('<I',cam,16+16*i+12)[0]+1] for i in range(numarea)]
 if allcuts!=area_cuts or allcuts!=cam_receipt['gc_cut_numbers'] or 13 in allcuts or 14 in allcuts:raise ValueError('Current camera namespace differs from blocker')
 camera_namespace=dict(dar=pin(dar),receipt=pin(cam_receipt_path),cam_sha256=hashlib.sha256(cam).hexdigest(),num_cut=numcut,num_area=numarea,all_cut_numbers=allcuts,area_linked_cut_numbers=area_cuts,PS2_cut13_or14_present=False,normal_active_cut_trigger_mapping='UNRESOLVED_NO_DIRECT_ID_MATCH')
 out=dict(classification='READ_ONLY_SOURCE_GROUP_WORKLOAD_NOT_SELECTED_SAVINGS',source=SOURCE,inputs=used,migration_receipt=pin(migration),reader_sha256=hashlib.sha256(data).hexdigest(),group_id=30,camera_namespace=camera_namespace,independent_direct_offsets_equal=True,placements=rows,totals=dict(totals),materials=list(materials.values()),trigger='PORTED_SOURCE_CAM13_OR14_BUT_CURRENT_CAMERA_MAPPING_UNRESOLVED',runtime_admitted=False,actual_saved_corners=None,ms=None,new_rays=0,new_shadow_predicates=0,limitations=['Full authoredLOD0 placement counts, not camera-selected/SG/cull/clip work or savings.','Original source group30 has13 physical placements; common dynamic bridge allocates unique IDs only.','Current pinned GC CAM namespace has no cut13/14; original PS2 trigger and current equivalent need authentication.','Material rows are physical pass/cull/alpha descriptors; no actual residency/header/transparent-visibility acceptance.','No current-visit source/camera/owner lifecycle or private render gate is established.'])
 a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(report=pin(a.out),totals=out['totals'],parts=len(materials),passes=sorted({x['pass_'] for x in materials.values()}),vertex_alpha_parts=sum(x['vertex_alpha'] for x in materials.values()))))
if __name__=='__main__':main()
