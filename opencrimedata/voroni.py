"""
voroni
~~~~~~

Some routines to allow forming Voroni diagrams, and constructing points from
them.
"""

import numpy as _np
from . import geometry
import open_cp.geometry
import open_cp.logger
import shapely.geometry
import datetime as _dt
import logging as _logging

_logger = _logging.getLogger(__name__)

class _BaseVoroni():
    @property
    def voroni(self):
        """The Voroni diagram object"""
        return self._voroni
        
    def all_polygons(self, distance=100):
        """Return an iterator of all polygons.  Each polygon will be a list
        of points.
        
        :param distance: The (minimum) distance to ensure that edge polygons
          enclose the point by.
        """
        for i in range(len(self._voroni.points)):
            yield self._voroni.polygon_for_by_distance(i, distance)

    def all_polygons_clipped(self, geo, distance=100):
        """Return an iterator of all polygons, clipped to the geometry.  Each
        polygon will be a `shapely` object, which may be empty!
        
        :param geo: The geometry to clip to.
        :param distance: The (minimum) distance to ensure that edge polygons
          enclose the point by.
        """
        for p in self.all_polygons(distance):
            try:
                yield shapely.geometry.Polygon(p).intersection(geo)
            except:
                yield p.intersection(geo)

    def _to_shapely(self, polygon_like_object):
        try:
            p = shapely.geometry.Polygon(polygon_like_object)
            if p.is_empty:
                return polygon_like_object
            return p
        except:
            return polygon_like_object

    def to_redistributor(self, geo, distance=100):
        """Construct an instance of :class:`geometry.Redistributor` using
        clipped polygons.
        
        :param geo: The geometry to clip to.  If `None` then perform no
          clipping.
        :param distance: The (minimum) distance to ensure that edge polygons
          enclose the point by.
        """
        if geo is None:
            polys = [self._to_shapely(p) for p in self.all_polygons(distance)]
        else:
            polys = list(self.all_polygons_clipped(geo, distance))
            polys = [p for p in polys if not p.is_empty]
        return geometry.Redistributor(polys)


class Voroni(_BaseVoroni):
    """Use a Voroni diagram to move points.
    
    :param points: Initial points to merge and construct the voroni diagram
      around.
    :param tolerance: The distance at which to merge points.  We use the
      "graph" based merging procedure, so if we have three points a, b and c,
      and a, b are within the tolerance, and b, c are within the tolerance,
      then all 3 points will be merged.
    """
    def __init__(self, points, tolerance=1):
        points = _np.asarray(points)
        _logger.debug("Aggregating close points from %s input points", len(points))
        self._agg_points = geometry.AggregatePointsViaGraph(points, tolerance)
        _logger.debug("Constructing Voroni diagram from %s merged points", len(self._agg_points.merged_points))
        self._voroni = open_cp.geometry.Voroni(self._agg_points.merged_points)
        
    @property
    def aggregated_points(self):
        """The "aggregated points" object"""
        return self._agg_points
    
    @property
    def merged_points(self):
        """Array of merged points"""
        return self._agg_points.merged_points
    
    def map_to_merged_point(self, pt):
        """Return the "merged point" which corresponds to the given point,
        which must have been a point in the input data."""
        return self._agg_points[pt]


class VoroniMergedCells(_BaseVoroni):
    """Construct a Voroni diagram where we merge (set-theoretic union) some
    of the cells.
    
    :param points: Array of shape `(n,2)` of `n` points to form the base
      Voroni diagram from.
    :param sections: Iterable of iterables of indices into `points` giving
      the cells to be merged.
    """
    def __init__(self, points, sections):
        _logger.debug("Constructing Voroni diagram from %s points", len(points))
        self._voroni = open_cp.geometry.Voroni(points)
        self._sections = list(set(x) for x in sections)
        
    @property
    def sections(self):
        """List of sets of indicies of points which will be merged."""
        return self._sections
    
    def polygon_for_section(self, section_index, distance=100):
        """Return the (merged) polygon for the section given by
        `section_index` into :attr:`sections`.

        :param distance: The (minimum) distance to ensure that edge polygons
          enclose the point by.

        :return: A `shapely` polygon object.
        """
        polygons = [ self._voroni.polygon_for_by_distance(e, distance)
            for e in self._sections[section_index] ]
        poly = shapely.geometry.Polygon(polygons[0])
        for p in polygons[1:]:
            poly = poly.union(shapely.geometry.Polygon(p))
        return poly

    def all_polygons(self, distance=100):
        """Return an iterator of all polygons.  Each polygon will be a list
        of points.
        
        :param distance: The (minimum) distance to ensure that edge polygons
          enclose the point by.
        """
        _logger.debug("Generating all merged polygons")
        pl = open_cp.logger.ProgressLogger(len(self._sections),
                _dt.timedelta(seconds=20), _logger)
        for i, _ in enumerate(self._sections):
            yield self.polygon_for_section(i, distance)
            pl.increase_count()


class VoroniGraphSegments(VoroniMergedCells):
    """Construct a Voroni diagram from "segments" of a graph.  Each segment
    should be a path in the graph, and segments should only intersect at their
    end points.  We use the mid-point of each edge to form an initial Voroni
    diagram (which can be accessed from the :attr:`voroni` ) and then the cells
    for each segment are merged, which can be accessed by the method
    :meth:`all_polygons`.

    :param graph: The graph the segments come from.
    :param segments: An iterable of iterables of edge indices, each forming
      a "segment".
    """
    def __init__(self, graph, segments):
        self._segments = [ set(seg) for seg in segments ]
        used_edges = set()
        for seg in self._segments:
            used_edges.update(seg)
        used_edges = list(used_edges)
        used_edges.sort()
        edge_lookup = {e:i for i,e in enumerate(used_edges)}
        sections = []
        for seg in self._segments:
            sections.append( [edge_lookup[e] for e in seg] )

        points = []
        for e in used_edges:
            k1, k2 = graph.edges[e]
            x1, y1 = graph.vertices[k1]
            x2, y2 = graph.vertices[k2]
            points.append( ((x1 + x2) / 2, (y1 + y2) / 2) )
        
        super().__init__(points, sections)
        
    @property
    def segments(self):
        """List of segments."""
        return self._segments

    def polygon_for_segment(self, segment_index, distance=100):
        """Return the (merged) polygon for the segment given by
        `segment_index` into :attr:`segments`.

        :param distance: The (minimum) distance to ensure that edge polygons
          enclose the point by.

        :return: A `shapely` polygon object.
        """
        return self.polygon_for_section(segment_index, distance)
