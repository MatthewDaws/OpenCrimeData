"""
tiger_lines
~~~~~~~~~~~

Import and process TIGER Lines data.  The data is in longitude/latitude format,
and should be projected before being passed to the graph creation routines.
"""

import fiona as _fiona
import numpy as _np
import collections as _collections
import geopandas as _gpd
import open_cp.network as _network
import shapely.geometry as _shapelygeometry
import logging as _logging

_logger = _logging.getLogger(__name__)

def load_roads(filename):
    """Load a "roads" TIGER Lines shape-file.
    
    :return: Iterable of pairs `(name, geo)` where `name` is the name of the
      road (may be `None`) and `geo` is a `numpy` array of coordinates of
      vertices of the line.
    """
    with _fiona.open(filename) as shapefile:
        yield from _yield_road_data(shapefile)

def _yield_road_data(shapefile):
    _FULLNAME = "FULLNAME"
    header = list(shapefile.schema["properties"])
    if _FULLNAME not in header:
        raise Exception("File schema not as expected: {}".format(shapefile.schema))
    for row in shapefile:
        road_name = row["properties"][_FULLNAME]
        geo = _np.asarray(row["geometry"]["coordinates"])
        yield (road_name, geo)

def load_roads_zip(zip_filename, zip_path=""):
    """As :func:`load_roads` but use `fiona`'s ability to load from a zip file.
    The the shapefile is not in the root directory of the zip file, specify
    `zip_path`.
    """
    with _fiona.open(zip_path, vfs="zip://" + zip_filename) as shapefile:
        yield from _yield_road_data(shapefile)

def project_roads(roads, proj):
    """Helper function to project road data.

    :param roads: Iterable of `(name, geo)`
    :param proj: A `pyproj.Proj` instance, or similar callable object
      which takes `(long, lat)` and returns `(x, y)`.

    :return: Iterable of `(name, geo)`
    """
    for name, geo in roads:
        yield name, _np.asarray([proj(*pt) for pt in geo])


Edge = _collections.namedtuple("edge", "fullname left_address_from left_address_to right_address_from right_address_to line")
EdgeNoLine = _collections.namedtuple("edge_noline", "fullname left_address_from left_address_to right_address_from right_address_to")

def _to_edge_noline(edge):
    return EdgeNoLine(*(tuple(edge)[:-1]))

def load_edges(filename):
    """Load a "edges" TIGER Lines shape-file, with just name and address
    information extracted.
    
    :return: Iterable of `Edge` objects
    """
    with _fiona.open(filename) as shapefile:
        yield from _yield_edge_data(shapefile)

def _yield_edge_data(shapefile):
    _HEADER_NAME = ["FULLNAME", "LFROMADD", "LTOADD", "RFROMADD", "RTOADD"]
    header = list(shapefile.schema["properties"])
    if not all(x in header for x in _HEADER_NAME):
        raise Exception("File schema not as expected: {}".format(shapefile.schema))
    for row in shapefile:
        data = [row["properties"][x] for x in _HEADER_NAME]
        geo = _np.asarray(row["geometry"]["coordinates"])
        yield Edge(*(data+[geo]))

def load_edges_zip(zip_filename, zip_path=""):
    """As :func:`load_edges` but use `fiona`'s ability to load from a zip file.
    The the shapefile is not in the root directory of the zip file, specify
    `zip_path`.
    """
    with _fiona.open(zip_path, vfs="zip://" + zip_filename) as shapefile:
        yield from _yield_edge_data(shapefile)

def project_edges(edges, proj):
    """Helper function to project edge data.

    :param roads: Iterable of `edge` objects
    :param proj: A `pyproj.Proj` instance, or similar callable object
      which takes `(long, lat)` and returns `(x, y)`.

    :return: Iterable of `edge` objects
    """
    for edge in edges:
        geo = _np.asarray([proj(*pt) for pt in edge.line])
        r = tuple(edge)[:-1] + (geo,)
        yield Edge(*r)

