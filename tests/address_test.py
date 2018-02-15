import pytest
import unittest.mock as mock
import os

import opencrimedata.address as address


def test_filenames():
    files = list(address.filenames(os.path.join("tests/data/example.zip")))
    assert set(files) == {("il","two"), ("ca", "one")}
    assert len(files) == 2
    
def check_read(out):
    assert len(out) == 9
    assert out[0].point == pytest.approx((-96.8201038,33.0109558))
    assert tuple(out[0])[1:] == ("", "", "", " ", "COLLIN COUNTY", "", "", "", "9e61faffd7d3fea4")
    
@pytest.fixture
def zipfile():
    return os.path.join("tests/data/example1.zip")

def test_readzip(zipfile):
    out = list(address.readzip(zipfile, "il", "cook"))
    check_read(out)
    
@pytest.fixture
def csvfile():
    return os.path.join("tests/data/test.csv")

def test_readcsv(csvfile):
    out = list(address.readcsv(csvfile))
    check_read(out)

def test_readcsv_from_file():
    with open(os.path.join("tests/data/test.csv"), "rb") as f:
        out = list(address.readcsv(f))
    check_read(out)

def test_read_to_geo_frame():
    frame = address.read_to_geo_frame(os.path.join("tests/data/example1.zip"), "il", "cook")
    assert len(frame) == 9
    assert list(frame.geometry[0].coords)[0] == pytest.approx((-96.8201038,33.0109558))
    
def test_AddressMatch(csvfile):
    proj = mock.Mock()
    proj.return_value = [0, 1]
    address.AddressMatch(csvfile, proj)

def test_AddressMatch_zip(zipfile):
    proj = mock.Mock()
    proj.return_value = [0, 1]
    address.AddressMatch.from_zip(zipfile, "il", "cook", proj)
