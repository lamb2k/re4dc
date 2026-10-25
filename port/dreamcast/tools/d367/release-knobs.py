#!/usr/bin/env python3
"""release-knobs.py: the public contributor kit's view of a test release recipe (stdlib only).

The release recipe (tools/d367/<test>/<t>-build.sh, arm tP) builds the play program through route/route-build.sh,
which writes every make knob it passed to build-r21.sh into out-<label>/candidate.txt. That list, with the private
directories replaced by their place in the Build-Assets zip, is the release's knob file
tools/d367/<test>/release-knobs.txt, and build-public.sh builds from it. Nothing is typed twice.

  write  <candidate.txt> <release-knobs.txt> --test N --tag TAG --source SHA --recipe PATH
         [--image-sha256 HEX] [--assets-zip NAME] [--disc-sets NAMES]
         Writes the knob file (one knob per line, after '# key: value' header lines).
  check  <candidate.txt> <release-knobs.txt>
         Exit 1 unless the knob file holds exactly the recipe's knobs (order kept: make takes the last value).
  args   <release-knobs.txt> <assets dir>
         Prints the knobs for build-public.sh, @ASSETS@ replaced by <assets dir>.
  zip    <candidate.txt> <out zip> [--bundle DIR] [--disc-sets NAMES]
         Writes the Build-Assets zip from the directories the recipe compiled in (deterministic: fixed dates).
  zipcheck <candidate.txt> <zip> [--bundle DIR] [--objdir DIR] [--disc-sets NAMES]
         Exit 1 unless the zip holds exactly those directories' files, byte for byte, and (with --objdir, the
         release build's objdir) every private file the release build's .d files name.
  doclint <release-knobs.txt> <doc>...
         Exit 1 if a contributor doc names an older test ("test 7", "test-c29c4bf5-...") than the knob file's.

Private directories: the recipe's ASSETS (route-build.sh's play actor bundle, --bundle) -> re4dc-assets/,
PS2_LEON_DIR -> re4dc-assets/ps2leon/, PS2_GANADO_DIR -> re4dc-assets/ps2ganado/, PS2_ENEMY_CH22_DIR and
PS2_ENEMY_CH23_DIR (test 17 on: the chapter 2-2 / 2-3 PS2 enemy rows, ps2_enemy_ch22_data.inc /
ps2_enemy_ch23_data.inc, compiled into the program) -> re4dc-assets/ps2enemych2/ (both knobs name one directory; two
different directories for one zip place are an error), ACTOR_GANADO_PS2_STUMP_DIR (test 17 on: the stump / hand-pose
package's layout header ganado_ps2_stump_runtime.h; the package itself is disc data set stump17) -> re4dc-assets/ps2stump/, LEON_HEADLESS_DIR (test 18 on: ps2leon_neck.h; the head archives are disc data set
garr18h) -> re4dc-assets/ps2leonhead/. Private files: GANADO_LOD_PACK
-> re4dc-assets/glod/<name> (the knob file names it kit-relative, @ASSETS@/glod/<name>). Any other knob whose value is
an absolute path outside the tree is an error: a new private input must get a place in the zip (and a line in
build-public.sh's PRIVATE_OFF) before the release can publish.
Disc data (--disc-sets, test 15 on): the files of the named data sets of test11/t11-fix.py (disc path -> source; a
later set replaces an earlier one's file at the same disc path, as on the disc) -> re4dc-assets/disc/<disc path>.
With a DROP_LOOSE set (pak17, test 17 on) no loose dc/tex/<c>/<key>.re4tex is on the disc, so none goes in the zip.
They are on the release disc already; the zip carries them for contributors who build their own disc. The knob file
records the set list ('# disc-sets:'), and kit-check.sh passes it to zipcheck.
"""
import argparse, hashlib, importlib.util, re, sys, zipfile
from pathlib import Path

