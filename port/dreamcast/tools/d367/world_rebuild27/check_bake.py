#!/usr/bin/env python3
"""Check private C10 bake data and the actual runtime routing block on the host.

No SDK, emulator, staging or asset generation. Output must be a new directory.
All decoded geometry and generated consumers remain in that private directory.
The streams cover every actual package level plus sparse/partial selections;
they do not claim to execute camera visibility or the SH4/PVR emitter.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import zlib


def require(ok, why):
    if not ok:
        raise AssertionError(why)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canon(tris):
    out = collections.Counter()
    for t in tris:
        t = tuple(tuple(v) for v in t)
        out[min(t, t[1:] + t[:1], t[2:] + t[:2])] += 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'source', 'reference', 'exchange', 'atlas', 'candidate', 'out'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    for name in vars(a):
        setattr(a, name, getattr(a, name).resolve())
    require(not a.out.exists(), 'refuse existing output')
    a.out.mkdir(parents=True)
    tools = a.repo / 'port/dreamcast/tools'
    sys.path.insert(0, str(tools))
    import world_rebuild27 as w
    import convert_tpl
    original, files, owners, policy = w.load(a.source)
    refblob = (a.reference / 'ps2-world.re4mesh').read_bytes()
    ref = w.codec.decode(refblob, files['ps2-world.r4pw'], True)
    raw = (a.candidate / 'ps2-world.re4mesh').read_bytes()
    d = w.codec.decode(raw, files['ps2-world.r4pw'], True)
    exchange = json.loads(a.exchange.read_text())
    atlas = json.loads(a.atlas.read_text())
    receipt = json.loads((a.candidate / 'RECEIPT.json').read_text())
    require(exchange['schema'] == 're4dc.world-rebuild27.house-exchange/1', 'exchange schema')
    require(atlas['schema'] == 're4dc.world-rebuild27.house-baked-atlas/1', 'atlas schema')
    require(exchange['candidate_sha256'] == hashlib.sha256(refblob).hexdigest() ==
            atlas['geometry_candidate_sha256'], 'reference/atlas candidate pin')
    for n in w.SOURCE_INPUTS:
        require(exchange['source_sha256'][n] == hashlib.sha256(files[n]).hexdigest(), 'source pin ' + n)
    require(policy == 0x68100b21, 'source policy')
    for n in w.UNCHANGED_COMPANIONS:
        require((a.reference / n).read_bytes() == files[n] == (a.candidate / n).read_bytes(),
                'unchanged whole companion ' + n)
    for field in ('meshes', 'placements', 'materials', 'part_lods'):
        require(d[field] == ref[field] == original[field], 'source identity ' + field)
    require([p[:6] + p[8:] for p in d['parts']] ==
            [p[:6] + p[8:] for p in ref['parts']] ==
            [p[:6] + p[8:] for p in original['parts']], 'part source identity and UV basis')
    require([c[6:] for c in d['clusters']] == [c[6:] for c in original['clusters']], 'cluster identity')
    require([c[6:] for c in ref['clusters']] == [c[6:] for c in original['clusters']], 'reference cluster identity')
    header = (a.candidate / 'world_rebuild27_bake_certificates.inc').read_text()
    numbers = lambda s: [int(v, 0) for v in re.findall(r'0x[0-9a-fA-F]+|\d+', s)]
    mesh_crc, mesh_bytes = numbers(re.search(r'mesh_crc=(.*?);', header).group(1))
    ranges = [numbers(s) for s in re.findall(r'\{(\d+U,\d+U,\d+U,\{[^}]+\})\}', header)]
    textures = [numbers(s) for s in re.findall(r'\{([^{}]+)\}', header.split('textures[2][4]=', 1)[1])]
    require(len(textures) == 2 and 0 < len(ranges) <= 16, 'bounded private table')
    require(len(raw) == mesh_bytes and struct.unpack_from('<I', raw, 12)[0] == mesh_crc ==
            zlib.crc32(raw[80:]) & 0xffffffff, 'actual body CRC')
    part_mesh = {pi: mi for mi, m in enumerate(d['meshes']) for pi in range(m[6], m[6] + m[7])}
    rolepart = {exchange[role]['part']: role for role in ('wall', 'roof')}
    require(set(rolepart) == {160, 288}, 'approved part scope')
    counts = {role: dict(source=len(exchange[role]['source']), target=len(exchange[role]['target']))
              for role in ('wall', 'roof')}
    target_count = sum(c['target'] for c in counts.values())
    require(sum(c['source'] for c in counts.values()) == 407 and
            all(c['target'] > 0 for c in counts.values()) and target_count <= 128,
            '407-source core and bounded final target exchange')
    by_meshlet = {}
    ranges_out = []
    for part, first, count, *key in ranges:
        require(part in rolepart and key in textures and count > 0, 'range shape/key')
        require(part_mesh[part] not in owners, 'range touches changing owner')
        require(d['parts'][part][7] <= 320 and d['materials'][part][4] == 0,
                'owned part exceeds certified selector capacity or opaque material scope')
        fc, cc = d['part_lods'][part]
        l0, higher = set(), set()
        for ci in range(fc, fc + cc):
            cl = d['clusters'][ci]
            for ordinal in range(cl[7]):
                lv = d['levels'][cl[6] + ordinal]
                (l0 if ordinal == 0 else higher).update(range(lv[0], lv[0] + lv[1]))
        selected = set(range(first, first + count))
        require(selected <= l0 and not selected & higher, 'range is not private L0')
        for j in selected:
            require(j not in by_meshlet, 'overlapping ranges')
            by_meshlet[j] = (part, textures.index(key))
        ranges_out.append(dict(part=part, mesh=part_mesh[part], first=first, count=count, key=key,
                               placements=[i for i, p in enumerate(d['placements']) if p[0] == part_mesh[part]]))
    def triangles(doc, j):
        vi = w.codec.local_vertices(doc, j)
        return [tuple(tuple(doc['vertices'][vi[k]]) for k in t) for t in w.codec.triangles(doc, j)]
    core = collections.defaultdict(list)
    corevi, othervi = set(), set()
    for j in range(len(d['meshlets'])):
        vi = set(w.codec.local_vertices(d, j))
        if j in by_meshlet:
            corevi.update(vi)
            part, slot = by_meshlet[j]
            core[part].extend(triangles(d, j))
            require(all(v[5] == 65535 for t in triangles(d, j) for v in t), 'baked vertex is not white')
        else:
            othervi.update(vi)
    require(not corevi & othervi, 'baked vertices shared with unbound meshlets')
    for part, role in rolepart.items():
        require(canon(core[part]) == canon(t['baked_corners_existing_part_basis']
                                        for t in atlas[role]['target_triangles']), 'exact encoded atlas coverage')
        require(canon(t['original_corners'] for t in atlas[role]['target_triangles']) ==
                canon(t['corners'] for t in exchange[role]['target']), 'atlas original target coverage')
        require(exchange[role]['mesh'] == part_mesh[part], 'exchange mesh ownership')
        require(atlas[role]['source_part'] == part and atlas[role]['source_mesh'] == part_mesh[part],
                'atlas ownership')
        require(all(v[:3] == original_v[:3] for t in atlas[role]['target_triangles']
                    for v, original_v in zip(t['baked_corners_existing_part_basis'], t['original_corners'])),
                'bake moved geometry')
    higher_count = owner_count = level_count = 0
    # Across each part's complete L0 stream, exactly the named source core is
    # replaced. This explicitly rejects inherited C8 panel losses in context.
    for pi, (fc, cc) in enumerate(d['part_lods']):
        base_l0, ref_l0, out_l0 = [], [], []
        for ci in range(fc, fc + cc):
            cl = d['clusters'][ci]
            for ordinal in range(cl[7]):
                li = cl[6] + ordinal
                before = w.level_triangles(original, original['levels'][li])
                reference = w.level_triangles(ref, ref['levels'][li])
                after = w.level_triangles(d, d['levels'][li])
                level_count += 1
                if ordinal:
                    require(canon(after) == canon(reference) == canon(before), 'higher LOD changed')
                    higher_count += 1
                else:
                    base_l0.extend(before); ref_l0.extend(reference); out_l0.extend(after)
                if part_mesh[pi] in owners:
                    require(canon(after) == canon(before), 'changing owner changed')
                    owner_count += 1
        basec, refc, outc = canon(base_l0), canon(ref_l0), canon(out_l0)
        if pi in rolepart:
            role = rolepart[pi]
            sourcec = canon(t['corners'] for t in exchange[role]['source'])
            targetc = canon(t['corners'] for t in exchange[role]['target'])
            require(not sourcec - basec and not targetc - refc, 'source/target triangle absent')
            require(refc == basec - sourcec + targetc, 'reference has unrelated source changes')
            require(outc == refc - targetc + canon(core[pi]), 'candidate has unrelated corner changes')
        else:
            require(outc == refc == basec, 'unrelated L0 part changed')
    require(receipt['source_triangles'] == 407 and receipt['candidate_core_triangles'] == target_count,
            'receipt triangle counts')
    require(receipt['candidate_sha256'] == hashlib.sha256(raw).hexdigest(), 'receipt candidate pin')
    texture_rows = []
    for key in textures:
        path = a.candidate / 'tex' / ('%08x-%08x.re4tex' % tuple(key[:2]))
        blob = path.read_bytes(); h = convert_tpl.HEADER.unpack_from(blob)
        t = convert_tpl.TEXTURE.unpack_from(blob, h[5]); payload = blob[h[6]:h[6] + h[7]]
        require((t[1], t[2], t[3], t[6], t[7]) ==
                (512, 512, convert_tpl.FORMAT_RGB565, 0, convert_tpl.PAYLOAD_VQ), 'texture format')
        require(t[5] == len(payload) == 67584, 'full VQ codebook/payload cost')
        require(key == [zlib.crc32(payload) & 0xffffffff, w.fnv(payload), 512, 512], 'texture key/payload')
        texture_rows.append(dict(key=key, sha256=sha(path), payload_bytes=len(payload)))
    # Oracle derives from independently validated exact triangle/range ownership,
    # rather than calling the runtime slot function to construct expectations.
    nparts, nlets = len(d['parts']), len(d['meshlets'])
    oracle = bytearray([255]) * (nparts * nlets)
    for j, (part, slot) in by_meshlet.items():
        oracle[part * nlets + j] = slot
    (a.out / 'oracle.bin').write_bytes(oracle)
    sg = (a.candidate / 'ps2-world.r4sg').read_bytes()
    sgh = struct.unpack_from('<4s7I', sg)
    require(sgh[:3] == (b'R4SG', 1, nlets) and 1 <= sgh[3] <= 8 and
            sgh[4:7] == (mesh_crc, mesh_bytes, policy) and
            zlib.crc32(sg[32:]) & 0xffffffff == sgh[7], 'actual strip-group binding')
    require(len(sg) == 32 + nlets * sgh[3] * 16, 'strip-group extent')
    partial_picks = bytearray()
    for j in range(nlets):
        previous = 0; groups = []
        for k in range(sgh[3]):
            group = struct.unpack_from('<8H', sg, 32 + (j * sgh[3] + k) * 16)
            if group[6] != previous:
                groups.append((k, group[7] & 255, group[7] >> 8))
            previous = group[6]
        chosen = groups[::2]
        require(chosen, 'meshlet has no actual strip group')
        partial_picks.extend(struct.pack('<H6B', j, len(chosen), sum(1 << g[0] for g in chosen),
                                         min(g[1] for g in chosen), max(g[2] for g in chosen), 7, 11))
    (a.out / 'partial-picks.bin').write_bytes(partial_picks)
    source_path = a.repo / 'port/dreamcast/game/platform/native_static.cpp'
    native = source_path.read_text()
    pick = re.search(r'    struct Pick \{.*?\n    \};', native, re.S).group(0)
    start = native.index('const ChunkPart& queued=cctx[j];unsigned consumed=0;')
    # Include the complete enabled routing preamble, including consumption
    # after selecting either the original snapshot or an owned routed copy.
    # The ordinary knob-OFF declaration is a stable boundary, independent of
    # the enabled path's local pointer/reference names.
    end = native.index('\n#else\n            const ChunkPart& x=cctx[j];', start)
    routing = native[start:end]
    require(routing.count('do {') == 1 and 'world_bake27::run' in routing, 'routing extraction')
    consumer = CONSUMER.replace('PICK_DEFINITION', pick).replace('ACTUAL_ROUTING_BLOCK', routing)
    (a.out / 'consumer.cpp').write_text(consumer)
    (a.out / 'kos').mkdir()
    (a.out / 'kos/fs.h').write_text('#pragma once\ntypedef int file_t;\n#define FILEHND_INVALID (-1)\n')
    flags = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
             '-DRE4DC_WORLD_REBUILD27=1', '-DRE4DC_SCENERY_N256=1', '-DRE4DC_WORLD_SG26=1',
             '-I' + str(a.out), '-I' + str(a.repo / 'port/dreamcast/room'),
             '-I' + str(a.repo / 'port/dreamcast/game/platform/include'),
             '-I' + str(tools / 'd367/texture_rect21')]
    def run(cmd, name, expected=0):
        result = subprocess.run([str(x) for x in cmd], capture_output=True, text=True)
        (a.out / (name + '.log')).write_text(result.stdout + result.stderr)
        require(result.returncode == expected if expected is not None else result.returncode != 0,
                name + ' unexpected exit: ' + result.stdout + result.stderr)
        return result
    run(flags + ['-I' + str(a.candidate), a.out / 'consumer.cpp', '-o', a.out / 'consumer'], 'compile')
    execution = run([a.out / 'consumer', a.candidate / 'ps2-world.re4mesh',
                     a.source / 'ps2-world.r4pw', a.out / 'oracle.bin', a.out / 'partial-picks.bin'], 'consumer')
    host = json.loads(execution.stdout)
    # Compile the genuine header against malformed private data; retain logs.
    syntax = a.out / 'syntax.cpp'
    syntax.write_text('#include "world_rebuild27_bake.h"\n')
    missing = a.out / 'missing'; missing.mkdir()
    failure = run(flags + ['-I' + str(missing), '-fsyntax-only', syntax], 'missing-private-include', None)
    require('world_rebuild27_bake_certificates.inc' in failure.stderr and
            'No such file' in failure.stderr, 'missing-include refusal has unrelated cause')
    first_row = re.search(r'\{\d+U,\d+U,\d+U,\{[^}]+\}\},', header).group(0)
    mutations = {
        'zero-count': re.sub(r'(\{\d+U,\d+U,)\d+U', r'\g<1>0U', header, count=1),
        'foreign-part': re.sub(r'\{(?:160|288)U,', '{159U,', header, count=1),
        'overflow-range': re.sub(r'(\{\d+U,)\d+U', r'\g<1>65536U', header, count=1),
        'bad-texture-size': header.replace('0x00000200U', '0x00000100U'),
        'overlap-range': header.replace(first_row, first_row + '\n' + first_row, 1),
    }
    for name, text in mutations.items():
        require(text != header, 'mutation did not change header ' + name)
        folder = a.out / name; folder.mkdir()
        (folder / 'world_rebuild27_bake_certificates.inc').write_text(text)
        failure = run(flags + ['-I' + str(folder), '-fsyntax-only', syntax], name, None)
        require('Invalid private house bake routing certificate' in failure.stderr,
                'mutation failed for unrelated reason ' + name)
    require(sha(source_path) == hashlib.sha256(native.encode()).hexdigest(), 'runtime source changed during checks')
    result = dict(scope='SOURCE/HOST ONLY; no camera selector, emitter, SDK, emulator or console execution',
                  status='PASS', source_geometry_clean_A=True, source_to_target=counts,
                  candidate_sha256=hashlib.sha256(raw).hexdigest(), mesh_crc='%08x' % mesh_crc,
                  mesh_bytes=mesh_bytes, ranges=ranges_out, textures=texture_rows,
                  incremental_texture_payload_bytes=sum(t['payload_bytes'] for t in texture_rows),
                  core_vertex_records=len(corevi), core_retained_vertex_overlap=0,
                  owner_levels_exact=owner_count, higher_levels_exact=higher_count,
                  actual_package_levels=level_count, host=host,
                  mutation_compile_refusals=['missing-private-include', *mutations],
                  runtime_source_sha256=sha(source_path),
                  routing_block_sha256=hashlib.sha256(routing.encode()).hexdigest(),
                  bake_header_sha256=sha(a.repo / 'port/dreamcast/game/platform/include/world_rebuild27_bake.h'),
                  private_header_sha256=sha(a.candidate / 'world_rebuild27_bake_certificates.inc'),
                  policy_header_sha256=sha(a.candidate / 'world_rebuild27_certificates.inc'),
                  exchange_sha256=sha(a.exchange), atlas_sha256=sha(a.atlas),
                  strip_groups_sha256=sha(a.candidate / 'ps2-world.r4sg'),
                  helper_sha256=sha(Path(__file__)), compiler=subprocess.check_output(['g++', '--version'], text=True).splitlines()[0])
    (a.out / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


CONSUMER = r'''#include "instanced_mesh.hpp"
#include "world_rebuild27_bake.h"
#include "world_rect_provenance.h"
#include <fstream>
#include <iterator>
#include <vector>
#include <iostream>
#include <cstdlib>
PICK_DEFINITION
struct ChunkPart{unsigned key[6],index,first,count;};
static unsigned long checks=0,streams=0,picks=0,runs=0,atlas_picks=0;
void check(bool ok){++checks;if(!ok){std::cerr<<"failed check "<<checks<<"\n";std::exit(10);}}
std::vector<unsigned char> read(const char* path){std::ifstream f(path,std::ios::binary);return {(std::istreambuf_iterator<char>(f)),{}};}
std::uint32_t crc32(const unsigned char* p,unsigned n){unsigned c=~0U;while(n--){c^=*p++;for(unsigned k=0;k<8;++k)c=(c>>1)^((0U-(c&1U))&0xedb88320U);}return ~c;}
std::vector<ChunkPart> route(const Pick* cpk,unsigned count,unsigned index,const unsigned* key,bool baked){
    struct{bool baked;}ps2w{baked};ChunkPart cctx[1]{};unsigned j=0;
    for(unsigned k=0;k<6;++k)cctx[0].key[k]=key[k];
    cctx[0].index=index;cctx[0].first=0;cctx[0].count=count;
    std::vector<ChunkPart> result;
    ACTUAL_ROUTING_BLOCK
    result.push_back(x);
    } while(consumed<queued.count);
    return result;
}
int main(int argc,char** argv){
    if(argc!=5)return 2;
    auto mesh=read(argv[1]),world=read(argv[2]),oracle=read(argv[3]);
    auto partial_bytes=read(argv[4]);
    re4dc::room::MeshPackage p;check(p.adopt(mesh.data(),unsigned(mesh.size()),true,true));
    using namespace re4dc::world_bake27;
    using re4dc::rect21::provenance::policy_source_crc;
    const auto& h=p.header();
    check(oracle.size()==h.part_count*h.meshlet_count);
    check(sizeof(Pick)==8U && partial_bytes.size()==h.meshlet_count*sizeof(Pick));
    std::vector<Pick> grouped(h.meshlet_count);std::memcpy(grouped.data(),partial_bytes.data(),partial_bytes.size());
    auto admit=[&](unsigned room,unsigned crc,unsigned bytes){return matches(room,crc,bytes)&&
      policy_source_crc(room,world.data(),unsigned(world.size()),crc,bytes,h.part_count,h.mesh_count,mesh.data(),crc32)==0x68100b21U;};
    check(admit(0x101,h.crc,h.bytes));
    check(!admit(0x100,h.crc,h.bytes));check(!admit(0x101,h.crc^1U,h.bytes));check(!admit(0x101,h.crc,h.bytes+1U));
    for(unsigned at:{0U,8U,12U,16U,20U,80U,unsigned(mesh.size()-1U)}){
      mesh[at]^=1;check(!admit(0x101,h.crc,h.bytes));mesh[at]^=1;
    }
    for(unsigned at:{0U,4U,8U,12U,16U,20U,24U,28U,40U,unsigned(world.size()-1U)}){
      world[at]^=1;check(!admit(0x101,h.crc,h.bytes));world[at]^=1;
    }
    for(unsigned pi=0;pi<h.part_count;++pi)for(unsigned li=0;li<h.meshlet_count;++li){
      int expected=oracle[pi*h.meshlet_count+li]==255?-1:int(oracle[pi*h.meshlet_count+li]);
      check(slot(pi,li)==expected);
    }
    auto exercise=[&](unsigned pi,const std::vector<Pick>& input,bool baked){
      unsigned key[6];for(unsigned k=0;k<4;++k)std::memcpy(key+k,world.data()+32U+16U*pi+4U*k,4);
      // R4PW stores width/height as u16 and pass/cull as u8 after the two hashes.
      std::uint16_t wh[2];std::memcpy(wh,world.data()+32U+16U*pi+8U,4);
      key[2]=wh[0];key[3]=wh[1];key[4]=world[32U+16U*pi+12U];key[5]=world[32U+16U*pi+13U];
      auto output=route(input.data(),unsigned(input.size()),pi,key,baked);unsigned cursor=0;
      ++streams;picks+=input.size();runs+=output.size();
      for(const auto& r:output){
        check(r.first==cursor && r.count<=input.size()-cursor && (r.count || input.empty()));
        check(r.index==pi && r.key[4]==key[4] && r.key[5]==key[5]);
        int expected=-1;if(r.count && baked){auto v=oracle[pi*h.meshlet_count+input[cursor].let];expected=v==255?-1:int(v);}
        for(unsigned k=0;k<4;++k)check(r.key[k]==(expected<0?key[k]:textures[expected][k]));
        for(unsigned k=0;k<r.count;++k){auto before=input[cursor+k];auto after=input[r.first+k];
          check(std::memcmp(&before,&after,sizeof(Pick))==0);
          auto v=oracle[pi*h.meshlet_count+before.let];int want=(baked&&v!=255)?int(v):-1;
          check(want==expected);if(want>=0)++atlas_picks;
        }
        cursor+=r.count;
      }check(cursor==input.size());
    };
    for(unsigned pi=0;pi<h.part_count;++pi){
      auto pl=p.part_lods()[pi];
      for(unsigned ci=pl.first_cluster;ci<pl.first_cluster+pl.cluster_count;++ci){auto cl=p.clusters()[ci];
        for(unsigned level=0;level<cl.level_count;++level){auto lv=p.levels()[cl.first_level+level];
          std::vector<Pick> full,sparse,partial;
          for(unsigned n=0;n<lv.meshlet_count;++n){Pick pick{};pick.let=std::uint16_t(lv.first_meshlet+n);
            pick.nr=0xffU;
            full.push_back(pick);
            if(n%2==0 || oracle[pi*h.meshlet_count+pick.let]!=255)sparse.push_back(grouped[pick.let]);
            if(n>0 && n+1<lv.meshlet_count)partial.push_back(grouped[pick.let]);
            if(oracle[pi*h.meshlet_count+pick.let]!=255){
              exercise(pi,{grouped[pick.let]},true);Pick empty=grouped[pick.let];empty.nr=0;empty.gmask=0;exercise(pi,{empty},true);
            }}
          exercise(pi,full,true);exercise(pi,sparse,true);exercise(pi,partial,true);exercise(pi,{},true);exercise(pi,full,false);
        }
      }
    }
    check(atlas_picks>=8U);
    std::cout<<"{\"checks\":"<<checks<<",\"streams\":"<<streams<<",\"pick_visits\":"<<picks<<",\"runs\":"<<runs<<",\"atlas_pick_visits\":"<<atlas_picks<<"}\n";
}
'''

if __name__ == '__main__':
    main()
