![test status](https://github.com/echemdb/autotag-metadata/actions/workflows/test.yml/badge.svg)

autotag-metadata is a lightweight tool that creates metadata files for newly created files in the filesystem. A common example is the creation of measurement files during an experiment, for which you would like to store additional information. The content of the newly stored metadata file is based on an input file. For example upon storing a `measurement001.csv` autotag-metadata automatically creates a `measurement001.csv.meta.yaml`. The latter contains information such as:

```yaml
time metadata: 'YYYY-MM-DDThh:mm:ss' # created by autotag-metadata
measurement file name: measurement001.csv # created by autotag-metadata
measurement file sha512: XXX # created by autotag-metadata
# the following information was derived from a pre-defined set of metadata
experimentalist: Max Mustermann
supervisor: John Doe
project: degradation
equipment:
  - temperature sensor XY
  - color probe 2.0
starting temperature:
  value: 300
  unit: K
```

# Installation instructions

Detailed installation instructions can be found in our [documentation](https://echemdb.github.io/autotag-metadata).

## Windows

The latest installer and/or executable can be found in the [release section](https://github.com/echemdb/autotag-metadata/releases).

Launch the program from th start menu.

Multiple instances of the program can be launched to observe different folders.

## Terminal

**Requirements**

* *Windows*: A terminal such as [Git Bash](https://gitforwindows.org/).
* *All*: Download and install the appropriate [miniconda package](https://docs.conda.io/en/latest/miniconda.html) or [micromamba package](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html) for your platform.
* *All*: Check if `pip` is installed, else `conda install pip` or `mamba install pip`.

**Installation**

Open a terminal and execute (*Windows*: right click on a folder and choose `Git Bash` from the context menu.)

```sh
pip install git+https://github.com/echemdb/autotag-metadata
```

*Windows*: Create an icon in the start menu

```sh
desktop-app install autotag_metadata
```

**Starting Autotag-Metadata**

```sh
python -m autotag_metadata
```

Multiple instances of the program can be launched to observe different folders.
