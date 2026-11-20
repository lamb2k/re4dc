#!/usr/bin/env python3
"""refsplit.py <tree> [--list out.tsv]: give the old game's REFERENCE build the owner's random-number split (lane eng-ref,
owner 2026-11-19 "Split it"; ENGINE_PLAN.md section 3).

Applied at build time to an exported copy of the tree (refbuild.sh), never to src/ or include/ in git, never on the
release line. It rewrites each presentation call of the game generator (Rnd, fRand0_1, fRand1_1) listed in SITES into
re4ref_rnd / re4ref_f01 / re4ref_f11 with its category bit; rnd.cpp gains a second generator (the original algorithm
on its own state, starting at 0 like the engine's) that answers a call when its bit is in re4ref_split_mask, else the
call goes to the original generator exactly as before. The warp fixture line `rsplit <mask> [seed]` sets the mask and
the presentation generator's start (dbgwarp_bridge.cpp); the logic trace prints `RS t= pd= pc=` whenever the
presentation generator was drawn (draws so far, categories drawn so far). Every count in SITES is asserted, so a source
change that moves a call fails the patch instead of silently dropping it.

Mask 0 is the unsplit game (every call reaches the original generator, in the original order): the identity proof.
"""
import os, re, sys

# Category bits (also in include/rnd.h after patching).
CAT = dict(
    FX=0x00001,       # effect system: sprites, generators, particles, filters, effect lights; the water shot
    CLOTH=0x00002,    # pendulum cloth (wind phase, skip ticks)
    EYE=0x00004,      # Leon's eye wander
    CAM=0x00008,      # camera sway and shake (scope, look-at, the Ganado's camera moves)
    VOICE=0x00010,    # voice and breath choice and timers (Leon's damage voice, the Ganado's voices, chainsaw tell)
    BLOOD=0x00020,    # the Ganado's blood-effect choice
    FACE=0x00040,     # the partner's face (eye and head wander, blinks)
    CART=0x00080,     # shell casings and pins (weapon objects' setCartridge / setPin, SetObj10)
    SOUND=0x00100,    # sound internals (random SE table pick, sound-area timers)
    # Presentation by nature that the engine images host on the BEHAVIOUR generator (as of engine 5a7c13b69):
    BLOOD2=0x01000,   # em_sub blood bursts (EmDmBloodSet*, EmPlBloodSet): hosted in the fight and boss images
    VOICE2=0x02000,   # em10CoreBreak's voice, r101's Ganado voice task: hosted in the fight image
    CAM2=0x04000,     # em10SetCampos2 (cut-in camera side), the rock-escape camera moves
    THUNDER_R11D=0x08000,  # r11d's thunder flash and sound timer (room script not hosted)
    RUMBLE=0x10000,   # pad rumble level (pad.cpp VibControl: hosted in every engine image)
    SCEOBJ_VIB=0x20000,    # scene-object vibration (cSceObj::getVibrationValue)
    THUNDER_R119=0x40000,  # r119's thunder (hosted in the boss image)
    # Behaviour by the integrator's ruling (eng-e1d), presentation in engine 5a7c13b69's images: an ARM only.
    AIMSWAY=0x80000,  # PlWepLockRand
)
OWNER = 0x001FF | 0x01000 | 0x02000 | 0x04000 | 0x08000 | 0x10000 | 0x20000 | 0x40000   # 0x7F1FF, the default

