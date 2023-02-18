import unittest

import walkman


class IntegrationTest(walkman.unit_tests.WalkmanTestCase, unittest.TestCase):
    def test_0(self):
        toml_str = rf"""
        {CONFIGURATION_HEADER}

        [configure.module.sine.0]
        send_to_physical_output = true

        [cue.0.sine.0]
        [cue.1.sine.0]
        """
        exception_list = self.do_test_run_from_toml_str(toml_str)
        self.assertFalse(exception_list)

    def test_1(self):
        toml_str = rf"""
        {CONFIGURATION_HEADER}

        [configure.module.sine.0]

        [configure.module.mixer.0]
        send_to_physical_output = true
        audio_input_0 = "sine.0.0"
        audio_input_1 = "sine.0.1"

        [cue.0.sine.0]
        """
        exception_list = self.do_test_run_from_toml_str(toml_str)
        self.assertEqual(len(exception_list), 1)
        self.assertTrue(isinstance(exception_list[0], walkman.IllegalPyoObjectIndexWarning))


CONFIGURATION_HEADER = r"""
[configure]
name            = "test"

[configure.audio]
audio           = "manual"
midi            = ""
buffer_size     = 8
"""
