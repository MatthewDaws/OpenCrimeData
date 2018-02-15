import pytest

import opencrimedata.network as network

import open_cp.network
import numpy as np

@pytest.fixture
def graph():
    b = open_cp.network.PlanarGraphGeoBuilder()
    b.add_path([(0,0), (10,0)])
    b.add_path([(10,10), (10,0)])
    b.add_path([(10,10), (0,10)])
    b.add_path([(0,10), (0,0)])
    return b.build()

def test_NetworkProjectAggregate_noagg(graph):
    points = [[0.1,0], [3,1], [9,7]]
    agg = network.NetworkProjectAggregate(graph, points, 0)

    np.testing.assert_allclose(agg.points, points)
    assert agg.graph is graph
    np.testing.assert_allclose(agg.projected_points, [[0.1,0], [3,0], [10,7]])
    assert agg.to_projected_lookup == [0,1,2]
    assert agg.graph_points == [(0,0.01), (0,0.3), (1,0.3)]

def test_NetworkProjectAggregate(graph):
    points = [[3,0], [3.2, 1], [3.3, 2]]
    agg = network.NetworkProjectAggregate(graph, points, 1)

    np.testing.assert_allclose(agg.points, points)
    np.testing.assert_allclose(agg.projected_points, [[3.2,0]])
    assert agg.to_projected_lookup == [0,0,0]
    assert agg.graph_points == [(0,0.32)]
    
def test_NetworkProjectAggregate_initial_agg(graph):
    points = [[3,0], [3.2, 1], [3.3, 2]]
    agg = network.NetworkProjectAggregate(graph, points, 1, 0)

    np.testing.assert_allclose(agg.points, points)
    np.testing.assert_allclose(agg.projected_points, [[3.2,0]])
    assert agg.to_projected_lookup == [0,0,0]
    assert agg.graph_points == [(0,0.32)]

def test_NetworkProjectAggregate_initial_agg1(graph):
    points = [[3,0], [3.01,0.01], [3.2, 1], [3.3, 2]]
    agg = network.NetworkProjectAggregate(graph, points, 1, 0.05)

    np.testing.assert_allclose(agg.points, points)
    np.testing.assert_allclose(agg.projected_points, [[3.2,0]])
    assert agg.to_projected_lookup == [0,0,0,0]
    assert agg.graph_points == [(0,0.32)]

def test_NetworkProjectAggregate1(graph):
    points = [[3,0], [3.2, 1], [3.3, 2], [5, 4]]
    agg = network.NetworkProjectAggregate(graph, points, 1)

    np.testing.assert_allclose(agg.points, points)
    np.testing.assert_allclose(agg.projected_points, [[3.2,0], [5,0]])
    assert agg.to_projected_lookup == [0,0,0,1]
    assert agg.graph_points == [(0,0.32), (0,0.5)]

def test_shortest_edge_paths(graph):
    assert graph.vertices == {0:(0,0), 1:(10,0), 2:(10,10), 3:(0,10)}
    
    lengths, prevs = open_cp.network.shortest_edge_paths(graph, 0, 0)
    assert lengths == {0:0, 1:10, 2:20, 3:10}
    print("Note that `2:3` is also allowed.")
    assert prevs == {0:0, 1:1, 2:1, 3:0}

    lengths, prevs = open_cp.network.shortest_edge_paths(graph, 0, 0.1)
    assert lengths == {0:1, 1:9, 2:19, 3:11}
    assert prevs == {0:0, 1:1, 2:1, 3:0}
    
    lengths, prevs = open_cp.network.shortest_edge_paths(graph, 1, 0.1)
    assert lengths == {0:19, 1:9, 2:1, 3:11}
    assert prevs == {0:1, 1:1, 2:2, 3:2}

def test_NetworkDistance(graph):
    dist = network.NetworkDistance(graph, 0, 0)
    assert dist.distance(0, 0) == pytest.approx(0)
    assert dist.distance(0, 0.5) == pytest.approx(5)
    assert dist.distance(1, 0) == pytest.approx(20)
    assert dist.distance(1, 1) == pytest.approx(10)

    dist = network.NetworkDistance(graph, 3, 0.5)
    assert dist.distance(0, 0) == pytest.approx(5)
    assert dist.distance(0, 0.5) == pytest.approx(10)
    assert dist.distance(3, 0.5) == pytest.approx(0)
    assert dist.distance(3, 0) == pytest.approx(5)
    assert dist.distance(3, 0.1) == pytest.approx(4)

