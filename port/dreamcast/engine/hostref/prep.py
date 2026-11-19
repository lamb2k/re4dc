#!/usr/bin/env python3
"""Host copies of original game sources for the hostref build (the game tree is never edited).

  prep.py copy <src.cpp> <out.cpp>
      The file as it is, with the empty scheduling-barrier asm statements' float operands moved from the
      PowerPC/SH-4 "f" register class to SSE ("x"): `asm("" : "+f"(z))` names an x87 stack register on
      x86, which GCC rejects. The statements emit no code on any target, so the arithmetic is unchanged.
  prep.py rnd <src/game/rnd.cpp> <out.cpp>
      copy, plus instrumentation that changes no result: Rnd() counts its calls (host_rnd_calls) and
      host_rnd_state() reads the generator, for the trace's generator fields.
  prep.py extract <src.cpp> <out.cpp> NAME...
      The file's preamble (everything above its first function definition: includes, file-scope tables
      and globals) followed by the named functions (`Class::method` or plain names, every overload)
      copied verbatim, signature line through the matching closing brace. Used where a file's other
      functions would pull in behaviour outside the E1 closure (em.cpp: the enemy and object classes
      behind cEmMgr::construct).
"""
import re
import sys


def host_text(text):
    return re.sub(r'"([+=]?)f"\(', r'"\1x"(', text)


def copy(src, dst):
    text = open(src).read()
    with open(dst, 'w') as f:
        f.write(f'#line 1 "{src}"\n')
        f.write(host_text(text))


def rnd(src, dst):
    text = host_text(open(src).read())
    head = 'u8 Rnd()\n{\n'
    if head not in text:
        sys.exit(f'{src}: Rnd() not found')
    text = text.replace(head, head + '    ++host_rnd_calls;\n', 1)
    with open(dst, 'w') as f:
        f.write('extern unsigned host_rnd_calls;\n')
        f.write(f'#line 1 "{src}"\n')
        f.write(text)
        f.write('\nextern "C" unsigned short host_rnd_state(void) { return Random; }\n')


def code_part(line):
    return line.split('//')[0].rstrip()


def is_def_start(line):
    # A function definition starts at column 0 with `name(` or `Type name(` and does not end in ';'.
    code = code_part(line)
    if code.startswith(('#', 'extern', 'typedef', 'static const', ' ', '\t')):
        return False
    m = re.match(r'^[A-Za-z_][\w\s\*&:<>,]*\b[\w:~]+\(', code)
    return m is not None and not code.endswith(';') and '=' not in code.split('(')[0]


def body_end(lines, start, name):
    depth = 0
    seen = False
    for i in range(start, len(lines)):
        depth += lines[i].count('{') - lines[i].count('}')
        seen = seen or '{' in lines[i]
        if seen and depth == 0:
            return i
    sys.exit(f'unterminated {name}')


def extract(src, dst, names):
    lines = open(src).read().split('\n')
    first_def = None
    depth = 0
    pp = 0
    for i, line in enumerate(lines):
        # only at file scope: outside extern "C" { ... } blocks and tables, and outside #if blocks
        if depth == 0 and pp == 0 and is_def_start(line):
            first_def = i
            break
        code = code_part(line)
        s = code.lstrip()
        if s.startswith('#if'):
            pp += 1
        elif s.startswith('#endif'):
            pp -= 1
        elif not s.startswith('#'):
            depth += code.count('{') - code.count('}')
    if first_def is None:
        sys.exit(f'{src}: no function definition found')
    out = [f'#line 1 "{src}"', host_text('\n'.join(lines[:first_def])), '']
    for name in names:
        pat = re.compile(r'^(?:[A-Za-z_][\w\s\*&:<>,]*?\s|[A-Za-z_][\w\s\*&:<>,]*?[\*&])?' + re.escape(name) + r'\(')
        starts = [i for i, line in enumerate(lines)
                  if i >= first_def and pat.match(line) and not code_part(line).endswith(';')]
        if not starts:
            sys.exit(f'{src}: function {name} not found')
        for start in starts:   # every overload
            end = body_end(lines, start, name)
            out.append(f'#line {start + 1} "{src}"')
            out.append(host_text('\n'.join(lines[start:end + 1])))
            out.append('')
    with open(dst, 'w') as f:
        f.write('\n'.join(out) + '\n')


if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    if sys.argv[1] == 'copy':
        copy(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'rnd':
        rnd(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'extract':
        extract(sys.argv[2], sys.argv[3], sys.argv[4:])
    else:
        sys.exit(__doc__)
