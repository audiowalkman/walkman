"""Setup user interface for walkman"""

import abc
import dataclasses
import datetime
import functools
import operator
import time
import typing

import PySimpleGUI as sg

import walkman


@dataclasses.dataclass(frozen=True)
class UIElement(abc.ABC):
    audio_host: walkman.audio.AudioHost
    key_tuple: typing.Optional[str] = None
    keyboard_key_tuple: typing.Optional[str] = None

    @property
    def gui_element(self) -> typing.Optional[typing.Union[list, sg.Element]]:
        return None

    @abc.abstractmethod
    def handle_event(self, event: str, value_dict: dict):
        ...

    @functools.cached_property
    def event_tuple(self) -> typing.Tuple[str, ...]:
        event_list = []
        if self.key_tuple:
            event_list.extend(self.key_tuple)
        if self.keyboard_key_tuple:
            event_list.extend(self.keyboard_key_tuple)
        return tuple(event_list)

    def tick(self):
        # Called in every loop part
        pass


class StopWatch(UIElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, key_tuple=("stop_watch",), **kwargs)
        self._start_time = time.time()
        self._last_time: typing.Optional[float] = None
        self.stop()

    @staticmethod
    def format_time(time_to_format: float) -> str:
        _, minutes, seconds = str(datetime.timedelta(seconds=time_to_format)).split(":")
        return f"{minutes}:{seconds[:2]}"

    @property
    def formatted_duration(self) -> str:
        return StopWatch.format_time(
            self.audio_host.sound_file_player.sound_file.duration_in_seconds
        )

    @property
    def current_time(self) -> float:
        return time.time() - self._start_time

    @property
    def current_time_formatted(self) -> str:
        return StopWatch.format_time(self.current_time)

    @functools.cached_property
    def gui_element(self) -> typing.Optional[typing.Union[list, sg.Element]]:
        return sg.Text(self._get_update_string())

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
        self.gui_element.update(self._get_update_string())

    def handle_event(self, _: str, __: dict):
        self.update()

    def tick(self):
        self.update()


class Volume(UIElement):
    pass


class JumpToTime(UIElement):
    pass


class Button(UIElement):
    def __init__(self, *args, button_kwargs={}, **kwargs):
        self.button_kwargs = button_kwargs
        super().__init__(*args, **kwargs)

    @functools.cached_property
    def gui_element(self) -> typing.Optional[typing.Union[list, sg.Element]]:
        return sg.Button(key=self.key_tuple[0], **self.button_kwargs)


class StartStopButton(Button):
    def __init__(self, stop_watch: StopWatch, *args, **kwargs):
        super().__init__(
            *args,
            button_kwargs={},
            key_tuple=("start_stop",),
            keyboard_key_tuple=("space:65",),
            **kwargs,
        )
        self.is_playing = 0
        self.stop_watch = stop_watch

    def handle_event(self, _: str, __: dict):
        if self.is_playing:
            self.audio_host.stop()
            self.stop_watch.stop()
        else:
            self.audio_host.start()
            self.stop_watch.start()
            if not self.audio_host.sound_file_player.is_playing:
                self.audio_host.sound_file_player.play()
        self.is_playing = not self.is_playing

    def tick(self):
        if self.is_playing:
            self.stop_watch.tick()


