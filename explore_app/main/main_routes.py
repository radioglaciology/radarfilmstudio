from flask import Blueprint, render_template, url_for, g, redirect, request, send_from_directory, abort

from flask import current_app as app
from .. import db, cache, scheduler, queue

from flask_login import current_user

from .map import make_bokeh_map, load_flight_lines
from .flight_plots import make_cbd_plot, make_linked_flight_plots
from .stats_plots import make_flight_progress_bar_plot
from explore_app.film_segment import FilmSegment
from .stats_plots import update_flight_progress_stats

from ..api.api_routes import has_write_permission, load_image
from ..api.image_processing import stitch_images

from sqlalchemy import and_, or_

import time
import math
from collections import OrderedDict
import uuid
import os
from datetime import datetime

main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates',
                    static_folder='static')

flight_lines = load_flight_lines(app.config['FLIGHT_POSITIONING_DIR'])
all_flights_map = make_bokeh_map(800, 800, flight_lines=flight_lines)

flight_progress_stats_updated = None

query_cache = {}
images_cache = {}


@main_bp.before_app_first_request
def before_app_first_request():
    update_flight_progress_stats(db.session)
    global flight_progress_stats_updated
    flight_progress_stats_updated = time.time()


@main_bp.route('/')
@main_bp.route('/map/')
def map_page():
    return render_template("map.html", map=all_flights_map,
                           breadcrumbs=[('Explorer', '/'),
                                        ('Map', url_for('main_bp.map_page'))])

@main_bp.route('/flight/<int:flight_id>/')
def flight_page(flight_id):
    #map = make_bokeh_map(300, 300, flight_id=flight_id, title="Flight Map", flight_lines=flight_lines)
    #cbd_plot = make_cbd_plot(db.session, flight_id, 500, 300)

    map, cbd = make_linked_flight_plots(db.session, flight_id, flight_lines=flight_lines)

    # Check for a direct link to a specific segment to be loaded
    if 'id' in request.args:
        segment_id = int(request.args['id'])
    else:
        segment_id = None

    print(app.config['ENABLE_TIFF'])

    return render_template("flight.html", flight=flight_id, map=map, cbd_plot=cbd, segment_id=segment_id,
                           pageref=0, show_view_toggle=True, enable_tiff=app.config['ENABLE_TIFF'],
                           breadcrumbs=[('Explorer', '/'), (f'Flight {flight_id}', url_for('main_bp.flight_page', flight_id=flight_id))])

@main_bp.route('/query/action', methods=["POST"])
def query_bulk_action():
    t = time.time()
    if not has_write_permission(current_user):
        return "You're not logged in or don't have the appropriate permissions."

    qid = request.form['query_id']
    action_type = request.form['action_type']
    scope = request.form['scope']
    if not qid or (not (qid in query_cache)):
        return "No query id specified or query id invalid. If you've had this page open more than an hour, your query "\
               "may have expired. "
    if not action_type:
        return "No action specified"
    if not scope:
        return "No scope specified"

    query_log = query_cache[qid]

    if scope == 'page':
        query_ids = query_log['page_query']
    elif scope == 'query':
        query_ids = query_log['full_query']
    else:
        return "Invalid scope specified"

    query = FilmSegment.query.filter(FilmSegment.id.in_(query_ids))

    if action_type == 'mark_verified':
        for f in query.all():
            f.is_verified = True
            f.updated_by = current_user.email
            f.last_changed = datetime.now()
        db.session.commit()
    elif action_type == 'set_60mhz':
        for f in query.all():
            f.instrument_type = 10
            f.updated_by = current_user.email
            f.last_changed = datetime.now()
        db.session.commit()
    elif action_type == 'set_300mhz':
        for f in query.all():
            f.instrument_type = 20
            f.updated_by = current_user.email
            f.last_changed = datetime.now()
        db.session.commit()
    elif action_type == 'stitch':
        image_type = request.form.get('format', 'jpg')
        scale_x = float(request.form.get('scale_x', 1))
        scale_y = float(request.form.get('scale_y', 1))
        flip = request.form.get('flip', "")

        if query.count() > 10 and image_type != 'jpg':
            return "Sorry, merging more than 10 images into TIFF format is not yet supported due to the absurd size of the original TIFF images."

        query = query.order_by(FilmSegment.first_cbd)
        img_paths = [f.path for f in query.all()]

        job = queue.enqueue(stitch_images, args=(img_paths, image_type, flip, scale_x, scale_y, qid, app.config['TMP_OUTPUTS_DIR'], app.config['FILM_IMAGES_DIR']))
        return f"started:{job.get_id()}"

    else:
        return "Unknown action type"

    print(f"Request type [{action_type}] took {time.time() - t} seconds to process")
    return "success"


@main_bp.route('/outputs/<query_id>')
def get_output_image(query_id):
    if query_id in images_cache:
        tmp_path = os.path.join(os.getcwd(), app.config['TMP_OUTPUTS_DIR'])
        return send_from_directory(tmp_path, images_cache[query_id]['filename'], as_attachment=True)
    else:
        return abort(404)


