# Details

Notebooks, scripts etc. which are needed to re-create research.


- `Address Database.ipynb`
  - Load data from `http://results.openaddresses.io/` and extract that which is relevant for the 3 case studies.
- `TIGER Lines Data.ipynb`
  - Load and process data from TIGER/Lines.  Demo the library code.  Try (and fail) to match up with street names.
  The examples here are all for San Francisco.



### Chicago

In logical order.

- `Chicago Geographic Boundaries.ipynb`
  - Look at how to split up Chicago into "natural" areas.  As in `open_cp`.
- `Chicago Explore Data.ipynb`
  - Look at the data (both old and new) briefly, and demo library code.
- `Chicago Time Series analysis.ipynb`
  - Plot some time series of how the number of events changes over time.
- `Chicago geo-coding.ipynb`
  - Make some plots.  Explore "unusual" cases.  Look at TIGER/Lines data.  Look at outliers.
- `Chicago old file.ipynb`
  - See how the old and new files match up.  Plot some examples of the changed geocoding.
- `Chicago conjecture.ipynb`
  - We _conjecture_ that there is a tight link between "segments" of the street network graph,
    and event locations.  This is _mostly_ true.
- `Chicago Street Lines.ipynb`
  - An alternative source of "street network" data
- `Chicago events to addesses.ipynb`
  - Attempt to link the crime data, by block, to open address data.  Too much noise to make this automatic.
- `Chicago Voroni From Segments.ipynb`
  - Use each "segment" of the graph to find areas where we will move points to.

- `Chicago Cluster.ipynb`
  - 2nd attempt at Voroni diagram making.  Need to revisit this in detail.



### San Francisco

- `SF Geographic Boundaries.ipynb`
  - Look at how to split up Chicago into "natural" areas.  As in `open_cp`.
- `SF Voroni around raw points.ipynb`
  - Uses the library code to merge the input coordinates if they are very close, and then just generate a voroni diagram from the output.



### Dallas

- `Dallas Explore Data.ipynb`
  - ???
- `Dallas Voroni Redist.ipynb`
  - ???