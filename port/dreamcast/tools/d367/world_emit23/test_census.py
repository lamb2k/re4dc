"""RAM-only controls for the actual flush body and gated census helper."""
from pathlib import Path
import argparse, hashlib, json, os, re, resource, subprocess, tempfile
from census import parse
BASE = "a5e972e44096410253ad93164b84d92e3c22655a"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
STATIC = ROOT / "port/dreamcast/game/platform/native_static.cpp"
HEADER = ROOT / "port/dreamcast/game/platform/include/scenery_emit_census.hpp"
MAKE = ROOT / "port/dreamcast/game/scenery19.mk"

def block(text, signature):
    begin=text.index("{",text.index(signature));depth=0
    tokens=r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|[{}]'
    for match in re.finditer(tokens,text[begin:]):
        token=match.group()
        if token=="{":depth+=1
        elif token=="}":
            depth-=1
            if not depth:return text[begin:begin+match.end()]
    raise AssertionError(signature)

def fixture(source, mutate=False):
    decl=source[source.index("    struct ChunkPart {"):source.index("    auto chunk_flush=[&]()->int{")]
    flush=block(source,"auto chunk_flush=[&]()->int")
    if mutate:
        a=flush.index("#if RE4DC_SCENERY_EMIT_CENSUS")
        b=flush.index("#endif",a)+len("#endif")
        code=flush[a:b]
        flush=flush[:a]+flush[b:]
        at=flush.index("        } submit_scope;")+len("        } submit_scope;")
        flush=flush[:at]+"\n"+code+flush[at:]
    # The production entry hook before bind/borrow, extracted rather than a test-only call.
    hook=source[source.index("    int emit_pick(const Pick& pk){"):source.index("        namespace vp=re4dc::vp;",source.index("    int emit_pick(const Pick& pk){"))]
    hook=hook[hook.index("\n")+1:]
    return r"""
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <cstdint>
#include <cstdlib>
bool sq;std::string logs,render;
extern "C" void re4dc_log(const char* fmt,...){
 assert(!sq);char line[256];va_list ap;va_start(ap,fmt);int n=vsnprintf(line,sizeof line,fmt,ap);va_end(ap);
 assert(n>=0 && unsigned(n)<sizeof line);logs+=line;
}
#include "scenery_emit_census.hpp"
struct MeshPart{float uv_bias[2]{},uv_scale[2]{};};
namespace re4dc{namespace room{using MeshPart=::MeshPart;}}
struct Re4dcModelPart{unsigned cull=0;float uv_offset[2]{};};
struct Let{unsigned first_vertex=0,strip_count=0,vertex_count=0;};
struct Package{struct Header{unsigned meshlet_count=320;}h;Let lets[320];MeshPart ps[64];
 const Header&header()const{return h;}const Let*meshlets()const{return lets;}const MeshPart*parts()const{return ps;}};
struct{Package package;void*lut=nullptr;void*gather=nullptr;const std::uint8_t*sg=nullptr;unsigned sg_groups=0;}ps2w;
struct Re4dcWorldSubmitBatch{bool held=false;};
void re4dc_ps2_world_batch_close(Re4dcWorldSubmitBatch* b){if(b->held){b->held=false;sq=false;}}
void re4dc_model_packet_abort(){assert(!sq);render+="A";}
int re4dc_model_packet_streaming(){return 1;}
int fail_part=-1,fail_at=-1,fail_code=-1;
struct MeshDraw{
 struct Pick{std::uint16_t let;std::uint8_t nr,gmask,lo,hi,pad[2];};
 struct Base{Re4dcModelPart&p;unsigned empty;float near,far;};
 MeshDraw(Base,const Package&,const MeshPart&,const void*,void*){}
 unsigned alpha=0,part_index=0;bool direct=false,lean_part=false,vertex_alpha=false,c4444=false,streaming=false;
 float cull_far=0,lod_scale=0,mvq[12]{},mv[12]{};const void*lut=nullptr;const std::uint8_t*sg=nullptr;unsigned sg_groups=0;
 const unsigned*ps2=nullptr;Re4dcWorldSubmitBatch*submit_batch=nullptr;
 void set_clip(){}void chunk_restart(){}
 void entry(const Pick& pk){
 (void)pk;
""" + hook + r"""
 }
 int chunk_emit(const Pick* p,unsigned n,const Pick* following=nullptr){
  (void)following;
  for(unsigned i=0;i<n;++i){
   entry(p[i]);sq=true;if(submit_batch)submit_batch->held=true;
   if(int(part_index)==fail_part && int(i)==fail_at)return fail_code;
   if(p[i].nr)render+=std::to_string(p[i].let)+",";
  }
  return 1;
 }
 void end_direct(){if(!submit_batch)sq=false;}
};
struct Count{unsigned native=0,aborts=0,fallback=0;};
std::string run(unsigned scenario){
 scenery_emit_census::state={};logs.clear();render.clear();sq=false;
 fail_part=fail_at=-1;fail_code=-1;
 Re4dcModelPart part;Count c;float near=1,far=100;unsigned pass=0;
 scenery_emit_census::Pass census_pass(360,0x101,pass);
""" + decl + r"""
 if(scenario==3){nctx=48;npk=320;}
 else {nctx=4;npk=4;}
 for(unsigned j=0;j<nctx;++j){auto&x=cctx[j];x={};x.index=j;x.placement=100+j;x.first=j<4?j:4;x.count=j<4?1:0;x.key[0]=0x1200+j;x.key[1]=0x3400+j;}
 cctx[0].count=0;cctx[1].first=0;cctx[1].count=2;cctx[2].first=2;cctx[2].count=1;cctx[3].first=3;cctx[3].count=1;
 for(unsigned i=0;i<npk;++i){cpk[i]={std::uint16_t(i),0xff,0,0,0,{0,0}};ps2w.package.lets[i]={0,i%2?0x8000U:0U,10+i};}
 cpk[1].nr=0;cpk[2].nr=1;cpk[2].lo=2;cpk[2].hi=5;
 if(scenario==3){for(unsigned j=4;j<nctx;++j){cctx[j].first=4+(j-4)*7;cctx[j].count=j==47?15:7;}}
 if(scenario==1 || scenario==2){fail_part=2;fail_at=0;fail_code=scenario==1?-1:0;}
 auto chunk_flush=[&]()->int""" + flush + r""";
 int result=chunk_flush();assert(!sq);assert(!nctx && !npk);
 if(scenario==1){assert(result==-1 && c.aborts==1);assert(render=="0,A");}
 else if(scenario==2){assert(result==1 && c.fallback==1 && c.native==3);assert(render=="0,3,");}
 else {assert(result==1 && c.native==(scenario==3?48U:4U));}
 if(scenario==0){
  assert(logs.find("plain=2 indexed=2 pv=22 iv=24 zero=1 iz=1 zv=11 whole=2 partial=1 span=27 bad=0")!=std::string::npos);
  assert(logs.find("picks=4 sum=4 tried=4 completed=4 fallback=0 aborted=0 untried=0")!=std::string::npos);
  // A second synchronous drain must preserve the frame-local flush identity.
  nctx=1;npk=1;cctx[0].first=0;cctx[0].count=1;
  assert(chunk_flush()==1 && logs.find("q=2")!=std::string::npos);
 }
 if(scenario==1){
  assert(logs.find("picks=1 tried=1 result=-1")!=std::string::npos);
  assert(logs.find("picks=1 tried=0 result=2")!=std::string::npos);
  assert(logs.find("tried=3 completed=2 fallback=0 aborted=1 untried=1")!=std::string::npos);
 }
 if(scenario==2)assert(logs.find("tried=4 completed=3 fallback=1 aborted=0 untried=0")!=std::string::npos);
 if(scenario==3)assert(logs.find("picks=320 sum=320 tried=320 completed=48 fallback=0 aborted=0 untried=0")!=std::string::npos);
 census_pass.result=result<0?-1:c.fallback?0:1;
 return logs;
}
int main(){
 for(unsigned i=0;i<4;++i)run(i);
 scenery_emit_census::state={};logs.clear();
 {scenery_emit_census::Pass p(359,0x101,0);assert(!p.active);}
 {scenery_emit_census::Pass p(360,0x101,0);p.result=1;}
 {scenery_emit_census::Pass p(360,0x101,1);p.result=1;}
 {scenery_emit_census::Pass p(360,0x101,2);p.result=1;}
 assert(logs.find("begun=7 ended=7 complete=1")!=std::string::npos);
 {scenery_emit_census::Pass p(361,0x101,0);assert(!p.active);}
 scenery_emit_census::state={};logs.clear();
 {scenery_emit_census::Pass p(360,0x100,0);}
 {scenery_emit_census::Pass p(361,0x101,0);assert(!p.active);}
 assert(logs.find("complete=0")!=std::string::npos);
 // Worst-case legal unsigned logger fields remain within the actual logger buffer.
 scenery_emit_census::Counts max;max.plain=max.indexed=max.pv=max.iv=max.empty=max.izero=max.ev=max.whole=max.partial=max.span=max.bad=~0U;
 scenery_emit_census::counts("PART_COUNTS",~0U,~0U,~0U,~0U,max);
 if(std::getenv("CENSUS_CAPTURE")){
  run(0);
  {scenery_emit_census::Pass p(360,0x101,1);p.result=1;}
  {scenery_emit_census::Pass p(360,0x101,2);p.result=1;}
  printf("%s",logs.c_str());
 }
 puts("actual flush + queue census controls PASS");
}
"""

