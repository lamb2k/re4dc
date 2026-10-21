from pathlib import Path
import json,collections,math
D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');r=json.loads((D/'route-walk272/owned-window-current-stair-walk.json').read_text());es=r['events'];ss=[x for x in r['samples']if 'ray_yaw_error'in x];print('EVENTS',collections.Counter(k for e in es for k in e if k not in ['key','up','down','host_monotonic']));print('RAYBEST',[(s['frame'],round(s['ray_yaw_error'],4),round(s['ray_pitch_error'],4),round(s['ray_sphere_miss'],1),s.get('laser_target'),round(s['player_back_dot']),s.get('source_m3r'))for s in sorted(ss,key=lambda s:max(abs(s['ray_yaw_error']),abs(s['ray_pitch_error'])))[:12]]);print('FIRSTLAST',[(s['frame'],round(s['ray_yaw_error'],3),round(s['ray_pitch_error'],3),round(s['ray_sphere_miss']))for s in ss[:8]+ss[-8:]])
for e in es:
 if 'reviewed_dominant_axis_held_correction'in e:
  q=e['reviewed_dominant_axis_held_correction'];print('CORR',q['frame_interval'],q['keys'],q.get('fine_one_tick_then_actual_neutral'),[round(v,4)for v in q['initial_errors']],[round(v,4)for v in q['ended_errors']])
