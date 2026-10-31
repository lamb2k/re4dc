"""console_pt.py LOG...: mean per-tick phase times (us) over the complete PT windows of QA-link console logs."""
import re, sys, collections, json
FIELDS_END = 'post'   # last field of a window's final line

def windows(path):
    w = collections.OrderedDict()
    seen = set()
    for line in open(path, encoding='utf-8', errors='replace'):
        if line in seen:
            continue
        seen.add(line)
        m = re.search(r' L PT f=(\d+)-(\d+) n=(\d+) (.*)', line)
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        d = w.setdefault(key, {})
        for k, v in re.findall(r'([\w.]+)=([\d/]+)', m.group(4)):
            d[k] = [int(x) for x in v.split('/')]
    return {k: d for k, d in w.items() if 'total' in d and 'post' in d and 'setup' in d}

out = {}
for p in sys.argv[1:]:
    ws = windows(p)
    acc = collections.defaultdict(list)
    for d in ws.values():
        for k, v in d.items():
            acc[k].append(v[0])
    name = re.sub(r'.*[\\/]|\.log$', '', p)
    out[name] = {'windows': len(ws), 'frames': [list(k) for k in ws], **{k: round(sum(v) / len(v)) for k, v in acc.items()}}
    print(name, len(ws), 'windows', {k: out[name][k] for k in ('total', 'setup', 'logic', 'trans', 'post', 'cpu', 'remain') if k in out[name]})
json.dump(out, open('console_pt.json', 'w'), indent=1)
