"""Compile the actual pad mapper; retain the original stale-map negative control."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[5]
PAD = "port/dreamcast/game/platform/pad.cpp"
ORIGINAL = "aafc10f3601b087f60311ca5f24bb641ef6114bb"
PREFIX = r"""
#include <cstring>
#include <cassert>
#include <cstdio>
#define BIT(n) (1u<<(n))
#define CONT_C BIT(0)
#define CONT_B BIT(1)
#define CONT_A BIT(2)
#define CONT_START BIT(3)
#define CONT_DPAD_UP BIT(4)
#define CONT_DPAD_DOWN BIT(5)
#define CONT_DPAD_LEFT BIT(6)
#define CONT_DPAD_RIGHT BIT(7)
#define CONT_Z BIT(8)
#define CONT_Y BIT(9)
#define CONT_X BIT(10)
"""
HARNESS = r"""
static Re4dcPadMap m; static PADStatus p;
static void poll(u32 buttons=0,int lt=0,int rt=0,int ctx=RE4DC_PAD_CTX_LOOK,int dual=0) {
 Re4dcPadIn in={buttons,lt,rt,0,0,0,0};
 memset(&p,0,sizeof(p));re4dcMapPad(&in,ctx,dual,&m,&p);
}
static void reset(){memset(&m,0,sizeof(m));poll();}
"""


def mapper(source):
    return source[source.index("typedef signed char s8;"):source.index("// Scripted input fixture:")]


class QaChord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = subprocess.check_output(["git", "show", ORIGINAL + ":" + PAD], cwd=ROOT, text=True)
        cls.current = (ROOT / PAD).read_text()

    def executable(self, source, suffix, qa=1):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "mapper"
            subprocess.run(["g++", "-x", "c++", "-std=c++17", "-O2", "-Wall", "-Wno-unused-function",
                            "-DRE4DC_QA_MENU=" + str(qa), "-", "-o", str(output)],
                           input=PREFIX + mapper(source) + HARNESS + suffix, text=True, check=True)
            return subprocess.check_output([str(output)], text=True)

    def test_original_one_poll_chord_leaves_a_map_pulse(self):
        suffix = r"""
int main(){reset();poll(CONT_DPAD_DOWN,255,255);poll();
 assert(p.button&PAD_TRIGGER_Z);poll();assert(p.button&PAD_TRIGGER_Z);
 puts("original one-poll QA chord produces two stale map polls");}
"""
        self.assertIn("two stale map polls", self.executable(self.original, suffix))

    def test_consumed_chord_release_orders_and_regular_controls(self):
        suffix = r"""
int main(){
 int cases=0;
 for(int ctx=0;ctx<3;ctx++)for(int dual=0;dual<2;dual++)for(int release=0;release<4;release++) {
  reset();poll(0,0,0,ctx,dual);
  poll(CONT_DPAD_DOWN|CONT_A,255,255,ctx,dual);
  assert(!(p.button&PAD_TRIGGER_Z));assert(!(p.button&PAD_BUTTON_DOWN));
  assert(p.button&PAD_BUTTON_A);assert(p.triggerLeft==150&&p.triggerRight==150);
  // No mapper polls during the menu. The next poll sees all or part released.
  if(release==1)poll(0,255,255,ctx,dual);
  if(release==2)poll(CONT_DPAD_DOWN,0,0,ctx,dual);
  if(release==3){poll(CONT_DPAD_DOWN,255,0,ctx,dual);poll(CONT_DPAD_DOWN,0,255,ctx,dual);}
  for(int i=0;i<4;i++){poll(0,0,0,ctx,dual);assert(!(p.button&PAD_TRIGGER_Z));}
  ++cases;
 }
 for(int lt=0;lt<3;lt++)for(int rt=0;rt<3;rt++) {
  const int values[]={0,200,201};reset();poll(CONT_DPAD_DOWN,values[lt],values[rt]);poll();
  assert(bool(p.button&PAD_TRIGGER_Z)==!(values[lt]>200&&values[rt]>200));++cases;
 }
 // A new ordinary Down tap after the QA chord still opens the map normally.
 reset();poll(CONT_DPAD_DOWN,255,255);poll();poll(CONT_DPAD_DOWN);poll();
 assert(p.button&PAD_TRIGGER_Z);poll();assert(p.button&PAD_TRIGGER_Z);poll();assert(!p.button);
 // Any earlier synthetic map pulse is cleared when the raw QA chord is taken.
 reset();poll(CONT_DPAD_DOWN);poll();assert(p.button&PAD_TRIGGER_Z);
 poll(CONT_DPAD_DOWN,255,255);assert(!(p.button&PAD_TRIGGER_Z));poll();assert(!(p.button&PAD_TRIGGER_Z));
 printf("QA mapper release cases=%d; ordinary map and threshold controls pass\n",cases);
}
"""
        self.assertIn("cases=33", self.executable(self.current, suffix))

    def test_disabled_mapper_object_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for index, (source, defines) in enumerate(((self.original, []), (self.current, []),
                                                       (self.current, ["-DRE4DC_QA_MENU=0"]))):
                output = Path(directory) / f"mapper{index}.o"
                suffix = r"""
void mapped(const Re4dcPadIn* in,int ctx,int dual,Re4dcPadMap* m,PADStatus* p){
 re4dcMapPad(in,ctx,dual,m,p);
 p->button=re4dcBlockDebugChords(p->button,0,m);
}
"""
                subprocess.run(["g++", "-x", "c++", "-std=c++17", "-O2", "-c", *defines, "-", "-o", str(output)],
                               input=PREFIX + mapper(source) + suffix, text=True, check=True)
                outputs.append(output.read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0], outputs[2])


if __name__ == "__main__":
    unittest.main()
