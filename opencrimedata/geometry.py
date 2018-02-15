"""
geometry
~~~~~~~~

Some simple geometry routines.
"""

import numpy as _np
import scipy.spatial as _spatial
import open_cp.network as _network
import shapely.geometry as _shapelygeometry
import collections as _collections
import logging as _logging

_logger = _logging.getLogger(__name__)

class AggregatePoints():
    """Merge very close points together.  Does not try to find an optimal
    solution, but instead uses a greedy algorithm.
    
    :param points: An iterable of pairs `(x,y)` of coordinates.
    :param tolerance: The cut-off distance at which points will be merged.
    """
    def __init__(self, points, tolerance = 0.1):
        all_nodes = list(set(((x,y) for x,y in points)))
        tree = _spatial.cKDTree(all_nodes)
        
        self._nodes = []
        allnodes_to_nodes_lookup = dict()
        
        for i, pt in enumerate(all_nodes):
            if i in allnodes_to_nodes_lookup:
                continue
            index = len(self._nodes)
            self._nodes.append(pt)
            for x in tree.query_ball_point(pt, tolerance):
                if x not in allnodes_to_nodes_lookup:
                    allnodes_to_nodes_lookup[x] = index
                    
        self._lookup = {pt:allnodes_to_nodes_lookup[i] for i, pt in enumerate(all_nodes)}

    @property
    def merged_points(self):
        return self._nodes
    
    def index(self, pt):
        pt = tuple(pt)
        return self._lookup[pt]
    
    def __getitem__(self, pt):
        return self._nodes[self.index(pt)]


class AggregatePointsViaGraph():
    """Merge very close points together.  Proceeds by forming a graph whose
    vertices are the points, and where vertices are joined by an edge if they
    are within `tolerance` distance.  Then we find the connected components of
    the graph, find the vertex closest to the centroid of the component, and
    use this vertex as a "merged point".
    
    :param points: An iterable of pairs `(x,y)` of coordinates.
    :param tolerance: The cut-off distance at which points will be merged.
    """
    def __init__(self, points, tolerance = 0.1):
        all_nodes = list(set(((x,y) for x,y in points)))
        all_nodes.sort()
        all_nodes = _np.asarray(all_nodes)
        builder = _network.GraphBuilder()
        idx = _np.arange(all_nodes.shape[0])
        tsq = tolerance ** 2
        _logger.debug("Merging %s points", len(all_nodes))
        for i, pt in enumerate(all_nodes):
            builder.vertices.add(i)
            distsq = _np.sum((all_nodes[i+1:] - pt)**2, axis=1)
            for j in idx[i+1:][distsq <= tsq]:
                builder.add_edge(i, j)
            if i % 1000 == 0:
                _logger.debug("Done %s / %s points", i, len(all_nodes))
        graph = builder.build()
        
        self._make_data(graph, all_nodes)

    def _make_data(self, graph, all_nodes):
        self._nodes = []
        self._lookup = dict()
        for com in _network.connected_components(graph):
            pts = all_nodes[list(com)]
            centroid = _np.mean(pts, axis=0)
            assert centroid.shape == (2,)
            i = _np.argmin( _np.sum((pts - centroid)**2, axis=1) )
            self._nodes.append(pts[i])
            for j in com:
                ptj = tuple(all_nodes[j])
                self._lookup[ptj] = len(self._nodes) - 1
        self._nodes = _np.asarray(self._nodes)

    @property
    def merged_points(self):
        return self._nodes
    
    def index(self, pt):
        pt = tuple(pt)
        return self._lookup[pt]
    
    def __getitem__(self, pt):
        return self._nodes[self.index(pt)]


try:
    import rtree as _rtree
except Exception as ex:
    _logger.error("Cannot load 'rtree' because %s / %s", type(ex), ex)
    _rtree = None


