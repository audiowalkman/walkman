"""Setup user interface for walkman"""

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


@dataclasses.dataclass(frozen=True)
class UIElement(abc.ABC):
    backend: walkman.Backend
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
        return time.time() - self._start_time

    @property
    def current_time_formatted(self) -> str:
        return StopWatch.format_time(self.current_time)

    @property
    def display_time(self) -> float:
        return self._display_time

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
        if (current_time := self.current_time) <= self.duration:
            self._display_time = current_time
            self.gui_element.update(self._get_update_string())

    def handle_event(self, _: str, __: dict):
        self.update()

    def tick(self):
        self.update()


class Volume(UIElement):
    pass


class Button(UIElement):
    def __init__(self, *args, button_kwargs={}, **kwargs):
        self.button_kwargs = button_kwargs
        super().__init__(*args, **kwargs)

    @functools.cached_property
    def gui_element(self) -> typing.Optional[typing.Union[list, sg.Element]]:
        return sg.Button(key=self.key_tuple[0], **self.button_kwargs)


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
            button_kwargs={"button_text": "JUMP TO"},
            **kwargs,
        )

    def handle_event(self, _: str, value_dict: dict):
        minutes = value_dict[self.jump_to_time_input_minutes_key]
        seconds = value_dict[self.jump_to_time_input_seconds_key]
        time = (int(minutes) * 60) + float(seconds)
        if time <= (cue_duration := self.backend.cue_manager.current_cue.duration):
            for module in self.backend.module_dict.module_tuple:
                module.jump_to(time)
            self.stop_watch.set_to(time)
            if not self.backend.audio_host.is_playing:
                self.stop_watch.stop()
            self.stop_watch.update()
        else:
            warnings.warn(TooLargeTimeWarning(time - cue_duration))


class FrozenText(UIElement):
    def __init__(self, *args, text_kwargs={}, **kwargs):
        self.text_kwargs = text_kwargs
        super().__init__(*args, **kwargs)

    @functools.cached_property
    def gui_element(self) -> typing.Optional[typing.Union[list, sg.Element]]:
        return sg.Text(**self.text_kwargs)

    def handle_event(self, _: str, __: dict):
        pass


class Title(FrozenText):
    def __init__(self, backend: walkman.Backend, *args, **kwargs):
        text_kwargs = {"text": backend.name}
        super().__init__(backend, *args, text_kwargs=text_kwargs, **kwargs)


class Logging(UIElement):
    def handle_event(self, _: str, __: dict):
        pass


class JumpToTimeInput(UIElement):
    @functools.cached_property
    def gui_element(self) -> typing.Optional[typing.Union[list, sg.Element]]:
        return sg.InputText(
            key=self.key_tuple[0], default_text="0", enable_events=False, size=(4, 1)
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
    def __init__(self, stop_watch: StopWatch, *args, **kwargs):
        super().__init__(
            *args,
            button_kwargs={"button_text": "START // STOP"},
            key_tuple=("start_stop",),
            keyboard_key_tuple=(" ",),
            **kwargs,
        )
        self.is_playing = 0
        self.stop_watch = stop_watch

    def handle_event(self, _: str, __: dict):
        if self.is_playing:
            # self.backend.audio_host.stop()
            self.backend.cue_manager.current_cue.stop()
            self.stop_watch.stop()
        else:
            self.backend.cue_manager.current_cue.play()
            self.stop_watch.start()
            # self.backend.cue_manager.current_cue.play()
        self.is_playing = not self.is_playing

    def tick(self):
        if self.is_playing:
            self.stop_watch.tick()


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
    def gui_element(self) -> typing.Optional[typing.Union[list, sg.Element]]:
        return sg.Combo(
            self.value_tuple,
            default_value=self.value_tuple[0],
            readonly=True,
            enable_events=True,
            key=self.combo_key,
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


class NestedUIElement(UIElement):
    def __init__(
        self,
        backend,
        ui_element_sequence: typing.Sequence[UIElement],
    ):
        super().__init__(backend=backend)
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
            FrozenText(backend, text_kwargs={"text": "MIN"}),
            self.jump_to_time_input_seconds,
            FrozenText(backend, text_kwargs={"text": "SEC"}),
        )

        super().__init__(backend, ui_element_sequence)


class Transport(NestedUIElement):
    def __init__(
        self,
        backend,
    ):
        self.stop_watch = StopWatch(backend)
        self.start_stop_button = StartStopButton(self.stop_watch, backend)
        self.select_cue_menu = SelectCueMenu(self.stop_watch, backend)

        ui_element_sequence = (
            self.start_stop_button,
            self.select_cue_menu,
            self.stop_watch,
        )

        super().__init__(backend, ui_element_sequence)

    def tick(self):
        for ui_element in self.ui_element_tuple:
            # Stop watch tick is handled in StartStopButton
            if ui_element != self.stop_watch:
                ui_element.tick()


class CueControl(NestedUIElement):
    def __init__(
        self,
        backend,
    ):
        self.transport = Transport(backend)
        self.jump_to_time_control = JumpToTimeControl(
            self.transport.stop_watch, backend
        )

        ui_element_sequence = (
            self.transport,
            self.jump_to_time_control,
        )

        super().__init__(backend, ui_element_sequence)


class Walkman(NestedUIElement):
    def __init__(
        self,
        backend,
    ):
        self.title = Title(backend)
        self.cue_control = CueControl(backend)

        ui_element_sequence = (
            self.cue_control,
            self.title,
        )

        super().__init__(backend, ui_element_sequence)

    @functools.cached_property
    def gui_element(self) -> list:
        return [
            [self.title.gui_element],
            self.cue_control.gui_element,
        ]


class GUI(NestedUIElement):
    def __init__(
        self,
        backend: walkman.Backend,
        ui_element_sequence: typing.Sequence[UIElement],
        theme: str = "DarkBlack",
    ):
        super().__init__(backend, ui_element_sequence)
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
            scaling=3,
        )

        self.backend.audio_host.start()

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
                try:
                    self.handle_event(event, value_dict)
                except Exception:
                    walkman.constants.LOGGER.exception(
                        f"Catched exception when handling event '{event}'"
                        f"with value_dict = '{value_dict}': "
                    )

            try:
                self.tick()
            except Exception:
                walkman.constants.LOGGER.exception(
                    "Catched exception when running tick method: "
                )

        self.backend.cue_manager.current_cue.stop()
        self.backend.module_dict.close()
        self.backend.audio_host.close()
        window.close()


UI_CLASS_TUPLE = (Walkman,)
"""All used UI classes"""


def backend_to_gui(backend: walkman.Backend) -> GUI:
    gui = GUI(backend, [ui_class(backend=backend) for ui_class in UI_CLASS_TUPLE])
    return gui
