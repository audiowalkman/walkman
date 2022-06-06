import functools
import typing

import walkman

ModuleNameToInitialiseKwargsDict = typing.Dict[str, typing.Union[bool, dict]]


class Cue(object):
    def __init__(
        self,
        module_dict: walkman.ModuleDict,
        name: str,
        **kwargs: typing.Union[dict, bool]
    ):
        self._is_playing = False
        self._module_dict = module_dict
        self._name = name
        self._module_name_to_initialise_kwargs_dict = kwargs
        self._duration = None

    @functools.cached_property
    def active_module_name_set(self) -> typing.Set[str]:
        return set(
            module_name
            for module_name in self._module_name_to_initialise_kwargs_dict.keys()
            if module_name in self._module_dict
        )

    @functools.cached_property
    def active_module_tuple(self) -> typing.Tuple[walkman.Module, ...]:
        return tuple(
            self._module_dict[module_name]
            for module_name in self.active_module_name_set
        )

    @functools.cached_property
    def name(self) -> str:
        return self._name

    @property
    def duration(self) -> float:
        if self._duration:
            return self._duration
        return 0

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def module_name_to_initialise_kwargs_dict(self) -> ModuleNameToInitialiseKwargsDict:
        return self._module_name_to_initialise_kwargs_dict

    def play(self):
        for module in self.active_module_tuple:
            module.play()
        self._is_playing = True

    def stop(self):
        for module in self.active_module_tuple:
            module.stop()
        self._is_playing = False

    def activate(self):
        for module_name, module in self._module_dict.items():
            try:
                initialise_kwargs = self.module_name_to_initialise_kwargs_dict[
                    module_name
                ]
            except KeyError:
                if module.auto_stop:
                    module.stop()
            else:
                try:
                    module.initialise(**initialise_kwargs)
                except TypeError:
                    if initialise_kwargs is False:
                        module.stop()

        if self._duration is None:
            duration_list = [
                self._module_dict[module_name].duration
                for module_name in self.active_module_name_set
            ]
            try:
                duration = max(duration_list)
            except ValueError:
                duration = 0
            self._duration = duration

    def jump_to(self, time_in_seconds: float):
        for module in self.active_module_tuple:
            module.jump_to(time_in_seconds)


class CueManager(object):
    def __init__(self, cue_tuple: typing.Tuple[Cue, ...]):
        self._cue_index = 0
        self._cue_tuple = cue_tuple
        self._cue_count = len(cue_tuple)

        self._active_cue_index = None
        self._activate_cue()

        self._cue_name_tuple = tuple(cue.name for cue in self._cue_tuple)

    def _set_cue_index(self, index: int):
        self._cue_index = index % self._cue_count

    def _activate_cue(self):
        if self._active_cue_index != self.current_cue_index:
            self.current_cue.activate()
            self._active_cue_index = self.current_cue_index
        self.current_cue.jump_to(0)

    def _move_and_activate_cue(self, cue_index: int):
        if is_playing := self.current_cue.is_playing:
            self.current_cue.stop()
        self._set_cue_index(cue_index)
        self._activate_cue()
        if is_playing:
            self.current_cue.play()

    def __getitem__(self, index_or_key: typing.Union[str, int]) -> Cue:
        if isinstance(index_or_key, str):
            index = self._cue_name_tuple.index(index_or_key)
        else:
            index = index_or_key
        return self._cue_tuple[index]

    @property
    def cue_name_tuple(self) -> typing.Tuple[str, ...]:
        return self._cue_name_tuple

    @property
    def active_module_tuple(self):
        return self.current_cue.active_module_tuple

    @property
    def cue_count(self):
        return self._cue_count

    @property
    def current_cue_index(self):
        return self._cue_index

    @property
    def current_cue(self) -> Cue:
        return self._cue_tuple[self._cue_index]

    def move_to_previous_cue(self):
        self._move_and_activate_cue(self._cue_index - 1)

    def move_to_next_cue(self):
        self._move_and_activate_cue(self._cue_index + 1)

    def jump_to_cue(self, cue_index: int):
        self._move_and_activate_cue(cue_index)
