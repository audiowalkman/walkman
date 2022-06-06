# walkman

[![Build Status](https://circleci.com/gh/audiowalkman/walkman.svg?style=shield)](https://circleci.com/gh/audiowalkman/walkman)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![PyPI version](https://badge.fury.io/py/audiowalkman.svg)](https://badge.fury.io/py/audiowalkman)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Walkman is a minimalistic, robust software to trigger (audio) cues in performance contexts.
It uses [pyo](http://ajaxsoundstudio.com/software/pyo/) as its backend and [pysimplegui](https://pypi.org/project/PySimpleGUI/) as its frontend.
It can be configured by [toml](https://toml.io/en/) files.

## Rationale

Live-electronic setups tend to be messy, difficult to maintain and difficult to test.
Furthermore many compositions with live-electronics make use of cue-based pattern, but in most of electronic music frameworks (Pd, Max/MSP, ...) no default implementation exists.
`walkman` aims to improve the situation by providing a simple, declarative configuration language to setup programs based on cues.
The actual software is implemented in Python3, can be extended in python3 and can be tested with unit tests.

## Installation

walkman is available on pip:

```bash
pip3 install audiowalkman
```

You can also use [buildout](https://buildout.readthedocs.io/) to create an isolated environment.
Please consult the [respective README](https://github.com/levinericzimmermann/walkman/blob/main/buildout/README.md) for more information.

## Configuration file

```toml
# my_composition.toml

# ##    General configurations  ## #

[configure]
name = "my composition"

[configure.audio]
sampling_rate = 44100

[configure.input]
midi_control_list = [
    # [midi control, midi channel]
    [0, 1],
    [1, 1]
]

[configure.input.channel_mapping]
# physical input -> input index
1 = 0
2 = 1
3 = [0, 1]

[configure.output.channel_mapping]
# output index -> physical output
0 = 1
1 = 2
2 = 4
3 = [5, 6]


[configure.module.sound_file_player]
replication_count = 1

[configure.module.sound_file_player.0]
# We can set values passed to '__init__'
auto_stop = false

# And we can also override the default values of
# 'initialize' method.
[configure.module.sound_file_player.0.default_dict.decibel]
value = -6
midi_control_index = 0
midi_range = [-120, 0]

# ##    Cues                  ## #

[cue.1.sound_file_player.0]
path = "jungle_rain.wav"
decibel = -12
loop = true

[cue.2]
sound_file = false

[cue.2.harmonizer.0]
# Move in 10 seconds from decibel -20 to decibel 0
decibel = [[0, -20], [10, 0]]
factor = 4
```

## Usage

```bash
walkman my_composition.toml
```
