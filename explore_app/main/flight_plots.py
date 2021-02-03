from bokeh.plotting import figure
from bokeh.models.sources import ColumnDataSource
from bokeh.models import TapTool, CustomJS, CDSView, CustomJSFilter, HoverTool
from bokeh.embed import components
from bokeh.transform import linear_cmap
from bokeh.layouts import column, row
from bokeh.models import Toggle, Select, CustomJS, Circle, WheelZoomTool

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from explore_app.film_segment import FilmSegment

from explore_app.main.map import make_bokeh_map

from flask import current_app as app


def make_cbd_plot(session, flight_id, width, height, return_plot=False, pageref=0):
    df = pd.read_sql(session.query(FilmSegment).filter(FilmSegment.flight == flight_id).statement, session.bind)

    # Add colormaps to plot
    norm_reels = matplotlib.colors.Normalize(vmin=df['reel'].min(), vmax=df['reel'].max(), clip=True)
    mapper_reels = plt.cm.ScalarMappable(norm=norm_reels, cmap=plt.cm.viridis)

    df['Color by Reel'] = df['reel'].apply(lambda x: mcolors.to_hex(mapper_reels.to_rgba(x)))
    df['Color by Verified'] = df['is_verified'].apply(lambda x: app.config['COLOR_ACCENT'] if x else app.config['COLOR_GRAY'])
    df['Color by Review'] = df['needs_review'].apply(lambda x: app.config['COLOR_ACCENT'] if x else app.config['COLOR_GRAY'])
    df['Color by Frequency'] = df['instrument_type'].apply(lambda x: app.config['COLOR_REDWOOD'] if x == FilmSegment.RADAR_60MHZ else (app.config['COLOR_PALO_ALOT'] if x == FilmSegment.RADAR_300MHZ else app.config['COLOR_GRAY']))

    #

    source = ColumnDataSource(df)

    toggle_verified = Toggle(label="Show only verified")
    toggle_junk = Toggle(label="Hide junk", active=True)
    toggle_z = Toggle(label="Show Z Scopes", active=True)
    toggle_a = Toggle(label="Show A Scopes", active=True)

    toggle_verified.js_on_change('active', CustomJS(args=dict(source=source), code="source.change.emit()"))
    toggle_junk.js_on_change('active', CustomJS(args=dict(source=source), code="source.change.emit()"))
    toggle_z.js_on_change('active', CustomJS(args=dict(source=source), code="source.change.emit()"))
    toggle_a.js_on_change('active', CustomJS(args=dict(source=source), code="source.change.emit()"))

    filter_verified = CustomJSFilter(args=dict(tog=toggle_verified), code='''
        var indices = [];
        for (var i = 0; i < source.get_length(); i++){
            if ((!tog.active) || source.data['is_verified'][i]){
                indices.push(true);
            } else {
                indices.push(false);
            }
        }
        return indices;
    ''')
    filter_junk = CustomJSFilter(args=dict(tog=toggle_junk), code='''
        var indices = [];
        for (var i = 0; i < source.get_length(); i++){
            if (tog.active && source.data['is_junk'][i]){
                indices.push(false);
            } else {
                indices.push(true);
            }
        }
        console.log(indices);
        return indices;
    ''')
    filter_scope = CustomJSFilter(args=dict(tog_a=toggle_a, tog_z=toggle_z), code='''
        console.log('filter_scope');
        var indices = [];
        for (var i = 0; i < source.get_length(); i++){
            if (tog_a.active && (source.data['scope_type'][i] == 'a')){
                indices.push(true);
            } else if (tog_z.active && (source.data['scope_type'][i] == 'z')) {
                indices.push(true);
            } else {
                indices.push(false);
            }
        }
        console.log(indices);
        return indices;
    ''')
    view = CDSView(source=source, filters=[filter_verified, filter_junk, filter_scope])

    p = figure(tools=['pan,box_zoom,wheel_zoom,box_select,lasso_select,reset,tap'], active_scroll='wheel_zoom')



    segs = p.segment(y0='first_frame', y1='last_frame', x0='first_cbd', x1='last_cbd',
              color=app.config["COLOR_GRAY"], source=source, view=view)
    scat_first = p.scatter('first_cbd', 'first_frame', color='Color by Verified', source=source, view=view,
                           nonselection_fill_color=app.config["COLOR_GRAY"])
    scat_last = p.scatter('last_cbd', 'last_frame', color='Color by Verified', source=source, view=view,
                          nonselection_fill_color=app.config["COLOR_GRAY"])

    p.add_tools(HoverTool(
        renderers=[segs],
        tooltips=[
            ("Reel", "@reel"),
            ("Scope", "@scope_type"),
            ("Verified", "@is_verified")
        ]
    ))

    p.xaxis.axis_label = "CBD"
    p.yaxis.axis_label = "Frame"

    p.sizing_mode = "stretch_both"
    if (width is not None) and (height is not None):
        p.width = width
        p.height = height
    p.title.text = "Film Segments"

    # Select matching code from https://stackoverflow.com/questions/54768576/python-bokeh-customjs-debugging-a-javascript-callback-for-the-taping-tool

    cb_cselect = CustomJS(args=dict(s1=scat_first, s2=scat_last, csource=source), code="""
            var selected_color = cb_obj.value;
            s1.glyph.line_color.field = selected_color;
            s1.glyph.fill_color.field = selected_color;
            s2.glyph.line_color.field = selected_color;
            s2.glyph.fill_color.field = selected_color;
            csource.change.emit();
        """)

    color_select = Select(value="Color by Verified",
                          options=["Color by Verified", "Color by Reel", "Color by Review", "Color by Frequency"])
    color_select.js_on_change('value', cb_cselect)

    p.toolbar.active_scroll = p.select_one(WheelZoomTool)

    if return_plot:
        return p, column(toggle_verified, toggle_junk, toggle_z, toggle_a, color_select), source
    else:
        layout = row(p, column(toggle_verified, toggle_junk, toggle_z, toggle_a, color_select))

        script, div = components(layout)
        return f'\n{script}\n\n{div}\n'


