from flask import Blueprint, render_template, url_for

from flask import current_app as app
from .. import db, cache

from .map import make_bokeh_map, load_flight_lines
from .flight_plots import make_cbd_plot, make_linked_flight_plots
from .stats_plots import make_flight_progress_bar_plot
from explore_app.film_segment import FilmSegment

from sqlalchemy import and_, or_

main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates',
                    static_folder='static')

flight_lines = load_flight_lines(app.config['FLIGHT_POSITIONING_DIR'])
all_flights_map = make_bokeh_map(800, 800, flight_lines=flight_lines)

@main_bp.route('/')
@main_bp.route('/map/')
@cache.cached()
def map_page():
    return render_template("map.html", map=all_flights_map,
                           breadcrumbs=[('Explorer', '/'),
                                        ('Map', url_for('main_bp.map_page'))])

@main_bp.route('/flight/<int:flight_id>/')
def flight_page(flight_id):
    #map = make_bokeh_map(300, 300, flight_id=flight_id, title="Flight Map", flight_lines=flight_lines)
    #cbd_plot = make_cbd_plot(db.session, flight_id, 500, 300)

    map, cbd = make_linked_flight_plots(db.session, flight_id, flight_lines=flight_lines)

    return render_template("flight.html", flight=flight_id, map=map, cbd_plot=cbd,
                           breadcrumbs=[('Explorer', '/'), (f'Flight {flight_id}', url_for('main_bp.flight_page', flight_id=flight_id))])

@main_bp.route('/update_form/<int:id>/')
def update_page(id):
    seg = FilmSegment.query.get(id)
    return render_template("update.html", segment=seg, breadcrumbs=[('Explorer', '/')])


@main_bp.route('/stats/')
def stats_page():
    total_verified = FilmSegment.query.filter(FilmSegment.is_verified == True).count()
    total = FilmSegment.query.count()
    #
    # distinct_ids = FilmSegment.query.with_entities(FilmSegment.flight).distinct().all()
    # flight_ids = [x[0] for x in distinct_ids]
    #
    # for fid in flight_ids:
    #     count_verified = FilmSegment.query.filter(and_(FilmSegment.flight == fid, FilmSegment.is_verified == True)).count()
    #     count_total = FilmSegment.query.filter(FilmSegment.flight == fid).count()
    #     print(f"Flight {fid}: {count_verified} of {count_total} verified")
    #
    # return f"{total_verified} / {total}"

    flightprogress_html = make_flight_progress_bar_plot(db.session)

    return render_template("stats.html", flightprogress=flightprogress_html,
                           total_verified=total_verified, total=total, percent=int(100*total_verified/total),
                           breadcrumbs=[('Explorer', '/')])


# TODO
# distinct_ids = FilmSegment.query.with_entities(FilmSegment.flight).distinct().all()
# flight_ids = [x[0] for x in distinct_ids]
#
# for fid in flight_ids:
#     count_verified = FilmSegment.query.filter(and_(FilmSegment.flight == fid, FilmSegment.is_verified == True)).count()
#     count_total = FilmSegment.query.filter(FilmSegment.flight == fid).count()
#     print(f"Flight {fid}: {count_verified} of {count_total} verified")