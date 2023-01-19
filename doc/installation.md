Installation
============

## Requirements

**Install Conda:**
Download and install the appropriate [miniconda package](https://docs.conda.io/en/latest/miniconda.html) for your platform.

**Install Git:**

* **Linux**

Debian/apt-based distribution:

```sh
 sudo apt-get install git
```

Fedora/RPM-based distribution:

```sh
 sudo dnf install git-all
```

* **Windows**

Download and install [Git Bash](https://gitforwindows.org/)

## Install Autotag Metadata

Open a terminal and execute (On Windows right click on a folder and choose `Git Bash` from the context menu.)

```sh
pip install git+https://github.com/echemdb/autotag-metadata
```

Create an icon in the start menu

```sh
desktop-app install autotag_metadata
```

## Starting Autotag Metadata

From the (Windows) start menu launch `autotag_metadata`
![icon](../autotag_metadata/autotag_metadata.ico)

Multiple instances of the program can be launched to observe different folders.

## Installation instructions for developers

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
