from flask import Blueprint, render_template, url_for, g, redirect, request, send_from_directory, abort, send_file
from rq.job import Job

from flask import current_app as app
from .. import db, cache, scheduler, queue
from worker import conn

from flask_login import current_user

from .map import make_bokeh_map, load_flight_lines
from .flight_plots import make_linked_flight_plots
from .stats_plots import make_flight_progress_bar_plot
from explore_app.film_segment import FilmSegment
from .stats_plots import update_flight_progress_stats

from ..api.api_routes import has_write_permission, load_image, query_results_from_database
from ..api.api_routes import query_cache, images_cache
from ..api.image_processing import stitch_images
from ..api.metadata_helper import worker_dummy_serve_metadata_dict

from sqlalchemy import and_, or_
from sqlalchemy.sql import func

from bokeh.embed import components

import time
import math
from collections import OrderedDict
import uuid
import os
import io
import sys
from datetime import datetime
import pandas as pd
import numpy as np

main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates',
                    static_folder='static')

flight_lines = {
    'antarctica': load_flight_lines(app.config['ANTARCTICA_FLIGHT_POSITIONING_DIR'], 'antarctica'),
    'greenland': load_flight_lines(app.config['GREENLAND_FLIGHT_POSITIONING_DIR'], 'greenland')
}

all_flights_maps = {}
for dataset in flight_lines:
    all_flights_maps[dataset] = make_bokeh_map(800, 800, flight_lines=flight_lines[dataset], return_components=True, dataset=dataset)
    all_flights_maps[dataset] = {k:all_flights_maps[dataset][k] for k in all_flights_maps[dataset] if k in ['map', 'color_bar', 'tile_select', 'date_select']}

flight_progress_stats_updated = None

def make_contributors_df():
    contributors_df = pd.read_csv('contributors.csv', sep=' - ', comment='#')
    contributors_df['last_name'] = [n.split(' ')[-1] for n in contributors_df['name']]
    contributors_df.sort_values(['order', 'last_name'], inplace=True)
    return contributors_df

contributors_df = make_contributors_df()

with app.app_context():
    update_flight_progress_stats(db.session)
    flight_progress_stats_updated = time.time()


@main_bp.route('/')
def landing_page():
    return render_template("landing.html")

@main_bp.route('/docs/start')
def docs_start_page():
    return render_template("docs/start.html")

@main_bp.route('/docs/citation')
def docs_citation_page():
    return render_template("docs/citation.html", contributors=contributors_df)

@main_bp.route('/docs/contact')
def docs_contact_page():
    return render_template("docs/contact.html")

@main_bp.route('/map/')
@main_bp.route('/map/<dataset>/')
def map_page(dataset='antarctica'):
    script, divs = components(all_flights_maps[dataset])
    
    return render_template("map.html",
                            bokeh_script=script, map=divs['map'], color_bar=divs['color_bar'],
                            tile_select=divs['tile_select'],
                            date_select=divs["date_select"], show_date_select=(dataset=='greenland'))

@main_bp.route('/flight/<int:flight_id>/')
@main_bp.route('/flight/<dataset>/<int:flight_id>/')
@main_bp.route('/flight/<dataset>/<int:flight_id>/<int:flight_date>')
def flight_page(flight_id, dataset='antarctica', flight_date=None):
    map_html, cbd_html, cbd_controls_html, map_controls_html = make_linked_flight_plots(db.session, current_user, flight_id,
                                                                    flight_lines=flight_lines[dataset], dataset=dataset,
                                                                    flight_date=flight_date)

    # Check what years we have the correspond to this flight ID
    fl = flight_lines[dataset]
    year_urls = [url_for('main_bp.flight_page', flight_id=flight_id, dataset=dataset, flight_date=None)]
    year_titles = ["(All years)"]
    for fl_ident in fl.keys():
        if fl_ident[0] == flight_id:
            year_lasttwo = fl_ident[1]
            if year_lasttwo is not None:
                year_urls.append(url_for('main_bp.flight_page', flight_id=flight_id, dataset=dataset, flight_date=year_lasttwo))
                year_titles.append(f"19{year_lasttwo}")

    # Check for a direct link to a specific segment to be loaded
    if 'id' in request.args:
        segment_id = int(request.args['id'])
    else:
        segment_id = None

    return render_template("flight.html", flight=flight_id, map=map_html, cbd_plot=cbd_html, cbd_controls=cbd_controls_html,
                            segment_id=segment_id, map_controls=map_controls_html,
                           show_view_toggle=True, enable_tiff=app.config['ENABLE_TIFF'],
                           links_to_years=list(zip(year_urls, year_titles)))

