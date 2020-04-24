from bokeh.plotting import figure
from bokeh.models.sources import ColumnDataSource
from bokeh.models import TapTool, CustomJS, CDSView, CustomJSFilter
from bokeh.embed import components
from bokeh.transform import linear_cmap
from bokeh.layouts import column, row
from bokeh.models import Toggle

import pandas as pd

from explore_app.film_segment import FilmSegment

from explore_app.main.map import make_bokeh_map


def make_cbd_plot(session, flight_id, width, height, return_plot=False):
    df = pd.read_sql(session.query(FilmSegment).filter(FilmSegment.flight == flight_id).statement, session.bind)
    source = ColumnDataSource(df)

    toggle_verified = Toggle(label="Show only verified")
    toggle_junk = Toggle(label="Hide junk", active=True)
    toggle_z = Toggle(label="Show Z Scopes", active=True)
    toggle_a = Toggle(label="Show A Scopes", active=True)

    toggle_verified.js_on_change('active', CustomJS(args=dict(source=source), code="source.change.emit()"))
    toggle_junk.js_on_change('active', CustomJS(args=dict(source=source), code="source.change.emit()"))
    toggle_z.js_on_change('active', CustomJS(args=dict(source=source), code="source.change.emit()"))
    toggle_a.js_on_change('active', CustomJS(args=dict(source=source), code="source.change.emit()"))

    filter_verified = CustomJSFilter(args=dict(source=source, tog=toggle_verified), code='''
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
    filter_junk = CustomJSFilter(args=dict(source=source, tog=toggle_junk), code='''
        var indices = [];
        for (var i = 0; i < source.get_length(); i++){
            if (tog.active && source.data['is_junk'][i]){
                indices.push(false);
            } else {
                indices.push(true);
            }
        }
        return indices;
    ''')
    filter_scope = CustomJSFilter(args=dict(source=source, tog_a=toggle_a, tog_z=toggle_z), code='''
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
        return indices;
    ''')
    view = CDSView(source=source, filters=[filter_verified, filter_junk, filter_scope])

    TOOLTIPS = [
        ("Reel", "@reel"),
        ("Scope", "@scope_type"),
        ("Verified", "@is_verified")
    ]

    p = figure(tools=['pan,wheel_zoom,box_zoom,reset,tap,hover'], tooltips=TOOLTIPS)

    p.segment(y0='first_frame', y1='last_frame', x0='first_cbd', x1='last_cbd',
              color=linear_cmap('reel', "Viridis256", 1, 57), source=source, view=view)
    p.scatter('first_cbd', 'first_frame', color=linear_cmap('reel', "Viridis256", 1, 57), source=source, view=view)
    p.scatter('last_cbd', 'last_frame', color=linear_cmap('reel', "Viridis256", 1, 57), source=source, view=view)

    p.xaxis.axis_label = "CBD"
    p.yaxis.axis_label = "Frame"

    p.sizing_mode = "fixed"
    p.width = width
    p.height = height
    p.title.text = "Film Segments"

    # Select matching code from https://stackoverflow.com/questions/54768576/python-bokeh-customjs-debugging-a-javascript-callback-for-the-taping-tool

    code = """
    update_form_id(source.data['id'][source.selected.indices[0]]);
    """

    tap = p.select(type=TapTool)
    callback = CustomJS(args={'source': source}, code=code)
    tap.callback = callback

    if return_plot:
        return p, column(toggle_verified, toggle_junk, toggle_z, toggle_a), source
    else:
        layout = row(p, column(toggle_verified, toggle_junk, toggle_z, toggle_a))

        script, div = components(layout)
        return f'\n{script}\n\n{div}\n'


def make_linked_flight_plots(session, flight_id, flight_lines=None):
    p_map, map_flight_lines = make_bokeh_map(300, 300, flight_id=flight_id, title=f"Flight {flight_id}",
                           flight_lines=flight_lines, return_plot=True)
    p_cbd, cbd_controls, cbd_source = make_cbd_plot(session, flight_id, 500, 300, return_plot=True)

    # What this does:
    # 1. Only allow selection of one segment at a time
    # Old additional code:
    #     var inds = cb_obj.indices;
    #     var cbd_data = cbd_source.data;
    #     for (var i = 0; i < inds.length; i++) {
    #         console.log(cbd_data['first_cbd'][inds[i]]);
    #         console.log(cbd_data['last_cbd'][inds[i]]);
    #     }
    cbd_source.selected.js_on_change('indices', CustomJS(args=dict(cbd_source=cbd_source), code="""
        cb_obj.indices = [cb_obj.indices[0]];
    """))


    layout = row(p_cbd, cbd_controls)
    cbd_script, cbd_div = components(layout)
    cbd_html = f'\n{cbd_script}\n\n{cbd_div}\n'

    map_script, map_div = components(p_map)
    map_html = f"\n{map_script}\n\n{map_div}\n"

    return map_html, cbd_html