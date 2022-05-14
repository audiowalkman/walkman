import abc
import dataclasses
import functools
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


class StopWatch(UIElement):
    pass


class Volume(UIElement):
    pass


class JumpToSecond(UIElement):
    pass


class Button(UIElement):
    def __init__(self, *args, button_kwargs={}, **kwargs):
        self.button_kwargs = button_kwargs
        super().__init__(*args, **kwargs)

    @functools.cached_property
    def gui_element(self) -> typing.Optional[typing.Union[list, sg.Element]]:
        return sg.Button(key=self.key_tuple[0], **self.button_kwargs)


class StartStopButton(Button):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            button_kwargs={},
            key_tuple=("start_stop",),
            keyboard_key_tuple=("space:65",),
            **kwargs,
        )
        self.is_playing = 0

    def handle_event(self, _: str, __: dict):
        if self.is_playing:
            self.audio_host.stop()
        else:
            self.audio_host.start()
            if not self.audio_host.sound_file_player.is_playing:
                self.audio_host.sound_file_player.play()
        self.is_playing = not self.is_playing


class SelectSoundFileMenu(UIElement):
    def __init__(self, *args, **kwargs):
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


class DuplicateEventError(Exception):
    def __init__(self, event: str):
        super().__init__(f"Event '{event}' has been defined twice!")


class GUI(object):
    def __init__(
        self,
        audio_host: walkman.audio.AudioHost,
        ui_element_sequence: typing.Sequence[UIElement],
        theme: str = "DarkBlack",
    ):
        sg.theme(theme)

        self.audio_host = audio_host
        self.ui_element_tuple = tuple(ui_element_sequence)
        event_to_ui_element_dict = {}
        for ui_element in self.ui_element_tuple:
            for event in ui_element.event_tuple:
                if event not in event_to_ui_element_dict:
                    event_to_ui_element_dict.update({event: ui_element})
                else:
                    raise DuplicateEventError(event)
        self.event_to_ui_element_dict = event_to_ui_element_dict

    @property
    def layout(self) -> list:
        return [
            [
                ui_element.gui_element
                for ui_element in self.ui_element_tuple
                if ui_element.gui_element
            ]
        ]

    def handle_event(self, event: str, value_dict: dict):
        try:
            ui_element = self.event_to_ui_element_dict[event]
        except KeyError:
            pass
        else:
            return ui_element.handle_event(event, value_dict)

    def loop(self):
        window = sg.Window(
            walkman.constants.NAME,
            self.layout,
            return_keyboard_events=True,
            resizable=True,
        )

        while True:
            event, value_dict = window.read()

            # See if user wants to quit or window was closed
            if event == sg.WINDOW_CLOSED or event == "Quit":
                break

            walkman.constants.LOGGER.debug(
                f"Catched event       = '{event}' \n"
                f"with value_dict     = '{value_dict}'\n."
            )
            self.handle_event(event, value_dict)

        self.audio_host.close()
        window.close()


UI_CLASS_TUPLE = (StartStopButton, SelectSoundFileMenu)


def audio_host_to_gui(audio_host: walkman.audio.AudioHost) -> GUI:
    gui = GUI(
        audio_host, [ui_class(audio_host=audio_host) for ui_class in UI_CLASS_TUPLE]
    )
    return gui
