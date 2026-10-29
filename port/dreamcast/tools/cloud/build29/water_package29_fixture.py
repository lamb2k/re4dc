#!/usr/bin/env python3
"""Exercise real W29 DAR producer, room-load hook, copied selector and retirement."""
import os
from pathlib import Path
import shlex
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'port/dreamcast/tools/d367/water'))
sys.path.insert(0, str(ROOT / 'port/dreamcast/tools/d367/graft'))
sys.path.insert(0, str(ROOT / 'port/dreamcast/tools'))
import water_package29 as producer  # noqa: E402
import dar_graft  # noqa: E402
import room_smd  # noqa: E402
from water_layer29_fixture import SOURCE, production_cpp  # noqa: E402

READ = ROOT / 'src/game/read.cpp'
EFFECT = ROOT / 'port/dreamcast/game/platform/native_effect.cpp'
BASE = '14b5c196db699640f7a9f39bc2318df22dc45ade'
RECOVERY_BASE = 'd45eb759dd92685255929625e04fae3d7a46bca7'


def archive(entries):
    header = bytearray(room_smd.align(16 + 8 * len(entries)))
    struct.pack_into('<I', header, 0, len(entries))
    data = bytearray(header)
    offsets = []
    for i, (tag, body) in enumerate(entries):
        offsets.append(len(data))
        struct.pack_into('<I', data, 16 + 4 * i, len(data))
        data[16 + 4 * len(entries) + 4 * i:20 + 4 * len(entries) + 4 * i] = tag
        data += body
        data += bytes(room_smd.align(len(data)) - len(data))
    return bytes(data), offsets


def container(payload):
    head = bytearray(1024)
    head[:32] = room_smd.CONTAINER_MAGIC
    struct.pack_into('<4I', head, 32, 0, len(payload), 0, 1024)
    struct.pack_into('<I', head, 64, 0xffffffff)
    out = bytes(head) + payload
    return out + bytes(room_smd.align(len(out), 2048) - len(out))


def synthetic_dar(changed=False):
    blob = bytes((i * 13 + 7) & 255 for i in range(320))
    pay, offs = archive([(b'BIN\0', blob), (b'QAX\0', (b'other' if changed else b'unknown') + bytes(56)),
                         (b'NTR\0', bytes(64)), (b'ESQ\0', bytes(64)),
                         (b'EX1\0', bytes(range(32))), (b'EX2\0', bytes(range(31, -1, -1)))])
    data = bytearray(pay)
    ntr = struct.pack('<3I', offs[0], offs[0] + 32, offs[0] + 80)
    struct.pack_into('<8s6I', data, offs[2], b'R4NTBL\0\0', 1, 1, 12,
                     zlib.crc32(ntr) & 0xffffffff, len(data), len(data))
    data[offs[2] + 32:offs[2] + 44] = ntr
    esq = struct.pack('<3I', offs[0] + 96, 64, 1)
    struct.pack_into('<8s6I', data, offs[3], b'R4ESQTBL', 1, 1, 12,
                     zlib.crc32(esq) & 0xffffffff, len(data), 0)
    data[offs[3] + 32:offs[3] + 44] = esq
    return container(bytes(data))


def function(source, marker):
    start = source.index(marker)
    return source[start:source.index('\n}\n', start) + 3]