def filter_edge_names(edges):
    """Remove "edges" which have no name, or which are an "alley" or which are
    a railroad.

    :param edges: Iterable of `edge` objects
    :return: Iterable of filtered `edge` objects
    """
    for edge in edges:
        if filter_names(edge.fullname):
            yield edge

def filter_names(name):
    """As :func:`filter_edge_names` but given `name` return `True` if
    it's valid, or `False` if invalid."""
    if name is None:
        return False
    uname = name.upper()
    if uname == "ALLEY":
        return False
    if uname.endswith(" RR") or uname.endswith(" RLWY"):
        return False
    return True

def roads_to_graph(roads):
    """Construct an `open_cp.network` style graph from a "roads" input.
    Merges very close vertices (<0.1 meters) and repeated edges.

    :param roads: Iterable of `(name, geo)`

    :return: `(graph, names)` where `names` is a dictionary from the edge
      index to the set of road names which make use of that edge (in
      either direction).
    """
    roads = list(roads)
    all_nodes = []
    for _, geo in roads:
        for pt in geo:
            all_nodes.append(pt)

    b = _network.PlanarGraphNodeOneShot(all_nodes)
    name_lookup = _collections.defaultdict(set)
    for name, geo in roads:
        for e in b.add_path(geo):
            name_lookup[e].add(name)

    b.remove_duplicate_edges()
    graph = b.build()
    names = _collections.defaultdict(set)
    for e, ns in name_lookup.items():
        index, _ = graph.find_edge(*e)
        names[index].update(ns)
    return graph, dict(names)

def edges_to_graph(edges):
    """Construct an `open_cp.network` style graph from an "edges" input.
    Merges very close vertices (<0.1 meters).  From "edges" data there should
    not be repeated edges.

    :param roads: Iterable of `(name, geo)`

    :return: `(graph, names)` where `names` is a dictionary from the edge
      index to an instance of `EdgeNoLine`.
    """
    edges = list(edges)
    all_nodes = []
    for edge in edges:
        for pt in edge.line:
            all_nodes.append(pt)

    b = _network.PlanarGraphNodeOneShot(all_nodes)
    name_lookup = _collections.defaultdict(set)
    for edge in edges:
        for e in b.add_path(edge.line):
            name_lookup[e].add(_to_edge_noline(edge))

    graph = b.build()
    names = dict()
    for e, ns in name_lookup.items():
        index, _ = graph.find_edge(*e)
        if index in names:
            raise Exception("Repeated edge: {}".format(e))
        if len(ns) > 1:
            raise Exception("Edge {} has multiple data: {}".format(e, ns))
        names[index] = list(ns)[0]
    return graph, names

def merge_graphs(roads_graph, edges_graph):
    """Merge the graphs.  We assume that each vertex of `roads_graph`
    matches (up to a small tolerance) a vertex in `edges_graph`, and that
    under this identification, `roads_graph` is a sub-graph of `edges_graph`.

    :return: A list, the same length as the number of edges in `roads_graph`,
      giving the corresponding edge index in `edges_graph`.
    """
    vertex_lookup = _merge_vertices(edges_graph, roads_graph)
    edge_lookup = []
    for edge in roads_graph.edges:
        try:
            index, _ = edges_graph.find_edge(*[vertex_lookup[k] for k in edge])
            edge_lookup.append(index)
        except KeyError:
            raise ValueError("Edge {} missing from `edges` graph".format(edge))
    return edge_lookup

def _merge_vertices(super_graph, sub_graph, tolerance=0.1):
    """Attempt to match each vertex in `sub_graph` to a vertex in
    `super_graph`.

    :return: A dictionary from the vertex keys of `sub_graph` to vertex keys
      in `super_graph`.
    """
    tolerance = tolerance ** 2
    lookup = dict()
    for key, (x,y) in sub_graph.vertices.items():
        (v1,v2), t = super_graph.project_point_to_graph(x, y)
        v = v1 if t < 0.5 else v2
        xx, yy = super_graph.vertices[v]
        if (x-xx)**2 + (y-yy)**2 > tolerance:
            raise ValueError("Vertices do not match up to tolerance.")
        lookup[key] = v
    return lookup

