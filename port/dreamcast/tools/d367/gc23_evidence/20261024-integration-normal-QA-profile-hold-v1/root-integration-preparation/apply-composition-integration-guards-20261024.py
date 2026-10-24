from pathlib import Path
root=Path('/root/work/lanes/codex-composition-int24');g=root/'port/dreamcast/game'
p=g/'scenery19.mk';s=p.read_text();old='$(PS2_WORLD_PREFLIGHT_DIAG)),)';assert s.count(old)==1;s=s.replace(old,'$(PS2_WORLD_PREFLIGHT_DIAG) $(GC_ASSET_GATE) $(GC_ASSET_MOTION_UNKNOWN)),)');p.write_text(s)
block='''#if (defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE != 0) || (defined(RE4DC_GC_ASSET_MOTION_UNKNOWN) && RE4DC_GC_ASSET_MOTION_UNKNOWN != 0)
#error PS2_PVS_BATCH_COMPOSE does not yet qualify GC asset diagnostics
#endif
'''
for rel in ['platform/native_static.cpp','platform/native_ui.cpp']:
 p=g/rel;s=p.read_text();anchor='#if RE4DC_PS2_PVS_BATCH_COMPOSE\n';assert s.count(anchor)>=1;s=s.replace(anchor,anchor+block,1);p.write_text(s)
parent=root/'port/dreamcast/tools/d367';out=parent/'composition_int24';out.mkdir()
s=(parent/'pvs_batch_compose24/test_compose.py').read_text();s=s.replace("BASE='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'","BASE='e3ed0d2ab2482ade7f5a3615009f59a43ccdcfae'")
s=s.replace("PS2_WORLD_PREFLIGHT_DIAG'.split()","PS2_WORLD_PREFLIGHT_DIAG GC_ASSET_GATE GC_ASSET_MOTION_UNKNOWN'.split()")
s=s.replace("(['0','2'] if k in must else ['2'])","(['0','2'] if k in must else (['1','2'] if k in ZERO else ['2']))")
s=s.replace('for pvs,batch in [(0,0),(0,1),(1,0)]:','for pvs,batch,gc in [(p,b,c) for p,b in [(0,0),(0,1),(1,0)] for c in [0,1]]:')
s=s.replace("flags=['-DRE4DC_PS2_PVS_BATCH_COMPOSE=0'","flags=['-DRE4DC_GC_ASSET_GATE='+str(gc),'-DRE4DC_GC_ASSET_MOTION_UNKNOWN='+str(gc),'-DRE4DC_PS2_PVS_BATCH_COMPOSE=0'")
(out/'test_compose_integrated.py').write_text(s)
print('root guard edits and integrated source fixture staged, no SDK')
