from flask import Blueprint, render_template, url_for

from flask import current_app as app
from .. import db, cache

from .map import make_bokeh_map, load_flight_lines
from .flight_plots import make_cbd_plot, make_linked_flight_plots
from explore_app.film_segment import FilmSegment

main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates',
                    static_folder='static')

flight_lines = load_flight_lines(app.config['FLIGHT_POSITIONING_DIR'])

@main_bp.route('/')
@main_bp.route('/map/')
@cache.cached()
def map_page():
    flights_map = make_bokeh_map(500, 500, flight_lines=flight_lines)
    return render_template("map.html", map=flights_map,
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
