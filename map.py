import os

from bokeh.io import output_file, show, output_notebook
from bokeh.plotting import figure
from bokeh.models.sources import ColumnDataSource
from bokeh.models import OpenURL, TapTool

import geoviews as gv
import geoviews.feature as gf
from geoviews import tile_sources

from geoviews import opts
from cartopy import crs

import pandas as pd

gv.extension('bokeh')


def bokeh_map(doc):
    positioning_dir = '/home/thomas/Downloads/Original_Positioning/Original_Positioning/'
    flight_lines = []

    for filename in os.listdir(positioning_dir):
        if filename.endswith(".csv"):
            df = pd.read_csv(os.path.join(positioning_dir, filename))
            df = df.rename(columns={'LAT': 'Latitude', 'LON': 'Longitude'}).dropna()
            df['Track'] = int(filename.split('.')[0])

            p = gv.Path(df, kdims=['Longitude', 'Latitude'],
                        vdims=['Track', 'CBD']).options(tools=['hover', 'tap'])

            flight_lines.append(p)

    points = gv.Points([(166.668, -77.846)])

    coast = (gf.coastline.clone(extents=(-180, -90, 180, -60)) * gv.Overlay(flight_lines) * points)
    p = gv.render(coast.options(projection=crs.SouthPolarStereo(), tools=['hover', 'tap']))

    url = f"/flight/@Track/"
    taptool = p.select(type=TapTool)
    taptool.callback = OpenURL(url=url, same_tab=True)

    p.sizing_mode = "scale_both"

    doc.add_root(p)