@main_bp.route('/query/action', methods=["POST"])
def query_bulk_action():
    t = time.time()
    qid = request.form['query_id']
    action_type = request.form['action_type']
    scope = request.form['scope']

    if not (has_write_permission(current_user) or (action_type == 'stitch')):
        return "You're not logged in or don't have the appropriate permissions."

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

    query = FilmSegment.query_visible_to_user(current_user).filter(FilmSegment.id.in_(query_ids))

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

        if ((query.count() > 10) or image_type != 'jpg') and not has_write_permission(current_user):
            return "Must be logged in with appropriate permissions to stitch more than 10 images."

        if query.count() > 10 and image_type != 'jpg':
            return "Sorry, merging more than 10 images into TIFF format is not yet supported due to the absurd size of the original TIFF images."

        query = query.order_by(FilmSegment.first_cbd)
        img_paths = [f.get_path(format=image_type) for f in query.all()]

        job = queue.enqueue(stitch_images, failure_ttl=60, args=(img_paths, image_type, flip, scale_x, scale_y, qid))
        return f"started:{job.get_id()}"
    elif action_type == 'download_metadata':
        query = query.order_by(FilmSegment.first_cbd)
        metadata_dict = {}
        for idx, seg in enumerate(query.all()):
            metadata_dict[idx] = seg.to_dict()
        job = queue.enqueue(worker_dummy_serve_metadata_dict, failure_ttl=60, args=(metadata_dict, qid))
        return f"started:{job.get_id()}"
    else:
        return "Unknown action type"

    print(f"Request type [{action_type}] took {time.time() - t} seconds to process")
    return "success"

@main_bp.route('/query/status/<job_id>')
def get_job_status(job_id):
    job = Job.fetch(job_id, connection=conn)

    if job.is_finished:
        return 'done'
    else:
        return 'running'

@main_bp.route('/outputs/<job_id>')
def get_output_image(job_id):
    job = Job.fetch(job_id, connection=conn)

    if job.is_finished:
        if job.result['job_type'] == 'stitch_images':
            img_io = job.result['image']

            return send_file(img_io, mimetype=f'image/{job.result["image_type"]}',
                            as_attachment=True, download_name=job.result['filename'])
        elif job.result['job_type'] == 'metadata_to_dict':
            return job.result['metadata']
        else:
            return f"Unknown job type {job.result['job_type']}", 202
    else:
        return "Job not complete", 202


@main_bp.route('/query')
def query_results():
    query, query_page, current_page, qid, n = query_results_from_database(request)

    # Pagination counts
    n_total_results = query.count()
    n_pages = math.ceil(n_total_results / n)

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
                           n_total_results=n_total_results, n_pages=n_pages, current_page=current_page, paginate=True,
                           next_page=next_page, prev_page=prev_page, page_map=pages, query_id=qid,
                           enable_tiff=app.config['ENABLE_TIFF'],
                           breadcrumbs=[('Explorer', '/'), ('Query Results', url_for('main_bp.query_results'))])


# List of results for set of film segments
@main_bp.route('/api/queryids', methods=["POST"])
def query_id_results():
    segment_ids = request.form.getlist('ids[]')
    query = FilmSegment.query_visible_to_user(current_user).filter(FilmSegment.id.in_(segment_ids))
    
    if request.form.get('sort'):
        if request.form.get('sort') == 'cbd':
            query = query.order_by(FilmSegment.first_cbd)
        elif request.form.get('sort') == 'frame':
            query = query.order_by(FilmSegment.first_frame)

    segs = query.all()

    # Record this query (temporarily)
    query_log = {'full_query': [x.id for x in segs],
                 'timestamp': time.time()}
    qid = str(uuid.uuid4())
    query_cache[qid] = query_log

    return render_template("queryresultslist.html", segments=segs, show_view_toggle=True, show_history=True,
                            n_total_results=len(segs), stitch_preview=(len(segs) <= 10),
                           query_id=qid, enable_tiff=app.config['ENABLE_TIFF'], paginate=False)

@main_bp.route('/update_form/<int:id>/')
def update_page(id):
    seg = FilmSegment.query_visible_to_user(current_user).filter(FilmSegment.id == id).first()
    return render_template("update.html", segment=seg, enable_tiff=app.config['ENABLE_TIFF'],
                           breadcrumbs=[('Explorer', '/')])


@main_bp.route('/stats/refresh/')
def stats_page_refresh():
    update_flight_progress_stats(db.session)
    return redirect(url_for("main_bp.stats_page"))

@main_bp.route('/stats/')
def stats_page():
    global flight_progress_stats_updated

    total_verified = FilmSegment.query_visible_to_user(current_user).filter(FilmSegment.is_verified == True).count()
    total = FilmSegment.query_visible_to_user(current_user).count()

    if current_user.is_authenticated:
        include_greenland = current_user.view_greenland
    else:
        include_greenland = False

    flightprogress_html = make_flight_progress_bar_plot(include_greenland=include_greenland)

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

@scheduler.task('interval', id='clear_main_query_cache', seconds=(60*60))
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
    if hasattr(g, 'start'):
        diff = time.time() - g.start
    else:
        diff = 0
    
    if ((response.response) and
        (200 <= response.status_code < 300) and
        (response.content_type.startswith('text/html'))):
        response.set_data(response.get_data().replace(
            b'__EXECUTION_TIME__', bytes(f"{diff:.3f}", 'utf-8')))
    return response