class SelectSoundFileMenu(UIElement):
    def __init__(self, stop_watch: StopWatch, *args, **kwargs):
        self.stop_watch = stop_watch
        self.combo_key = "select_sound_file"

        self.left_key = "Left:113"
        self.right_key = "Right:114"

        super().__init__(
            *args,
            key_tuple=(self.combo_key,),
            keyboard_key_tuple=(self.left_key, self.right_key),
            **kwargs,
        )

        self.name_to_sound_file_dict = {
            sound_file.name: sound_file
            for sound_file in self.audio_host.sound_file_tuple
        }
        self.value_tuple = tuple(self.name_to_sound_file_dict.keys())
        self.value_count = len(self.value_tuple)

    @functools.cached_property
    def gui_element(self) -> typing.Optional[typing.Union[list, sg.Element]]:
        return sg.Combo(
            self.value_tuple,
            default_value=self.value_tuple[0],
            readonly=True,
            enable_events=True,
            key=self.combo_key,
        )

    def handle_event(self, event: str, value_dict: dict):
        sound_file_name = value_dict[self.combo_key]
        if event != self.combo_key:
            sound_file_index = self.value_tuple.index(sound_file_name)
            new_sound_file_index = (
                sound_file_index + {self.left_key: -1, self.right_key: 1}[event]
            ) % self.value_count
            sound_file_name = self.value_tuple[new_sound_file_index]
            self.gui_element.update(value=sound_file_name)
        sound_file = self.name_to_sound_file_dict[sound_file_name]
        self.audio_host.sound_file_player.sound_file = sound_file
        self.stop_watch.reset()
        self.stop_watch.stop()


class DuplicateEventError(Exception):
    def __init__(self, event: str):
        super().__init__(f"Event '{event}' has been defined twice!")


class NestedUIElement(UIElement):
    def __init__(
        self,
        audio_host,
        ui_element_sequence: typing.Sequence[UIElement],
    ):
        super().__init__(audio_host=audio_host)
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
    def event_tuple(self) -> typing.Tuple[str, ...]:
        return functools.reduce(
            operator.add,
            (ui_element.event_tuple for ui_element in self.ui_element_tuple),
        )

    def handle_event(self, event: str, value_dict: dict):
        try:
            ui_element = self.event_to_ui_element_dict[event]
        except KeyError:
            pass
        else:
            return ui_element.handle_event(event, value_dict)

    def tick(self):
        for ui_element in self.ui_element_tuple:
            ui_element.tick()

    @functools.cached_property
    def gui_element(self) -> list:
        return [
            ui_element.gui_element
            for ui_element in self.ui_element_tuple
            if ui_element.gui_element
        ]


class SoundFileControl(NestedUIElement):
    def __init__(
        self,
        audio_host,
    ):
        self.stop_watch = StopWatch(audio_host)
        self.start_stop_button = StartStopButton(self.stop_watch, audio_host)
        self.select_sound_file_menu = SelectSoundFileMenu(self.stop_watch, audio_host)

        ui_element_sequence = (
            self.stop_watch,
            self.start_stop_button,
            self.select_sound_file_menu,
        )

        super().__init__(audio_host, ui_element_sequence)

    def tick(self):
        for ui_element in self.ui_element_tuple:
            # Stop watch tick is handled in StartStopButton
            if ui_element != self.stop_watch:
                ui_element.tick()


class GUI(NestedUIElement):
    def __init__(
        self,
        audio_host: walkman.audio.AudioHost,
        ui_element_sequence: typing.Sequence[UIElement],
        theme: str = "DarkBlack",
    ):
        super().__init__(audio_host, ui_element_sequence)
        sg.theme(theme)

    @property
    def layout(self) -> list:
        return [
            [
                ui_element.gui_element
                for ui_element in self.ui_element_tuple
                if ui_element.gui_element
            ]
        ]

    def loop(self):
        window = sg.Window(
            walkman.constants.NAME,
            self.layout,
            return_keyboard_events=True,
            resizable=True,
        )

        while True:
            event, value_dict = window.read(timeout=0.85)

            # See if user wants to quit or window was closed
            if event == sg.WINDOW_CLOSED or event == "Quit":
                break

            # Ignore timeout events
            if event != sg.TIMEOUT_EVENT:
                walkman.constants.LOGGER.debug(
                    f"Catched event       = '{event}' \n"
                    f"with value_dict     = '{value_dict}'\n."
                )
                self.handle_event(event, value_dict)

            self.tick()

        self.audio_host.close()
        window.close()


UI_CLASS_TUPLE = (SoundFileControl,)
"""All used UI classes"""


def audio_host_to_gui(audio_host: walkman.audio.AudioHost) -> GUI:
    gui = GUI(
        audio_host, [ui_class(audio_host=audio_host) for ui_class in UI_CLASS_TUPLE]
    )
    return gui
