"""
network.py
~~~~~~~~~~

Some explicitly graph/network based methods.
"""

import open_cp.network as _network
from . import geometry as _geometry
import numpy as _np
import rtree as _rtree
import datetime as _datetime
import collections as _collections
import open_cp.logger as _ocp_logger
import logging as _logging
_logger = _logging.getLogger(__name__)

class LimitedNetworkDistance():
    """Helper class to (repeatedly) compute distances between locations on
    edges in a graph.  Features a cut-off which speeds up execution; but
    note that for vertices whose distance from the starting point is much
    more than `maximum_distance`, the resulting data may be incorrect.

    :param graph: Graph to use
    :param edge: The edge index into `graph`
    :parma t: Distance (between 0 and 1) along that edge
    :param maximum_distance: The maximum distance we are interested in.
    """
    def __init__(self, graph, edge, t, maximum_distance):
        self._graph = graph
        self._source_edge = edge
        self._source_t = t
        self._max = maximum_distance
        self._walk()

    def _walk(self):
        distances = dict()
        v1, v2 = self._graph.edges[self._source_edge]
        edge_length = self._graph.lengths[self._source_edge]
        distances[v1] = self._source_t * edge_length
        distances[v2] = (1 - self._source_t) * edge_length
        paths = {v1:v1, v2:v2}
        vertices_to_visit = {v1, v2}
        while len(vertices_to_visit) > 0:
            v = vertices_to_visit.pop()
            for u in self._graph.neighbours(v):
                e, _ = self._graph.find_edge(v, u)
                d = distances[v] + self._graph.lengths[e]
                if u not in distances or d < distances[u]:
                    distances[u] = d
                    if d <= self._max:
                        vertices_to_visit.add(u)
                    paths[u] = v
        self._vertex_distances = distances
        self._paths = paths

    @property
    def graph(self):
        """The input graph."""
        return self._graph

    @property
    def paths(self):
        """Dictionary from vertex to vertex giving the shortest path back to
        the starting edge."""
        return self._paths

    def distance(self, edge, t):
        """Find the distance to this location.  Raises `ValueError` if the edge
        is not connected to the starting edge, or the edge is too distant.

        :param edge: The edge index into :attr:`graph`
        :parma t: Distance (between 0 and 1) along that edge
        """
        if self._source_edge == edge:
            return self._graph.lengths[edge] * abs(self._source_t - t)
        v1, v2 = self._graph.edges[edge]
        d1, d2 = None, None
        edge_length = self._graph.lengths[edge]
        if v1 in self._vertex_distances:
            d1 = self._vertex_distances[v1] + t * edge_length
        if v2 in self._vertex_distances:
            d2 = self._vertex_distances[v2] + (1 - t) * edge_length
        if d1 is None:
            if d2 is None:
                raise ValueError("Starting location is not connected to this point, or is too distant.")
            return d2
        if d2 is None:
            return d1
        return min(d1, d2)


class NetworkDistance():
    """Helper class to (repeatedly) compute distances between locations on
    edges in a graph.  Rather slow for large graphs.

    :param graph: Graph to use
    :param edge: The edge index into `graph`
    :parma t: Distance (between 0 and 1) along that edge
    """
    def __init__(self, graph, edge, t):
        self._graph = graph
        self._lengths, self._prevs = _network.shortest_edge_paths(graph, edge, t)
        self._source_edge = edge
        self._source_t = t

    @property
    def graph(self):
        """The input graph."""
        return self._graph

    def distance(self, edge, t):
        """Find the distance to this location.  Raises `ValueError` if the edge
        is not connected to the starting edge.

        :param edge: The edge index into :attr:`graph`
        :parma t: Distance (between 0 and 1) along that edge
        """
        if self._source_edge == edge:
            return self._graph.lengths[edge] * abs(self._source_t - t)
        v1, v2 = self._graph.edges[edge]
        try:
            edge_length = self._graph.lengths[edge]
            d1 = self._lengths[v1] + t * edge_length
            d2 = self._lengths[v2] + (1 - t) * edge_length
            return min(d1, d2)
        except KeyError:
            raise ValueError("Starting location is not connected to this point.")
        

