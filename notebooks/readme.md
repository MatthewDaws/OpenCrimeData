# Notebooks

Random thoughts in notebooks.

### Chicago

- `Chicago Address Clean via Edges.ipynb`
  - Attempt to link the crime data, by block, to the TIGER/Lines `edge` data.  Too much noise.
- `Chicago address data.ipynb`
  - Process the ZIP files from `http://results.openaddresses.io/` to extract Chicago data
- `Chicago by block.ipynb`
  - Initial look at each "block" of events from the crime data, and try to "cluster", fit to a line etc.
- `Chicago inital clean.ipynb`
  - Try to remove outliers where the "block" just doesn't match the geo-coding
- `Chicago Points as a Graph.ipynb`
  - Get the points into a graph structure, and perform some analysis.
- `Chicago rectangles.ipynb`
  - For each block, put a rectangle around the block. Then intersect them.
- `Chicago roads as graph.ipynb`
  - Part of 4 notebooks which actually did something useful.  Use the TIGER/Lines data, convert to a graph,
  and then find the "segments".
- `Chicago roads as graph 2.ipynb`
  - Load crime points, project to the graph.  Experiment with forming Voroni.
- `Chicago roads as graph 3.ipynb`
  - Simplify the graph.  
- `Chicago roads as graph 4.ipynb`
  - Use this data to randomise locations
- `Chicago to shapefile.ipynb`
  - Convert the events, with a small amount of metadata, to a shapefile.
- `Chicago visualise new data.ipynb`
  - Join the old and new datasets, and visualise the movements.
- `Chicago Voroni.ipynb`
  - For each "block" take the (weighted?) centroid. Form the voroni diagram, and assign each block to its segment.
  Doesn't work so well.
- `Compare data-sets.ipynb`
  - Compare the "old" and "new" datasets for Chicago.
  
### Dallas

To document

### SANFRAN

To delete??
