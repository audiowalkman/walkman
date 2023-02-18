"""Setup user interface for walkman"""

from __future__ import annotations

import abc
import dataclasses
import datetime
import functools
import operator
import time
import typing
import warnings

import PySimpleGUI as sg

import walkman


DEFAULT_FONT_TYPE = "DejaVuSansMono"
DEFAULT_FONT_SIZE = 25


class Font(str):
    def __new__(cls, font_type: str, font_size: int):
        font = str.__new__(cls, f"{font_type} {font_size}")
        font.font_type = font_type
        font.font_size = font_size
        return font

    def scale(self, percentage: float) -> Font:
        return Font(self.font_type, int(self.font_size * percentage))


DEFAULT_FONT = Font(DEFAULT_FONT_TYPE, DEFAULT_FONT_SIZE)


@dataclasses.dataclass(frozen=True)
class UIElement(abc.ABC):
    backend: walkman.Backend
    key_tuple: typing.Optional[str] = None
    keyboard_key_tuple: typing.Optional[str] = None

    @property
    def gui_element(self) -> list | sg.Element:
        return []

    @abc.abstractmethod
    def handle_event(self, event: str, value_dict: dict):
        ...

    @functools.cached_property
    def event_tuple(self) -> tuple[str, ...]:
        event_list = []
        if self.key_tuple:
            event_list.extend(self.key_tuple)
        if self.keyboard_key_tuple:
            event_list.extend(self.keyboard_key_tuple)
        return tuple(event_list)

    def tick(self, value_dict: dict):
        # Called in every loop part
        pass


@dataclasses.dataclass(frozen=True)
class SimpleUIElement(UIElement):
    element_args: tuple = tuple([])
    element_kwargs: dict = dataclasses.field(default_factory=lambda: {})
    pysimple_gui_class: typing.Optional[typing.Type[sg.Element]] = None

    @functools.cached_property
    def gui_element(self) -> list | sg.Element:
        if self.pysimple_gui_class:
            return self.get_element_instance()
        return None

    def get_element_instance(self) -> sg.Element:
        assert self.pysimple_gui_class is not None
        return self.pysimple_gui_class(*self.element_args, **self.element_kwargs)

    def handle_event(self, _: str, __: dict):
        pass


class NestedUIElement(UIElement):
    def __init__(
        self,
        backend,
        ui_element_sequence: typing.Sequence[UIElement],
        **kwargs,
    ):
        super().__init__(backend=backend, **kwargs)
        self.ui_element_tuple = tuple(ui_element_sequence)

        event_to_ui_element_dict = {}
        for ui_element in self.ui_element_tuple:
            for event in ui_element.event_tuple:
                if event not in event_to_ui_element_dict:
                    event_to_ui_element_dict.update({event: ui_element})
                else:
                    raise DuplicateEventError(event)
        self.event_to_ui_element_dict = event_to_ui_element_dict

    @functools.cached_property
    def event_tuple(self) -> tuple[str, ...]:
        return (
            functools.reduce(
                operator.add,
                (ui_element.event_tuple for ui_element in self.ui_element_tuple),
            )
            + super().event_tuple
        )

    @property
    def simple_ui_element_tuple(self) -> tuple[SimpleUIElement, ...]:
        simple_ui_element_list = []
        for ui_element in self.ui_element_tuple:
            try:
                simple_ui_element_tuple = ui_element.simple_ui_element_tuple
            except AttributeError:
                simple_ui_element_list.append(ui_element)
            else:
                simple_ui_element_list.extend(simple_ui_element_tuple)
        return tuple(simple_ui_element_list)

    def handle_event(self, event: str, value_dict: dict):
        try:
            ui_element = self.event_to_ui_element_dict[event]
        except KeyError:
            pass
        else:
            return ui_element.handle_event(event, value_dict)

    def tick(self, value_dict: dict):
        for ui_element in self.ui_element_tuple:
            ui_element.tick(value_dict)

    @functools.cached_property
    def gui_element(self) -> list:
        return [
            ui_element.gui_element
            for ui_element in self.ui_element_tuple
            if ui_element.gui_element
        ]