def compute_all_names(roads_graph, roads_names, edges_graph, edges_names, roads_edges_to_edges_edges=None):
    """Makes the same assumptions as :func:`merge_graphs`.

    :param roads_graph:
    :param roads_names: Output of :func:`load_roads`
    :param edges_graph:
    :param edges_names: Output of :func:`load_edges`
    :param roads_edges_to_edges_edges: Optionally, the output of
      :func:`merge_graphs`, or `None`.

    :return: Iterable, same length as the number of edges in `edges_graph`,
      giving the edge data (instance of `EdgeNoLine`) and a set of possible
      names.
    """
    if roads_edges_to_edges_edges is None:
        roads_edges_to_edges_edges = merge_graphs(roads_graph, edges_graph)
    inverse = dict()
    for i, e in enumerate(roads_edges_to_edges_edges):
        if e in inverse:
            raise ValueError("Edge {} in 'edges' mapped to twice from 'roads'".format(e))
        inverse[e] = i
    for i, edge in enumerate(edges_graph.edges):
        if i in inverse:
            names = set(roads_names[inverse[i]])
        else:
            names = set()
        names.add(edges_names[i].fullname)
        yield edges_names[i], names

def all_names_to_frame(edges_graph, all_names):
    """Produce a :class:`GeoDataFrame` summarising the names.
    The returned frame will not have a `crs` set.

    :param edges_graph: Graph produced from the `edges` dataset
    :param all_names: As from :func:`compute_all_names`
    """
    all_names = list(all_names)
    frame = _gpd.GeoDataFrame({"left_add_from" : [e.left_address_from for e, _ in all_names],
        "left_add_to" : [e.left_address_to for e, _ in all_names],
        "right_add_from" : [e.right_address_from for e, _ in all_names],
        "right_add_to" : [e.right_address_to for e, _ in all_names],
        "edge_number" : [i for i,_ in enumerate(all_names)],
        })
    
    all_name_options = [list(names) for _, names in all_names]
    maxlen = max(len(names) for names in all_name_options)
    for i in range(maxlen):
        name = "name{}".format(i)
        data = []
        for names in all_name_options:
            if len(names) > i:
                data.append(names[i])
            else:
                data.append(None)
        frame[name] = data

    geo = []
    for edge in edges_graph.edges:
        line = [edges_graph.vertices[x] for x in edge]
        geo.append(_shapelygeometry.LineString(line))
    frame.geometry = geo

    return frame


