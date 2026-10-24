from pathlib import Path
import hashlib,json,struct,subprocess,zlib,bisect,time,os
L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/worldemit-ui-pair23')
R=Path('/root/work/lanes/stat-bytes23-takeover-scratch/release')
P=R/'tree/dc/tex.pak'
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/49ad20f9')
launch=E/'captures/B-mendez-r1/current-gate-launch.json';lb=launch.read_bytes();gate=json.loads(lb)
T=Path('/root/probe/worldemit-ui-pair23');SOURCE='49ad20f9932d638ddb7becf5db6f86b92e0a76a2'
key=(0x7d4e1e92,0x052bdc2e)
sha=lambda b:hashlib.sha256(b).hexdigest()
start=time.monotonic()
with P.open('rb') as f:
 before=os.fstat(f.fileno());head=f.read(2048)
 if head[:8]!=b'RE4PAK1\0':raise ValueError('bad pack magic')
 ver,count,index_at,data_at,crc=struct.unpack_from('<5I',head,8)
 if ver!=1 or not 1<=count<=8192 or index_at!=2048:raise ValueError('bad pack header')
 nsec=(count*16+2047)//2048;index=f.read(nsec*2048)
 if len(index)!=nsec*2048 or zlib.crc32(index)&0xffffffff!=crc:raise ValueError('bad index CRC')
 if data_at<2048+len(index) or data_at%2048 or data_at>before.st_size:raise ValueError('bad data offset')
 rows=[struct.unpack_from('<4I',index,16*i) for i in range(count)];keys=[row[:2] for row in rows]
 for i,(a,b,o,n) in enumerate(rows):
  if i and not keys[i-1]<(a,b):raise ValueError('key order')
  if not n or o%2048 or o<data_at or o+n>before.st_size:raise ValueError('bad extent')
 h=hashlib.sha256();h.update(head);h.update(index)
 while True:
  chunk=f.read(1024*1024)
  if not chunk:break
  h.update(chunk)
 after=os.fstat(f.fileno())
 stamp=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 if stamp(before)!=stamp(after) or stamp(P.stat())!=stamp(after):raise ValueError('pack changed')
digest=h.hexdigest()
manifest=R/'manifest.json';mb=manifest.read_bytes();m=json.loads(mb)
if sha(mb)!=gate['unit']['release_manifest_sha256']:raise ValueError('release manifest launch mismatch')
if m['dc/tex.pak']!={'sha256':digest,'size':before.st_size}:raise ValueError('release pack member mismatch')
baseman=E/'_discs/B-t/base-manifest.json';bm=baseman.read_bytes()
if sha(bm)!=gate['staged']['base_manifest_sha256'] or json.loads(bm)['dc/tex.pak']!=m['dc/tex.pak']:raise ValueError('B-t pack manifest mismatch')
first=[keys[128*s] for s in range(nsec)];s=max(0,bisect.bisect_right(first,key)-1);part=keys[128*s:min(128*(s+1),count)]
lo=0;hi=len(part);trace=[];found=False
while lo<hi:
 mid=(lo+hi)//2;k=part[mid];trace.append(dict(local_index=mid,key='%08x-%08x'%k))
 if k==key:found=True;break
 if k<key:lo=mid+1
 else:hi=mid
if found or key in keys:raise ValueError('candidate key already in pack')
sources={}
for p in ['port/dreamcast/game/platform/include/texpack_index.inc','port/dreamcast/game/platform/native_ui.cpp']:
 b=subprocess.check_output(['git','show',SOURCE+':'+p],cwd=T);sources[p]=dict(sha256=sha(b))
idx=bisect.bisect_left(keys,key)
report=dict(schema='MENDEZ_PAIR_ACTUAL_PACK_ABSENCE_V1',status='ABSENT_VALIDATED_INDEX_NO_SHADOW',
 source=SOURCE,lookup_sources=sources,pack=dict(path=str(P),bytes=before.st_size,sha256=digest,count=count,
 index_sectors=nsec,index_crc32='%08x'%crc,index_sha256=sha(index),stat_before=stamp(before),stat_after=stamp(after)),
 query='7d4e1e92-052bdc2e',found=False,sector=s,sector_first='%08x-%08x'%first[s],search_trace=trace,
 adjacent=dict(previous='%08x-%08x'%keys[idx-1] if idx else None,next='%08x-%08x'%keys[idx] if idx<count else None),
 binding=dict(launch=str(launch),launch_sha256=sha(lb),release_manifest=str(manifest),release_manifest_sha256=sha(mb),
 B_t_base_manifest=str(baseman),B_t_base_manifest_sha256=sha(bm)),
 algorithm='Frozen49ad texpack::find chooses greatest first-sector key <= query, then binary-searches <=128 sorted CRC/FNV pairs. kNotInPack reaches loose path; kFound shadows loose; kError refuses.',
 seconds=time.monotonic()-start,scope='Read-only actual pack header/index and one full streamed SHA256; no payload copies, stage, SDK, guest or gate acceptance')
(L/'PACK-ABSENCE.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],pack_sha256=digest,bytes=before.st_size,count=count,seconds=report['seconds'],receipt_sha256=sha((L/'PACK-ABSENCE.json').read_bytes())),indent=2))