@pytest.fixture
def graph1():
    b = open_cp.network.GraphBuilder()
    b.add_edge(0, 1)
    b.add_edge(0, 2)
    b.add_edge(2, 3)
    b.add_edge(2, 4)
    b.add_edge(4, 5)
    b.add_edge(5, 6)
    b.add_edge(0, 6)
    b.lengths = [1] * 7
    return b.build()

def test_LimitedNetworkDistance(graph):
    dist = network.LimitedNetworkDistance(graph, 0, 0, 2)
    assert dist.distance(0, 0) == pytest.approx(0)
    assert dist.distance(0, 0.5) == pytest.approx(5)
    assert dist.distance(1, 0) == pytest.approx(20)
    assert dist.distance(1, 1) == pytest.approx(10)
    assert dist.paths == {0:0, 1:1, 2:1, 3:0}

    dist = network.LimitedNetworkDistance(graph, 3, 0.5, 2)
    assert dist.distance(0, 0) == pytest.approx(5)
    assert dist.distance(0, 0.5) == pytest.approx(10)
    assert dist.distance(3, 0.5) == pytest.approx(0)
    assert dist.distance(3, 0) == pytest.approx(5)
    assert dist.distance(3, 0.1) == pytest.approx(4)
    assert dist.paths == {0:0, 3:3, 1:0, 2:3}

def test_LimitedNetworkDistance1(graph1):
    dist = network.LimitedNetworkDistance(graph1, 1, 0.2, 2)
    assert dist.distance(1, 0.5) == pytest.approx(0.3)
    assert dist.distance(0, 1) == pytest.approx(1.2)
    assert dist.distance(2, 1) == pytest.approx(1.8)
    assert dist.distance(6, 0.1) == pytest.approx(0.3)
    # Vertex 5 is too distant to care.
    p = dict(dist.paths)
    del p[5]
    assert p == {0:0, 1:0, 2:2, 3:2, 4:2, 6:0}

def test_GraphSubSet(graph1):
    edges = [(0, None), (2,None), (3,[(0,0.4), (0.7,0.7)]) ]
    ss = network.GraphSubSet(graph1, edges)

    assert ss.graph is graph1
    assert ss.edges == edges
    assert not ss.contains(1, 0.5)
    assert ss.contains(0,0)
    assert ss.contains(0,0.5)
    assert ss.contains(0,1)
    assert ss.contains(2,0.5)
    assert ss.contains(3, 0.7)
    assert ss.contains(3, 0.2)
    assert ss.contains(3, 0)
    assert ss.contains(3, 0.4)
    assert not ss.contains(3, 0.5)
    with pytest.raises(ValueError):
        lines = ss.as_lines()

def test_GraphSubSet_distribute_into_parts():
    ss = network.GraphSubSet(None, [])
    parts = [(0,0.4), (0.7,0.9)]
    assert ss.distribute_into_parts(0, parts) == pytest.approx(0)
    assert ss.distribute_into_parts(1, parts) == pytest.approx(0.9)
    assert ss.distribute_into_parts(0.5, parts) == pytest.approx(0.3)
    assert ss.distribute_into_parts(0.75, parts) == pytest.approx(0.6 * 0.75 - 0.4 + 0.7)

def test_GraphSubSet_sample(graph1):
    edges = [(0, None), (2,None), (3,[(0,0.4), (0.7,0.7)]) ]
    ss = network.GraphSubSet(graph1, edges)

    e, t = ss.sample()
    samples = ss.sample(10)
    assert len(samples) == 10

@pytest.fixture
def graph_small_builder():
    b = open_cp.network.GraphBuilder()
    b.add_edge(0, 1)
    b.lengths = [1]
    return b
    