class StopWatch(UIElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, key_tuple=("stop_watch",), **kwargs)
        self._start_time = time.time()
        self._last_time: typing.Optional[float] = None
        self._display_time: float = 0
        self.stop()

    @staticmethod
    def format_time(time_to_format: float) -> str:
        _, minutes, seconds = str(datetime.timedelta(seconds=time_to_format)).split(":")
        return f"{minutes}:{seconds[:2]}"

    @property
    def duration(self) -> float:
        return self.backend.cue_manager.current_cue.duration

    @property
    def formatted_duration(self) -> str:
        return StopWatch.format_time(self.duration)

    @property
    def current_time(self) -> float:
        if self.duration > 0:
            return time.time() - self._start_time
        else:
            return 0

    @property
    def current_time_formatted(self) -> str:
        return StopWatch.format_time(self.current_time)

    @property
    def display_time(self) -> float:
        return self._display_time

    @functools.cached_property
    def gui_element(self) -> list | sg.Element:
        return sg.Text(self._get_update_string(), font=DEFAULT_FONT)

    def start(self):
        if self._last_time is not None:
            self.set_to(self._last_time)
            self._last_time = None

    def stop(self):
        self._last_time = self.current_time

    def reset(self):
        self._start_time = time.time()
        self.update()

    def set_to(self, time_in_seconds: float):
        self._start_time = time.time() - time_in_seconds

    def _get_update_string(self) -> str:
        return f"{self.current_time_formatted} // {self.formatted_duration}"

    def update(self):
        if (current_time := self.current_time) <= self.duration:
            self._display_time = current_time
            self.gui_element.update(self._get_update_string())

    def handle_event(self, _: str, __: dict):
        self.update()

    def tick(self, value_dict: dict):
        self.update()


class Button(SimpleUIElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, pysimple_gui_class=sg.Button, **kwargs)
        self.element_kwargs.update({"key": self.key_tuple[0]})


class TooLargeTimeWarning(Warning):
    def __init__(self, time: float):
        super().__init__(
            f"Can't jump to given time: {time} seconds longer than cue duration."
        )


class JumpToTimeButton(Button):
    def __init__(
        self,
        stop_watch: StopWatch,
        jump_to_time_input_minutes_key: str,
        jump_to_time_input_seconds_key: str,
        *args,
        **kwargs,
    ):
        self.stop_watch = stop_watch
        self.key = "jump_to_time_button"
        self.jump_to_time_input_minutes_key = jump_to_time_input_minutes_key
        self.jump_to_time_input_seconds_key = jump_to_time_input_seconds_key
        super().__init__(
            *args,
            key_tuple=(self.key,),
            element_kwargs={"button_text": "JUMP TO", "font": DEFAULT_FONT},
            **kwargs,
        )

    def handle_event(self, _: str, value_dict: dict):
        minutes = value_dict[self.jump_to_time_input_minutes_key]
        seconds = value_dict[self.jump_to_time_input_seconds_key]
        time = (int(minutes) * 60) + float(seconds)
        if time <= (cue_duration := self.backend.cue_manager.current_cue.duration):
            for module in self.backend.module_container.module_tuple:
                module.jump_to(time)
            self.stop_watch.set_to(time)
            if not self.backend.audio_host.is_playing:
                self.stop_watch.stop()
            self.stop_watch.update()
        else:
            warnings.warn(TooLargeTimeWarning(time - cue_duration))


class FrozenText(SimpleUIElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, pysimple_gui_class=sg.Text, **kwargs)


class Popup(SimpleUIElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, pysimple_gui_class=sg.Popup, **kwargs)
        self.popup = None

    @functools.cached_property
    def gui_element(self) -> list | sg.Element:
        return []

    def handle_event(self, _: str, value_dict: dict):
        self.popup = self.get_element_instance()


class Window(SimpleUIElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, pysimple_gui_class=sg.Window, **kwargs)


class ModalWindow(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.element_kwargs.update({"modal": True})


class TitleBar(SimpleUIElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, pysimple_gui_class=sg.Titlebar, **kwargs)


class Output(SimpleUIElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, pysimple_gui_class=sg.Output, **kwargs)


class Slider(SimpleUIElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, pysimple_gui_class=sg.Slider, **kwargs)


class Title(TitleBar):
    def __init__(self, backend: walkman.Backend, *args, **kwargs):
        element_kwargs = {
            "title": f"{walkman.constants.NAME}: {backend.name}",
            "icon": walkman.constants.ICON,
            "font": DEFAULT_FONT,
        }
        super().__init__(backend, *args, element_kwargs=element_kwargs, **kwargs)


class Menu(SimpleUIElement):
    sg.MENU_SHORTCUT_CHARACTER = "&"

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            pysimple_gui_class=sg.Menu,
            element_kwargs={"font": DEFAULT_FONT.scale(0.8)},
            **kwargs,
        )


