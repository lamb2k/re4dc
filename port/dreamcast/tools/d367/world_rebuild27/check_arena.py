#!/usr/bin/env python3
"""Host consumer of actual HOUSE_ARENA27 predicates and ExecOt; never launches SDK/guest.

OFF identity is a targeted HOUSE_ARENA27 conditional projection, preserving all
other directives, compared as C++ tokens against the named Git baseline. It is
not a substitute for SDK preprocessing/object identity. Outputs are private.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

BASE = '322d8bc4fab3d6dbf41237281ced5cd08266fb2f'
FILES = ['port/dreamcast/game/coarse.cpp', 'port/dreamcast/game/model_bridge.cpp',
         'port/dreamcast/game/platform/native_static.cpp',
         'port/dreamcast/game/platform/native_ui.cpp', 'src/game/trans.cpp', 'src/game/trans_ot.cpp',
         'port/dreamcast/game/platform/mem.cpp']

def sha(b):
    return hashlib.sha256(b).hexdigest()

TOKEN = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_]\w*|\d+(?:[.\w]*)|[^\s]')

def tokens(s):
    return [m.group() for m in TOKEN.finditer(s) if not m.group().startswith(('//', '/*'))]

def function(s, name):
    """Extract the complete actual definition, with comments/strings brace-safe."""
    hits = list(re.finditer(r'\b' + re.escape(name) + r'\s*\(', s))
    for m in hits:
        start = s.rfind('\n', 0, m.start()) + 1
        opening = s.find('{', m.end())
        semi = s.find(';', m.end())
        if opening < 0 or (semi >= 0 and semi < opening):
            continue
        depth = 0
        for t in TOKEN.finditer(s, opening):
            v = t.group()
            if v == '{': depth += 1
            if v == '}':
                depth -= 1
                if depth == 0: return s[start:t.end()]
    raise ValueError('definition missing: ' + name)

def off_projection(s):
    """Evaluate only arena conditionals. Ordinary nested #ifs stay verbatim."""
    stack, out = [], []
    for line in s.splitlines(True):
        t = line.strip()
        m = re.match(r'#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)', t)
        live = all(x[1] for x in stack)
        if m:
            op, arg = m.groups()
            if op in ('if', 'ifdef', 'ifndef'):
                arena = bool(re.search(r'\bRE4DC_HOUSE_ARENA27\b',arg))
                value = op == 'ifndef' if arena else True
                stack.append([arena, value])
                if not arena and live: out.append(line)
            elif op in ('else', 'elif'):
                if not stack: raise ValueError('unbalanced directive')
                if stack[-1][0]:
                    if op != 'else': raise ValueError('arena elif needs explicit parser support')
                    stack[-1][1] = not stack[-1][1]
                elif live: out.append(line)
            else:
                arena, _ = stack.pop()
                if not arena and all(x[1] for x in stack): out.append(line)
        elif live and not re.match(r'#\s*include\s+"(?:platform/)?(?:include/)?house_arena27.h"', t):
            out.append(line)
    if stack: raise ValueError('unbalanced directives')
    return ''.join(out)

def run(cmd, **kw):
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)
    if p.returncode: raise RuntimeError(' '.join(map(str, cmd)) + '\n' + p.stdout)
    return p.stdout

def compile_run(out, name, source, flags=()):
    cpp, exe = out / (name + '.cpp'), out / name
    cpp.write_text(source)
    run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', '-Wno-unused-variable', *flags, str(cpp), '-o', str(exe)])
    return run([str(exe)]).strip()

def brace_block(s, opening):
    depth=0
    for m in TOKEN.finditer(s,opening):
        if m.group()=='{': depth+=1
        elif m.group()=='}':
            depth-=1
            if depth==0:return s[opening:m.end()]
    raise ValueError('unbalanced source block')