class NetworkProjectAggregate():
    """Supports projecting points onto a network and aggregating close points
    by network distance.  Proceeds by forming a graph whose vertices are the
    points, and where vertices are joined by an edge if they are within
    `tolerance` distance.  Then we find the connected components of the graph,
    find the vertex closest to the centroid of the component, and use this
    vertex as a "merged point".

    :param graph: Graph, conforming to interface of :mod:`open_cp.network`
    :param points: Array of points of shape `(n,2)` to project to the network
    :param tolerance: Distance at which to aggregate.  Set to be `<=0` to skip
      the aggregation step.
    :param initial_tolerance: If not `None`, then initially group points up to
      this tolerance, ignoring the graph.
    """
    def __init__(self, graph, points, tolerance=0.1, initial_tolerance=None):
        self._graph = graph
        points = _np.asarray(points)
        self._points = points
        self._tolerance = tolerance

        agg = None
        if initial_tolerance is not None:
            _logger.debug("Performing initial spatial aggregation...")
            agg = _geometry.AggregatePointsViaGraphFast(points, initial_tolerance)
            points = agg.merged_points

        _logger.debug("Projecting %s points to graph", points.shape[0])
        edges, projected_points = self._project_to_graph(points)
        self._agg_points = projected_points
        self._lookup = list(range(projected_points.shape[0]))
        self._graph_points = edges
        if tolerance > 0:
            self._aggregate(points)
        if agg is not None:
            lookup = []
            for pt in self._points:
                i = agg.index(pt)
                lookup.append(self._lookup[i])
            self._lookup = lookup

    def _aggregate(self, points):
        _logger.debug("Performing aggregation")
        pl = _ocp_logger.ProgressLogger(points.shape[0], _datetime.timedelta(seconds=15), _logger)
        builder = _network.GraphBuilder()
        for i, choices in enumerate(self._initial_aggregate()):
            edge, t = self._graph_points[i]
            dist = LimitedNetworkDistance(self._graph, edge, t, self._tolerance)
            for j in choices:
                try:
                    if i != j and dist.distance(*self._graph_points[j]) <= self._tolerance:
                        builder.add_edge(i, j)
                except ValueError:
                    pass
            pl.increase_count()

        builder.remove_duplicate_edges()
        builder.vertices.update(range(points.shape[0]))
        g = builder.build()
        _logger.debug("Performing final aggregation...")
        pl = _ocp_logger.ProgressLogger(points.shape[0], _datetime.timedelta(seconds=15), _logger)
        agg_points = []
        lookup = dict()
        agged_graph_points = []
        for com in _network.connected_components(g):
            com = list(com)
            pts = self._agg_points[com]
            centroid = _np.mean(pts, axis=0)
            i = _np.argmin( _np.sum((pts - centroid)**2, axis=1) )
            agg_points.append(pts[i])
            agged_graph_points.append(self._graph_points[com[i]])
            for j in com:
                lookup[j] = len(agg_points) - 1
            pl.add_to_count(len(com))
        self._agg_points = _np.asarray(agg_points)
        self._lookup = [lookup[i] for i in range(points.shape[0])]
        self._graph_points = agged_graph_points

    def _initial_aggregate(self):
        _logger.debug("Performing initial aggregation...")
        index = self._make_index()
        d = self._tolerance / 20
        return [list(index.intersection((x-d, y-d, x+d, y+d)))
                for x,y in self._agg_points]

    def _make_index(self):
        def index_gen():
            d = self._tolerance * 1.05
            for i, (x, y) in enumerate(self._agg_points):
                bounds = (x-d, y-d, x+d, y+d)
                yield i, bounds, None
        return _rtree.index.Index(index_gen())

    @property
    def points(self):
        """Array of the input points."""
        return self._points

    @property
    def graph(self):
        """The input graph."""
        return self._graph

    @property
    def projected_points(self):
        """Array of projected and aggregated points."""
        return self._agg_points

    @property
    def to_projected_lookup(self):
        """A list, same length as the number of input points, giving a map from
        input points to indicies into :attr:`projected_points`."""
        return self._lookup

    @property
    def graph_points(self):
        """List of projected and aggregated points, in the format of pairs
        `(edge, t)` where `edge` is the edge in :attr:`graph` and `t` is the
        distance along that edge."""
        return self._graph_points

    def _project_to_graph(self, points):
        edges = []
        projected_points = []
        for pt in points:
            edge, t = self._graph.project_point_to_graph(*pt)
            projected_points.append(self._graph.edge_to_coords(*edge, t))
            ei, orient = self._graph.find_edge(*edge)
            if orient < 0:
                t = 1 - t
            edges.append((ei, t))
        return edges, _np.asarray(projected_points)


