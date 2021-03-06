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

from flask import current_app as app


map_tile_sources_all = {}
map_tile_sources_all['antarctica'] = [
    {
        "name": "Land/Water Mask",
        "url": "https://gibs.earthdata.nasa.gov/wms/epsg3031/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0?TIME=2016-01-08T00:00:00Z&LAYERS=SCAR_Land_Water_Map,Coastlines&STYLES=&FORMAT=image%2Fpng&TRANSPARENT=true&HEIGHT=256&WIDTH=256&CRS=EPSG:3031&BBOX={XMIN},{YMIN},{XMAX},{YMAX}",
        "attribution": "© <a href='https://www.openstreetmap.org/copyright' target='_blank'>OpenStreetMap</a> contributors. Tiles served by NASA's <a href='https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs' target='_blank'>GIBS</a>."
    },
    {
        "name": "Blue Marble",
        "url": "https://gibs.earthdata.nasa.gov/wms/epsg3031/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0?TIME=2016-01-08T00:00:00Z&LAYERS=BlueMarble_ShadedRelief_Bathymetry,Coastlines&STYLES=&FORMAT=image%2Fpng&TRANSPARENT=true&HEIGHT=256&WIDTH=256&CRS=EPSG:3031&BBOX={XMIN},{YMIN},{XMAX},{YMAX}",
        "attribution": "MODIS <a href='https://earthobservatory.nasa.gov/features/BlueMarble' target='_blank'>Cloud-Free Composite</a>. Tiles served by NASA's <a href='https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs' target='_blank'>GIBS</a>."
    },
    {
        "name": "MEaSUREs Ice Velocity",
        "url": "https://gibs.earthdata.nasa.gov/wms/epsg3031/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0?TIME=2011-01-08T00:00:00Z&LAYERS=MEaSUREs_Ice_Velocity_Antarctica,Coastlines&STYLES=&FORMAT=image%2Fpng&TRANSPARENT=true&HEIGHT=256&WIDTH=256&CRS=EPSG:3031&BBOX={XMIN},{YMIN},{XMAX},{YMAX}",
        "attribution": "<a href='https://nsidc.org/data/nsidc-0484/versions/1', target='_blank'>MEaSUREs Ice Velocity</a>.  Tiles served by NASA's <a href='https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs' target='_blank'>GIBS</a>."
    }
]
map_tile_sources_all['greenland'] = [
    {
        "name": "Land/Water Mask",
        "url": "https://gibs.earthdata.nasa.gov/wms/epsg3413/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0?TIME=2016-01-08T00:00:00Z&LAYERS=OSM_Land_Water_Map,Coastlines&STYLES=&FORMAT=image%2Fpng&TRANSPARENT=true&HEIGHT=256&WIDTH=256&CRS=EPSG:3413&BBOX={XMIN},{YMIN},{XMAX},{YMAX}",
        "attribution": "© <a href='https://www.openstreetmap.org/copyright' target='_blank'>OpenStreetMap</a> contributors. Tiles served by NASA's <a href='https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs' target='_blank'>GIBS</a>."
    },
    {
        "name": "Blue Marble",
        "url": "https://gibs.earthdata.nasa.gov/wms/epsg3413/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0?TIME=2016-01-08T00:00:00Z&LAYERS=BlueMarble_ShadedRelief_Bathymetry,Coastlines&STYLES=&FORMAT=image%2Fpng&TRANSPARENT=true&HEIGHT=256&WIDTH=256&CRS=EPSG:3413&BBOX={XMIN},{YMIN},{XMAX},{YMAX}",
        "attribution": "MODIS <a href='https://earthobservatory.nasa.gov/features/BlueMarble' target='_blank'>Cloud-Free Composite</a>. Tiles served by NASA's <a href='https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs' target='_blank'>GIBS</a>."
    },
    {
        "name": "MEaSUREs Ice Velocity",
        "url": "https://gibs.earthdata.nasa.gov/wms/epsg3413/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0?TIME=2009-01-08T00:00:00Z&LAYERS=MEaSUREs_Ice_Velocity_Greenland,Coastlines&STYLES=&FORMAT=image%2Fpng&TRANSPARENT=true&HEIGHT=256&WIDTH=256&CRS=EPSG:3413&BBOX={XMIN},{YMIN},{XMAX},{YMAX}",
        "attribution": "<a href='https://nsidc.org/data/nsidc-0478', target='_blank'>MEaSUREs Ice Velocity</a>.  Tiles served by NASA's <a href='https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs' target='_blank'>GIBS</a>."
    }
]


