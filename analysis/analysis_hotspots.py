import open_cp.scripted as scripted
import open_cp.data, open_cp.geometry

import pickle, bz2

def load_points():
    with bz2.open("points1.pic.bz") as f:
        return pickle.load(f)

def load_geometry():
    with bz2.open("geo.pic.bz") as f:
        return pickle.load(f)

import datetime, itertools

grid = open_cp.data.Grid(xsize=150, ysize=150, xoffset=0, yoffset=0)
grid = open_cp.geometry.mask_grid_by_intersection(load_geometry(), grid)

with scripted.Data(load_points, load_geometry,
        start=datetime.datetime(2007,1,1), grid=grid) as state:
    
    time_range = scripted.TimeRange(datetime.datetime(2007,10,1),
            datetime.datetime(2008,1,1), datetime.timedelta(days=1))

    state.add_prediction(scripted.NaiveProvider, time_range)

    for bw in range(50,301,10):
        weight = open_cp.retrohotspot.Quartic(bw)
        state.add_prediction(scripted.RetroHotspotProvider(weight), time_range)

    for bw in range(50,301,10):
        weight = open_cp.retrohotspot.Quartic(bw)
        state.add_prediction(scripted.RetroHotspotCtsProvider(weight), time_range)

    for tb, sb in itertools.product([30,50,70,90], [3,4,5,6,7]):
        weight = open_cp.prohotspot.ClassicWeight(time_bandwidth=tb, space_bandwidth=sb)
        distance = open_cp.prohotspot.DistanceCircle()
        state.add_prediction(scripted.ProHotspotProvider(weight, distance), time_range)

    for tb, sb in itertools.product([30,50,70,90], [0.5,1,1.5]):
        weight = open_cp.prohotspot.ClassicWeight(time_bandwidth=tb, space_bandwidth=sb)
        state.add_prediction(scripted.ProHotspotCtsProvider(weight, 150), time_range)

    for max_s in [100,200,500,1000]:
        for max_t in [7,14,21,8*7]:
            provider = scripted.STScanProvider(max_s, datetime.timedelta(days=max_t), False)
            state.add_prediction(provider, time_range)
            state.add_prediction(provider.with_new_max_cluster(True), time_range)

    for tw in [12, 16, 20]:
        for bw in [50, 75, 100]:
            tk = open_cp.kde.ExponentialTimeKernel(tw*7)
            sk = open_cp.kde.GaussianFixedBandwidthProvider(bw)
            state.add_prediction(scripted.KDEProvider(tk, sk), time_range)

    state.score(scripted.HitCountEvaluator)
    state.process(scripted.HitCountSave("hotspots.csv"))
