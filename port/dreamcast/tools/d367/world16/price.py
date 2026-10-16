import sys, json, os
mode, out, rooms = sys.argv[1], sys.argv[2], sys.argv[3]
RB = r'C:\Game Dev\Emulators\room-budget-20261015'
sys.path.insert(0, RB)
import roomproj as R
P = os.environ.get('W16P', r'C:\Game Dev\Emulators\re4-assets-private\world16-ch1-20261016')
src = json.load(open(os.path.join(P, 'sources.json')))['rooms']
def wpath(p):
    if p.startswith('/root/'):
        return r'\\wsl.localhost\Ubuntu-24.04' + p.replace('/', '\\')
    return R.hp(p)
def load_room(room, rep):
    if mode == 'cur':
        m = wpath(src[room]['ps2-world.re4mesh']['path']); pw = wpath(src[room]['ps2-world.r4pw']['path'])
    else:
        d = os.path.join(P, room); m = os.path.join(d, 'ps2-wv5.re4mesh')
        if not os.path.exists(m): m = os.path.join(d, 'ps2-world.re4mesh')
        pw = os.path.join(d, 'ps2-world.r4pw')
    return R.Pkg(m, pw), m
R.load_room = load_room
sys.argv = [sys.argv[0], out, rooms]
R.main()
