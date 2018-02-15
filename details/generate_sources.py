### Generates various shapefiles etc. from inputs

# Set `outdir` to None to use input dir, or other directory
# Set the `datadir` to be where you have downloaded the following files:
# - "Chicago_Areas.geojson" available from https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas-current-/cauq-8yn6


import os
#datadir = os.path.join("..", "..", "..", "..", "..", "Data")
datadir = os.path.join("//media", "disk", "Data")
outdir = os.path.join(datadir, "generated")

# Necessary on my windows box; not needed on my linux box
#gdal_data_dir = os.path.join("C:\\", "Users", "Matthew", "Anaconda3", "Library", "share", "gdal")
gdal_data_dir = None

########################

import logging, sys
ch = logging.StreamHandler(sys.stdout)
fmt = logging.Formatter("{asctime} {levelname} {name} - {message}", style="{")
ch.setFormatter(fmt)
logger = logging.getLogger("__main__")
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

logger.info("Generating source files from directory %s", datadir)
logger.debug("Contents of directory: %s", str(os.listdir(datadir)))

if gdal_data_dir is not None:
    try:
        os.listdir(gdal_data_dir)
    except Exception:
        logger.warn("Failed to find GDAL data directory '%s'", gdal_data_dir)
        gdal_data_dir = None
    if gdal_data_dir is not None:
        os.environ["GDAL_DATA"] = gdal_data_dir
        logger.info("Set GDAL_DATA=%s", gdal_data_dir)

import geopandas as gpd

_LONLAT_CRS = {"init": "epsg:4326"}

# Regions / Sides of chicago

logger.info("Generating regions / sides shapefiles...")
frame = gpd.read_file(os.path.join(datadir, "Chicago_Areas.geojson"))
frame.crs = _LONLAT_CRS

regions_mapping = {
    "North" : [1,2,3,4,5,6,7,77],
    "Northwest" : list(range(9,23)) + [76],
    "West" : list(range(23,32)),
    "Central" : [8, 32, 33],
    "South" : [35, 36] + list(range(38, 49)) + [69],
    "Southwest" : [34, 37] + list(range(56, 69)) + [70],
    "FarSouth" : list(range(49, 56)) + list(range(71, 76))
}
def get_region(x):
    return next( key for key, item in regions_mapping.items() if int(x) in item )
frame["region"] = frame.area_numbe.map(get_region)

side_mapping = {
    "Far North" : [1,2,3,4,9,10,11,12,13,14,76,77],
    "Northwest" : [15,16,17,18,19,20],
    "North" : [5,6,7,21,22],
    "West" : list(range(23, 32)),
    "Central" : [8,32,33],
    "South" : list(range(34,44)) + [60, 69],
    "Southwest" : [56,57,58,59] + list(range(61,69)),
    "Far Southwest" : list(range(70,76)),
    "Far Southeast" : list(range(44,56))
}
frame["side"] = frame.area_numbe.map(lambda x : next(key
    for key, item in side_mapping.items() if int(x) in item) )

regions = frame.drop(["area", "area_num_1", "comarea", "comarea_id",
                        "perimeter", "shape_area", "shape_len", "side"], axis=1)
old_columns = list(regions.columns)
old_columns[0] = "area_numbers"
regions.columns = old_columns
regions.to_file( os.path.join(outdir, "Chicago_Regions") )

sides = frame.drop(["area", "area_num_1", "comarea", "comarea_id",
                        "perimeter", "shape_area", "shape_len", "region"], axis=1)
old_columns = list(sides.columns)
old_columns[0] = "area_numbers"
sides.columns = old_columns
sides.to_file( os.path.join(outdir, "Chicago_Sides") )
