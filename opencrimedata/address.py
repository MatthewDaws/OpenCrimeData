"""
address.py
~~~~~~~~~~

Thin wrapper for reading USA data from files from
http://results.openaddresses.io/
"""

import zipfile as _zipfile
import collections as _collections
import csv as _csv
import io as _io
import geopandas as _gpd
import pandas as _pd
import numpy as _np
import shapely.geometry as _geometry
from . import geometry

def filenames(zipfilename):
    """Find the available address filenames.
    
    :param zipfilename: Name of the input zip filename
    
    :return: An iterable of pairs `(state, name)` where `state` is the US
      state and `name` is the available csv filename.
    """
    zf = _zipfile.ZipFile(zipfilename)
    try:
        for info in zf.filelist:
            name = info.filename
            if name.startswith("us/") and name.endswith(".csv"):
                name = name[3:-4]
                yield tuple(name.split("/"))
    finally:
        zf.close()

_HEADER = ["LON", "LAT", "NUMBER", "STREET", "UNIT", "CITY", "DISTRICT", "REGION", "POSTCODE", "ID", "HASH"]
Row = _collections.namedtuple("Row", "point street number unit city district region postcode idd hash")

def readzip(zipfilename, state, filename):
    """Open the data for the given state and filename, check the format,
    and yield objects.
    
    :param zipfilename: Name of the input zip filename
    :param state: Name of the state to open, e.g. "il"
    :param filename: Name of the filename to open without `.csv`, e.g.
      "cook"
    
    :return: An iterable of objects which have attributes for each field.
      The coordinates are converted to a pair of floats.
    """
    filename = "us/{}/{}.csv".format(state, filename)
    zf = _zipfile.ZipFile(zipfilename)
    try:
        with zf.open(filename, "r") as f:
            yield from readcsv(f)
    finally:
        zf.close()
        
def readcsv(csvfile):
    """Open the data, check the format, and yield objects.
    
    :param csvfile: Filename or file-like object.  If a file-like object,
      should return _bytes_ not string objects.
    
    :return: An iterable of objects which have attributes for each field.
      The coordinates are converted to a pair of floats.
    """
    toclose = False
    if isinstance(csvfile, str):
        file = open(csvfile, "rb")
        toclose = True
    else:
        file = csvfile
    try:
        r = _io.TextIOWrapper(file, encoding="utf8", newline="")
        reader = _csv.reader(r)
        header = [x.strip().upper() for x in next(reader)]
        assert set(header) == set(_HEADER)
        lookup = [ header.index(x) for x in _HEADER ]
        for row in reader:
            row = [row[x] for x in lookup]
            x, y = float(row[0]), float(row[1])
            r = Row(point=(x,y), street=row[3], number=row[2], unit=row[4],
                    city=row[5], district=row[6], region=row[7],
                    postcode=row[8], idd=row[9], hash=row[10])
            yield r
    finally:
        if toclose:
            file.close()
    
def read_to_geo_frame(zipfilename, state, filename):
    """Read the data to a GeoPandas dataframe."""
    frame = _pd.DataFrame(list(readzip(zipfilename, state, filename)))
    geo = [_geometry.Point(*pt) for pt in frame.point]
    frame = frame.drop("point", axis=1)
    frame = _gpd.GeoDataFrame(frame)
    frame.geometry = geo
    frame.crs = {"init":"epsg:4326"}
    return frame


class AddressMatch():
    """Load an address database, and use it to match points.

    :param filename: CSV filename (or file-like object) to read from.
    :param proj: Projection object.
    """
    def __init__(self, filename, proj):
        address_points = []
        self._addresses = []
        for row in readcsv(filename):
            address_points.append(row.point)
            self._addresses.append((row.number, row.street))
        self._addresses = _np.asarray(self._addresses)
        address_points = _np.asarray(address_points)
        address_points = _np.vstack(proj(*address_points.T)).T
        self._matcher = geometry.ClosestPoint(address_points)

    @staticmethod
    def from_zip(zipfile, state, filename, proj):
        """Construct an instance from a zip file; see
        :func:`readzip`.
        """
        filename = "us/{}/{}.csv".format(state, filename)
        zf = _zipfile.ZipFile(zipfile)
        try:
            with zf.open(filename, "r") as f:
                match = AddressMatch(f, proj)
        finally:
            zf.close()
        return match

    def closest(self, pt):
        """Return the point in the address data which is closest to this
        point.
        
        :param pt: The point, `(x,y)`
        
        :return: Pair `(address, point)` where point is the closest point,
          and `address` is the address string.
        """
        i, pt = self._matcher.closest(pt)
        return self._addresses[i], pt

    def all_in_disc(self, pt, radius):
        """Find all points which are within `radius` of `pt`.

        :return: `(addresses, points)`
        """
        indices, points = self._matcher.all_in_disc(pt, radius)
        return self._addresses[indices], points

    @property
    def address_points(self):
        """The points of the input addresses."""
        return self._matcher.points

    @property
    def addresses(self):
        """The addresses, in the same order as :attr:`address_points`."""
        return self._addresses
    