@main_bp.route('/query')
def query_results():
    query = FilmSegment.query

    # Filters

    if request.args.get('flight'):
        query = query.filter(FilmSegment.flight == int(request.args.get('flight')))

    if request.args.get('reel'):
        query = query.filter(FilmSegment.reel == int(request.args.get('reel')))

    if request.args.get('verified'):
        if int(request.args.get('verified')) == 0:
            query = query.filter(FilmSegment.is_verified == False)
        elif int(request.args.get('verified')) == 1:
            query = query.filter(FilmSegment.is_verified == True)

    if request.args.get('scope'):
        query = query.filter(FilmSegment.scope_type == request.args.get('scope'))

    if request.args.get('mincbd'):
        query = query.filter(FilmSegment.first_cbd >= int(request.args.get('mincbd')))

    if request.args.get('maxcbd'):
        query = query.filter(FilmSegment.first_cbd <= int(request.args.get('maxcbd')))

    if request.args.get('minframe'):
        query = query.filter(FilmSegment.first_frame >= int(request.args.get('minframe')))

    if request.args.get('maxframe'):
        query = query.filter(FilmSegment.first_frame <= int(request.args.get('maxframe')))

    # Sorting

    if request.args.get('sort'):
        if request.args.get('sort') == 'cbd':
            query = query.order_by(FilmSegment.first_cbd)
        elif request.args.get('sort') == 'frame':
            query = query.order_by(FilmSegment.first_frame)

    # Number and page of results

    if request.args.get('n'):
        n = int(request.args.get('n'))
    else:
        n = 10

    if request.args.get('skip'):
        query.offset(int(request.args.get('skip')))

    n_total_results = query.count()
    n_pages = math.ceil(n_total_results / n)

    if request.args.get('page'):
        current_page = int(request.args.get('page'))
        query = query.offset((current_page-1) * n)
    else:
        current_page = 1

    query_page = query.limit(n)  # Just this page

    # Record this query (temporarily)

    query_log = {'full_query': [x.id for x in query.all()],
                 'page_query': [x.id for x in query_page.all()],
                 'timestamp': time.time()}

    qid = str(uuid.uuid4())
    query_cache[qid] = query_log

    # Display options

    if request.args.get('history') and int(request.args.get('history')) == 0:
        show_history = 0
    else:
        show_history = 1

    # Figure out pagination

    # All the page links should repeat all the GET arguments except the page
    base_args = {k: v for k,v in request.args.items() if k != 'page'}

    # Create an ordered dictionary of page numbers to links to the appropriate query
    pages = OrderedDict()
    # Our convention here is to display links to the first page, the the last page, and the pages before/after the current
    for pg in [1, current_page-1, current_page, current_page+1, n_pages]:
        if (pg > 0) and (pg <= n_pages) and (not (pg in pages)):  # Sometimes this list may overlap - don't repeat any pages
            pages[pg] = url_for('main_bp.query_results', page=pg, **base_args)

    prev_page = current_page - 1 # A value of 0 indicates no previous page
    if current_page < n_pages:
        next_page = current_page + 1
    else:
        next_page = 0

    # Return results

    segs = query_page.all()
    return render_template("queryresults.html", segments=segs, show_view_toggle=True, show_history=show_history,
                           n_total_results=n_total_results, n_pages=n_pages, current_page=current_page,
                           next_page=next_page, prev_page=prev_page, page_map=pages, query_id=qid,
                           enable_tiff=app.config['ENABLE_TIFF'],
                           breadcrumbs=[('Explorer', '/'), ('Query Results', url_for('main_bp.query_results'))])


@main_bp.route('/update_form/<int:id>/')
def update_page(id):
    seg = FilmSegment.query.get(id)
    return render_template("update.html", segment=seg, enable_tiff=app.config['ENABLE_TIFF'],
                           breadcrumbs=[('Explorer', '/')])


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


@main_bp.route('/testerror')
def testerror():
    raise Exception("Not a real error. Just a test.")


# Periodic background updating

@scheduler.task('interval', id='update_stats', seconds=(60*30))
def update_stats():
    with db.app.app_context():
        update_flight_progress_stats(db.session)
        global flight_progress_stats_updated
        flight_progress_stats_updated = time.time()

@scheduler.task('interval', id='clear_query_cache', seconds=(60*60))
def clear_query_cache():
    with db.app.app_context():
        for k in list(query_cache):
            if time.time() - query_cache[k]['timestamp'] > (60*60):
                query_cache.pop(k, None)
        for k in list(images_cache):
            if time.time() - images_cache[k]['timestamp'] > (2*60):
                old_file = os.path.join(app.config['TMP_OUTPUTS_DIR'], images_cache[k]['filename'])
                print(f"Deleting {old_file}")
                os.remove(old_file)
                images_cache.pop(k, None)

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