class TigerLines():
    """Encapsulates the process of loading TIGER/Lines data.

    :param roads_filename: The path to the directory containing the shapefile
      of the "roads" data.  To load from a zip file, use the filename
      "zip://{filename_of_zip}:{path_in_zipfile}"
    :param edges_filename: Same for the "edges" data.
    :param proj: A projection object, for example from `pyproj`.
    """
    def __init__(self, roads_filename, edges_filename, proj):
        zf = self._zip_filename(roads_filename)
        if zf is None:
            _logger.debug("Attempting to open %s to read roads data", roads_filename)
            roads = load_roads(roads_filename)
        else:
            _logger.debug("Attempting to open zip file %s path '%s' to read roads data", *zf)
            roads = load_roads_zip(*zf)
        roads = project_roads(roads, proj)
        _logger.info("Reading roads shapefile into a graph structure")
        self._roads_graph, self._roads_name_lookup = roads_to_graph(roads)

        zf = self._zip_filename(edges_filename)
        if zf is None:
            _logger.debug("Attempting to open %s to read edges data", edges_filename)
            edges = load_edges(edges_filename)
        else:
            _logger.debug("Attempting to open zip file %s path '%s' to read edges data", *zf)
            edges = load_edges_zip(*zf)
        edges = project_edges(edges, proj)
        _logger.info("Reading edges shapefile into a graph structure")
        self._edges_graph, self._edges_name_lookup = edges_to_graph(edges)

        _logger.info("Merging graphs")
        self._roads_edges_to_edges_edges = merge_graphs(self._roads_graph, self._edges_graph)
        self._all_names_data = list(compute_all_names(self._roads_graph,
            self._roads_name_lookup, self._edges_graph, self._edges_name_lookup,
            self._roads_edges_to_edges_edges))

        self._in_roads_only = []
        for i in range(self._roads_graph.number_edges):
            e = self._roads_edges_to_edges_edges[i]
            name = self._edges_name_lookup[e].fullname
            roads_names = self._roads_name_lookup[i]
            if not name in roads_names:
                self._in_roads_only.append( (i, name, roads_names) )

    @property
    def roads_graph(self):
        """The graph generated from "roads" data."""
        return self._roads_graph

    @property
    def roads_name_lookup(self):
        """A list of sets of names for each edge in `roads_graph`."""
        return self._roads_name_lookup
    
    @property
    def edges_graph(self):
        """The graph generated from "edges" data."""
        return self._edges_graph
    
    @property
    def edges_name_lookup(self):
        """A list of the name and address data for each edge in `edges_graph`.
        """
        return self._edges_name_lookup

    @property
    def from_roads_to_edges(self):
        """A dictionary lookup from edges in `roads_graph` to edges in
        `edges_graph`."""
        return self._roads_edges_to_edges_edges

    @property
    def merged_names(self):
        """A list, for each edge in `edges_graph`, of pairs of the address
        data and a complete list of possible names."""
        return self._all_names_data

    @property
    def name_in_roads_only(self):
        """A list of edges whose name from "edges" is not repeated in "roads".
        We think such results are errors in the data.  A list of triples
        `(i, name, roads_names)` where `i` is the edge index in `roads_graph`,
        `name` is the "edges" name, and `roads_names` is the set of names from
        "roads".
        """
        return list(self._in_roads_only)

    def check_null_edges(self):
        """Check that each edge which "edges" assigns `None` is not given a
        valid name by "roads".  Raises `AssertError` on failure."""
        for i in range(self._roads_graph.number_edges):
            e = self._roads_edges_to_edges_edges[i]
            if self._edges_name_lookup[e].fullname is None:
                assert self._roads_name_lookup[i] == {None}

    def to_geodataframe(self):
        """Convert to a :class:`GeoDataFrame`.  Does not set the `crs`."""
        return all_names_to_frame(self._edges_graph, self._all_names_data)

    def to_reduced_geodataframe(self):
        """Convert to a :class:`GeoDataFrame`.  Does not set the `crs`.
        Only contains rows where some name passes the "filter".
        """
        frame = self.to_geodataframe()
        maxlen = len([x for x in frame.columns if x.startswith("name")])
        mask = []
        for i, row in frame.iterrows():
            want = any(filter_names(row["name{}".format(i)]) for i in range(maxlen))
            mask.append(want)
        mask = _np.asarray(mask)
        return _gpd.GeoDataFrame(frame[mask])

    def make_reduced_graph(self):
        """Compute the "edges" graph, where we remove any edge which has a name
        which is "filtered".

        :return: `(graph, edge_list)` where `graph` is the new graph, and
          `edge_list` is a list (in order) of the edges of `edges_graph` used.
        """
        builder = _network.PlanarGraphBuilder()
        builder.vertices.update(self.edges_graph.vertices)
        edge_list = []
        for i, (edge, (address, names)) in enumerate(zip(self.edges_graph.edges, self.merged_names)):
            if any(filter_names(x) for x in names):
                builder.add_edge(*edge)
                edge_list.append(i)
        builder.remove_unused_vertices()
        return builder.build(), edge_list

    @staticmethod
    def _zip_filename(filename):
        if not filename.startswith("zip://"):
            return None
        filename = filename[6:]
        parts = filename.split(":")
        return parts[0], parts[1]