def test_Flower_from_current_position(graph_small_builder):
    graph = graph_small_builder.build()
    
    flower = network.Flower(graph, 0.2, 100, {0:[0.1, 0.4]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.1, 0, False), True)
    assert part == pytest.approx((0, 1, 0.1, 0.4))
    assert ns is None
    
    flower = network.Flower(graph, 0.3, 100, {0:[0.1, 0.4]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.1, 0, False), True)
    assert part == pytest.approx((0, 1, 0.1, 0.4))
    assert ns is None
    
    flower = network.Flower(graph, 0.7, 100, {0:[0.1, 0.4]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.1, 0, False), True)
    assert part == pytest.approx((0, 1, 0.1, 0.8))
    assert ns is None

    flower = network.Flower(graph, 0.9, 100, {0:[0.1, 0.4]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.1, 0, False), True)
    assert part == pytest.approx((0, 1, 0.1, 1))
    assert ns is None

    flower = network.Flower(graph, 1, 100, {0:[0.1, 0.4]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.1, 0, False), True)
    assert part == pytest.approx((0, 1, 0.1, 1))
    assert tuple(ns) == (1, None, 0, 0.9, True)


    flower = network.Flower(graph, 0.2, 100, {0:[0.1]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.1, 0, False), True)
    assert part == pytest.approx((0, 1, 0.1, 1))
    assert tuple(ns) == (1, None, 0, 0.9, False)
    
    flower = network.Flower(graph, 0.9, 100, {0:[0.1]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.1, 0, False), True)
    assert part == pytest.approx((0, 1, 0.1, 1))
    assert tuple(ns) == (1, None, 0, 0.9, False)

    flower = network.Flower(graph, 1, 100, {0:[0.1]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.1, 0, False), True)
    assert part == pytest.approx((0, 1, 0.1, 1))
    assert tuple(ns) == (1, None, 0, 0.9, False)


    flower = network.Flower(graph, 0.3, 100, {0:[0.4]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.1, 0, False), False)
    assert part == pytest.approx((0, 1, 0.1, 0.4))
    assert ns is None

def assert_state(ns, d, b, v=1):
    assert tuple(ns)[:3] == (v, None, 0)
    assert ns.distance == pytest.approx(d)
    assert ns.blocked == b

def test_Flower_from_current_position_with_longer_edge(graph_small_builder):
    graph_small_builder.lengths = [2]
    graph = graph_small_builder.build()

    flower = network.Flower(graph, 0.7, 1.5, {0:[0.15]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.15, 0, False), True)
    assert part == pytest.approx((0, 1, 0.15, 0.9))
    assert ns is None
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.15, 0.5, False), True)
    assert part == pytest.approx((0, 1, 0.15, 0.65))
    assert ns is None

    flower = network.Flower(graph, 0.7, 2, {0:[0.15]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.15, 0, False), True)
    assert part == pytest.approx((0, 1, 0.15, 1))
    assert_state(ns, 1.7, False)


    flower = network.Flower(graph, 0.7, 1.5, {0:[0.3]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.15, 0, False), True)
    assert part == pytest.approx((0, 1, 0.15, 0.5))
    assert ns is None
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.15, 0.5, False), True)
    assert part == pytest.approx((0, 1, 0.15, 0.3))
    assert ns is None

    flower = network.Flower(graph, 1.7, 2, {0:[0.3]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.15, 0, False), True)
    assert part == pytest.approx((0, 1, 0.15, 1))
    assert ns is None

    flower = network.Flower(graph, 2, 2, {0:[0.3]})
    part, ns = flower.from_current_position(network.Flower.State(0, 1, 0.15, 0, False), True)
    assert part == pytest.approx((0, 1, 0.15, 1))
    assert_state(ns, 1.7, True)

def test_Flower_from_current_position_with_reversed_edges(graph_small_builder):
    graph_small_builder.lengths = [2]
    graph = graph_small_builder.build()

    flower = network.Flower(graph, 0.7, 1.5, {0:[0.85]})
    part, ns = flower.from_current_position(network.Flower.State(1, 0, 0.15, 0, False), True)
    assert part == pytest.approx((0, -1, 0.15, 0.9))
    assert ns is None

    flower = network.Flower(graph, 0.7, 2, {0:[0.85]})
    part, ns = flower.from_current_position(network.Flower.State(1, 0, 0.15, 0, False), True)
    assert part == pytest.approx((0, -1, 0.15, 1))
    assert_state(ns, 1.7, False, v=0)


@pytest.fixture
def graph2():
    b = open_cp.network.GraphBuilder()
    b.add_edge(0, 1)
    b.add_edge(0, 2)
    b.add_edge(2, 3)
    b.add_edge(2, 4)
    b.add_edge(4, 5)
    b.add_edge(5, 6)
    b.add_edge(0, 6)
    b.lengths = [2, 1, 3, 2, 3, 4, 2]
    return b.build()

