# Module documentation

## Mixer

```toml
[configure.module.mixer.X]
audio_input_X                   = string

[cue.X.mixer.X.audio_input_X_channel_mapping]
INPUT_CHANNEL_INDEX             = list[int]     (output channel index list)
```

### Example

```toml
[configure.module.mixer.master]
send_to_physical_output         = true
audio_input_0                   = "sine.0"
audio_input_1                   = "sine.1"

[configure.module.mixer.default_dict.audio_input_0_channel_mapping]
# Send mono signal to two channels
0                               = [0, 1]

[configure.module.mixer.default_dict.audio_input_1_channel_mapping]
# Send mono signal only to right channel.
0                               = [1]

# We have two cues. Mixer starts automatically.
[cue.0.sine.0]
[cue.0.sine.1]

[cue.1.sine.0]
```
