import open_cp.scripted as scripted
import open_cp.data, open_cp.geometry

import pickle, bz2

def load_points():
    with bz2.open("points1.pic.bz") as f:
        return pickle.load(f)

def load_geometry():
    with bz2.open("geo.pic.bz") as f:
        return pickle.load(f)

import datetime

grid = open_cp.data.Grid(xsize=150, ysize=150, xoffset=0, yoffset=0)
grid = open_cp.geometry.mask_grid_by_intersection(load_geometry(), grid)

with scripted.Data(load_points, load_geometry,
        start=datetime.datetime(2007,1,1), grid=grid) as state:
    
    time_range = scripted.TimeRange(datetime.datetime(2007,10,1),
            datetime.datetime(2008,1,1), datetime.timedelta(days=1))
    state.add_prediction(scripted.NaiveProvider, time_range)

    state.score(scripted.HitCountEvaluator)
    state.process(scripted.HitCountSave("naive_counts.csv"))
