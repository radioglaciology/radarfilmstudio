from flask import Blueprint, render_template, url_for, g, redirect

from flask import current_app as app
from .. import db, cache, scheduler

from .map import make_bokeh_map, load_flight_lines
from .flight_plots import make_cbd_plot, make_linked_flight_plots
from .stats_plots import make_flight_progress_bar_plot
from explore_app.film_segment import FilmSegment
from .stats_plots import update_flight_progress_stats

from sqlalchemy import and_, or_

import time

main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates',
                    static_folder='static')

flight_lines = load_flight_lines(app.config['FLIGHT_POSITIONING_DIR'])
all_flights_map = make_bokeh_map(800, 800, flight_lines=flight_lines)

flight_progress_stats_updated = None

@main_bp.before_app_first_request
def before_app_first_request():
    update_flight_progress_stats(db.session)
    global flight_progress_stats_updated
    flight_progress_stats_updated = time.time()


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


@main_bp.route('/stats/refresh/')
def stats_page_refresh():
    update_flight_progress_stats(db.session)
    return redirect(url_for("main_bp.stats_page"))

@main_bp.route('/stats/')
def stats_page():
    global flight_progress_stats_updated

    total_verified = FilmSegment.query.filter(FilmSegment.is_verified == True).count()
    total = FilmSegment.query.count()

    flightprogress_html = make_flight_progress_bar_plot()

    elapsed_time = time.time() - flight_progress_stats_updated
    if elapsed_time < 5:
        update_string = "just now"
    elif elapsed_time < 60:
        update_string = "less than a minute ago"
    else:
        update_string = f"about {int(elapsed_time / 60)} minutes ago"

    return render_template("stats.html", flightprogress=flightprogress_html,
                           total_verified=total_verified, total=total, percent=int(100*total_verified/total),
                           update_string=update_string,
                           breadcrumbs=[('Explorer', '/'), ('Stats', url_for('main_bp.stats_page'))])


# Periodic background updating

@scheduler.task('interval', id='update_stats', seconds=(60*30))
def update_stats():
    with db.app.app_context():
        update_flight_progress_stats(db.session)
        global flight_progress_stats_updated
        flight_progress_stats_updated = time.time()

# Page load time logic

@app.before_request
def before_request():
    g.start = time.time()

@app.after_request
def after_request(response):
    diff = time.time() - g.start
    if ((response.response) and
        (200 <= response.status_code < 300) and
        (response.content_type.startswith('text/html'))):
        response.set_data(response.get_data().replace(
            b'__EXECUTION_TIME__', bytes(f"{diff:.3f}", 'utf-8')))
    return response