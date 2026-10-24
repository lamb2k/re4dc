"""Fail-closed host checks of the future mode1 SH4 allocator route graph."""
import hashlib, json, re, shlex, struct
from pathlib import Path

WRAPS = ['malloc', 'calloc', 'realloc', 'memalign', 'free', '_Znwj', '_Znaj']
ROUTES = [('_aligned_alloc', '__memalign_r'), ('__memalign_r', '___wrap_memalign'),
          ('__malloc_r', '___wrap_malloc'), ('__calloc_r', '___wrap_calloc'),
          ('__realloc_r', '___wrap_realloc'), ('__free_r', '___wrap_free')]

class ELF:
    def __init__(self, data):
        self.data = data
        assert len(data) < 64 * 1024**2 and data[:7] == b'\x7fELF\x01\x01\x01'
        e = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
        assert e[1] == 2 and e[2] == 42 and e[11] == 40 and 0 < e[12] < 8192
        assert e[6] + e[11] * e[12] <= len(data)
        self.sections = [struct.unpack_from('<IIIIIIIIII', data, e[6] + i * e[11]) for i in range(e[12])]
        self.symbols = {}
        for s in self.sections:
            if s[1] != 2: continue
            assert s[9] == 16 and s[4] + s[5] <= len(data)
            st = self.sections[s[6]]; strings = data[st[4]:st[4] + st[5]]
            for pos in range(s[4], s[4] + s[5], 16):
                name, value, size, info, other, index = struct.unpack_from('<IIIBBH', data, pos)
                assert name < len(strings)
                name = strings[name:].split(b'\0', 1)[0].decode()
                if name and index and (info & 15) == 2:
                    entry = (value, size, index)
                    if name in self.symbols: assert self.symbols[name] == entry
                    self.symbols[name] = entry

    def function(self, name):
        address, size, index = self.symbols[name]
        s = self.sections[index]
        assert s[2] & 2 and s[2] & 4 and 0 < size <= s[5]
        assert s[3] <= address and address + size <= s[3] + s[5]
        return address, size

    def at(self, address, size):
        found = [s for s in self.sections if s[1] != 8 and s[2] & 2 and s[3] <= address and address + size <= s[3] + s[5]]
        assert len(found) == 1
        s = found[0]; pos = s[4] + address - s[3]
        assert pos + size <= len(self.data)
        return self.data[pos:pos + size]

    def tail_route(self, source, target):
        """Bounded literal-load then jmp/jsr; only harmless argument moves permitted."""
        begin, size = self.function(source); destination, _ = self.function(target)
        assert size <= 1024
        hits = []
        for address in range(begin, begin + size - 1, 2):
            op, = struct.unpack('<H', self.at(address, 2))
            if op & 0xf000 != 0xd000: continue
            reg = (op >> 8) & 15; literal = ((address + 4) & ~3) + (op & 255) * 4
            if not begin <= literal <= begin + size - 4: continue
            value, = struct.unpack('<I', self.at(literal, 4))
            if value != destination: continue
            for distance in range(1, 5):
                pc = address + distance * 2
                if pc + 4 > min(literal, begin + size): break
                instruction, = struct.unpack('<H', self.at(pc, 2))
                if instruction in (0x402b | reg << 8, 0x400b | reg << 8):
                    hits.append({'load': address, 'literal': literal, 'branch': pc, 'target': destination}); break
                # mov Rm,Rn or mov.l @Rm,Rn, used for reentrant argument shuffles.
                if instruction == 0x0009: continue
                if instruction & 0xf00f in (0x6003, 0x6002) and (instruction >> 8) & 15 != reg: continue
                break
        assert len(hits) == 1, (source, target, hits)
        return hits[0]

def link_graph(log, arm, baseline_wraps=None):
    lines = log.splitlines()
    links = [line for line in lines if 'bash tools/link.sh ' in line]
    assert len(links) == 1
    args = shlex.split(links[0]); objects = [a for a in args if a.endswith('.o')]
    wraps = re.findall(r'-Wl,--wrap=([A-Za-z0-9_]+)', ' '.join(args))
    assert set(WRAPS) <= set(wraps) and 'aligned_alloc' not in wraps
    assert all(wraps.count(w) == 1 for w in WRAPS)
    if baseline_wraps is not None:
        assert [w for w in wraps if w not in WRAPS] == baseline_wraps
    assert len(objects) == {'off': 449, 'on': 455}[arm]
    assert sum(x.endswith('/kos_census.o') for x in objects) == 1
    motion = [x for x in objects if x.endswith('/gc_asset_motion_unknown.o')]
    assert len(motion) == int(arm == 'on')
    if motion:
        i = objects.index(motion[0]); assert objects[i-1].endswith('/gc_asset_audio.o') and objects[i+1].endswith('/mtx.o')
    compile_lines = [line for line in lines if ' -c platform/kos_census.cpp ' in line]
    ui_lines = [line for line in lines if ' -c ui_bridge.cpp ' in line]
    assert len(compile_lines) == len(ui_lines) == 1
    for line in compile_lines + ui_lines:
        assert '-DRE4DC_KOS_CENSUS=1' in shlex.split(line)
        assert '-DRE4DC_KOS_CENSUS=2' not in line
    overlays = [line.split('gen_overlay: .ovl_', 1)[1].split()[0] for line in lines if 'gen_overlay: .ovl_' in line]
    assert overlays == ['pl0f','em2f','em22','em2b','pl11','pl14','em3b','em35','st1_0','st1_1','st1_2','st1_3','st2_0','Sscrn']
    return {'raw_object_count': len(objects), 'wraps': wraps, 'kos_census_compiles': 1,
            'overlay_order': overlays, 'ordered_objects': objects, 'link_line_sha256': hashlib.sha256(links[0].encode()).hexdigest()}

def verify(elf_path, build_log, arm, baseline_wraps=None):
    data = Path(elf_path).read_bytes(); elf = ELF(data)
    graph = link_graph(Path(build_log).read_text(), arm, baseline_wraps)
    routes = {source + ' -> ' + target: elf.tail_route(source, target) for source, target in ROUTES}
    for name in WRAPS:
        wrapper = '___wrap_' + name; provider = '_' + name
        assert elf.function(wrapper)[0] != elf.function(provider)[0]
        routes[wrapper + ' -> ' + provider] = elf.tail_route(wrapper, provider)
    assert '_re4dc_kos_census_log' in elf.symbols
    assert '_re4dc_kos_threads_report' not in elf.symbols and '_re4dc_kos_census_window' not in elf.symbols
    return {'status': 'MODE1_LINK_AND_REENTRANT_ROUTE_GRAPH_PASS', 'ELF_sha256': hashlib.sha256(data).hexdigest(),
            'graph': graph, 'routes': routes, 'runtime_coverage': 'UNKNOWN until live table/lost/overflow/mallinfo reconciliation',
            'qualification': 'Diagnostic graph only. Not memory/performance/guest acceptance.'}
