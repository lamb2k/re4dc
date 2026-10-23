"""Write three private, matching r119 controls; no staging or gameplay edits.
The caller must supply a global late tick observed after camera settlement.
Goto uses room PAD tick, so it has a separate explicit argument.
"""
from pathlib import Path
import argparse,json
a=argparse.ArgumentParser();a.add_argument('--output',required=True);a.add_argument('--late-tick',required=True,type=int);a.add_argument('--goto-tick',required=True,type=int);a.add_argument('--field',type=int,choices=[5,7],default=5);v=a.parse_args()
assert v.late_tick>=0 and v.goto_tick>=0
out=Path(v.output);assert not out.exists();out.mkdir()
x,z=(112950,19750) if v.field==5 else (117050,20000)
common=f'room 0x119\npos 128000 2251 10888\nang -1.571\ngoto {v.goto_tick} {x} 2298.247 {z} 3.14159265\nalivelog 120\n'
for name,mask in [('off',0),('census',32),('reject',64)]:
 (out/f'warp-{name}.txt').write_text(common+f'late {mask} {v.late_tick} 0x119\n')
(out/'fixture.json').write_text(json.dumps({'kind':'UNEXECUTED camera candidate; actual boss/camera intersection must be qualified','field':v.field,'global_late_tick':v.late_tick,'room_PAD_goto_tick':v.goto_tick,'original_start':[128000,2251,10888],'candidate_Leon':[x,2298.247,z],'original_enemy_logic':True,'RSF_or_enemy_move_or_kill':False,'required_room_metadata_sha256':'9338bd8530b4f45b3c6e891e584f37cc81e93242c4eaec9a0a6bfd7abeb3d22c'},indent=2)+'\n')
