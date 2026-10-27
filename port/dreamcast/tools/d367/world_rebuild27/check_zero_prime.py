#!/usr/bin/env python3
"""Host-consume the actual zero-prime emitter/restart/chunk source, OFF versus ON.

No SDK, guest, assets or timing model. Generated consumers/results stay in a new
private output directory. Stub dependencies observe admission, transforms, output,
census and failures; the actual emit_pick/chunk_emit/restart control flow is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def function(source, anchor):
    start = source.index(anchor)
    clean = re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                   lambda m: ' ' * len(m.group()), source)
    first = clean.index('{', start)
    depth = 0
    for end in range(first, len(clean)):
        depth += (clean[end] == '{') - (clean[end] == '}')
        if not depth:
            return source[start:end + 1]
    raise AssertionError('unclosed source function')


PRELUDE = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#define RE4DC_WORLD_ZERO_PRIME27 ZP
#define RE4DC_SCENERY_STREAM STREAM
#define RE4DC_SCENERY_EMIT_PREFETCH PREFETCH
#define RE4DC_SCENERY_DIRECT_STRIPS DIRECT
#define RE4DC_WORLD_METER OBSERVE
#define RE4DC_WORLD_CENSUS24 OBSERVE
#define RE4DC_SCN_CENSUS OBSERVE
#define RE4DC_SCENERY_REPLAY_LEAN 1
#define RE4DC_SCENERY_RECORD_SPLIT 0
#define RE4DC_SCENERY_DEDUP 0
#define RE4DC_PS2_PVS 0
constexpr unsigned PVR_CMD_VERTEX=0xe0000000U;
struct pvr_vertex_t { unsigned flags; float x,y,z,u,v; unsigned argb,oargb; };
struct Trace { std::string semantic; unsigned prime_entries=0,prime_calls=0; } trace;
void note(const std::string& s){trace.semantic+=s+';';}
struct Stats { unsigned groups_visible=0,bind_rejects=0,batches=0,reserve_rejects=0,strips=0,strips_culled=0; } stats;
unsigned scn_cen[7]{};
namespace lean { const pvr_vertex_t* prime_at=nullptr; unsigned primed=0; }
namespace re4dc::room {
struct CompactVertex12 { unsigned short q[6]; };
struct CompactBatch { float uv_bias[2]{},uv_scale[2]{}; };
}
namespace re4dc::wc24 {
enum Phase {Other,Transform,Submit,Transformed};
struct Scope { explicit Scope(Phase p){note("scope"+std::to_string(p));} ~Scope(){note("scope-end");} void phase(Phase p){note("phase"+std::to_string(p));} };
void count(Phase p,unsigned n){note("census"+std::to_string(p)+":"+std::to_string(n));}
}
namespace re4dc::vp {
using Vertex12=re4dc::room::CompactVertex12;
struct Constants{};
constexpr unsigned kChecksAll=3;
void prime(pvr_vertex_t* p,unsigned count){++trace.prime_calls;trace.prime_entries+=count;for(unsigned i=0;i<count;++i){p[i].flags=PVR_CMD_VERTEX;p[i].oargb=0;}}
void transform_one(const Vertex12& in,pvr_vertex_t& out,unsigned char& oc){
    assert(out.flags==PVR_CMD_VERTEX && out.oargb==0); // Every actual consumer requires demand priming.
    out.x=in.q[0];out.y=in.q[1];out.z=in.q[2];out.u=in.q[3];out.v=in.q[4];out.argb=in.q[5];oc=0;
}
template<unsigned Checks> void transform_sched(const Vertex12* in,unsigned count,pvr_vertex_t* cache,unsigned char* oc,const Constants&){
    note("plain-transform:"+std::to_string(count));for(unsigned i=0;i<count;++i)transform_one(in[i],cache[i],oc[i]);
}
void transform_sched_ix(const Vertex12* in,const unsigned short* ix,unsigned count,pvr_vertex_t* cache,unsigned char* oc,const Constants&){
    note("index-transform:"+std::to_string(count));for(unsigned i=0;i<count;++i)transform_one(in[ix[i]],cache[i],oc[i]);
}
}
void re4dc_wm_corners(const unsigned char*,unsigned n,unsigned mask){note("meter:"+std::to_string(n)+":"+std::to_string(mask));}
void re4dc_model_packet_commit(unsigned n){note("commit:"+std::to_string(n));}
void re4dc_model_result(unsigned a,unsigned b,unsigned c){note("result:"+std::to_string(a)+":"+std::to_string(b)+":"+std::to_string(c));}
int re4dc_model_packet_streaming(){note("streaming");return 1;}
struct Meshlet { unsigned first_vertex=0,strip_bytes=4;unsigned short vertex_count=4;bool indexed=false; };
struct Package {
    std::array<Meshlet,6> lets{};std::array<re4dc::room::CompactVertex12,256> verts{};std::array<unsigned short,256> offsets{};unsigned char strips_[4]{0,1,2,3};
    Package(){unsigned counts[6]={4,8,32,128,256,16};for(unsigned j=0;j<6;++j){lets[j].vertex_count=counts[j];lets[j].indexed=(j&1)!=0;}for(unsigned i=0;i<256;++i){offsets[i]=255-i;for(unsigned j=0;j<6;++j)verts[i].q[j]=i*6+j;}}
    const Meshlet* meshlets()const{return lets.data();} const auto* vertices()const{return verts.data();}
    bool indexed(const Meshlet& l)const{return l.indexed;}const unsigned short* pool_offsets(const Meshlet&)const{return offsets.data();}
    const unsigned char* strip_begin(const Meshlet&)const{return strips_;}
};
std::array<pvr_vertex_t,256> shared_cache;
struct Emitter {
    struct Pick { unsigned short let;unsigned char nr,gmask,lo,hi; };
    Package package;
    const unsigned* ps2=nullptr;
    bool lean_part=true,bound=false,submitted=false,streaming=false;
    bool fail_bind=false,fail_gather=false,fail_borrow=false,direct_return=false;
    unsigned used=0,input=0,output=0,slots=0,primed=0;
    pvr_vertex_t* cache=nullptr;unsigned char codes_[256]{};unsigned char* outcodes=codes_;
    const Meshlet* stream_l=nullptr;
    re4dc::room::CompactBatch batch,part;
    re4dc::vp::Constants k;
    unsigned short sg_records[6*16]{};const unsigned char* sg=reinterpret_cast<const unsigned char*>(sg_records);unsigned sg_groups=2;
    explicit Emitter(bool world=true){static unsigned key=1;ps2=world?&key:nullptr;for(unsigned i=0;i<6;++i){sg_records[i*16+6]=2;sg_records[i*16+14]=4;}}
    bool bind(){note("bind");if(fail_bind)return false;if(!bound){note("header");bound=true;}return true;}
    bool borrow_gather(){note("gather-admit");return !fail_gather;}
    bool borrow(){note("borrow");if(fail_borrow)return false;if(!cache){cache=shared_cache.data();primed=lean_part && lean::prime_at==cache?lean::primed:0;}return true;}
    const re4dc::room::CompactVertex12* corners(const Meshlet&){note("corners");return package.verts.data();}
    const re4dc::room::CompactVertex12* emit_corners(const Meshlet& l,const Pick&){note("decoder");return corners(l);}
    bool sequential_direct(const Meshlet&){note("direct-check");return direct_return;}
    void prefetch_emit_header(const Pick&){note("prefetch-header");}
    void prefetch_emit_payload(const Pick&){note("prefetch-payload");}
    void set_clip(){note("set-clip");}void* palette=nullptr;
    void strips_lean(const unsigned char* begin,const unsigned char* end,const re4dc::room::CompactVertex12*,re4dc::room::CompactBatch&,int& result){
        note("strip:"+std::to_string(begin-package.strips_)+":"+std::to_string(end-package.strips_));
        for(auto* p=begin;p<end;++p){const auto& v=cache[*p];assert(v.flags==PVR_CMD_VERTEX && v.oargb==0);unsigned words[8];std::memcpy(words,&v,sizeof words);for(unsigned w:words)note("word:"+std::to_string(w));}
        ++stats.strips;input+=unsigned(end-begin);output+=unsigned(end-begin);used+=unsigned(end-begin);result=strip_result;
    }
    int strip_result=1;
    // ACTUAL_METHODS
};
'''

TESTS = r'''
void reset(){trace={};stats={};for(auto& n:scn_cen)n=0;lean::prime_at=nullptr;lean::primed=0;std::memset(shared_cache.data(),0xcd,sizeof(shared_cache));}
void finish(const std::string& label,const std::vector<int>& returns,const Emitter& e){
    note("stats:"+std::to_string(stats.groups_visible)+":"+std::to_string(stats.bind_rejects)+":"+std::to_string(stats.batches)+":"+std::to_string(stats.reserve_rejects)+":"+std::to_string(stats.strips));
    for(unsigned n:scn_cen)note("scnc:"+std::to_string(n));for(int n:returns)note("return:"+std::to_string(n));
    std::cout<<"{\"case\":\""<<label<<"\",\"semantic\":\""<<trace.semantic<<"\",\"prime_entries\":"<<trace.prime_entries<<",\"prime_calls\":"<<trace.prime_calls<<",\"primed\":"<<e.primed<<",\"lean_primed\":"<<lean::primed<<"}\n";
}
Emitter::Pick pick(unsigned li,unsigned nr=255,unsigned lo=0,unsigned hi=3,unsigned mask=3){return {static_cast<unsigned short>(li),static_cast<unsigned char>(nr),static_cast<unsigned char>(mask),static_cast<unsigned char>(lo),static_cast<unsigned char>(hi)};}
int main(){
    for(bool world:{false,true})for(bool lean_part:{false,true}){
        const std::string prefix=std::string(world?"ps2":"generic")+(lean_part?"-shared":"-local");
        for(unsigned mode=0;mode<8;++mode){
            reset();Emitter e(world);e.lean_part=lean_part;std::vector<int> returns;
            std::vector<Emitter::Pick> stream;
            if(mode==0)stream={pick(3,0),pick(4)}; // Deferred writes: same eventual maximum.
            if(mode==1)stream={pick(3,0),pick(2)}; // Smaller consumer: surplus zero-pick prime is avoidable.
            if(mode==2)stream={pick(1,0),pick(3,0),pick(2,0)};
            if(mode==3)stream={pick(0),pick(3,0),pick(1)};
            if(mode==4)stream={pick(4),pick(2,0),pick(3)};
            if(mode==5)stream={pick(1,1,0,1,1),pick(3,0),pick(0,1,2,3,2)};
            if(mode==6)stream={pick(2,1,2,3,2),pick(0)};
            if(mode==7)stream={pick(3,0),pick(3,1,0,1,1),pick(3)};
            for(const auto& pk:stream)returns.push_back(e.emit_pick(pk));
            finish(prefix+"-sequence"+std::to_string(mode),returns,e);
        }
        for(unsigned failure=0;failure<3;++failure)for(bool submitted:{false,true}){
            reset();Emitter e(world);e.lean_part=lean_part;e.submitted=submitted;e.fail_bind=failure==0;e.fail_gather=failure==1;e.fail_borrow=failure==2;
            auto pk=pick(3,0);int r=e.emit_pick(pk);assert(r==(submitted?-1:0));assert(trace.prime_entries==0);
            finish(prefix+"-failure"+std::to_string(failure)+(submitted?"-submitted":"-fresh"),{r},e);
        }
        for(int outcome:{-1,0,1}){
            reset();Emitter e(world);e.lean_part=lean_part;e.strip_result=outcome;auto pk=pick(1,1,0,1,1);int r=e.emit_pick(pk);assert(r==outcome);
            finish(prefix+"-strip-result"+std::to_string(outcome),{r},e);
        }
        reset();Emitter e(world);e.lean_part=lean_part;e.used=0;int empty=e.chunk_emit(nullptr,0);assert(empty==1);assert(trace.prime_entries==0);assert(trace.semantic.find("result:0:0:0;")!=std::string::npos);
        finish(prefix+"-empty-emitter-once",{empty},e);
        reset();Emitter reused(world);reused.lean_part=lean_part;auto z=pick(3,0),full=pick(2);int a=reused.emit_pick(z);reused.chunk_restart();assert(!reused.bound && !reused.submitted && !reused.cache && !reused.primed && !reused.used && !reused.input && !reused.output && !reused.slots);int b=reused.emit_pick(full);
        finish(prefix+"-restart-zero-smaller",{a,b},reused);
        reset();Emitter first(world);first.lean_part=lean_part;int aa=first.emit_pick(z);Emitter next(world);next.lean_part=lean_part;int bb=next.emit_pick(full);
        finish(prefix+"-shared-next-emitter",{aa,bb},next);
        for(unsigned shape=0;shape<2;++shape){
            reset();Emitter chunk(world);chunk.lean_part=lean_part;std::vector<Emitter::Pick> picks=shape?std::vector<Emitter::Pick>{pick(1,1,0,1,1),pick(3,0),pick(0,1,2,3,2)}:std::vector<Emitter::Pick>{pick(3,0),pick(2)};
            int cr=chunk.chunk_emit(picks.data(),unsigned(picks.size()));assert(cr==1);
            finish(prefix+"-chunk-loop"+std::to_string(shape),{cr},chunk);
        }
        for(int outcome:{-1,0}){
            reset();Emitter aborting(world);aborting.lean_part=lean_part;aborting.strip_result=outcome;std::vector<Emitter::Pick> picks={pick(0),pick(3,0),pick(2)};
            int cr=aborting.chunk_emit(picks.data(),unsigned(picks.size()));assert(cr==outcome && stats.groups_visible==1);
            assert(trace.semantic.find("result:")==std::string::npos); // Actual chunk loop returns before success publication.
            finish(prefix+"-chunk-stop"+std::to_string(outcome),{cr},aborting);
        }
#if DIRECT
        reset();Emitter direct(world);direct.lean_part=lean_part;direct.direct_return=true;int dr=direct.emit_pick(full);assert(dr==1 && trace.prime_entries==0);finish(prefix+"-direct-shortcut",{dr},direct);
#endif
    }
}
'''


def main():
    # Negative consumers intentionally assert. Keep their artifacts confined to
    # this private evidence output instead of dumping cores in the caller tree.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    repo, out = a.repo.resolve(), a.out.resolve()
    assert not out.exists(), 'fresh private output required'
    assert out.parent == Path('/root/re4data/private/world-rebuild27-20261027')
    source_path = repo / 'port/dreamcast/game/platform/native_static.cpp'
    source = source_path.read_text()
    emit_start = source.index('    int emit_pick(const Pick& pk)')
    # The guarded prime has alternative opening braces across #if/#else.
    # Use its stable next-method boundary rather than counting both branches.
    emit = source[emit_start:source.index('\n#if RE4DC_SCENERY_REPLAY_LEAN\n    // CHUNK_REPLAY_RESTART', emit_start)]
    assert emit.count('RE4DC_WORLD_ZERO_PRIME27') == 2
    assert 'if((!ps2 || pk.nr!=0U) && l.vertex_count>primed)' in emit
    restart = function(source, '    [[gnu::always_inline]] void chunk_restart()')
    anchor = '    __attribute__((noinline)) int chunk_emit(const Pick* pk,unsigned n){'
    start = source.rfind('#if RE4DC_SCENERY_EMIT_PREFETCH', 0, source.index(anchor))
    end = source.index('\n#endif\n    int run(){', start)
    chunk = source[start:end]
    methods = emit + '\n' + restart + '\n' + chunk
    consumer = PRELUDE.replace('    // ACTUAL_METHODS', methods) + TESTS
    out.mkdir()
    (out / 'actual-methods.inc').write_text(methods)
    (out / 'consumer.cpp').write_text(consumer)
    configs = [dict(name='stream', STREAM=1, OBSERVE=0, PREFETCH=0, DIRECT=0),
               dict(name='stream-observers', STREAM=1, OBSERVE=1, PREFETCH=0, DIRECT=0),
               dict(name='nonstream', STREAM=0, OBSERVE=0, PREFETCH=0, DIRECT=0),
               dict(name='prefetch-direct-observers', STREAM=1, OBSERVE=1, PREFETCH=1, DIRECT=1)]
    results = []
    reference = None
    for config in configs:
        runs = []
        for zp in (0, 1):
            prefix = out / (config['name'] + '-' + str(zp))
            args = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-missing-field-initializers',
                    '-Wno-misleading-indentation', '-DZP=' + str(zp)]
            args += [f'-D{k}={v}' for k, v in config.items() if k != 'name']
            args += [str(out / 'consumer.cpp'), '-o', str(prefix)]
            compile_result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            prefix.with_suffix('.compile.txt').write_text(compile_result.stdout + compile_result.stderr)
            assert compile_result.returncode == 0, compile_result.stderr
            run = subprocess.run([str(prefix)], cwd=out, capture_output=True, text=True, timeout=10)
            prefix.with_suffix('.stdout.txt').write_text(run.stdout)
            prefix.with_suffix('.stderr.txt').write_text(run.stderr)
            assert run.returncode == 0, (config, zp, run.stderr)
            runs.append({r['case']: r for r in map(json.loads, run.stdout.splitlines())})
        off, on = runs
        if config['name'] == 'stream':
            reference = off
        assert off.keys() == on.keys()
        eliminated = deferred = 0
        for name in off:
            assert off[name]['semantic'] == on[name]['semantic'], (config['name'], name, 'semantic mismatch')
            assert on[name]['prime_entries'] <= off[name]['prime_entries'], (config['name'], name, 'increased priming')
            if name.startswith('generic'):
                assert off[name] == on[name], (config['name'], name, 'non-PS2 changed')
            if name.startswith('ps2') and '-sequence0' in name:
                assert off[name]['prime_entries'] == on[name]['prime_entries'] == 256
                deferred += 1
            if name.startswith('ps2') and '-sequence1' in name:
                assert off[name]['prime_entries'] == 128 and on[name]['prime_entries'] == 32
                eliminated += 1
            if name.startswith('ps2') and '-sequence2' in name:
                assert off[name]['prime_entries'] == 128 and on[name]['prime_entries'] == 0
                eliminated += 1
        results.append(dict(configuration=config, cases=len(off), semantic_parity='PASS',
                            deferred_only_examples=deferred, reduced_priming_examples=eliminated))
    # Generated consumer mutations only. Prove the consumer rejects loss of the
    # non-PS2 gate, failure to prime real consumers, and an unsafe early return.
    mutations = {
        'wrong-nonps2-gate': consumer.replace('(!ps2 || pk.nr!=0U)', '(pk.nr!=0U)'),
        'wrong-zero-predicate': consumer.replace('(!ps2 || pk.nr!=0U)', '(!ps2 || pk.nr==0U)'),
        'unsafe-early-return': consumer.replace('        ++stats.groups_visible;',
                                              '        if(ps2 && !pk.nr)return 1;\n        ++stats.groups_visible;')}
    negatives = []
    for name, mutant in mutations.items():
        assert mutant != consumer
        src = out / (name + '.cpp')
        src.write_text(mutant)
        exe = out / name
        cmd = ['g++', '-std=c++17', '-O2', '-DZP=1', '-DSTREAM=1', '-DOBSERVE=0', '-DPREFETCH=0', '-DDIRECT=0', str(src), '-o', str(exe)]
        build = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        assert build.returncode == 0, build.stderr
        run = subprocess.run([str(exe)], cwd=out, capture_output=True, text=True, timeout=10)
        (out / (name + '.stdout.txt')).write_text(run.stdout)
        (out / (name + '.stderr.txt')).write_text(run.stderr)
        rejected = run.returncode != 0
        if not rejected:
            got = {r['case']: r for r in map(json.loads, run.stdout.splitlines())}
            rejected = any(got[k]['semantic'] != reference[k]['semantic'] or
                           (k.startswith('generic') and got[k] != reference[k]) for k in reference)
        assert rejected, 'consumer failed to reject mutation ' + name
        negatives.append(dict(mutation=name, rejected=True, host_exit=run.returncode))
    receipt = dict(status='PASS', repo_commit=subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
                   helper_sha256=sha(Path(__file__).read_bytes()), source=str(source_path), source_sha256=sha(source.encode()),
                   extracted_actual_methods_sha256=sha(methods.encode()), consumer_sha256=sha(consumer.encode()),
                   cases=sum(r['cases'] for r in results), configs=results, negative_contract_tests=negatives,
                   scope='Actual emitter, restart and chunk control flow; stub admission/transform/strip dependencies. No SH4/PVR, runtime guest, asset or timing acceptance.',
                   limit='Zero-to-larger can only defer priming; zero-to-smaller/all-zero reduce surplus writes in the host model. Retained38zero-return/draw does not establish the count of expanding zero picks or saved milliseconds. No perf claim.')
    (out / 'RESULT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
