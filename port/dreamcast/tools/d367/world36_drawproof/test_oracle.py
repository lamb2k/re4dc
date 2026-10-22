#!/usr/bin/env python3
from pathlib import Path
import copy,json,struct,sys
from snapshot_oracle import decode,Rejected

def test(binding):
 total=0;negatives=0
 def word(b,o,v):struct.pack_into('<I',b,o,v)
 for row in binding['selected']:
  E=binding['types']['Entry']['members'];P=binding['types']['Package']['members'];K=binding['types']['Key']['members'];H=binding['types']['Header']['members'];entry=bytearray(224);address=binding['variables']['entries']['address'];frame=100;hp=0x8c800000;data=hp;ptrs=0x8c810000;owns=0x8c820000;vram=0xa4100000
  for field,value in [('header_',hp),('data_',data),('pvr_textures_',ptrs),('owns_texture_',owns)]:word(entry,E['package']+P[field],value)
  entry[E['package']+P['upload_complete_']]=1;entry[E['valid']]=1;word(entry,E['frame'],frame);c,f=[int(v,16) for v in row['key'].split('-')];word(entry,E['key']+K['crc'],c);word(entry,E['key']+K['fnv'],f)
  room=int(row['bindings'][0]['room'].split('/')[2][1:],16);scene={'room_id':room,'source_frame':103,'ui_frame':frame}
  s={'ELF_sha256':binding['ELF_sha256'],'entry_address':address,'entry_before':entry.hex(),'entry_after':entry.hex(),'header_address':hp,'header_before':row['header_hex'],'header_after':row['header_hex'],'texture_address':data+48,'texture_before':row['texture_hex'],'texture_after':row['texture_hex'],'pvr_table_address':ptrs,'pvr_table_before':struct.pack('<II',vram,vram).hex(),'pvr_table_after':struct.pack('<II',vram,vram).hex(),'owns_texture_byte':1,'owns_texture_address':owns,'scene_before':scene,'scene_after':dict(scene)}
  out=decode(s,binding);assert out['evidence_level']=='RESIDENT_DESCRIPTOR_FORMAT' and not out['draw_proof'];total+=1
  pass_=row['bindings'][0]['render_pass'];list_=0 if pass_==0 else 4 if pass_==1 else 2;pcw=0x80840008|(list_<<24);width,height=row['physical'];tsp=((width.bit_length()-4)<<3)|(height.bit_length()-4)|(1<<13);tcw=0xc8000000|((vram&0x7fffff)>>3);packet=struct.pack('<8I',pcw,0,tsp,tcw,0,0,0,0)
  guard={'frame':frame,'direct_open':1,'model_handle':address,'model_used':0,'model_pending':1,'model_packets':0x8c900000,'frame_ready':1,'stream_scene':1,'stream_aborted':0};s.update(guard_before=guard,guard_after=dict(guard),packet_header_address=guard['model_packets'],packet_header_before=packet.hex(),packet_header_after=packet.hex())
  out=decode(s,binding);assert out['evidence_level']=='COHERENT_CPU_DIRECT_PACKET_HEADER' and out['TCW_mipmap_bit'] and not out['draw_proof'] and not out['actual_submitted_header'] and out['chosen_LOD']=='UNAVAILABLE';total+=1
  cases=[]
  def add(label,fn):x=copy.deepcopy(s);fn(x);cases.append((label,x))
  add('wrongELF',lambda x:x.update(ELF_sha256='0'*64));add('stride',lambda x:x.update(entry_address=address+1));add('owner',lambda x:x.update(owns_texture_byte=0));add('headerchain',lambda x:x.update(header_address=hp+4));add('VRAMchain',lambda x:x.update(pvr_table_address=ptrs+4));add('scene',lambda x:x['scene_after'].update(source_frame=104));add('wrongroom',lambda x:(x['scene_before'].update(room_id=0x200),x['scene_after'].update(room_id=0x200)));add('directtuple',lambda x:x['guard_after'].update(model_used=1));add('framenotlive',lambda x:(x['guard_before'].update(stream_aborted=1),x['guard_after'].update(stream_aborted=1)));add('headertear',lambda x:x.update(packet_header_after=('00'+packet.hex()[2:])));add('packetptr',lambda x:x.update(packet_header_address=guard['model_packets']+32))
  add('metadataRAM',lambda x:x.update(owns_texture_address=0))
  for name,index in [('header',36),('texture',84)]:
   bad=bytearray.fromhex(s[name+'_before']);bad[index]^=1;bad=bad.hex();add(name+'canonical',lambda x,name=name,bad=bad:x.update({name+'_before':bad,name+'_after':bad}))
  for label,offset,mask in [('TCWmip',12,1<<31),('TCWVQ',12,1<<30),('TCWaddress',12,1),('TSPsize',8,1),('TSPclamp',8,1<<15),('PCWtype',0,1<<29)]:
   b=bytearray(packet);word(b,offset,struct.unpack_from('<I',b,offset)[0]^mask);bad=b.hex();add(label,lambda x,bad=bad:x.update(packet_header_before=bad,packet_header_after=bad))
  for label,x in cases:
   try:decode(x,binding)
   except Rejected:negatives+=1
   else:raise AssertionError('accepted '+label)
  # A cache/header snapshot without a live direct tuple stays resident only.
  x=copy.deepcopy(s);del x['guard_before'];del x['guard_after'];assert decode(x,binding)['evidence_level']=='RESIDENT_DESCRIPTOR_FORMAT';total+=1
 return {'synthetic_positive_cases':total,'synthetic_rejections':negatives,'keys':36,'all_header_observations_keep_draw_false':True,'chosen_LOD_never_inferred':True,'guest_observations':0}
if __name__=='__main__':
 binding=json.loads(Path(sys.argv[1]).read_text());result=test(binding);Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