class FlowPoints():
    """For each input point on the graph, find the subset of the graph which
    can be reached using a walk from the starting point:

    - Which always continues `min_distance` from the starting point;
    - Can continue up to `max_distance`;
    - Any shortest path will be stopped at `min_distance` if another input
      point is encountered.  (We do not consider all paths, so for a very
      multiply connected graph, this might behave a bit strangely.)

    :param graph: The graph to use.
    :param points: The input points, as pairs `(edge, t)` where `edge` is an
      edge index in `graph`, and `t` between 0 and 1 is the distance along
      `edge`.
    :param min_distance: The distance to always travel up to.
    :param max_distance: The maximum distance to travel, if not "blocked"
      by another point.
    """
    def __init__(self, graph, points, min_distance, max_distance):
        self._graph = graph
        self._points = points
        self._min_distance = min_distance
        self._max_distance = max_distance
        if max_distance < min_distance:
            raise ValueError()
        
        self._used_edges = dict()
        for e, t in self._points:
            if e not in self._used_edges:
                self._used_edges[e] = []
            self._used_edges[e].append(t)
        for e in self._used_edges:
            self._used_edges[e].sort()

    @property
    def graph(self):
        """The input graph"""
        return self._graph

    @property
    def input_points(self):
        """The input points"""
        return self._points

    def flow(self, index):
        """For the point given by `index` return the subset of the graph
        which can be reached.
        
        :param index: Into :attr:`input_points`.
        """
        edge, t = self._points[index]
        dist = LimitedNetworkDistance(self._graph, edge, t, self._max_distance)
        inverse_paths = dict()
        for target, source in dist.paths.items():
            if source not in inverse_paths:
                inverse_paths[source] = set()
            inverse_paths[source].add(target)
        flower = Flower(self._graph, self._min_distance, self._max_distance, self._used_edges)
        v1, v2 = self._graph.edges[edge]
        states, parts = [], []
        for start in [Flower.State(v1, v2, t, 0, False), Flower.State(v2, v1, 1-t, 0, False)]:
            p, s = flower.from_current_position(start, True)
            parts.append(p)
            if s is not None:
                states.append(s)

        while len(states) > 0:
            state = states.pop()
            if state.blocked and state.distance >= self._min_distance:
                continue
            if state.v1 not in inverse_paths:
                continue
            for v2 in inverse_paths[state.v1]:
                if v2 == state.v1:
                    continue
                s = Flower.State(state.v1, v2, state.t, state.distance, state.blocked)
                p, s = flower.from_current_position(s)
                parts.append(p)
                if s is not None:
                    states.append(s)
            
        return GraphSubSet(self._graph, self._merge_parts_to_subset(parts))
    
    def _merge_parts_to_subset(self, parts):
        by_edge = dict()
        for edge, orient, t0, t1 in parts:
            if edge not in by_edge:
                by_edge[edge] = []
            if orient == -1:
                t0, t1 = 1 - t1, 1 - t0
            if t0 > t1:
                t0, t1 = t1, t0
            by_edge[edge].append((t0, t1))

        subset = []
        for edge in by_edge:
            interval = Intervals(by_edge[edge], True)
            bits = list(interval.buffer())
            if len(bits) == 1 and bits[0][0] == 0 and bits[0][1] == 1:
                subset.append((edge, None))
            else:
                subset.append((edge, bits))
        return subset


