#!/usr/bin/env python3
"""pak_chain.py <out root> <first base tex.pak> <set>=<set store dir> ...   (lane compose-test24, 2026-10-24)

Re-derives a chain of tex.pak data sets, each on the previous output. Every set's own pak-derived.json names the pack
it was built on (base) and its result (out); its delta is the keys it added (pack_add.py: kept when the running pack
lacks them) and the keys whose bytes it changed (replace tools: ps2_hud_pak / fx_cross_room / ps2_tpl_pak /
build_leonhair24 / build_leonatl24, which re-make a key's package from its own sources, independent of other keys).
Applying that delta to the running pack is what re-running the set's tool with --pak <running pack> produces.
Refuses a key two sets both change (or add with different bytes), and a set whose recorded base/out do not match its
files. Writes <out root>/<set>/dc/tex.pak + pak-derived.json (base = previous out) and SHA256SUMS."""
import hashlib, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import tex_merge, texpack  # noqa: E402

sha = lambda b: hashlib.sha256(b).hexdigest()


def main():
    root, base_path, *sets = sys.argv[1:]
    running = tex_merge.read(base_path)
    prev = sha(open(base_path, 'rb').read())
    owner = {}
    sums = []
    for spec in sets:
        name, d = spec.split('=', 1)
        pd = json.load(open(d + '/pak-derived.json'))
        own = open(d + '/dc/tex.pak', 'rb').read()
        assert sha(own) == pd['out'], '%s: tex.pak is not its pak-derived out' % name
        outp = tex_merge.read(d + '/dc/tex.pak')
        basep = BASES[pd['base']]
        added = [k for k in outp if k not in basep]
        changed = [k for k in outp if k in basep and outp[k] != basep[k]]
        removed = [k for k in basep if k not in outp]
        assert not removed, '%s removes %d keys' % (name, len(removed))
        for k in changed:
            if running[k] != basep[k]:
                raise SystemExit('%s: key %08x-%08x changed by %s too' % (name, k[0], k[1], owner.get(k)))
            running[k] = outp[k]; owner[k] = name
        for k in added:
            if k in running and running[k] != outp[k]:
                raise SystemExit('%s: added key %08x-%08x clashes with %s' % (name, k[0], k[1], owner.get(k)))
            running[k] = outp[k]; owner.setdefault(k, name)
        blob, count = texpack.build(running)
        texpack.verify(blob)
        o = os.path.join(root, name, 'dc'); os.makedirs(o, exist_ok=True)
        open(o + '/tex.pak', 'wb').write(blob)
        out = sha(blob)
        BASES[out] = dict(running)
        fmt = lambda ks: sorted('%08x-%08x' % k for k in ks)
        json.dump(dict(base=prev, out=out, count=count, added=fmt(added), changed=fmt(changed),
                       source_set=d, source_base=pd['base'], source_out=pd['out']),
                  open(os.path.join(root, name, 'pak-derived.json'), 'w'), indent=1)
        print('%-11s base %s +%d ~%d -> %s (%d keys)%s' % (name, prev[:8], len(added), len(changed), out[:8], count,
              '  (unchanged: same as the store)' if out == pd['out'] else ''))
        sums.append('%s  %s/dc/tex.pak' % (out, name))
        prev = out
    open(os.path.join(root, 'SHA256SUMS'), 'w').write('\n'.join(sums) + '\n')


BASES = {}
if __name__ == '__main__':
    # every pack a set may name as its base: the stores' own packs (keyed by sha256)
    for p in os.environ['PAK_BASES'].split(':'):
        BASES[sha(open(p, 'rb').read())] = tex_merge.read(p)
    main()
