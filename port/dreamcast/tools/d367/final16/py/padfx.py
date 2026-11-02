"""padfx.py <armed.json> <padscript.txt>: stage a padscript as dc/padscript.txt on a fixture."""
import json, sys
f, p = sys.argv[1:3]
d = json.load(open(f)); d['replace']['dc/padscript.txt'] = p
d['remove'] = [x for x in d.get('remove', []) if x != 'dc/padscript.txt']
json.dump(d, open(f, 'w'), indent=1, sort_keys=True); print('padscript', p)
