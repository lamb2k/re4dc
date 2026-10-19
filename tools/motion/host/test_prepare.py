#!/usr/bin/env python3
"""Regressions for extracting current source functions across conditional arms."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('prepare', Path(__file__).with_name('prepare.py'))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class Extraction(unittest.TestCase):
    def extract(self, source):
        with tempfile.TemporaryDirectory(prefix='motion-extract-') as directory:
            src, dst = Path(directory)/'input.cpp', Path(directory)/'output.cpp'
            src.write_text(source)
            prepare.extract(str(src), str(dst), ['pose'])
            return dst.read_text()

    def test_alternative_open_braces_and_lexical_braces(self):
        body = '''void pose()
{
#if defined(SH4)
#if WIDE
    if (true) {
#else
    if (scope) {
#endif
        run(); // } not a close
    }
#elif CHECK
    if (scope) { check(); }
#endif
    const char* message = "{";
    /* { } { */
    source();
}
'''
        actual = self.extract(body+'void next() { unrelated(); }\n')
        self.assertIn(body, actual)
        self.assertNotIn('unrelated', actual)

    def test_inconsistent_arms_refuse_instead_of_truncating(self):
        with self.assertRaisesRegex(SystemExit, 'inconsistent conditional scopes'):
            self.extract('void pose() {\n#if ONE\n if (x) {\n#else\n normal();\n#endif\n}\n')

    def test_unterminated_function_refuses(self):
        with self.assertRaisesRegex(SystemExit, 'unterminated function'):
            self.extract('void pose() {\n')


if __name__ == '__main__':
    unittest.main()
