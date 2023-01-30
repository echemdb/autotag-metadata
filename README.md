![test status](https://github.com/echemdb/autotag/actions/workflows/test.yml/badge.svg)
# Installation instructions

## Requirements

**Install Conda:**   
Download and install the appropriate [miniconda package](https://docs.conda.io/en/latest/miniconda.html) for your platform.

**Install Git:**  

* **Linux**

Debian/apt-based distribution:

```
 sudo apt-get install git
```

Fedora/RPM-based distribution:

```
 sudo dnf install git-all
```

* **Windows**

Download and install [Git Bash](https://gitforwindows.org/)

## Install Autotag

Open a terminal and execute (On Windows right click on a folder and chose `Git Bash` from the context menu.)

```sh
pip install git+https://github.com/echemdb/autotag-metadata
```

Create an icon in the start menu

```sh
desktop-app install autotag_metadata
```

## Starting Autotagger

From the (Windows) start menu launch `autotag_metadata`  
![icon](autotag_metadata/autotag.ico)

The program can be launched multiple times to observe different folders.

# Installation instructions for developers

Download the repository

```sh
ssh://git@github.com/echemdb/autotag-metadata.git
```

Install dependencies

```sh
conda env create --name autotag --file environment-dev.yml
conda activate autotag
pip install -e .
```

Starting Autotagger

```sh
python -m autotag_metadata
```
