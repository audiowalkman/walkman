import walkman


class CueTest(walkman.unit_tests.WalkmanTestCase):
    def setUp(self):
        super().setUp()
        self.module_container = walkman.ModuleContainer(
            {
                "sine": {"modern": walkman.Sine()},
                "mixer": {"master_output": walkman.Mixer(send_to_physical_output=True)},
            }
        )
        module_instance_list = []
        for replication_key_to_module in self.module_container.values():
            for module_instance in replication_key_to_module.values():
                module_instance_list.append(module_instance)
        for module_instance in module_instance_list:
            self.setup_module_instance(module_instance, self.module_container)

        self.cue_0 = walkman.Cue(
            self.module_container, "1", sine={"modern": {"frequency": 99}}
        )

    def test_active_main_module_tuple(self):
        self.assertEqual(
            self.cue_0.active_main_module_tuple,
            (self.module_container["sine"]["modern"],),
        )

    def test_active_dependency_module_tuple(self):
        self.assertEqual(
            self.cue_0.active_dependency_module_tuple,
            (
                self.module_container["sine"]["modern"].frequency,
                self.module_container["sine"]["modern"].decibel,
            ),
        )