class Intervals():
    """Represents a union of disjoint closed intervals."""
    def __init__(self, intervals, with_overlap=False):
        self._intervals = []
        for a, b in intervals:
            if a > b:
                a, b = b, a
            self._intervals.append((a,b))
        self._intervals.sort()
        
        if with_overlap:
            self._intervals = self._merge()
        else:
            for i in range(len(self._intervals) - 1):
                low_b = self._intervals[i][1]
                high_a = self._intervals[i + 1][0]
                if not low_b < high_a:
                    raise ValueError("Intervals are not disjoint")
            
    def __add__(self, other_intervals):
        intervals = list(self._intervals)
        for i in other_intervals._intervals:
            intervals.append(i)
        intervals.sort(key = lambda i : i[0])
        
        reduced_intervals = [intervals[0]]
        for next_int in intervals[1:]:
            if reduced_intervals[-1][1] >= next_int[0]:
                reduced_intervals[-1] = (reduced_intervals[-1][0], next_int[1])
            else:
                reduced_intervals.append(next_int)
        return Intervals(reduced_intervals)
        
    def _merge(self, delta=1e-8):
        if len(self._intervals) == 0:
            return []
        reduced_intervals = [self._intervals[0]]
        for next_int in self._intervals[1:]:
            if reduced_intervals[-1][1] + delta >= next_int[0]:
                reduced_intervals[-1] = (reduced_intervals[-1][0], next_int[1])
            else:
                reduced_intervals.append(next_int)
        return reduced_intervals

    def buffer(self, delta=1e-8):
        """Merge the intervals up to the `delta` value.
        
        :return: A new instance
        """
        if len(self._intervals) == 0:
            return self
        return Intervals(self._merge(delta))
    
    def __iter__(self):
        for a, b in self._intervals:
            yield (a, b)
    
    def __repr__(self):
        s = "Intervals("
        s += ", ".join("[{}, {}]".format(a, b)  for a, b in self._intervals)
        return s + ")"
        

class Flower():
    """As in Flow-er not the thing which attracts Bees.

    Factored out to allow testing, as the code is _horrible_.
    """
    def __init__(self, graph, min_distance, max_distance, used_edges):
        self._graph = graph
        self._min_distance = min_distance
        self._max_distance = max_distance
        self._used_edges = used_edges

    State = _collections.namedtuple("_State", "v1 v2 t distance blocked")

    def from_current_position(self, state, ignore_initial_t=False):
        """Start at `t` in `[0,1]` between v1 and v2 (in that order) and
        consider how far we can travel, supposing we have already travelled
        `distance` and are `blocked` or not.
        """
        if state.blocked:
            assert state.distance < self._min_distance

        edge, orient = self._graph.find_edge(state.v1, state.v2)
        edge_length = self._graph.lengths[edge]

        blocks = self.points_on_edge(edge, orient, state.t, 1)
        if ignore_initial_t:
            blocks = [t for t in blocks if t > state.t + 1e-8]
        else:
            blocks = [t for t in blocks if t >= state.t]
        if len(blocks) == 0:
            t_block = None
        else:
            t_block = min(blocks)
            
        t_min = state.t + (self._min_distance - state.distance) / edge_length
        t_max = state.t + (self._max_distance - state.distance) / edge_length
        
        t_new = max(state.t, t_min)
        if t_block is None:
            t_new = max(t_new, t_max)
        else:
            t_new = max(t_new, min(t_block, t_max))

        if t_new <= 1:
            part = (edge, orient, state.t, t_new)
            newstate = None
        else:
            part = (edge, orient, state.t, 1)
            if t_block is None:
                blocked = False
            else:
                blocked = (t_new >= t_block)
            newstate = self.State(v1=state.v2, v2=None, t=0,
                    distance=state.distance + (1 - state.t) * edge_length,
                    blocked=blocked)
            
        return part, newstate

    def points_on_edge(self, edge, orient, s=None, t=None):
        """If `s` is `None` then find the used locations on the edge, taking
        account of the orientation.  Otherwise, intersect with the interval
        `[s, t]`."""
        if edge not in self._used_edges:
            return []
        if s is None:
            used = self._used_edges[edge]
            if orient == 1:
                return list(used)
            return [1-t for t in used]
        if orient == -1:
            s, t = 1-s, 1-t
        if s > t:
            s, t = t, s
        if orient == 1:
            return [x for x in self._used_edges[edge] if s <= x and x <= t]
        return [1 - x for x in self._used_edges[edge] if s <= x and x <= t]