def host_prefix(arena):
    return r'''
#include <cassert>
#include <cstdio>
#include <vector>
#define RE4DC_HOUSE_ARENA27 VALUE
#define RE4DC_PS2_WORLD_R11F_OWNER 1
#define RE4DC_PS2_WORLD_TRANSITION_OWNER 1
#define RE4DC_OT_PROF 1
using u16=unsigned short;
struct cModel { unsigned kindid=0,id=0,nParts=119,ot_type=7,be_flag=0; void* pList=(void*)1; void* pParts=(void*)2; };
struct Player:cModel{}; struct Global{unsigned room_id=0x101;};
Global global;Global* pG=&global;Player player;Player* pPL=&player;
int variant=0;extern "C" int re4dc_house_arena27_variant(){return variant;}
int model_calls,other_calls,begins,ends,profiles,alpha,stop_after=-1;
std::vector<int> events;
void ModelRender(cModel*){++model_calls;events.push_back(2);}
void Other(void*){++other_calls;events.push_back(9);}
struct OtData{void (*func)(void*);void* data;unsigned kind;OtData* next;};
struct OtWork{OtData* list;int max;unsigned prev_kind;};
constexpr int OT_MAX=23;OtWork g_OtWork[OT_MAX];int g_NowExecOtType=OT_MAX;
bool re4dc_source_world_callback_continue(){return stop_after<0 || ends<stop_after;}
bool re4dc_r11f_callback_continue(){return true;}
void re4dc_source_world_callback_begin(unsigned,OtData*,void(*)(void*),void*,unsigned){++begins;events.push_back(1);}
void re4dc_source_world_callback_end(){++ends;events.push_back(3);}
void GXSetAlphaCompare(int,int,int,int,int){++alpha;events.push_back(4);}
void otp_window(){}
unsigned long long re4dc_otp_now_us(){return 0;}
unsigned re4dc_stream_model_bytes_now(){return 0;}
void otp_add(void*,void*,unsigned,unsigned,unsigned){++profiles;events.push_back(5);}
'''.replace('VALUE', str(arena))

def log_checks(out, source):
    """Actual writer/helpers with separate cached/physical host backing stores.

    Only target-layout fixture declarations normalize unsigned long to uint32_t
    for the LP64 host. Actual writer/helper text is unchanged.
    """
    alias=function(source,'arena27_log_alias')
    startup=function(source,'arena27_log_startup')
    raw=function(source,'re4dc_log_raw')
    head_decl=re.search(r'struct alignas\(32\) Arena27LogHeadLine[^\n]+',source).group()
    ring_decl=re.search(r'struct Re4dcLogRing[^\n]+',source).group().replace('unsigned long','uint32_t')
    prefix=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <vector>
#include <string>
#include <climits>
#define RE4DC_HOUSE_ARENA27 1
#define RE4DC_HOUSE_ARENA27_LOG_HOST_TEST 1
#define RE4DC_LOG_ATOMIC _ATOMIC_
#define RE4DC_LOG_RING_HDR _HEADER_
#define RE4DC_LOG_TRIM _TRIM_
#define RE4DC_LOG_SIZE (0x10000-RE4DC_LOG_TRIM)
HEAD_DECL
Arena27LogHeadLine re4dc_arena27_log_head_line,physical_head;
#define re4dc_log_head re4dc_arena27_log_head_line.value
#if RE4DC_LOG_RING_HDR
RING_DECL
alignas(32) Re4dcLogRing re4dc_logring,physical_ring;
#define re4dc_logbuf re4dc_logring.buf
unsigned char* cached_begin=(unsigned char*)&re4dc_logring;
unsigned char* physical_begin=(unsigned char*)&physical_ring;
constexpr unsigned total_bytes=sizeof(Re4dcLogRing);
char* physical_buf=physical_ring.buf;
#else
alignas(32) char re4dc_logbuf[RE4DC_LOG_SIZE],physical_buf[RE4DC_LOG_SIZE];
unsigned char* cached_begin=(unsigned char*)re4dc_logbuf;
unsigned char* physical_begin=(unsigned char*)physical_buf;
constexpr unsigned total_bytes=RE4DC_LOG_SIZE;
#endif
struct Event{uintptr_t address;unsigned count;bool wb;};std::vector<Event> cache_events;
unsigned irq_state=0,disable_calls=0,restore_calls=0;bool pending=false,request=false;
void re4dc_log_raw(const char*,unsigned long);
int irq_disable(){int saved=irq_state;irq_state=0x100000f0U;++disable_calls;return saved;}
void irq_restore(int saved){assert(irq_state==0x100000f0U);irq_state=unsigned(saved);++restore_calls;if(!irq_state&&pending){pending=false;re4dc_log_raw("IRQ\n",4);}}
uintptr_t map_address(uintptr_t address){
 const auto begin=reinterpret_cast<uintptr_t>(cached_begin),head=reinterpret_cast<uintptr_t>(&re4dc_arena27_log_head_line);
 if(address>=begin&&address<begin+total_bytes)return reinterpret_cast<uintptr_t>(physical_begin)+(address-begin);
 if(address>=head&&address<head+sizeof(Arena27LogHeadLine))return reinterpret_cast<uintptr_t>(&physical_head)+(address-head);
 assert(false);return 0;}