def make_linked_flight_plots(session, flight_id, flight_lines=None):
    p_cbd, cbd_controls, cbd_source = make_cbd_plot(session, flight_id, None, None, return_plot=True)
    cbd_controls.sizing_mode = 'stretch_both'

    map_dict = make_bokeh_map(None, None, flight_id=flight_id, title=f"Flight {flight_id}",
                                         flight_lines=flight_lines, return_components=True)
    

    # Selecting data updates list of film segments
    cbd_source.selected.js_on_change('indices',
                                    CustomJS(args=dict(cbd_source=cbd_source), code="""
                
                console.log(cbd_source.selected.indices);
                var ids = [];
                for (var j=0; j < cbd_source.selected.indices.length; j++) {
                    ids.push(cbd_source.data['id'][cb_obj.indices[j]]);
                }
                update_film_segment_list(ids);
                """))


    if map_dict is not None:
        p_map, map_data_sources, map_highlight_source = map_dict['map'], map_dict['data_sources'], map_dict['highlight_source'] # unpack map parts we need

        map_dict['tile_select'].sizing_mode = 'stretch_width'

        # Setup cross-linking between CDB and map plots
        cbd_source.selected.js_on_change('indices',
                                        CustomJS(args=dict(cbd_source=cbd_source,
                                                            map_source=map_data_sources[0],
                                                            highlight_source=map_highlight_source), code="""
                highlight_source.data['X'] = [];
                highlight_source.data['Y'] = [];

                for (var j=0; j < cbd_source.selected.indices.length; j++) {
                    var first_cbd = cbd_source.data['first_cbd'][cb_obj.indices[j]];
                    var last_cbd = cbd_source.data['last_cbd'][cb_obj.indices[j]];
                    if (first_cbd > last_cbd) {
                        var temp = first_cbd;
                        first_cbd = last_cbd;
                        last_cbd = temp;
                    }
                    
                    for (var i=0; i < map_source.data['CBD'].length; i++) {
                        if ((map_source.data['CBD'][i] >= first_cbd) && (map_source.data['CBD'][i] <= last_cbd)) {
                            highlight_source.data['X'].push(map_source.data['X'][i]);
                            highlight_source.data['Y'].push(map_source.data['Y'][i]);
                        }
                    }
                }

                highlight_source.change.emit();
            """))

        map_data_sources[0].selected.js_on_change('line_indices', CustomJS(args={'cbd_source': cbd_source, 'map_source': map_data_sources[0]}, code="""
            if (cb_obj.line_indices.length > 0) {
                cbd_source.selected.indices = [];

                for (var j=0; j < cb_obj.line_indices.length; j++) {
                    var cbd = map_source.data['CBD'][cb_obj.line_indices[j]];

                    for (var i=0; i < cbd_source.data['first_cbd'].length; i++) {
                        var first_cbd = cbd_source.data['first_cbd'][i];
                        var last_cbd = cbd_source.data['last_cbd'][i];
                        if (first_cbd > last_cbd) {
                            var temp = first_cbd;
                            first_cbd = last_cbd;
                            last_cbd = temp;
                        }

                        if ((cbd >= first_cbd) && (cbd <= last_cbd)) {
                            cbd_source.selected.indices.push(i);
                        }
                    }
                }

                cbd_source.change.emit();
                cbd_source.selected.change.emit();

                //var change_callbacks = cbd_source.selected.js_property_callbacks["change:indices"];
                //for (var i=0; i < change_callbacks.length; i++) {
                //    change_callbacks[i].execute(cbd_source.selected, null);
                //}
            }
        
        """))

        plots = {'map': p_map, 'cbd': p_cbd, 'controls': cbd_controls, 'tile_select': map_dict['tile_select']}
        script, divs = components(plots)
        return f'\n{script}\n\n{divs["map"]}\n', f'\n {divs["cbd"]}\n', f'\n{divs["controls"]}\n', f'\n{divs["tile_select"]}\n'
    else:
        plots = {'cbd': p_cbd, 'controls': cbd_controls}
        script, divs = components(plots)
        return f"\n{script}\n\n<div class='plot_error'>Couldn't find the requested flight ID.</div>\n", f'\n {divs["cbd"]}\n', f'\n{divs["controls"]}\n', f''
