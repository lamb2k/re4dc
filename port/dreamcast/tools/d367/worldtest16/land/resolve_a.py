import re
R = '/root/probe/worldtest16-20261016/landA/port/dreamcast/'


def resolve(path, fn):
    s = open(path, encoding='utf-8').read()
    pat = re.compile(r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> origin/t15/int\n', re.S)
    s2, n = pat.subn(lambda m: fn(m.group(1), m.group(2)), s)
    assert '<<<<<<<' not in s2 and n > 0
    open(path, 'w', encoding='utf-8').write(s2)
    print(path, n)


resolve(R + 'tools/d367/test11/t11-fix.py', lambda ours, theirs: theirs.replace(',wv32r101,fsh', ',wt16r101,fsh'))


def ki(ours, theirs):
    if 'Known, not yet worked on' in theirs:
        t = theirs.replace('the problem was not console-only | 22 |', 'the problem was not console-only | 23 |')
        return t.replace('Known, not yet worked on | 11 |', 'Known, not yet worked on | 12 |')
    # rows: theirs' Foliage row (fixed in 16), then our two r101 rows
    return theirs + ''.join(l + '\n' for l in ours.splitlines() if l.startswith('| In the village (r101)'))


resolve(R + 'docs/KNOWN_ISSUES.md', ki)
