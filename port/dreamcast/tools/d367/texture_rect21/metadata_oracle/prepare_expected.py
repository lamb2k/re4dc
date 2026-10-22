from pathlib import Path
import hashlib,json,struct,zlib,collections,re
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/metadata-oracle-f42-01')
R=E.parent;T=Path('/root/probe/codex-texture-rect21');files=json.loads((R/'image-plan-04/baseline-file-identities.json').read_text())['files']
sha=lambda b:hashlib.sha256(b).hexdigest()
def fnv(b):
 h=2166136261
 for x in b:h=((h^x)*16777619)&0xffffffff
 return h
def asset(name):
 r=files[name]
 with(R/'standalone-B-01/gdemu/track03.iso').open('rb')as f:f.seek((r['extent']-45000)*2048);b=f.read(r['bytes'])
 assert sha(b)==r['sha256'],name
 return b
def ident(b):return dict(bytes=len(b),sha256=sha(b),crc32=zlib.crc32(b)&0xffffffff,fnv_bytes=fnv(b))
rooms={}
for room in('r100','r101','r103'):
 pre='/dc/native/'+room+'/';bw=asset(pre+'ps2-world.r4pw');mesh=asset(pre+'ps2-world.re4mesh');ids=asset(pre+'ps2-world.ids');tc=asset(pre+'ps2-world.r4tc');rc=asset(pre+'room.r4rc')
 candidate=Path('/root/re4data/private/texture-world-next21-r101-scoped9-v2-20261021/dc/native/r101/ps2-world.r4pw')if room=='r101'else Path('/root/re4data/private/texture-rect21-current948-scoped17-20261021/dc/native')/room/'ps2-world.r4pw'
 cw=candidate.read_bytes();bh=struct.unpack_from('<4s7I',bw);ch=struct.unpack_from('<4s7I',cw);mh=struct.unpack_from('<4s19I',mesh)
 assert bh[:5]+bh[6:]==ch[:5]+ch[6:]and bw[32+16*bh[3]:]==cw[32+16*ch[3]:]
 assert zlib.crc32(bw[32:])&0xffffffff==bh[5]and zlib.crc32(cw[32:])&0xffffffff==ch[5]
 ih=struct.unpack_from('<4s3I',ids);th=struct.unpack_from('<4s5I',tc);cls=tc[24:24+bh[3]]
 assert ih==(b'R4ID',1,bh[2],bh[5])and th[:5]==(b'R4TC',1,1,bh[3],bh[5])and th[5]==zlib.crc32(cls)&0xffffffff
 idbody=ids[16:16+bh[2]];freq=collections.Counter(idbody);unique=[i for i in range(250)if freq[i]==1]
 slotmap=[unique.index(i)if i in unique else 255 for i in range(250)]
 parts=list(struct.iter_unpack('<IIHH4B',bw[32:32+16*bh[3]]));placements=list(struct.iter_unpack('<HH12f',bw[32+16*bh[3]:]))
 meshes=[struct.unpack_from('<HBBHHIII12f',mesh,mh[10]+68*i)for i in range(mh[4])]
 masks=[];raw_masks=[]
 for place in placements:
  m=meshes[place[0]];mask=0;raw=0
  for j in range(m[6],m[6]+m[7]):
   p=parts[j];mask|=1<<p[4];raw|=1<<p[4]
   if p[4]==2 and not(p[7]&1):
    extra=0 if cls[j]in(3,4)else 1 if cls[j]in(6,7)else 2
    if extra<2:mask|=1<<extra
  masks.append(mask);raw_masks.append(raw)
 sections={}
 for at in range(64,64+32*struct.unpack_from('<H',rc,12)[0],32):
  tag,ver,flags,off,size=struct.unpack_from('<4sHHII',rc,at);tag=tag.rstrip(b'\0').decode();sections[tag]=dict(version=ver,flags=flags,offset=off,bytes=size,sha256=sha(rc[off:off+size]))
 occ=sections['OCCL'];body=rc[occ['offset']:occ['offset']+occ['bytes']];ocrc=struct.unpack_from('<I',body,12)[0]
 assert occ['version']==2 and ocrc==bh[5]
 r=dict(room=int(room[1:],16),mesh=ident(mesh)|dict(body_crc=mh[3],meshes=mh[4],parts=mh[5],meshlets=mh[6],vertices=mh[7]),
        source_crc=bh[5],world_original=ident(bw)|dict(body_crc=bh[5]),world_candidate=ident(cw)|dict(body_crc=ch[5]),
        placements=bh[2],ids=ident(ids)|dict(count=ih[2],expected_source_crc=ih[3],body=ident(idbody),unique_slots=len(unique),slot_of=slotmap,unique_ids=unique),
        classes=ident(tc)|dict(parts=th[3],classifier=th[2],expected_source_crc=th[4],class_body=ident(cls),histogram=dict(sorted(collections.Counter(cls).items()))),
        pass_mask=ident(bytes(masks))|dict(values=masks),pass_mask_after_movie=ident(bytes(raw_masks))|dict(values=raw_masks),
        room_r4rc=ident(rc),OCCL=occ|dict(source_crc=ocrc,occluders=struct.unpack_from('<H',body,6)[0]),
        physical_profile_crc='actual loaded world bodyCRC, never canonical sourceCRC',
        expected_trans_policy=3)
 if room=='r100':
  cell=asset(pre+'interior.cell');h=struct.unpack_from('<8I',cell)
  assert h[:7]==(0x314c4350,0x100,mh[3],bh[5],len(mesh),170,1186)
  r['PCL']=ident(cell)|dict(mesh_crc=h[2],source_crc=h[3],mesh_bytes=h[4],cells=h[5],portals=h[6],cell_bytes=33256,frustum_bytes_two_states=2*24*108)
  r['movie_capture_actual']=dict(mesh=len(mesh),side=len(cw),mesh_crc=zlib.crc32(mesh)&0xffffffff,mesh_fnv=fnv(mesh),side_crc=zlib.crc32(cw)&0xffffffff,side_fnv=fnv(cw))
 else:r['PCL']=dict(expected='not this package; no r100 PCL load for this room')
 sgname=pre+'ps2-world.r4sg'
 if sgname in files:
  sg=asset(sgname);h=struct.unpack_from('<4s7I',sg)
  assert h[:3]==(b'R4SG',1,mh[6])and h[4:7]==(mh[3],len(mesh),bh[5])and h[7]==zlib.crc32(sg[32:])&0xffffffff
  r['R4SG']=ident(sg)|dict(meshlets=h[2],per_meshlet_groups=h[3],mesh_crc=h[4],mesh_bytes=h[5],source_crc=h[6],record_crc=h[7],record_bytes=len(sg)-32)
 else:r['R4SG']=dict(expected='absent',groups=0)
 r['expected_open_log_lines']=[
  f'PS2DYN room={room[1:]} ids=ok placements={bh[2]} unique={len(unique)}',
  f'trans: room={room[1:]} policy=3 classes=ok parts={bh[3]}',
  f'ENEMYVIS {room} ok occluders={r["OCCL"]["occluders"]} crc={bh[5]:08x}',
  f'PCCULL cell room={room[1:]} mesh_crc={mh[3]:08x} sidecar_crc=<ACTUAL world bodyCRC> '+('adopted cells=170 portals=1186 mode=1'if room=='r100'else'not this package cells=170 portals=1186 mode=1'),
  f'PS2SG room={room[1:]} groups='+('ok'if sgname in files else'absent'),
  f'PS2MESH open bytes=<allocation> version=3 meshes={mh[4]} parts={mh[5]} meshlets={mh[6]} vertices={mh[7]} placements={bh[2]}']
 rooms[room]=r
