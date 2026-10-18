import re, sys
B = sys.argv[1]
pat = re.compile(r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n', re.S)

def resolve(path, fn):
    s = open(path).read()
    i = [0]
    def rep(m):
        i[0] += 1
        return fn(i[0], m.group(1), m.group(2))
    s = pat.sub(rep, s)
    open(path, 'w').write(s)
    print(path, 'resolved', i[0])

def mk(n, head, inc):
    # 1: union (CH3 modules + gallery module rule)
    if n == 1:
        return head + inc
    if n == 2:   # STAGE_OVL_NAMES: head + st2_4
        return head.replace('st2_3 st4_0', 'st2_3 st2_4 st4_0')
    if n == 3:   # audited modules: both
        return head.split('ifeq ($(ENEMY_DEMAND),1)')[0] + inc
    raise SystemExit('mk %d' % n)

def mc(n, head, inc):
    if n in (1, 2):
        # head ends with the '#if !(DISC2)' opener: put the gallery block before it
        k = head.rindex('#if !(defined(RE4DC_DISC2)')
        return head[:k] + inc + head[k:]
    if n == 3:
        h = head.replace('#if defined(RE4DC_ROUTE_CH3) && RE4DC_ROUTE_CH3\n',
            '#if (defined(RE4DC_ROUTE_CH3) && RE4DC_ROUTE_CH3) || (defined(RE4DC_ROUTE_GALLERY) && RE4DC_ROUTE_GALLERY)\n', 1)
        h = h.replace('80};', '80, 94};', 1)
        assert '80, 94}' in h
        return h
    if n == 4:
        return '#if (defined(RE4DC_ROUTE_CH3) && RE4DC_ROUTE_CH3) || (defined(RE4DC_ROUTE_GALLERY) && RE4DC_ROUTE_GALLERY)\nRouteOverlay g_stage_ovl[14];  // st2_4 (r22c) at 13\n'
    if n == 5:
        return head + '#endif\n#if defined(RE4DC_ROUTE_GALLERY) && RE4DC_ROUTE_GALLERY\n    case 118: return 13;                                                         // st2_4 (r22c)\n'
    raise SystemExit('mc %d' % n)

resolve(B + 'Makefile', mk)
resolve(B + 'platform/modules.cpp', mc)
