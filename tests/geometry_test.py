import pytest
import unittest.mock as mock
import numpy as np
import shapely.geometry

import opencrimedata.geometry as geometry

def test_AggregatePoints():
    pts = [(1,1), (0,0), (1,1), (0.01,0)]
    ap = geometry.AggregatePoints(pts)
    print("Could be a bad test...")
    assert set(ap.merged_points) == {(0,0), (1,1)}
    assert ap[(1,1)] == (1,1)
    assert ap[(0,0)] == (0,0)
    assert ap[(0.01,0)] == (0,0)
    
def test_AggregatePoints1():
    pts = np.random.random(size=(1000,2))
    ap = geometry.AggregatePoints(pts)
    for pt in pts:
        assert np.sqrt(np.sum((ap[pt] - pt)**2)) < 0.1

def test_AggregatePointsViaGraph():
    pts = [(1,1), (0,0), (1,1), (0.01,0)]
    ap = geometry.AggregatePointsViaGraph(pts)
    print("Could be a bad test...")
    assert len(ap.merged_points) == 2
    assert set(tuple(pt) for pt in ap.merged_points) == {(0,0), (1,1)}
    assert tuple(ap[(1,1)]) == (1,1)
    assert tuple(ap[(0,0)]) == (0,0)
    assert tuple(ap[(0.01,0)]) == (0,0)

@pytest.fixture
def rd1():
    p1 = shapely.geometry.Polygon([[0,0], [1,0], [1,1]])
    p2 = shapely.geometry.Polygon([[2,0], [2,1], [3,2]])
    return geometry.Redistributor([p1,p2])    

def test_Redistributor_find(rd1):
    assert rd1.find_containing_polygon(0, 1) == []
    assert rd1.find_containing_polygon(0, 0) == [0]
    assert rd1.find_containing_polygon(0.2, 0.1) == [0]
    assert rd1.find_containing_polygon(2.2, 1) == [1]

def test_Redistributor_redistribute(rd1):
    assert rd1.redistribute(0, 1) == []
    
    out = np.asarray(rd1.redistribute(0, 0))
    out = np.atleast_2d(out)
    assert len(out.shape) == 2 and out.shape[1] == 2
    assert out.shape[0] >= 1
    for x,y in out:
        pt = shapely.geometry.Point(x, y)
        assert pt.intersects(rd1.polygons[0])

    out = np.asarray(rd1.redistribute(0, 0, 100))
    assert out.shape[0] >= 100
    
    out = np.asarray(rd1.redistribute_from_poly(1, 10))
    assert out.shape[0] >= 10
    for x,y in out:
        pt = shapely.geometry.Point(x, y)
        assert pt.intersects(rd1.polygons[1])

@pytest.fixture
def crd1():
    p1 = shapely.geometry.Polygon([[0,0], [1,0], [1,1]])
    p2 = shapely.geometry.Polygon([[2,0], [2,1], [3,2]])
    return geometry.CachingRedistributor([p1,p2])    

def test_CachingRedistributor(crd1):
    out = np.asarray(crd1.redistribute_from_poly(1, 10))
    assert out.shape[0] == 10
    for x,y in out:
        pt = shapely.geometry.Point(x, y)
        assert pt.intersects(crd1.polygons[1])

def test_CachingRedistributor_redistribute_within_radius(crd1):
    assert crd1.redistribute_within_radius(0, 1, 10) is None
    
    x, y = crd1.redistribute_within_radius(0, 0, 0.3)
    pt = shapely.geometry.Point(x, y)
    assert pt.intersects(crd1.polygons[0])
    assert x*x+y*y <= 0.3**2

def test_ClosestPoint():
    cl = geometry.ClosestPoint([[0,0], [0,1], [1,1], [1,0]], 0.01)

    i, pt = cl.closest([0.1, 0.1])
    assert i == 0
    np.testing.assert_allclose(pt, [0,0])

    i, pt = cl.closest([0.9, 0.1])
    assert i == 3
    np.testing.assert_allclose(pt, [1,0])

    indices, points = cl.all_in_disc([0.1, 0.1], 0.5)
    assert indices == [0]
    np.testing.assert_allclose(points, [[0,0]])

    indices, points = cl.all_in_disc([0.1, 0.1], 0.12)
    np.testing.assert_allclose(indices, [])
    np.testing.assert_allclose(points, np.empty((0,2)))

    indices, points = cl.all_in_disc([0.1, 0.1], 1)
    np.testing.assert_allclose(indices, [0,1,3])
    np.testing.assert_allclose(points, [[0,0], [0,1], [1,0]])