BUNDLE = '/root/probe/lanes/play-actor-bundle'
PRIVATE = {'PS2_LEON_DIR': 'ps2leon', 'PS2_GANADO_DIR': 'ps2ganado',
           'PS2_ENEMY_CH22_DIR': 'ps2enemych2', 'PS2_ENEMY_CH23_DIR': 'ps2enemych2',
           'ACTOR_GANADO_PS2_STUMP_DIR': 'ps2stump', 'LEON_HEADLESS_DIR': 'ps2leonhead'}
PRIVATE_FILES = {'GANADO_LOD_PACK': 'glod'}
FIX_TOOL = Path(__file__).resolve().parent / 'test11' / 't11-fix.py'
ZIP_ROOT = 're4dc-assets'
DATE = (2026, 10, 12, 0, 0, 0)


def die(msg):
    sys.exit('release-knobs: ' + msg)


def candidate_knobs(path):
    toks = Path(path).read_text().split()
    bad = [t for t in toks if not re.match(r'^[A-Z][A-Z0-9_]*=', t)]
    if bad:
        die('%s: not a knob: %s' % (path, ' '.join(bad[:5])))
    return toks


def sanitize(knobs):
    out = []
    for kv in knobs:
        k, v = kv.split('=', 1)
        if k in PRIVATE:
            out.append('%s=@ASSETS@/%s' % (k, PRIVATE[k]))
        elif k in PRIVATE_FILES:
            out.append('%s=@ASSETS@/%s/%s' % (k, PRIVATE_FILES[k], Path(v).name))
        elif v.startswith('/'):
            die('%s names a private path (%s): give it a place in the Build-Assets zip and in build-public.sh' % (k, v))
        else:
            out.append(kv)
    return out


def read_file(path):
    head, knobs = {}, []
    for line in Path(path).read_text().splitlines():
        m = re.match(r'^# ([a-z0-9_-]+): (.*)$', line)
        if m:
            head[m.group(1)] = m.group(2).strip()
        elif line.strip() and not line.startswith('#'):
            knobs.append(line.strip())
    return head, knobs


def private_dirs(knobs, bundle):
    dirs = [(ZIP_ROOT, Path(bundle))]
    seen = {}
    for kv in knobs:
        k, v = kv.split('=', 1)
        if k in PRIVATE:
            pre = '%s/%s' % (ZIP_ROOT, PRIVATE[k])
            # a repeated knob keeps only its last value (make takes the last one)
            seen[pre] = {x for x in seen.get(pre, set()) if x[0] != k} | {(k, Path(v).resolve())}
            dirs = [d for d in dirs if d[0] != pre]
            dirs.append((pre, Path(v)))
    for pre, kd in seen.items():
        if len({d for _, d in kd}) > 1:  # PS2_ENEMY_CH22_DIR / _CH23_DIR share ps2enemych2/: one directory only
            die('%s would hold two directories: %s' % (pre, ', '.join('%s=%s' % x for x in sorted(kd))))
    return dirs


def disc_files(sets):
    """{zip name: source} for the named t11-fix.py data sets, in order (a later set's file wins, as on the disc)."""
    names = [s for s in (sets or '').replace(',', ' ').split() if s]
    if not names:
        return {}
    spec = importlib.util.spec_from_file_location('t11fix', str(FIX_TOOL))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = {}
    for n in names:
        if n not in mod.DATA:
            die('disc set %s is not in %s' % (n, FIX_TOOL))
        for dest, src in mod.DATA[n].items():
            if dest == 'tex':
                die('disc set %s stages loose textures (tex): not supported in the Build-Assets zip' % n)
            if dest == 'ovl':
                continue  # overlay names (ch2: em3b em35 pl14): built by the recipe, not data; the program zip has them
            out['%s/disc/%s' % (ZIP_ROOT, dest)] = Path(src)
    # a set with DROP_LOOSE (pak17, test 17 on) leaves no loose dc/tex/<c>/<key>.re4tex on the disc (the pack holds
    # them all): the zip carries what the disc carries, so the earlier sets' loose textures stay out
    if any(n in getattr(mod, 'DROP_LOOSE', {}) for n in names):
        pre = '%s/disc/' % ZIP_ROOT
        out = {k: v for k, v in out.items() if not mod.LOOSE.match(k[len(pre):])}
    for name, f in out.items():
        if not f.is_file():
            die('disc data file %s (%s) is missing' % (f, name))
    return out