class GraphSubSet():
    """Represents a subset of a graph.
    
    :param graph: The graph
    :param edges: The edges in the subset, a list of pairs `(edge, parts)` where
      `edge` is the edge in `graph`, and `parts` is either `None` to indicate the
      whole edge, or an iterable of pairs `(s,t)` where `s <= t` is the subinterval
      `[s,t]` of `[0,1]` indicating a part of the edge.
    """
    def __init__(self, graph, edges):
        self._graph = graph
        self._edges = list(edges)
        self._edges_dict = {e : v for (e,v) in self._edges}
        self._p = None

    @property
    def graph(self):
        return self._graph

    @property
    def edges(self):
        return self._edges

    def contains(self, edge, t):
        """Does the specified point live in the subset?"""
        if edge not in self._edges_dict:
            return False
        parts = self._edges_dict[edge]
        if parts is None:
            return True
        for part in parts:
            if part[0] <= t and t <= part[1]:
                return True
        return False

    @staticmethod
    def distribute_into_parts(t, parts):
        """Find the absolute location given by fraction `t` into
        the list of intervals `parts`."""
        target = sum(b-a for a, b in parts) * t
        done_length = 0
        for a, b in parts:
            next_length = b - a
            if done_length + next_length >= target:
                return a + target - done_length
            done_length += next_length
        return parts[-1][1]

    def sample(self, size=1):
        """Sample uniformly at random from the subset, according to edge
        length.  Uses :mod:`numpy.random`.
        
        :return: List of pairs `(edge, t)` in the usual format.
        """
        if self._p is None:
            lengths = []
            for edge, parts in self._edges:
                if parts is None:
                    lengths.append(self._graph.lengths[edge])
                else:
                    lengths.append(sum(b-a for a,b in parts) * self._graph.lengths[edge])
            lengths = _np.asarray(lengths)
            norm = _np.sum(lengths)
            if norm <= 0:
                raise ValueError("Lengths of segments is zero!", self._edges)
            self._p = lengths / norm

        indicies = _np.random.choice(len(self._p), size, p=self._p)
        ts = _np.random.random(size)

        out = []        
        for i, t in zip(indicies, ts):
            edge, parts = self._edges[i]
            if parts is not None:
                t = self.distribute_into_parts(t, parts)
            out.append((edge, t))

        if size == 1:
            return out[0]
        return out

    def as_lines(self):
        """As `graph.as_lines()` but only for the subset represented."""
        try:
            lines = self._graph.as_lines()
        except AttributeError:
            raise ValueError("Graph type does not support plotting.")
        out = []
        for e, parts in self._edges:
            if parts is None:
                out.append(lines[e])
            else:
                s = _np.asarray(lines[e][0])
                t = _np.asarray(lines[e][1])
                for a, b in parts:
                    c = s * (1 - a) + t * a
                    d = s * (1 - b) + t * b
                    out.append([tuple(c), tuple(d)])
        return out


class Redistributor():
    """Abstract away the process of redistributing:

    - Aggregate and project the points using :class:`NetworkProjectAggregate`
    - Construct a :class:`FlowPoints` instance
    - Abstract away (and speed up) the task of redistributing points

    :param graph: The graph to use
    :param points: Array of shape `(n,2)` giving the original points
    :param min_distance: When moving points around the network, the distance to
      always travel up to.
    :param max_distance: The maximum distance to travel, if not "blocked"
      by another point.
    :param tolerance: Distance at which to aggregate, on the network.
      Set to be `<=0` to skip the aggregation step.
    :param initial_tolerance: If not `None`, then initially group points up to
      this tolerance, ignoring the graph.
    """
    def __init__(self, graph, points, min_distance, max_distance, tolerance=10, initial_tolerance=0.5):
        self._agg = NetworkProjectAggregate(graph, points, tolerance, initial_tolerance)
        self._flow = FlowPoints(graph, self._agg.graph_points, min_distance, max_distance)
        self._cache = dict()
        self._point_lookup = None

    @property
    def aggregator(self):
        """The :class:`NetworkProjectAggregate` instance"""
        return self._agg

    @property
    def flow(self):
        """The :class:`FlowPoints`"""
        return self._flow

    def redistribute(self, index):
        """Return a new location for the point which is `index` into the
        original input list."""
        i = self._agg.to_projected_lookup[index]
        if i not in self._cache or len(self._cache[i]) == 0:
            subset = self._flow.flow(i)
            self._cache[i] = subset.sample(100)
        e, t = self._cache[i].pop()
        graph = self._flow.graph
        return graph.edge_to_coords(*graph.edges[e], t)

    def redistribute_from_point(self, pt):
        """Return a new location for the point, which should have been in the
        input data."""
        if self._point_lookup is None:
            self._point_lookup = {tuple(pt) : i for i, pt in enumerate(self._agg.points)}
        pt = tuple(pt)
        if pt not in self._point_lookup:
            raise ValueError("Point was not in original collection.")
        return self.redistribute(self._point_lookup[pt])
