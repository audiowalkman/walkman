import collections
import unittest

import walkman


class SequencerTest(walkman.unit_tests.WalkmanTestCase, unittest.TestCase):
    E = collections.namedtuple("Event", ("duration", "kwargs", "is_rest"))

    def test_sequencer(self):
        e_tuple = (self.E(1, {}, True), self.E(1, {}, False), self.E(1, {}, True))
        module_name_to_replication_configuration_dict = {"sine": {"0": {}}}
        module_container = walkman.ModuleContainer.from_module_configuration(
            module_name_to_replication_configuration_dict
        )
        sine = module_container["sine"]["0"]
        p = sine.pyo_object
        sequencer = walkman.Sequencer(sine)
        sequencer.event_iterator = iter(e_tuple)
        self.assertIsSilent(p, duration_in_seconds=1)
        sequencer.play()
        self.assertIsSilent(p, duration_in_seconds=1)
        self.assertIsNotSilent(
            p,
            # + 0.01 because fade out is imprecise
            duration_in_seconds=1 + sine.fade_out_duration + 0.01,
        )
        self.assertIsSilent(p, duration_in_seconds=1)
        sequencer.stop()
