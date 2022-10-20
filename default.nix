with import <nixpkgs> {};
with pkgs.python3Packages;

let

  pyo = pkgs.python39Packages.buildPythonPackage rec {
    name = "pyo";
    src = fetchFromGitHub {
      owner = "belangeo";
      repo = "pyo";
      rev = "360c429138e170e291a89da605a8dc20f837466f";
      sha256 = "sha256-CRHl+lAdiDXrXVcr9W14XE9lTJ6T7MfE8WeTMm6FpzU=";
    };
    doCheck = false;
    setupPyGlobalFlags = [
        "--use-double"
        "--use-jack"
    ];
    propagatedBuildInputs = with pkgs; [ 
      # C library dependencies for pyo
      portaudio
      libsndfile
      portmidi
      liblo
      alsa-lib
      alsa-utils
      libjack2
      flac
      libogg
      libvorbis
      # Other pyo dependencies
      python39Packages.wxPython_4_1
    ];
  };

in

  buildPythonPackage rec {
    name = "audiowalkman";
    src = fetchFromGitHub {
      owner = "audiowalkman";
      repo = "walkman";
      rev = "f30b3ea9296a584f8ba551c2f52ec74a5c804bfd";
      sha256 = "sha256-ipIHy1wvXAkOhlDj8siQycfr2vJrUqKIWEatzQL13H4=";
    };
    propagatedBuildInputs = [ 
      pyo
      python39Packages.pysimplegui
      python39Packages.click
      python39Packages.tomli
      python39Packages.jinja2
    ];
    doCheck = false;
  }