HELP_KEY = "Help"
ABOUT_KEY = "About"
DEBUG_KEY = "Debug"
CHANNEL_TEST_KEY = "Test audio & midi"
ROTATION_CHANNEL_TEST_KEY = "Launch rotation test"
MIDI_INPUT_TEST_KEY = "Launch midi input test"


class Debug(UIElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, key_tuple=(DEBUG_KEY,), **kwargs)

    def handle_event(self, _: str, value_dict: dict):
        sg.show_debugger_window()


class Logger(Output):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            element_kwargs={"size": (120, 20)},
            **kwargs,
        )


class WalkmanMenu(Menu):
    def __init__(self, backend: walkman.Backend, *args, **kwargs):
        super().__init__(
            backend,
            *args,
            element_args=(
                [
                    [
                        f"&{CHANNEL_TEST_KEY}",
                        [
                            ROTATION_CHANNEL_TEST_KEY,
                            "Launch individual channel test",
                            MIDI_INPUT_TEST_KEY,
                        ],
                    ],
                    [f"&{HELP_KEY}", [ABOUT_KEY, DEBUG_KEY]],
                ],
            ),
            **kwargs,
        )


class Logging(UIElement):
    def handle_event(self, _: str, __: dict):
        pass


class AboutText(Popup):
    def __init__(self, backend: walkman.Backend, *args, **kwargs):
        element_args = (
            f"Welcome to {walkman.constants.NAME}. "
            "This is a software for audio cue control. "
            "Please consult the github page "
            "for futher information at "
            "https://github.com/audiowalkman/walkman.",
        )
        super().__init__(
            backend,
            *args,
            element_args=element_args,
            element_kwargs={"font": DEFAULT_FONT.scale(0.7)},
            key_tuple=(ABOUT_KEY,),
            **kwargs,
        )


class JumpToTimeInput(UIElement):
    @functools.cached_property
    def gui_element(self) -> list | sg.Element:
        return sg.InputText(
            key=self.key_tuple[0],
            default_text="0",
            enable_events=False,
            size=(4 * 3, 1 * 3),
            font=DEFAULT_FONT,
        )

    def handle_event(self, _: str, __: dict):
        pass


class JumpToTimeInputMinutes(JumpToTimeInput):
    def __init__(self, *args, **kwargs):
        self.key = "jump_to_time_input_minutes"
        super().__init__(*args, key_tuple=(self.key,), **kwargs)


class JumpToTimeInputSeconds(JumpToTimeInput):
    def __init__(self, *args, **kwargs):
        self.key = "jump_to_time_input_seconds"
        super().__init__(*args, key_tuple=(self.key,), **kwargs)


class StartStopButton(Button):
    def __init__(
        self,
        *args,
        key_tuple=("start_stop",),
        element_kwargs={
            "button_text": "START // STOP",
            "font": DEFAULT_FONT,
        },
        **kwargs,
    ):
        super().__init__(
            *args,
            key_tuple=key_tuple,
            element_kwargs=element_kwargs,
            keyboard_key_tuple=(" ", "space:65"),
            **kwargs,
        )
        self.is_playing = 0

    def play(self):
        self.gui_element.update(button_color="red")

    def stop(self):
        self.gui_element.update(button_color="white")

    def handle_event(self, _: str, __: dict):
        if self.is_playing:
            self.stop()
        else:
            self.play()
        self.is_playing = not self.is_playing


class WalkmanStartStopButton(StartStopButton):
    def __init__(self, stop_watch: StopWatch, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
        )
        self.stop_watch = stop_watch

    def play(self):
        super().play()
        self.gui_element.update(button_color="red")
        self.backend.cue_manager.current_cue.play()
        self.stop_watch.start()

    def stop(self):
        super().stop()
        self.backend.cue_manager.current_cue.stop()
        self.stop_watch.stop()

    def tick(self, value_dict: dict):
        if self.is_playing:
            self.stop_watch.tick(value_dict)


