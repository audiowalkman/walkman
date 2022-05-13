# walkman

Walkman is a minimalistic, robust software to play audio files in performance contexts.
It uses [pyo](http://ajaxsoundstudio.com/software/pyo/) as its backend and [pysimplegui](https://pypi.org/project/PySimpleGUI/) as its frontend.
It can be configured by using [toml](https://toml.io/en/) files.


## Installation

```bash
pip3 install walkman
```

## Configuration file

```toml
# nature_and_guitar_piece.toml

# Global name
name = nature-and-guitar

# Used soundfiles
[soundfile.forest]
path = "files/forest.wav"

[soundfile.ocean]
path = "files/ocean.wav"
loop = True

[soundfile.guitar-quartet]
path = "files/guitar_quartet.wav"

# Specifiy audio settings
[audio]
audio = "jack"
sampling_rate = 48000
player = disk  # alternatively: ram

[audio.channel_mapping]
# input -> output
0 = 1
1 = 2
2 = 3
3 = 4
```

## Usage

```bash
walkman nature_and_guitar_piece.toml
```
