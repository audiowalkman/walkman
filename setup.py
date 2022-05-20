import setuptools  # type: ignore

version = {}
with open("walkman/version.py") as fp:
    exec(fp.read(), version)

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="audiowalkman",
    version=version['__version__'],
    license="GPL",
    description="play audio files in performance contexts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Levin Eric Zimmermann",
    author_email="levin.eric.zimmermann@posteo.eu",
    packages=["walkman"],
    setup_requires=[],
    install_requires=[
        # for audio
        "pyo==1.0.4",
        # for GUI
        "PySimpleGUI==4.60.0",
        # for CLI
        "click==8.1.3",
        # to read config files
        "tomli==2.0.1",
        # to convert smaller channel sound files
        # to larger channel sound files
        "SoundFile==0.10.3.post1",
        "numpy==1.22.3",
    ],
    extras_require={"testing": ["nose"]},
    python_requires="==3.8",
    entry_points={"console_scripts": ["walkman=walkman.__main__:main"]},
)
