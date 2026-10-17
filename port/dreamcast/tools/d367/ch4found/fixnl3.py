import sys
# fixnl3.py <file> <marker>: join a string literal split by a raw newline (heredoc backslash trap) back into "\n".
p, mark = sys.argv[1], sys.argv[2]
BS = chr(92)
L = open(p).read().split('\n'); out = []; i = 0; n = 0
while i < len(L):
    l = L[i]
    if mark in l and l.count('"') % 2 == 1 and i + 1 < len(L) and L[i + 1].startswith('"'):
        out.append(l + BS + 'n' + L[i + 1]); i += 2; n += 1; continue
    out.append(l); i += 1
open(p, 'w').write('\n'.join(out)); print(p, n)
