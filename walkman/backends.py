import dataclasses
import typing

import walkman


@dataclasses.dataclass(frozen=True)
class Backend(object):
    """Namespace for all relevant backend objects"""

    name: str
    audio_host: walkman.AudioHost
    module_container: walkman.ModuleContainer
    cue_manager: walkman.CueManager

    def get_audio_test(
        self,
        audio_test_class: typing.Type[
            walkman.tests.AudioTest
        ] = walkman.tests.AudioRotationTest,
    ) -> walkman.tests.AudioTest:
        return audio_test_class(self.audio_host.channel_count)

    def start(self):
        self.audio_host.play()

    def stop(self):
        self.cue_manager.current_cue.stop()
        walkman.constants.LOGGER.info("SHUTDOWN: Cue manager has been stopped.")
        self.module_container.close()
        walkman.constants.LOGGER.info("SHUTDOWN: Module container has been stopped.")
        self.audio_host.close()
        walkman.constants.LOGGER.info("SHUTDOWN: Audio host has been stopped.")
