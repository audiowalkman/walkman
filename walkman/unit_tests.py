import abc
import math
import inspect
import typing
import unittest

import pyo

import walkman


class SineAudioObject(walkman.PyoObjectMixin):
    """Minimalistic audio object useful to unit testing."""

    def __init__(self, *args, **kwargs):
        self._pyo_object = pyo.Sine(*args, **kwargs)

    @property
    def pyo_object(self) -> pyo.PyoObject:
        return self._pyo_object


class WalkmanTestCase(unittest.TestCase):
    server_args: typing.Tuple[typing.Any, ...] = tuple([])
    # XXX: buffer size is set to an extremely low value, to
    # ensure tests give precise results. If we use
    # a higher buffer size it is more likely that we get
    # rounding errors.
    server_kwargs: typing.Dict[str, typing.Any] = {"audio": "manual", "buffersize": 8}

    def process_server(self, buffer_count: int):
        for _ in range(buffer_count):
            self.server.process()

    def jump_to(self, duration_in_seconds: float):
        buffer_count = int(
            math.ceil(
                duration_in_seconds
                * self.server.getSamplingRate()
                / self.server.getBufferSize()
            )
        )
        self.process_server(buffer_count)

    def is_pyo_object_not_silent(
        self, pyo_object_to_test: pyo.PyoObject, duration_in_seconds: float = 2
    ) -> bool:
        is_active_list = []
        is_silent_tracker = pyo.Change(pyo_object_to_test)
        is_silent_writer = pyo.TrigFunc(
            is_silent_tracker, lambda: is_active_list.append(True)
        )
        is_silent_writer.play()

        self.jump_to(duration_in_seconds)
        return bool(is_active_list)

    def is_pyo_object_silent(self, *args, **kwargs) -> bool:
        return not self.is_pyo_object_not_silent(*args, **kwargs)

    def setup_module_instance(
        self,
        module_instance: walkman.Module,
        module_container: typing.Optional[walkman.ModuleContainer] = None,
    ):
        if module_container is None:
            module_container = walkman.ModuleContainer({})
        module_container.prepare_module(module_instance)
        module_instance.initialise()
        for input_module_instance in module_instance.module_input_chain:
            input_module_instance.initialise()

    def setUp(self):
        self.server = pyo.Server(*self.server_args, **self.server_kwargs).boot().start()

    def tearDown(self):
        self.server.shutdown()


