#!/usr/bin/env python3
"""Exercise the actual 792 candidate certificate helper on all sealed worlds."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

HERE = Path(__file__).resolve().parent
DRIVER = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <vector>
#include "world_rect_provenance.h"
int main() {
    unsigned p[8]{};
    assert(std::fread(p,4,8,stdin)==8);
    std::vector<unsigned char>b(p[1]);
    assert(std::fread(b.data(),1,b.size(),stdin)==b.size());
    auto value=re4dc::rect21::provenance::policy_source_crc(p[0],b.data(),p[1],p[2],p[3],p[4],p[5]);
    assert(value==p[6]);
    assert(re4dc::rect21::provenance::policy_source_crc(p[0],nullptr,p[1],p[2],p[3],p[4],p[5])==0);
    assert(re4dc::rect21::provenance::policy_source_crc(p[0],b.data(),31,p[2],p[3],p[4],p[5])==0);
}
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--selected-receipt', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(exist_ok=False)
    receipt_data = a.selected_receipt.read_bytes()
    selected = json.loads(receipt_data)
    cpp = a.output / 'certificate.cpp'
    cpp.write_text(DRIVER)
    exe = a.output / 'certificate'
    cmd = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-fsanitize=undefined,address', '-I'+str(HERE), str(cpp), '-o', str(exe)]
    subprocess.run(cmd, check=True)
    checks = 0
    cases = []
    for room, spec in (selected['selected'] | selected['held']).items():
        original = Path(spec['absolute_path']).read_bytes()
        assert hashlib.sha256(original).hexdigest() == spec['sha256']
        actual = struct.unpack_from('<I', original, 20)[0]
        qualified = room in selected['selected']
        params = [int(room[1:], 16), len(original), spec['mesh_crc'], spec['mesh_bytes'], spec['parts'], spec['meshes']]

        def run(blob, values, expected):
            nonlocal checks
            packet = struct.pack('<8I', *values, expected, 0) + blob
            result = subprocess.run([str(exe)], input=packet, capture_output=True)
            assert result.returncode == 0, (room, checks, result.stderr.decode())
            checks += 1

        run(original, params, spec['canonical_source_crc'] if qualified else actual)
        for field in (0, 2, 3, 4, 5):
            mutated = params.copy()
            mutated[field] ^= 1
            # An exact foreign room tuple must never accidentally qualify.
            run(original, mutated, actual)
        for offset in (0, 4, 8, 12, 16, 20, 24, 28, 32, len(original)-1):
            blob = bytearray(original)
            blob[offset] ^= 1
            run(blob, params, struct.unpack_from('<I', blob, 20)[0])
        for offset in (32, len(original)-1):
            blob = bytearray(original)
            blob[offset] ^= 1
            struct.pack_into('<I', blob, 20, zlib.crc32(blob[32:]) & 0xffffffff)
            run(blob, params, struct.unpack_from('<I', blob, 20)[0])
        # Supplying fewer bytes must reject the otherwise genuine tuple safely.
        mutated = params.copy()
        mutated[1] -= 1
        run(original[:-1], mutated, actual)
        cases.append(dict(room=room, selected=qualified, world_sha256=spec['sha256']))
    result = dict(status='HOST_ACTUAL_CERTIFICATE_HELPER_ONLY_NO_TARGET_ACCEPTANCE', checks=checks,
                  null_and_short_checks=2*checks, selected=27, held=['r11f','r200'], worlds=cases,
                  selected_receipt_sha256=hashlib.sha256(receipt_data).hexdigest(), command=cmd,
                  sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'world_rect_provenance.h',HERE/'provenance_certificates.inc',Path(__file__)]})
    (a.output/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','checks','null_and_short_checks','selected','held','selected_receipt_sha256')}))


if __name__ == '__main__':
    main()