class AudioTestStartStopButton(StartStopButton):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
        )
        self.audio_test = None

    def play(self):
        super().play()
        if self.audio_test:
            self.audio_test.play()

    def stop(self):
        super().stop()
        if self.audio_test:
            self.audio_test.stop()


class VolumeSlider(Slider):
    def __init__(
        self,
        *args,
        default_value: typing.Optional[float] = -12,
        key_suffix: str = "",
        volume_range: tuple[float, float] = (-120, 12),
        resolution: float = 0.25,
        audio_object_with_decibel: typing.Optional[walkman.DecibelMixin] = None,
        orientation: str = "horizontal",
        tooltip: typing.Optional[str] = None,
        **kwargs,
    ):
        self.key = f"volume_{key_suffix}"
        super().__init__(
            *args,
            element_kwargs={
                "default_value": default_value,
                "font": DEFAULT_FONT,
                "key": self.key,
                "range": volume_range,
                "resolution": resolution,
                "orientation": orientation,
                "enable_events": True,
                "tooltip": tooltip,
            },
            **kwargs,
        )
        self.audio_object_with_decibel = audio_object_with_decibel

    def set_decibel(self, value_dict: dict):
        if (
            self.audio_object_with_decibel
            and value_dict
            and (decibel := value_dict.get(self.key, None))
        ):
            self.audio_object_with_decibel.decibel = decibel

    def handle_event(self, event: str, value_dict: dict):
        self.set_decibel(value_dict)

    def tick(self, value_dict: dict):
        self.set_decibel(value_dict)


class SelectCueMenu(UIElement):
    def __init__(self, stop_watch: StopWatch, *args, **kwargs):
        self.stop_watch = stop_watch
        self.combo_key = "select_cue"

        self.left_key = "Left:113"
        self.right_key = "Right:114"

        super().__init__(
            *args,
            key_tuple=(self.combo_key,),
            keyboard_key_tuple=(self.left_key, self.right_key),
            **kwargs,
        )

        self.value_tuple = self.backend.cue_manager.cue_name_tuple
        self.value_count = len(self.value_tuple)

    @functools.cached_property
    def gui_element(self) -> list | sg.Element:
        return sg.Combo(
            self.value_tuple,
            default_value=self.value_tuple[0],
            readonly=True,
            enable_events=True,
            key=self.combo_key,
            font=DEFAULT_FONT,
        )

    def handle_event(self, event: str, value_dict: dict):
        cue_name = value_dict[self.combo_key]
        if event == self.combo_key:
            new_cue_index = self.backend.cue_manager.cue_name_tuple.index(cue_name)
        else:
            cue_index = self.value_tuple.index(cue_name)
            # When current duration != 0 and one left key: jump to beginning
            # of current cue.
            if event == self.left_key and int(self.stop_watch.display_time) != 0:
                new_cue_index = cue_index
            else:
                new_cue_index = (
                    cue_index + {self.left_key: -1, self.right_key: 1}[event]
                ) % self.value_count
            cue_name = self.value_tuple[new_cue_index]
            self.gui_element.update(value=cue_name)

        self.backend.cue_manager.jump_to_cue(new_cue_index)
        self.stop_watch.reset()
        self.stop_watch.stop()


class DuplicateEventError(Exception):
    def __init__(self, event: str):
        super().__init__(f"Event '{event}' has been defined twice!")


class JumpToTimeControl(NestedUIElement):
    def __init__(
        self,
        stop_watch: StopWatch,
        backend,
    ):
        self.jump_to_time_input_minutes = JumpToTimeInputMinutes(backend)
        self.jump_to_time_input_seconds = JumpToTimeInputSeconds(backend)
        self.jump_to_time_button = JumpToTimeButton(
            stop_watch,
            self.jump_to_time_input_minutes.key,
            self.jump_to_time_input_seconds.key,
            backend,
        )

        ui_element_sequence = (
            self.jump_to_time_button,
            self.jump_to_time_input_minutes,
            FrozenText(
                backend, element_kwargs={"text": "MIN", "font": DEFAULT_FONT.scale(0.5)}
            ),
            self.jump_to_time_input_seconds,
            FrozenText(
                backend, element_kwargs={"text": "SEC", "font": DEFAULT_FONT.scale(0.5)}
            ),
        )

        super().__init__(backend, ui_element_sequence)


