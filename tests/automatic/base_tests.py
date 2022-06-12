"""Test walkman unit test utilities"""

import pyo

import walkman


class BaseTest(walkman.unit_tests.WalkmanTestCase):
    def test_sine_audio_object(self):
        sine_audio_object = walkman.unit_tests.SineAudioObject()
        sine_audio_object.pyo_object.play()
        self.assertTrue(self.is_pyo_object_not_silent(sine_audio_object.pyo_object))

    def test_is_pyo_object_not_silent(self):
        sine = pyo.Sine()
        sine.play()
        is_pyo_object_not_silent = self.is_pyo_object_not_silent(sine)
        is_pyo_object_silent = self.is_pyo_object_silent(sine)

        self.assertTrue(is_pyo_object_not_silent)
        self.assertFalse(is_pyo_object_silent)

    def test_is_pyo_object_silent(self):
        sine = pyo.Sine(mul=0)
        sine.play()
        is_pyo_object_silent = self.is_pyo_object_silent(sine)
        self.assertTrue(is_pyo_object_silent)