def load_flight_lines(positioning_dir, dataset):
    flight_lines = {}

    crs_3031 = crs.Stereographic(central_latitude=-90, true_scale_latitude=-71)
    #crs_3413 = crs.Stereographic(central_latitude=90, true_scale_latitude=70)
    crs_3413 = crs.epsg(3413)
    crs_lonlat = crs.PlateCarree()

    for filename in os.listdir(positioning_dir):
        if filename.endswith(".csv"):
            # Two formats of positioning CSVs unfortunately
            if filename.endswith("_final_QC.csv"): # Assume Greenland-style data
                fparts = filename.split('_')
                id = int(fparts[1][2:]) # flight id
                fdate = int(fparts[0])%100 # last 2 digits of year only

                df = pd.read_csv(os.path.join(positioning_dir, filename), header=None, names=["CBD", "Longitude", "Latitude", "a", "b"])
                df = df.drop(['a', 'b'], axis='columns').dropna()
                df['Track'] = id
                df['Date'] = fdate
                df['url'] = f"/flight/{dataset}/{id}/{fdate}"

            else: # Assume Antarctica style data
                id = int(filename.split('.')[0])
                fdate = None

                df = pd.read_csv(os.path.join(positioning_dir, filename)).drop(['THK', 'SRF', 'SURF'], axis='columns', errors='ignore')
                df = df.rename(columns={'LAT': 'Latitude', 'LON': 'Longitude'}).dropna()
                df['Track'] = id
                df['Date'] = None
                df['url'] = f"/flight/{dataset}/{id}"

            if dataset == 'antarctica':
                # Project to CRS 3031 (South Polar Stereographic)
                projected_coords = crs_3031.transform_points(crs_lonlat, np.array(df['Longitude']), np.array(df['Latitude']))
            elif dataset == 'greenland':
                # Project to CRS 3413 (Polar Stereographic North)
                projected_coords = crs_3413.transform_points(crs_lonlat, np.array(df['Longitude']), np.array(df['Latitude']))
            else:
                raise(Exception(f"Unexpected dataset {dataset} - should be antarctica or greenland"))
            
            df['X'] = projected_coords[:, 0]
            df['Y'] = projected_coords[:, 1]

            flight_lines[(id,fdate)] = df
            if not ((id, None) in flight_lines):
                flight_lines[(id,None)] = df # Arbitrarily make the first flight we process the default if no year known

    return flight_lines


def make_bokeh_map(width, height, flight_id=None, dataset='antarctica', title="", flight_lines = None, flight_date=None, return_plot=False, return_components=False):
    if flight_lines is None:
        raise(Exception("Providing flight lines is now required."))
        # print("Warning: Recommend pre-loading positioning files to speedup page load.")
        # flight_lines = load_flight_lines('../original_positioning/')

    if not flight_id:
        flight_lines = list(flight_lines.values())
    else:
        if flight_date is None:
            flight_identifier = (flight_id, None)
        else:
            flight_identifier = (flight_id, flight_date%100) # only year part
        
        if flight_identifier in flight_lines:
            flight_lines = [flight_lines[flight_identifier]]
        else:
            not_found_html = "<div class='plot_error'>Couldn't find the requested flight ID.</div>"
            if return_components:
                return None
            elif return_plot:
                return not_found_html, None
            else:
                return not_found_html

    p = figure(match_aspect=True, tools=['pan,wheel_zoom,box_zoom,reset,tap'])

    data_sources = []
    flight_glyphs = []

    for df in flight_lines:
        data_source = ColumnDataSource(data=df)
        l_b = p.line(x='X', y='Y', source=data_source, color='white', line_width=2)

    for df in flight_lines:
        data_source = ColumnDataSource(data=df)
        data_sources.append(data_source)
        l = p.line(x='X', y='Y', source=data_source, color=app.config["COLOR_PRIMARY"], line_width=1)
        flight_glyphs.append(l)

    highlight_source = ColumnDataSource(data={'X': [], 'Y': []})
    p.scatter(x='X', y='Y', source=highlight_source, line_width=3, color=app.config["COLOR_ACCENT"])

    if dataset == 'antarctica':
        p.xaxis.axis_label = "ESPG:3031 X"
        p.yaxis.axis_label = "ESPG:3031 Y"
    elif dataset == 'greenland':
        p.xaxis.axis_label = "ESPG:3413 X"
        p.yaxis.axis_label = "ESPG:3413 Y"
    else:
        raise(Exception(f"Unexpected dataset {dataset} - should be antarctica or greenland"))

    p.add_tools(HoverTool(
        renderers=flight_glyphs,
        tooltips=[
            ('Track', '@{Track}'),
            ('CBD', '@CBD')
        ]
    ))


    map_tile_sources = map_tile_sources_all[dataset] # select greenland or antarctica data tiles
    
    tile_options = {}
    tile_options['url'] = map_tile_sources[0]['url']
    tile_options['attribution'] = map_tile_sources[0]['attribution']
    tile_source = BBoxTileSource(**tile_options)
    ts_glyph = p.add_tile(tile_source)
    ts_glyph.level = 'underlay'

    # Create tile change code
    tile_select_code = ""
    first = True
    for ts in map_tile_sources:
        if not first:
            tile_select_code += " else "
        else:
            first = False
        
        tile_select_code += f"""if (cb_obj.value == "{ts["name"]}") {{
    tile_source.url = "{ts["url"]}";
    tile_source.attribution = "{ts["attribution"]}";
    $(".bk-tile-attribution").html("{ts["attribution"]}");
}}"""
    # Manually setting the tile attribution div is a bit of a hack. Updating the attribution in the tile source does not
    # cause a change in what is displayed, so this is a workaround for now.

    cb_tile_select = CustomJS(args=dict(tile_source=tile_source), code=tile_select_code)

    tile_select = Select(value=map_tile_sources[0]['name'],
                          options=[ts['name'] for ts in map_tile_sources])
    tile_select.js_on_change('value', cb_tile_select)

    if len(flight_lines) > 1:
        url = f"@url"
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