class Transport(NestedUIElement):
    def __init__(
        self,
        backend,
    ):
        self.stop_watch = StopWatch(backend)
        self.start_stop_button = WalkmanStartStopButton(self.stop_watch, backend)
        self.select_cue_menu = SelectCueMenu(self.stop_watch, backend)

        ui_element_sequence = (
            self.start_stop_button,
            self.select_cue_menu,
            self.stop_watch,
        )

        super().__init__(backend, ui_element_sequence)

    def tick(self, value_dict: dict):
        for ui_element in self.ui_element_tuple:
            # Stop watch tick is handled in StartStopButton
            if ui_element != self.stop_watch:
                ui_element.tick(value_dict)


class CueControl(NestedUIElement):
    def __init__(
        self,
        backend,
    ):
        self.transport = Transport(backend)
        self.jump_to_time_control = JumpToTimeControl(
            self.transport.stop_watch, backend
        )
        self.volume_slider = VolumeSlider(
            backend,
            key_suffix="master",
            audio_object_with_decibel=backend.audio_host,
            tooltip="Set volume of master output",
        )

        ui_element_sequence = (
            self.transport,
            self.jump_to_time_control,
            self.volume_slider,
        )

        super().__init__(backend, ui_element_sequence)


class LoggerWindow(NestedUIElement):
    def __init__(
        self,
        backend,
    ):
        self.logger_text = FrozenText(
            backend, element_kwargs={"text": "Logger", "font": DEFAULT_FONT.scale(1)}
        )
        self.logger = Logger(backend)
        ui_element_sequence = (
            self.logger_text,
            self.logger,
        )

        walkman.constants.LOGGER.window_logger_handler.logger_window = (
            self.logger.gui_element
        )

        super().__init__(backend, ui_element_sequence)

    @functools.cached_property
    def gui_element(self) -> list:
        return [
            [self.logger_text.gui_element],
            self.logger.gui_element,
        ]


class Walkman(NestedUIElement):
    def __init__(
        self,
        backend,
    ):
        self.menu = WalkmanMenu(backend)
        self.about_text = AboutText(backend)
        self.audio_rotation_test = AudioRotationTest(backend)
        self.midi_input_test = MidiInputTest(backend)
        self.cue_control = CueControl(backend)
        self.debug = Debug(backend)
        self.logger_window = LoggerWindow(backend)

        ui_element_sequence = (
            self.cue_control,
            self.menu,
            self.about_text,
            self.audio_rotation_test,
            self.midi_input_test,
            self.debug,
            self.logger_window,
        )

        super().__init__(backend, ui_element_sequence)

    @functools.cached_property
    def gui_element(self) -> list:
        return [
            [self.menu.gui_element],
            self.cue_control.gui_element,
            self.about_text.gui_element,
            self.logger_window.gui_element,
        ]


class NestedWindow(NestedUIElement):
    def __init__(
        self,
        backend: walkman.Backend,
        ui_element_sequence: typing.Sequence[UIElement],
        window_class: typing.Type[Window] = Window,
        window_name: str = walkman.constants.NAME,
        window_kwargs: dict[str, typing.Any] = {},
        **kwargs,
    ):
        window_kwargs.update(
            {
                "resizable": True,
                "return_keyboard_events": True,
            }
        )
        super().__init__(backend, ui_element_sequence, **kwargs)
        self.window_name = window_name
        self.window_kwargs = window_kwargs
        self.window_class = window_class

    def set_window(self):
        # Initialisation of windows has to be dynamic (so
        # when closing and reopening windows we don't use the same
        # layout, which is prohibited).
        self.window = self.window_class(
            self.backend,
            element_args=(self.window_name, self.gui_element),
            element_kwargs=self.window_kwargs,
        )

    def before_loop(self):
        self.set_window()
        self.pysimple_gui_window = self.window.get_element_instance()
        self.pysimple_gui_window.finalize()

    def after_loop(self):
        self.pysimple_gui_window.close()
        del self.pysimple_gui_window
        for ui_element in self.simple_ui_element_tuple + (self,):
            try:
                del ui_element.gui_element
            except AttributeError:
                pass

    def read(self, pysimple_gui_window: sg.Window) -> bool:
        shall_break = False
        event, value_dict = pysimple_gui_window.read(timeout=1000)

        # See if user wants to quit or window was closed
        if event == sg.WINDOW_CLOSED or event == "Quit":
            shall_break = True

        # Ignore timeout events
        if event != sg.TIMEOUT_EVENT:
            walkman.constants.LOGGER.debug(
                f"Catched event       = '{event}' \n"
                f"with value_dict     = '{value_dict}'\n."
            )
            try:
                self.handle_event(event, value_dict)
            except Exception:
                walkman.constants.LOGGER.exception(
                    f"Catched exception when handling event '{event}'"
                    f"with value_dict = '{value_dict}': "
                )

        try:
            self.tick(value_dict)
        except Exception:
            walkman.constants.LOGGER.exception(
                "Catched exception when running tick method: "
            )

        return shall_break

    def loop(self):
        self.before_loop()
        while True:
            shall_break = self.read(self.pysimple_gui_window)
            if shall_break:
                break
        self.after_loop()


