"""Prepare exact current-R-g readback layout from actual nm and DWARF receipts; no execution."""
import argparse,hashlib,json,pathlib,re,subprocess
SOURCE='49ad20f9932d638ddb7becf5db6f86b92e0a76a2'
def sha(p):
 with pathlib.Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--elf',required=True);ap.add_argument('--tree',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();elf=pathlib.Path(a.elf);tree=pathlib.Path(a.tree);here=pathlib.Path(__file__).parent
 assert subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()==SOURCE
 assert not subprocess.check_output(['git','-C',str(tree),'status','--porcelain'],text=True).strip()
 research=json.loads((here/'layout-research.json').read_text());compact=json.loads((here/'dwarf-compact.json').read_text());actual=sha(elf)
 assert research['elf_sha256']==compact['elf_sha256']==actual,'ELF mismatch; re-extract DWARF for different arm/twin'
 nm=subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-nm','-C','-S','--defined-only',str(elf)],text=True);rows=[]
 for line in nm.splitlines():
  m=re.fullmatch(r'([0-9a-f]+) ([0-9a-f]+) ([bBdD]) (.+)',line)
  if m:rows.append({'address':int(m[1],16),'size':int(m[2],16),'storage':m[3],'name':m[4]})
 specs={'profile':('completed_render_profile',428),'completed':('completed_frame',192),'source_begin':('render_source_begin',112),'pG':('pG',4),'pPL':('pPL',4),'EmMgr':('EmMgr',56),'ObjMgr':('ObjMgr',56),'pvr':('pvr_state',520),'pending':('pvr_pending_decision',4),'flip':('pvr_flip_allowed',1),'manual':('pvr_manual_flip',1),'viewport':('re4dc_gxf_viewport',24),'projection':('re4dc_gxf_projection',28),'entries':('(anonymous namespace)::entries',0x18800),'loads':('(anonymous namespace)::loads',4),'submitted':('(anonymous namespace)::present_submitted',4),'resolved':('(anonymous namespace)::present_resolved',4),'failures':('(anonymous namespace)::present_failures',4),'steady_q':('(anonymous namespace)::q_n',4),'steady_watch':('(anonymous namespace)::watch',4),'ui_frame':('(anonymous namespace)::frame',4),'frame_ready':('(anonymous namespace)::frame_ready',1),'stream_scene':('(anonymous namespace)::stream_scene',1)}
 syms={}
 for key,(name,size) in specs.items():
  matches=[r for r in rows if r['size']==size and (r['name']==name or r['name']=='(anonymous namespace)::'+name)]
  assert len(matches)==1,(key,matches)
  syms[key]=matches[0]
 types={}
 for t in research['types']:
  name=t['name'] or 'pvr_state_t';types[name]={'size':int(t['size']),'members':{m['name']:int(m['offset']) for m in t['members'] if m['name'] and m['offset'] is not None}}
 dies={int(k,16):v for k,v in compact['dies'].items()}
 for root in compact['roots']:
  d=dies[int(root,16)];name=d.get('resolved_name','')
  if name not in {'cUnit','cCoord','cManager<cEm>','cManager<cObj>'}:continue
  fields={x['attrs'].get('DW_AT_name','').split('): ',1)[-1]:int(x['attrs']['DW_AT_data_member_location']) for x in dies.values() if x['parent']==d['offset'] and x['tag']=='DW_TAG_member' and 'DW_AT_data_member_location' in x['attrs']}
  new={'size':int(d['attrs']['DW_AT_byte_size']),'members':fields}
  assert name not in types or types[name]==new,(name,'conflicting DWARF')
  types[name]=new
 assert types['cUnit']['members']['be_flag']==4 and types['cUnit']['members']['pNext']==8
 paths=['src/game/main.cpp','src/game/main_sub.cpp','src/game/game.cpp','port/dreamcast/game/dbgwarp_bridge.cpp','port/dreamcast/game/ui_bridge.cpp','port/dreamcast/game/pace_present.cpp','port/dreamcast/game/platform/native_ui.cpp','port/dreamcast/game/platform/include/native_model.h','port/dreamcast/game/platform/include/native_render_profile.hpp','port/dreamcast/game/platform/include/native_actor.hpp','port/dreamcast/game/platform/native_actor.cpp','port/dreamcast/game/platform/native_actor_fast.cpp','port/dreamcast/game/platform/res_mode.cpp','include/cManager.h','include/model.h','include/global.h']
 kos=pathlib.Path('/root/work/kos-re4dc-d367');kp=['kernel/arch/dreamcast/hardware/pvr/pvr_irq.c','kernel/arch/dreamcast/hardware/pvr/pvr_internal.h']
 out={'source':SOURCE,'elf':str(elf),'elf_sha256':actual,'symbols':syms,'types':types,'source_pins':{str(tree/p):sha(tree/p) for p in paths},'kos_pins':{str(kos/p):sha(kos/p) for p in kp},'dwarf_receipts':{str(here/n):sha(here/n) for n in ['dwarf-compact.json','layout-research.json']},'phase_contract':{'freeze_tick':330,'live_begin_source_tick':329,'last_completed_source_tick':328,'proof':'Render_before/Render -> Frame_cnt++ -> TaskScheduler(gameMainLoop freeze) -> Render_done -> Render_swap. Refuse different observed relationship.'},'unproven_completed_bindings':['completed actor count/identity/pose roster (ACTOR_STATS_LEAN1/ACTOR_LOG0 synthesize actor counters as zero; aggregate work cannot prove actor0)','completed viewport/projection/jitter paired with source/frame (live GXF globals overwritten by next Render_before)','completed texture/upload owner table and presented-buffer generation tied to that completed UI frame']}
 out['backends']={k:{'path':str(p),'sha256':sha(p)} for k,p in {'owned':pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23/stat_owned_ram.py'),'decoder':pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/d367-harness-par/capture_ui_vram.py')}.items()}
 dest=pathlib.Path(a.output);dest.write_text(json.dumps(out,indent=2)+'\n');print('layout',dest,'sha256',sha(dest),'ELF',actual)
if __name__=='__main__':main()