def run(out):
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    source=STATIC.read_text();checks={}
    with tempfile.TemporaryDirectory(prefix="world-emit23-census-",dir="/dev/shm") as tmp:
        temp=Path(tmp);cpp=temp/"fixture.cpp";exe=temp/"fixture"
        cpp.write_text(fixture(source))
        for replay in (0,1):
            for batch in (0,1):
                for prefetch in (0,1):
                    name=f"replay{replay}-batch{batch}-prefetch{prefetch}"
                    cmd=["g++","-std=c++17","-O2","-Wall","-Wextra","-Werror","-Wno-missing-field-initializers",
                         "-DRE4DC_SCENERY_EMIT_CENSUS=360",f"-DRE4DC_SCENERY_REPLAY_LEAN={replay}",
                         f"-DRE4DC_SCENERY_SUBMIT_BATCH={batch}",f"-DRE4DC_SCENERY_EMIT_PREFETCH={prefetch}",
                         "-I",str(HEADER.parent),str(cpp),"-o",str(exe)]
                    subprocess.run(cmd,check=True,text=True)
                    subprocess.run(["/lib64/ld-linux-x86-64.so.2",str(exe)],check=True,text=True)
                    checks[name]="PASS"
        captured=subprocess.run(["/lib64/ld-linux-x86-64.so.2",str(exe)],check=True,capture_output=True,text=True,
                                env=dict(os.environ,CENSUS_CAPTURE="1")).stdout
        assert parse(captured,0x101)["totals"]["indexed"]==2
        for altered in (captured.replace("complete=1","complete=0"),captured.replace("sum=4","sum=3"),
                        captured.replace("result=1","result=-1",1),captured+next(x for x in captured.splitlines() if "PART_COUNTS" in x)+"\n"):
            try:parse(altered,0x101)
            except ValueError:pass
            else:raise AssertionError("forged/incomplete census accepted")
        try:parse(captured,0x100)
        except ValueError:pass
        else:raise AssertionError("wrong room accepted")
        checks["actual-log-parser-and-five-negatives"]="PASS"
        lines=[line for line in captured.splitlines() if line.startswith("WEC23 ")]
        q2=[line for line in lines if " q=2" in line]
        remaining=[line for line in lines if " q=2" not in line]
        def log(lines):return "\n".join(lines)+"\n"
        # A valid globally second flush can occur in another active pass.
        before_p1_end=next(i for i,line in enumerate(remaining) if line.startswith("WEC23 PASS_END") and " p=1 " in line)
        multipass=remaining[:before_p1_end]+[line.replace(" p=0 "," p=1 ") for line in q2]+remaining[before_p1_end:]
        assert [x["pass"] for x in parse(log(multipass),0x101)["flushes"]]==[0,1]
        protocol={
            "flush-after-frame-end":log(remaining+q2),
            "flush-wrong-active-pass":log([line.replace(" p=0 "," p=1 ") if " q=2" in line else line for line in lines]),
            "reverse-complete-records":log(list(reversed(lines))),
            "future-threshold":captured.replace("threshold=360","threshold=999999"),
            "zero-threshold":captured.replace("threshold=360","threshold=0"),
            "out-of-range-threshold":captured.replace("threshold=360","threshold=10000001"),
            "global-flush-id-reuse":log([line.replace(" q=2 "," q=1 ") for line in multipass]),
            "global-flush-id-gap":log([line.replace(" q=2 "," q=3 ") for line in lines]),
            "duplicate-begin":log([lines[0]]+lines),
            "record-after-frame-end":log(lines+[lines[1]]),
        }
        swapped=list(lines);at=next(i for i,line in enumerate(swapped) if line.startswith("WEC23 PART "))
        swapped[at],swapped[at+1]=swapped[at+1],swapped[at]
        protocol["counts-before-part"]=log(swapped)
        swapped=list(lines);at=next(i for i,line in enumerate(swapped) if line.startswith("WEC23 FLUSH_COUNTS "))
        swapped[at],swapped[at+1]=swapped[at+1],swapped[at]
        protocol["flush-end-before-counts"]=log(swapped)
        for name,altered in protocol.items():
            try:parse(altered,0x101)
            except ValueError:checks["protocol-"+name]="REJECTED"
            else:raise AssertionError("ordered protocol accepted "+name)
        checks["actual-log-valid-multipass"]="PASS"
        cpp.write_text(fixture(source,True))
        cmd=[x for x in cmd if x!="-DRE4DC_SCENERY_SUBMIT_BATCH=1"]+["-DRE4DC_SCENERY_SUBMIT_BATCH=1"]
        subprocess.run(cmd,check=True,text=True)
        bad=subprocess.run(["/lib64/ld-linux-x86-64.so.2",str(exe)],capture_output=True,text=True)
        assert bad.returncode!=0 and "!sq" in bad.stderr,bad
        checks["mutation-log-before-batch-close"]="REJECTED"
        base=subprocess.check_output(["git","-C",str(ROOT),"show",BASE+":port/dreamcast/game/platform/native_static.cpp"],text=True)
        for knob in (None,"0"):
            outputs=[]
            for text in (base,source):
                # Full source directives/C++ text, includes removed identically. No SDK parse/image claim.
                text=re.sub(r'^\s*#\s*include[^\n]*','',text,flags=re.M)
                opts=["g++","-E","-P","-x","c++","-DRE4DC_SCENERY_CHUNK=1","-DRE4DC_PS2_WORLD_MESH=1","-DRE4DC_SCENERY_SELECT_ONLY=1",
                      "-D__sh__=1","-DRE4DC_MESH_DIRECT=1","-DRE4DC_NATIVE_MESH=1","-DRE4DC_SCENERY_REPLAY_LEAN=1","-DRE4DC_SCENERY_SUBMIT_BATCH=1",
                      "-DRE4DC_PS2_STRIP_GROUPS=1","-DRE4DC_PS2_WORLD_LEAN=23",
                      "-DRE4DC_MESH_LOD=1","-DRE4DC_MESH_FASTPATH=1","-DRE4DC_MESH_PRIME_LAZY=1",
                      "-DRE4DC_MESH_VP_SCHED=1","-DRE4DC_MESH_STRIP_LEAN=1","-DRE4DC_HW_LEAN=1","-"]
                if knob is not None:opts.insert(-1,"-DRE4DC_SCENERY_EMIT_CENSUS="+knob)
                r=subprocess.run(opts,input=text,text=True,capture_output=True)
                assert r.returncode==0,r.stderr
                outputs.append(r.stdout)
            assert outputs[0]==outputs[1]
            checks["off-source-directive-"+str(knob)]={"sha256":hashlib.sha256(outputs[0].encode()).hexdigest(),"result":"IDENTICAL"}
        baseline_make=temp/"baseline.mk";baseline_make.write_text(subprocess.check_output(["git","-C",str(ROOT),"show",BASE+":port/dreamcast/game/scenery19.mk"],text=True))
        def make(path,value=None,chunk="1"):
            f=temp/"Makefile";f.write_text("OBJDIR := obj\nSCENERY_CHUNK := "+chunk+"\nPS2_STRIP_GROUPS := 1\nPS2_WORLD_MESH := 1\ninclude "+str(path)+"\nobj/platform/native_static.o:\n\t@echo CMD $(PLATFORM_CPPFLAGS)\n")
            cmd=["make","-s","-f",str(f),"obj/platform/native_static.o"]
            if value is not None:cmd.append("SCENERY_EMIT_CENSUS="+value)
            return subprocess.run(cmd,text=True,capture_output=True)
        original=make(baseline_make).stdout
        for value in (None,"0"):
            r=make(MAKE,value);assert r.returncode==0 and r.stdout==original,r
        assert "RE4DC_SCENERY_EMIT_CENSUS=360" in make(MAKE,"360").stdout
        for value in ("-1","01","x","1 2","10000001",""):
            assert make(MAKE,value).returncode!=0,value
        assert make(MAKE,"360","0").returncode!=0
        checks["make-default-absent-zero"]="IDENTICAL"
        checks["make-invalid-values-and-dependency"]="REJECTED"
    receipt={"base":BASE,"source_sha256":hashlib.sha256(source.encode()).hexdigest(),
             "header_sha256":hashlib.sha256(HEADER.read_bytes()).hexdigest(),
             "parser_sha256":hashlib.sha256((HERE/"census.py").read_bytes()).hexdigest(),
             "test_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             "integration_review_profile":{"SCENERY_SUBMIT_BATCH":1,"PS2_PVS":0,"selected_affine":"unapplied/unadmitted"},
             "checks":checks,
             "limits":["host/extracted diagnostic integration only","no SDK, complete emitter FP, linked image, guest or target memory qualification"]}
    if out:Path(out).write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,indent=2))

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--output");args=ap.parse_args();run(args.output)
