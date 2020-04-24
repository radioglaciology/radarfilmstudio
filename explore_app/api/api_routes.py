import os
from io import BytesIO
from PIL import Image
from datetime import datetime

from flask import Blueprint, request, send_file, send_from_directory
from flask_restful import Api, Resource
from flask_login import current_user
from sqlalchemy_continuum.utils import count_versions

from flask import current_app as app
from .. import db, ma, continuum

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
    #if not has_write_permission(current_user):
    #    return None, 401

    seg = FilmSegment.query.get_or_404(id)

    print(count_versions(seg))
    history = []
    for version in range(count_versions(seg)-1,-1,-1):
        history.append(seg.versions[version].changeset)

    return {'history': history}


# Image Loading

def serve_pil_image(pil_img):
    img_io = BytesIO()
    pil_img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')

@api_bp.route('/api/radargram/jpg/<int:id>')
@api_bp.route('/api/radargram/jpg/<int:id>.jpg')
@api_bp.route('/api/radargram/jpg/<int:id>/h/<int:max_height>')
def radargram_jpg(id, max_height = None):
    base_path = "/data3/schroeder/jemmons/35mm_output.2018-01-12"

    seg = FilmSegment.query.get(id)
    pre, ext = os.path.splitext(seg.path)
    filename = pre + ".jpg"

    if max_height:
        im = Image.open(os.path.join(base_path, filename))
        if max_height >= im.height:
            return send_from_directory(base_path,
                                       filename)
        else:
            scale = max_height / im.height
            return serve_pil_image(im.resize((int(im.width*scale), int(im.height*scale))))
    else:
        return send_from_directory(base_path,
                                    filename)

@api_bp.route('/api/radargram/tiff/<int:id>')
@api_bp.route('/api/radargram/tiff/<int:id>.tiff')
def radargram_tiff(id):
    base_path = "/data3/schroeder/jemmons/35mm_output.2018-01-12"
    seg = FilmSegment.query.get(id)
    return send_from_directory(base_path, seg.path)