uintptr_t re4dc_house_arena27_log_test_alias(uintptr_t address){assert(irq_state==0x100000f0U);if(request){pending=true;request=false;}return map_address(address);}
void dcache_wback_range(uintptr_t address,unsigned count){assert(irq_state==0x100000f0U);assert(count&&count<=16384&&address%32==0&&count%32==0);cache_events.push_back({address,count,true});std::memcpy(reinterpret_cast<void*>(map_address(address)),reinterpret_cast<void*>(address),count);}
void dcache_inval_range(uintptr_t address,unsigned count){assert(irq_state==0x100000f0U);assert(!cache_events.empty());auto e=cache_events.back();assert(e.wb&&e.address==address&&e.count==count);cache_events.push_back({address,count,false});}
'''.replace('HEAD_DECL',head_decl).replace('RING_DECL',ring_decl)
    tests=r'''
int main(){
 static_assert(sizeof(Arena27LogHeadLine)==32&&alignof(Arena27LogHeadLine)==32);
 assert(sizeof(re4dc_log_head)==4);
 std::memset(cached_begin,0,total_bytes);std::memset(physical_begin,0xA5,total_bytes);physical_head.value=0xDEADBEEF;
 re4dc_log_raw(nullptr,0);assert(physical_head.value==0&&re4dc_log_head==0);
 assert(disable_calls==1&&restore_calls==1&&irq_state==0);
 const unsigned init_events=cache_events.size();assert(init_events==2*((total_bytes+16383)/16384+1));
 uintptr_t next=reinterpret_cast<uintptr_t>(cached_begin);unsigned covered=0;
 for(unsigned i=0;i<init_events-2;i+=2){assert(cache_events[i].address==next);next+=cache_events[i].count;covered+=cache_events[i].count;}assert(covered==total_bytes);
 assert(cache_events[init_events-2].address==reinterpret_cast<uintptr_t>(&re4dc_arena27_log_head_line));
#if RE4DC_LOG_RING_HDR
 assert(physical_ring.magic==0x5A53474CU&&physical_ring.nmagic==~uint32_t(0x5A53474CU)&&physical_ring.size==RE4DC_LOG_SIZE);
 assert(re4dc_logring.magic==0); // metadata writes are uncached too
#endif
 std::vector<char> oracle(RE4DC_LOG_SIZE,0);uint32_t position=0;
 auto expected=[&](const char* data,unsigned len){for(unsigned i=0;i<len;++i){oracle[position%RE4DC_LOG_SIZE]=data[i];++position;}};
 auto equal=[&](){assert(physical_head.value==position);assert(!std::memcmp(oracle.data(),physical_buf,RE4DC_LOG_SIZE));assert(re4dc_log_head==0);assert(cache_events.size()==init_events);};
 const char binary[]={'A','\0','B','\n'};re4dc_log_raw(binary,sizeof(binary));expected(binary,sizeof(binary));equal();
 std::vector<char> long_input(2*RE4DC_LOG_SIZE+87);for(unsigned i=0;i<long_input.size();++i)long_input[i]=char((i*37)%256);
 re4dc_log_raw(long_input.data(),long_input.size());expected(long_input.data(),long_input.size());equal();
 request=true;re4dc_log_raw("outer\n",6);expected("outer\n",6);expected("IRQ\n",4);equal();assert(!pending);
 irq_state=0x100000f0U;re4dc_log_raw("masked\n",7);expected("masked\n",7);equal();assert(irq_state==0x100000f0U);irq_state=0;
 physical_head.value=position=UINT32_MAX-2;re4dc_log_raw(binary,sizeof(binary));expected(binary,sizeof(binary));equal();assert(position==1);
 assert(disable_calls==restore_calls);for(unsigned i=0;i<total_bytes;++i)assert(cached_begin[i]==0);
 puts("actual raw logger PASS: physical-only bytes/head/header, first bounded WB/inval once, IRQ/restoration/deferred interrupt, empty/binary/long/ring+uint32 wrap");}
