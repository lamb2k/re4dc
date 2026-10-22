"""New69f selected1004 descriptor reader; no guest attach or gameplay writes."""
import struct
from observer import Typed,Invalid,u32,key,vram_pointer
class TypedCanonical(Typed):
 def __init__(self,read,plan):
  super().__init__(read,{**plan,'selected':[]});self.expected={r['key']:r for r in plan['selected']}
  if len(self.expected)!=1004:raise Invalid('exact canonical1004 metadata required')
  self.expected.update({r['key']:r for r in plan.get('supplemental_originals',[])})
  self.world_pairs=plan.get('world_original_map',[]);self.selected={k:(i,'canonical')for i,k in enumerate(self.expected)}
 def local(self,n):
  name='__ZN12_GLOBAL__N_1L'+str(len(n))+n+'E';r=self.sy[name]
  if r['size']not in (1,4):raise Invalid('local scalar type width')
  b=self.read(r['address'],r['size']);return b[0]if r['size']==1 else u32(b)
 @staticmethod
 def expected_texture(row):
  n=row['native_descriptor']
  if 'physical'in n:return {'width':n['physical'][0],'height':n['physical'][1],'format':n['native_format'],'flags':n['flags'],'payload':n['payload'],'data_size':n['payload_bytes']}
  return {('reserved_0'if k=='reserved'else k):v for k,v in n.items()}
 def table(self):
  raw=self.read(self.entries,448*self.stride);rows=[];valid=0;alloc=set();unknown=0
  P=self.t['native_ui']['types']['Package']['members'];H=self.t['native_ui']['types']['Header']['members'];T=self.t['native_ui']['types']['Texture']['members']
  for i in range(448):
   b=raw[i*self.stride:(i+1)*self.stride]
   if b[76]!=1:continue
   valid+=1;k=key(b,64)
   if k not in self.expected:unknown+=1;continue
   expected=self.expected[k];address=self.entries+i*self.stride;row={'slot':i,'address':address,'key':k,'category':expected['category'],'entry_frame':u32(b,72),'cached_model_header':b[96:128].hex(),'model_header_key':u32(b,128)}
   pkg={n:(b[o]if n in ('streamed_','payload_released_','upload_complete_')else u32(b,o))for n,o in P.items()};row['package']=pkg
   try:
    h=self.read(pkg['header_'],48);hdr={n:(h[:8].hex()if n=='magic'else u32(h,o))for n,o in H.items()};row['header']=hdr
    if h[:8]!=b'RE4DCTX\0'or hdr['texture_count']!=1 or hdr['texture_stride']!=96:raise Invalid('selected magic/descriptor count/stride')
    descriptor_address=pkg['data_']+hdr['texture_offset'];t=self.read(descriptor_address,96);tex={n:u32(t,o)for n,o in T.items()if n!='material'};tex['material']=t[:64].split(b'\0')[0].decode('ascii','replace');row['texture']=tex;wanted=self.expected_texture(expected)
    row['canonical_descriptor_match']=hdr['payload_crc32']==expected['canonical_body_crc32']and t.hex()==expected['native_descriptor_hex']and all(tex.get(n)==v for n,v in wanted.items());row['candidate_descriptor_match']=row['canonical_descriptor_match']
    ptrs=self.read(pkg['pvr_textures_'],8);sampled,base=struct.unpack('<II',ptrs);owns=self.read(pkg['owns_texture_'],1)[0];row.update(pvr_sampled=sampled,pvr_allocation_base=base,owns_texture=owns,texture_address=descriptor_address)
    row['vram_pointers_valid']=vram_pointer(sampled)and vram_pointer(base)
    if row['vram_pointers_valid']:alloc.add(base&0xffffff)
    row['admission']='canonical_descriptor_uploaded'if row['canonical_descriptor_match']and pkg['upload_complete_']==1 and row['vram_pointers_valid']else 'UNKNOWN'
    if b!=self.read(address,self.stride)or h!=self.read(pkg['header_'],48)or t!=self.read(descriptor_address,96)or ptrs!=self.read(pkg['pvr_textures_'],8)or owns!=self.read(pkg['owns_texture_'],1)[0]:raise Invalid('torn selected entry/descriptor/owner')
   except (Invalid,struct.error)as exc:row['admission']='UNKNOWN';row['reason']=str(exc)
   rows.append(row)
  live={r['key']:r for r in rows if r['admission']=='canonical_descriptor_uploaded'};both=[{**p,'original_base':live[p['original_key']]['pvr_allocation_base'],'scoped_base':live[p['scoped_key']]['pvr_allocation_base'],'original_owns':live[p['original_key']]['owns_texture'],'scoped_owns':live[p['scoped_key']]['owns_texture']}for p in self.world_pairs if p['original_key']in live and p['scoped_key']in live];known={}
  for r in live.values():
   t=r['texture']
   if r['owns_texture']==1 and t['format']==0 and t['payload']==2:known[r['pvr_allocation_base']]=max(known.get(r['pvr_allocation_base'],0),t['data_size'])
  return {'valid_slots':valid,'slot_capacity':448,'selected':rows,'unselected_valid_slots':unknown,'unique_selected_vram_allocation_bases':sorted(alloc),'co_resident_world_pairs':both,'known_owned_VQ_payload_bytes_minimum':sum(known.values()),'known_owned_VQ_rounded_request_minimum':sum((n+31)//32*32 for n in known.values()),'allocation_bytes':'Selected VQ knownrequestlowerbound only; not fullallocator extent/highwater/netVRAMsaving. PAL/other formats and unselected allocations not quantified.','draw_proof':False,'chosen_LOD':'UNAVAILABLE'}
 def witness(self):
  names=['frame','direct_open','model_handle','model_used','model_pending','model_packets','frame_ready','stream_scene','stream_aborted']
  def guard():return {n:self.local(n)for n in names}
  def scene():
   g=self.scalar('_pG');G=self.t['scene']['types']['GlobalWork']['members'];return {'source_pointer':g,'source_frame':u32(self.read(g+G['Frame_cnt'],4)),'room_id':struct.unpack('<H',self.read(g+G['room_id'],2))[0],'ui_frame':self.local('frame')}
  a=guard()
  if not a['direct_open']:return None
  if a['frame_ready']!=1 or a['stream_scene']!=1 or a['stream_aborted']:raise Invalid('direct packet phase unsuitable')
  handle=a['model_handle'];used=a['model_used'];pending=a['model_pending'];packets=a['model_packets']
  if not self.entries<=handle<self.entries+448*self.stride or(handle-self.entries)%self.stride or not 0<=used<pending<=384:raise Invalid('direct packet typedbounds')
  before=scene();e=self.read(handle,224);k=key(e,64)
  if k not in self.expected:return None
  if e[76]!=1 or u32(e,72)!=a['frame']:raise Invalid('direct entry frame/key not current')
  P=self.t['native_ui']['types']['Package']['members'];pkg={n:u32(e,P[n])for n in ['header_','data_','pvr_textures_','owns_texture_']};h=self.read(pkg['header_'],48);H=self.t['native_ui']['types']['Header']['members']
  if h[:8]!=b'RE4DCTX\0'or u32(h,H['texture_count'])!=1 or u32(h,H['texture_stride'])!=96:raise Invalid('direct magic/descriptor count/stride')
  ta=pkg['data_']+u32(h,H['texture_offset']);t=self.read(ta,96);pv=self.read(pkg['pvr_textures_'],8);own=self.read(pkg['owns_texture_'],1)[0];pa=packets+used*32;packet=self.read(pa,32)
  ee=self.read(handle,224);hh=self.read(pkg['header_'],48);tt=self.read(ta,96);pp=self.read(pkg['pvr_textures_'],8);oo=self.read(pkg['owns_texture_'],1)[0];after=scene();aa=guard()
  if a!=aa or before!=after or e!=ee or h!=hh or t!=tt or pv!=pp or own!=oo or packet!=self.read(pa,32):raise Invalid('incoherent direct packet snapshot')
  snapshot={'ELF_sha256':'69f2e7db588f515f4e6a67455d627a74fc17132d5ca20a591db4e0f15deedcae','entry_address':handle,'entry_before':e.hex(),'entry_after':ee.hex(),'header_address':pkg['header_'],'header_before':h.hex(),'header_after':hh.hex(),'texture_address':ta,'texture_before':t.hex(),'texture_after':tt.hex(),'pvr_table_address':pkg['pvr_textures_'],'pvr_table_before':pv.hex(),'pvr_table_after':pp.hex(),'owns_texture_byte':own,'owns_texture_address':pkg['owns_texture_'],'scene_before':before,'scene_after':after,'guard_before':a,'guard_after':aa,'packet_header_address':pa,'packet_header_before':packet.hex(),'packet_header_after':packet.hex()}
  match=u32(h,H['payload_crc32'])==self.expected[k]['canonical_body_crc32']and t.hex()==self.expected[k]['native_descriptor_hex']
  return {'key':k,'ui_frame':a['frame'],'source_frame':before['source_frame'],'canonical_descriptor_match':match,'snapshot':snapshot,'evidence_class':'COHERENT_CPU_DIRECT_PACKET_HEADER','submitted_header':False,'vertices':False,'draw':False,'chosen_LOD':'UNAVAILABLE','scope':'Stable CPU packet/key/descriptors only; noactualTA/vertices/raster/chosenLOD or completed-pose correspondence proof'}