CASES = r'''
#include <fstream>
#include <iterator>
struct EffectBinding { void* archive; };
static EffectBinding bindings[6]{};
static unsigned unbind_calls=0;
extern "C" void re4dc_effect_unbind(void* archive) {
    assert(archive==bindings[5].archive);
    Water29View view{};
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND);
    assert(view.owner!=WATER29_ARCHIVE_OWNER);  // water retires before effect backing
    bindings[5].archive=nullptr;
    ++unbind_calls;
}
__READ_HOOK__
__RETIRE_HOOK__
static std::vector<u8> payload(const char* name) {
    std::ifstream in(name,std::ios::binary);
    std::vector<u8> dar((std::istreambuf_iterator<char>(in)),{});
    assert(dar.size()>=1024);
    u32 kind,bytes,destination,offset;
    memcpy(&kind,dar.data()+32,4);memcpy(&bytes,dar.data()+36,4);
    memcpy(&destination,dar.data()+40,4);memcpy(&offset,dar.data()+44,4);
    assert(!kind && !destination && offset<=dar.size() && bytes<=dar.size()-offset);
    return std::vector<u8>(dar.begin()+offset,dar.begin()+offset+bytes);
}
static void setup() {
    for(int i=0;i<256;i++) {
        tpls[i].numDescriptors=60;tpls[i].id=i;
        texhdr[i]={&pixel[i],64,64,6};
        for(auto& d:tpls[i].descriptor){d.textureHeader=&texhdr[i];d.CLUTHeader=nullptr;}
        system_tex.Esp_tex_tbl[i]={0,&tpls[i],&animation};
    }
    animation.Frames=60;animation.Data_num=0;
    game.Cam.v_mat[0][0]=game.Cam.v_mat[1][1]=game.Cam.v_mat[2][2]=1.0f;
    game.prim_cnt=0x1000;
}
static u32 word(const u8* p){u32 v;memcpy(&v,p,4);return v;}
static void put(u8* p,u32 v){memcpy(p,&v,4);}
static u32 water_start(const std::vector<u8>& data) {
    u32 n=word(data.data());
    for(u32 i=0;i<n;i++) {
        const u8* tag=data.data()+16+4*n+4*i;
        if(tag[0]=='W' && tag[1]=='2' && tag[2]=='9' && !tag[3])return word(data.data()+16+4*i);
    }
    assert(false);return 0;
}
int main(int argc,char** argv) {
    assert(argc==4);setup();G_ROOM_ID=0x107;now_level=0;now_tick=3;
    auto arena=payload(argv[1]);const u8* fixed=arena.data();
    Water29View view{};assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND);
    assert(view.owner!=WATER29_ARCHIVE_OWNER && view.main_count==2);
    puts("COMPILED");re4dc_water_ps2_draw(nullptr);puts("END-COMPILED");
    bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_BOUND);
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND);
    assert(view.owner==WATER29_ARCHIVE_OWNER && view.incarnation==1 && view.main_count==2);
    assert(!memcmp(view.main_rows,kWaterPs2,2*sizeof(WaterPs2Row)));
    const float original=view.main_rows[0].x;
    unsigned before=ot_calls;re4dc_water_ps2_queue();assert(ot_calls==before+1);
    ++now_frame;
    puts("LOADED");re4dc_water_ps2_draw(nullptr);puts("END-LOADED");
    auto start=water_start(arena);
    float newer=original+17.0f;
    memcpy(arena.data()+start+sizeof(Water29PackageHeader)+4,&newer,4);
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND && view.main_rows[0].x==original);
    put(arena.data()+start+52,water29PackageCrc32(arena.data()+start+56,2*sizeof(WaterPs2Row)));
    re4dc_effect_retire_room();assert(unbind_calls==1);
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND && view.owner!=WATER29_ARCHIVE_OWNER);
    assert(fixed==arena.data());bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_BOUND);
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND && view.incarnation==2 && view.main_rows[0].x==newer);
    re4dc_water29_retire(WATER29_ARCHIVE_OWNER,1);
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND && view.incarnation==2);
    re4dc_effect_retire_room();
    // Failed package reads retire the old authority and retain compiled water.
    arena[start+4] ^= 1;
    bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_REFUSED);
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND && view.owner!=WATER29_ARCHIVE_OWNER);
    re4dc_effect_retire_room();
    arena[start+4] ^= 1;
    arena[start+16] ^= 1; // wrong source family
    bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_REFUSED);
    re4dc_effect_retire_room();arena[start+16] ^= 1;
    arena[start+12] ^= 1; // wrong serialized room
    bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_REFUSED);
    re4dc_effect_retire_room();arena[start+12] ^= 1;
    arena[start+48] = 1; // noncanonical extension origin with zero extension rows
    bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_REFUSED);
    re4dc_effect_retire_room();arena[start+48] = 0;
    const u32 good_bytes=word(arena.data()+start+8);
    put(arena.data()+start+8,~u32(0)); // claimed member exceeds DVD extent
    bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_REFUSED);
    re4dc_effect_retire_room();put(arena.data()+start+8,good_bytes);
    bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),start+good_bytes-1,G_ROOM_ID)==WATER29_REFUSED);
    re4dc_effect_retire_room();
    arena[start+56+4] ^= 1; // CRC detects a mutated row before publication
    bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_REFUSED);
    re4dc_effect_retire_room();arena[start+56+4] ^= 1;
    float invalid=__builtin_nanf("");
    float saved;memcpy(&saved,arena.data()+start+56+4,4);
    memcpy(arena.data()+start+56+4,&invalid,4);
    put(arena.data()+start+52,water29PackageCrc32(arena.data()+start+56,2*sizeof(WaterPs2Row)));
    bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_REFUSED);
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND && view.owner!=WATER29_ARCHIVE_OWNER);
    re4dc_effect_retire_room();
    memcpy(arena.data()+start+56+4,&saved,4);
    put(arena.data()+start+52,water29PackageCrc32(arena.data()+start+56,2*sizeof(WaterPs2Row)));
    u32 n=word(arena.data());
    const u32 water_off=word(arena.data()+16+4*(n-1));
    put(arena.data()+16+4*(n-1),0xffffffe0u);
    bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_REFUSED);
    re4dc_effect_retire_room();put(arena.data()+16+4*(n-1),water_off);
    u8* tag=arena.data()+16+4*n;memcpy(tag,"W29\0",4); // duplicate tag, distinct start
    bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_REFUSED);
    re4dc_effect_retire_room();
    memcpy(tag,"BIN\0",4);tag=arena.data()+16+4*n+4*(n-1);
    memcpy(tag,"Q29\0",4); // no W29, same address
    bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_UNBOUND);
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND && view.owner!=WATER29_ARCHIVE_OWNER);
    re4dc_effect_retire_room();
    auto aligned=payload(argv[1]);
    std::vector<u8> skewed(1,0);
    skewed.insert(skewed.end(),aligned.begin(),aligned.end());
    assert((uintptr_t(skewed.data()+1)&3)!=0);
    bindings[5].archive=skewed.data()+1;
    assert(Water29ReadRoomLoaded(skewed.data()+1,unsigned(aligned.size()),G_ROOM_ID)==WATER29_BOUND);
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND &&
           !memcmp(view.main_rows,kWaterPs2,2*sizeof(WaterPs2Row)));
    re4dc_effect_retire_room();
    const u32 before_exhaustion=s_water29_archive_incarnation;
    s_water29_archive_incarnation=~u32(0);bindings[5].archive=arena.data();
    assert(Water29ReadRoomLoaded(arena.data(),unsigned(arena.size()),G_ROOM_ID)==WATER29_REFUSED);
    re4dc_effect_retire_room();s_water29_archive_incarnation=before_exhaustion;
    auto no=payload(argv[2]);G_ROOM_ID=0x10b;
    bindings[5].archive=no.data();
    assert(Water29ReadRoomLoaded(no.data(),unsigned(no.size()),G_ROOM_ID)==WATER29_NO_WATER);
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_NO_WATER && !re4dc_water_ps2_rows());
    re4dc_effect_retire_room();
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND && re4dc_water_ps2_rows());
#if RE4DC_WATER_PS2_EXT
    auto ext=payload(argv[3]);G_ROOM_ID=0x10c;bindings[5].archive=ext.data();
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND && view.ext_count==14);
    ++now_frame;
    puts("COMPILED-EXT");re4dc_water_ps2_draw(nullptr);puts("END-COMPILED-EXT");
    assert(Water29ReadRoomLoaded(ext.data(),unsigned(ext.size()),G_ROOM_ID)==WATER29_BOUND);
    assert(Water29Select(G_ROOM_ID,&view)==WATER29_BOUND && view.ext_count==14);
    assert(!memcmp(view.ext_rows,kWaterPs2Ext,14*sizeof(WaterPs2ExtRow)));
    before=ot_calls;re4dc_water_ps2_queue();assert(ot_calls==before+1);
    ++now_frame;
    puts("LOADED-EXT");re4dc_water_ps2_draw(nullptr);puts("END-LOADED-EXT");
    re4dc_effect_retire_room();
#endif
    puts("PASS W29 actual package/load/consumer/retire");
}
'''


