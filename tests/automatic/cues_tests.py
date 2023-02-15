import unittest

import walkman


class CueTest(walkman.unit_tests.WalkmanTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.module_container = walkman.ModuleContainer(
            {
                "sine": {"modern": walkman.Sine()},
                "mixer": {
                    "master_output": walkman.Mixer(
                        send_to_physical_output=True, audio_input_0="sine.modern"
                    )
                },
            }
        )

        self.sine = self.module_container["sine"]["modern"]
        self.mixer = self.module_container["mixer"]["master_output"]

        module_instance_list = []
        for replication_key_to_module in self.module_container.values():
            for module_instance in replication_key_to_module.values():
                module_instance_list.append(module_instance)
        for module_instance in module_instance_list:
            self.setup_module_instance(module_instance, self.module_container)

        self.cue_0 = walkman.Cue(
            self.module_container, "1", sine={"modern": {"frequency": 99}}
        )
        self.cue_1 = walkman.Cue(
            self.module_container, "cue_2", mixer={"master_output": {}}
        )

    def test_name(self):
        self.assertEqual(self.cue_0.name, "1")
        self.assertEqual(self.cue_1.name, "cue_2")

    def test_duration(self):
        self.assertEqual(self.cue_0.duration, 0)

    def test_active_main_module_tuple(self):
        self.assertEqual(
            self.cue_0.active_main_module_tuple,
            (self.sine,),
        )
        self.assertEqual(
            self.cue_1.active_main_module_tuple,
            (self.mixer,),
        )

    def test_active_dependency_module_tuple(self):
        self.assertEqual(
            self.cue_0.active_dependency_module_tuple,
            (self.sine.frequency, self.sine.decibel, self.mixer, self.mixer.decibel),
        )
        self.assertEqual(
            self.cue_1.active_dependency_module_tuple,
            (
                self.mixer.audio_input_1,
                self.sine.frequency,
                self.sine.decibel,
                self.sine,
                self.mixer.decibel,
            ),
        )

    def test_active_module_tuple(self):
        self.assertEqual(
            self.cue_0.active_module_tuple,
            (
                self.sine.frequency,
                self.sine.decibel,
                self.mixer,
                self.mixer.decibel,
                self.sine,
            ),
        )
        self.assertEqual(
            self.cue_1.active_module_tuple,
            (
                self.mixer.audio_input_1,
                self.sine.frequency,
                self.sine.decibel,
                self.sine,
                self.mixer.decibel,
                self.mixer,
            ),
        )
