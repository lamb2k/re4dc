import json
L='/root/probe/lanes-20261014/ch22/fix/'
d=json.load(open(L+'route-v3.json'))
k='dc/tex/f/fbec854a-b7656a09.re4tex'
d['replace'][k]='/root/probe/lanes-20261010/r117/rooms/pairs-em11/fbec854a-b7656a09.re4tex'
d['remove']=[x for x in d['remove'] if x!=k]
d['provenance']['route-v4']='route-v3 + fbec854a-b7656a09 (r117 after-state em11 pair; same file as the test 11 --data fbec)'
json.dump(d,open(L+'route-v4.json','w'),indent=1,sort_keys=True)
print('v4',len(d['replace']))