idx=asset('/dc/native/trclass.idx');n=struct.unpack_from('<I',idx,4)[0];idxrooms=struct.unpack_from('<'+'H'*n,idx,8)
assert all(r['room']in idxrooms for r in rooms.values())
result=dict(source='845abb1f4ad3a2721d17f64899b6dc59d4bce66c',ELF_sha256='f42dbb7261ff93c23dbc8f0dfb810a77cd64ad460472239e58a7cb6fa1404e00',programme_sha256='4ef617a1888ec2fb48c45aae789b8cb21c2c6086f36b1a5d2efe56ceebadb4f9',status='STATIC_HOLD_CRC_CONVENTION_REPAIR_REQUIRED_NOT_GUEST_RESULT',rooms=rooms,trclass_index=ident(idx)|dict(count=n,rooms_present=[r['room']for r in rooms.values()]),
 scenarios={'M0':dict(r100='world_original',r101='world_original',r103='world_original'),'965':dict(r100='world_candidate',r101='world_original',r103='world_candidate'),'994':dict(r100='world_candidate',r101='world_candidate',r103='world_candidate')},
 phases=dict(post_open='IDs/classes/pass-mask/SGlive; PCL st.ok true+blockloaded r100 only; OCCL source anchor matches policyCRC',
 movie_borrowed='Do not read retained world pointers. No comparison gate.',
 after_r100_movie_restore='Physical CRC/FNV must equal captured actual files; IDs retained; trans closes and cls=null/nparts0/room~0 until nextopen by baseline design. PCL can reload afterlend; require settled loaded before comparison.'),
 limits=['ENEMYVIS ok is metadata load only, not world_intact','OCCL eligibility does not prove actual hidden draw/raster/unchanged source placement state','No all-key draw/performance/VRAM/release/hardware claim'])
(E/'expected-room-policy.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:dict(unique=v['ids']['unique_slots'],classes=v['classes']['histogram'],occluders=v['OCCL']['occluders'],sg=v['R4SG'])for k,v in rooms.items()}))
