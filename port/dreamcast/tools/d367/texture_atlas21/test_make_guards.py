"""Exercise the actual ps2leon.mk guards without compiling or private assets."""
from pathlib import Path
import subprocess
import tempfile
import unittest


class AtlasMakeGuards(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='re4dc-atlas-make-')
        self.root=Path(self.tmp.name)
        self.game=Path(__file__).resolve().parents[3]/'game'
        for name in ('ps2leon_runtime.h','ps2leon_hair_runs.h','ps2leon_pl08_pack_identity.inc','leon_atlas_split_data.h'):
            (self.root/name).write_text('// Parse-only fixture. No source asset.\n')
        self.obj=self.root/'coarse_actor.o'
        self.mk=self.root/'probe.mk'
        self.mk.write_text('''OBJDIR := {root}
COARSE_LEON=1
ACTOR_TRANSACTION=1
LEON_NATIVE_PIPE=0
CHARBAKE_HAIR=0
PS2_LEON=1
PS2_LEON_DIR={root}
ACTOR_PL08=1
ACTOR_PL08_PACK=1
LEON_ATLAS_SPLIT_DIR={root}
include {game}/ps2leon.mk
.PHONY: report
report:
\t@printf '%s\\n' 'split=$(LEON_ATLAS_SPLIT)'
$(OBJDIR)/coarse_actor.o:
\t@printf '%s\\n' 'flags=$(GAME_CPPFLAGS)'
'''.format(root=self.root,game=self.game))

    def tearDown(self):
        self.tmp.cleanup()

    def run_make(self,*knobs,target='report'):
        return subprocess.run(['make','--no-print-directory','-f',str(self.mk),*knobs,target],
                              cwd=self.game,capture_output=True,text=True)

    def test_default_and_explicit_off_commands_match(self):
        self.assertEqual(self.run_make().stdout.strip(),'split=0')
        default=self.run_make('-n',target=str(self.obj))
        explicit=self.run_make('LEON_ATLAS_SPLIT=0','-n',target=str(self.obj))
        self.assertEqual((default.returncode,explicit.returncode),(0,0))
        self.assertEqual(default.stdout,explicit.stdout)
        self.assertNotIn('RE4DC_LEON_ATLAS_SPLIT',default.stdout)

    def test_valid_on(self):
        result=self.run_make('LEON_ATLAS_SPLIT=1','-n',target=str(self.obj))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('-DRE4DC_LEON_ATLAS_SPLIT=1',result.stdout)

    def test_invalid_values(self):
        for value in ('','0 1','1 0','1 1','0 0','2','true','1 '):
            with self.subTest(value=value):
                result=self.run_make('LEON_ATLAS_SPLIT='+value)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('LEON_ATLAS_SPLIT must be 0 or 1',result.stderr)

    def test_missing_prerequisites(self):
        for knob in ('PS2_LEON=0','PS2_LEON=2','ACTOR_PL08=0','ACTOR_PL08=11','ACTOR_PL08_PACK=0','ACTOR_PL08_PACK=',
                     'LEON_ATLAS_SPLIT_DIR='):
            with self.subTest(knob=knob):
                result=self.run_make('LEON_ATLAS_SPLIT=1',knob)
                self.assertNotEqual(result.returncode,0)
        result=self.run_make('LEON_ATLAS_SPLIT=1','LEON_LOD=1','LEON_HAND_PACK=1','LEON_LOD_PACK='+str(self.root/'unselected.re4lp'))
        self.assertNotEqual(result.returncode,0)
        self.assertIn('LEON_ATLAS_SPLIT has no alternate LEON_LOD',result.stderr)


if __name__=='__main__':unittest.main()