def expected_files(knobs, bundle, disc_sets=None):
    files = {}
    for pre, d in private_dirs(knobs, bundle):
        if not d.is_dir():
            die('private directory %s is missing' % d)
        for f in sorted(p for p in d.resolve().iterdir() if p.is_file()):
            files['%s/%s' % (pre, f.name)] = f
    for kv in knobs:
        k, v = kv.split('=', 1)
        if k in PRIVATE_FILES:
            if not Path(v).is_file():
                die('private file %s=%s is missing' % (k, v))
            files['%s/%s/%s' % (ZIP_ROOT, PRIVATE_FILES[k], Path(v).name)] = Path(v)
    files.update(disc_files(disc_sets))
    return files


def cmd_write(a):
    knobs = sanitize(candidate_knobs(a.candidate))
    head = [('test', a.test), ('tag', a.tag), ('source', a.source), ('recipe', a.recipe)]
    if a.image_sha256:
        head.append(('image-sha256', a.image_sha256))
    if a.assets_zip:
        head.append(('assets-zip', a.assets_zip))
    if a.disc_sets:
        disc_files(a.disc_sets)  # every file must exist
        head.append(('disc-sets', ','.join(a.disc_sets.replace(',', ' ').split())))
    lines = ['# RE4DC release knobs: the make knobs of the test release play program, in the order the recipe passes',
             '# them (make takes the last value). Written by tools/d367/release-knobs.py write from the release build\'s',
             '# out-<label>/candidate.txt; checked by tools/d367/kit-check.sh; read by build-public.sh. Do not edit.',
             '# @ASSETS@ = the unpacked Build-Assets zip (re4dc-assets/).']
    lines += ['# %s: %s' % kv for kv in head]
    Path(a.out).write_text('\n'.join(lines + knobs) + '\n')
    print('release-knobs: wrote %s (%d knobs)' % (a.out, len(knobs)))


def cmd_check(a):
    want = sanitize(candidate_knobs(a.candidate))
    _, have = read_file(a.knobs)
    if want == have:
        print('release-knobs: %s matches %s (%d knobs)' % (a.knobs, a.candidate, len(have)))
        return
    import difflib
    sys.stdout.writelines(difflib.unified_diff([k + '\n' for k in have], [k + '\n' for k in want],
                                               a.knobs, a.candidate))
    die('the knob file differs from the recipe: rerun release-knobs.py write')


def cmd_args(a):
    _, knobs = read_file(a.knobs)
    print(' '.join(k.replace('@ASSETS@', a.assets) for k in knobs))


