import os

import numpy as np

from bokeh.plotting import figure
from bokeh.models.sources import ColumnDataSource
from bokeh.models import OpenURL, TapTool, HoverTool, BBoxTileSource, Select, LinearColorMapper, CustomJSHover, ColorBar
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
    crs_3413 = crs.Stereographic(central_latitude=90, central_longitude=-45, true_scale_latitude=70)
    #crs_3413 = crs.epsg(3413)
    crs_lonlat = crs.PlateCarree()

    for filename in os.listdir(positioning_dir):
        if filename.endswith(".csv"):
            # Two formats of positioning CSVs unfortunately
            if filename.endswith("_final_QC.csv"): # Assume Greenland-style data
                fparts = filename.split('_')
                id = int(fparts[1][2:]) # flight id
                fdate = int(fparts[0])%100 # last 2 digits of year only

                df = pd.read_csv(os.path.join(positioning_dir, filename),
                                 header=None,
                                 names=["CBD", "Longitude", "Latitude", "Surf", "Bed"])
                df = df.apply(pd.to_numeric, errors='coerce')
                df = df.dropna(subset=["CBD", "Longitude", "Latitude"])
                df['Track'] = id
                df['Date'] = fdate
                df['url'] = f"/flight/{dataset}/{id}/{fdate}"
                df['Thickness'] = df['Surf'] - df['Bed']

            else: # Assume Antarctica style data
                id = int(filename.split('.')[0])
                fdate = None

                df = pd.read_csv(
                        os.path.join(positioning_dir, filename),
                        na_values=["9999"]
                    )
                df = df.rename(columns={'LAT': 'Latitude', 'LON': 'Longitude', 'THK': 'Thickness'}, errors='ignore').dropna(subset=["CBD", "Longitude", "Latitude"])
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

    no_flights_found = False
    if flight_id: # Select a specific flight
        if flight_date is not None:
            flight_identifier = (flight_id, flight_date%100) # only year part
            if flight_identifier in flight_lines:
                flight_lines = {flight_identifier: flight_lines[flight_identifier]}
            else:
                no_flights_found = True
        else:
            flight_lines = {flt_ident: flt_line for (flt_ident, flt_line) in flight_lines.items() if flt_ident[0] == flight_id}
            if len(flight_lines) == 0:
                no_flights_found = True
            
    # Handle case where no flights match the query
    if no_flights_found:
        not_found_html = "<div class='plot_error'>Couldn't find the requested flight ID.</div>"
        if return_components:
            return None
        elif return_plot:
            return not_found_html, None
        else:
            return not_found_html

    p = figure(match_aspect=True, tools=['pan,wheel_zoom,box_zoom,reset,tap,save'], active_scroll='wheel_zoom')

    data_sources = []
    flight_glyphs = {}

    thickness_color_mapper = LinearColorMapper(palette='Magma256', low=0, high=4000)
    color_bar = ColorBar(color_mapper=thickness_color_mapper)

    color_bar_plot = figure(title="Ice Thickness [m]", title_location="right",
                        sizing_mode='stretch_both',
                        toolbar_location=None, min_border=0, 
                        outline_line_color=None)

    color_bar_plot.add_layout(color_bar, 'right')
    color_bar_plot.title.align="center"

    for flight_identifier, df in flight_lines.items():
        data_source = ColumnDataSource(data=df)
        data_sources.append(data_source)
        #l = p.line(x='X', y='Y', source=data_source, color=app.config["COLOR_PRIMARY"], line_width=1)
        l = p.scatter(x='X', y='Y', source=data_source, color={'field': 'Thickness', 'transform': thickness_color_mapper}, size=2)
        flight_glyphs[flight_identifier] = l

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

    tooltips = [
        ('Track', '@{Track}'),
        ('CBD', '@CBD'),
    ]
    if dataset == 'greenland':
        tooltips.append(('Year', '19@{Date}'))

    p.add_tools(HoverTool(
        renderers=list(flight_glyphs.values()),
        tooltips=tooltips
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

    # Date picker
    glyphs_dict = {'All years': []}
    for ident, glyph in flight_glyphs.items():
        glyphs_dict['All years'].append(glyph)

        if ident[1] is not None:
            year_string = f"19{ident[1]}"
            if year_string not in glyphs_dict:
                glyphs_dict[year_string] = []
            glyphs_dict[year_string].append(glyph)

    years = list(set([yr for (_, yr) in flight_lines.keys()]))

    filter_flight_lines = """
    for (var i = 0; i < glyphs['All years'].length; i++) {
        glyphs['All years'][i].visible = false;
    }
    for (var i = 0; i < glyphs[cb_obj.value].length; i++) {
        glyphs[cb_obj.value][i].visible = true;
    }
    console.log(cb_obj.value);
    """
    cb_filter_flight_lines = CustomJS(args={'glyphs': glyphs_dict}, code=filter_flight_lines)
    date_select = Select(value="All years", options=["All years"] + [f"19{yr}" for yr in years if yr is not None])
    date_select.js_on_change('value', cb_filter_flight_lines)


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
            'color_bar': color_bar_plot,
            'tile_select': tile_select,
            'flight_lines': flight_lines,
            'data_sources': data_sources,
            'highlight_source': highlight_source,
            'date_select': date_select
        }
    elif return_plot:
        return p, flight_lines
    else:
        script, div = components(p)
        return f'\n{script}\n\n{div}\n'



