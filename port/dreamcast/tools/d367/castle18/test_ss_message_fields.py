#!/usr/bin/env python3
"""Exercise original message bodies and menu consumers with typed port fields.

Original classes/getMes, code01, code08, checkMsgWindow and consumer branches are
extracted verbatim. External rendering/audio/board consequences are host stubs.
The SH-4 probe separately compiles the actual header and verifies target layout.
Neither test is a guest-menu, asset, item-discard or hardware acceptance gate.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,tempfile,re
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();root=a.root or Path(__file__).resolve().parents[5];out=a.output or Path(tempfile.mkdtemp(prefix='re4dc-msg-'));out.mkdir(parents=True,exist_ok=True);records=[]
def read(p):return(root/p).read_text()
def block(text,sig):
 start=text.index(sig) if sig.endswith('{') else re.search(re.escape(sig)+r'\s*\{',text).start();brace=text.index('{',start);i=brace+1;depth=1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[start:i]
def keep(name,s):records.append({'name':name,'sha256':hashlib.sha256(s.encode()).hexdigest()});return s
header=read('include/mes.h');msg=keep('actual Message class',block(header,'class Message {')+';');control=keep('actual MessageControl class',block(header,'class MessageControl {')+';');source=read('src/game/mes.cpp');puzzle=read('src/Sscrn/ss_pzzl.cpp')
start=puzzle.index('#if defined(RE4DC_SS_MSG_FIELDS)');end=puzzle.index('#endif',start)+6;aliases=keep('actual conditional aliases',puzzle[start:end]);assert aliases.count('cMes.getMes(1)')==2
check=keep('actual completion predicate',block(puzzle,'int checkMsgWindow(SUB_SCREEN* wk)'));code1=keep('actual end opcode',block(source,'int Message::code01()'));code8=keep('actual input opcode',block(source,'int Message::code08()'))
move=puzzle[puzzle.index('void PieceCommand::move(SUB_SCREEN* wk)'):puzzle.index('void PieceCommand::quit(SUB_SCREEN* wk)')];start=move.rindex('    case 3:');finish=keep('actual command completion branch',move[start+len('    case 3:'):move.index('\n    }',start)])
move=block(puzzle,'void PieceSelect::move(SUB_SCREEN* wk)');start=move.index('    case 1: {\n        int r;');choice=keep('actual case selection branch',move[start+len('    case 1:'):move.index('\n    case 2:',start)])
host=r"""
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <type_traits>
using u8=uint8_t;using s8=int8_t;using u16=uint16_t;using s16=int16_t;using u32=uint32_t;using f32=float;
class MessageFont;struct MesQue{};struct TEXPalette;
#define RE4DC_SS_MSG_FIELDS 1
"""+msg+'\ntypedef Message MesWork;\n'+control+r"""
MessageControl cMes;
struct Global{u32 Stop_flg=0,Status_flg[4]{};}global,*pG=&global;
struct KeyWork{u32 trg=0;}Key;
struct IdSystem{bool shown=false;int setCk(int){return shown;}}IdSys;
struct Cockpit{int calls=0;void lifeMeterDisp(int){calls++;}}Cckpt;
void SndCall(int,int,void*,int,int,void*){}
void Message::putSelCursol(){}void Message::putNextCursol(int){}
struct pzlBoard{};
struct Player{void*m_extra=nullptr;int rehashed=0;void rehash(){rehashed++;}}pl;
struct SUB_SCREEN{int type=0;Player*puzzlePlayer=&pl;void*p_get_item=nullptr;}wk;
struct Items{int dumped=0;void*last=nullptr;void offboardDump(void*p){dumped++;last=p;}}ItemMgr;
int closes=0,transits=0,back=0,state=1,msg_open=0;
void closeMsgWindow(SUB_SCREEN*){closes++;}void transit(int,SUB_SCREEN*){transits++;}void back2PieceSelect(SUB_SCREEN*){back++;}
"""+aliases+'\n'+check+'\n'+code1+'\n'+code8+'\nvoid commandComplete(SUB_SCREEN*wk){do{\n'+finish+'\n}while(0);}\nvoid caseAnswer(SUB_SCREEN*wk){int st=state;pzlBoard*b=nullptr;do{\n'+choice+'\n}while(0);}\n'+r"""
void reset(){cMes=MessageControl{};global={};Key={};IdSys={};Cckpt={};wk={};pl={};ItemMgr={};closes=transits=back=msg_open=0;state=1;}
int main(){
 static_assert(std::is_polymorphic<Message>::value&&std::is_polymorphic<MessageControl>::value);
 assert(cMes.getMes(0)==&cMes.mes[0]&&cMes.getMes(1)==&cMes.mes[1]&&cMes.getMes(15)==&cMes.mes[15]);
 assert((char*)cMes.getMes(1)-(char*)cMes.getMes(0)==sizeof(Message));
 assert((char*)&cMes.mes[1].stop_bak-(char*)&cMes.mes[1]==sizeof(void*));
 unsigned flagCases=0,answerCases=0,inputCases=0;
 for(unsigned flags=0;flags<16;flags++)for(unsigned decoy=0;decoy<16;decoy++){
  reset();auto&m=cMes.mes[1];m.flags2=flags;m.be_flag=decoy;cMes.mes[0].flags2=~flags;cMes.mes[2].flags2=~flags;
  assert(checkMsgWindow(&wk)==bool(flags&2));commandComplete(&wk);assert(closes==bool(flags&2)&&transits==bool(flags&2));assert(m.flags2==flags&&m.be_flag==decoy);flagCases++;
 }
 for(unsigned keep=0;keep<2;keep++)for(unsigned attr10=0;attr10<2;attr10++){
  reset();auto&m=cMes.mes[1];m.be_flag=3;m.flags2=1;m.stop_bak=0x1234;m.m_attr=(keep?0x01000000:0)|(attr10?0x10:0);global.Stop_flg=0xABCD;
  assert(!checkMsgWindow(&wk));assert(m.code01()==2&&m.r_no_0==1&&m.flags2==1);assert(!checkMsgWindow(&wk));
  assert(m.code01()==2&&checkMsgWindow(&wk));assert(m.flags2==(keep?3U:2U));assert(m.be_flag==(keep?3U:2U));assert(global.Stop_flg==((keep||attr10)?0xABCDU:0x1234U));commandComplete(&wk);assert(closes==1&&transits==1);flagCases++;
 }
 for(int answer: {-128,-1,0,1,2,127})for(int extra=0;extra<2;extra++)for(int type4=0;type4<2;type4++){
  reset();wk.type=type4?4:0;pl.m_extra=extra?&pl:nullptr;wk.p_get_item=&wk;auto&m=cMes.mes[1];m.m_sel=answer;cMes.mes[0].m_sel=1;cMes.mes[2].m_sel=2;m.selCur[7]=(MesQue*)uintptr_t(0x11223344);
  assert(int(CMES_RESULT)==answer);caseAnswer(&wk);assert(closes==(answer!=0));assert(ItemMgr.dumped==(answer==1)&&pl.rehashed==(answer==1)&&back==(answer==1));assert(state==(answer==1?2:answer==2?0:1));
  if(answer==1)assert(ItemMgr.last==((type4&&extra)?wk.p_get_item:nullptr));answerCases++;
 }
 for(int choice=0;choice<2;choice++){
  reset();auto&m=cMes.mes[1];m.m_selTbl_size=2;m.m_btn=1;m.m_cur=choice;Key.trg=0x80000000;assert(m.code08()==0);assert(int(CMES_RESULT)==choice+1);caseAnswer(&wk);assert(state==(choice?0:2));inputCases++;
 }
 reset();auto&m=cMes.mes[1];m.m_selTbl_size=2;m.m_btn=1;m.m_attr=0x00100000;Key.trg=0x40000000;assert(m.code08()==0&&int(CMES_RESULT)==-1);caseAnswer(&wk);assert(closes==1&&state==1&&ItemMgr.dumped==0);inputCases++;
 reset();auto&n=cMes.mes[1];n.m_selTbl_size=2;n.m_btn=1;n.m_attr=0x00300000;Key.trg=0x40000000;assert(n.code08()==0&&int(CMES_RESULT)==2);caseAnswer(&wk);assert(state==0&&ItemMgr.dumped==0);inputCases++;
 reset();auto&q=cMes.mes[1];q.m_selTbl_size=2;Key.trg=0x80000000;assert(q.code08()==2&&CMES_RESULT==0);q.waitCnt=1;assert(q.code08()==2&&CMES_RESULT==0&&q.waitCnt==0);inputCases++;
 printf("flag_cases=%u answer_cases=%u original_input_cases=%u typed_slot_stride_and_signed_answers=PASS\n",flagCases,answerCases,inputCases);
}
"""
host=host.replace('#include <type_traits>','#include <type_traits>\n#include <initializer_list>');cpp=out/'actual-source-message-fields.cpp';cpp.write_text(host);exe=out/'actual-source-message-fields';cmd=['g++','-std=c++20','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(cpp),'-o',str(exe)];r=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr;r=subprocess.run([str(exe)],capture_output=True,text=True);(out/'run.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
probe=out/'actual-header-sh4-layout.cpp';probe.write_text('#include "mes.h"\nstatic_assert(sizeof(void*)==4,"SH4 pointers");\nstatic_assert(sizeof(Message)==236,"slot stride");\nstatic_assert(sizeof(MessageControl)==4608,"control size");\nstatic_assert(__builtin_offsetof(MessageControl,mes)==8,"vptr then x0");\nstatic_assert(__builtin_offsetof(Message,flags2)==16,"typed flags");\nstatic_assert(__builtin_offsetof(Message,be_flag)==8,"decoy active flags");\nstatic_assert(__builtin_offsetof(Message,m_sel)==229,"signed answer");\nstatic_assert(sizeof(((Message*)0)->m_sel)==1,"answer byte");\nMessageControl layoutEvidence;\n');layoutcmd=['/opt/toolchains/dc/sh-elf/bin/sh-elf-g++','-std=gnu++11','-fpermissive','-g','-I'+str(root/'include'),'-I'+str(root/'port/dreamcast/game/platform/include'),'-c',str(probe),'-o',str(out/'actual-header-sh4-layout.o')];q=subprocess.run(layoutcmd,capture_output=True,text=True);(out/'layout-compile.txt').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
proof={'status':'SOURCE_MESSAGE_FIELDS_PASS','compiler':cmd,'output':r.stdout.strip(),'extracted_sources':records,'harness_sha256':hashlib.sha256(cpp.read_bytes()).hexdigest(),'SH4_actual_header_layout_command':layoutcmd,'SH4_layout_object_sha256':hashlib.sha256((out/'actual-header-sh4-layout.o').read_bytes()).hexdigest(),'limits':__doc__};(out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'status':proof['status'],'output':proof['output'],'proof':str(out/'proof.json')}))


