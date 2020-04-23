import os

from bokeh.io import output_file, show, output_notebook
from bokeh.plotting import figure
from bokeh.models.sources import ColumnDataSource
from bokeh.models import OpenURL, TapTool
from bokeh.embed import components

import geoviews as gv
import geoviews.feature as gf
from geoviews import tile_sources

from geoviews import opts
from cartopy import crs

import pandas as pd

gv.extension('bokeh')

def load_flight_lines(positioning_dir):
    flight_lines = {}

    for filename in os.listdir(positioning_dir):
        if filename.endswith(".csv"):
            id = int(filename.split('.')[0])

            df = pd.read_csv(os.path.join(positioning_dir, filename))
            df = df.rename(columns={'LAT': 'Latitude', 'LON': 'Longitude'}).dropna()
            df['Track'] = id

            p = gv.Path(df, kdims=['Longitude', 'Latitude'],
                        vdims=['Track', 'CBD']).options(tools=['hover', 'tap'])

            flight_lines[id] = p

    return flight_lines


def make_bokeh_map(width, height, flight_id=None, title="", flight_lines = None):
    if not flight_lines:
        print("Warning: Recommend pre-loading positioning files to speedup page load.")
        flight_lines = load_flight_lines('../original_positioning/')

    if not flight_id:
        flight_lines = list(flight_lines.values())
    else:
        if flight_id in flight_lines:
            flight_lines = [flight_lines[flight_id]]
        else:
            return "<div class='plot_error'>Couldn't find the requested flight ID.</div>"

    points = gv.Points([(166.668, -77.846)])

    coast = (gf.coastline.clone(extents=(-180, -90, 180, -60)) * gv.Overlay(flight_lines) * points)
    p = gv.render(coast.options(projection=crs.SouthPolarStereo(), tools=['hover', 'tap']))

    url = f"/flight/@Track/"
    taptool = p.select(type=TapTool)
    taptool.callback = OpenURL(url=url, same_tab=True)

    p.sizing_mode = "fixed"
    p.width = width
    p.height = height
    p.title.text = title

    script, div = components(p)
    return f'\n{script}\n\n{div}\n'