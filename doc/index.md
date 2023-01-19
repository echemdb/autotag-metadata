---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.13.8
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

Welcome to autotag-metadata's documentation!
===================================

Autotag-metadata allows automatic creation of metadata files upon file creation. The input metadata file can be added in a simple GUI or from template YAML files.
The program was originally developed to create metadata files for experimental data acquired in a laboratory. However, it can in principle be used in any process where files are generated in the file system.

Input and output metadata files are currently in the YAML format, which can easily be converted in any other kinds of formats such as JSON, XML, ...

The benefit of recording such metadata files is that these machine readable metadata files allow for further usage of the research data in following data management workflows, i.e., to transfer files to a data repository, to update electronic lab notebooks, or perform automated data evaluation based on the available metadata.

Example
=======

Assume one records automatically in the laboratory the change in color of a fruit at different temperatures, i.e., of a banana. For the first temperature the program returns a `banana.csv` and or the second a `banana2.csv`. These files contain a limited amount of information, such as a time `t` and intensity `I` axis.

All other information on the experimentalist, the banana, and other starting parameters would have to be stored elsewhere (sheet of paper or - electronic - lab notebook). All this information can be pre-defined in autotag-metadata such as:

```
experimentalist: Max Mustermann
supervisor: John Doe
project: degradation
equipment:
  - temperature sensor XY
  - color probe 2.0
starting temperature:
  value: 300
  unit: K
humidity:
  value: 80
  unit: %
fruit:
  type: banana
  purchased: YYYY.MM.DD
  supplier: Banana corp.
```

When autotag-metadata is active when `banana.csv` is generated, a new file `banana.csv.meta.yaml` is written in the same folder, which contains the pre-defined set of metadata. The next measurement is supposed to be done at 320 K. In that case, while autotag-metadata is running, we change in the mask of the programm the temperature from 300 to 320 K. Once the next file is created, here `banana2.csv` the newly created `banana2.csv.meta.yaml` will contain the updated temperature.

An elaborate metadata file for an electrochemistry experiment can be found [echemdbs' metadata schema](https://github.com/echemdb/metadata-schema/blob/main/examples/file_schemas/autotag.yaml) repository.

```{note}
The program can be launched multiple times to observe multiple folders.
```

Refer to the [usage](usage.md) section for more details on the GUI.
<!--
```{todo}
* explain installation for developers.
* explain installation from conda-forge, assuming we release it there soon.
* explain installation from PyPI, assuming we release it there soon.
* only leave the very basics of installation in the README and refer here instead.
```
-->

Installation
============

See the [installation instructions](installation.md) for details.

+++

```{toctree}
:maxdepth: 2
:caption: "Contents:"
:hidden:
installation.md
usage.md
```
