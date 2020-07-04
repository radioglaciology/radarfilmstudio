from bokeh.plotting import figure
from bokeh.models.sources import ColumnDataSource
from bokeh.models import TapTool, CustomJS, CDSView, CustomJSFilter, OpenURL
from bokeh.embed import components
from bokeh.transform import linear_cmap
from bokeh.layouts import column, row
from bokeh.models import Toggle, Select, CustomJS, Circle

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import time

from explore_app.film_segment import FilmSegment

from explore_app.main.map import make_bokeh_map

from flask import current_app as app
from flask import g
from sqlalchemy import and_

flight_progress_stats = {
    'flight_ids': [],
    'flights': [],
    'total_segments': [],
    'verified': [],
    'unverified': []
}


def update_flight_progress_stats(session):
    distinct_ids = FilmSegment.query.with_entities(FilmSegment.flight).distinct().all()
    flight_ids = [x[0] for x in distinct_ids]

    verified_list = []
    unverified_list = []
    total_list = []
    for fid in flight_ids:
        count_verified = FilmSegment.query.filter(and_(FilmSegment.flight == fid, FilmSegment.is_verified == True)).count()
        count_total = FilmSegment.query.filter(FilmSegment.flight == fid).count()

        verified_list.append(count_verified)
        total_list.append(count_total)
        unverified_list.append(count_total - count_verified)

    flight_progress_stats['flight_ids'] = flight_ids
    flight_progress_stats['flights'] = [f"Flight {f}" for f in flight_ids]
    flight_progress_stats['total_segments'] = total_list
    flight_progress_stats['verified'] = verified_list
    flight_progress_stats['unverified'] = unverified_list


def make_flight_progress_bar_plot():
    fps_df = pd.DataFrame(flight_progress_stats).sort_values(by='flight_ids', ascending=False)

    p = figure(y_range=fps_df['flights'], plot_height=20*len(flight_progress_stats['flight_ids']),
               toolbar_location=None, tools="hover,tap", tooltips="@$name film segments")

    p.hbar_stack(['verified', 'unverified'], y='flights', height=0.8,
                 source=ColumnDataSource(fps_df),
                 color=[app.config['COLOR_SKY'], app.config['COLOR_GRAY']],
                 legend_label=['Verified', 'Unverified'])

    p.y_range.range_padding = 0.1
    p.ygrid.grid_line_color = None
    p.legend.location = "top_right"
    p.axis.minor_tick_line_color = None
    p.outline_line_color = None
    p.min_border_top = 0
    p.min_border_bottom = 0
    p.sizing_mode = 'stretch_width'

    url = "/flight/@flight_ids/"
    taptool = p.select(type=TapTool)
    taptool.callback = OpenURL(url=url, same_tab=True)

    script, div = components(p)
    return f'\n{script}\n\n{div}\n'
