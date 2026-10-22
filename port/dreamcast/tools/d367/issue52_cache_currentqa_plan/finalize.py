from pathlib import Path
import gzip,hashlib,json
P=Path('/root/probe/codex-issue52-objects/port/dreamcast/tools/d367/issue52_cache_currentqa_plan');C=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-cache-currentqa-plan-20261022');G=Path('/root/probe/codex-cache21-integration-next/port/dreamcast/game');Q=Path('/root/re4data/private/texture-consumers21-next792-runner03-20261022')
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):p=Path(p);return {'p':str(p),'b':p.stat().st_size,'sha':sha(p.read_bytes())}
def write(n,d,z=False):
 b=json.dumps(d,sort_keys=True,separators=(',',':')).encode()+b'\n';b=gzip.compress(b,mtime=0)if z else b
 for p in[P,C]:(p/n).write_bytes(b)
canonical=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/canonical-programme-plan-01/plan02.json');d=json.load(open(canonical));libs=[]
for r in d['unchanged_library_pins']:
 p=pin(r['path']);assert p['sha']==r['sha256']and p['b']==r['bytes'];libs.append(p)
support=[]
for n in['obj/aliases-all.ld','obj/missing.o','obj/overlay-a.ld','platform/ps_alias_sh4.ld','platform/char_data_block.ld','tools/gen_overlay.py','tools/ovl_id_patch.py','tools/link.sh']:
 support.append(pin(G/n))
for n in['shlelf-tight.ld','link-order-rot-fsca.ld']:
 a=Path('/root/probe/cache21-ganado-reader-build-20261021/on-01/obj')/n;b=Path('/root/probe/texture-rect21-program-pair-20261021-01/obj')/n;assert a.read_bytes()==b.read_bytes();support.append(pin(a))
write('link-support.json',{'canonical_structural_ref':pin(canonical),'libraries':libs,'C57_context_support':support,'kosenv':pin(G.parent/'kos-env.sh')if(G.parent/'kos-env.sh').exists()else None,'namespace':'Immutable inputs only; future main resolves fresh private context, actual tool/pre/post closure and exact argv. Existing retained link.sh not executed.','overlay_steps':[{'name':r['p'].split('/')[-1],'base':hex(0x8e000000+i*0x400000),'relocation_shift':1048576}for i,r in enumerate(json.load(open(P/'qa52190.json'))['overlays'])]})
# The table above must use original overlay address order, not lexical QA receipt order.
s=json.load(open(P/'link-support.json'));s['overlay_steps']=[{'name':n+'.ovl','section':sec,'base':hex(0x8e000000+i*0x400000),'relocation_shift':1048576}for i,(n,sec)in enumerate([(n,'.ovl_'+n)for n in['pl0f','em2f','em22','em2b','pl11','pl14','em3b','em35','st1_0','st1_1','st1_2','st1_3','st2_0']]+[('sscrn','.ovl_Sscrn')])];write('link-support.json',s)
f=P/'tool-closure-reuse.json';t=json.load(open(f));qual=json.load(open(Q/'SOURCE03-qualification.json'));t['qualification']=pin(Q/'SOURCE03-qualification.json');t['manifest']=pin(Q/'SHA256SUMS.txt');assert t['manifest']['sha']==t['source_seal'];t['source_files']=[]
for r in qual['source_files']:
 x=pin(r['path']);assert x['sha']==r['sha256']and x['b']==r['bytes'];t['source_files'].append(x)
t['tool_closure']=pin('/root/probe/codex-mipmap21-alpha-reader/port/dreamcast/tools/d367/link_closure21/tool_closure.py');write('tool-closure-reuse.json',t)
# Current helper object projections are actual retained C57 inputs, not presumed same bytes as historical helper packet.
x=json.loads(gzip.decompress((P/'link-input-template.json.gz').read_bytes()));x['fresh_owned_path_rewrites_required']=['finalELF/OUT','fresh private overlay script contexts','TMPDIR (old canonical namespace forbidden)','EM10G pending fresh output','SS/main OFF or ON replacements'];x['link_support_reference']='link-support.json';write('link-input-template.json.gz',x,True)
print(json.dumps({'support':len(support),'libraries':len(libs),'consumer_source_files':len(t['source_files']),'consumer_source_seal':t['source_seal']}))