def cmd_zip(a):
    files = expected_files(candidate_knobs(a.candidate), a.bundle, a.disc_sets)
    sums = []
    with zipfile.ZipFile(a.out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, f in files.items():
            data = f.read_bytes()
            zi = zipfile.ZipInfo(name, date_time=DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)
            sums.append('%s  %s' % (hashlib.sha256(data).hexdigest(), name))
        z.writestr(zipfile.ZipInfo('%s/SHA256SUMS.assets' % ZIP_ROOT, date_time=DATE), '\n'.join(sums) + '\n')
    with zipfile.ZipFile(a.out) as z:
        assert z.testzip() is None and all('\\' not in n for n in z.namelist())
        print('release-knobs: %s %d entries' % (a.out, len(z.namelist())))


def cmd_zipcheck(a):
    knobs = candidate_knobs(a.candidate)
    files = expected_files(knobs, a.bundle, a.disc_sets)
    bad = []
    with zipfile.ZipFile(a.zip) as z:
        names = {n for n in z.namelist() if not n.endswith('/')} - {'%s/SHA256SUMS.assets' % ZIP_ROOT}
        for n in sorted(set(files) - names):
            bad.append('missing from zip: ' + n)
        for n in sorted(names - set(files)):
            bad.append('in zip, not in the recipe directories: ' + n)
        for n in sorted(names & set(files)):
            if z.read(n) != files[n].read_bytes():
                bad.append('differs: %s vs %s' % (n, files[n]))
    if a.objdir:
        roots = [(pre, str(d)) for pre, d in private_dirs(knobs, a.bundle)]
        roots += [(pre, str(d.resolve())) for pre, d in private_dirs(knobs, a.bundle)]
        deps = set()
        for d in Path(a.objdir).rglob('*.d'):
            for tok in d.read_text(errors='replace').replace('\\\n', ' ').split():
                tok = tok.rstrip(':')
                for pre, root in roots:
                    if tok.startswith(root.rstrip('/') + '/'):
                        deps.add('%s/%s' % (pre, tok[len(root.rstrip('/')) + 1:]))
        missing = sorted(deps - set(files))
        bad += ['the release build read %s, not in the zip' % n for n in missing]
        if not missing:
            print('release-knobs: the release build read %d private files, all in the zip' % len(deps))
    if bad:
        print('\n'.join(bad))
        die('%s does not match the recipe (%d problems): rebuild it with release-knobs.py zip' % (a.zip, len(bad)))
    print('release-knobs: %s matches the recipe directories (%d files)' % (a.zip, len(files)))


def cmd_doclint(a):
    head, _ = read_file(a.knobs)
    cur = float(head.get('test', '0'))
    tag = head.get('tag', '')
    bad = []
    for doc in a.docs:
        for i, line in enumerate(Path(doc).read_text().splitlines(), 1):
            for m in re.finditer(r'(?<![/\w-])[Tt]est ?(\d+(?:\.\d+)?)\b', line):   # not a path (tools/d367/test15/)
                if float(m.group(1)) < cur and int(float(m.group(1))) != int(cur):   # a hotfix (16.1) keeps its base (16)
                    bad.append('%s:%d: names test %s (current %s): %s' % (doc, i, m.group(1), head['test'], line.strip()))
            for m in re.finditer(r'\btest-[0-9a-f]{8}-\d{8}\b', line):
                if m.group(0) != tag:
                    bad.append('%s:%d: names release %s (current %s): %s' % (doc, i, m.group(0), tag, line.strip()))
            for m in re.finditer(r'RE4DC-Console-Test-([0-9a-f]{8})-', line):
                if m.group(1) != head.get('source', '')[:8]:
                    bad.append('%s:%d: names release zip of %s (current %s): %s' % (doc, i, m.group(1), head.get('source'), line.strip()))
    if bad:
        print('\n'.join(bad))
        die('%d stale release names in the contributor docs' % len(bad))
    print('release-knobs: contributor docs name no release older than test %s' % head.get('test'))


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    s = p.add_subparsers(dest='cmd', required=True)
    w = s.add_parser('write'); w.add_argument('candidate'); w.add_argument('out')
    for k in ('--test', '--tag', '--source', '--recipe'):
        w.add_argument(k, required=True)
    w.add_argument('--image-sha256'); w.add_argument('--assets-zip'); w.add_argument('--disc-sets')
    c = s.add_parser('check'); c.add_argument('candidate'); c.add_argument('knobs')
    r = s.add_parser('args'); r.add_argument('knobs'); r.add_argument('assets')
    z = s.add_parser('zip'); z.add_argument('candidate'); z.add_argument('out'); z.add_argument('--bundle', default=BUNDLE)
    z.add_argument('--disc-sets')
    zc = s.add_parser('zipcheck'); zc.add_argument('candidate'); zc.add_argument('zip')
    zc.add_argument('--bundle', default=BUNDLE); zc.add_argument('--objdir'); zc.add_argument('--disc-sets')
    d = s.add_parser('doclint'); d.add_argument('knobs'); d.add_argument('docs', nargs='+')
    a = p.parse_args()
    {'write': cmd_write, 'check': cmd_check, 'args': cmd_args, 'zip': cmd_zip, 'zipcheck': cmd_zipcheck,
     'doclint': cmd_doclint}[a.cmd](a)


if __name__ == '__main__':
    main()
