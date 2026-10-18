import json, collections, sys
need = json.load(open('need-n3.json'))['need']
have = set(json.load(open(r'C:\Game Dev\Emulators\re4-assets-private\ch2regen-20261018\discmatch\isomatch.json')))
for p in sys.argv[1:]:
    try: have |= set(json.load(open(p)))
    except Exception as e: print('skip', p, e)
rem = [k for k in need if k not in have]
c = collections.Counter(('dc/tex' if k.startswith('dc/tex/') else k) for k in rem)
print('remaining', len(rem)); print(sorted(c.items()))
json.dump(sorted(rem), open('remaining.json', 'w'), indent=0)
