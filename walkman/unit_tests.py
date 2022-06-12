import time
import typing
import unittest

import pyo

import walkman


class SineAudioObject(walkman.SimpleAudioObject):
    """Minimalistic audio object useful to unit testing."""

    def __init__(self, *args, **kwargs):
        self._pyo_object = pyo.Sine(*args, **kwargs)

    @property
    def pyo_object(self) -> pyo.PyoObject:
        return self._pyo_object


class WalkmanTestCase(unittest.TestCase):
    server_args: typing.Tuple[typing.Any, ...] = tuple([])
    server_kwargs: typing.Dict[str, typing.Any] = {"audio": "manual"}

    def process_server(self, buffer_count: int):
        for _ in range(buffer_count):
            self.server.process()

    def is_pyo_object_not_silent(self, pyo_object_to_test: pyo.PyoObject) -> bool:
        is_active_list = []
        is_silent_tracker = pyo.Thresh(pyo_object_to_test, threshold=0, dir=0)
        is_silent_writer = pyo.TrigFunc(
            is_silent_tracker, lambda: is_active_list.append(True)
        )
        is_silent_writer.play()

        self.process_server(4)
        return bool(is_active_list)

    def is_pyo_object_silent(self, pyo_object_to_test: pyo.PyoObject) -> bool:
        return not self.is_pyo_object_not_silent(pyo_object_to_test)

    def setUp(self):
        self.server = pyo.Server(*self.server_args, **self.server_kwargs).boot().start()

    def tearDown(self):
        self.server.shutdown()
