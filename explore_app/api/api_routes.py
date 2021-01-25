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
from .. import db, ma, continuum, scheduler

from explore_app.film_segment import FilmSegment

api_bp = Blueprint('api_bp', __name__,
                   template_folder='templates',
                   static_folder='static')
seg_api = Api(api_bp)

# Database GET/POST

class FilmSegmentSchema(ma.Schema):
    class Meta:
        fields = ("id", "path", "reel", "first_frame", "last_frame", "first_cbd", "last_cbd", "flight",
                  "is_junk", "is_verified", "needs_review", "scope_type", "instrument_type", "notes",
                  "updated_by", "last_changed")


segment_schema = FilmSegmentSchema()

def has_write_permission(current_user):
    if not current_user.is_authenticated:
        return False

    return current_user.write_permission


def add_next_previous(seg_dict, seg):
    # Add next/prev by frame order
    prev_frame = min(seg_dict['first_frame'], seg_dict['last_frame']) - 1
    next_frame = max(seg_dict['first_frame'], seg_dict['last_frame']) + 1

    next_by_frame = FilmSegment.query.filter(
        (FilmSegment.first_frame >= next_frame) & (FilmSegment.last_frame >= next_frame) & (
                FilmSegment.reel == seg.reel) & (FilmSegment.scope_type == seg.scope_type)
    ).order_by(FilmSegment.first_frame.asc()).first()
    prev_by_frame = FilmSegment.query.filter(
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

    next_by_cbd = FilmSegment.query.filter(
        (FilmSegment.first_cbd >= next_cbd) & (FilmSegment.last_cbd >= next_cbd) & (
                FilmSegment.flight == seg.flight) & (FilmSegment.scope_type == seg.scope_type)
    ).order_by(FilmSegment.first_cbd.asc()).first()
    prev_by_cbd = FilmSegment.query.filter(
        (FilmSegment.first_cbd <= prev_cbd) & (FilmSegment.last_cbd <= prev_cbd) & (
                FilmSegment.flight == seg.flight) & (FilmSegment.scope_type == seg.scope_type)
    ).order_by(FilmSegment.first_cbd.desc()).first()

    if prev_by_cbd:
        seg_dict['prev_by_cbd'] = prev_by_cbd.id
    if next_by_cbd:
        seg_dict['next_by_cbd'] = next_by_cbd.id

class FilmSegmentResource(Resource):

    def get(self, id):
        seg = FilmSegment.query.get_or_404(id)
        seg_dict = segment_schema.dump(seg)
        add_next_previous(seg_dict, seg)
        return seg_dict

    def post(self, id):
        if not has_write_permission(current_user):
            return None, 401

        seg = FilmSegment.query.get_or_404(id)

        if not request.is_json: # only accept json formatted update requests
            return None, 400

        print("Scope type: ", request.json['scope_type'])
        print("Instrument type: ", request.json['instrument_type'])

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
    seg = FilmSegment.query.get_or_404(id)
    seg_dict = segment_schema.dump(seg.versions[version])
    add_next_previous(seg_dict, seg)
    return seg_dict

@api_bp.route('/api/segments/<int:id>/history')
def film_segment_history(id):
    if not has_write_permission(current_user):
        return None, 401

    seg = FilmSegment.query.get_or_404(id)

    print(count_versions(seg))
    history = []
    for version in range(count_versions(seg)):
        history.append(seg.versions[version].changeset)

    return {'history': history}


# Image Loading

def serve_pil_image(pil_img):
    img_io = BytesIO()
    pil_img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')

def serve_unmodified_image(filename):
    if "https://" in app.config['FILM_IMAGES_DIR']:
        return redirect(app.config['FILM_IMAGES_DIR'] + filename)
    else:
        send_from_directory(app.config['FILM_IMAGES_DIR'], filename)

def load_image(filename):
    if "https://" in app.config['FILM_IMAGES_DIR']:
        response = requests.get(app.config['FILM_IMAGES_DIR'] + filename)
        return Image.open(BytesIO(response.content))
    else:
        return Image.open(os.path.join(app.config['FILM_IMAGES_DIR'], filename))

@api_bp.route('/api/radargram/jpg/<int:id>')
@api_bp.route('/api/radargram/jpg/<int:id>.jpg')
@api_bp.route('/api/radargram/jpg/<int:id>/h/<int:max_height>')
@api_bp.route('/api/radargram/jpg/<int:id>/crop/first/<int:crop_w_start>')
@api_bp.route('/api/radargram/jpg/<int:id>/crop/last/<int:crop_w_end>')
def radargram_jpg(id, max_height = None, crop_w_start = None, crop_w_end = None):
    seg = FilmSegment.query.get(id)
    pre, ext = os.path.splitext(seg.path)
    filename = pre + "_lowqual.jpg"

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
    seg = FilmSegment.query.get(id)
    return serve_unmodified_image(seg.path)
