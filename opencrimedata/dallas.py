"""
dallas
~~~~~~

Load data from 

https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-present/ijzp-q8t2
"""

import csv as _csv
import collections as _collections
import datetime as _datetime
import geopandas as _gpd
import pandas as _pd
import numpy as _np
import shapely.geometry as _geometry
import pyproj as _pyproj
import fiona as _fiona

_HEADER = ["Service Number ID", "UCR Offense Description", "UCR Offense Name",
           "Starting  Date/Time", "Ending Date/Time", "Call Date Time",
           "Incident Address", "City", "Zip Code", "Location1", "X Coordinate",
           "Y Coordinate"]
_DT_FMT = "%m/%d/%Y %I:%M:%S %p"
_FT_TO_METERS = 1200 / 3937

Row = _collections.namedtuple("Row", "code crime_type crime_subtype start_time end_time call_time address city lonlat xy")

def projector():
    """A projector which is suitable for the Dallas data, EPSG:2845."""
    return _pyproj.Proj({"init":"epsg:2845"})

def load(filename):
    """Load the data.  We assume that the _first_ record for each crime event
    will carry the information (this is not satisfied for all events!)
    
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
            s, data = _process_row([row[x] for x in lookup])
            if s == 1:
                yield data
    finally:
        if toclose:
            filename.close()
            
def write(filename, rows):
    """Write out a csv file which minimally corresponds to the input format.
    That is, we use the same field names, but only write the columns which
    we read.  Does not write lon/lat coords!

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
            city, zipcode = "", ""
            if row.city is not None:
                parts = row.city.split(" ")
                if len(parts) == 1:
                    city = parts[0]
                else:
                    city = " ".join(parts[:-1])
                    zipcode = parts[-1]

            if row.xy is None:
                x, y = "", ""
            else:
                x, y = row.xy
                x /= _FT_TO_METERS
                y /= _FT_TO_METERS

            start = "" if row.start_time is None else row.start_time.strftime(_DT_FMT)
            end = "" if row.end_time is None else row.end_time.strftime(_DT_FMT)
            call = "" if row.call_time is None else row.call_time.strftime(_DT_FMT)

            cells = [row.code + "-01",
                row.crime_type, row.crime_subtype,
                start, end, call,
                row.address,
                city, zipcode,
                "",
                x, y]
            writer.writerow(cells)
    finally:
        if toclose:
            filename.close()
    
def row_with_new_position(row, x, y):
    """Give a new :class:`Row` with a new `xy` position, and no `lonlat`
    position."""
    t = tuple(row)[:-2] + (None, (x,y))
    return Row(*t)

