import unittest

import pyo

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


class PyoObjectMixinSwitch(walkman.unit_tests.WalkmanTestCase, unittest.TestCase):
    class MultiPyoObjectMixin(walkman.PyoObjectMixin):
        @property
        def pyo_object_tuple(self):
            return self.pyo_object, pyo.Sig(10), pyo.Sig(100)

    def setUp(self):
        super().setUp()
        self.pyo_object_mixin = self.MultiPyoObjectMixin()
        self.pyo_object_mixin_switch = walkman.PyoObjectMixinSwitch(
            self.pyo_object_mixin
        )

    def test_base(self):
        self.assertEqual(self.pyo_object_mixin_switch.base, self.pyo_object_mixin)

    def test_delegate_get(self):
        v = self.pyo_object_mixin.t = 100
        self.assertEqual(self.pyo_object_mixin_switch.t, v)

    def test_delegate_set(self):
        v = self.pyo_object_mixin_switch.t = 100
        self.assertEqual(self.pyo_object_mixin.t, v)

    def test_pyo_object_index(self):
        self.assertEqual(self.pyo_object_mixin_switch.pyo_object_index, 0)

    def test_pyo_object(self):
        # By default assigned to first pyo object.
        self.assertEqual(
            self.pyo_object_mixin.pyo_object, self.pyo_object_mixin.pyo_object
        )
        # After resetting index should point to other pyo object.
        self.pyo_object_mixin.pyo_object_index = 1
        self.assertNotEqual(
            self.pyo_object_mixin_switch.pyo_object, self.pyo_object_mixin.pyo_object
        )
        self.assertEqual(
            self.pyo_object_mixin_switch.pyo_object_tuple[1],
            self.pyo_object_mixin.pyo_object,
        )

    def test_switch(self):
        pyo_object_switch_switched = self.pyo_object_mixin_switch.switch(1)
        self.assertTrue(
            isinstance(pyo_object_switch_switched, walkman.PyoObjectMixinSwitch)
        )
        # Wrapped object should still be the same
        self.assertEqual(
            pyo_object_switch_switched._pyo_object_mixin,
            self.pyo_object_mixin_switch._pyo_object_mixin,
        )
        # But index should be different now
        self.assertNotEqual(
            pyo_object_switch_switched.pyo_object_index,
            self.pyo_object_mixin_switch.pyo_object_index,
        )


class DecibelMixinTest(unittest.TestCase):
    def test_decibel(self):
        self.assertEqual(walkman.DecibelMixin().decibel, -120)
