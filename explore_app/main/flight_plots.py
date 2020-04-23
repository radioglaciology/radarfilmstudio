from bokeh.plotting import figure
from bokeh.models.sources import ColumnDataSource
from bokeh.models import TapTool, CustomJS, CDSView, CustomJSFilter
from bokeh.embed import components
from bokeh.transform import linear_cmap
from bokeh.layouts import column, row
from bokeh.models import Toggle

import pandas as pd

from explore_app.film_segment import FilmSegment


def make_cbd_plot(session, flight_id, width, height):
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

    layout = row(p, column(toggle_verified, toggle_junk, toggle_z, toggle_a))

    script, div = components(layout)
    return f'\n{script}\n\n{div}\n'