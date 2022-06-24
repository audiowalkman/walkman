import setuptools  # type: ignore

version = {}
with open("walkman/version.py") as fp:
    exec(fp.read(), version)

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="audiowalkman",
    version=version["__version__"],
    license="GPL",
    description="play audio files in performance contexts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Levin Eric Zimmermann",
    author_email="levin.eric.zimmermann@posteo.eu",
    setup_requires=[],
    install_requires=[
        # for audio
        "pyo>=1.0.3",
        # for GUI
        "PySimpleGUI>=4.60.0, <5.0.0",
        # for CLI
        "click>=8.1.3, <9.0.0",
        # to read config files
        "tomli>=2.0.1, <3.0.0",
        # to parse jinja2 syntax in config files
        "jinja2>=3.1.2, <4.0.0",
    ],
    packages=[
        package for package in setuptools.find_packages() if package[:5] != "tests"
    ],
    python_requires=">=3.8",
    extras_require={"testing": ["nose"]},
    entry_points={"console_scripts": ["walkman=walkman.__main__:main"]},
)
