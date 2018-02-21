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
- `Chicago 01 Voroni from street network.ipynb` uses the street network graph to form voroni cells
  into which events are randomly redistributed.
- `Chicago 02 Voroni from clustering of points.ipynb` instead uses the clustering of events in the input
  data to form voroni cells.
- `Chicago 03 Link points to buildings.ipynb` use the address database as a proxy for building location,
  and then randomly redistribute events to nearby buildings.
- `Chicago 04 Cluster and network flow.ipynb` moves the events around the street network, and then secondly
  moves to nearby buildings.


## San Francisco

- Initial exploration of the data, see `SF 00 Explore Data.ipynb`
- Exploring geo-coding, see `SF 01 Geocoding.ipynb`
- For redistributing points using Voroni cells, see `SF 02 Voroni from raw points.ipynb`
- Street network data: initial exploration of data is in `notebooks/SF - Street network data.ipynb`
- Matching events to the network is in `notebooks/SF - Streets into graph.ipynb`
- For details about the TIGER/Lines data, see `details/TIGER Lines Data.ipynb`
- For projecting the output of `SF 02` to the street network, see `SF 03 Project back to street network.ipynb`
- `SF 04 Project and flow along street network.ipynb` moves events around the street network.
- `SF 05 Link up to buildings.ipynb` uses the results of the previous notebook and assigns events to
  buildings.


## Dallas
- Initial exploration of the data, see `Dallas 00 - The input data.ipynb`
- `Dallas 01 - Join coords to street segments.ipynb` uses the subset of the data which contains both
  projected coordinates and longitude/latitude coordinates to form voroni cells, and then assign all
  projected coordinates to "likely" street locations.
- `Dallas 02 - Move to nearest building.ipynb` then assigns these locations to nearby buildings.
