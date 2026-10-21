"""Actual source declaration/call versus actual callee pointer-copy contract."""
from pathlib import Path
import subprocess,tempfile,unittest
R=Path(__file__).resolve().parents[3]

class ClothLightABI21(unittest.TestCase):
    def test_enabled_cross_TU_passes_live_nonnull_position_and_callee_copies_value(self):
        cloth=(R/'src/game/cloth.cpp').read_text();lit=(R/'src/game/trans_lit.cpp').read_text()
        marker='#if defined(RE4DC_CLOTH_LIGHT_ABI_FIX)'
        start=cloth.index(marker);decl=cloth[start:cloth.index('#endif',start)+6]
        start=cloth.index(marker,start+len(decl));call=cloth[start:cloth.index('#endif',start)+6]
        sig='void commonClothLightSet(cLight** list, int n, Vec* pos, f32 size)'
        start=lit.index(sig+'\n{');end=lit.index('    mask = 0;',start)
        # The actual callee's prefix includes its original *pos -> obj_pos copy.
        prefix=lit[start:end]
        self.assertIn('obj_pos = *pos;',prefix)
        tail=lit[end:lit.index('\n// Lighting for the water',end)]
        self.assertNotIn('pos',tail) # the input pointer is not retained later
        types='''#include <cassert>
using f32=float;using u32=unsigned;
struct Vec{float x,y,z;};struct cLight{};struct GXLightObj{};struct GXColor{unsigned char r,g,b,a;};
struct Info{cLight** pLight;};struct Model{Info LightInfo;Vec pos;};
#define LIGHT_FUNC_TABLE do{}while(0)
#define ISet(a,b) ((a)=(b))
'''
        caller=types+'extern "C" {\n'+decl+'\n}\n'+'''
extern "C" void caller(Model& model,float r){
'''+call+'''
}
extern Vec obj_pos;extern const Vec* observed;extern float obj_size;
int main(){cLight* lights[8]{};Model model{{lights},{13.25f,-2.75f,105.5f}};
 for(int i=0;i<8;++i){model.pos.x+=1;caller(model,33.5f);
 assert(observed==&model.pos);assert(obj_pos.x==model.pos.x&&obj_pos.y==model.pos.y&&obj_pos.z==model.pos.z);assert(obj_size==33.5f);}
 model.pos={0,0,0};assert(obj_pos.x!=model.pos.x); // callee owns a value copy
}
'''
        callee=types+'''
int obj_flag;Vec obj_pos;float obj_size;const Vec* observed;
extern "C" '''+prefix+'''
assert(pos);observed=pos;assert(n==8);assert(list);}
'''
        with tempfile.TemporaryDirectory(prefix='re4dc-cloth-abi21-') as temp:
            temp=Path(temp);a=temp/'caller.cpp';b=temp/'callee.cpp';a.write_text(caller);b.write_text(callee);exe=temp/'abi'
            result=subprocess.run(['g++','-std=c++17','-DRE4DC_CLOTH_LIGHT_ABI_FIX=1','-fsanitize=address,undefined','-fno-pie','-no-pie',str(a),str(b),'-o',str(exe)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);result=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            for flags in ([],['-DRE4DC_CLOTH_LIGHT_ABI_FIX=0'],['-DRE4DC_CLOTH_LIGHT_ABI_FIX=1','-D__PPC__=1']):
                result=subprocess.run(['g++','-std=c++17','-E','-P',*flags,str(a)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('Vec pos, f32 radius',result.stdout)
                self.assertIn('8, model.pos, r',result.stdout)

if __name__=='__main__':unittest.main()
