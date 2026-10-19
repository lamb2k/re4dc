"""Asset-free original-text extraction guards for the motion host helper."""
import tempfile
import unittest
from pathlib import Path

import prepare


class ExtractTests(unittest.TestCase):
    def extract(self, source, name='target'):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'source.cpp', Path(tmp) / 'out.cpp'
            src.write_text(source, encoding='utf-8')
            prepare.extract(str(src), str(dst), [name])
            return dst.read_text(encoding='utf-8')

    def test_ordinary_output_keeps_existing_host_transforms(self):
        body = 'inline void target()\n{\n    register int n asm("r3");\n    auto p = (u32)ptr;\n}\n'
        result = self.extract(body + '\nvoid unrelated() {}\n')
        self.assertTrue(result.endswith(prepare.host_text(body.replace('inline ', '', 1))))
        self.assertNotIn('unrelated', result)

    def test_alternative_opening_braces_and_nested_branches_are_retained(self):
        body = """void target()
{
#if defined(FIRST)
#if NESTED == 3
    if (true) {
#else
    if (scope) {
#endif
        if (inner) { work(); }
#elif defined(SECOND)
    if (other) {
#else
    if (fallback) {
#endif
        work();
    }
}
"""
        result = self.extract(body + '\nvoid unrelated() {}\n')
        self.assertTrue(result.endswith(body))
        self.assertEqual(result.count('#if'), body.count('#if'))
        self.assertNotIn('unrelated', result)

    def test_comments_and_quoted_braces_do_not_change_boundaries(self):
        body = """void target()
{
    // unmatched {
    const char* s = "} /* } */";
    char c = '{';
    /* another { */
}
"""
        self.assertTrue(self.extract(body + '\nvoid unrelated() {}\n').endswith(body))

    def test_inconsistent_conditional_refuses_instead_of_selecting_a_macro(self):
        with self.assertRaisesRegex(ValueError, 'conditional brace depths disagree'):
            self.extract('void target()\n{\n#if OPEN\n if (x) {\n#else\n work();\n#endif\n}\n')

    def test_incomplete_function_refuses(self):
        with self.assertRaisesRegex(ValueError, 'incomplete function'):
            self.extract('void target()\n{\n if (x) {\n}\n')

    def test_conditional_without_else_is_balanced_on_both_paths(self):
        body = 'void target()\n{\n#if OPTIONAL\n if (x) { work(); }\n#endif\n}\n'
        self.assertTrue(self.extract(body).endswith(body))


if __name__ == '__main__':
    unittest.main()
