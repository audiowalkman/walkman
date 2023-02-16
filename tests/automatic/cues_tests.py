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
        self.cue_2 = walkman.Cue(
            self.module_container, "3", mixer={"master_output": {}}, sine={"modern": {}}
        )

    def test_name(self):
        self.assertEqual(self.cue_0.name, "1")
        self.assertEqual(self.cue_1.name, "cue_2")

    def test_duration(self):
        self.assertEqual(self.cue_0.duration, 0)

    def test_active_main_module_tuple(self):
        self.assertEqual(
            self.cue_0.active_main_module_tuple,
            (self.sine.base,),
        )
        self.assertEqual(
            self.cue_1.active_main_module_tuple,
            (self.mixer.base,),
        )
        self.assertEqual(
            self.cue_2.active_main_module_tuple,
            (self.mixer.base, self.sine.base),
        )

    def test_active_dependency_module_tuple(self):
        self.assertEqual(
            self.cue_0.active_dependency_module_tuple,
            (
                self.sine.frequency.base,
                self.sine.decibel.base,
                self.mixer.base,
                self.mixer.decibel.base,
            ),
        )
        self.assertEqual(
            self.cue_1.active_dependency_module_tuple,
            (self.mixer.decibel.base,),
        )
        self.assertEqual(
            self.cue_2.active_dependency_module_tuple,
            (
                self.mixer.decibel.base,
                self.sine.frequency.base,
                self.sine.decibel.base,
                self.mixer.base,
            ),
        )

    def test_active_module_tuple(self):
        self.assertEqual(
            self.cue_0.active_module_tuple,
            (
                self.sine.frequency.base,
                self.sine.decibel.base,
                self.mixer.base,
                self.mixer.decibel.base,
                self.sine.base,
            ),
        )
        self.assertEqual(
            self.cue_1.active_module_tuple,
            (self.mixer.decibel.base, self.mixer.base),
        )
