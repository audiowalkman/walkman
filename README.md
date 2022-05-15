# walkman

[![Build Status](https://circleci.com/gh/levinericzimmermann/walkman.svg?style=shield)](https://circleci.com/gh/levinericzimmermann/walkman)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![PyPI version](https://badge.fury.io/py/audiowalkman.svg)](https://badge.fury.io/py/audiowalkman)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


Walkman is a minimalistic, robust software to play audio files in performance contexts.
It uses [pyo](http://ajaxsoundstudio.com/software/pyo/) as its backend and [pysimplegui](https://pypi.org/project/PySimpleGUI/) as its frontend.
It can be configured by using [toml](https://toml.io/en/) files.


## Installation

walkman is available on pip:

```bash
pip3 install audiowalkman
```

You can also use [buildout](https://buildout.readthedocs.io/) for creating an isolated stable environment.
Please consult the [respective README](https://github.com/levinericzimmermann/walkman/blob/main/buildout/README.md).

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