class AggregatePointsViaGraphFast(AggregatePointsViaGraph):
    """As :class:`AggregatePointsViaGraph` but using `rtree` to accelerate
    the initial grouping of points."""
    def __init__(self, points, tolerance = 0.1):
        all_nodes = list(set(((x,y) for x,y in points)))
        all_nodes = _np.asarray(all_nodes)
        builder = _network.GraphBuilder()
        index = self._make_index(all_nodes, tolerance)
        
        d = tolerance / 20
        for i, pt in enumerate(all_nodes):
            builder.vertices.add(i)
            x, y = pt
            for j in index.intersection((x-d, y-d, x+d, y+d)):
                if i < j:
                    builder.add_edge(i, j)
        graph = builder.build()
        
        self._make_data(graph, all_nodes)

    @staticmethod
    def _make_index(all_nodes, tolerance):
        def index_gen():
            d = tolerance * 1.05
            for i, (x, y) in enumerate(all_nodes):
                bounds = (x-d, y-d, x+d, y+d)
                yield i, bounds, None
        return _rtree.index.Index(index_gen())


class Redistributor():
    """Allow sampling points uniformly at random from polygons.
    
    :param polygons: List of `shapely` polygon objects.
    """
    def __init__(self, polygons):
        self._polygons = polygons
        self._make_index()
        
    @property
    def polygons(self):
        """The list of source polygons"""
        return self._polygons
        
    def find_containing_polygon(self, x, y):
        """Find the containing polygon(s) as indicies into `self.polygons`.
        """
        pt = _shapelygeometry.Point(x, y)
        if self._index is None:
            return [i for i, poly in enumerate(self._polygons)
                    if poly.intersects(pt)]
        return [i for i in self._index.intersection((x-.1,y-.1,x+.1,y+.1))
                if self._polygons[i].intersects(pt)]

    def redistribute_from_poly(self, index, size=1):
        """Return a number of points in the polygon.
        
        :param index: Index into `self.polygons`.
        :param size: The _minimum_ number of points to return.
        
        :return: Array of points, empty if no polygon.
        """
        polygon = self._polygons[index]
        xmin, ymin, xmax, ymax = polygon.bounds
        xd, yd = xmax - xmin, ymax - ymin
        ratio = xd * yd / polygon.area
        out = []
        while len(out) < size:
            need = int((size - len(out) + 1) * ratio)
            pts = _np.random.random(size=(need, 2))
            pts = pts * _np.asarray([xd, yd])[None,:] + _np.asarray([xmin, ymin])[None,:]
            pts = _shapelygeometry.MultiPoint(pts)
            pts = _np.asarray(pts.intersection(polygon))
            if len(pts) == 0:
                continue
            out.extend( _np.atleast_2d(pts) )
        return out

    def redistribute(self, x, y, size=1):
        """Return a number of points in the polygon containing the points.
        
        :param size: The _minimum_ number of points to return.
        
        :return: Array of points, empty if no polygon.
        """
        choices = self.find_containing_polygon(x, y)
        if len(choices) == 0:
            return []
        return self.redistribute_from_poly(choices[0], size)
    
    def _make_index(self):
        if _rtree is None:
            self._index = None
            return
        _logger.debug("Making rtree index from %s polygons", len(self._polygons))
        def index_gen():
            for i, p in enumerate(self._polygons):
                yield i, p.bounds, None
        self._index = _rtree.index.Index(index_gen())


class CachingRedistributor(Redistributor):
    """As :class:`Redistributor` but caching lists of points for polygons,
    to support faster and richer operations, at the expense of space."""
    def __init__(self, polygons):
        super().__init__(polygons)
        self._cache = dict()
        self._maxsize = 128
        self._maxsize_cache = dict()
        
    def _populate(self, index, size):
        if index not in self._cache:
            self._cache[index] = []
            self._maxsize_cache[index] = 1
        if len(self._cache[index]) < size:
            s = max(size, min(self._maxsize_cache[index] * 2, self._maxsize))
            self._maxsize_cache[index] = s
            self._cache[index].extend( super().redistribute_from_poly(index, s) )
        return self._cache[index]
        
    def redistribute_from_poly(self, index, size=1):
        out = self._populate(index, size)
        toret = out[-size:]
        del out[-size:]
        return toret
    
    def redistribute_within_radius(self, x, y, radius):
        """Return a single point in the polygon containing that point, and
        within a disc of the given radius.
        
        :return: A point `(x,y)` or `None` if no containing polygon
        """
        choices = self.find_containing_polygon(x, y)
        if len(choices) == 0:
            return None
        index = choices[0]
        out = self._populate(index, 1)
        rs = radius * radius
        while True:
            xx, yy = out.pop()
            if (x-xx)*(x-xx) + (y-yy)*(y-yy) <= rs:
                return xx, yy
            if len(out) == 0:
                out = self._populate(index, 1)


