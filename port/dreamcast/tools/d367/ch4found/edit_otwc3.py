p = '/root/probe/lanes-20261016/ch4found/tree/src/game/trans.cpp'; s = open(p).read()
start = s.index('#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK\n// OT_WALK_CHECK (lane ch4found16, debug arm)')
end = s.index('#endif\n', start) + len('#endif\n')
block = s[start:end]
s = s[:start] + s[end:]
anchor = 'void SetPrimBuffPtr()\n{'
assert s.count(anchor) == 1
s = s.replace(anchor, block + anchor)
open(p, 'w').write(s)
print('moved', len(block))
