from pathlib import Path
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class RuntimeGlyphTests(unittest.TestCase):
    def test_actual_upload_cache_and_accepted_run_versions(self):
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        header = (GAME / 'platform/include/native_ui.h').read_text()
        glyph = function(header, 'struct Re4dcUiGlyph {')+';'
        states = ui[ui.index('using GcAssetPacketState='):ui.index('void gcasset_packet_emitted(')]
        metadata = ui[ui.index('struct GlyphCell {'):ui.index('Entry* const kGlyphRun=')]
        observer = function(ui, 'void gcasset_packet_emitted(')
        methods = '\n'.join(function(ui, marker) for marker in (
            'unsigned glyph_color(', 'int glyph_bank(', 'int glyph_cell(',
            'bool gcasset_glyph_matches(', 'void gcasset_glyph_emitted(',
            'void glyph_draw_run(', 'short glyph_quarter(', 'extern "C" void re4dc_ui_glyph('))
        fixture = r'''
#include "gc_asset_payloads.h"
#include "gc_asset_packet_cursor.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <cstddef>
using namespace re4dc_gcasset;
namespace re4dc_gcasset{bool ensure_disc_catalog(){return true;}}
bool sq_held;std::string logs;
extern "C" void re4dc_log(const char* fmt,...){assert(!sq_held);char text[256];va_list ap;va_start(ap,fmt);const int n=vsnprintf(text,sizeof text,fmt,ap);va_end(ap);assert(n>=0 && unsigned(n)<256);logs+=text;}
struct Re4dcModelPart{const void* model;const void* info;};
struct Package{struct Header{unsigned texture_count=0;}head;bool upload_complete()const{return true;}const Header&header()const{return head;}void*pvr_texture(unsigned)const{return nullptr;}};
struct Entry{bool valid=false;Package package;};Entry entries[1];
void gcasset_texture_emitted(Entry*,Consumer){assert(false);}
using pvr_ptr_t=void*;struct pvr_poly_hdr_t{unsigned words[8];};
struct pvr_vertex_t{unsigned flags;float x,y,z,u,v;unsigned argb,oargb;};
constexpr unsigned PVR_CMD_VERTEX=0xe0000000,PVR_CMD_VERTEX_EOL=0xf0000000;
constexpr unsigned kGlyphCells=64,kGlyphCapacity=384,kGlyphBanks=8,kGlyphAtlasH=256,kGlyphAtlasBytes=32768,kQuadCount=256;
unsigned frame=3;bool frame_ready=true,stream_aborted;
unsigned palette_ram[128];unsigned char last_tile[512];alignas(32) unsigned char atlas[kGlyphAtlasBytes];
void pvr_set_pal_entry(unsigned index,unsigned value){assert(index<128);palette_ram[index]=value;}
void pvr_txr_load(const void* source,void* destination,unsigned bytes){memcpy(destination,source,bytes);assert(bytes==512);memcpy(last_tile,source,512);}
float overlay_depth(){return 1;}
#define RE4DC_UI_X(x) (x)
#define RE4DC_UI_Y(y) (y)
''' + glyph + '\n' + states + '\n' + observer + '\n' + metadata + r'''
Entry* const kGlyphRun=reinterpret_cast<Entry*>(glyph_cells);
struct Re4dcUiQuad{struct Image{unsigned width=0,height=0;}image;};Re4dcUiQuad quads[kQuadCount];Entry* handles[kQuadCount];unsigned nquad;
bool discard,wrong_pointer,wrong_extent,bad_address;
const pvr_poly_hdr_t& glyph_header(unsigned){static pvr_poly_hdr_t hdr{};hdr.words[0]=0x80000008;hdr.words[3]=((unsigned(reinterpret_cast<std::uintptr_t>(glyph_atlas))+(bad_address?4096:0))&0x007fffffU)/8;return hdr;}
void stream_send(const void* packet,unsigned bytes){assert(!sq_held);if(discard)return;
    if(wrong_extent){gcasset_packet_emitted(packet,bytes-32,2,gcasset_packet_consumer);return;}
    if(wrong_pointer){alignas(32) unsigned copy[520];memcpy(copy,packet,bytes);gcasset_packet_emitted(copy,bytes,2,gcasset_packet_consumer);}
    else gcasset_packet_emitted(packet,bytes,2,gcasset_packet_consumer);
}
''' + methods + r'''
unsigned rows(){unsigned count=0;std::size_t at=0;while((at=logs.find("GC-ASSET v=",at))!=std::string::npos){++at;++count;}return count;}
std::string sha(const Digest& digest){std::string out;char part[3];for(unsigned i=0;i<32;++i){snprintf(part,3,"%02x",digest.bytes[i]);out+=part;}return out;}
int main(){assert(install(nullptr,0));glyph_atlas=atlas;
 for(unsigned i=0;i<32;++i)for(unsigned bit=0;bit<5;++bit)if(i>>bit&1){glyph_twx[i]|=2U<<(2*bit);glyph_twy[i]|=1U<<(2*bit);}
 unsigned char sheet[32],clut[32];memset(sheet,0x12,32);for(unsigned i=0;i<32;++i)clut[i]=i;
 Re4dcUiGlyph g{};g.sheet=sheet;g.sheet_w=g.sheet_h=8;g.format=8;g.clut=clut;g.clut_entries=16;g.clut_format=0;
 g.cw=g.ch=4;g.x1=g.y1=4;g.argb=0xffffffff;
 begin(0x111,1,Required);for(unsigned i=0;i<40;++i)re4dc_ui_glyph(&g);assert(!rows());
 assert(nglyph==40);const auto tile=fingerprint(last_tile,512),palette=fingerprint(palette_ram,64);
 glyph_draw_run(0,40);end(1);
#if RE4DC_TREE_IMPOSTOR && !RE4DC_TEX_PAL4_ALPHA
 assert(!rows() && logs.find("unqualified-glyph-packet")!=std::string::npos);return 0;
#endif
 assert(rows()==2 && logs.find("provenance=unknown")!=std::string::npos);
 assert(logs.find("sha256="+sha(tile))!=std::string::npos && logs.find("sha256="+sha(palette))!=std::string::npos);
 assert(logs.find("texture=80")!=std::string::npos && logs.find("font=80 ui=80")!=std::string::npos);
 assert(logs.find("errors=0")!=std::string::npos); // three flushes, including carried bare-vertex batches
 // Borrowing/overwriting source font storage cannot relabel uploaded VRAM.
 memset(sheet,0xaa,32);memset(clut,0xbb,32);logs.clear();begin(0x113,2,Required);glyph_draw_run(0,1);end(1);assert(rows()==2);
 // Actual queued cell and palette versions are mandatory, not an atlas range.
 ++glyph_cells[glyph_quads[0].cell].serial;logs.clear();begin(0x111,3,Required);glyph_draw_run(0,1);end(1);
 assert(!rows() && logs.find("unqualified-glyph-packet")!=std::string::npos);--glyph_cells[glyph_quads[0].cell].serial;
 ++glyph_banks[glyph_quads[0].bank].serial;logs.clear();begin(0x111,4,Required);glyph_draw_run(0,1);end(1);assert(!rows());--glyph_banks[glyph_quads[0].bank].serial;
 wrong_pointer=true;logs.clear();begin(0x111,5,Required);glyph_draw_run(0,1);end(1);assert(!rows());wrong_pointer=false;
 wrong_extent=true;logs.clear();begin(0x111,5,Required);glyph_draw_run(0,1);end(1);assert(!rows());wrong_extent=false;
 bad_address=true;logs.clear();begin(0x111,6,Required);glyph_draw_run(0,1);end(1);assert(!rows());bad_address=false;
 discard=true;logs.clear();begin(0x111,7,Required);glyph_draw_run(0,1);end(1);assert(!rows());discard=false;
 logs.clear();begin(0x111,8,Required);unsigned packet[16]{};memcpy(packet,&glyph_header(0),32);packet[8]=PVR_CMD_VERTEX_EOL;
 stream_send(packet,64);end(1);assert(logs.find("unmapped-texture-address")!=std::string::npos); // no ambient atlas exemption
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-glyph-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            command = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_PVR_STREAM=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                            str(GAME / 'platform/gc_asset_payloads.cpp'), '-o', str(executable)]
            for variant in ([], ['-DRE4DC_TREE_IMPOSTOR=1', '-DRE4DC_TEX_PAL4_ALPHA=0']):
                subprocess.run(command+variant, check=True)
                subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':unittest.main()