'''
    result={}
    mutation_program=None
    for hdr,trim in ((0,0),(0,24576),(1,0),(1,24576)):
        program=prefix.replace('_ATOMIC_','1').replace('_HEADER_',str(hdr)).replace('_TRIM_',str(trim))
        program+=alias+'\n'+startup+'\n'+raw+'\n'+tests
        if not hdr and not trim:mutation_program=program
        name=f'log_h{hdr}_t{trim}'
        try:result[name]={'pass':True,'stdout':compile_run(out,name,program,('-Wno-overflow',))}
        except RuntimeError as e:result[name]={'pass':False,'error':str(e)}
    for sh in (0,1):
        p='#include <cstdint>\n#include <cassert>\n#include <cstdio>\n'+('#define __sh__ 1\n' if sh else '')+alias
        p+='\nint main(){for(uintptr_t p:{uintptr_t(0x8c000000U),uintptr_t(0x8c1234a0U),uintptr_t(0x8cffffffU)})assert(arena27_log_alias(p)==EXPECTED);puts("actual alias arithmetic PASS");}'
        p=p.replace('#include <cstdint>','#include <cstdint>\n#include <initializer_list>').replace('EXPECTED','(p|uintptr_t(0xa0000000U))' if sh else 'p')
        name='log_alias_sh'+str(sh)
        try:result[name]={'pass':True,'stdout':compile_run(out,name,p)}
        except RuntimeError as e:result[name]={'pass':False,'error':str(e)}
    for name,before,after in (
        ('cached_write','return re4dc_house_arena27_log_test_alias(address);','return address;'),
        ('repeated_init','coherent=true;','coherent=false;'),
        ('no_irq','const int irq = irq_disable();','const int irq = 0;')):
        mutated=mutation_program.replace(before,after)
        assert mutated!=mutation_program
        name='log_mutation_'+name
        try:
            compile_run(out,name,mutated,('-Wno-overflow',))
            result[name]={'pass':False,'error':'mutant accepted'}
        except RuntimeError as e:
            result[name]={'pass':(out/name).exists() and 'Assertion' in str(e),'diagnostic':str(e)}
    return result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tree', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--baseline', default=BASE)
    ap.add_argument('--private-header', type=Path)
    ap.add_argument('--asset-root', type=Path, help='Actual private arena root with native/r101/arena0..2 and certificates')
    args = ap.parse_args()
    tree, out = args.tree.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    result = {'scope':'HOST/SOURCE ONLY; no SDK, emulator or timing claim', 'baseline':args.baseline,
              'head':run(['git','-C',str(tree),'rev-parse','HEAD']).strip(), 'source':{}, 'off_tokens':{}, 'host':{}}
    sources = {}
    for rel in FILES:
        data = (tree / rel).read_bytes(); s = data.decode(); sources[rel]=s
        base = run(['git','-C',str(tree),'show',args.baseline+':'+rel])
        result['source'][rel]=sha(data)
        projected, original = tokens(off_projection(s)), tokens(base)
        result['off_tokens'][rel]={'pass':projected==original,'tokens':len(projected)}
        if projected != original:
            first=next((i for i,(a,b) in enumerate(zip(projected,original)) if a!=b),min(len(projected),len(original)))
            result['off_tokens'][rel]['first_difference']={'token':first,'current':projected[max(0,first-5):first+6],'baseline':original[max(0,first-5):first+6]}
    bridge=sources[FILES[1]]; static=sources[FILES[2]]; ot=sources[FILES[5]]
    funcs='\n'.join(function(bridge,n) for n in ('re4dc_house_arena27_active','re4dc_house_arena27_model'))
    exec_ot=function(ot,'ExecOt')
    mutations=[]
    predicate_tests=r'''
