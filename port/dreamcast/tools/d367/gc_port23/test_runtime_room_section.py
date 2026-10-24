"""Actual optional callers and room_section's non-null output precondition."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE=Path(__file__).resolve().parent
GAME=HERE.parents[2]/'game'
BASE='3c7d93f661b2d05e3c7a01aba3304eb319c29107'


class RoomSectionTests(unittest.TestCase):
    def test_actual_optional_callers_match_c_output_contract(self):
        room=(GAME/'platform/room_file.c').read_text()
        rf=re.search(r'^#define MAXSEC .*$',room,re.M).group(0)+'\n'+room[room.index('static struct {'):room.index('} rf;')+len('} rf;')]
        consumer=(GAME/'platform/native_static.cpp').read_text()
        original=subprocess.check_output(['git','-C',str(GAME.parents[2]),'show',BASE+':port/dreamcast/game/platform/native_static.cpp'],text=True)
        for tag in ['SCCN','SCPS','SCDD']:
            with self.subTest(tag=tag):
                calls=[]
                for text in [consumer,original]:
                    matches=re.findall(r'    *const auto\* sec=static_cast<const std::uint8_t\*>\(re4dc_room_section\("'+tag+r'"[^\n]+',text)
                    self.assertEqual(len(matches),1)
                    call=matches[0]
                    if '&source_header' in call:call='const re4dc_room_header* source_header=nullptr;\n'+call
                    calls.append(call)
                for call,success in [(calls[0],True),(calls[1],False),(calls[0].replace('&source_header','nullptr'),False)]:
                    fixture='#include "room_file.h"\n#include <cassert>\n#include <cstdint>\n#include <cstring>\n'+rf+'\n'+function(room,'const void* re4dc_room_section(')+r'''
int main(){unsigned char bytes[32]{};rf.nsec=1;memcpy(rf.sec[0].tag,"TAG",4);rf.sec[0].len=32;rf.sec[0].version=1;rf.sec[0].flags=2;rf.sec[0].data=bytes;unsigned len=0,ver=0,fl=0;
CALL
assert(sec==bytes && len==32 && ver==1 && fl==2);
}
'''.replace('TAG',tag).replace('CALL',call)
                    if 'const re4dc_room_header* source_header' in call:fixture=fixture.replace('assert(sec==bytes','(void)source_header;assert(sec==bytes')
                    if success:fixture=fixture.replace('assert(sec==bytes','assert(source_header==&rf.hdr);assert(sec==bytes')
                    self.run_fixture(fixture,success)

    def run_fixture(self,fixture,success):
        with tempfile.TemporaryDirectory(prefix='gc-port23-room-section-',dir='/dev/shm') as scratch:
            root=Path(scratch);(root/'fixture.cpp').write_text(fixture)
            subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(GAME/'platform/include'),str(root/'fixture.cpp'),'-o',str(root/'fixture')],check=True)
            result=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(root/'fixture')],capture_output=True,text=True)
            if success:result.check_returncode()
            else:self.assertNotEqual(result.returncode,0,'actual old null caller escaped output-pointer precondition')

    def test_current_optional_off_projection_unchanged(self):
        path='port/dreamcast/game/platform/native_static.cpp'
        original=subprocess.check_output(['git','-C',str(GAME.parents[2]),'show',BASE+':'+path],text=True)
        current=(GAME/'platform/native_static.cpp').read_text()
        with tempfile.TemporaryDirectory(prefix='gc-port23-room-section-off-',dir='/dev/shm') as scratch:
            streams=[]
            for i,text in enumerate([original,current]):
                source=Path(scratch)/(str(i)+'.cpp');source.write_text(re.sub(r'^#include .*\n','',text,flags=re.M))
                streams.append(subprocess.check_output(['g++','-E','-P','-DRE4DC_GC_ASSET_GATE=0',
                    '-DRE4DC_NATIVE_STATIC=1','-DRE4DC_SCENERY_CONE=0','-DRE4DC_SCENERY_PIECE_STATE=0','-DRE4DC_SCENERY_DEDUP=0',str(source)],text=True))
            tokens=lambda s:re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|\d+|\S',s)
            self.assertEqual(tokens(streams[0]),tokens(streams[1]))


if __name__=='__main__':unittest.main()
