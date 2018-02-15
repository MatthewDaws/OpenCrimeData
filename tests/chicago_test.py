import pytest

import opencrimedata.chicago as chicago
import os
import datetime

def test_projector():
    proj = chicago.projector()
    assert proj(-87.5, 41.65) == pytest.approx((369417.90128689713, 553564.6265444394))

@pytest.fixture
def filename():
    return os.path.join("tests", "data", "chicago_test.csv")

def test_load(filename):
    out = list(chicago.load(filename))
    assert len(out) == 9
    
    assert out[0].id == "5189091"
    assert out[0].crime_type == "OFFENSE INVOLVING CHILDREN"
    assert out[0].crime_subtype == "CHILD ABUSE"
    assert out[0].location == "RESIDENCE"
    assert out[0].address == "108XX S AVENUE G"
    assert out[0].point == pytest.approx((-87.531655723, 41.698387427))

@pytest.fixture
def out_test_file():
    filename = os.path.join("tests", "data", "chicago_test_out.csv")
    try:
        os.remove(filename)
    except:
        pass
    yield filename
    try:
        os.remove(filename)
    except:
        pass

def test_write(filename, out_test_file):
    out = list(chicago.load(filename))
    chicago.write(out_test_file, out)
    out1 = list(chicago.load(out_test_file))
    assert out == out1

def test_to_geoframe(filename):
    frame = chicago.to_geoframe(filename)
    assert len(frame) == 9
    
    def filter(row):
        return row.id == "5189099"
    frame = chicago.to_geoframe(filename, filter)
    assert len(frame) == 1

def test_load_streets():
    filename = os.path.join("tests", "data", "test_streets")
    out = list(chicago.load_street_centre_lines(filename))
    assert out[0].street_id == 1782
    assert out[0].street_name == "S YALE AVE"
    assert out[0].length == pytest.approx(67.2286548)
    assert out[0].source.street_id == 2208
    assert out[0].source.node_id == 10809
    assert out[0].source.street_address == "245|W|ENGLEWOOD|AVE|"
    assert out[0].destination.street_id == 0
    assert out[0].destination.node_id == 16581
    assert out[0].destination.street_address == "6250|S|||"
    assert out[0].left.start == 0
    assert out[0].left.end == 0
    assert out[0].left.parity == "O"
    assert out[0].right.start == 6228
    assert out[0].right.end == 6248
    assert out[0].right.parity == "E"
    assert tuple(out[0].line[0]) == pytest.approx((-87.63187018,  41.78080975))
    assert tuple(out[0].line[-1]) == pytest.approx((-87.63184151,  41.78020488))

def test_load_streets_wrong_format():
    filename = os.path.join("tests", "data", "test_lines")
    with pytest.raises(ValueError):
        list(chicago.load_street_centre_lines(filename))

def test_load_to_open_cp(filename):
    chicago.load_to_open_cp(filename)
    chicago.load_to_open_cp(filename, "BURGLARY")
    
def test_row_with_new_position():
    row = chicago.Row(168345, "ahgsga", "ahdgda", "locatadsa", "add_ahgsdfga",
                datetime.datetime.now(), (152.1654572, -61.463521))
    row1 = chicago.row_with_new_position(row, 12.64552, -32.27471)
    
    assert tuple(row)[:-1] == tuple(row1)[:-1]
    assert row1.point == pytest.approx((12.64552, -32.27471))
