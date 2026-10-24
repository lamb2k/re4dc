#!/usr/bin/env python3
"""RAM-only exact-source negative controls; writes only the new text receipt."""
import ast,collections,importlib.util,json,struct,sys,types,zlib
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('bounded',HERE/'check_core_tranche_v1.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);A=G.A
fx=A.source('port/dreamcast/tools/d367/test12fx/fx_ps2_pack.py');cs=A.source('port/dreamcast/tools/convert_tpl.py');ce={'struct':struct};wanted={'MAGIC','VERSION','FORMAT_PAL4_ARGB4444','FLAG_ALPHA','FLAG_BINARY_ALPHA','PAYLOAD_TWIDDLED','HEADER','TEXTURE'}
nodes=[v for v in ast.parse(cs).body if isinstance(v,ast.Assign) and any(isinstance(t,ast.Name) and t.id in wanted for t in v.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),'<constants>','exec'),ce)
A.exact_functions(cs,['_pack_4444','_twiddle_table','twiddle_16bpp'],ce);env={'struct':struct,'zlib':zlib,'C':types.SimpleNamespace(**ce)};A.exact_functions(fx,['premul','palette16','package'],env)
eff=Path('/root/re4data/private/worldfx-20261018/cache/Core.ps2.eff1').read_bytes();assert A.sha(eff)=='e0a571bec16baa427c4267feb59ea6ec9aa64703b833d7ed42598115c62b0124'
pics,meta=G.pictures(eff,0xa);pal=env['palette16'](collections.Counter(c for _,_,px in pics for c in px));blobs=[env['package'](w,h,px,pal,(w,h))[0] for w,h,px in pics]
checks={};checks['actual_animated_frames_distinct']=len(set(blobs))>1;assert checks['actual_animated_frames_distinct']
checks['wrong_frame_changes_full_SHA']=any(A.sha(blobs[i])!=A.sha(blobs[(i+1)%len(blobs)]) for i in range(len(blobs)));assert checks['wrong_frame_changes_full_SHA']
per=[env['package'](w,h,px,env['palette16'](collections.Counter(px)),(w,h))[0] for w,h,px in pics];checks['wrong_per_frame_palette_changes_output']=any(a!=b for a,b in zip(blobs,per));assert checks['wrong_per_frame_palette_changes_output']
w,h,px=pics[0];black=[(0,0,0,255)]*len(px);mut=env['package'](w,h,black,env['palette16'](collections.Counter(black)),(w,h))[0];checks['changed_source_pixels_change_output']=mut!=blobs[0];assert checks['changed_source_pixels_change_output']
# Reuse exact frozen public mip modules, in memory only.
for name in ['convert_tpl','mipmap_vq','mipmap_pal4']:
 path=HERE/'composed-01'/('historical-'+name+'-0425534d.py');raw=path.read_bytes();m=types.ModuleType(name);m.__file__='<frozen public source>';sys.modules[name]=m;exec(compile(raw,m.__file__,'exec'),m.__dict__)
M=sys.modules['mipmap_pal4'];blob,ev=M.add_mipmaps(blobs[0],enabled=True,engine='python');native=M.read_native_pal4(blob);bad=bytearray(blob);bad[145]^=1
checks['lower_mip_mutation_keeps_base_and_palette_but_fails_full_SHA']=(bytes(bad)[144+M.level_offset(native.size):144+M.level_offset(native.size)+native.size*native.size//2]==native.base_indices and bytes(bad)[-32:]==native.palette and A.sha(bad)!=A.sha(blob));assert checks['lower_mip_mutation_keeps_base_and_palette_but_fails_full_SHA']
# Malformed actual descriptors must reject BEFORE converter execution.
for label,offset,value in [('zero_width',meta['pictures'][0]['descriptor_offset'],0),('unsupported_depth',meta['pictures'][0]['descriptor_offset']+4,9),('unsupported_swizzle',meta['pictures'][0]['descriptor_offset']+6,2)]:
 bad=bytearray(eff);struct.pack_into('<H',bad,offset,value)
 try:G.pictures(bad,0xa)
 except AssertionError:checks[label]=True
 else:raise AssertionError(label+' accepted')
try:G.pictures(eff[:meta['TPL_offset']+12],0xa)
except (AssertionError,struct.error):checks['truncated_original_TPL_rejected']=True
else:raise AssertionError('truncated original accepted')
record={'schema':1,'status':'PASS','controls':checks,'positive':{'frozen_mip_base_exact':ev['base_level_exact'],'frozen_mip_palette_exact':ev['palette_exact']},'checks':len(checks),'asset_bytes_RAM_only':True,'filesystem_asset_output':False,'source_helper':A.pin(HERE/'test_core_chain_controls_v1.py')}
p=HERE/'EXACT-CHAIN-CONTROLS.json';assert not p.exists();p.write_bytes(A.enc(record));print(json.dumps(record,indent=2))