int main(){
 for(int v=0;v<3;++v){variant=v;assert(re4dc_house_arena27_active());assert(re4dc_house_arena27_model(pPL));cModel imposter;assert(!re4dc_house_arena27_model(&imposter));assert(!re4dc_house_arena27_model(nullptr));}
 variant=0;pPL=nullptr;assert(!re4dc_house_arena27_model(&player));pPL=&player;
 pG=nullptr;assert(!re4dc_house_arena27_active());pG=&global;
 global.room_id=0x100;assert(!re4dc_house_arena27_active());global.room_id=0x101;
 for(int v:{-1,3,2147483647}){variant=v;assert(re4dc_house_arena27_active());cModel other;assert(!re4dc_house_arena27_model(&other));}
 variant=0;player.nParts=141;assert(!re4dc_house_arena27_model(pPL));player.nParts=119;
 player.kindid=1;assert(!re4dc_house_arena27_model(pPL));player.kindid=0;
 player.id=1;assert(!re4dc_house_arena27_model(pPL));player.id=0;
 puts("actual model predicates PASS: variants, null, impersonator, invalid variant, wrong player shape");
}
'''
    # Strict negative contracts deliberately fail until runtime fixes land.
    for name, source in [('model_contract',host_prefix(1)+funcs+predicate_tests)]:
        try: result['host'][name]={'pass':True,'stdout':compile_run(out,name,source)}
        except RuntimeError as e: result['host'][name]={'pass':False,'error':str(e)}
    mutations.append(('model_identity',host_prefix(1)+funcs.replace('m==static_cast<const cModel*>(pPL)','true')+predicate_tests))
    for arena in (0,1):
        tests=r'''
void reset(){model_calls=other_calls=begins=ends=profiles=alpha=0;stop_after=-1;events.clear();}
int main(){
 cModel other;
 OtData a[4]={{(void(*)(void*))ModelRender,&player,11,&a[1]},
 {(void(*)(void*))ModelRender,&other,12,&a[2]}, {Other,&other,13,&a[3]}, {Other,nullptr,14,nullptr}};
 for(int table=0;table<OT_MAX;++table){reset();g_OtWork[table]={a,1,99};int n=ExecOt(table);
 assert(n==3&&begins==3&&ends==3&&profiles==3&&alpha==1&&g_NowExecOtType==OT_MAX&&g_OtWork[table].prev_kind==13);
 if(ARENA){assert(other_calls==0);assert(model_calls==((table==0xB||table==0xD||table==0x11)?1:0));}else{assert(other_calls==1&&model_calls==2);}}
 reset();g_OtWork[0x11]={a,1,99};stop_after=1;assert(ExecOt(0x11)==1);assert(begins==1&&ends==1&&profiles==1&&alpha==1&&g_NowExecOtType==OT_MAX);
 assert(g_OtWork[0x11].prev_kind==0); // existing abort-before-prev_kind semantics
 reset();g_OtWork[0x11]={a,1,99};stop_after=0;assert(ExecOt(0x11)==0);assert(begins==0&&ends==0&&alpha==1&&g_NowExecOtType==OT_MAX);
 puts("actual ExecOt PASS: all tables, allowed/dropped/null entries, observer balance, cleanup, abort-before/after");}
