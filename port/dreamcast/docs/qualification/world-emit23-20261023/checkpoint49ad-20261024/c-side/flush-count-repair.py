from pathlib import Path
r=Path('/root/work/lanes/world-emit23-census')
p=r/'port/dreamcast/game/platform/include/scenery_emit_census.hpp';s=p.read_text()
old='re4dc_log("WEC23 FRAME_END f=%u room=%03x begun=%x ended=%x complete=0\\n",state.frame,state.room,state.begun,state.ended);'
new='re4dc_log("WEC23 FRAME_END f=%u room=%03x begun=%x ended=%x flushes=%u complete=0\\n",state.frame,state.room,state.begun,state.ended,state.flush);'
assert s.count(old)==1;s=s.replace(old,new)
old='''re4dc_log("WEC23 FRAME_END f=%u room=%03x begun=%x ended=%x complete=%u\\n",
                frame,state.room,state.begun,state.ended,unsigned(state.begun==7 && state.ended==7));'''
new='''re4dc_log("WEC23 FRAME_END f=%u room=%03x begun=%x ended=%x flushes=%u complete=%u\\n",
                frame,state.room,state.begun,state.ended,state.flush,unsigned(state.begun==7 && state.ended==7));'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
p=r/'port/dreamcast/tools/d367/world_emit23/census.py';s=p.read_text().replace('"FRAME_END":{"f","room","begun","ended","complete"}','"FRAME_END":{"f","room","begun","ended","flushes","complete"}')
needle='    if cursor!=len(rows):raise ValueError("census record after FRAME_END")'
assert needle in s;s=s.replace(needle,'    if end["flushes"]!=next_flush-1:raise ValueError("missing flush block")\n'+needle);p.write_text(s)
p=r/'port/dreamcast/tools/d367/world_emit23/test_census.py';s=p.read_text().replace('begun=7 ended=7 complete=1','begun=7 ended=7 flushes=0 complete=1')
needle='            "flush-after-frame-end":log(remaining+q2),'
assert needle in s;s=s.replace(needle,needle+'\n            "whole-last-flush-missing":log(remaining),');p.write_text(s)
p=r/'port/dreamcast/tools/d367/world_emit23/README.md';s=p.read_text()
s=s.replace('The actual generated host log supplies twelve protocol mutations, all rejected,','The actual generated host log supplies thirteen protocol mutations, all rejected,')
s=s.replace('Runtime/header/make files are unchanged by this repair. Source integration','The protocol successor also adds source-authored flushes=state.flush to both\nguarded FRAME_END logs. The parser requires exactly that many global flush IDs,\nso a wholly missing final flush cannot become a complete census. Renderer state,\nstructs, native callsites and make files remain unchanged by the repair. Source integration')
p.write_text(s)