# (file, function or '*' for every call in the file, category, expected calls)
SITES = [
    # FX: the effect system, whole files (the engine's native effect service has its own generator)
    ('game/esp04.cpp', '*', 'FX', 2), ('game/esp05.cpp', '*', 'FX', 4), ('game/esp06.cpp', '*', 'FX', 1),
    ('game/esp0b.cpp', '*', 'FX', 4), ('game/esp16.cpp', '*', 'FX', 6), ('game/esp1a.cpp', '*', 'FX', 4),
    ('game/esp4b.cpp', '*', 'FX', 2), ('game/esp4e.cpp', '*', 'FX', 2), ('game/espgen00.cpp', '*', 'FX', 5),
    ('game/espgen02.cpp', '*', 'FX', 5), ('game/espgen45.cpp', '*', 'FX', 2), ('game/Espgen42.cpp', '*', 'FX', 2),
    ('game/Espgen43.cpp', '*', 'FX', 1), ('game/est.cpp', '*', 'FX', 3), ('game/filter06.cpp', '*', 'FX', 6),
    ('game/filter08.cpp', '*', 'FX', 2), ('game/light01.cpp', '*', 'FX', 1),
    ('game/pl_wep.cpp', 'wepSetWaterShot', 'FX', 3),
    # CLOTH
    ('game/pendulum.cpp', '*', 'CLOTH', 11),
    # EYE, CAM, VOICE, BLOOD, FACE: the engine's e1_present list (engine/game/Makefile PRESENT_*, fight.mk PRESENT_em10)
    ('game/pl_class.cpp', 'cPlayer::moveEyeNormal', 'EYE', 4),
    ('game/cam_extra.cpp', 'CameraScope::move', 'CAM', 3),
    ('game/cam_extra.cpp', 'CameraLookAt::CameraLookAt', 'CAM', 1),
    ('em10/em10.cpp', 'em10CamMove', 'CAM', 3),
    ('em10/em10.cpp', 'em10CamMoveCri', 'CAM', 3),
    ('game/pl_sub.cpp', 'PlSetDamageSe', 'VOICE', 1),
    ('em10/em10.cpp', 'em10CallVoiceSe', 'VOICE', 2),
    ('em10/em10.cpp', 'em10CallVoiceSe2', 'VOICE', 2),
    ('em10/em10.cpp', 'em10BreathSe', 'VOICE', 2),
    ('em10/em10.cpp', 'em10CsawSignSe', 'VOICE', 2),
    ('em10/em10.cpp', 'em10SetDamageVoice', 'VOICE', 2),
    ('em10/em10.cpp', 'em10BloodSet', 'BLOOD', 1),
    ('em10/em10.cpp', 'em1cBloodSet', 'BLOOD', 1),
    ('game/pl_npc.cpp', 'cSubChar::moveFace', 'FACE', 4),
    # CART: the engine moves cObjRuger::setCartridge and stubs SetObj10; every other weapon's casing / pin likewise
    ('wep/objRuger.cpp', 'cObjRuger::setCartridge', 'CART', 3),
    ('wep/objMachinegun.cpp', 'cObjMachinegun::setCartridge', 'CART', 3),
    ('wep01/objFn57.cpp', 'cObjFn57::setCartridge', 'CART', 3),
    ('wep02/objMauser.cpp', 'cObjMauser::setCartridge', 'CART', 3),
    ('wep02/objMauser.cpp', 'cObjMauser::setPin', 'CART', 3),
    ('wep04/wep04.cpp', 'cObjXd9::setCartridge', 'CART', 3),
    ('wep06/wep06.cpp', 'cObjGovernment::setCartridge', 'CART', 3),
    ('wep07/wep07.cpp', 'cObjShotgun::setCartridge', 'CART', 3),
    ('wep08/wep08.cpp', 'cObjStriker::setCartridge', 'CART', 3),
    ('wep09/objSniper.cpp', 'cObjSniper::setCartridge', 'CART', 3),
    ('wep12/objTompson.cpp', 'cObjTompson::setCartridge', 'CART', 3),
    ('wep14/objMine.cpp', 'cObjMine::setCartridge', 'CART', 3),
    ('wep17/objVp70.cpp', 'cObjVp70::setCartridge', 'CART', 3),
    ('wep27/wep27.cpp', 'cObjMachinegun::setCartridge', 'CART', 3),
    ('wep33/wep33.cpp', 'cObjShotgun::setCartridge', 'CART', 3),
    ('wep38/wep38.cpp', 'cObjRuger::setCartridge', 'CART', 3),
    ('wep39/wep39.cpp', 'cObjMachinegun::setCartridge', 'CART', 3),
    ('wep44/wep44.cpp', 'cObjGovernment::setCartridge', 'CART', 3),
    ('game/obj10.cpp', 'SetObj10', 'CART', 5),
    # SOUND (not hosted by the engine: SndCall is a stub)
    ('game/snd.cpp', '*', 'SOUND', 1), ('game/se_at.cpp', '*', 'SOUND', 1),
    # Presentation by nature, on the engine's behaviour generator where hosted (bits outside the engine's list)
    ('game/em_sub.cpp', 'EmDmBloodSet', 'BLOOD2', 17),
    ('game/em_sub.cpp', 'EmDmBloodSet2', 'BLOOD2', 3),
    ('game/em_sub.cpp', 'EmDmBloodSet3', 'BLOOD2', 3),
    ('game/em_sub.cpp', 'EmPlBloodSet', 'BLOOD2', 2),
    ('em10/em10.cpp', 'em10CoreBreak', 'VOICE2', 2),
    ('st1/r101.cpp', 'r101_callGanadoVoice', 'VOICE2', 2),
    ('em10/em10.cpp', 'em10SetCampos2', 'CAM2', 1),
    ('game/emrock.cpp', 'plemRockEscapeCamMove', 'CAM2', 3),
    ('game/emrock.cpp', 'plemRockEscapeCamMove2', 'CAM2', 3),
    ('st1/r11d.cpp', 'r11d_ThunderMove', 'THUNDER_R11D', 2),
    ('st1/r119.cpp', 'r119_ThunderMove', 'THUNDER_R119', 2),
    ('game/pad.cpp', 'VibControl', 'RUMBLE', 2),
    ('st/cSceObj.cpp', 'cSceObj::getVibrationValue', 'SCEOBJ_VIB', 6),
    # Behaviour by ruling; a bit so the engine images of 5a7c13b69 (aim sway still presentation) can be matched
    ('game/pl_wep.cpp', 'PlWepLockRand', 'AIMSWAY', 4),
]

