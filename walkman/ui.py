import abc
import typing

import pynput
import PySimpleGUI as sg

import walkman


class UIElement(abc.ABC):
    def __init__(
        self,
        audio_host: walkman.audio.AudioHost,
        keyboard_key: typing.Optional[pynput.keyboard.Key] = None,
    ):
        self.audio_host = audio_host
        self.keyboard_key = keyboard_key

    @property
    @abc.abstractmethod
    def gui_element(self):
        ...

    @abc.abstractmethod
    def handle_event(self, event: str, value_dict: dict):
        ...

    def handle_keyboard(self, is_pressed: bool):
        pass


class Button(UIElement):
    def __init__(self, name: str, *args, button_kwargs={}, **kwargs):
        self.name = name
        self.button_kwargs = button_kwargs
        super().__init__(*args, **kwargs)

    @property
    def gui_element(self):
        return sg.Button(self.name, **self.button_kwargs)


class StartStopButton(Button):
    def __init__(self, *args, **kwargs):
        super().__init__(
            "start_stop",
            *args,
            button_kwargs={},
            keyboard_key=pynput.keyboard.Key.space,
            **kwargs
        )
        self.is_playing = 0

    def _handle(self):
        if self.is_playing:
            self.audio_host.stop()
        else:
            self.audio_host.start()
            if not self.audio_host.sound_file_player.is_playing:
                self.audio_host.sound_file_player.play()
        self.is_playing = not self.is_playing

    def handle_event(self, event: str, _: dict):
        if event == self.name:
            self._handle()

    def handle_keyboard(self, is_pressed: bool):
        if is_pressed:
            self._handle()


class GUI(object):
    def __init__(self, ui_element_sequence: typing.Sequence[UIElement]):
        self.ui_element_tuple = tuple(ui_element_sequence)
        self.keyboard_key_to_ui_element = {
            ui_element.keyboard_key: ui_element
            for ui_element in self.ui_element_tuple
            if ui_element.keyboard_key is not None
        }

    @property
    def layout(self) -> list:
        return [[ui_element.gui_element for ui_element in self.ui_element_tuple]]

    def handle_keyboard_event(
        self, keyboard_key: pynput.keyboard.Key, is_pressed: bool
    ):
        try:
            ui_element = self.keyboard_key_to_ui_element[keyboard_key]
        except KeyError:
            pass
        return ui_element.handle_keyboard(is_pressed)

    def loop(self):
        window = sg.Window(walkman.constants.NAME, self.layout)

        keyboard_listener = pynput.keyboard.Listener(
            on_press=lambda keyboard_key: self.handle_keyboard_event(
                keyboard_key, True
            ),
            on_release=lambda keyboard_key: self.handle_keyboard_event(
                keyboard_key, False
            ),
        )
        keyboard_listener.start()

        while True:
            event, value_dict = window.read()

            # See if user wants to quit or window was closed
            if event == sg.WINDOW_CLOSED or event == "Quit":
                break

            for ui_element in self.ui_element_tuple:
                ui_element.handle_event(event, value_dict)

        window.close()


UI_CLASS_TUPLE = (StartStopButton,)


def audio_host_to_gui(audio_host: walkman.audio.AudioHost) -> GUI:
    gui = GUI([ui_class(audio_host) for ui_class in UI_CLASS_TUPLE])
    return gui