def test_Flower_points_on_edge(graph2):
    flower = network.Flower(graph2, None, None, {1:[0,0.3,0.8]})

    assert flower.points_on_edge(0, 1) == []
    np.testing.assert_allclose(flower.points_on_edge(1, 1), [0, 0.3, 0.8])
    np.testing.assert_allclose(flower.points_on_edge(1, -1), [1, 0.7, 0.2])

    np.testing.assert_allclose(flower.points_on_edge(1, 1, 0.1, 0.2), [])
    np.testing.assert_allclose(flower.points_on_edge(1, 1, 0.1, 0.3), [0.3])
    np.testing.assert_allclose(flower.points_on_edge(1, -1, 0.1, 0.3), [0.2])

def test_Intervals():
    i = network.Intervals([])
    assert repr(i) == "Intervals()"
    i = network.Intervals([(5, 4)])
    assert repr(i) == "Intervals([4, 5])"
    i = network.Intervals([(5, 4), [2, 3]])
    assert repr(i) == "Intervals([2, 3], [4, 5])"
    with pytest.raises(ValueError):
        network.Intervals([(5, 4), [2, 4]])

    i1 = network.Intervals([])
    i2 = network.Intervals([(5, 4)])
    i = i1 + i2
    assert repr(i) == "Intervals([4, 5])"
    i = i2 + i1
    assert repr(i) == "Intervals([4, 5])"

    i1 = network.Intervals([[3, 2]])
    i = i1 + i2
    assert repr(i) == "Intervals([2, 3], [4, 5])"
    
    i1 = network.Intervals([[2, 4]])
    i = i1 + i2
    assert repr(i) == "Intervals([2, 5])"

    i = network.Intervals([[1,2], [3,4]]) + network.Intervals([[2,3]])
    assert repr(i) == "Intervals([1, 4])"
    
    i = network.Intervals([[1,2], [2.00000000000001, 3]])
    i = i.buffer()
    assert repr(i) == "Intervals([1, 3])"
    
    assert list(i) == [(1, 3)]

def test_Intervals_overlap():
    with pytest.raises(ValueError):
        network.Intervals([[0,0], [0,0.8]])
    
    i = network.Intervals([[0,0.8], [0,0]], True)
    assert repr(i) == "Intervals([0, 0.8])"

def test_FlowPoints_no_blocks(graph2):
    points = [(1, 0.2)]
    flow = network.FlowPoints(graph2, points, 1, 2)
    
    parts = flow.flow(0)
    subset = {e:v for e,v in parts.edges}
    assert subset[1] is None
    assert subset[0] == [(0, 0.9)]
    assert subset[2] == [(0, 1.2 / 3)]
    assert subset[3] == [(0, 1.2 / 2)]
    assert subset[6] == [(0, 1.8 / 2)]
    assert set(subset) == {0,1,2,3,6}

def test_FlowPoints(graph2):
    points = [(1, 0.2), (1, 0.9), (6, 0.5)]
    flow = network.FlowPoints(graph2, points, 0.5, 2)
    
    parts = flow.flow(0)
    by_edge = {e:v for e,v in parts.edges}
    assert by_edge[1] == [(0, 0.9)]
    assert by_edge[0] == [(0, 0.9)]
    assert by_edge[6] == [(0, 0.5)]
    assert set(by_edge) == {0,1,6}

@pytest.fixture
def geograph():
    b = open_cp.network.PlanarGraphGeoBuilder()
    b.add_path([(0,0), (2,0)])
    b.add_path([(2,0), (2,1)])
    b.add_path([(2,1), (0,2)])
    b.add_path([(0,2), (0,0)])
    return b.build()

def test_GraphSubSet_as_lines(geograph):
    ss = network.GraphSubSet(geograph, [(0,None), (1,[(0.2, 0.6)]), (2,None)])
    lines = ss.as_lines()
    assert len(lines) == 3
    assert lines[0] == pytest.approx(((0,0), (2,0)))
    assert lines[1] == pytest.approx(((2,0.2), (2,0.6)))
    assert lines[2] == pytest.approx(((2,1), (0,2)))

def test_Redistributor(geograph):
    redist = network.Redistributor(geograph, [[0,0], [0.5, 0.1]], 0.2, 0.5)
    x, y = redist.redistribute(0)
    x, y = redist.redistribute_from_point([0,0])
    with pytest.raises(ValueError):
        redist.redistribute_from_point([0.1,0])
        