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

flight_progress_stats = {'greenland': {}, 'antarctica': {}}

def update_flight_progress_stats(session):
    update_flight_progress_stats_dataset(session, 'antarctica', 'Antarctica ')
    update_flight_progress_stats_dataset(session, 'greenland', 'Greenland ', separate_by_date=True)

def update_flight_progress_stats_dataset(session, dataset, flight_name_prefix, separate_by_date=False):
    if separate_by_date:
        distinct_flights = FilmSegment.query.filter(FilmSegment.dataset == dataset).filter(FilmSegment.is_junk == False).with_entities(FilmSegment.flight, FilmSegment.raw_date).distinct().all()
    else:
        distinct_flights = FilmSegment.query.filter(FilmSegment.dataset == dataset).filter(FilmSegment.is_junk == False).with_entities(FilmSegment.flight).distinct().all()
        distinct_flights = [(x[0], None) for x in distinct_flights]

    verified_list = []
    unverified_list = []
    total_list = []
    for fid, fdate in distinct_flights:
        q = FilmSegment.query.filter(and_(FilmSegment.flight == fid, FilmSegment.raw_date == fdate,
                                            FilmSegment.dataset == dataset, FilmSegment.is_junk == False))
        count_verified = q.filter(FilmSegment.is_verified == True).count()
        count_total = q.count()

        verified_list.append(count_verified)
        total_list.append(count_total)
        unverified_list.append(count_total - count_verified)

    def make_flight_url(id, date, dataset):
        if date is None:
            return f"/flight/{dataset}/{id}"
        else:
            return f"/flight/{dataset}/{id}/{date}"

    flight_progress_stats[dataset]['flight_ids'] = [x[0] for x in distinct_flights]
    flight_progress_stats[dataset]['flight_dates'] = [x[1] for x in distinct_flights]
    flight_progress_stats[dataset]['url'] = [make_flight_url(x[0], x[1], dataset) for x in distinct_flights]
    flight_progress_stats[dataset]['flights'] = [f"{flight_name_prefix}Flight {fid}{'' if (fdate is None) else ' ['+str(fdate)+']'}" for fid, fdate in distinct_flights]
    flight_progress_stats[dataset]['total_segments'] = total_list
    flight_progress_stats[dataset]['verified'] = verified_list
    flight_progress_stats[dataset]['unverified'] = unverified_list
    flight_progress_stats[dataset]['dataset'] = [dataset]*len(unverified_list)


def make_flight_progress_bar_plot(include_greenland=False):

    if include_greenland:
        stats = {}
        for k in flight_progress_stats['antarctica']:
            stats[k] = flight_progress_stats['antarctica'][k] + flight_progress_stats['greenland'][k]
    else:
        stats = flight_progress_stats['antarctica']

    fps_df = pd.DataFrame(stats).sort_values(by=['dataset', 'flight_ids'], ascending=False)

    p = figure(y_range=fps_df['flights'], plot_height=20*len(stats['flight_ids']),
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

    url = "@url"
    taptool = p.select(type=TapTool)
    taptool.callback = OpenURL(url=url, same_tab=True)

    script, div = components(p)
    return f'\n{script}\n\n{div}\n'
