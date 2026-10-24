from pathlib import Path
r=Path('/root/work/lanes/world-emit23-census')
p=r/'port/dreamcast/game/platform/native_static.cpp';s=p.read_text()
def once(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
once('#ifndef RE4DC_WORLD_RECT21\n',"""// SCENERY_EMIT_CENSUS_CONFIG_BEGIN
#ifndef RE4DC_SCENERY_EMIT_CENSUS
#define RE4DC_SCENERY_EMIT_CENSUS 0
#endif
#if RE4DC_SCENERY_EMIT_CENSUS < 0 || RE4DC_SCENERY_EMIT_CENSUS > 10000000
#error SCENERY_EMIT_CENSUS must be a frame from 0 to 10000000
#endif
#if RE4DC_SCENERY_EMIT_CENSUS && (!RE4DC_SCENERY_CHUNK || !RE4DC_PS2_WORLD_MESH)
#error SCENERY_EMIT_CENSUS needs the PS2 scenery chunk path
#endif
// SCENERY_EMIT_CENSUS_CONFIG_END
#ifndef RE4DC_WORLD_RECT21
""")
once('#include "re4dc_platform.h"\n',"""#include "re4dc_platform.h"
#if RE4DC_SCENERY_EMIT_CENSUS
#include "include/scenery_emit_census.hpp"
#endif
""")
once('    int emit_pick(const Pick& pk){\n',"""    int emit_pick(const Pick& pk){
#if RE4DC_SCENERY_EMIT_CENSUS
        scenery_emit_census::pick_attempt();
#endif
""")
once('    auto& c=ps2w.count[pass];c={};\n',"""    auto& c=ps2w.count[pass];c={};
#if RE4DC_SCENERY_EMIT_CENSUS
    scenery_emit_census::Pass census_pass(re4dc_ui_frame(),ps2w.room,pass);
#endif
""")
once('#if RE4DC_PS2_PVS\n                       unsigned placement;\n', '#if RE4DC_PS2_PVS || RE4DC_SCENERY_EMIT_CENSUS\n                       unsigned placement;\n')
once('        // The pending selection/ordinary draw references this shared record.\n',"""#if RE4DC_SCENERY_EMIT_CENSUS
        // Declared before SubmitScope: diagnostics run after its SQ/batch close.
        scenery_emit_census::Flush census_flush(census_pass,cpkg,cctx,nctx,cpk,npk);
#endif
        // The pending selection/ordinary draw references this shared record.
""")
once('            const ChunkPart& x=cctx[j];\n',"""            const ChunkPart& x=cctx[j];
#if RE4DC_SCENERY_EMIT_CENSUS
            census_flush.start(j);
#endif
""")
once('            e.end_direct();\n',"""            e.end_direct();
#if RE4DC_SCENERY_EMIT_CENSUS
            census_flush.finish(j,result);
#endif
""")
# These two original PVS placement assignments also supply diagnostic identity.
for indent in ('                    ','                '):
 a='#if RE4DC_PS2_PVS\n'+indent+'x.placement=i;\n'
 once(a,'#if RE4DC_PS2_PVS || RE4DC_SCENERY_EMIT_CENSUS\n'+indent+'x.placement=i;\n')
once('    return c.fallback?0:1;\n',"""#if RE4DC_SCENERY_EMIT_CENSUS
    census_pass.result=c.fallback?0:1;
#endif
    return c.fallback?0:1;
""")
p.write_text(s)
p=r/'port/dreamcast/game/scenery19.mk';s=p.read_text()
s+='''\n# One-frame diagnostic census only. Nonzero is the minimum UI capture frame.
# Off adds no definition or compiler-command change.
SCENERY_EMIT_CENSUS ?= 0
ifneq ($(SCENERY_EMIT_CENSUS),0)
scenery_census_nondigits := $(subst 9,,$(subst 8,,$(subst 7,,$(subst 6,,$(subst 5,,$(subst 4,,$(subst 3,,$(subst 2,,$(subst 1,,$(subst 0,,$(SCENERY_EMIT_CENSUS)))))))))))
ifneq ($(scenery_census_nondigits),)
$(error SCENERY_EMIT_CENSUS must be a decimal frame from 0 to 10000000)
endif
ifneq ($(filter 0%,$(SCENERY_EMIT_CENSUS)),)
$(error SCENERY_EMIT_CENSUS does not accept leading zeroes)
endif
ifneq ($(shell test "$(SCENERY_EMIT_CENSUS)" -le 10000000 2>/dev/null && echo yes),yes)
$(error SCENERY_EMIT_CENSUS must be a decimal frame from 0 to 10000000)
endif
ifeq ($(SCENERY_CHUNK),0)
$(error SCENERY_EMIT_CENSUS needs SCENERY_CHUNK)
endif
ifneq ($(PS2_WORLD_MESH),1)
$(error SCENERY_EMIT_CENSUS needs PS2_WORLD_MESH=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_EMIT_CENSUS=$(SCENERY_EMIT_CENSUS)
endif
'''
p.write_text(s)
print('source and make diagnostic hooks added')
