"""addmov.py <armed.json>...: add the island route movies (st3 lane 288x192 .seq; r331/r332 left to stress16b)."""
import json, sys, glob, os
M = '/root/probe/lanes-20261014/st3/movies/movies-288x192-full'
movies = {'dc/movie/%s.seq' % os.path.basename(d.rstrip('/')): '%s/%s.seq' % (d.rstrip('/'), os.path.basename(d.rstrip('/')))
          for d in glob.glob(M + '/r3*/') if not os.path.basename(d.rstrip('/')).startswith(('r331', 'r332'))}
for f in sys.argv[1:]:
    j = json.load(open(f)); j['replace'].update(movies)
    j['remove'] = [x for x in j.get('remove', []) if x not in j['replace']]
    json.dump(j, open(f, 'w'), indent=1, sort_keys=True)
    print(f.split('/')[-1], len(movies), 'movies')
