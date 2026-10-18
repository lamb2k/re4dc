import glob, json, os
P = '/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1/programs/candidate-routecrmW'
for f in glob.glob('/root/probe/lanes-20261017r/ch2regen/fix/*-crmW.json'):
    d = json.load(open(f)); n = 0
    for o in glob.glob(P + '/*.ovl'):
        k = 'dc/' + os.path.basename(o)
        if d['replace'].get(k) != o: d['replace'][k] = o; n += 1
    json.dump(d, open(f, 'w'), indent=1); print(os.path.basename(f), 'overlays added', n)
