"""ashley_rooms.py <room>... (WSL; lane ps2cast 2026-10-15, PS2_ASHLEY, offline): Ashley's chapter 2 room packages.
Copies ashley_package.sh's r117 cast (<A>/regcast-ashley11) to <A>/regcast-ashley-ch2 with the chapter 2 rooms added to
every room list, and writes model-registry/ps2-ashley-r<room>.json per room (the r117 spec, same three descriptors). Then:
  model_registry.py model-registry/ps2-ashley-r<room>.json <W>/reg-r<room> --tree <T> --package-room <room> --pack-bones 64
      --wide-identity --source-normal-length --ch23-facts --slots
Rooms that already have a package (r112 merchant, r118 em17 + wolf, r11f Mendez) need a merged package: not built here
(capacity: chunks / the 256 KiB ceiling; see docs/lanes/ps2cast.md)."""
import glob, json, os, shutil, sys
A = '/root/probe/lanes-20261014/ps2cast/ashley'
T = '/root/probe/lanes-20261014/ps2cast/t11tree/port/dreamcast/tools/d367/model-registry'
ROOMS = ['r117', 'r118', 'r112', 'r111', 'r113', 'r11c', 'r11f']
src, dst = A + '/regcast-ashley11', A + '/regcast-ashley-ch2'
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(src, dst, symlinks=True)
def fix(o):
    n = 0
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'rooms' and isinstance(v, list) and 'r117' in v:
                for r in ROOMS:
                    if r not in v: v.append(r); n += 1
            else: n += fix(v)
    elif isinstance(o, list):
        for v in o: n += fix(v)
    return n
tot = 0
for p in sorted(glob.glob(dst + '/**/*.json', recursive=True)):
    if os.path.islink(p): continue
    s = json.load(open(p)); k = fix(s)
    if k: json.dump(s, open(p, 'w'), indent=1); tot += k
print('rooms added', tot)
base = json.load(open(T + '/ps2-ashley-r117.json'))
for room in sys.argv[1:]:
    s = json.loads(json.dumps(base))
    s['registry'] = 'ps2-ashley-r' + room
    s['about'] = s['about'].split(' Package only')[0] + ' Room package r%s (lane ps2cast 2026-10-15, offline): Ashley follows Leon here in chapter 2.' % room
    s['cast_dir'] = dst
    s['room_packages'] = {room: dict(descriptors=['ashley11', 'ashley11-h1', 'ashley11-h3'], evidence='stage route: Ashley follows (warp presets r112-entry / r111-entry / r11c-entry; r11f the chapter 2-3 hall)')}
    json.dump(s, open(T + '/ps2-ashley-r%s.json' % room, 'w', newline='\n'), indent=1)
    print('spec', room)
