import pathlib,json,hashlib,resource,signal,time,types,sys,re,gc,stat,datetime,collections
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));signal.alarm(120);start=time.monotonic()
W=pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24');R=W/'kos-census-media-root-review-v1';K=W/'kos-census-media-prep-v1';O=W/'kos-census-attribution-readback-v1';pins={}
def pin(p):
 p=pathlib.Path(p);h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 x={'size':p.stat().st_size,'sha256':h.hexdigest()};pins[str(p)]=x;return x
def verify(p,x):assert pin(p)==x,(str(p),x,pins[str(p)])
def load(p):pin(p);return json.loads(pathlib.Path(p).read_text())
def module(n):
 p=K/(n+'.py');pin(p);m=types.ModuleType(n);m.__file__=str(p);sys.modules[n]=m;exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
G=load(R/'ROOT-CALLER-GUEST-GRANT-v1.json');assert pins[str(R/'ROOT-CALLER-GUEST-GRANT-v1.json')]['sha256']=='195f59bdb3e94945e51bfcb47b0b759f1a1abb488631a6c63a06c45e3d91992b'
verify(R/'root-caller-pair-v2.py',{'size':6394,'sha256':'4092d7eb8f839c76125f6db98c7d298bef99c2e36e3e358251699e90b2751634'})
S=load(K/'TOOLCHAIN-SEAL.json');verify(K/'TOOLCHAIN-SEAL.json',G['kit_seal'])
for n,p in S['members'].items():verify(K/n,p)
B=load(K/'BINDING.json');verify(K/'BINDING.json',G['binding'])
P=load(K/'OBSERVATION-PROPOSAL.json');verify(K/'OBSERVATION-PROPOSAL.json',G['proposal'])
adapter_pin=pin(R/'parse-full-log-v1.py'); root=load(R/'ROOT-CALLER-PAIR-RESULT.json');assert root['complete'] and root['grant_sha256']==pins[str(R/'ROOT-CALLER-GUEST-GRANT-v1.json')]['sha256'] and root['helpers']==G['helpers'] and root['template']==G['template']
post=W/'kos-census-media-independent-review-v1/POSTSTAGE-SUMMARY.json';verify(post,root['poststage_review']);postdata=load(post);assert postdata['status']=='CLEAR_POSTSTAGE_ALL_FILES_NO_GUEST'
for h in G['helpers'].values():verify(h['path'],h['identity'])
c=module('common');e=module('elf');cp=module('census');observations={}
for arm in('off','on'):
 a=root['arms'][arm];cap=pathlib.Path(a['cap']);pr=load(R/('caller-'+arm+'-PROCESS.json'));assert pr==a and a['complete'] and a['returncode']==0
 expected=list(P['arms'][arm]['argv']);expected[expected.index('--period')+1]='25';expected[5:5]=['-I','-S','-B','-X','pycache_prefix='+expected[expected.index('--cap')+1]+'-pycache'];assert a['argv']==expected
 for n,p in a['capture_files'].items():verify(cap/n,p)
 bounded=load(cap/'bounded-launch.json');run=load(cap/'run-result.json');assert bounded==a['bounded'] and run==a['run'];assert bounded['deadline_seconds']==55 and bounded['guest_exited']and not bounded['deadline_fired']and 0<bounded['guest_observed_elapsed_s']<=55
 assert int((cap/'flycast.pid').read_text())==bounded['pid'];assert bounded['harness_sha256']==G['helpers']['harness']['identity']['sha256']and bounded['expected_executable_sha256']==G['helpers']['console']['identity']['sha256']
 assert run['reader_exit']==0 and run['emu']=='console'and run['seconds']==45 and run['stop']is None and run['keys']is None and not run['key_log'] and run['emu_env']=={} and 'early_emulator_exit'not in run
 assert run['errors']==[{'kind':'screenshot','error':"No module named 'PIL'"}];assert not list(cap.rglob('*.png'));assert run['emulator_exited']
 samples=a['kernel_lock_sample'];assert {6,9}<={x['fd']for x in samples};assert all('lock:'in x['fdinfo'] and 'FLOCK  ADVISORY  WRITE'in x['fdinfo']for x in samples)
 for x in samples:assert (x['fd']==6 and x['target'].startswith('/root/work/lanes/stat-bytes23-complete-scratch/guest-slots/slot-'))or(x['fd']==9 and x['target'].startswith('/root/probe/.trace.lock'))
 assert (cap/'syms.txt').read_text().strip()==P['arms'][arm]['syms_offsets'];verify(cap/'fixture-warp.txt',G['fixture']);assert run['fixtures']['warp']['sha256']==G['fixture']['sha256']
 cfg=(cap/'emu.cfg').read_text();assert 'aica.LimitFPS = no'in cfg and 'rend.vsync = no'in cfg
 # Recheck the previously independently approved stage identity chain; do not duplicate the all-track readback.
 pa=postdata['arms'][arm];verify(pa['readback_path'],pa['readback_identity']);rb=load(pa['readback_path']);assert rb['status']=='STAGE_ALL_FILE_READBACK_PASS_GUEST_NOT_RUN';verify(c.FINAL/arm/'COMPLETE.json',pa['complete_identity']);assert run['tracks']['track03_sha256']==rb['tracks']['track03.iso']['sha256']
 elf=e.ELF(B['arms'][arm]['ELF']['path'],B['arms'][arm]['ELF']['identity']['sha256']);parser=cp.Parser(elf);log=cap/'run-output.txt';before=log.stat();assert stat.S_ISREG(before.st_mode)and before.st_size<=64*1024**2;h=hashlib.sha256();total=0;selected=[];life=[];squeeze=[];alerts=[];headers=[]; asset_errors=collections.Counter(); first_asset=None; tail=collections.deque(maxlen=6); watches=[]
 with log.open('rb')as f:
  while True:
   line=f.readline(2049)
   if not line:break
   assert len(line)<=2048;total+=len(line);assert total<=64*1024**2;h.update(line);text=line.rstrip(b'\n').decode('utf-8',errors='replace');parser.feed(text)
   tail.append({'line':parser.lines,'text':text})
   er=re.search(r'GC-ASSET-ERROR v=2 why=([a-z-]+) consumer=([0-9]+)',text)
   if er:
    asset_errors[er.group(1)+'/consumer'+er.group(2)]+=1
    if first_asset is None:first_asset={'line':parser.lines,'text':text}
   if 'kos watch:' in text:watches.append({'line':parser.lines,'text':text})
   if 'room lifecycle:'in text:life.append({'line':parser.lines,'text':text})
   if 'kos census:'in text:headers.append({'line':parser.lines,'text':text})
   if 'squeeze'in text.lower()and len(squeeze)<20:squeeze.append({'line':parser.lines,'text':text})
   if 'warp: alert'in text and len(alerts)<20:alerts.append({'line':parser.lines,'text':text})
 after=log.stat();assert(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns);assert total==before.st_size and h.hexdigest()==a['capture_files']['run-output.txt']['sha256']
 parsed=parser.result();assert parsed['status']=='BOUNDED_REQUESTED_ROWS_PARSED_COVERAGE_UNKNOWN'and len(parsed['groups'])==1 and not parsed['errors'];g=parsed['groups'][0];assert g['phase']=='enter'and g['room']=='101'and g['lost']==g['overflow']==0 and len(g['rows'])==g['callers']==23
 assert sum(x['blocks']for x in g['rows'])==g['blocks']and sum(x['bytes']for x in g['rows'])==g['bytes'];assert g['arena_exclusion']['status']=='AUTHENTICATED_ONE_REQUESTED_ARENA_BLOCK_EXCLUDED';ar=g['arena_exclusion']['requested'];assert g['nonarena_requested_bytes']==g['bytes']-ar;heap=g['heap_context'];assert g['mallinfo_requested_residual']['used_minus_all_census_requested']==heap['used']-g['bytes'];assert g['mallinfo_requested_residual']['used_less_arena_requested_including_its_allocator_overhead']==heap['used']-ar
 prior=load(R/('CENSUS-OFF-v1.json'if arm=='off'else'CENSUS-ON-FULL-v1.json'));assert all(parsed[k]==prior[k]for k in parsed)
 aggregate={}
 for x in g['rows']:
  names=x['caller']['function_candidates'];assert x['caller']['unique_function']and len(names)==1;z=aggregate.setdefault(names[0],{'blocks':0,'bytes':0});z['blocks']+=x['blocks'];z['bytes']+=x['bytes']
 parsed.update(arm=arm,log=str(log),log_bytes=total,log_sha256=h.hexdigest());(O/(arm+'-INDEPENDENT.json')).write_text(json.dumps(parsed,indent=2)+'\n')
 observations[arm]={'pid':bounded['pid'],'elapsed':bounded['guest_observed_elapsed_s'],'guest_rc':bounded['guest_rc'],'log_bytes':total,'log_sha256':h.hexdigest(),'lines':parser.lines,'groups':len(parsed['groups']),'census_group':g,'aggregate_by_function':aggregate,'lifecycle_lines':life,'squeeze_lines':squeeze,'alert_lines':alerts,'census_raw_lines':headers,'run_errors':run['errors'],'asset_error_counts':dict(asset_errors),'first_asset_error':first_asset,'last_log_lines':list(tail),'kos_watch_first_last':([watches[0],watches[-1]] if watches else []), 'kos_watch_min_headroom':min([int(re.search(r'headroom=([0-9]+)',x['text'])[1]) for x in watches],default=None),'kernel_lock_sample':samples}
 del elf,parser;gc.collect()
