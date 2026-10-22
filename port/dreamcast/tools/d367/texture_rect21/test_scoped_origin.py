#!/usr/bin/env python3
"""Host tests for scoped -> original policy identity (lane mipfix22).

1. scoped_origin.h (the runtime lookup, compiled with g++) maps every scoped key of
   both tables to its original and leaves unknown keys unchanged.
2. Every scoped_representations.inc key is covered by scoped_origins.inc.
3. FOLIAGE_TRIM Full / Near / Off: for each scoped key whose original is a foliage
   key, the pass and the Near distance cutoff with the lookup equal the original's
   (the policy of native_static.cpp foliage::pass_of + the foliage_near cutoff).
4. MIST_CUT: a scoped alias of a listed mist part is cut like the original.
"""
import os, re, struct, subprocess, tempfile, unittest
import scoped_origin as so

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
FOLIAGE = os.path.join(ROOT, 'game', 'platform', 'include', 'foliage_keys.inc')
MIST = [(0xe967b886, 0x9bd0a435)]


def rows(path, n):
    return [tuple(int(x, 16) for x in re.findall(r'0x([0-9a-fA-F]+)', l)[:n]) for l in open(path) if l.startswith('{')]


def foliage():
    out = {}
    for l in open(FOLIAGE):
        m = re.match(r'\{0x([0-9a-f]+)U,0x([0-9a-f]+)U,(\d)\}', l)
        if m:
            out[(int(m[1], 16), int(m[2], 16))] = int(m[3])
    return out


def pass_of(key, setting, keys, mapping):
    """foliage::pass_of for a pass-2 part without vertex alpha; returns (pass, near_cutoff)."""
    if setting == 0:
        return 2, False
    key = mapping.get(key, key)
    level = keys.get(key, 0)
    p = (3 if level else 2) if setting == 2 else (3 if level == 1 else 1 if level == 2 else 2)
    return p, p != 2 and p == 1  # foliage_near: moved out of pass 2 into the punch-through list


class T(unittest.TestCase):
    tables = [('scoped_origins.inc', 'scoped_representations.inc'), ('scoped_origins792.inc', None)]

    def maps(self):
        for inc, _ in self.tables:
            yield inc, {r[:2]: r[2:] for r in rows(os.path.join(HERE, inc), 4)}

    def test_runtime_lookup(self):
        for inc, m in self.maps():
            src = r'''#include <cstdio>
#include "scoped_origin.h"
int main(){unsigned a,b;while(std::scanf("%x %x",&a,&b)==2){std::uint32_t c=a,f=b;re4dc::rect21::origin::original(c,f);std::printf("%08x %08x\n",c,f);}}'''
            with tempfile.TemporaryDirectory() as d:
                inc_dir = os.path.join(d, 'i')
                os.mkdir(inc_dir)
                open(os.path.join(inc_dir, 'scoped_origins.inc'), 'w').write(open(os.path.join(HERE, inc)).read())
                open(os.path.join(inc_dir, 'scoped_origin.h'), 'w').write(open(os.path.join(HERE, 'scoped_origin.h')).read())
                open(os.path.join(d, 't.cpp'), 'w').write(src)
                subprocess.run(['g++', '-std=c++17', '-O2', '-I', inc_dir, '-o', os.path.join(d, 't'), os.path.join(d, 't.cpp')], check=True)
                probe = list(m) + [(0x12345678, 0x9abcdef0), (0, 0)]
                out = subprocess.run([os.path.join(d, 't')], input=''.join(f'{a:x} {b:x}\n' for a, b in probe),
                                     capture_output=True, text=True, check=True).stdout.split('\n')
                for k, line in zip(probe, out):
                    self.assertEqual(tuple(int(x, 16) for x in line.split()), m.get(k, k), inc)

    def test_cover_representations(self):
        for inc, rep in self.tables:
            if rep:
                m = {r[:2] for r in rows(os.path.join(HERE, inc), 4)}
                self.assertFalse({r[:2] for r in rows(os.path.join(HERE, rep), 2)} - m)

    def test_foliage_full_near_off(self):
        keys = foliage()
        total = 0
        for inc, m in self.maps():
            for s, o in m.items():
                if o not in keys:
                    continue
                total += 1
                for setting in (0, 1, 2):
                    self.assertEqual(pass_of(s, setting, keys, m), pass_of(o, setting, keys, {}), (inc, setting, s))
                # without the lookup the review defect reproduces: Off draws it, Near loses the cutoff
                self.assertEqual(pass_of(s, 2, keys, {}), (2, False))
        self.assertGreater(total, 0)

    def test_mist_cut(self):
        for inc, m in self.maps():
            for s, o in m.items():
                if o in MIST:
                    self.assertNotIn(s, MIST)
                    self.assertIn(m.get(s, s), MIST)

    def test_pair_rejects_geometry_change(self):
        head = b'R4PW' + struct.pack('<7I', 1, 0, 1, 1, 0, 0, 0)
        a = head + struct.pack('<2I', 1, 2) + b'\0' * 8
        self.assertEqual(so.pair_map(a, head + struct.pack('<2I', 3, 4) + b'\0' * 8), {(3, 4): {(1, 2)}})
        with self.assertRaises(ValueError):
            so.pair_map(a, head + struct.pack('<2I', 3, 4) + b'\1' + b'\0' * 7)


if __name__ == '__main__':
    unittest.main()