'''.replace('ARENA',str(arena))
        name='exec_ot_'+str(arena)
        try: result['host'][name]={'pass':True,'stdout':compile_run(out,name,host_prefix(arena)+funcs+exec_ot+tests)}
        except RuntimeError as e: result['host'][name]={'pass':False,'error':str(e)}
        if arena: mutations.append(('callback_admission',host_prefix(1)+funcs+exec_ot.replace('if(!re4dc_house_arena27_active() ||','if(true ||')+tests))
    # Actual constexpr consumers; use real private table where supplied, otherwise
    # clearly mark synthetic fixtures (never asset/header acceptance).
    helper='\n'.join(function(static,n) for n in ('placement','matches'))
    header=args.private_header or (args.asset_root/'world_rebuild27_arena.inc' if args.asset_root else None)
    arrays=header.read_text() if header else 'constexpr unsigned placements[]={1,7,222}; constexpr unsigned mesh_identity[3][2]={{11,101},{22,202},{33,303}}; constexpr unsigned textures[2][4]={{1,2,3,4},{5,6,7,8}};'
    tests=r'''
int main(){
 for(unsigned i=0;i<3;++i){assert(matches(i,mesh_identity[i][0],mesh_identity[i][1]));assert(!matches(i,mesh_identity[i][0]^1U,mesh_identity[i][1]));assert(!matches(i,mesh_identity[i][0],mesh_identity[i][1]+1));}
 assert(!matches(-1,0,0)&&!matches(3,0,0));
 for(unsigned p:placements){assert(placement(p));}assert(!placement(~0U));
 for(unsigned p=0;p<1000;++p){bool expect=false;for(unsigned q:placements)expect|=p==q;assert(placement(p)==expect);}
 puts("actual package/placement predicates PASS: exact rows, wrong CRC/bytes/variant, complete placement domain");}
'''
    try:
        result['host']['package_helpers']={'pass':True,'fixture':'actual private header' if header else 'synthetic contract only','stdout':compile_run(out,'package_helpers','#include <cassert>\n#include <cstdio>\n'+arrays+'\n'+helper+tests)}
    except RuntimeError as e: result['host']['package_helpers']={'pass':False,'error':str(e)}
    mutations.append(('package_crc', '#include <cassert>\n#include <cstdio>\n'+arrays+'\n'+helper.replace('mesh_identity[variant][0]==crc','true')+tests))
    try:
        open_body=function(static,'ps2_open')
        pos=open_body.index('if(ps2w.room==0x101U){')
        end=open_body.index('{',pos)
        actual_if=open_body[pos:end]+brace_block(open_body,end)
        package_program=r'''
