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

Welcome to echemdb's documentation!
===================================
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/echemdb/echemdb/0.4.0?urlpath=tree%2Fdoc%2Fusage%2Fentry_interactions.md)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.6502901.svg)](https://doi.org/10.5281/zenodo.6502901)

This echemdb module provides a Python library to interact with a database of
[frictionless datapackages](https://frictionlessdata.io/)
containing electrochemical data following [echemdb's metadata schema](https://github.com/echemdb/metadata-schema).
Such a database can be generated from the data on [echemdb.org](https://www.echemdb.org)
or from local files.

Examples
========

..: TODO

Installation
=========

This package is available on [PiPY](https://pypi.org/project/echemdb/) and can be installed with pip:

```sh .noeval
pip install echemdb
```
The package is also available on [conda-forge](https://github.com/conda-forge/echemdb-feedstock) an can be installed with conda:

```sh .noeval
conda install -c conda-forge echemdb
```

See the [installation instructions](installation.md) for further details.

+++

```{toctree}
:maxdepth: 2
:caption: "Contents:"
:hidden:
installation.md
```
