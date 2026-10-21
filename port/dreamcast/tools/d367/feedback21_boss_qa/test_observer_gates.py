"""Read-only scheduling must reject stale safe-tick counters during an event."""
from copy import deepcopy
import unittest

from observe import Observer


class ObserverGates(unittest.TestCase):
    def test_safe_sample_and_each_original_gate(self):
        sample = dict(qa_frames=30, event_start_cnt=0, subscreen_type=0,
                      player=dict(rno=[0, 0, 0, 0], alive=1),
                      global_=dict(rno=[3, 0, 0, 0], status=[0, 0, 0, 0]))
        sample["global"] = sample.pop("global_")
        self.assertTrue(Observer.qa_safe(sample))
        for group, field, value in ((None, "qa_frames", 29), (None, "event_start_cnt", 1),
                                    (None, "subscreen_type", 2), ("player", "rno", [5, 0, 0, 0]),
                                    ("player", "alive", 0), ("global", "rno", [6, 0, 0, 0]),
                                    ("global", "rno", [3, 1, 0, 0]),
                                    ("global", "status", [0, 0x10000000, 0, 0])):
            denied = deepcopy(sample)
            (denied[group] if group else denied)[field] = value
            self.assertFalse(Observer.qa_safe(denied), (group, field))

    def test_missing_or_unbound_samples_are_not_safe(self):
        self.assertFalse(Observer.qa_safe(None))
        self.assertFalse(Observer.qa_safe({}))
        self.assertFalse(Observer.qa_safe(dict(qa_frames=500)))


if __name__ == "__main__":
    unittest.main()