#include <cassert>
#include <cstdio>
#include <cstring>
int variant,missing;struct {unsigned room=0x101;}ps2w;
int re4dc_house_arena27_variant(){return variant;}
void re4dc_missing(const char*){++missing;}
void re4dc_log(const char*,...){}
char mpath[48],ppath[48];
bool open_test(){ACTUAL;return true;}
int main(){for(int v:{-1,3,2147483647}){variant=v;missing=0;assert(!open_test()&&missing==1);}
for(int v=0;v<3;++v){variant=v;missing=0;assert(open_test()&&missing==0);char wanted[48];snprintf(wanted,48,"/cd/dc/native/r101/arena%d/ps2-world.re4mesh",v);assert(!strcmp(wanted,mpath));snprintf(wanted,48,"/cd/dc/native/r101/arena%d/ps2-world.r4pw",v);assert(!strcmp(wanted,ppath));}
puts("actual package routing PASS: all three paths and invalid variant refusal");}
'''.replace('ACTUAL',actual_if).replace('#include <cstring>','#include <cstring>\n#include <initializer_list>')
        result['host']['package_path']={'pass':True,'stdout':compile_run(out,'package_path',package_program)}
        passbody=function(static,'ps2_pass')
        gate=re.search(r'if\(ps2w.room==0x101U && !re4dc::house_arena27::placement\(i\)\)continue;',passbody)
        if not gate:raise ValueError('placement admission missing')
        placement_program='#include <cassert>\n#include <cstdio>\n#include <vector>\nnamespace re4dc::house_arena27{'+arrays+helper+'}\n'
        placement_program+='struct{unsigned room=0x101,nplacements=223;}ps2w;std::vector<unsigned> selected;void test(){for(unsigned i=0;i<ps2w.nplacements;++i){'+gate.group()+'selected.push_back(i);}}\n'
        placement_program+='int main(){for(unsigned n=0;n<225;++n){ps2w.nplacements=n;selected.clear();test();unsigned j=0;for(unsigned i=0;i<n;++i)if(re4dc::house_arena27::placement(i)){assert(j<selected.size()&&selected[j++]==i);}assert(j==selected.size());}ps2w.room=0x100;selected.clear();test();assert(selected.size()==ps2w.nplacements);puts("actual placement admission PASS: ordered whitelist, truncated/empty/extended iteration bounds, other-room passthrough");}'
        result['host']['placement_bounds']={'pass':True,'stdout':compile_run(out,'placement_bounds',placement_program)}
    except (RuntimeError,ValueError) as e: result['host']['package_path_and_bounds']={'pass':False,'error':str(e)}
    # Compile actual leading guards at direct native entry boundaries. The rest
    # of each SDK renderer is replaced by a counter, not reimplemented.
    ui=sources[FILES[3]]
    api=[('re4dc_ui_glyph','void'),('re4dc_ui_submit','void'),
         ('re4dc_effect_sprite','int'),('re4dc_subscreen_quad','int'),
         ('re4dc_subscreen_line','int'),('re4dc_water45_quad','int'),
         ('re4dc_ui_tr_packet','int'),('re4dc_post_filter00','void')]
    guards=[]
    try:
        for name, ret in api:
            body=function(ui,name).split('{',1)[1]
            m=re.match(r'\s*(#if[^\n]*RE4DC_HOUSE_ARENA27[^\n]*\n[\s\S]*?#endif)',body)
            if not m: raise ValueError('missing leading arena guard: '+name)
            guards.append(ret+' test_'+name+'(){\n'+m.group(1)+'\n++writes;'+('return 7;' if ret=='int' else '')+'}\n')
        test='int main(){variant=0;\n'
        for name,ret in api:
            test+='writes=0;'+('assert(test_'+name+'()==1);' if ret=='int' else 'test_'+name+'();')+'assert(writes==0);\n'
        test+='global.room_id=0x100;\n'
        for name,ret in api:
            test+='writes=0;'+('assert(test_'+name+'()==7);' if ret=='int' else 'test_'+name+'();')+'assert(writes==1);\n'
        test+='puts("actual native direct guards PASS: eight entry boundaries, handled return, no write, inactive passthrough");}'
        result['host']['native_direct_guards']={'pass':True,'stdout':compile_run(out,'native_direct_guards',host_prefix(1)+funcs+'\nint writes;\n'+''.join(guards)+test)}
    except (RuntimeError,ValueError) as e: result['host']['native_direct_guards']={'pass':False,'error':str(e)}
    result['host'].update(log_checks(out,sources[FILES[6]]))
    if args.asset_root:
        root=args.asset_root.resolve()
        (out/'kos').mkdir()
        (out/'kos/fs.h').write_text('#pragma once\ntypedef int file_t;\n#define FILEHND_INVALID (-1)\n')
        asset_source=r'''
