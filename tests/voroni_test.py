import pytest
from unittest import mock
import numpy as np
import opencrimedata.voroni as voroni
import open_cp.network

@pytest.fixture
def voronimock():
    with mock.patch("open_cp.geometry.Voroni") as m:
        yield m

@pytest.fixture
def agmock():
    with mock.patch("opencrimedata.voroni.geometry.AggregatePointsViaGraph") as m:
        yield m

@pytest.fixture
def points():
    return np.array([[0,0], [1,1]])

@pytest.fixture
def vor(points, agmock, voronimock):
    return voroni.Voroni(points, 12.3)

def test_Voroni_construct(vor, points, agmock, voronimock):
    agmock.assert_called_with(points, 12.3)
    voronimock.assert_called_with(agmock.return_value.merged_points)
    
    assert vor.aggregated_points == agmock.return_value
    assert vor.merged_points == agmock.return_value.merged_points
    assert vor.voroni == voronimock.return_value

def test_Voroni_map_to_merged(vor, agmock):
    ag = agmock.return_value
    assert vor.map_to_merged_point((1,4)) == ag.__getitem__.return_value
    ag.__getitem__.assert_called_with((1,4))

def test_Voroni_all_polys(vor, voronimock):
    v = voronimock.return_value
    v.points = list(range(10))
    
    assert list(vor.all_polygons(54.5)) == [v.polygon_for_by_distance.return_value for _ in range(10)]
    assert v.polygon_for_by_distance.call_args_list == [
            mock.call(i, 54.5) for i in range(10) ]

@pytest.fixture
def shgeomock():
    with mock.patch("shapely.geometry") as m:
        yield m

def test_Voroni_all_polygons_clipped(vor, voronimock, shgeomock):
    v = voronimock.return_value
    v.points = list(range(10))
    geo = mock.Mock()
    assert list(vor.all_polygons_clipped(geo, 12.3)) == [
            shgeomock.Polygon.return_value.intersection.return_value
            for _ in range(10) ]
    assert shgeomock.Polygon.call_args_list == [
            mock.call(v.polygon_for_by_distance.return_value) for _ in range(10)]
    assert shgeomock.Polygon.return_value.intersection.call_args_list == [
            mock.call(geo) for _ in range(10) ]

@pytest.fixture
def rdmock():
    with mock.patch("opencrimedata.voroni.geometry.Redistributor") as m:
        yield m

def test_Voroni_to_redistributor(vor, rdmock, voronimock):
    v = voronimock.return_value
    v.points = list(range(10))
    assert vor.to_redistributor(None) == rdmock.return_value
    polys = [v.polygon_for_by_distance.return_value for _ in range(10)]
    rdmock.assert_called_with(polys)
    
def test_Voroni_to_redistributor_clipping(vor, rdmock, voronimock, shgeomock):
    v = voronimock.return_value
    v.points = list(range(10))
    geo = mock.Mock()
    poly = shgeomock.Polygon.return_value.intersection.return_value
    poly.is_empty = False
    assert vor.to_redistributor(geo) == rdmock.return_value
    polys = [poly for _ in range(10)]
    rdmock.assert_called_with(polys)

    poly.is_empty = True
    assert vor.to_redistributor(geo) == rdmock.return_value
    rdmock.assert_called_with([])

@pytest.fixture
def graph():
    b = open_cp.network.PlanarGraphBuilder()
    b.add_vertex(0,0)
    b.add_vertex(1,0)
    b.add_vertex(3,0)
    b.add_vertex(1,2)
    b.add_edge(0,1)
    b.add_edge(1,2)
    b.add_edge(2,3)
    b.add_edge(3,1)
    return b.build()

def test_VoroniGraphSegments(graph):
    v = voroni.VoroniGraphSegments(graph, [[0,1],[3]])

    assert v.segments == [{1,0}, {3}]

    p = np.asarray(v.polygon_for_segment(1).exterior)
    assert p.shape == (4,2)
    np.testing.assert_allclose(p[2], [1.25, 0.25])

    p = np.asarray(v.polygon_for_segment(0).exterior)
    assert p.shape == (6,2)
    np.testing.assert_allclose(p[2], [1.25, 0.25])
