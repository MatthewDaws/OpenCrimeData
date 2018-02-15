"""
san_francisco
~~~~~~~~~~~~~

Load data from 

https://data.sfgov.org/Public-Safety/Police-Department-Incidents/tmnf-yvry

Each row of the input has a unique id number, which is field `idd` in the data
we report.  Typically each crime event may generate multiple reports, but these
will share the same `incident` code.
"""

import csv as _csv
import collections as _collections
import datetime as _datetime
import geopandas as _gpd
import pandas as _pd
import numpy as _np
import fiona as _fiona
import shapely.geometry as _geometry
import pyproj as _pyproj

def projector():    
    """:class:`pyproj.Proj` instance suitable for this data,
    EPSG:2768."""
    return _pyproj.Proj({"init":"EPSG:2768"})

_HEADER = ['IncidntNum', 'Category', 'Descript', 'DayOfWeek', 'Date', 'Time',
           'PdDistrict', 'Resolution', 'Address', 'X', 'Y', 'Location', 'PdId']

Row = _collections.namedtuple("Row", "category description datetime block point idd incident")

def load(filename):
    """Load the data.  Skips data with incorrectly coded position (which is
    a tiny number).
    
    :param filename: Filename or a file-like object opended in text mode.
    
    :return: Iterable of typed rows of the data.
    """
    toclose = False
    if isinstance(filename, str):
        filename = open(filename, "rt")
        toclose = True
    try:
        reader = _csv.reader(filename)
        header = [x.strip().upper() for x in next(reader)]
        assert set(header) == set(x.upper() for x in _HEADER)
        lookup = [header.index(x.upper()) for x in _HEADER]
        for row in reader:
            row = [row[x] for x in lookup]
            dt = _datetime.datetime.strptime(row[4] + " " + row[5], "%m/%d/%Y %H:%M")
            x, y = float(row[9]), float(row[10])
            if abs(y-90) < 1e-5:
                continue
            yield Row(row[1], row[2], dt, row[8], (x,y), row[12], row[0])
    finally:
        if toclose:
            filename.close()
    
def write(filename, rows):
    """Write out a csv file which minimally corresponds to the input format.
    That is, we use the same field names, but only write the columns which
    we read.

    :param filename: Filename or a file-like object opended in text mode.
    :param rows: An iterable of :class:`Row` objects.
    """
    toclose = False
    if isinstance(filename, str):
        filename = open(filename, "wt", newline="")
        toclose = True
    try:
        writer = _csv.writer(filename)
        writer.writerow(_HEADER)
        for row in rows:
            data = [""] * len(_HEADER)
            data[1] = row.category
            data[2] = row.description
            dt = row.datetime.strftime("%m/%d/%Y %H:%M").split(" ")
            data[4], data[5] = dt
            data[8] = row.block
            data[9], data[10] = row.point
            data[12] = row.idd
            data[0] = row.incident
            writer.writerow(data)
    finally:
        if toclose:
            filename.close()

def row_with_new_position(row, lon, lat):
    t = tuple(row)
    t = t[:4] + ((lon, lat), ) + t[5:]
    return Row(*t)
    
def to_geoframe(filename, filter=None):
    """Load the data to a GeoPandas dataframe.
    
    :param filename: Filename or a file-like object opended in text mode.
    :param filter: If not null, a function object which takes a `Row` object
      and returns `True` if and only if we want this row.
    
    :return: GeoDataFrame
    """
    if filter is None:
        filter = lambda r : True
    frame = _pd.DataFrame([row for row in load(filename) if filter(row)])
    geo = [_geometry.Point(*pt) for pt in frame.point]
    frame = frame.drop("point", axis=1)
    frame = _gpd.GeoDataFrame(frame)
    frame.geometry = geo
    frame.crs = {"init":"epsg:4326"}
    return frame

Street = _collections.namedtuple("Street", "street_id layer nhood oneway name left right line")
StreetAddress = _collections.namedtuple("StreetAddress", "start end")
_STREET_HEADER = {0:"cnn", 1:"layer", 2:"nhood", 3:"oneway", 4:"streetname",
        10:"lf_fadd", 11:"lf_toadd", 12:"rt_fadd", 13:"rt_toadd"}

def load_street_centre_lines(filename):
    """Load the street network data from
    https://data.sfgov.org/Geographic-Locations-and-Boundaries/San-Francisco-Basemap-Street-Centerlines/7hfy-8sz8

    Returns all data.  If you want to filter to streets which we believe are
    based on geographic reality, combine with :func:`street_layer_accept`.

    :param filename: Filename of the directory containing the shapefile data
    
    :return: Iterable of typed rows of the data.
    """
    with _fiona.open(filename) as shapefile:
        yield from _yield_street_data(shapefile)

def _yield_street_data(shapefile):
    header = list(shapefile.schema["properties"])
    for i, key in _STREET_HEADER.items():
        if key not in header:
            raise ValueError("Key '{}' missing from header: {}".format(key, header))

    if shapefile.crs != {'init': 'epsg:4326'} and shapefile.crs != {}:
        raise Exception("Shapefile crs is wrong: {}".format(shapefile.crs))
    
    for row in shapefile:
        if row["geometry"]["type"] != "LineString":
            raise ValueError("Unexpected geometry type: {}".format(row["geometry"]))
        geo = _np.asarray(row["geometry"]["coordinates"])
        
        props = row["properties"]

        def parse_address(start_index, end_index):
            start = int(props[_STREET_HEADER[start_index]])
            end = int(props[_STREET_HEADER[end_index]])
            if (start == 0 and end != 0) or (start != 0 and end == 0):
                raise ValueError("Unexpected address: {}".format(row))
            if start == 0:
                return None
            return StreetAddress(start=start, end=end)

        yield Street(street_id = int(props[_STREET_HEADER[0]]),
            layer = props[_STREET_HEADER[1]],
            nhood = props[_STREET_HEADER[2]],
            oneway = props[_STREET_HEADER[3]],
            name = props[_STREET_HEADER[4]],
            left = parse_address(10, 11),
            right = parse_address(12, 13),
            line = geo
            )

_ALLOW = {'FREEWAYS', 'PARKS', "PRVIATE", 'Parks_NPS_FtMaso', 'Parks_NPS_Presid',
        'Private', 'Private_parking', 'STREETS', 'Streets_HuntersP',
        'Streets_Pedestri', 'streets_ti', 'streets_ybi'}
_DONT = {'PAPER', "PSEUDO", 'Paper_fwys', 'Paper_water', "UPROW"}
_ALLOW = set(x.upper() for x in _ALLOW)
_DONT = set(x.upper() for x in _DONT)
    
def street_layer_accept(row):
    """Filter streets by the `layer`.
    
    :param row: Instance of `Street`

    :return: True if we want, False otherwise.
    """
    if row.layer.upper() in _ALLOW:
        return True
    if row.layer.upper() in _DONT:
        return False
    raise ValueError("Unexpected 'layer' type: {}".format(row))