#include "instanced_mesh.hpp"
#include "world_rect_provenance.h"
#include <cassert>
#include <fstream>
#include <iterator>
#include <vector>
#include <string>
#include <cstdio>
namespace arena { ARRAYS HELPERS }
std::vector<unsigned char> read(const std::string& path){std::ifstream f(path,std::ios::binary);return {(std::istreambuf_iterator<char>(f)),{}};}
unsigned crc32(const unsigned char* p,unsigned n){unsigned c=~0U;while(n--){c^=*p++;for(unsigned k=0;k<8;++k)c=(c>>1)^((0U-(c&1U))&0xedb88320U);}return ~c;}
int main(){
for(int arm=0;arm<3;++arm){std::string path=ROOT+std::string("/native/r101/arena")+std::to_string(arm)+"/";
auto mesh=read(path+"ps2-world.re4mesh"),world=read(path+"ps2-world.r4pw");
assert(mesh.size()>=80&&world.size()>=32);
re4dc::room::MeshPackage package;assert(package.adopt(mesh.data(),unsigned(mesh.size()),true,true));
const auto& h=package.header();
auto admit=[&](unsigned room,unsigned crc,unsigned bytes){return room==0x101U&&arena::matches(arm,crc,bytes)&&re4dc::rect21::provenance::policy_source_crc(room,world.data(),unsigned(world.size()),crc,bytes,h.part_count,h.mesh_count,mesh.data(),crc32)==0x68100b21U;};
assert(admit(0x101,h.crc,h.bytes));assert(!admit(0x100,h.crc,h.bytes));assert(!admit(0x101,h.crc^1U,h.bytes));assert(!admit(0x101,h.crc,h.bytes+1));
unsigned places=re4dc::rect21::provenance::word(world.data()+8);
assert(places==223);for(unsigned p:arena::placements)assert(p<places);
for(unsigned at:{0U,8U,12U,16U,20U,80U,unsigned(mesh.size()-1U)}){mesh[at]^=1;assert(!admit(0x101,h.crc,h.bytes));mesh[at]^=1;}
for(unsigned at:{0U,4U,8U,12U,16U,20U,24U,28U,40U,unsigned(world.size()-1U)}){world[at]^=1;assert(!admit(0x101,h.crc,h.bytes));world[at]^=1;}
printf("actual arena arm%d MeshPackage+full-body/policy authentication PASS; %u bytes, %u parts, %u placements; mutations refused\n",arm,h.bytes,h.part_count,places);
}}
'''.replace('ARRAYS',arrays).replace('HELPERS',helper).replace('ROOT',json.dumps(str(root)))
        flags=['-DRE4DC_SCENERY_N256=1','-DRE4DC_WORLD_SG26=1','-DRE4DC_WORLD_REBUILD27=1',
               '-I'+str(out),'-I'+str(tree/'port/dreamcast/room'),'-I'+str(tree/'port/dreamcast/game/platform/include'),'-I'+str(tree/'port/dreamcast/tools/d367/texture_rect21'),'-I'+str(root)]
        try:
            result['host']['actual_assets']={'pass':True,'stdout':compile_run(out,'actual_assets',asset_source,flags)}
            paths=[root/'world_rebuild27_arena.inc',root/'world_rebuild27_certificates.inc']
            paths += [root/f'native/r101/arena{i}/ps2-world.{ext}' for i in range(3) for ext in ('re4mesh','r4pw','r4sg')]
            result['asset_sha256']={str(p):sha(p.read_bytes()) for p in paths}
        except (RuntimeError,OSError) as e: result['host']['actual_assets']={'pass':False,'error':str(e)}
    result['mutations']={}
    for name,program in mutations:
        try:
            compile_run(out,'mutation_'+name,program)
            result['mutations'][name]={'rejected':False}
        except RuntimeError as e:
            # Compiler rejection is not evidence that a behavioral mutation
            # test detected anything. Require a produced executable + assertion.
            rejected=(out/('mutation_'+name)).exists() and 'Assertion' in str(e)
            result['mutations'][name]={'rejected':rejected,'diagnostic':str(e)}
    result['source_readback_identical']=all(sha((tree/p).read_bytes())==digest for p,digest in result['source'].items())
    result['helper_sha256']=sha(Path(__file__).read_bytes())
    result['compiler']=run(['g++','--version']).splitlines()[0]
    result['pass']=result['source_readback_identical'] and all(x['pass'] for group in ('off_tokens','host') for x in result[group].values()) and all(x['rejected'] for x in result['mutations'].values())
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if result['pass'] else 1

if __name__=='__main__': raise SystemExit(main())