class AudioRotationTest(NestedWindow):
    def __init__(self, backend: walkman.Backend, *args, **kwargs):
        self.start_stop_button = AudioTestStartStopButton(backend)
        self.volume_slider = VolumeSlider(backend, key_suffix="rotation_test")
        ui_element_tuple = (self.start_stop_button, self.volume_slider)
        super().__init__(
            backend,
            ui_element_tuple,
            window_class=ModalWindow,
            key_tuple=(ROTATION_CHANNEL_TEST_KEY,),
            window_kwargs={"finalize": True},
            **kwargs,
        )
        self.event_tuple = self.key_tuple

    def before_loop(self):
        super().before_loop()
        self.audio_rotation_test = self.backend.get_audio_test(
            audio_test_class=walkman.tests.AudioRotationTest
        )
        self.start_stop_button.audio_test = self.audio_rotation_test
        self.volume_slider.audio_object_with_decibel = self.audio_rotation_test

    def after_loop(self):
        super().after_loop()
        self.audio_rotation_test.close()
        self.start_stop_button.audio_rotation_test = None
        del self.audio_rotation_test

    def handle_event(self, event: str, value_dict: dict):
        if event == ROTATION_CHANNEL_TEST_KEY:
            self.loop()
        else:
            super().handle_event(event, value_dict)

    @property
    def gui_element(self) -> list:
        return [
            [self.start_stop_button.gui_element],
            [self.volume_slider.gui_element],
        ]


class MidiInputTest(NestedWindow):
    def __init__(self, backend: walkman.Backend, *args, **kwargs):
        self.title = FrozenText(
            backend,
            element_args=("MIDI Input Test",),
            element_kwargs={"font": DEFAULT_FONT},
        )
        self.midi_output = Output(
            backend,
            element_kwargs={"size": (120, 20)},
        )
        ui_element_tuple = (
            self.title,
            self.midi_output,
        )
        super().__init__(
            backend,
            ui_element_tuple,
            window_class=ModalWindow,
            key_tuple=(MIDI_INPUT_TEST_KEY,),
            window_kwargs={"finalize": True},
            **kwargs,
        )
        self.event_tuple = self.key_tuple

    def before_loop(self):
        super().before_loop()
        self.midi_input_test = walkman.tests.MidiInputTest(self.midi_output.gui_element)

    def after_loop(self):
        super().after_loop()
        self.midi_input_test.close()
        del self.midi_input_test

    def handle_event(self, event: str, value_dict: dict):
        if event == MIDI_INPUT_TEST_KEY:
            self.loop()
        else:
            super().handle_event(event, value_dict)

    @property
    def gui_element(self) -> list:
        return [
            [self.title.gui_element],
            [self.midi_output.gui_element],
        ]


class GUI(NestedWindow):
    def __init__(
        self,
        backend: walkman.Backend,
        *args,
        theme: str = "DarkBlack",
        **kwargs,
    ):
        sg.theme(theme)
        super().__init__(
            backend,
            *args,
            window_name=backend.name,
            window_kwargs={"icon": walkman.constants.ICON},
            **kwargs,
        )

    def before_loop(self):
        super().before_loop()
        self.backend.start()
        walkman.constants.LOGGER.window_logger_handler.update_output()

    def after_loop(self):
        super().after_loop()
        self.backend.stop()


UI_CLASS_TUPLE = (Walkman,)
"""All used UI classes"""


def backend_to_gui(backend: walkman.Backend) -> GUI:
    gui = GUI(backend, [ui_class(backend=backend) for ui_class in UI_CLASS_TUPLE])
    return gui
