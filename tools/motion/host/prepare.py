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
    return text.replace('(u32)', '(uintptr_t)')


def motion(src, dst):
    with open(dst, 'w') as f:
        f.write(f'#line 1 "{src}"\n')
        f.write(host_text(open(src).read()))


def function_end(lines, start, label):
    """Match all conditional arms, retaining the original preprocessor text.

    Alternative arms may each open the same block that closes after #endif.
    Their depths must agree; selecting a guessed macro configuration would
    hide malformed or incomplete source. Comments and quoted braces are not
    C++ blocks. This changes extraction boundaries only, never source text.
    """
    tokens = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
    clean = tokens.sub(lambda m: '\n' * m.group().count('\n'), '\n'.join(lines)).split('\n')
    depth, opened, branches = 0, False, []
    for i in range(start, len(lines)):
        text = clean[i]
        directive = re.match(r'^\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b', text)
        if directive:
            kind = directive.group(1)
            if kind in ('if', 'ifdef', 'ifndef'):
                branches.append([depth, [], False])
            elif not branches:
                raise ValueError(f'{label}: unmatched #{kind} at line {i + 1}')
            elif kind in ('else', 'elif'):
                branch = branches[-1]
                if branch[2]:
                    raise ValueError(f'{label}: #{kind} after #else at line {i + 1}')
                branch[1].append(depth)
                depth = branch[0]
                branch[2] = kind == 'else'
            else:
                entry, ends, had_else = branches.pop()
                ends.append(depth)
                if not had_else:
                    ends.append(entry)
                if len(set(ends)) != 1:
                    raise ValueError(f'{label}: conditional brace depths disagree at line {i + 1}')
                depth = ends[0]
        else:
            opened |= '{' in text
            depth += text.count('{') - text.count('}')
            if depth < 0:
                raise ValueError(f'{label}: unmatched closing brace at line {i + 1}')
        if opened and depth == 0 and not branches:
            return i
    raise ValueError(f'{label}: incomplete function or conditional block')


def extract(src, dst, names):
    with open(src, encoding='utf-8') as source:
        lines = source.read().split('\n')
    out = [f'#include "re4_host_stub.h"', '']
    for name in names:
        start = None
        for i, line in enumerate(lines):
            if re.match(r'^[A-Za-z_][\w\s\*&:]*\b' + re.escape(name) + r'\(', line) and not line.rstrip().endswith(';'):
                start = i
                break
        if start is None:
            sys.exit(f'{src}: function {name} not found')
        end = function_end(lines, start, f'{src}: function {name}')
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