CALL = re.compile(r'\b(Rnd|fRand0_1|fRand1_1)\s*\(\s*\)')
FN = re.compile(r'^(?:[A-Za-z_][\w:<>\*&\s,]*?\s)?\**([A-Za-z_~][\w:~]*)\s*\(')
REPL = dict(Rnd='re4ref_rnd', fRand0_1='re4ref_f01', fRand1_1='re4ref_f11')


def functions(lines):
    """Enclosing function of each line: the last column-0 line that opens a function (as s/rndsites.py)."""
    cur, out = '?', []
    for l in lines:
        if l and not l[0].isspace() and not l.startswith(('#', '//', '/*', '{', '}')) and '(' in l \
                and not l.rstrip().endswith(';'):
            m = FN.match(re.sub(r'^extern "C"\s+', '', l))
            if m and m.group(1) not in ('if', 'for', 'while', 'switch', 'return'):
                cur = m.group(1)
        out.append(cur)
    return out


def sub_once(path, a, b):
    s = open(path, encoding='latin-1').read()
    assert s.count(a) == 1, (path, a[:60], s.count(a))
    open(path, 'w', encoding='latin-1').write(s.replace(a, b))


RND_H = '''
// re4ref split (lane eng-ref; REFERENCE build only, applied at build time by tools/plays_right/refsplit/refsplit.py):
// presentation calls draw from a second generator when their category bit is in re4ref_split_mask.
extern "C" {
unsigned char re4ref_rnd(unsigned int cat);
float re4ref_f01(unsigned int cat);
float re4ref_f11(unsigned int cat);
void re4ref_pseed(unsigned short seed);
}
'''

RND_CPP = '''
// re4ref split (lane eng-ref; REFERENCE build only). The presentation generator: the original algorithm on its own
// state, starting at 0 (as the engine's, host/e1_wraps.cpp). A call whose category bit is in re4ref_split_mask draws
// from it; any other call reaches the original Rnd / fRand0_1 / fRand1_1 above, unchanged.
extern "C" {
volatile unsigned int re4ref_split_mask = %#x;
unsigned int re4ref_pdraws;    // presentation generator steps so far
unsigned int re4ref_pcats;     // categories that drew from it so far
}
static u16 PRandom;
extern "C" void re4ref_pseed(unsigned short s) { PRandom = s; }
static u8 PRnd()
{
    u16 r = PRandom;
    u32 n = ((u8) ((r >> 1) + (r >> 8)) << 8) | (u8) (r >> 1);
    u32 m = (n << 16) >> 16;

    if (m == r) {
        m = n + 0x101;
    }
    PRandom = m;
    re4ref_pdraws++;
    return m >> 8;
}
static f32 PUnit()
{
    u32 a = PRnd();
    u32 b = PRnd();
    u32 c = PRnd();
    u32 u = a + (b << 8) + ((c & 0x7F) << 16) + 0x3F800000;

    return *(f32*) &u;
}
extern "C" unsigned char re4ref_rnd(unsigned int cat)
{
    if (re4ref_split_mask & cat) {
        re4ref_pcats |= cat;
        return PRnd();
    }
    return Rnd();
}
extern "C" float re4ref_f01(unsigned int cat)
{
    if (re4ref_split_mask & cat) {
        re4ref_pcats |= cat;
        return PUnit() - 1.0f;
    }
    return fRand0_1();
}
extern "C" float re4ref_f11(unsigned int cat)
{
    if (re4ref_split_mask & cat) {
        re4ref_pcats |= cat;
        return PUnit() * 2.0f - 3.0f;
    }
    return fRand1_1();
}
'''

