import pytest
import unittest.mock as mock

import opencrimedata.san_francisco as san_francisco

import os, datetime
import numpy as np

def test_load():
    filename = os.path.join("tests", "data", "sf_test.csv")
    out = list(san_francisco.load(filename))
    assert len(out) == 9

    assert out[0].category == "NON-CRIMINAL"
    assert out[0].description == "LOST PROPERTY"
    assert out[0].datetime == datetime.datetime(2015,1,19,14,0)
    assert out[0].block == "18TH ST / VALENCIA ST"
    assert out[0].point == pytest.approx((-122.42158168137,37.7617007179518))
    assert out[0].idd == "15006027571000"

@pytest.fixture
def out_test_file():
    filename = os.path.join("tests", "data", "sf_test_out.csv")
    try:
        os.remove(filename)
    except:
        pass
    yield filename
    try:
        os.remove(filename)
    except:
        pass

def test_write(out_test_file):
    filename = os.path.join("tests", "data", "sf_test.csv")
    out = list(san_francisco.load(filename))
    san_francisco.write(out_test_file, out)
    out1 = list(san_francisco.load(out_test_file))
    assert out == out1

def test_to_geoframe():
    filename = os.path.join("tests", "data", "sf_test.csv")
    frame = san_francisco.to_geoframe(filename)
    assert len(frame) == 9
    
    def filter(row):
        return row.idd == "15006027571000"
    frame = san_francisco.to_geoframe(filename, filter)
    assert len(frame) == 1

def test_load_streets():
    filename = os.path.join("tests", "data", "test_sf_streets")
    out = list(san_francisco.load_street_centre_lines(filename))
    assert out[0].street_id == 15145000
    assert out[0].layer == "PRIVATE"
    assert out[0].nhood == "Twin Peaks"
    assert out[0].oneway == "B"
    assert out[0].name == "CROWN CT"
    assert out[0].left is None
    assert out[0].right is None
    np.testing.assert_allclose(out[0].line, [(-122.44694244517986, 37.757228921523726),
         (-122.44664129285069, 37.757205402896545),
         (-122.44586701647785, 37.7569364867545)])

    assert out[3].street_id == 13798000
    assert out[3].layer == "STREETS"
    assert out[3].nhood == "Ingleside Terrace"
    assert out[3].oneway == "F"
    assert out[3].name == "CORONA ST"
    assert out[3].left.start == 221
    assert out[3].left.end == 299
    assert out[3].right.start == 222
    assert out[3].right.end == 298
    
def test_street_layer_accept():
    row = mock.Mock()
    row.layer = "StreeTS"
    assert san_francisco.street_layer_accept(row)

    row.layer = "PaPEr"
    assert not san_francisco.street_layer_accept(row)

    row.layer = "Bob"
    with pytest.raises(ValueError):
        san_francisco.street_layer_accept(row)
        
def test_row_with_new_position():
    row = san_francisco.Row(category="catagasf", description="descfjkafkj",
                datetime=datetime.datetime.now(), block="blockajjpioyj",
                point=(123.456, -876.543), idd=528762, incident="ingjdsh")
    row1 = san_francisco.row_with_new_position(row, 653.243, -746.1432)
    
    assert tuple(row)[:4] == tuple(row1)[:4]
    assert tuple(row)[5:] == tuple(row1)[5:]
    assert row1.point == pytest.approx((653.243, -746.1432))
    