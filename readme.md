# Open crime data

## Abstract

The rise of Open Data has lead to the release, especially in the USA, of rich
crime datasets, often with seemingly precisely coded geographical locations.
These datasets are increasingly being used by researchers; we are in particular
interested in the design and evaluation of predictive policing algorithms.
We present a case study of data from a number of US cities, exploring some of
the problems with naively assuming that the data is correct "as is".  We offer
some algorithms for reassigning location points in a more "realistic", or at
least "random" manner.  The software used is released in a Open Source manner,
in the hope that other researchers can directly use, and also extend, the work,
with minimal extra effort.

### Folder structure

- `article` The LaTeX source of the article, and Jupyter notebooks to produce graphics etc.
  directly for the article.

- `details` Other notebooks which explore the data etc.
- `notebooks` Notebooks which are not directly connected with the article.
- `analysis` Results of running `open_cp` prediction algorithms on `opencrimedata` data.
  - _ToDo_ : Script this more, and make as automatic as possible.

- `opencrimedata` The Python package
- `tests` And tests

