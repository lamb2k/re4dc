"""Exercise the production sort eligibility and overlay packet transformations."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]

def function(source, signature):
    start=source.index(signature)
    pos=source.index('{',start)+1
    depth=1
    while depth:
        depth+=(source[pos]=='{')-(source[pos]=='}')
        pos+=1
    return source[start:pos]

class WorldAutosort(unittest.TestCase):
    def test_profile_default_and_comparison_override(self):
        source=(ROOT/'port/dreamcast/game/game30.mk').read_text()
        a=source.index('WORLD_AUTOSORT ?=');b=source.index('# PS2_PRELOAD_LEAN=',a)
        fragment=source[a:b]+'\n.PHONY: check\ncheck:\n\t@echo $(WORLD_AUTOSORT)\n'
        for args,expected in [([], '0'),(['PS2_WORLD_DRAW=1','SS_UI_ORDER=1'],'1'),
                              (['PS2_WORLD_DRAW=1','SS_UI_ORDER=1','WORLD_AUTOSORT=0'],'0')]:
            result=subprocess.run(['make','-s','-f','-','check',*args],input=fragment,text=True,capture_output=True,check=True)
            self.assertEqual(result.stdout.strip(),expected)
        for args in (['WORLD_AUTOSORT=2'],['WORLD_AUTOSORT=1'],['PS2_WORLD_DRAW=1','WORLD_AUTOSORT=1']):
            result=subprocess.run(['make','-s','-f','-','check',*args],input=fragment,text=True,capture_output=True)
            self.assertNotEqual(result.returncode,0)

    def test_nonstream_overlay_depth(self):
        source=(ROOT/'port/dreamcast/game/platform/native_ui.cpp').read_text()
        start=source.index('#if !RE4DC_WORLD_AUTOSORT\nconstexpr float overlay_depth()')
        end=source.index('// One serial PVR owner',start)
        code='#define RE4DC_WORLD_AUTOSORT 0\n#define RE4DC_PVR_STREAM 0\n'+source[start:end]+'\n#endif\nstatic_assert(overlay_depth()==1.0f);\n'
        subprocess.run(['g++','-std=c++17','-x','c++','-fsyntax-only','-'],input=code,text=True,check=True)

    def test_actual_sort_and_packets(self):
        source=(ROOT/'port/dreamcast/game/platform/native_ui.cpp').read_text()
        code=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#define RE4DC_WORLD_AUTOSORT 1
#define RE4DC_ROUTE_MOVIES 1
#define RE4DC_D349_RENDERER_STACK 1
#define RE4DC_PS2_WORLD_DRAW 1
struct pvr_poly_hdr_t {std::uint32_t words[8];};
struct pvr_vertex_t {std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};
struct pvr_sprite_txr_t {std::uint32_t flags;float ax,ay,az,bx,by,bz,cx,cy,cz,dx,dy;std::uint32_t dummy,auv,buv,cuv;};
static_assert(sizeof(pvr_vertex_t)==32 && sizeof(pvr_sprite_txr_t)==64);
constexpr unsigned kPostPass=160,kSpritePacket=96;
bool world_autosort,ui_order,movie_texture,movie_picture;
unsigned overlay_layer,mode_changes,sends,last_bytes;
bool presort=true;
bool bank_ready=true,stream_scene;
unsigned stream_closed_lists;
using pvr_list_t=int;
constexpr int PVR_LIST_TR_POLY=2;
pvr_list_t stream_list,desired_list;
unsigned char sent[640];
void pvr_set_presort_mode(bool p){assert(bank_ready);presort=p;++mode_changes;}
void pvr_scene_begin(){bank_ready=false;}
int pvr_list_begin(int){bank_ready=true;return 0;}
void sq_unlock(){}
void re4dc_missing(const char*){assert(false);}
void stream_send(const void* data,unsigned bytes){assert(bytes<=sizeof(sent));std::memcpy(sent,data,bytes);last_bytes=bytes;++sends;}
'''+'\n'.join(function(source, sig) for sig in ('\nfloat overlay_depth()', 'void world_sort_begin()', 'void post_send(', 'void fx_send(', 'void stream_open()'))+r'''
void reset(){world_autosort=false;ui_order=false;movie_texture=movie_picture=false;overlay_layer=mode_changes=sends=0;presort=true;}
int main(){
    reset();assert(overlay_depth()==1 && overlay_layer==0);
    ui_order=true;world_sort_begin();assert(presort && mode_changes==0 && !world_autosort);
    ui_order=false;movie_texture=movie_picture=true;world_sort_begin();assert(presort && mode_changes==0);
    movie_picture=false;world_sort_begin();assert(!presort && mode_changes==1 && world_autosort);
    world_sort_begin();assert(mode_changes==1);
    for(unsigned i=0;i<8192;++i)assert(overlay_depth()==float(2+i));

    alignas(32) unsigned char packet[4*kPostPass],expected[sizeof(packet)];
    std::memset(packet,0x39,sizeof(packet));
    for(unsigned k=0;k<4;++k){
        auto* v=reinterpret_cast<pvr_vertex_t*>(packet+k*kPostPass+32);
        for(unsigned i=0;i<4;++i){v[i].z=1;v[i].x=float(i*11);v[i].y=float(i*7);v[i].u=0.25f;v[i].v=0.75f;}
    }
    std::memcpy(expected,packet,sizeof(packet));
    reset();post_send(packet,sizeof(packet));assert(std::memcmp(packet,expected,sizeof(packet))==0 && sends==1);
    world_sort_begin();
    for(unsigned k=0;k<4;++k){auto* v=reinterpret_cast<pvr_vertex_t*>(expected+k*kPostPass+32);for(unsigned i=0;i<4;++i)v[i].z=float(2+k);}
    post_send(packet,sizeof(packet));assert(overlay_layer==4 && last_bytes==sizeof(packet));
    assert(std::memcmp(packet,expected,sizeof(packet))==0 && std::memcmp(sent,expected,sizeof(packet))==0);

    alignas(32) unsigned char sprite[kSpritePacket],sprite_expected[kSpritePacket];
    std::memset(sprite,0x45,sizeof(sprite));auto* b=reinterpret_cast<pvr_sprite_txr_t*>(sprite+32);
    b->az=0.1f;b->bz=0.2f;b->cz=0.3f;std::memcpy(sprite_expected,sprite,sizeof(sprite));
    fx_send(sprite,false);assert(std::memcmp(sprite,sprite_expected,sizeof(sprite))==0 && overlay_layer==4);
    auto* e=reinterpret_cast<pvr_sprite_txr_t*>(sprite_expected+32);e->az=e->bz=e->cz=6;
    fx_send(sprite,true);assert(overlay_layer==5 && last_bytes==sizeof(sprite));
    assert(std::memcmp(sprite,sprite_expected,sizeof(sprite))==0);
    assert(std::memcmp(sent,sprite_expected,sizeof(sprite))==0);
    reset();ui_order=true;world_sort_begin();fx_send(sprite,true);assert(std::memcmp(sprite,sprite_expected,sizeof(sprite))==0);
    // scene_begin alone has not acquired the double-buffered TA bank. The
    // first non-DMA list begin waits for it; only then may tile state change.
    reset();world_autosort=true;overlay_layer=17;stream_closed_lists=15;
    stream_open();assert(bank_ready && stream_scene && presort);
    assert(!world_autosort && overlay_layer==0 && stream_closed_lists==0);
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);(path/'check.cpp').write_text(code)
            subprocess.run(['g++','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(path/'check.cpp'),'-o',str(path/'check')],check=True)
            subprocess.run([str(path/'check')],check=True)

if __name__=='__main__':unittest.main()
