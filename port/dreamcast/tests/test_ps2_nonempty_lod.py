"""Exercise both actual native selection blocks and the default-off make guard."""
from pathlib import Path
import shutil,subprocess,tempfile,unittest
R=Path(__file__).resolve().parents[1]

class NonemptyLod(unittest.TestCase):
 @unittest.skipUnless(shutil.which('g++'),'host compiler required')
 def test_actual_selectors(self):
  source=(R/'game/platform/native_static.cpp').read_text();blocks=[]
  for name in ['int draw_clusters(){','unsigned chunk_select(Pick* out){']:
   tail=source[source.index(name):];start=tail.index('unsigned level=cl.level_count-1;');end=tail.index('++stats.lod_draws',start);blocks.append(tail[start:end])
  self.assertEqual(blocks[0],blocks[1])
  ps2=source[source.index('int ps2_pass('):]
  projection=ps2[ps2.index('const float px_x='):ps2.index('const auto& pk=ps2w.package;')]
  matrix=ps2[ps2.index('float scale=0;'):ps2.index('for(unsigned k=0;k<mesh.part_count;++k){',ps2.index('float scale=0;'))]
  preamble='''#include <cassert>
#include <cmath>
#include <limits>
#include "nonempty_lod.hpp"
#define RE4DC_SCREEN_HALF_WF 320.0f
#define RE4DC_SCREEN_HALF_HF 240.0f
#define RE4DC_QUALITY 1
#define RE4DC_SCENERY_FAR_LOD 4
struct Quality{float lod_px=5;};
Quality* re4dc_quality(){static Quality q;return &q;}
struct Level{unsigned first_meshlet,meshlet_count;float error;};
struct Cluster{unsigned first_level,level_count;};
'''
  functions=''.join('unsigned choose_'+str(i)+'(const Level* levels,Cluster cl,float lod_scale,float depth,bool ps2){'+block+'return level;}\n' for i,block in enumerate(blocks))
  functions+='float actual_scale(const float* P,const float* mv){'+projection+matrix+'return lod_scale;}\n'
  cases=r'''
int main(){
 float projection[7]={0,1.2f,0,1.6f,0,0,0},world[12]={1,0,0,0,0,1,0,0,0,0,1,0};
 assert(std::fabs(actual_scale(projection,world)-19.2f)<0.0001f);
 world[0]=-2;world[5]=2;world[10]=2;
 assert(std::fabs(actual_scale(projection,world)-38.4f)<0.0001f);
 Level l[]={{0,99,0},{0,99,0},{0,9,0},{9,4,10},{0,0,20},{0,0,30},{13,1,40}};Cluster cl{2,5};
 for(float scale:{1.0f,3.0f,20.0f})for(float depth:{0.0f,9.999f,10.0f,19.999f,20.0f,29.999f,30.0f,39.999f,40.0f,1000.0f})for(bool ps2:{false,true}){
  unsigned original=4;while(original && l[2+original].error*scale>depth)--original;
  unsigned expected=original;
#if RE4DC_PS2_WORLD_NONEMPTY_LOD
  if(ps2)while(expected && !l[2+expected].meshlet_count)--expected;
#endif
  assert(choose_0(l,cl,scale,depth,ps2)==expected);assert(choose_1(l,cl,scale,depth,ps2)==expected);
  if(expected)assert(l[2+expected].error*scale<=depth);
 }
 // Exact stand boundary: normal policy picks the generated empty level at equality.
 Level stand[]={{0,9,0},{9,0,86.73419952392578f}};const float scale=16,threshold=stand[1].error*scale;
 assert(choose_0(stand,{0,2},scale,std::nextafter(threshold,0.0f),true)==0);
#if RE4DC_PS2_WORLD_NONEMPTY_LOD
 assert(choose_0(stand,{0,2},scale,threshold,true)==0);assert(choose_1(stand,{0,2},scale,threshold,true)==0);
#else
 assert(choose_0(stand,{0,2},scale,threshold,true)==1);assert(choose_1(stand,{0,2},scale,threshold,true)==1);
#endif
 assert(choose_0(stand,{0,2},scale,threshold,false)==1); // source mesh path unchanged
 Level authored_empty[]={{0,0,0},{0,0,10}};
#if RE4DC_PS2_WORLD_NONEMPTY_LOD
 assert(choose_0(authored_empty,{0,2},1,100,true)==0);
#endif
 assert(re4dc::room::nonempty_lod(authored_empty,2,1)==0); // no invented geometry
 assert(re4dc::room::nonempty_lod<Level>(nullptr,1,0)==0);
 assert(re4dc::room::nonempty_lod(stand,0,0)==0);
 assert(re4dc::room::nonempty_lod(stand,2,2)==0);
 Level one[]={{0,1,0}};assert(re4dc::room::nonempty_lod(one,1,0)==0);
 Level full[]={{0,9,0},{9,4,10},{13,2,20}};
 assert(choose_0(full,{0,3},1,100,true)==2);assert(choose_1(full,{0,3},1,100,true)==2);
}
'''
  with tempfile.TemporaryDirectory() as temp:
   cpp=Path(temp)/'test.cpp';cpp.write_text(preamble+'#include <initializer_list>\n'+functions+cases)
   for mode in ['default','0','1']:
    cmd=['g++','-std=c++17','-O1','-fsanitize=address,undefined','-I'+str(R/'room'),str(cpp),'-o',str(Path(temp)/mode)]
    if mode!='default':cmd+=['-DRE4DC_PS2_WORLD_NONEMPTY_LOD='+mode]
    subprocess.run(cmd,check=True);subprocess.run([str(Path(temp)/mode)],check=True)

 @unittest.skipUnless(shutil.which('make'),'make required')
 def test_actual_make_guard(self):
  text=(R/'game/game30.mk').read_text();block=text[text.index('# PS2_WORLD_NONEMPTY_LOD=1:'):text.index('# PS2_WORLD_ROOT_POSE=1:')]
  make='OBJDIR:=owned\n'+block+'\n.PHONY: owned/platform/native_static.o\nowned/platform/native_static.o:\n\t@echo FLAG=$(PLATFORM_CPPFLAGS)\n'
  def run(*args):return subprocess.run(['make','--no-print-directory','-f','-','owned/platform/native_static.o',*args],input=make,text=True,capture_output=True)
  for args in [(),('PS2_WORLD_NONEMPTY_LOD=0',)]:
   r=run(*args);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout.strip(),'FLAG=')
  r=run('PS2_WORLD_NONEMPTY_LOD=1','MESH_LOD=1','PS2_WORLD_ROOMS=2');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('-DRE4DC_PS2_WORLD_NONEMPTY_LOD=1',r.stdout)
  for args in [('PS2_WORLD_NONEMPTY_LOD=2',),('PS2_WORLD_NONEMPTY_LOD=-1',),('PS2_WORLD_NONEMPTY_LOD=1','MESH_LOD=0','PS2_WORLD_ROOMS=2'),('PS2_WORLD_NONEMPTY_LOD=1','MESH_LOD=1','PS2_WORLD_ROOMS=0')]:
   self.assertNotEqual(run(*args).returncode,0,args)

if __name__=='__main__':unittest.main()
