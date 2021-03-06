[![Build Status](https://travis-ci.org/MatthewDaws/OpenCrimeData.svg?branch=master)](https://travis-ci.org/MatthewDaws/OpenCrimeData) 

# Open crime data

## Abstract

The rise of Open Data has lead to the release, especially in the USA, of rich
crime datasets, often with seemingly precisely coded geographical locations.
These datasets are increasingly being used by researchers; we are particularly
interested in the design and evaluation of predictive policing algorithms.
We present a case study of data from a number of US cities, exploring some of
the problems with naively assuming that the data is correct "as is".  We develop
novel algorithms for reassigning location points in a more "realistic" manner,
operating both in two dimensional space, and on the street network.
The software used is released in a Open Source manner,
in the hope that other researchers can directly use, and also extend, the work,
with minimal extra effort.

### Folder structure

- `article` The LaTeX source of the article, and Jupyter notebooks to produce graphics etc.
  directly for the article.

- `details` Other notebooks which explore the data etc.
- `notebooks` Notebooks which are not directly connected with the article.
- `analysis` Results of running `open_cp` prediction algorithms on `opencrimedata` data.
- `opencrimedata` The Python package
- `tests` And tests

### Installation

Clone or download.  Run

     python setup.py install