class ModuleTestCase(WalkmanTestCase, abc.ABC):
    @abc.abstractmethod
    def get_module_class(self) -> typing.Type[walkman.Module]:
        ...

    def get_module_instance(
        self,
        module_class: typing.Optional[typing.Type[walkman.Module]] = None,
        **kwargs
    ) -> walkman.Module:
        if module_class is None:
            module_class = self.get_module_class()
        module_instance = module_class(**kwargs)
        self.setup_module_instance(module_instance)
        return module_instance

    def play_module_instance(self, module_instance: walkman.Module, **kwargs):
        """Wrapper to play module instance and all dependencies"""
        for depending_module_instance in module_instance.module_chain:
            depending_module_instance.play(**kwargs)
        module_instance.play(**kwargs)

    def stop_module_instance(self, module_instance: walkman.Module, wait: float = 0):
        """Wrapper to stop module instance and all dependencies"""
        for depending_module_instance in module_instance.module_chain:
            depending_module_instance.stop(wait + module_instance.fade_out_duration)
        module_instance.stop(wait)

    def test_is_playing(self):
        module_instance = self.get_module_instance()
        self.assertFalse(module_instance.is_playing)
        self.assertFalse(module_instance.pyo_object.isPlaying())

        self.play_module_instance(
            module_instance,
        )
        self.assertTrue(module_instance.is_playing)
        self.assertTrue(module_instance.pyo_object.isPlaying())

        self.stop_module_instance(
            module_instance,
        )
        self.jump_to(module_instance.fade_out_duration + 0.1)
        self.assertFalse(module_instance.is_playing)
        self.assertFalse(module_instance.pyo_object.isPlaying())

    def test_play(self):
        module_instance = self.get_module_instance()
        self.assertTrue(self.is_pyo_object_silent(module_instance.pyo_object))

        self.play_module_instance(module_instance)
        self.assertFalse(self.is_pyo_object_silent(module_instance.pyo_object))

        for pyo_object in module_instance.internal_pyo_object_list:
            self.assertTrue(pyo_object.isPlaying())

    def test_play_with_delay(self):
        module_instance = self.get_module_instance()

        self.play_module_instance(module_instance, delay=4)
        # For 4 seconds it will still be silent
        self.assertFalse(module_instance.pyo_object.isPlaying())
        self.assertTrue(self.is_pyo_object_silent(module_instance.pyo_object, 4))

        self.assertTrue(module_instance.pyo_object.isPlaying())
        self.assertFalse(self.is_pyo_object_silent(module_instance.pyo_object, 4))

    def test_play_with_duration(self):
        module_instance = self.get_module_instance()

        self.play_module_instance(module_instance, duration=4)
        self.assertFalse(self.is_pyo_object_silent(module_instance.pyo_object, 4))

        self.assertTrue(self.is_pyo_object_silent(module_instance.pyo_object, 2))

    def test_stop(self):
        module_instance = self.get_module_instance()

        self.play_module_instance(module_instance)
        self.assertFalse(self.is_pyo_object_silent(module_instance.pyo_object))

        self.stop_module_instance(
            module_instance,
        )
        self.jump_to(module_instance.fade_out_duration)
        self.assertTrue(self.is_pyo_object_silent(module_instance.pyo_object))

        for pyo_object in module_instance.internal_pyo_object_list:
            # XXX: This doesn't work for mixer objects:
            #   SystemError: <class '_pyo.InputFader_base'> returned a result with an error set
            if not isinstance(pyo_object, pyo.Mixer):
                self.assertTrue(self.is_pyo_object_silent(pyo_object))
                self.assertFalse(pyo_object.isPlaying())

    def test_stop_with_wait(self):
        module_instance = self.get_module_instance()

        self.play_module_instance(module_instance)
        self.assertFalse(self.is_pyo_object_silent(module_instance.pyo_object))

        self.stop_module_instance(module_instance, wait=4)
        self.assertFalse(
            self.is_pyo_object_silent(
                module_instance.pyo_object, 4 + module_instance.fade_out_duration
            )
        )

        self.assertTrue(self.is_pyo_object_silent(module_instance.pyo_object)) 

    def test_initialise_basic(self):
        """Ensure there are no errors when calling initialise method."""
        module_instance = self.get_module_instance(fade_out_duration=10)
        module_instance.initialise()

    def test_send_to_physical_output(self):
        module_instance = self.get_module_instance(send_to_physical_output=True)
        self.play_module_instance(module_instance)

        self.assertTrue(module_instance.pyo_object.isOutputting())

    def test_do_not_send_to_physical_output(self):
        module_instance = self.get_module_instance(send_to_physical_output=False)
        self.play_module_instance(module_instance)

        self.assertFalse(module_instance.pyo_object.isOutputting())

    def test_no_module_input_argument_in_private_initialse(self):
        # If there are any arguments with equal name as
        # names of input modules, the passed arguments of a user
        # will never reach the _initialise method because
        # of walkmans syntactic sugar (defined in initialise method
        # of base.Module). Therefore a module class should never
        # add any argument like this to its _initialise method.
        module_class = self.get_module_class()
        for parameter in inspect.signature(module_class._initialise).parameters:
            self.assertTrue(parameter not in module_class.default_module_input_dict)


class ModuleWithFaderTestCase(ModuleTestCase):
    def test_fader(self):
        """Ensure pyo_object is a combination of _pyo_object and fader"""

        module_instance = self.get_module_instance(fade_in_duration=4)

        self.play_module_instance(module_instance)
        step_size = 0.1
        for _ in range(int(module_instance.fade_out_duration / step_size)):
            current_fader_sample = module_instance.fader.get()
            current_private_pyo_object_sample = module_instance._pyo_object.get()
            self.assertEqual(
                current_fader_sample * current_private_pyo_object_sample,
                module_instance.pyo_object.get(),
            )

    def test_fade_in(self):
        module_instance = self.get_module_instance(fade_in_duration=4)

        self.play_module_instance(module_instance)
        step_size = 0.1
        last_fader_sample = -0.001
        for _ in range(int(module_instance.fade_in_duration / step_size)):
            current_fader_sample = module_instance.fader.get()
            self.assertLess(last_fader_sample, current_fader_sample)
            last_fader_sample = current_fader_sample
            self.jump_to(step_size)

    def test_fade_out(self):
        module_instance = self.get_module_instance(fade_out_duration=10)

        self.play_module_instance(module_instance)
        self.assertFalse(self.is_pyo_object_silent(module_instance.pyo_object))

        self.stop_module_instance(
            module_instance,
        )
        step_size = 0.1
        last_fader_sample = 1.001
        for _ in range(int(module_instance.fade_out_duration / step_size)):
            current_fader_sample = module_instance.fader.get()
            self.assertGreater(last_fader_sample, current_fader_sample)
            self.assertTrue(module_instance.pyo_object.isPlaying())
            self.assertFalse(
                self.is_pyo_object_silent(module_instance.pyo_object, step_size)
            )
            last_fader_sample = current_fader_sample

        self.assertFalse(module_instance.pyo_object.isPlaying())
        self.assertTrue(self.is_pyo_object_silent(module_instance.pyo_object, 2))
