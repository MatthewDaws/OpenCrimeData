import pytest

import opencrimedata.tiger_lines as tiger_lines
import os, sys
import numpy as np

def test_load_roads():
    filename = os.path.join("tests", "data", "test_lines")
    out = list(tiger_lines.load_roads(filename))
    _assert_roads(out)

def _assert_roads(out):
    assert out[0][0] == "47th Pl Exd"
    expected_pts = np.asarray([(-87.595765, 41.814607999999986),
        (-87.595702, 41.81463399999999),
        (-87.59551599999999, 41.81471299999999),
        (-87.59545399999999, 41.81474)])
    np.testing.assert_allclose(expected_pts, out[0][1])
    assert len(out) == 5

def test_load_roads_zip():
    if sys.platform == "linux":
        # ZIP doesn't seem to work on linux for me.
        return
    filename = os.path.join("tests", "data", "test_lines.zip")
    out = list(tiger_lines.load_roads_zip(filename))
    _assert_roads(out)

def test_load_edges():
    filename = os.path.join("tests", "data", "test_edges")
    out = list(tiger_lines.load_edges(filename))
    _assert_edges(out)

def _assert_edges(out):
    assert len(out) == 5
    assert out[0].fullname is None
    assert out[1].fullname == "Great Lakes"
    assert out[2].fullname == "Jeffery Ave"
    assert out[2].left_address_from == "22501"
    assert out[2].left_address_to == "22519"
    assert out[2].right_address_from == "22442"
    assert out[2].right_address_to == "22498"

def test_load_edges_zip():
    if sys.platform == "linux":
        # ZIP doesn't seem to work on linux for me.
        return
    filename = os.path.join("tests", "data", "test_edges.zip")
    out = list(tiger_lines.load_edges_zip(filename))
    _assert_edges(out)

def test_filter_edge_names():
    def edge(name):
        return tiger_lines.Edge(name, None, None, None, None, [])
    data = [edge(None), edge("Bob"), edge("Alley"), edge("Dave"), edge("CA RR")]
    out = list(tiger_lines.filter_edge_names(data))
    assert out == [data[1], data[3]]

def test_roads_to_graph():
    roads = [
        ("one", [[0,0], [10,0], [10,5]]),
        ("two", [[10,5], [8,5], [10,0], [0,0], [5,-1]])
        ]
    graph, names = tiger_lines.roads_to_graph(roads)
    assert set(graph.vertices.values()) == {(0,0), (10,0), (10,5), (8,5), (5,-1)}
    out = {}
    for i, (v1, v2) in enumerate(graph.edges):
        x, y = graph.vertices[v1]
        xx, yy = graph.vertices[v2]
        key = (x,y,xx,yy)
        out[key] = names[i]
    assert out[(0,0, 10,0)] == {"one", "two"}
    assert out[(10,0, 10,5)] == {"one"}
    assert out[(10,5, 8,5)] == {"two"}
    assert out[(8,5, 10,0)] == {"two"}
    assert out[(0,0, 5,-1)] == {"two"}
    assert len(out) == 5
    
def test_edges_to_graph():
    edges = [
        tiger_lines.Edge("one", "a", "b", "c", "d", [[0,0], [10,0], [10,5]]),
        tiger_lines.Edge("two", "a1", "b1", "c1", "d1", [[10,5], [8,5], [10,0], [5,-1]])
        ]
    graph, names = tiger_lines.edges_to_graph(edges)
    assert set(graph.vertices.values()) == {(0,0), (10,0), (10,5), (8,5), (5,-1)}
    out = {}
    for i, (v1, v2) in enumerate(graph.edges):
        x, y = graph.vertices[v1]
        xx, yy = graph.vertices[v2]
        key = (x,y,xx,yy)
        out[key] = names[i]
    one = tiger_lines.EdgeNoLine("one", "a", "b", "c", "d")
    two = tiger_lines.EdgeNoLine("two", "a1", "b1", "c1", "d1")
    assert out[(0,0, 10,0)] == one
    assert out[(10,0, 10,5)] == one
    assert out[(10,5, 8,5)] == two
    assert out[(8,5, 10,0)] == two
    assert out[(10,0, 5,-1)] == two
    assert len(out) == 5