BTRACE_CPP = '''
// re4ref site trace (lane eng-ref, diagnostic build only): behaviour draws named by site when re4ref_btrace is set.
extern "C" void re4dc_log(const char* fmt, ...);
extern "C" {
volatile unsigned int re4ref_btrace;
unsigned char re4ref_brnd(unsigned int s)
{
    if (re4ref_btrace) re4dc_log("RB s=%u\\n", s);
    return Rnd();
}
float re4ref_bf01(unsigned int s)
{
    if (re4ref_btrace) re4dc_log("RB s=%u\\n", s);
    return fRand0_1();
}
float re4ref_bf11(unsigned int s)
{
    if (re4ref_btrace) re4dc_log("RB s=%u\\n", s);
    return fRand1_1();
}
}
'''
BWARP_OLD = '''        } else if (!strcmp(k, "god")) {
'''
BWARP_NEW = '''        } else if (!strcmp(k, "rsplit_trace") && n >= 2) {
            re4ref_btrace = num(tok[1]);
        } else if (!strcmp(k, "god")) {
'''

DECL_PORT = ('extern "C" { extern volatile unsigned int re4ref_split_mask, re4ref_btrace; extern unsigned int re4ref_pdraws, '
             're4ref_pcats; void re4ref_pseed(unsigned short); }  // re4ref split (lane eng-ref)\n')

WARP_OLD = '''        } else if (!strcmp(k, "god")) {
'''
WARP_NEW = '''        } else if (!strcmp(k, "rsplit") && n >= 2) {
            // re4ref split (lane eng-ref, reference build only): `rsplit <mask> [presentation seed]`
            re4ref_split_mask = num(tok[1]);
            if (n >= 3) re4ref_pseed((unsigned short) num(tok[2]));
            re4dc_log("warp: rsplit mask=%x seed=%x\\n", (unsigned) re4ref_split_mask, n >= 3 ? (unsigned) num(tok[2]) : 0u);
        } else if (!strcmp(k, "autoplay")) {
            // the outcome check's closed-loop player (tools/plays_right/autoplay/autoplay.inc) drives pad 0
            re4ap_on = 1;
            re4dc_log("warp: autoplay\\n");
        } else if (!strcmp(k, "god")) {
'''

# the outcome check's player: included after the game headers; drives the pad after the event check
INC_OLD = '''#include "em10.h"
'''
INC_NEW = '''#include "em10.h"
static int re4ap_on;   // lane eng-ref: `autoplay` fixture line
#include "re4ap_autoplay.inc"
'''
PAD_OLD = '''        re4dc_warp_cut("event");
        return;
    }
'''
PAD_NEW = '''        re4dc_warp_cut("event");
        return;
    }
    if (re4ap_on) {   // lane eng-ref: the closed-loop player replaces the fixture's actions
        re4ap_pad(buttons, stickX, stickY);
        return;
    }
'''

TRACE_OLD = '''    const unsigned rng = re4dc_rnd_state();
    const unsigned room = (unsigned(pG->stage_no) << 8) | pG->room_no;
'''
TRACE_NEW = '''    const unsigned rng = re4dc_rnd_state();
    {   // re4ref split (lane eng-ref, reference build only): presentation draws so far, when they moved
        static unsigned int rs_last = ~0u;
        if (re4ref_pdraws != rs_last) {
            re4dc_log("RS t=%u pd=%u pc=%x\\n", (unsigned) pG->Frame_cnt, (unsigned) re4ref_pdraws, (unsigned) re4ref_pcats);
            rs_last = re4ref_pdraws;
        }
    }
    const unsigned room = (unsigned(pG->stage_no) << 8) | pG->room_no;
'''


