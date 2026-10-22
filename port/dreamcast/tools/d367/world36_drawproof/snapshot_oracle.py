#!/usr/bin/env python3
"""Pure WORLD36 snapshot oracle. It never attaches, reads a process or writes RAM.

A CPU packet/cache header is not proof of emitted vertices, raster or chosenLOD.
"""
import struct
class Rejected(ValueError):pass
def need(ok,why):
 if not ok:raise Rejected(why)
def u(b,off):return struct.unpack_from('<I',b,off)[0]
def raw(s,name,n):
 b=bytes.fromhex(s[name]);need(len(b)==n,name+' extent');return b
def vram(a):return (a&0xff000000) in (0xa4000000,0xa5000000) and (a&0xffffff)<8*1024**2 and (a&7)==0

def ram(a,n):return 0x8c000000<=a and a+n<=0x8d000000

def decode(s,binding):
 need(s['ELF_sha256']==binding['ELF_sha256'],'wrong ELF lineage')
 need(binding['member_widths']['Entry']['valid']['bytes']==1 and binding['member_widths']['Package']['upload_complete_']['bytes']==1,'unbound bool widths')
 t=binding['types'];e=raw(s,'entry_before',t['Entry']['size']);need(e==raw(s,'entry_after',len(e)),'torn Entry')
 E=t['Entry']['members'];P=t['Package']['members'];H=t['Header']['members'];T=t['Texture']['members'];K=t['Key']['members']
 a=s['entry_address'];v=binding['variables']['entries'];need(v['address']<=a<v['address']+v['bytes'] and (a-v['address'])%len(e)==0,'wrong Entry array/CU/stride')
 key='%08x-%08x'%(u(e,E['key']+K['crc']),u(e,E['key']+K['fnv']));expect=next((r for r in binding['selected'] if r['key']==key),None);need(expect is not None,'not canonical WORLD36')
 need(e[E['valid']]==1,'invalid Entry')
 p=E['package'];header=raw(s,'header_before',48);texture=raw(s,'texture_before',96);ptr=raw(s,'pvr_table_before',8)
 need(all(ram(s[name+'_address'],n) for name,n in [('header',48),('texture',96),('pvr_table',8),('owns_texture',1)]),'metadata RAM range')
 for name,b in [('header',header),('texture',texture),('pvr_table',ptr)]:need(b==raw(s,name+'_after',len(b)),'torn '+name)
 need(s['header_address']==u(e,p+P['header_']),'header pointer chain')
 need(s['texture_address']==u(e,p+P['data_'])+u(header,H['texture_offset']),'descriptor pointer chain')
 need(s['pvr_table_address']==u(e,p+P['pvr_textures_']),'VRAM pointer chain')
 need(header.hex()==expect['header_hex'],'live header differs from canonical asset header')
 need(texture.hex()==expect['texture_hex'],'live descriptor differs from canonical asset descriptor')
 sampled,base=struct.unpack('<II',ptr);need(vram(sampled) and vram(base),'unqualified VRAM address')
 need(e[p+P['upload_complete_']]==1,'not uploaded')
 need(s['owns_texture_byte']==1 and s['owns_texture_address']==u(e,p+P['owns_texture_']),'not current texture owner')
 scene=s['scene_before'];need(scene==s['scene_after'],'torn scene tuple')
 rooms={int(r['room'].split('/')[2][1:],16) for r in expect['bindings']};need(scene['room_id'] in rooms,'key not bound to scene room')
 result={'evidence_level':'RESIDENT_DESCRIPTOR_FORMAT','key':key,'original_key':expect['original_key'],'canonical_package_sha256':expect['package_sha256'],'asset_identity_role':'EXPECTED source package; resident metadata is not an observed payload hash','expected_descriptor_sha256':expect['descriptor_sha256'],'expected_payload_sha256':expect['payload_sha256'],'observed_header_body_crc32':u(header,H['payload_crc32']),'logical':expect['logical'],'physical':expect['physical'],'native_format':u(texture,T['format']),'native_layout':u(texture,T['payload']),'mip_flag':bool(u(texture,T['flags'])&4),'sampled_VRAM_address':sampled,'owned_VRAM_base':base,'scene':scene,'render_path':'UNKNOWN: source-scoped world binding alone is not observed caller','actual_submitted_header':False,'actual_submitted_vertices':False,'draw_proof':False,'chosen_LOD':'UNAVAILABLE','phase_qualification':'External benchmark channel required; this decoder does not qualify completed-state phase.','coverage':'A captured resident record; absence is not proof of nonuse.'}
 if 'guard_before' not in s:return result
 g=s['guard_before'];need(g==s['guard_after'],'torn direct tuple')
 need(g['frame']==scene['ui_frame'] and g['frame']==u(e,E['frame']),'direct/source UI frame mismatch')
 need(g['direct_open']==1 and g['frame_ready']==1 and g['stream_scene']==1 and g['stream_aborted']==0,'direct frame not live')
 need(g['model_handle']==a and 0<=g['model_used']<g['model_pending']<=384,'direct packet bounds/owner')
 need(0x8c000000<=g['model_packets'] and g['model_packets']+g['model_pending']*32<=0x8d000000,'packet RAM range')
 need(s['packet_header_address']==g['model_packets']+g['model_used']*32,'packet pointer chain')
 packet=raw(s,'packet_header_before',32);need(packet==raw(s,'packet_header_after',32),'torn direct packet header')
 pcw,isp,tsp,tcw=struct.unpack_from('<4I',packet)
 need(pcw>>29==4 and pcw&8,'not textured polygon header')
 width,height=8<<((tsp>>3)&7),8<<(tsp&7);need([width,height]==expect['physical'],'physical TSP size mismatch')
 need(tcw&0xffe00000==0xc8000000,'TCW must encode mipmapped VQ RGB565')
 need(((tcw&0x1fffff)<<3)==(sampled&0x7fffff),'TCW points elsewhere')
 need(((tsp>>15)&3)==0,'UV clamp changed from native repeat')
 actual_list=(pcw>>24)&7;allowed={0 if r['render_pass']==0 else 4 if r['render_pass']==1 else 2 for r in expect['bindings'] if int(r['room'].split('/')[2][1:],16)==scene['room_id']};need(actual_list in allowed,'list/pass incompatible with world binding')
 result.update(evidence_level='COHERENT_CPU_DIRECT_PACKET_HEADER',packet_header_hex=packet.hex(),TSP=tsp,TCW=tcw,TCW_mipmap_bit=True,TCW_VQ_bit=True,TCW_texture_address_bytes=(tcw&0x1fffff)<<3,list=actual_list,filter_mode=(tsp>>13)&3,mip_bias=(tsp>>8)&15,render_path='CPU direct packet joined to WORLD36 scoped Entry; exact submitting caller/part not observed',limits=['Direct-open is a shared mutable latch; model_packets is CPU staging, not an immutable post-flush event.','Header/cached state alone does not prove vertices, accepted TA work, raster, presentation or chosen LOD.','To promote evidence, add a reviewed per-world-window after-submit marker with stable sequence/key/frame/header/vertexcount; no hook exists in this tool.'])
 return result
