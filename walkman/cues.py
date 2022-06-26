from __future__ import annotations

import functools
import typing
import warnings

import walkman

__all__ = ("Cue", "CueManager")


class UndefinedModuleWarning(Warning):
    def __init__(self, cue_name: str, module_name: str):
        super().__init__(f"CUE '{cue_name}': Found undefined module '{module_name}'.")


class UndefinedModuleReplicationWarning(Warning):
    def __init__(self, cue_name: str, module_name: str, undefined_replication_key: str):
        super().__init__(
            f"CUE '{cue_name}': Found undefined replication '{undefined_replication_key}' "
            f"in module '{module_name}'. WALKMAN ignored undefined replication."
        )


ModuleNameToInitialiseKwargsDict = typing.Dict[str, typing.Union[bool, dict]]


class Cue(walkman.PlayMixin, walkman.JumpToMixin):
    def __init__(
        self,
        module_container: walkman.ModuleContainer,
        name: str,
        **kwargs: typing.Dict[int, typing.Union[dict, bool]],
    ):
        self._module_container = module_container
        self._name = name
        self._module_name_to_replication_configuration = kwargs
        # We can't call '_set_duration' when initialising a Cue,
        # because the cue won't be activated yet and the modules
        # will return wrong values for 'duration'.
        self._duration = None

    def _set_duration(self):
        if self._duration is None:
            duration_list = []
            for module in self.active_module_tuple:
                duration_list.append(module.duration)
            try:
                duration = max(duration_list)
            except ValueError:
                duration = 0
            self._duration = duration

    def _initialise_module_tuple(
        self,
        module_name: str,
        module_dict: typing.Dict[str, walkman.Module],
        replication_configuration: typing.Dict[int, typing.Dict[str, typing.Any]],
    ) -> typing.Tuple[walkman.Module, ...]:
        initialised_module_list = []
        for (
            module_replication_key,
            initialise_kwargs,
        ) in replication_configuration.items():
            try:
                module = module_dict[module_replication_key]
            except KeyError:
                warnings.warn(
                    UndefinedModuleReplicationWarning(
                        self.name, module_name, module_replication_key
                    )
                )
            else:
                try:
                    initialised_module_list.extend(
                        module.initialise(**initialise_kwargs)
                    )
                # Instead of providing kwargs, we can also simply
                # write 'false', to stop modules with 'auto_stop = false'
                except TypeError:
                    if initialise_kwargs is False:
                        module.stop()

        return tuple(initialised_module_list)

    def _play(self, duration: float = 0, delay: float = 0):
        for module in self.active_module_tuple:
            module.play(duration=duration, delay=delay)

    def _stop(
        self,
        wait: float = 0,
        module_to_keep_playing_tuple: typing.Tuple[walkman.Module, ...] = tuple([]),
        apply_auto_stop: bool = False,
    ):
        def stop_module(module_to_stop: walkman.Module, wait: float = 0):
            if module_to_stop not in module_to_keep_playing_tuple:
                # Auto stop
                if not apply_auto_stop or (
                    apply_auto_stop and module_to_stop.auto_stop
                ):
                    module_to_stop.stop(wait=wait)

        for main_module in self.active_main_module_tuple:
            stop_module(main_module, wait=wait)

        for (
            dependency_module,
            main_module_tuple,
        ) in self.dependency_module_to_main_module_tuple_dict.items():
            local_wait = (
                max(main_module.fade_out_duration for main_module in main_module_tuple)
                + wait
            )
            stop_module(
                dependency_module,
                wait=local_wait,
            )

    @functools.cached_property
    def active_main_module_tuple(self) -> typing.Tuple[walkman.Module, ...]:
        active_module_list = []
        for (
            module_name,
            replication_configuration,
        ) in self.module_name_to_replication_configuration.items():
            try:
                module_dict = self._module_container[module_name]
            except KeyError:
                warnings.warn(UndefinedModuleWarning(self.name, module_name))
            else:
                for replication_key in replication_configuration.keys():
                    try:
                        active_module_list.append(module_dict[replication_key])
                    except KeyError:
                        warnings.warn(
                            UndefinedModuleReplicationWarning(
                                self.name, module_name, replication_key
                            )
                        )
        return tuple(active_module_list)

    @functools.cached_property
    def main_module_to_dependency_module_chain_dict(
        self,
    ) -> typing.Dict[walkman.Module, tuple[walkman.Module]]:
        main_module_to_dependency_module_chain_dict = {}
        for main_module in self.active_main_module_tuple:
            dependency_module_chain = main_module.module_chain
            main_module_to_dependency_module_chain_dict.update(
                {main_module: dependency_module_chain}
            )
        return main_module_to_dependency_module_chain_dict

    @functools.cached_property
    def dependency_module_to_main_module_tuple_dict(
        self,
    ) -> typing.Dict[walkman.Module, tuple[walkman.Module]]:
        dependency_module_to_main_module_tuple_dict = {}
        for dependency_module in self.active_dependency_module_tuple:
            main_module_list = []
            for (
                main_module,
                dependency_module_chain,
            ) in self.main_module_to_dependency_module_chain_dict.items():
                if dependency_module in dependency_module_chain:
                    main_module_list.append(main_module)
            dependency_module_to_main_module_tuple_dict.update(
                {dependency_module: tuple(main_module_list)}
            )
        return dependency_module_to_main_module_tuple_dict

    @functools.cached_property
    def active_dependency_module_tuple(self) -> typing.Tuple[walkman.Module, ...]:
        active_dependency_module_list = []
        for (
            dependency_module_chain
        ) in self.main_module_to_dependency_module_chain_dict.values():
            for module in dependency_module_chain:
                if module not in active_dependency_module_list:
                    active_dependency_module_list.append(module)
        return tuple(active_dependency_module_list)

    @functools.cached_property
    def active_module_tuple(self) -> typing.Tuple[walkman.Module, ...]:
        active_module_list = []
        for module in (
            self.active_dependency_module_tuple + self.active_main_module_tuple
        ):
            if module not in active_module_list:
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
    def module_name_to_replication_configuration(
        self,
    ) -> ModuleNameToInitialiseKwargsDict:
        return self._module_name_to_replication_configuration

    def activate(self):
        initialised_module_list = []
        for (
            module_name,
            replication_configuration,
        ) in self.module_name_to_replication_configuration.items():
            try:
                module_dict = self._module_container[module_name]
            except KeyError:
                warnings.warn(f"Found invalid module_name '{module_name}'!")
            else:
                initialised_module_list.extend(
                    self._initialise_module_tuple(
                        module_name, module_dict, replication_configuration
                    )
                )

        self._set_duration()

        # Finally initialise all modules which didn't receive any
        # explicit settings.
        # XXX: We have to put parameters after other modules, to ensure
        # syntactic sugar is effective.
        for module_instance in sorted(
            self.active_module_tuple,
            key=lambda module: isinstance(module, walkman.Parameter),
        ):
            if module_instance not in initialised_module_list:
                initialised_module_list.extend(module_instance.initialise())

    def deactivate(
        self, module_to_keep_playing_tuple: typing.Tuple[walkman.Module, ...]
    ):
        if self.is_playing:
            self._is_playing = False
            self._stop(
                module_to_keep_playing_tuple=module_to_keep_playing_tuple,
                apply_auto_stop=True,
            )
        return self

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
        cue_to_deactivate = self.current_cue
        is_playing = cue_to_deactivate.is_playing
        self._set_cue_index(cue_index)
        cue_to_deactivate.deactivate(self.current_cue.active_module_tuple)
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
