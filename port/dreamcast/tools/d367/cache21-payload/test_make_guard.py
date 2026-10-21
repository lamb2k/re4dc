from pathlib import Path
import tempfile,subprocess,json
R=Path(__file__).resolve().parents[5]
s=(R/'port/dreamcast/game/game30.mk').read_text();fragment=s[s.index('# TEX_PAYLOAD_RETRY=1'):s.index('# TEX_PACK_WINDOW=KB')]
with tempfile.TemporaryDirectory()as d:
 p=Path(d)/'Makefile';p.write_text('OBJDIR:=owned\nTEX_PACK?=1\nTEX_RESIDENT?=1\n'+fragment+'\nowned/platform/native_ui.o:\n\t@echo FLAGS=$(PLATFORM_CPPFLAGS)\n')
 cases={'default':([],True),'off':(['TEX_PAYLOAD_RETRY=0'],True),'on':(['TEX_PAYLOAD_RETRY=1'],True),'empty':(['TEX_PAYLOAD_RETRY='],False),'word':(['TEX_PAYLOAD_RETRY=other'],False),'two':(['TEX_PAYLOAD_RETRY=2'],False),'multiple01':(['TEX_PAYLOAD_RETRY=0 1'],False),'multiple11':(['TEX_PAYLOAD_RETRY=1 1'],False),'multiple10':(['TEX_PAYLOAD_RETRY=1 0'],False),'no_pack':(['TEX_PAYLOAD_RETRY=1','TEX_PACK=0'],False),'no_resident':(['TEX_PAYLOAD_RETRY=1','TEX_RESIDENT=0'],False)}
 outputs={}
 for name,(args,valid)in cases.items():
  result=subprocess.run(['make','--no-print-directory','-f',str(p),*args],text=True,capture_output=True);assert (result.returncode==0)==valid,(name,result.stdout,result.stderr);outputs[name]=result.stdout+result.stderr
 assert outputs['default']==outputs['off']=='FLAGS=\n'
 assert outputs['on']=='FLAGS=-DRE4DC_TEX_PAYLOAD_RETRY=1\n'
 print(json.dumps({'actual_source_fragment_cases':len(cases),'default_equals_off':True,'on_only_adds_candidate_define':True,'invalid_and_dependency_cases_refused':8},indent=2))
