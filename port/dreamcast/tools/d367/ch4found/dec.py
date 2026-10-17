import re, sys, glob, os
H = r'C:\Flycast-Evidence\re4-dreamcast\ch4found-20261016/' + sys.argv[1]
suf = sys.argv[2]
for d in sorted(glob.glob(H + r'\scenarios\cx-r*-walk-' + suf)):
    room = os.path.basename(d).split('-')[1]
    if len(sys.argv) > 3 and room not in sys.argv[3:]: continue
    try: L = open(d + r'\capture\run-output.txt', 'rb').read().decode('latin1').splitlines()
    except Exception: print(room, 'no log'); continue
    def c(p): return sum(1 for l in L if re.search(p, l))
    print('==', room, 'lines', len(L), 'kills', c(r'warp: kill 0x.. hp<=0'), 'fired', c(r'kill 0x.. fired'),
          'hold', c(r'alivecap: hold'), 'defer', c(r'alivecap: defer'), 'release', c(r'alivecap: release'), 'park', c(r'alivecap: park'),
          'destroy', c(r'alivecap: destroy|far delete drops'), 'fatal', c(r'FAULT|HALT|OSPanic|RE4DC MISSING'))
    for l in L:
        if re.search(r'ps2en:|alivecap: peak|warp: alive |goto \d+ at|room enter|RsfSet|clear|SceExit|kill repeat 0', l):
            print('   ', l.strip()[:200])
