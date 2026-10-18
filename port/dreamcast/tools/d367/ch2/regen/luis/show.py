"""show.py FILE FROM_TS TO_TS N [REGEX]: print calls in [FROM,TO) (first N chars of body), optional body filter."""
import re, sys
t = open(sys.argv[1], encoding='utf-8').read().split('\n##CALL ')[1:]
t.sort(key=lambda b: b[:24])
lo, hi, n = sys.argv[2], sys.argv[3], int(sys.argv[4])
rx = re.compile(sys.argv[5]) if len(sys.argv) > 5 else None
for b in t:
    if lo <= b[:24] < hi:
        body = b.split('\n', 1)[1]
        call, _, out = body.partition('\n##OUT')
        if rx and not rx.search(call):
            continue
        print('=====', b[:24])
        print(call[:n].replace('\\n', '\n').replace('\\\\', '\\'))
        print('--- out:', out[:400].replace('\\n', '\n'))
