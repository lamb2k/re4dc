"""Source-log census contract only; cannot certify a programme or cuts."""
import re
from actor_log import EvidenceFailure,MissingTelemetry,clean,timing_rows,window,require
LATE=re.compile(r'^warp: late 0x20 open at t=(\d+) room=119 \(1=world20px 2=actor8px 4=nodraw 8=cap 10=leon-source\)\r?$',re.M)
GOTO=re.compile(r'^warp: goto 0 at room frame 300 pl=112950,2298,19750 vbl=(\d+) wall_ms=(\d+)\r?$',re.M)
END=re.compile(r'^\[end: head=(\d+) stage=(None|\d+) overruns=(\d+)\]\r?$',re.M)
DEADLINE=re.compile(r'^\[capture stop reason=([^ ]+) elapsed=([0-9]+\.[0-9]{3})\]\r?$',re.M)

def census(result,text):
 clean(text)
 require(result.get('status')=='RUN_COMPLETE'and result.get('emu')=='console'and result.get('seconds')==54 and not result.get('errors'),'clean exact54 console census required')
 require('stopped'not in result and type(result.get('reader_exit'))is int and result['reader_exit']==0 and 'early_emulator_exit'not in result and not result.get('checkpoint_close_timeout'),'natural reader_exit0; no early goal/emulator exit')
 require(type(result.get('elapsed_s'))in(int,float)and 54<=result['elapsed_s']<=59.5,'original natural reader/closure bounds required')
 ends=list(END.finditer(text));stops=list(DEADLINE.finditer(text))
 require(len(ends)==len(stops)==1 and ends[0][3]=='0'and stops[0][1]=='deadline'and 54<=float(stops[0][2])<=59.5 and ends[0].end()<stops[0].start(),'full reader deadline/zero overruns required')
 require(re.findall(r'^warp: room enter ([0-9a-f]{3}) \(#\d+\)',text,re.M)==['119'],'one cold r119 entry required')
 require(not re.search(r'^warp: (?:still|frozen)',text,re.M),'census has no finite hold/freeze/passive attempt')
 moves=list(GOTO.finditer(text));late=list(LATE.finditer(text))
 require(len(moves)==len(late)==1 and len(re.findall(r'^warp: goto ',text,re.M))==1,'exact single candidate-A goto and census late marker required')
 require(int(late[0][1])>=539 and moves[0].end()<late[0].start(),'observed late global tick must be at/after539 and after candidate goto')
 starts=list(re.finditer(r'^AV23WINDOW ',text,re.M))
 require(len(starts)==2 and late[0].end()<starts[0].start()and starts[-1].end()<ends[0].start(),'one window must start after late and complete inside original reader output')
 proof=window(text,1);a=proof['actor_totals'];w=proof['work_totals']
 proof['clock_interpretation']['goto']='Source wp.room_frames room-poll clock. Goto stamp VI/wall fields are separate; no PAD/global conversion inferred.'
 require(all(a[key]>0 for key in('query','sections','bound','wall'))and all(w[key]>0 for key in('groups','world_ok','metadata_checks','metadata_bytes')),'meaningful census needs positive actual bounds/groups/current world receipts/metadata')
 require(a['skip']==a['tri']==0,'census cannot skip positions/triangles')
 require(any(r['fields'].get('vopq',{}).get('max',0)>0 for r in proof['PT_game_tick_samples']),'positive actual WORLD_METER contribution required')
 potential=a['hidden']>0 and a['would']>0
 return dict(status='SOURCE_CENSUS_LOG_CONTRACT_COMPLETE_PENDING_PROGRAMME_BINDING',selected_mode=1,restored_mode=0,workspace_binds=600,completion_flush_observed=True,natural_reader_deadline_observed=True,late_open_observed_global_tick=int(late[0][1]),start_workspace_serial=proof['window_events'][0]['workspace_serial'],end_workspace_serial=proof['window_events'][1]['workspace_serial'],candidate_goto=dict(room_poll_frame=300,VI_retrace=int(moves[0][1]),wall_ms=int(moves[0][2]),global_game_tick=None,PAD_read_count=None),actor_totals=a,work_totals=w,raw_window=proof,alive_rows=re.findall(r'^warp: (?:alive|alivelist)[^\n]*$',text,re.M),positive_potential_observed=potential,positive_potential_required_before_mode2=True,mode2_ready=False,actual_cut_acceptance=False,pixel_parity=False,geometry_accepted=False,memory_or_hardware_accepted=False,whole_frame_gain=False,programme_binding='PENDING',runtime_qualified=False,actor_attribution='Aggregate source-qualified cohort only. No per-owner2b attribution from AV23 totals or raw alive rows.',time_scope='Completion is present before the unchanged reader terminal deadline marker. No invented per-line host timestamp or workspace-to-game-tick join. No completion grace after reader expiry.',potential_scope='Hidden/would in mode1 are potential only. Positive potential alone cannot admit mode2; paired pixels and all guarded scene cases remain separate.')