def main():
    tree = sys.argv[1]
    out = sys.argv[sys.argv.index('--list') + 1] if '--list' in sys.argv else None
    mask = int(sys.argv[sys.argv.index('--mask') + 1], 0) if '--mask' in sys.argv else OWNER
    src = os.path.join(tree, 'src')
    rows, byfile = [], {}
    for f, fn, cat, n in SITES:
        byfile.setdefault(f, []).append((fn, cat, n))
    for f, entries in sorted(byfile.items()):
        path = os.path.join(src, f)
        lines = open(path, encoding='latin-1').read().split('\n')
        owner = functions(lines)
        for fn, cat, n in entries:
            hit = 0
            for i, l in enumerate(lines):
                if fn != '*' and owner[i] != fn:
                    continue
                if l.strip().startswith('//'):
                    continue
                def rep(m):
                    return '%s(%#x)' % (REPL[m.group(1)], CAT[cat])
                new, k = CALL.subn(rep, l)
                if k:
                    for m in CALL.finditer(l):
                        rows.append((f, i + 1, owner[i], cat, '%#x' % CAT[cat], m.group(1)))
                    lines[i] = new
                    hit += k
            assert hit == n, (f, fn, cat, 'expected', n, 'found', hit)
        decl = ('extern "C" { unsigned char re4ref_rnd(unsigned int); float re4ref_f01(unsigned int); '
                'float re4ref_f11(unsigned int); }  // re4ref split (lane eng-ref)')
        open(path, 'w', encoding='latin-1').write(decl + '\n' + '\n'.join(lines))
    if '--trace-sites' in sys.argv:
        # diagnostic build: every OTHER generator call (behaviour) gets a site number and, when the fixture says
        # `rsplit_trace 1`, logs `RB s=<site>` as it draws (the cause of a draw-count difference, by name)
        bmap = []
        for d, _, fs in os.walk(src):
            for fn in sorted(fs):
                if not fn.endswith('.cpp'):
                    continue
                path = os.path.join(d, fn)
                rel = os.path.relpath(path, src).replace(os.sep, '/')
                if rel == 'game/rnd.cpp':
                    continue
                text = open(path, encoding='latin-1').read()
                if not CALL.search(text):
                    continue
                lines = text.split('\n')
                owner = functions(lines)
                for i, l in enumerate(lines):
                    if l.strip().startswith('//') or not CALL.search(l):
                        continue
                    def rep(m):
                        bmap.append((len(bmap), rel, i + 1, owner[i], m.group(1)))
                        return '%s(%d)' % (dict(Rnd='re4ref_brnd', fRand0_1='re4ref_bf01', fRand1_1='re4ref_bf11')[
                            m.group(1)], len(bmap) - 1)
                    lines[i] = CALL.sub(rep, l)
                bdecl = ('extern "C" { unsigned char re4ref_brnd(unsigned int); float re4ref_bf01(unsigned int); '
                         'float re4ref_bf11(unsigned int); }  // re4ref site trace (lane eng-ref)')
                open(path, 'w', encoding='latin-1').write(bdecl + '\n' + '\n'.join(lines))
        with open(os.path.join(src, 'game/rnd.cpp'), 'a', encoding='latin-1') as fp:
            fp.write(BTRACE_CPP)
        if out:
            with open(out.replace('.tsv', '-bsites.tsv'), 'w') as fp:
                fp.write('site\tfile\tline\tfunction\tcall\n')
                for r in bmap:
                    fp.write('\t'.join(str(x) for x in r) + '\n')
        sub_once(os.path.join(tree, 'port/dreamcast/game/dbgwarp_bridge.cpp'), BWARP_OLD, BWARP_NEW)
        print('refsplit: site trace on %d behaviour calls' % len(bmap))
    rnd_h = os.path.join(tree, 'include/rnd.h')
    s = open(rnd_h, encoding='latin-1').read()
    assert '#endif' in s
    i = s.rindex('#endif')
    open(rnd_h, 'w', encoding='latin-1').write(s[:i] + RND_H + '\n' + s[i:])
    with open(os.path.join(src, 'game/rnd.cpp'), 'a', encoding='latin-1') as fp:
        fp.write(RND_CPP % mask)
    sub_once(os.path.join(tree, 'port/dreamcast/game/dbgwarp_bridge.cpp'), WARP_OLD, WARP_NEW)
    sub_once(os.path.join(tree, 'port/dreamcast/game/logic_trace.cpp'), TRACE_OLD, TRACE_NEW)
    sub_once(os.path.join(tree, 'port/dreamcast/game/dbgwarp_bridge.cpp'), INC_OLD, INC_NEW)
    sub_once(os.path.join(tree, 'port/dreamcast/game/dbgwarp_bridge.cpp'), PAD_OLD, PAD_NEW)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, '..', 'autoplay', 'autoplay.inc'), encoding='latin-1') as fp:
        ap = fp.read()
    with open(os.path.join(tree, 'port/dreamcast/game/re4ap_autoplay.inc'), 'w', encoding='latin-1') as fp:
        fp.write(ap)
    # file-scope C declarations (the parser and the trace live in anonymous namespaces: a block-scope extern there
    # would name a different, unresolved symbol)
    for f in ('port/dreamcast/game/dbgwarp_bridge.cpp', 'port/dreamcast/game/logic_trace.cpp'):
        p = os.path.join(tree, f)
        s = open(p, encoding='latin-1').read()
        open(p, 'w', encoding='latin-1').write(DECL_PORT + s)
    if out:
        with open(out, 'w') as fp:
            fp.write('file\tline\tfunction\tcategory\tbit\tcall\n')
            for r in rows:
                fp.write('\t'.join(str(x) for x in r) + '\n')
    print('refsplit: %d calls rewritten in %d files, default mask %#x' % (len(rows), len(byfile), mask))


if __name__ == '__main__':
    main()
