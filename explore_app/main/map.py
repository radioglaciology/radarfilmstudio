import os

import numpy as np

from bokeh.plotting import figure
from bokeh.models.sources import ColumnDataSource
from bokeh.models import OpenURL, TapTool, HoverTool, BBoxTileSource, Select
from bokeh.embed import components
from bokeh.models.callbacks import CustomJS
from bokeh.layouts import column, row

from cartopy import crs

import pandas as pd

def load_flight_lines(positioning_dir):
    flight_lines = {}

    crs_3031 = crs.Stereographic(central_latitude=-90, true_scale_latitude=-71)
    crs_lonlat = crs.PlateCarree()

    for filename in os.listdir(positioning_dir):
        if filename.endswith(".csv"):
            id = int(filename.split('.')[0])

            df = pd.read_csv(os.path.join(positioning_dir, filename))
            df = df.rename(columns={'LAT': 'Latitude', 'LON': 'Longitude'}).dropna()
            df['Track'] = id

            # Project to CRS 3031 (South Polar Stereographic)
            projected_coords = crs_3031.transform_points(crs_lonlat, np.array(df['Longitude']), np.array(df['Latitude']))
            df['X'] = projected_coords[:, 0]
            df['Y'] = projected_coords[:, 1]

            flight_lines[id] = df

    return flight_lines


def make_bokeh_map(width, height, flight_id=None, title="", flight_lines = None, return_plot=False, return_components=False):
    if not flight_lines:
        print("Warning: Recommend pre-loading positioning files to speedup page load.")
        flight_lines = load_flight_lines('../original_positioning/')

    if not flight_id:
        flight_lines = list(flight_lines.values())
    else:
        print("specific flight")
        if flight_id in flight_lines:
            flight_lines = [flight_lines[flight_id]]
        else:
            not_found_html = "<div class='plot_error'>Couldn't find the requested flight ID.</div>"
            if return_components:
                return None
            elif return_plot:
                return not_found_html, None
            else:
                return not_found_html

    p = figure(match_aspect=True, tools=['pan,wheel_zoom,box_zoom,reset,tap'])

    #points = p.circle([0], [0]) # TODO: Should be McMurdo at (166.668, -77.846)

    data_sources = []
    flight_glyphs = []
    for df in flight_lines:
        data_source = ColumnDataSource(data=df)
        data_sources.append(data_source)
        l = p.line(x='X', y='Y', source=data_source)
        flight_glyphs.append(l)

    highlight_source = ColumnDataSource(data={'X': [], 'Y': []})
    p.line(x='X', y='Y', source=highlight_source, line_width=2, color='firebrick')

    p.xaxis.axis_label = "ESPG:3031 X"
    p.yaxis.axis_label = "ESPG:3031 Y"

    p.add_tools(HoverTool(
        renderers=flight_glyphs,
        tooltips=[
            ('Track', '@{Track}'),
            ('CBD', '@CBD')
        ]
    ))

    # TODO tile sources
    tile_options = {}
    tile_options[
        'url'] = 'https://ops.cresis.ku.edu/geoserver/antarctic/wms?LAYERS=antarctic:antarctica_coastline&TRANSPARENT=TRUE&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&FORMAT=image/png&SRS=EPSG:3031&BBOX={XMIN},{YMIN},{XMAX},{YMAX}&WIDTH=256&HEIGHT=256'
        #'url'] = 'https://ops.cresis.ku.edu/geoserver/antarctic/wms?LAYERS=antarctic:antarctica_measures_velocity_log_magnitude&TRANSPARENT=TRUE&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&FORMAT=image/png&SRS=EPSG:3031&BBOX={XMIN},{YMIN},{XMAX},{YMAX}&WIDTH=256&HEIGHT=256'
    tile_options['attribution'] = """cresis"""
    tile_source = BBoxTileSource(**tile_options)
    ts_glyph = p.add_tile(tile_source)
    ts_glyph.level = 'underlay'

    cb_tile_select = CustomJS(args=dict(tile_source=tile_source), code="""
                //var selected_color = cb_obj.value;
                if (cb_obj.value == 'Coastline') {
                    tile_source.url = 'https://ops.cresis.ku.edu/geoserver/antarctic/wms?LAYERS=antarctic:antarctica_coastline&TRANSPARENT=TRUE&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&FORMAT=image/png&SRS=EPSG:3031&BBOX={XMIN},{YMIN},{XMAX},{YMAX}&WIDTH=256&HEIGHT=256';
                } else if (cb_obj.value == 'Surface Velocity') {
                    tile_source.url = 'https://ops.cresis.ku.edu/geoserver/antarctic/wms?LAYERS=antarctic:antarctica_measures_velocity_log_magnitude&TRANSPARENT=TRUE&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&FORMAT=image/png&SRS=EPSG:3031&BBOX={XMIN},{YMIN},{XMAX},{YMAX}&WIDTH=256&HEIGHT=256';
                }
            """)

    tile_select = Select(value="Coastline",
                          options=["Coastline", "Surface Velocity", "BedMachine Mask"])
    tile_select.js_on_change('value', cb_tile_select)

    if len(flight_lines) > 1:
        url = f"/flight/@Track/"
        taptool = p.select(type=TapTool)
        taptool.callback = OpenURL(url=url, same_tab=True)

    p.sizing_mode = 'stretch_both'
    if (width is not None) and (height is not None):
        p.width = width
        p.height = height
    p.title.text = title

    if return_components:
        return {
            'map': p,
            'tile_select': tile_select,
            'flight_lines': flight_lines,
            'data_sources': data_sources,
            'highlight_source': highlight_source
        }
    elif return_plot:
        return p, flight_lines
    else:
        script, div = components(p)
        return f'\n{script}\n\n{div}\n'



