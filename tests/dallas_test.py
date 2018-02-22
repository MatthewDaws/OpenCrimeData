import pytest

import opencrimedata.dallas as dallas

import os, datetime
import unittest.mock as mock

@pytest.fixture
def filename():
    return os.path.join("tests", "data", "dallas_test.csv")

def test_load(filename):
    out = list(dallas.load(filename))

    assert out[0].code == "276285-2016"
    assert out[0].crime_type == "BURGLARY"
    assert out[0].crime_subtype == "BURGLARY-RESIDENCE"
    assert out[0].start_time == datetime.datetime(2016,11,16, 11,0)
    assert out[0].end_time == datetime.datetime(2016,11,18, 11,0)
    assert out[0].call_time == datetime.datetime(2016,11,18, 11,42,26)
    assert out[0].address == "5850 BELT LINE RD"
    assert out[0].city == "DALLAS 75254"
    assert out[0].lonlat == pytest.approx((-96.807131, 32.953948))
    assert out[0].xy == pytest.approx((2487549.90103337*1200 / 3937, 7034119.57307657*1200 / 3937))

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
    out = list(dallas.load(filename))
    dallas.write(out_test_file, out)
    out1 = list(dallas.load(out_test_file))
    for x, y in zip(out, out1):
        assert tuple(x)[:-2] == tuple(y)[:-2]
        assert y.lonlat is None
        assert x.xy == pytest.approx(y.xy)

def test_load_full(filename):
    out = list(dallas.load_full(filename))

    index = [entry.code for entry in out].index("276285-2016")
    #assert out[0].code == "276285-2016"
    assert out[index].crime_type == "BURGLARY"
    assert out[index].crime_subtype == "BURGLARY-RESIDENCE"
    assert out[index].start_time == datetime.datetime(2016,11,16, 11,0)
    assert out[index].end_time == datetime.datetime(2016,11,18, 11,0)
    assert out[index].call_time == datetime.datetime(2016,11,18, 11,42,26)
    assert out[index].address == "5850 BELT LINE RD"
    assert out[index].city == "DALLAS 75254"
    assert out[index].lonlat == pytest.approx((-96.807131, 32.953948))
    assert out[index].xy == pytest.approx((2487549.90103337*1200 / 3937, 7034119.57307657*1200 / 3937))

def test_to_geoframe(filename):
    frame = dallas.to_geoframe(filename)
    assert len(frame) == 3
    
    def filter(row):
        return row.code == "276593-2016"
    frame = dallas.to_geoframe(filename, filter)
    assert len(frame) == 1
    
def test_row_with_new_position():
    row = dallas.Row(code="codeajshd", crime_type="ctafsgja", crime_subtype="cstsdafjjds",
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now() - datetime.timedelta(hours=5),
        call_time=datetime.datetime.now() - datetime.timedelta(hours=7),
        address="adshdsgjsfdhj", city="cityaJFJ",
        lonlat=(1535.15372, -1683.1372),
        xy=(4125747.54, 1248563.438))
    row1 = dallas.row_with_new_position(row, 47.286326, 1325.25368682)
    
    assert tuple(row)[:8] == tuple(row1)[:8]
    assert len(tuple(row)) == 10
    assert row1.lonlat is None
    assert row1.xy == pytest.approx((47.286326, 1325.25368682))
    
def test_streets():
    filename = os.path.join("tests", "data", "test_dallas_streets")
    out = list(dallas.load_street_lines(filename))
    assert out[0].street_id == 2784
    assert out[0].clazz == "PRIVATE"
    assert out[0].name is None
    assert out[0].oneway == 0
    assert out[0].left.start == 0
    assert out[0].left.end == 0
    assert out[0].right.start == 0
    assert out[0].right.end == 0

    assert out[1].oneway == -1

    assert out[2].right.start == 7600
    assert out[2].right.end == 7698

    assert out[3].left.start == 15336
    assert out[3].left.end == 15398

def test_street_clazz_accept():
    row = mock.MagicMock()
    row.clazz = "paper"
    assert not dallas.street_clazz_accept(row)

    row.clazz = "private"
    assert dallas.street_clazz_accept(row)