try:
    import rtree as _rtree
except:
    pass


class ClosestPoint():
    """Find the closest point in an input collection, or match to a closest
    point in disc.  Useful for working with the address database.

    :param points: The input points we'll match to; array of shape `(n,2)`
    :param scale: Defaults to 1; should be "small" compared to the input
      scale.
    """
    def __init__(self, points, scale=1):
        self._points = _np.asarray(points)
        self._scale = scale
        self._index = _rtree.index.Index(self._index_gen(self._scale))

    def _index_gen(self, e):
        for i, (x, y) in enumerate(self._points):
            xmin, xmax = x-e, x+e
            ymin, ymax = y-e, y+e
            yield i, (xmin, ymin, xmax, ymax), None

    @property
    def points(self):
        """The input points."""
        return self._points

    def closest(self, pt):
        """Return the point in the input data which is closest to this
        point.
        
        :param pt: The point, `(x,y)`
        
        :return: Pair `(index, point)` where point is the closest point,
          and `index` is into :attr:`points`.
        """
        pt = _np.asarray(pt)
        d = 10 * self._scale
        choices = []
        while len(choices) == 0:
            d += d
            xmin, xmax = pt[0] - d, pt[0] + d
            ymin, ymax = pt[1] - d, pt[1] + d
            choices = list(self._index.intersection((xmin, ymin, xmax, ymax)))
        diffs = pt - self._points[choices]
        distsqs = _np.sum(diffs**2, axis=1)
        i = _np.argmin(distsqs)
        i = choices[i]
        return i, self._points[i]

    def all_in_disc(self, pt, radius):
        """Find all points which are within `radius` of `pt`.

        :return: `(indices, points)`
        """
        pt = _np.asarray(pt)
        xmin, xmax = pt[0] - radius, pt[0] + radius
        ymin, ymax = pt[1] - radius, pt[1] + radius
        choices = list(self._index.intersection((xmin, ymin, xmax, ymax)))
        if len(choices) == 0:
            return [], []
        distsq = _np.sum((pt - self._points[choices])**2, axis=1)
        mask = distsq <= radius**2
        choices = _np.asarray(choices, dtype=_np.int)[mask]
        return choices, self._points[choices]


def graph_from_streets(streets, to_projected_line):
    """Constructs a graph from a generic collection of "streets".
    
    :param streets: Iterator of "street" objects
    :param to_projected_line: Callable object which takes a "street" object
      as from the iterable `streets`, and returns a "line" which is
      suitable projected (if necessary).  A "line" is an iterable of points,
      where each point is a pair `(x,y)`.
      
    :return: Pair `(graph, names)` where `graph` is a graph object, and
      `names` is a dictionary from edge index (in graph) to a list of
      "street" instances which are the street(s) associated with that
      edge.
    """
    all_streets, projected_lines = [], []
    for street in streets:
        all_streets.append(street)
        projected_lines.append(to_projected_line(street))
    
    all_nodes = []    
    for line in projected_lines:
        for pt in line:
            all_nodes.append(pt)

    b = _network.PlanarGraphNodeOneShot(all_nodes)
    name_lookup = _collections.defaultdict(list)
    for street, line in zip(all_streets, projected_lines):
        for e in b.add_path(line):
            name_lookup[e].append(street)
            
    b.remove_duplicate_edges()
    graph = b.build()
    names = _collections.defaultdict(list)
    for e, ns in name_lookup.items():
        if e[0] == e[1]:
            # These have been removed
            continue
        index, _ = graph.find_edge(*e)
        names[index].extend(ns)
        
    return graph, names
