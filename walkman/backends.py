import dataclasses
import typing

import walkman


@dataclasses.dataclass(frozen=True)
class Backend(object):
    """Namespace for all relevant backend objects"""

    name: str
    audio_host: walkman.AudioHost
    input_provider: walkman.InputProvider
    output_provider: walkman.OutputProvider
    module_dict: walkman.ModuleDict
    cue_manager: walkman.CueManager

    def get_audio_test(
        self,
        audio_test_class: typing.Type[
            walkman.tests.AudioTest
        ] = walkman.tests.AudioRotationTest,
    ) -> walkman.tests.AudioTest:
        return audio_test_class(self.audio_host.output_channel_mapping)
