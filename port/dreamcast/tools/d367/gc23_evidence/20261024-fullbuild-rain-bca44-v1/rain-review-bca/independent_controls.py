"""Independent host-source controls; no author writes, SDK, guest or asset inputs."""
import ast,hashlib,json,os,pathlib,subprocess,tempfile,time
P=pathlib.Path; R=P(__file__).resolve().parent
REPO=P('/root/work/lanes/water-rain24'); SRC=REPO/'port/dreamcast/tools/d367/water_rain24'
COMMIT='bca44d58a1fa0a51fd87ba94deba8cba925c8998'
def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
def put(n,x):
    with open(R/n,'x') as f:json.dump(x,f,indent=2);f.write('\n')
assert subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()==COMMIT
assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True).strip()
author=SRC/'test_rain_r10c.py'; tree=ast.parse(author.read_text())
# Load only the read-only extraction and source-order prefix; exclude the runner's compilation block.
first=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.With))
ns={'__file__':str(author),'__name__':'review_extract_only'}
exec(compile(ast.Module(body=tree.body[:first],type_ignores=[]),'review actual extractor definitions','exec'),ns)
new=ns['new']; fixture=ns['fixture']
anchor='std::puts("PASS r10c signature/dispatcher/alloc/fade/frame+room/rebind/destruct/stop/consume/reused-night");'
assert fixture.count(anchor)==1
extra=r'''
// Every retained signature field is revoked AFTER callback, then restored without a new callback.
for(int field=0;field<18;field++){
 setup();flt06.cur[3]=80;Filter06Work saved=flt06;Filter06Render();
 switch(field){case 0:pG->room_id=0x10d;break;case 1:flt06.p=nullptr;break;case 2:flt06.num=1099;break;
 case 3:flt06.col[0]--;break;case 4:flt06.col[1]--;break;case 5:flt06.col[2]--;break;case 6:flt06.col[3]--;break;
 case 7:flt06.rate=.5f;break;case 8:flt06.scale=2;break;case 9:flt06.spd.x++;break;case 10:flt06.spd.y++;break;
 case 11:flt06.spd.z++;break;case 12:flt06.alphaMin=1;break;case 13:flt06.rate=std::nanf("");break;
 case 14:flt06.scale=std::nanf("");break;case 15:flt06.spd.x=std::nanf("");break;
 case 16:flt06.spd.y=std::nanf("");break;case 17:flt06.spd.z=std::nanf("");break;}
 GXSetDrawSync(0xADEB);assert(sent==0&&s_raindc_pending==0&&s_raindc_queued_room==0&&s_raindc_queued_frame==0);
 flt06=saved;pG->room_id=0x10c;GXSetDrawSync(0xADEB);assert(sent==0); // no resurrection
}
// Refresh callback alpha in the same actual frame, consume exactly the latest snapshot once.
setup();flt06.cur[3]=20;Filter06Render();flt06.cur[3]=40;Filter06Render();
GXSetDrawSync(0xAAAA);assert(sent==0&&s_raindc_pending==1);
GXSetDrawSync(0xADEB);assert(sent==320&&s_raindc_alpha==40);
assert((s_raindc_out[0].head>>24)==(u32)(s_raindc[0].a*.5f*1.2f));
n=sent;GXSetDrawSync(0xADEB);assert(sent==n);
// UINT_MAX→0 is a stale callback, not an ancient same-valued ticket.
setup();pG->Frame_cnt=0xffffffffU;flt06.cur[3]=80;Filter06Render();++pG->Frame_cnt;
GXSetDrawSync(0xADEB);assert(sent==0&&s_raindc_pending==0);
// Long Stop must advance the private anchor; unpause resumes with one tick, not clamped catch-up.
setup();image();for(auto &drop:s_raindc){drop.y=10;drop.len=20;}
pG->Stop_flg=0x08000000;pG->Frame_cnt+=100;image();assert(s_raindc[0].y==10&&s_raindc_frame==pG->Frame_cnt);
pG->Stop_flg=0;++pG->Frame_cnt;image();assert(s_raindc[0].y==32);
'''
ns['fixture']=fixture.replace(anchor,extra+'\n'+anchor)
results=[]; start=time.monotonic()
with tempfile.TemporaryDirectory(prefix='rain-bca-independent-',dir='/dev/shm') as t:
    tmp=P(t); source=tmp/'host.cpp'; binary=tmp/'host'
    def run(text):
        source.write_text(ns['unit'](text))
        compiled=subprocess.run(['g++','-std=c++17','-O2','-DRE4DC_RAIN_R10C_DC=1',str(source),'-o',str(binary)],capture_output=True,timeout=30)
        assert compiled.returncode==0,compiled.stderr.decode()
        return subprocess.run([str(binary)],capture_output=True,text=True,timeout=5)
    good=run(new);assert good.returncode==0,good.stderr
    results.append(dict(kind='independent extended source controls',returncode=good.returncode,stdout=good.stdout,
       controls=['18 post-callback signature losses including five NaNs','restoration cannot resurrect consumed cancellation',
                 'same-frame replacement alpha snapshot and consume-once','wrong draw-sync token','UINT_MAX-to-zero stale wrap',
                 '100-tick Stop anchor and exact one-tick unpause movement']))
    mutants={'omit-postcallback-profile-check':('!Filter06R10cRain()','false'),
             'stop-anchor-not-updated':('    s_raindc_frame = now;','    if (!(pG->Stop_flg & 0x08000000)) s_raindc_frame = now;')}
    for name,(before,after) in mutants.items():
        assert new.count(before)==1,name
        bad=run(new.replace(before,after));assert bad.returncode!=0,name+' survived'
        results.append(dict(kind='independent mutant defeated',name=name,returncode=bad.returncode,stderr=bad.stderr[-1600:]))
    # Actual included Make flags, including non-filter objects: new macro must not escape filter06.o.
    mk=tmp/'test.mk'; obj=tmp/'obj'; target=str(obj/'src/game/filter06.o'); other=str(obj/'platform/native_ui.o')
    mk.write_text('OBJDIR := '+str(obj)+'\ninclude '+str(REPO/'port/dreamcast/game/effects30.mk')+'\n'+target+':\n\t@echo FILTER $(GAME_CPPFLAGS)\n'+other+':\n\t@echo UI $(PLATFORM_CPPFLAGS)\n')
    prereq=['RAIN_DC=1','RAIN_PS2=1','D349_RENDERER_STACK=1','PVR_STREAM=1','NATIVE_LASER=1','EFFECT_SPRITES=1']
    flags=subprocess.run(['make','-s','--no-print-directory','-f',str(mk),target,other,'RAIN_R10C_DC=1',*prereq],capture_output=True,text=True,timeout=5,check=True)
    rows=flags.stdout.splitlines();assert len(rows)==2 and '-DRE4DC_RAIN_R10C_DC=1' in rows[0] and 'RE4DC_RAIN_R10C_DC' not in rows[1]
    results.append(dict(kind='actual Make macro scope',stdout=flags.stdout))
put('INDEPENDENT-HOST-RESULTS.json',dict(status='PASS_HOST_SOURCE_ONLY',source_commit=COMMIT,elapsed_s=time.monotonic()-start,
     results=results,mutants_defeated=2,extractor_sha256=sha(author),fixture_sha256=sha(SRC/'fixture_rain_r10c.cpp.in'),
     controls_sha256=sha(__file__),SDK=False,guest=False,author_tree_edit=False,assets_read_or_written=False))
print(json.dumps(dict(status='PASS_HOST_SOURCE_ONLY',mutants_defeated=2,receipt_sha256=sha(R/'INDEPENDENT-HOST-RESULTS.json'))))
