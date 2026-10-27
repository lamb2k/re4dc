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
         'port/dreamcast/game/platform/native_ui.cpp', 'src/game/trans.cpp', 'src/game/trans_ot.cpp']

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
                arena = 'RE4DC_HOUSE_ARENA27' in arg
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
