#!/usr/bin/env python3
"""Prepares host copies of the game sources for the helper build (the game tree is not edited).

  prepare.py motion <src/game/motion.cpp> <out.cpp>   (also src/game/ik.cpp)
      copy with the PowerPC register pins removed (`register T x asm("r0")` -> `register T x`; the
      empty `asm("" : ...)` statements are valid GCC asm on any target and stay) and the pointer
      casts through `u32` widened to `uintptr_t` (the game runs on 32-bit PowerPC where u32 holds a
      pointer; on the 64-bit host it would truncate), and the MOT_HIST byte-offset macro turned
      into the member access it stands for.
  prepare.py extract <src/game/math_sub.cpp> <out.cpp> NAME...
      the named top-level functions (also `Class::method`, also from the SDK .c files) copied
      verbatim (signature line at column 0 through the matching closing brace), with the same
      register-pin / u32-cast treatment and a leading `inline` dropped.
"""
import re
import sys


# motion.cpp addresses the root key history by its 32-bit byte offset in MotionWork
# (Key_hist at 0x08, [flip][rot/pos][axis]); the host layout has 64-bit pointers before it.
MOT_HIST_GAME = '#define MOT_HIST(w, flip, n) ((u16*) ((u8*) (w) + ((flip) * 12 + 8 + (n) * 6)))'
MOT_HIST_HOST = '#define MOT_HIST(w, flip, n) ((w)->Key_hist[flip][n])'


def host_text(text):
    text = re.sub(r'\s*asm\("f?r\d+"\)', '', text)
    text = text.replace(MOT_HIST_GAME, MOT_HIST_HOST)
    # The target's size_t is 32-bit; the host libc declaration is pointer-sized.
    text = text.replace('extern "C" void* memset(void* dst, int c, unsigned int n);',
                        'extern "C" void* memset(void* dst, int c, size_t n);')
    return text.replace('(u32)', '(uintptr_t)')


def motion(src, dst):
    with open(dst, 'w') as f:
        f.write(f'#line 1 "{src}"\n')
        f.write(host_text(open(src).read()))


def extract(src, dst, names):
    with open(src) as source:
        lines = source.read().split('\n')
    # Count source braces, not braces in comments/strings. Each conditional arm
    # starts at the same depth: e.g. two alternative `if (...) {` lines before
    # one shared body must not be counted as two nested scopes.
    tokens = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
    lexical = tokens.sub(lambda m: '\n' * m.group(0).count('\n'), '\n'.join(lines)).split('\n')
    out = [f'#include "re4_host_stub.h"', '']
    for name in names:
        start = None
        for i, line in enumerate(lines):
            if re.match(r'^[A-Za-z_][\w\s\*&:]*\b' + re.escape(name) + r'\(', line) and not line.rstrip().endswith(';'):
                start = i
                break
        if start is None:
            sys.exit(f'{src}: function {name} not found')
        depth = 0
        end = None
        opened = False
        conditional = []
        for i in range(start, len(lines)):
            line = lexical[i]
            directive = re.match(r'^\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b', line)
            if directive:
                op = directive.group(1)
                if op in ('if', 'ifdef', 'ifndef'):
                    conditional.append([depth, [], False])
                elif op in ('elif', 'else'):
                    if not conditional:
                        sys.exit(f'{src}:{i+1}: unmatched #{op} in {name}')
                    frame = conditional[-1]
                    frame[1].append(depth)
                    frame[2] |= op == 'else'
                    depth = frame[0]
                else:
                    if not conditional:
                        sys.exit(f'{src}:{i+1}: unmatched #endif in {name}')
                    base, branches, has_else = conditional.pop()
                    branches.append(depth)
                    if not has_else:
                        branches.append(base)
                    if len(set(branches)) != 1:
                        sys.exit(f'{src}:{i+1}: inconsistent conditional scopes in {name}')
                    depth = branches[0]
                continue
            if line.lstrip().startswith('#'):
                continue
            opened |= '{' in line
            depth += line.count('{') - line.count('}')
            if depth == 0 and opened and not conditional:
                end = i
                break
        if end is None:
            sys.exit(f'{src}: unterminated function {name}')
        out.append(f'#line {start + 1} "{src}"')
        body = lines[start:end + 1]
        body[0] = re.sub(r'^inline ', '', body[0])   # defined in one TU, called from others
        out.append(host_text('\n'.join(body)))
        out.append('')
    with open(dst, 'w') as f:
        f.write('\n'.join(out))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'motion':
        motion(sys.argv[2], sys.argv[3])
    elif cmd == 'extract':
        extract(sys.argv[2], sys.argv[3], sys.argv[4:])
    else:
        sys.exit(__doc__)
