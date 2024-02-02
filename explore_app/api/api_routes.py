import os
from io import BytesIO
from PIL import Image
from datetime import datetime
import requests
import time
import uuid

from flask import Blueprint, request, send_file, send_from_directory, redirect, render_template
from flask_restful import Api, Resource
from flask_login import current_user
from sqlalchemy_continuum.utils import count_versions

from flask import current_app as app
from .. import db, ma, scheduler

from ..main.map import load_flight_lines

from explore_app.film_segment import FilmSegment

api_bp = Blueprint('api_bp', __name__,
                   template_folder='templates',
                   static_folder='static')
seg_api = Api(api_bp)

flight_lines = {
    'antarctica': load_flight_lines(app.config['ANTARCTICA_FLIGHT_POSITIONING_DIR'], 'antarctica'),
    'greenland': load_flight_lines(app.config['GREENLAND_FLIGHT_POSITIONING_DIR'], 'greenland')
}

query_cache = {}
images_cache = {}

# Database GET/POST

class FilmSegmentSchema(ma.Schema):
    class Meta:
        fields = ("id", "path", "reel", "first_frame", "last_frame", "first_cbd", "last_cbd", "flight",
                  "is_junk", "is_verified", "needs_review", "scope_type", "instrument_type", "notes",
                  "updated_by", "last_changed", "raw_date", "dataset")


segment_schema = FilmSegmentSchema()
segments_schema = FilmSegmentSchema(many=True)

def has_write_permission(current_user):
    if not current_user.is_authenticated:
        return False

    return current_user.write_permission


def add_next_previous(seg_dict, seg):
    # Add next/prev by frame order
    prev_frame = min(seg_dict['first_frame'], seg_dict['last_frame']) - 1
    next_frame = max(seg_dict['first_frame'], seg_dict['last_frame']) + 1

    next_by_frame = FilmSegment.query_visible_to_user(current_user).filter(
        (FilmSegment.first_frame >= next_frame) & (FilmSegment.last_frame >= next_frame) & (
                FilmSegment.reel == seg.reel) & (FilmSegment.scope_type == seg.scope_type)
    ).order_by(FilmSegment.first_frame.asc()).first()
    prev_by_frame = FilmSegment.query_visible_to_user(current_user).filter(
        (FilmSegment.first_frame <= prev_frame) & (FilmSegment.last_frame <= prev_frame) & (
                FilmSegment.reel == seg.reel) & (FilmSegment.scope_type == seg.scope_type)
    ).order_by(FilmSegment.first_frame.desc()).first()

    if prev_by_frame:
        seg_dict['prev_by_frame'] = prev_by_frame.id
    if next_by_frame:
        seg_dict['next_by_frame'] = next_by_frame.id

    # Add next/prev by CBD order
    prev_cbd = min(seg_dict['first_cbd'], seg_dict['last_cbd']) - 1
    next_cbd = max(seg_dict['first_cbd'], seg_dict['last_cbd']) + 1

    next_by_cbd = FilmSegment.query_visible_to_user(current_user).filter(
        (FilmSegment.first_cbd >= next_cbd) & (FilmSegment.last_cbd >= next_cbd) & (
                FilmSegment.flight == seg.flight) & (FilmSegment.scope_type == seg.scope_type)
    ).order_by(FilmSegment.first_cbd.asc()).first()
    prev_by_cbd = FilmSegment.query_visible_to_user(current_user).filter(
        (FilmSegment.first_cbd <= prev_cbd) & (FilmSegment.last_cbd <= prev_cbd) & (
                FilmSegment.flight == seg.flight) & (FilmSegment.scope_type == seg.scope_type)
    ).order_by(FilmSegment.first_cbd.desc()).first()

    if prev_by_cbd:
        seg_dict['prev_by_cbd'] = prev_by_cbd.id
    if next_by_cbd:
        seg_dict['next_by_cbd'] = next_by_cbd.id

class FilmSegmentResource(Resource):

    def get(self, id):
        seg = FilmSegment.query_visible_to_user(current_user).filter(FilmSegment.id == id).first_or_404(id)
        seg_dict = segment_schema.dump(seg)
        add_next_previous(seg_dict, seg)
        return seg_dict

    def post(self, id):
        if not has_write_permission(current_user):
            return None, 401

        seg = FilmSegment.query_visible_to_user(current_user).filter(FilmSegment.id == id).first_or_404(id)

        if not request.is_json: # only accept json formatted update requests
            return None, 400

        if 'flight' in request.json:
            seg.flight = request.json['flight']
        if 'first_cbd' in request.json:
            seg.first_cbd = request.json['first_cbd']
        if 'last_cbd' in request.json:
            seg.last_cbd = request.json['last_cbd']
        if 'scope_type' in request.json:
            seg.scope_type = request.json['scope_type']
        if 'instrument_type' in request.json:
            seg.instrument_type = request.json['instrument_type']
        if 'notes' in request.json:
            seg.notes = request.json['notes']
        
        if 'raw_date' in request.json:
            if request.json['raw_date'] == '':
                seg.raw_date = None
            else:
                seg.raw_date = request.json['raw_date']

        if 'is_junk' in request.json:
            seg.is_junk = (request.json['is_junk'] == "junk")
        if 'is_verified' in request.json:
            seg.is_verified = (request.json['is_verified'] == "verified")
        if 'needs_review' in request.json:
            seg.needs_review = (request.json['needs_review'] == "review")

        seg.updated_by = current_user.email
        seg.last_changed = datetime.now()

        db.session.commit()

        return segment_schema.dump(seg), 200

