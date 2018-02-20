# Article

Notebooks and scripts etc. for generation of the written article.  Compile `article.tex` using `pdflatex`.  Included
here are all the necessary figures for the article.

- `0 - The input data.ipynb`  Initial plotting of the 3 data sets.
- `1 - Library code to load data.ipynb`  Demo of how to use the library code to load the datasets.
- `2 - All the redistributed data.ipynb`  A guide to loading all the the "generated" data sets (including the originals).

## Chicago

- Initial exploration of the data, see `details/Chicago Explore Data.ipynb`
- Comparing "old" and "new" files, see `Chicago 00 Old File.ipynb`
- Looking at how each `block`s worth of events corresponds to the street network,
   see `details/Chicago geo-coding.ipynb`
- `details/Chicago conjecture.ipynb` further explores this.
- `Chicago 01 Voroni from street network.ipynb` looks 
- `Chicago 02 Voroni from clustering of points.ipynb` 
- `Chicago 03 Link points to buildings.ipynb`
- `Chicago 04 Cluster and network flow.ipynb`

## San Francisco

- Initial exploration of the data, see `SF 00 Explore Data.ipynb`
- Exploring geo-coding, see `SF 01 Geocoding.ipynb`
- For redistributing points using Voroni cells, see `SF 02 Voroni from raw points.ipynb`
- Street network data: initial exploration of data is in `notebooks/SF - Street network data.ipynb`
- Matching events to the network is in `notebooks/SF - Streets into graph.ipynb`
- For details about the TIGER/Lines data, see `details/TIGER Lines Data.ipynb`
- For projecting the output of `SF 02` to the street network, see `SF 03 Project back to street network.ipynb`
- `SF 04 Project and flow along street network.ipynb`
- `SF 05 Link up to buildings.ipynb`


## Dallas
- Initial exploration of the data, see `Dallas 00 - The input data.ipynb`
- `Dallas 01 - Join coords to street segments.ipynb`
- `Dallas 02 - Move to nearest building.ipynb`
