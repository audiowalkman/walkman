with import <nixpkgs> {};
with pkgs.python310Packages;

let

  pyo = buildPythonPackage rec {
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
      python310Packages.wxPython_4_1
    ];
  };

in

  buildPythonPackage rec {
    name = "audiowalkman";
    src = fetchFromGitHub {
      owner = "audiowalkman";
      repo = "walkman";
      rev = "8fa9c6d3108190bbcf17650e7cb9173af3931452";
      sha256 = "sha256-ZfxNO+8QVRr1PqfD26jPUVLD1iBOcYqgUbebCxz602U=";
    };
    propagatedBuildInputs = with pkgs.python310Packages; [ 
      pyo
      pysimplegui
      click
      tomli
      jinja2
    ];
    checkInputs = [
      python310Packages.pytest
    ];
    doCheck = true;
    checkPhase = ''
      runHook preCheck
      pytest
      runHook postCheck
    '';
  }
