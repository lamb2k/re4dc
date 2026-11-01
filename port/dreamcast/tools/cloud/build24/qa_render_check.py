#!/usr/bin/env python3
"""Actual Build24 Diagnostics pagination/font, guarded 320/640 framebuffer capture.

Extracts production display functions and fills their snapshot with the actual
observer's synthetic sealed rows. No image or game data is committed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    qa=DC/'game/qa_menu.cpp';core=DC/'game/draw_setup_audit.cpp'
    controls=HERE/'check_core.cpp';fixture=HERE.parent/'build10/qa_render_fixture.cpp'
    source=qa.read_text()
    colors=source[source.index('constexpr uint32_t kWhite'):source.index('// ---------------------------------------------------------------- framebuffer text')]
    font=source[source.index('const uint8_t* glyph'):source.index('Fb fb_boot()')]
    page=source[source.index('unsigned diag_page_rows'):source.index('#else\nvoid draw_diag',source.index('unsigned diag_page_rows'))]
    setup=controls.read_text().split('int main(',1)[0]
    capture=fixture.read_text().split('    const int width = atoi',1)[1]
    capture='    const int width = atoi'+capture
    capture=capture.replace('census_pages','diag_pages').replace('census_rows','diag_rows')
    capture=capture.replace('draw_census(fb, page);','g_diag_page=page;draw_diag(fb);')
    generated=out/'qa.cpp'
    generated.write_text(setup+colors+font+'''
static char g_diag[8192];
static int g_diag_len;
static unsigned g_diag_page;
'''+page+'''
int main(int argc,char** argv){
    if(argc!=4)return 1;
    partition();ds::pause();
    g_diag_len=snprintf(g_diag,sizeof(g_diag),"RE4DCQA1\\nBUILD24 SYNTHETIC DISPLAY CONTROL\\nWORLD_METER EXISTING ROWS RETAINED\\n");
    for(unsigned i=0;i<ds::line_count();++i){
        char line[240];const int n=ds::format_line(i,line,sizeof(line));assert(n>0&&n<int(sizeof(line)));
        const int k=snprintf(g_diag+g_diag_len,sizeof(g_diag)-g_diag_len,"%s\\n",line);
        assert(k>=0&&unsigned(k)<sizeof(g_diag)-g_diag_len);g_diag_len+=k;
    }
    g_diag_len+=snprintf(g_diag+g_diag_len,sizeof(g_diag)-g_diag_len,"LOG\\nEND OF COMPLETE SNAPSHOT\\n");
'''+capture)
    command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation',
             '-DRE4DC_DRAW_SETUP_AUDIT=1','-DRE4DC_DRAW_SETUP_AUDIT_HOST=1','-DRE4DC_DRAW_SETUP_AUDIT_WINDOW=3',
             '-I'+str(DC/'game/platform/include'),str(generated),str(core),'-o',str(out/'qa')]
    run=subprocess.run(command,capture_output=True,text=True);(out/'compile.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(run.stderr)
    layouts=[]
    for width in (320,640):
        for bpp in (2,4):
            layouts.append(json.loads(subprocess.check_output([str(out/'qa'),str(out/f'qa-{width}-{bpp}'),str(width),str(bpp)],text=True)))
    inputs=[qa,core,controls,fixture,DC/'game/platform/include/draw_setup_audit.h',Path(__file__)]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report=dict(status='PASS',scope=__doc__,layouts=layouts,command=command,
                source_sha256={str(x.relative_to(ROOT)):sha(x) for x in inputs},
                extracted_sha256=sha(generated),captures={x.name:sha(x) for x in sorted(out.glob('*.ppm'))})
    (out/'qa-render.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',layouts=layouts)))

if __name__=='__main__':main()
