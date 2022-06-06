import dataclasses

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
