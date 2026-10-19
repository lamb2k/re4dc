"""Source-lifetime regression from retained r11e actor replacement records."""
import unittest

from prepare_model_id_witness import source_models_in_window

REPLACEMENT = """NMRM admit t=181 room=011e m=8cd34640 id=2b desc=gigante-em2b-02 pos=440,-25,5800 gen=1
NMRM retire t=231 m=8cd34640 appearance=200 admitted_first=181 last=230 frames=50 declines=0
NMRM admit t=231 room=011e m=8cd35420 id=2b desc=gigante-em2b-02 pos=528,-25,5625 gen=1
"""


class Lifetime(unittest.TestCase):
    def select(self, text):
        return source_models_in_window(text, ['gigante-em2b-02'], (290, 309))

    def test_actual_roomless_retire_excludes_replaced_actor(self):
        self.assertEqual(list(self.select(REPLACEMENT)), ['8cd35420'])

    def test_selected_actor_retiring_inside_window_refuses(self):
        with self.assertRaisesRegex(ValueError, 'ownership changes'):
            self.select(REPLACEMENT + 'NMRM retire t=300 m=8cd35420 appearance=200\n')

    def test_new_selected_model_inside_window_refuses(self):
        with self.assertRaisesRegex(ValueError, 'ownership changes'):
            self.select(REPLACEMENT + 'NMRM admit t=300 room=011e m=8cd40000 desc=gigante-em2b-02\n')

    def test_optional_room_retire_has_same_lifetime(self):
        self.assertEqual(self.select(REPLACEMENT),
                         self.select(REPLACEMENT.replace('retire t=231 m=', 'retire t=231 room=011e m=')))

    def test_retired_only_descriptor_is_not_stable(self):
        with self.assertRaisesRegex(ValueError, 'lack stable'):
            self.select(REPLACEMENT + 'NMRM retire t=280 m=8cd35420 appearance=200\n')

    def test_malformed_retire_cannot_be_ignored(self):
        with self.assertRaisesRegex(ValueError, 'Malformed'):
            self.select(REPLACEMENT + 'NMRM retire t=300 unknown\n')


if __name__ == '__main__':
    unittest.main()
