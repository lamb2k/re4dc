#!/usr/bin/env python3
"""Execute production world admission and shared-strip audit sites on host.

The selector's chunk_ok and the chunk-submit outcode/dispatch functions are
extracted verbatim. Only the final SQ writer and callback use bounded test
sinks. Verify first-refusal precedence, intentional culls, null callbacks,
capacity/depth precedence, callback failure propagation and paused counters.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    helper_path = DC / "tools/d367/world_submit_spike/check_runtime.py"
    spec = importlib.util.spec_from_file_location("world26_sites_extract", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    selector = DC / "game/platform/include/scenery_chunk_select.inc"
    backend = DC / "game/platform/chunk_submit.cpp"
    chunk = backend.read_text()
    extracted = {
        "SELECTOR": helper.function(selector.read_text(), "bool chunk_ok()const"),
        "CODES": helper.function(chunk, "inline re4dc::vp::StripCodes codes_of("),
        "STRIPS": helper.function(chunk, "int re4dc_chunk_strips("),
    }
    source = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include "@DC@/game/platform/include/draw_fallback_audit.h"
#include "@DC@/game/platform/chunk_submit.h"
namespace re4dc { namespace dfa26 {
bool active=true;
std::uint32_t live[ReasonCount]{},overflow=0;
} namespace vp { struct StripCodes { unsigned all,any; }; } }
using namespace re4dc::dfa26;
namespace lean { unsigned kMode=0; }
struct Selector {
    struct Package { bool value=true; bool lod()const{return value;} } package;
    unsigned sg_groups=4,pc_mode=0;
    const void* pvs_set=nullptr;
    std::uint64_t skip_clusters=0;
@SELECTOR@
};
struct pvr_vertex_t { std::uint32_t words[8]; };
constexpr unsigned kDepth=3,kScreen=60;
unsigned sent=0,clipped=0;
std::uint32_t* send(std::uint32_t* sq,const pvr_vertex_t*,const std::uint8_t*,unsigned n,unsigned){sent+=n;return sq;}
@CODES@
@STRIPS@
void clear(){std::memset(live,0,sizeof(live));sent=clipped=0;}
int callback(void* context,const std::uint8_t*,unsigned,unsigned){++clipped;return *static_cast<int*>(context);}
unsigned total(){unsigned n=0;for(auto value:live)n+=value;return n;}
int main(){
    unsigned selects=0,strips=0;
    const Reason reasons[]={WorldChunkNoLod,WorldChunkCheckMode,WorldChunkGroups,
        WorldChunkPvs,WorldChunkInterior,WorldChunkImpostor};
    for(unsigned enabled=0;enabled<2;++enabled)for(unsigned bits=0;bits<64;++bits){
        clear();active=enabled;Selector s;
        s.package.value=!(bits&1);lean::kMode=bits&2?8:0;s.sg_groups=bits&4?9:4;
        s.pvs_set=bits&8?&s:nullptr;s.pc_mode=bits&16?1:0;s.skip_clusters=bits&32?1:0;
        assert(s.chunk_ok()==!bits);
        if(bits && enabled){unsigned first=0;while(!(bits&(1U<<first)))++first;
            assert(live[reasons[first]]==1 && total()==1);
        }else assert(total()==0);
        ++selects;
    }
    const std::uint8_t cases[][4]={{0,0,0,0},{2,2,2,2},{1,1,1,1},{2,0,0,0},
        {1,0,0,0},{3,0,0,0},{4,4,4,4},{32,32,32,32},{4,0,0,0},{2,1,0,0}};
    for(unsigned enabled=0;enabled<2;++enabled)for(unsigned form=0;form<2;++form)
    for(unsigned n=3;n<5;++n)for(unsigned limit: {2U,4U})for(const auto& codes:cases)
    for(int result=-1;result<3;++result){
        clear();active=enabled;std::uint32_t sq[8]{};pvr_vertex_t vertices[4]{};
        re4dc_chunk_sink sink{};sink.sq=sq;sink.limit=limit;sink.vsrc=vertices;sink.csrc=codes;
        sink.clip=result==2?nullptr:callback;sink.clip_ctx=&result;
        std::uint8_t input[5]{};unsigned bytes=n;
        if(form==RE4DC_CHUNK_STRIPS_R4IM){input[0]=n;++bytes;for(unsigned i=0;i<n;++i)input[1+i]=i;}
        else {for(unsigned i=0;i<n;++i)input[i]=i;input[n-1]|=128;}
        unsigned any=0,all=255;for(unsigned i=0;i<n;++i){any|=codes[i];all&=codes[i];}
        const bool slow=!(all&kDepth) && ((any&kDepth) || n>limit);
        const bool called=slow && result!=2;
        const int got=re4dc_chunk_strips(&sink,input,bytes,form);
        assert(got==(called && result<=0?result:1));
        assert(clipped==unsigned(called));
        assert(total()==unsigned(called && enabled));
        if(called && enabled)assert(live[n>limit?ChunkClipCapacity:ChunkClipDepth]==1);
        assert(sink.clipped==unsigned(slow));
        assert(sent==(!(all&kDepth) && !slow && !(all&kScreen)?n:0));
        ++strips;
    }
    std::printf("{\"selector_cases\":%u,\"strip_cases\":%u}\n",selects,strips);
}
'''.replace("@DC@", str(DC))
    source = source.replace("#include <cstdio>", "#include <cstdio>\n#include <initializer_list>")
    for key, value in extracted.items():
        source = source.replace("@" + key + "@", value)
    (out / "sites.cpp").write_text(source)
    command = ["g++", "-std=c++20", "-O2", "-Wall", "-Wextra",
        "-DRE4DC_DRAW_FALLBACK_AUDIT=1", "-DRE4DC_PS2_PVS=1",
        "-DRE4DC_PS2_INTERIOR_CULL=1", "-DRE4DC_QUALITY_ASSETS=1",
        str(out / "sites.cpp"), "-o", str(out / "sites")]
    built = subprocess.run(command, capture_output=True)
    (out / "compile.log").write_bytes(built.stdout + built.stderr)
    assert built.returncode == 0, built.stderr.decode()
    run = subprocess.run([str(out / "sites")], capture_output=True)
    (out / "stdout").write_bytes(run.stdout)
    (out / "stderr").write_bytes(run.stderr)
    assert run.returncode == 0, run.stderr.decode()
    inputs = [Path(__file__), helper_path, selector, backend,
        DC / "game/platform/include/draw_fallback_audit.h",
        *sorted((DC / "game/platform/include").glob("draw_fallback_*.def"))]
    receipt = dict(status="PASS", scope=__doc__, command=command,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        extracted_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in extracted.items()},
        **json.loads(run.stdout))
    (out / "world-sites.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k:receipt[k] for k in ("status", "selector_cases", "strip_cases")}))


if __name__ == "__main__":
    main()
