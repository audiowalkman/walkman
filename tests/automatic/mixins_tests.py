import time
import unittest

import walkman


class PlayMixinTest(unittest.TestCase):
    def test_play_and_stop(self):
        play = walkman.PlayMixin()
        self.assertFalse(play.is_playing)
        play.play()
        self.assertTrue(play.is_playing)
        play.stop()
        self.assertFalse(play.is_playing)


class NamedMixinTest(unittest.TestCase):
    class TestClass(walkman.NamedMixin):
        def __init__(self, instance_name: str):
            self._instance_name = instance_name

    def setUp(self):
        self.test = self.TestClass("instance-name")

    def test_get_class_name(self):
        self.assertEqual(self.test.get_class_name(), "test_class")

    def test_get_instance_name(self):
        self.assertEqual(self.test.get_instance_name(), "instance-name")


class PyoObjectMixin(walkman.unit_tests.WalkmanTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.pyo_object = walkman.PyoObjectMixin()

    def test_pyo_object(self):
        self.assertTrue(self.pyo_object.pyo_object)

    def test_pyo_object_or_float(self):
        self.assertTrue(self.pyo_object.pyo_object_or_float)
        self.assertEqual(
            self.pyo_object.pyo_object, self.pyo_object.pyo_object_or_float
        )

    def test_pyo_object_count(self):
        self.assertEqual(self.pyo_object.pyo_object_count, 1)

    def test_pyo_object_tuple(self):
        self.assertEqual(
            self.pyo_object.pyo_object_tuple, (self.pyo_object.pyo_object,)
        )


class DecibelMixinTest(unittest.TestCase):
    def test_decibel(self):
        self.assertEqual(walkman.DecibelMixin().decibel, -120)