class WaterPackage29Test(unittest.TestCase):
    def test_primary_makefile_scope_and_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            kos = Path(tmp) / 'kos'; kos.mkdir()
            (kos / 'Makefile.rules').write_text('')
            obj = Path(tmp) / 'obj'
            targets = tuple(str(obj / name) for name in
                            ('src/game/espgen45.o', 'src/game/read.o',
                             'platform/native_effect.o', 'platform/native_ui.o'))
            def run(value):
                args = ['make', '-f', 'Makefile', '-n', f'KOS_BASE={kos}', 'ROUTE_CH13=1',
                        'WATER_PS2=1', 'WATER45_NATIVE=1', f'OBJDIR={obj}', *targets]
                if value is not None:
                    args.append('WATER_LAYER29=' + value)
                return subprocess.run(args, cwd=ROOT / 'port/dreamcast/game',
                                      capture_output=True, text=True)
            arms = [run(None), run('0'), run('1')]
            for arm in arms:
                self.assertEqual(arm.returncode, 0, arm.stderr)
            commands = [[line for line in arm.stdout.splitlines() if line.startswith('kos-c++')]
                        for arm in arms]
            self.assertEqual(commands[0], commands[1])
            self.assertEqual(len(commands[2]), len(targets))
            for target, command in zip(targets, commands[2]):
                self.assertIn('-o ' + target, command)
                self.assertEqual(command.count('-DRE4DC_WATER_LAYER29=1'),
                                 int(target != str(obj / 'platform/native_ui.o')))
            for bad in ('', '%', '0 1', '2', '00'):
                self.assertNotEqual(run(bad).returncode, 0, bad)

    def test_primary_makefile_target_conditioned_off_identity(self):
        # Use the actual per-object Make definitions, including WATER45_LEAN
        # selected by ROUTE_CH13 and the disc-profile gate for EFFECT_BIND_DIAG.
        # Host cpp exercises the SH conditionals; this is not an SH object or
        # complete programme/overlay comparison with the pinned SDK.
        game = ROOT / 'port/dreamcast/game'
        paths = ('src/game/espgen45.cpp', 'src/game/read.cpp',
                 'port/dreamcast/game/platform/native_effect.cpp')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            kos = p / 'kos'; (kos / 'kos').mkdir(parents=True)
            (kos / 'Makefile.rules').write_text('')
            (kos / 'kos.h').write_text('')
            (kos / 'kos/net.h').write_text('')
            targets = tuple(str(p / 'obj' / name) for name in
                            ('src/game/espgen45.o', 'src/game/read.o', 'platform/native_effect.o'))
            for ext in (0, 1):
                for diag in (0, 1):
                    make = ['make', '-f', 'Makefile', '-n', f'KOS_BASE={kos}',
                            f'OBJDIR={p / "obj"}', 'ROUTE_CH13=1', 'WATER45_NATIVE=1',
                            'WATER_PS2=1', f'WATER_PS2_EXT={ext}', 'DISC_READ_FALLBACK=3',
                            f'EFFECT_BIND_DIAG={diag}', *targets]
                    run = subprocess.run(make, cwd=game, capture_output=True, text=True)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    commands = [shlex.split(line) for line in run.stdout.splitlines()
                                if line.startswith('kos-c++')]
                    self.assertEqual(len(commands), len(paths))
                    for path, args in zip(paths, commands):
                        self.assertEqual((game / args[args.index('-c') + 1]).resolve(), ROOT / path)
                        flags = [arg for arg in args if arg.startswith(('-D', '-U', '-I'))]
                        self.assertFalse(any('RE4DC_WATER_LAYER29' in arg for arg in flags))
                        self.assertEqual('-DRE4DC_EFFECT_BIND_DIAG=1' in flags,
                                         bool(diag and path != 'src/game/espgen45.cpp'))
                        old = p / Path(path).name
                        old.write_bytes(subprocess.check_output(
                            ['git', 'show', f'{RECOVERY_BASE}:{path}'], cwd=ROOT))
                        pp = ['g++', '-E', '-P', '-std=gnu++20', '-fpermissive', '-w',
                              '-D__sh__', '-U__PPC__', f'-I{kos}', f'-I{ROOT / "src/game"}',
                              *flags]
                        outputs = [subprocess.check_output(pp + extra + [str(source)], cwd=game)
                                   for source, extra in ((old, []), (ROOT / path, []),
                                       (ROOT / path, ['-DRE4DC_WATER_LAYER29=0']))]
                        self.assertEqual(outputs[0], outputs[1], (path, ext, diag, 'absent'))
                        self.assertEqual(outputs[0], outputs[2], (path, ext, diag, 'zero'))

    def test_feature_off_source_and_object_identity(self):
        def unit(path, source):
            if path == 'src/game/read.cpp':
                marker = '#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_WATER_LAYER29)'
                declaration = (source[source.index(marker):source.index('#endif', source.index(marker)) + 6]
                               if marker in source else '')
                start = source.index('        if (!re4dc_effect_bind_room(pG->pRoom, out_data_size))')
                end = source.index('        readTime = StopwatchStop(NULL);', start)
                body = source[start:end]
                return ('''#include <cstdint>\nstruct Game{void* pRoom;unsigned room_id;};
                         static Game game;static Game* pG=&game;static unsigned out_data_size;
                         static int re4dc_effect_bind_room(void*,unsigned){return 1;}
                         static int re4dc_ui_bind_room(void*,unsigned){return 1;}
                         static void re4dc_missing(const char*){}\n''' + declaration +
                        '\nvoid loaded(){\n' + body + '\n}\n')
            marker = '#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29\nextern "C" void re4dc_water29_retire_archive();'
            declaration = (source[source.index(marker):source.index('#endif', source.index(marker)) + 6]
                           if marker in source else '')
            return ('''struct Binding{void* archive;};static Binding bindings[6];
                      extern "C" void re4dc_effect_unbind(void*){}\n''' + declaration + '\n' +
                    function(source, 'extern "C" void re4dc_effect_retire_room()') + '\n')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for path in ('src/game/read.cpp', 'port/dreamcast/game/platform/native_effect.cpp'):
                original = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True)
                current = (ROOT / path).read_text()
                old, new = unit(path, original), unit(path, current)
                file = p / 'same.cpp'; obj = p / 'same.o'
                flags = ['g++', '-std=c++17', '-O2', '-DRE4DC_GAME=1']
                for value in (None, '0'):
                    arm = flags + (['-DRE4DC_WATER_LAYER29=' + value] if value else [])
                    preprocessed = []
                    objects = []
                    for code in (old, new):
                        file.write_text(code)
                        preprocessed.append(subprocess.check_output(arm + ['-E', '-P', str(file)], text=True))
                        subprocess.run(arm + ['-c', str(file), '-o', str(obj)], check=True)
                        objects.append(obj.read_bytes())
                    self.assertEqual(preprocessed[0], preprocessed[1], path)
                    self.assertEqual(objects[0], objects[1], path)
            # The complete effect TU also has line-number diagnostics outside
            # the retirement excerpt. Compare their real macro expansions;
            # source-line changes must not escape an otherwise disabled hook.
            stub = p / 'stubs'
            (stub / 'kos').mkdir(parents=True)
            (stub / 'kos.h').write_text('')
            (stub / 'kos/net.h').write_text('')
            old = subprocess.check_output(['git', 'show',
                f'{BASE}:port/dreamcast/game/platform/native_effect.cpp'], cwd=ROOT, text=True)
            new = EFFECT.read_text()
            file = p / 'native_effect.cpp'
            for diag in ('0', '1'):
                for value in (None, '0'):
                    arm = ['g++', '-E', '-P', '-std=c++17', '-D__sh__',
                           '-DRE4DC_EFFECT_BIND_DIAG=' + diag,
                           '-I' + str(stub),
                           '-I' + str(ROOT / 'port/dreamcast/game/platform/include')]
                    if value is not None:
                        arm += ['-DRE4DC_WATER_LAYER29=' + value]
                    outputs = []
                    for code in (old, new, new.replace('#line 15\n', '', 1)):
                        file.write_text(code)
                        outputs.append(subprocess.check_output(arm + [str(file)], text=True))
                    self.assertEqual(outputs[0], outputs[1], ('full effect TU', diag, value))
                    if diag == '1':
                        self.assertNotEqual(outputs[0], outputs[2], 'negative line-shift control')

    def test_producer_archive_and_existing_graft(self):
        original = synthetic_dar()
        source = synthetic_dar(changed=True)
        grafted, report = dar_graft.graft(original, source, ['0x5 QAX'])
        self.assertEqual(report['grafted'][0]['name'], '0x5 QAX')
        self.assertNotEqual(grafted, original)
        self.assertEqual(dar_graft._payload(grafted)[1], dar_graft._payload(source)[1])
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'source.dar'; src.write_bytes(original)
            out = Path(tmp) / 'water.dar'
            cmd = [sys.executable, '-B', str(producer.HERE / 'water_package29.py'),
                   '--input', str(src), '--output', str(out), '--room', 'r107']
            subprocess.run(cmd, check=True)
            self.assertFalse(out.exists())
            subprocess.run(cmd + ['--enable-water29'], check=True)
            self.assertEqual(src.read_bytes(), original)
            data = out.read_bytes()
            old = room_smd.tagged_entries(dar_graft._payload(original)[1], '<')
            new = room_smd.tagged_entries(dar_graft._payload(data)[1], '<')
            self.assertEqual(len(new), len(old) + 1)
            self.assertEqual(new[-1][0], b'W29\0')
            self.assertEqual(new[-1][2] - new[-1][1], room_smd.align(len(producer.member(0x107))))
            for i in range(len(old)):
                if old[i][0] not in (b'NTR\0', b'ESQ\0'):
                    a = dar_graft._payload(original)[1]; b = dar_graft._payload(data)[1]
                    self.assertEqual(a[old[i][1]:old[i][2]], b[new[i][1]:new[i][2]])
            a = dar_graft._payload(original)[1]; b = dar_graft._payload(data)[1]
            for i in (2, 3):
                old_record = struct.unpack_from('<3I', a, old[i][1] + 32)
                new_record = struct.unpack_from('<3I', b, new[i][1] + 32)
                self.assertNotEqual(old_record[0], new_record[0])
                for old_addr, new_addr, span in zip(old_record[:1] if i == 3 else old_record,
                                                    new_record[:1] if i == 3 else new_record,
                                                    (64,) if i == 3 else (32, 36, 12)):
                    self.assertEqual(a[old_addr:old_addr + span], b[new_addr:new_addr + span])
            self.assertNotEqual(subprocess.run(cmd + ['--enable-water29', '--input', str(out),
                                                      '--output', str(Path(tmp) / 'duplicate.dar')],
                                               capture_output=True).returncode, 0)
            self.assertNotEqual(subprocess.run(cmd + ['--enable-water29', '--output', str(src)],
                                               capture_output=True).returncode, 0)
            alias = Path(tmp) / 'input-hardlink.dar'
            os.link(src, alias)
            self.assertNotEqual(subprocess.run(cmd + ['--enable-water29', '--output', str(alias)],
                                               capture_output=True).returncode, 0)
            self.assertEqual(src.read_bytes(), original)
            bad = bytearray(original); bad[16:20] = bytes(4)
            self.assertRaises(ValueError, dar_graft.append_water_member, bytes(bad), producer.member(0x107))
            bad = bytearray(original); bad[1024 + 4] = 1
            self.assertRaises(ValueError, dar_graft.append_water_member, bytes(bad), producer.member(0x107))
            bad = bytearray(original); bad[16 + 4 * 4 + 3] = 1
            self.assertRaises(ValueError, dar_graft.append_water_member, bytes(bad), producer.member(0x107))
            bad = bytearray(original); ntr = room_smd.tagged_entries(dar_graft._payload(original)[1], '<')[2][1]
            bad[1024 + ntr:1024 + ntr + 8] = b'BADTABLE'
            self.assertRaises(ValueError, dar_graft.append_water_member, bytes(bad), producer.member(0x107))
            bad = bytearray(original)
            struct.pack_into('<I', bad, 1024 + ntr + 12, 4)  # rows cross the NTR member boundary
            self.assertRaises(ValueError, dar_graft.append_water_member, bytes(bad), producer.member(0x107))

    def test_production_load_to_consumer_and_retirement(self):
        read_source = READ.read_text()
        effect_source = EFFECT.read_text()
        self.assertLess(read_source.index('Water29ReadRoomLoaded(pG->pRoom, out_data_size, pG->room_id)'),
                        read_source.index('PSet(pG->Rtp, GetDataExt'))
        self.assertLess(effect_source.index('re4dc_water29_retire_archive();'),
                        effect_source.index('re4dc_effect_unbind(bindings[5].archive);'))
        read_hook = function(read_source, 'static inline int Water29ReadRoomLoaded(')
        retire_hook = function(effect_source, 'extern "C" void re4dc_effect_retire_room()')
        cpp = production_cpp(SOURCE.read_text()).split('\nint main() {')[0] + CASES
        cpp = cpp.replace('__READ_HOOK__', read_hook).replace('__RETIRE_HOOK__', retire_hook)
        sanitizer = os.environ.get('WATER29_SANITIZE') == '1'
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            source = p / 'source.dar'; source.write_bytes(synthetic_dar())
            files = [p / 'main.dar', p / 'no.dar', p / 'ext.dar']
            for file, room, no_water in zip(files, ('r107', 'r10b', 'r10c'), (False, True, False)):
                cmd = [sys.executable, '-B', str(producer.HERE / 'water_package29.py'),
                       '--enable-water29', '--input', str(source), '--output', str(file), '--room', room]
                if no_water:
                    cmd.append('--intentional-no-water')
                subprocess.run(cmd, check=True)
            source_cpp = p / 'water-package.cpp'; source_cpp.write_text(cpp)
            for ext_on in (0, 1):
                exe = p / f'water-package-{ext_on}'
                flags = ['g++', '-std=c++17', '-O1' if sanitizer else '-O2', '-g',
                         '-DRE4DC_WATER_LAYER29=1', '-DRE4DC_WATER_PS2=1',
                         f'-DRE4DC_WATER_PS2_EXT={ext_on}', '-DRE4DC_WATER45_NATIVE=1',
                         '-DRE4DC_WATER_PS2_ROOMS=63', '-DRE4DC_WATER_PS2_EXT_ROOMS=7',
                         '-DRE4DC_WATER_PS2_FLIP=8',
                         f'-I{ROOT / "src/game"}', str(source_cpp), '-o', str(exe)]
                if sanitizer:
                    flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
                subprocess.run(flags, check=True)
                run = subprocess.run([str(exe), *map(str, files)], check=True, capture_output=True, text=True)
                first = run.stdout.split('COMPILED\n', 1)[1].split('END-COMPILED\n', 1)[0]
                second = run.stdout.split('LOADED\n', 1)[1].split('END-LOADED\n', 1)[0]
                self.assertEqual(first, second)
                if ext_on:
                    first_ext = run.stdout.split('COMPILED-EXT\n', 1)[1].split('END-COMPILED-EXT\n', 1)[0]
                    second_ext = run.stdout.split('LOADED-EXT\n', 1)[1].split('END-LOADED-EXT\n', 1)[0]
                    self.assertEqual(first_ext, second_ext)
                self.assertIn('PASS W29 actual package/load/consumer/retire', run.stdout)


if __name__ == '__main__':
    unittest.main()
