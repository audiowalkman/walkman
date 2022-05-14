# walkman - buildout

The buildout file here aims to use [buildout](https://buildout.readthedocs.io/) for an easy reproducable setup of walkman.
Performances of electronic music tend to be messy and hard to maintain.
The buildout scripts tries to improve the situation.

### Example buildout

```buildout
[buildout]
extends = https://github.com/levinericzimmermann/walkman/raw/main/buildout/buildout.cfg
parts += cdd

[cdd]
<= walkman-binary
configuration-file-path = cdd.toml
```