assert datetime.datetime.fromisoformat(root['arms']['off']['run']['end_utc'])<datetime.datetime.fromisoformat(root['arms']['on']['run']['start_utc'])
changes={}
for n in set(observations['off']['aggregate_by_function'])|set(observations['on']['aggregate_by_function']):
 if n=='_re4dc_mem_init':continue
 x=observations['off']['aggregate_by_function'].get(n,{'blocks':0,'bytes':0});y=observations['on']['aggregate_by_function'].get(n,{'blocks':0,'bytes':0})
 if x!=y:changes[n]={'off':x,'on':y,'delta_blocks':y['blocks']-x['blocks'],'delta_bytes':y['bytes']-x['bytes']}
D={'decision':'CLEAR_BOUND_ENTER_REQUESTED_LEDGER_ONLY_STEADY_OWNER_UNKNOWN','root_receipt_identity':pins[str(R/'ROOT-CALLER-PAIR-RESULT.json')],'observations':observations,'nonarena_changes':changes,'steady_caller_phase':'UNKNOWN_ABSENT','residual_attribution':'UNKNOWN allocator overhead, unwrapped allocation or sequential sampling; not measured requested bytes','adapter_identity':adapter_pin,'ON_clean_matched_control':False,'retained_handle_vs_transient_classification':'UNKNOWN from one enter snapshot; extra ISO/open bookkeeping is observed at the sample, persistence/close ownership not established','pins':pins,'limits':{'address_space_bytes':256*1024**2,'process_seconds':120,'actual_seconds':time.monotonic()-start,'peak_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},'SDK_stage_guest_native_queries':0,'screenshots_accepted':False,'KOS48KiB_H2_performance_acceptance':False}
(O/'READBACK.json').write_text(json.dumps(D,indent=2)+'\n');print(json.dumps({'decision':D['decision'],'changes':changes,'arm_totals':{a:{k:observations[a]['census_group'][k]for k in('blocks','bytes','nonarena_requested_bytes','mallinfo_requested_residual')}for a in observations},'limits':D['limits']},indent=2))
