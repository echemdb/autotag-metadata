# Installation

## Windows

The latest installer and/or executable can be found in the [release section](https://github.com/echemdb/autotag-metadata/releases).

Launch the program from the start menu.

```{note}
Multiple instances of the program can be launched to watch different folders for file creations.
```

## From a Terminal

### Requirements

* *Windows*: A terminal such as [Git Bash](https://gitforwindows.org/).
* *All platforms*: Download and install the appropriate [miniconda package](https://docs.conda.io/en/latest/miniconda.html) or [micromamba package](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html) for your platform.
* *All platforms*: Check if `pip` is installed, else `conda install pip` or `mamba install pip`.

### Installation steps

Open a terminal and execute (*Windows*: right click on a folder and choose `Git Bash` from the context menu.)

```sh
pip install git+https://github.com/echemdb/autotag-metadata
```

*Windows*: Create an icon in the start menu

```sh
desktop-app install autotag_metadata
```

### Starting Autotag-Metadata

```sh
python -m autotag_metadata
```

```{note}
Multiple instances of the program can be launched to observe different folders.
```

## For developers

Download the repository

```sh
git clone ssh://git@github.com/echemdb/autotag-metadata.git
cd autotag-metadata
```

Install dependencies

```sh
conda env create --name autotag --file environment-dev.yml
conda activate autotag_metadata-dev
pip install -e .
```

Starting autotag-metadata

```sh
python -m autotag_metadata
```

To verify changes made to the documentation refer to the [readme](https://github.com/echemdb/autotag-metadata/tree/main/doc/README.md) in the repository.
