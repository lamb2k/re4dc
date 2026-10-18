"""Rebuild cx_room_fixtures.py from the 10-13 Codex rollout (cx-14 write + Replace patches 16 23 27 32 55 60 75)."""
import re, sys

BT = chr(96)


def ps_str(s, i):
    """Parse a PS string literal at s[i]; return (value, next_index)."""
    q = s[i]
    if q == "'":
        out = []
        j = i + 1
        while True:
            if s[j] == "'":
                if j + 1 < len(s) and s[j + 1] == "'":
                    out.append("'"); j += 2; continue
                return ''.join(out), j + 1
            out.append(s[j]); j += 1
    if q == '"':
        out = []
        j = i + 1
        esc = {'n': '\n', 't': '\t', 'r': '\r', '"': '"', BT: BT, '$': '$', '0': '\0'}
        while True:
            ch = s[j]
            if ch == BT:
                out.append(esc.get(s[j + 1], s[j + 1])); j += 2; continue
            if ch == '"':
                if s[j + 1] == '"':
                    out.append('"'); j += 2; continue
                return ''.join(out), j + 1
            if ch == '$':
                raise ValueError('interpolation at %d: %r' % (j, s[j:j + 30]))
            out.append(ch); j += 1
    raise ValueError('not a string at %d: %r' % (i, s[i:i + 20]))


def here(s, name):
    m = re.search(r'\$' + name + r"=@'\n(.*?)\n'@", s, re.S)
    return m.group(1)


def expr(s, i, env):
    """string expression: literal, $var, [Environment]::NewLine, joined by +"""
    parts = []
    while True:
        while s[i] == " ": i += 1
        if s.startswith('[Environment]::NewLine', i):
            parts.append('\r\n'); i += len('[Environment]::NewLine')
        elif s[i] == '$':
            m = re.match(r'\$(\w+)', s[i:]); parts.append(env[m.group(1)]); i += len(m.group(0))
        else:
            v, i = ps_str(s, i); parts.append(v)
        while s[i] == ' ': i += 1
        if s[i] == '+':
            i += 1; continue
        return ''.join(parts), i


def apply(src, cmd):
    env = {}
    for name in ('old', 'new'):
        if '$' + name + "=@'" in cmd:
            env[name] = here(cmd, name)
    n = 0
    for m in re.finditer(r'\.Replace\(', cmd):
        i = m.end()
        a, i = expr(cmd, i, env)
        assert cmd[i] == ',', cmd[i:i + 20]
        b, i = expr(cmd, i + 1, env)
        assert cmd[i] == ')', cmd[i:i + 20]
        if a not in src:
            print('  ANCHOR MISSING:', repr(a[:70]))
        src = src.replace(a, b); n += 1
    return src, n


