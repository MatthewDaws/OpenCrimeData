"""
chicago
~~~~~~~

Load data from 

https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-present/ijzp-q8t2
"""

import csv as _csv
import collections as _collections
import datetime as _datetime
import geopandas as _gpd
import fiona as _fiona
import numpy as _np
import shapely.geometry as _geometry
import pyproj as _pyproj

_HEADER = ["ID", 'Primary Type', 'Description', 'Location Description',
           'Block', "Date", 'Longitude', 'Latitude']
_DT_FMT = "%m/%d/%Y %I:%M:%S %p"

Row = _collections.namedtuple("Row", "id crime_type crime_subtype location address datetime point")

def projector():
    """Return a `pyproj` projection object for epsg:2790, which is
    suitable for Chicago."""
    return _pyproj.Proj({"init":"epsg:2790"})

def load(filename):
    """Load the data.
    
    :param filename: Filename or a file-like object opened in text mode.
    
    :return: Iterable of typed rows of the data.
    """
    toclose = False
    if isinstance(filename, str):
        filename = open(filename, "rt")
        toclose = True
    try:
        reader = _csv.reader(filename)
        header = [x.strip().upper() for x in next(reader)]
        lookup = [header.index(x.upper()) for x in _HEADER]
        for row in reader:
            data = [row[x] for x in lookup]
            data[5] = _datetime.datetime.strptime(data[5], _DT_FMT)
            if data[6] == "":
                data[6] = None
            else:
                data[6] = float(data[6]), float(data[7])
            del data[7]
            yield Row(*data)
    finally:
        if toclose:
            filename.close()
            
try:
    import open_cp.data as _ocpd
except:
    _ocpd = None
    
def load_to_open_cp(filename, crime_type=None):
    """Load into an `open_cp.data.TimedPoints` class, if possible.
    
    :param filename: Filename or a file-like object opened in text mode.
    :param crime_type: String of the crime type to load, or `None` to load all.
    """
    proj = projector()
    times = []
    points = []
    for row in load_only_with_point(filename):
        if crime_type is None or row.crime_type == crime_type:
            times.append(row.datetime)
            points.append(proj(*row.point))
    
    if len(times) == 0:
        return None
    
    times = _np.asarray(times)
    points = _np.asarray(points)
    if len(points.shape) == 1:
        points = points[None,:]
    i = _np.argsort(times)
    times = times[i]
    points = points[i,:]
    
    return _ocpd.TimedPoints(times, points.T)
            
def write(filename, rows):
    """Save a minimal version of the CSV file: includes all information to
    allow reloading, but other fields will be blank.
    
    :param filename: Filename or a file-like object opened in text mode.
    :param rows: Iterable of :class:`Row` objects
    """
    toclose = False
    if isinstance(filename, str):
        filename = open(filename, "wt", newline="")
        toclose = True
    try:
        writer = _csv.writer(filename)
        writer.writerow(_HEADER)
        for row in rows:
            data = list(tuple(row))
            data[5] = row.datetime.strftime(_DT_FMT)
            data[6] = row.point[0]
            data.append(row.point[1])
            writer.writerow(data)
    finally:
        if toclose:
            filename.close()

def load_only_with_point(filename):
    """As :func:`load` but skip entries which have no geo-coding point, or an
    obviously wrong geo-coded point."""
    for row in load(filename):
        if row.point is None:
            continue
        x, y = row.point
        if x < -91 and y < 37:
            continue
        yield row

def to_geoframe(filename, filter=None):
    """Load the data to a GeoPandas dataframe.  Note that typically we have a
    _lot_ of data, so use of `filter` is encouraged.
    
    :param filename: Filename or a file-like object opended in text mode.
    :param filter: If not null, a function object which takes a `Row` object
      and returns `True` if and only if we want this row.
    
    :return: GeoDataFrame
    """
    if filter is None:
        filter = lambda r : True
    frame = _gpd.GeoDataFrame([row for row in load(filename) if filter(row) and row.point is not None])
    def pt_to_point(pt):
        return _geometry.Point(*pt)
    frame.geometry = frame.point.map(pt_to_point)
    frame = frame.drop(["point"], axis=1)
    frame.crs = {"init":"epsg:4326"}
    return frame
    
def row_with_new_position(row, lon, lat):
    t = tuple(row)[:-1] + ((lon, lat),)
    return Row(*t)

Street = _collections.namedtuple("Street", "street_id street_name length source destination left right line")
StreetNode = _collections.namedtuple("StreetNode", "street_id node_id street_address")
StreetAddress = _collections.namedtuple("StreetAddress", "start end parity")
_STREET_HEADER = {0:"f_cross", 1:"f_cross_st", 2:"fnode_id",
    3:"t_cross", 4:"t_cross_st", 5:"tnode_id",
    6:"length", 7:"shape_len",
    8:"street_nam", 9:"street_typ", 10:"pre_dir", 11:"streetname",
    12:"l_f_add", 13:"l_t_add", 14:"l_parity",
    15:"r_f_add", 16:"r_t_add", 17:"r_parity"}

def load_street_centre_lines(filename):
    """Load the street network data from
    https://catalog.data.gov/dataset/street-center-lines
    Will skip data with no attached geometry.

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

    if shapefile.crs != {'init': 'epsg:4326'}:
        raise Exception("Shapefile crs is wrong: {}".format(shapefile.crs))
    
    for row in shapefile:
        if row["geometry"] is None:
            continue
        if row["geometry"]["type"] != "LineString":
            raise ValueError("Unexpected geometry type: {}".format(row["geometry"]))
        geo = _np.asarray(row["geometry"]["coordinates"])
        
        props = row["properties"]
        
        name = []
        for x in [10, 8, 9]:
            x = props[_STREET_HEADER[x]]
            if x is not None:
                name.append(x)
        name = " ".join(name)
        source_node = StreetNode(street_id = int(props[_STREET_HEADER[1]]),
            node_id = int(props[_STREET_HEADER[2]]),
            street_address = props[_STREET_HEADER[0]]
            )
        dest_node = StreetNode(street_id = int(props[_STREET_HEADER[4]]),
            node_id = int(props[_STREET_HEADER[5]]),
            street_address = props[_STREET_HEADER[3]]
            )
        left = StreetAddress(start = int(props[_STREET_HEADER[12]]),
            end = int(props[_STREET_HEADER[13]]),
            parity = props[_STREET_HEADER[14]]
            )
        right = StreetAddress(start = int(props[_STREET_HEADER[15]]),
            end = int(props[_STREET_HEADER[16]]),
            parity = props[_STREET_HEADER[17]]
            )

        yield Street(street_id = int(props[_STREET_HEADER[11]]),
            street_name = name,
            length = float(props[_STREET_HEADER[7]]) * 1200 / 3937,
            source = source_node, destination = dest_node,
            left=left, right=right,
            line = geo
            )
