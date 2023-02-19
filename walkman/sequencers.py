import typing
import warnings

import pyo

import walkman

__all__ = ("Sequencer", "UndefinedPropertyWarning")


class Sequencer(walkman.PlayMixin):
    """Simple sequencer to auto control a module.

    This sequencer has a 'stop_iteration_trigger' which sends a trigger
    once all events are played.

    Events need the following properties

        - is_rest
        - kwargs
        - duration

    Each of them have a fallback value (if event hasn't attribute):

        - True
        - {}
        - 1
    """

    def __init__(
        self,
        module: walkman.Module,
        event_iterator: typing.Iterable[typing.Any] = iter([]),
    ):
        self.module = module
        self.event_iterator = event_iterator
        self.step_trigger = pyo.Trig()
        self.step_caller = pyo.TrigFunc(self.step_trigger, self.step)
        self.stop_iteration_trigger = (
            pyo.Trig()
        )  # Is called when all events are finished.

        # Order matters: we first need to activate the caller and then play
        # the trigger to start the first 'step' call.
        self.internal_pyo_object_list = [self.step_caller, self.step_trigger]

    def step(self):
        # If sequencer already stopped, but step_trigger has been triggered
        # before, the step_caller may still want to run 'step'. We
        # explicitly prevent this 'step' by explicitly asking if we are really
        # still playing.
        if self.is_playing:
            self._step()

    def _step(self):
        try:
            event = next(self.event_iterator)
        except StopIteration:
            self.stop_iteration_trigger.play()
            self.stop()
        else:
            walkman.constants.LOGGER.debug(
                f"Catched event '{event}' when sequencing module '{self.module}'."
            )
            if self._catch_property(event, "is_rest", True):
                self.module.stop()
            else:
                kwargs = self._catch_property(event, "kwargs", {})
                self.module.initialise(**kwargs)
                self.module.play()
            self.step_trigger.play(delay=self._catch_property(event, "duration", 1))

    def _catch_property(self, event: typing.Any, attr: str, fallback_value: typing.Any):
        try:
            return getattr(event, attr)
        except AttributeError:
            warnings.warn(
                UndefinedPropertyWarning(self.module, event, attr, fallback_value)
            )
            return fallback_value

    # TODO: Duplication of code from 'Module._play/_stop' => should be
    # unified.

    def _play(self, duration: float = 0, delay: float = 0):
        for pyo_object in self.internal_pyo_object_list:
            pyo_object.play(delay=delay, dur=duration)

    def _stop(self, wait: float = 0):
        for pyo_object in reversed(self.internal_pyo_object_list):
            pyo_object.stop(wait=wait)

    # <= end duplication


class UndefinedPropertyWarning(Warning):
    def __init__(
        self,
        controlled_module: walkman.Module,
        event: typing.Any,
        missing_property: str,
        fallback_value: typing.Any,
    ):
        super().__init__(
            f"Problem occurred in sequencing module '{controlled_module}': "
            f"Event '{event}' misses attribute '{missing_property}'. "
            f"Walkman falls back to default value '{fallback_value}'."
        )
