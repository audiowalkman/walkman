import functools
import typing
import warnings

import walkman

ModuleNameToInitialiseKwargsDict = typing.Dict[str, typing.Union[bool, dict]]


class Cue(object):
    def __init__(
        self,
        module_dict: walkman.ModuleDict,
        name: str,
        **kwargs: typing.Dict[int, typing.Union[dict, bool]],
    ):
        self._is_playing = False
        self._module_dict = module_dict
        self._name = name
        self._module_name_to_replication_configuration = kwargs
        # We can't call '_set_duration' when initialising a Cue,
        # because the cue won't be activated yet and the modules
        # will return wrong values for 'duration'.
        self._duration = None

    def _set_duration(self):
        if self._duration is None:
            duration_list = []
            for module_name in self.active_module_name_set:
                for module in self._module_dict[module_name]:
                    duration_list.append(module.duration)
            try:
                duration = max(duration_list)
            except ValueError:
                duration = 0
            self._duration = duration

    def _initialise_module_tuple(
        self,
        module_tuple: typing.Tuple[walkman.Module, ...],
        replication_configuration: typing.Dict[int, typing.Dict[str, typing.Any]],
    ):
        for (
            module_replication_index,
            initialise_kwargs,
        ) in replication_configuration.items():
            try:
                module = module_tuple[module_replication_index]
            except IndexError:
                warnings.warn(
                    f"Module {module_name} only has {len(module_tuple)} "
                    f"replications. Replication '{module_replication_index}'"
                    f" doesn't exist."
                )
            else:
                try:
                    module.initialise(**initialise_kwargs)
                # Instead of providing kwargs, we can also simply
                # write 'false', to stop modules with 'auto_stop = false'
                except TypeError:
                    if initialise_kwargs is False:
                        module.stop()

    @functools.cached_property
    def active_module_name_set(self) -> typing.Set[str]:
        return set(
            module_name
            for module_name in self.module_name_to_replication_configuration.keys()
            if module_name in self._module_dict
        )

    @functools.cached_property
    def active_module_tuple(self) -> typing.Tuple[walkman.Module, ...]:
        active_module_list = []
        for module_name in self.active_module_name_set:
            for module in self._module_dict[module_name]:
                active_module_list.append(module)
        return tuple(active_module_list)

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
    def module_name_to_replication_configuration(
        self,
    ) -> ModuleNameToInitialiseKwargsDict:
        return self._module_name_to_replication_configuration

    def play(self):
        for module in self.active_module_tuple:
            module.play()
        self._is_playing = True

    def stop(self):
        for module in self.active_module_tuple:
            module.stop()
        self._is_playing = False

    def activate(self):
        for module_name, module_tuple in self._module_dict.items():
            try:
                replication_configuration = (
                    self.module_name_to_replication_configuration[module_name]
                )
            except KeyError:
                for module in module_tuple:
                    if module.auto_stop:
                        module.stop()
            else:
                self._initialise_module_tuple(module_tuple, replication_configuration)

            self._set_duration()

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