def load_full(filename):
    """Load the data.  We try to find the record for each crime which contains
    the most amount of information.  This costs memory and time.
    
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
        data = _collections.defaultdict(list)
        for row in reader:
            s, detail = _process_row([row[x] for x in lookup])
            data[detail.code].append((s,detail))
        for choices in data.values():
            ses = [x for x,_ in choices]
            ses.sort()
            assert ses == list(range(1,len(ses)+1))
            yield Row(*_best(choices))
    finally:
        if toclose:
            filename.close()
    
def _best(choices):
    choices = {s:d for (s,d) in choices}
    choices = [choices[s+1] for s in range(len(choices))]
    _all_agree_up_to_none(choices)
    choices = [tuple(c) for c in choices]
    out = [ _best_of_one([c[i] for c in choices])
            for i in range(len(choices[0])) ]
    return out
    
def _best_of_one(choices):
    for x in choices:
        if x is None:
            continue
        if isinstance(x, str) and x == "":
            continue
        return x
    return choices[0]
    
def _agree_up_to_none(a, b):
    if a is None or b is None:
        return True
    if isinstance(a, str) and a == "":
        return True
    if isinstance(b, str) and b == "":
        return True
    return a == b
        
def _all_agree_up_to_none(choices):
    choices = [tuple(c) for c in choices]
    # Crime type(s) can change
    choices = [ (c[0], *c[3:]) for c in choices ]
    for i in range(1, len(choices)):
        if not all(_agree_up_to_none(a,b) for a,b in zip(choices[0], choices[i])):
            print(choices)
            raise AssertionError()
            
def _to_dt(x):
    if x == "":
        return None
    return _datetime.datetime.strptime(x, _DT_FMT)
            
def _to_lon_lat(x):
    x = x.splitlines()
    if len(x) < 3:
        return None
    x = x[2]
    assert x[0] == "(" and x[-1] == ")"
    x = x[1:-1]
    x = x.split(", ")
    lon, lat = float(x[1]), float(x[0])
    # Ignore dodgy data
    if lon < -97.4 and lat < 26:
        return None
    return lon, lat

def _process_row(row):
    parts = row[0].replace(" ", "").split("-")
    subid = int(parts[2])
    
    code = "-".join(parts[:2])
    start = _to_dt(row[3])
    end = _to_dt(row[4])
    call = _to_dt(row[5])
    city = " ".join([row[7], row[8]]).strip()
    if row[10] == "":
        xy = None
    else:
        xy = float(row[10]) * _FT_TO_METERS, float(row[11]) * _FT_TO_METERS
    
    return subid, Row(code, row[1], row[2], start, end, call, row[6], city,
               _to_lon_lat(row[9]), xy)
            
def to_geoframe(filename, filter=None, geometry="xy"):
    """Load the data to a GeoPandas dataframe.  Uses the `load_full` method,
    and scales xy coordinates to _meters_ not _feet_.
    
    :param filename: Filename or a file-like object opended in text mode.
    :param filter: If not null, a function object which takes a `Row` object
      and returns `True` if and only if we want this row.
    :param geometry: One of `xy` or `lonlat` specifying which coordinates to
      use as the "geometry".  The other coordinates will still appear as a
      column.
    
    :return: GeoDataFrame
    """
    if filter is None:
        filter = lambda r : True
    frame = _pd.DataFrame([row for row in load_full(filename) if filter(row)])
    frame["x"] = frame["xy"].map(lambda p : p[0] if p is not None else _np.nan) * _FT_TO_METERS
    frame["y"] = frame["xy"].map(lambda p : p[1] if p is not None else _np.nan) * _FT_TO_METERS
    frame["lon"] = frame["lonlat"].map(lambda p : p[0] if p is not None else _np.nan)
    frame["lat"] = frame["lonlat"].map(lambda p : p[1] if p is not None else _np.nan)
    if geometry == "xy":
        geo = [_geometry.Point(x, y) for x, y in zip(frame.x, frame.y)]
    elif geometry == "lonlat":
        geo = [_geometry.Point(x, y) for x, y in zip(frame.lon, frame.lat)]
    else:
        raise ValueError()
    frame = _gpd.GeoDataFrame(frame.drop(["xy", "lonlat"], axis=1))
    frame.geometry = geo
    if geometry == "lonlat":
        frame.crs = {"init":"epsg:4326"}
    else:
        frame.crs = {"init":"epsg:2845"}
    return frame

Street = _collections.namedtuple("Street", "street_id clazz name oneway left right line")
StreetAddress = _collections.namedtuple("StreetAddress", "start end")
_STREET_HEADER = {0:"class", 1:"ft_dir", 2:"tf_dir", 3:"fullstreet", 4:"segment_id",
        10:"l_f_add", 11:"l_t_add", 12:"r_f_add", 13:"r_t_add"}

def load_street_lines(filename):
    """Load the street network data from
    https://www.dallasopendata.com/Geography-Boundaries/Streets-Shapefile-Polyline/cvgm-fp24

    Returns all data.  If you want to filter to streets which we believe are
    based on geographic reality, combine with :func:`street_clazz_accept`.

    :param filename: Filename of the directory containing the shapefile data
    
    :return: Iterable of typed rows of the data.
    """
    with _fiona.open(filename) as shapefile:
        yield from _yield_street_data(shapefile)

def _empty_string_to_none(x):
    try:
        if x == "":
            return None
    except:
        pass
    return x

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
        props = {k:_empty_string_to_none(props[v]) for k,v in _STREET_HEADER.items()}

        oneway = 0
        if props[1] is not None and props[2] is None:
            oneway = 1
        if props[1] is None and props[2] is not None:
            oneway = -1

        yield Street(street_id = int(props[4]),
            clazz = props[0],
            name = props[3],
            oneway = oneway,
            left = StreetAddress(int(props[10]), int(props[11])),
            right = StreetAddress(int(props[12]), int(props[13])),
            line = geo)

_ALLOW = {'DALLAS AREA HIGHWAY', 'HIGHWAY', "MAJOR ARTERIAL", 'MINOR ARTERIAL',
    'PRIMARY HIGHWAY', 'PRIVATE', "RAMP", "SECONDARY", "WALKWAY"}
_DONT = {"CAD ONLY", "TRAIL", "PAPER"}

def street_clazz_accept(row):
    """Filter streets by the `clazz`.
    
    :param row: Instance of `Street`

    :return: True if we want, False otherwise.
    """
    if row.clazz.upper() in _ALLOW:
        return True
    if row.clazz.upper() in _DONT:
        return False
    raise ValueError("Unexpected 'layer' type: {}".format(row))