seg_api.add_resource(FilmSegmentResource, '/api/segments/<int:id>')

@api_bp.route('/api/segments/<int:id>/version/<int:version>')
def film_segment_version(id, version):
    seg = FilmSegment.query_visible_to_user(current_user).filter(FilmSegment.id == id).first_or_404(id)
    seg_dict = segment_schema.dump(seg.versions[version])
    add_next_previous(seg_dict, seg)
    return seg_dict

@api_bp.route('/api/segments/<int:id>/history')
def film_segment_history(id):
    if not has_write_permission(current_user):
        return None, 401

    seg = FilmSegment.query_visible_to_user(current_user).filter(FilmSegment.id == id).first_or_404(id)

    history = []
    for version in range(count_versions(seg)):
        history.append(seg.versions[version].changeset)

    return {'history': history}

# Positioning data

# @api_bp.route('/api/positioning/<dataset>/<int:flight_id>', methods=['GET'])
# @api_bp.route('/api/positioning/<dataset>/<int:flight_id>/<int:flight_date>', methods=['GET'])
# def positioning_data(dataset, flight_id, flight_date=None):
#     if not (dataset in flight_lines):
#         return "Unknown dataset"
    
#     first_cbd = request.args.get("first_cbd", default=None)
#     last_cbd = request.args.get("last_cbd", default=None)

#     if flight_date is None:
#         flight_ident = (flight_id, None)
#     else:
#         flight_ident = (flight_id, flight_date % 100)

#     if not (flight_ident in flight_lines[dataset]):
#         return ""

# Image Loading

def serve_pil_image(pil_img):
    img_io = BytesIO()
    pil_img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')

def serve_unmodified_image(p):
    if "https://" in p:
        return redirect(p)
    else:
        send_from_directory(p)

def load_image(p):
    if "https://" in p:
        response = requests.get(p)
        return Image.open(BytesIO(response.content))
    else:
        return Image.open(p)

@api_bp.route('/api/radargram/jpg/<int:id>')
@api_bp.route('/api/radargram/jpg/<int:id>.jpg')
@api_bp.route('/api/radargram/jpg/<int:id>/h/<int:max_height>')
@api_bp.route('/api/radargram/jpg/<int:id>/crop/first/<int:crop_w_start>')
@api_bp.route('/api/radargram/jpg/<int:id>/crop/last/<int:crop_w_end>')
def radargram_jpg(id, max_height = None, crop_w_start = None, crop_w_end = None):
    seg = FilmSegment.query_visible_to_user(current_user).filter(FilmSegment.id == id).first()
    filename = seg.get_path(format='jpg')

    if max_height:
        im = load_image(filename)
        if max_height >= im.height:
            return serve_unmodified_image(filename)
        else:
            scale = max_height / im.height
            return serve_pil_image(im.resize((int(im.width*scale), int(im.height*scale))))
    elif crop_w_start:
        im = load_image(filename)
        return serve_pil_image(im.crop(box=(0, 0, crop_w_start, im.size[1])))
    elif crop_w_end:
        im = load_image(filename)
        return serve_pil_image(im.crop(box=(im.size[0]-crop_w_end, 0, im.size[0], im.size[1])))
    else:
        return serve_unmodified_image(filename)

@api_bp.route('/api/radargram/tiff/<int:id>')
@api_bp.route('/api/radargram/tiff/<int:id>.tiff')
def radargram_tiff(id):
    seg = FilmSegment.query_visible_to_user(current_user).filter(FilmSegment.id == id).first()
    return serve_unmodified_image(seg.get_path(format='tiff'))


def query_results_from_database(request):
    query = FilmSegment.query_visible_to_user(current_user)

    # Filters

    if request.args.get('flight'):
        query = query.filter(FilmSegment.flight == int(request.args.get('flight')))

    if request.args.get('reel'):
        query = query.filter(FilmSegment.reel == request.args.get('reel'))

    if request.args.get('verified'):
        if int(request.args.get('verified')) == 0:
            query = query.filter(FilmSegment.is_verified == False)
        elif int(request.args.get('verified')) == 1:
            query = query.filter(FilmSegment.is_verified == True)

    if request.args.get('scope'):
        query = query.filter(FilmSegment.scope_type == request.args.get('scope'))

    if request.args.get('dataset'):
        query = query.filter(FilmSegment.dataset == request.args.get('dataset'))

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

    return query, query_page, current_page, qid, n

""" The API version of the query path, which returns a JSON-formatted list of segment IDs or the actual segment metadata """
@api_bp.route('/api/query')
def query_json_results():
    query, _, _, qid, n = query_results_from_database(request)
    if request.args.get('ids_only'):
        segment_ids = [seg.id for seg in query.all()]
        return {'ids': segment_ids}
    else:
        #segments = [segment_schema.dump(seg) for seg in query.all()]
        return {'segments': segments_schema.dump(query.all())}

@api_bp.route('/api/test')
def api_test_page():
    return "1"