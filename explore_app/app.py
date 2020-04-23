from threading import Thread

import os
from io import BytesIO
from PIL import Image
import numpy as np

from flask import Flask, render_template, url_for, request, send_from_directory, send_file, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_restful import Api, Resource, reqparse

from flask_images import Images
from flask_images import resized_img_src, resized_img_tag

from tornado.ioloop import IOLoop

from flask import current_app as app

import bokeh
from bokeh.plotting import figure
from bokeh.server.server import Server
from bokeh.embed import server_document

from . import map, flight_plots, film_segment
from map import make_bokeh_map, load_flight_lines
from flight_plots import make_cbd_plot

from film_segment import db, FilmSegment

import config

app = Flask(__name__)
app.config.from_object(config.Config)
db.init_app(app)

ma = Marshmallow(app)
api = Api(app)
images = Images(app)

# To play with the db in a REPL:
# > from app import db, app
# > from film_segment import FilmSegment
# > app.app_context().push()
# > db.session.query(FilmSegment).filter( ... bla ... ) # or whatever


class FilmSegmentSchema(ma.Schema):
    class Meta:
        fields = ("id", "path", "reel", "first_frame", "last_frame", "first_cbd", "last_cbd", "flight",
                  "is_junk", "is_verified", "needs_review", "scope_type", "instrument_type")


segment_schema = FilmSegmentSchema()


class FilmSegmentResource(Resource):
    def get(self, id):
        seg = FilmSegment.query.get_or_404(id)
        seg_dict = segment_schema.dump(seg)

        # Add next/prev by frame order
        prev_frame = min(seg_dict['first_frame'], seg_dict['last_frame']) - 1
        next_frame = max(seg_dict['first_frame'], seg_dict['last_frame']) + 1

        next_by_frame = FilmSegment.query.filter(
                (FilmSegment.first_frame >= next_frame) & (FilmSegment.last_frame >= next_frame) & (FilmSegment.reel == seg.reel)
            ).order_by(FilmSegment.first_frame.asc()).first()
        prev_by_frame = FilmSegment.query.filter(
                (FilmSegment.first_frame <= prev_frame) & (FilmSegment.last_frame <= prev_frame) & (FilmSegment.reel == seg.reel)
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
                        FilmSegment.flight == seg.flight)
        ).order_by(FilmSegment.first_cbd.asc()).first()
        prev_by_cbd = FilmSegment.query.filter(
            (FilmSegment.first_cbd <= prev_cbd) & (FilmSegment.last_cbd <= prev_cbd) & (
                        FilmSegment.flight == seg.flight)
        ).order_by(FilmSegment.first_cbd.desc()).first()

        if prev_by_cbd:
            seg_dict['prev_by_cbd'] = prev_by_cbd.id
        if next_by_cbd:
            seg_dict['next_by_cbd'] = next_by_cbd.id

        return seg_dict

    def post(self, id):
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

        db.session.commit()

        return segment_schema.dump(seg), 200


api.add_resource(FilmSegmentResource, '/api/segments/<int:id>')


## Resource pre-loading
flight_lines = load_flight_lines('../original_positioning/')


@app.route('/')
@app.route('/map/')
def map_page():
    map = make_bokeh_map(500,500, flight_lines=flight_lines)
    return render_template("map.html", map=map,
                           breadcrumbs=[('Explorer', '/'), ('Map', url_for('map_page'))])


@app.route('/flight/<int:flight_id>/')
def flight_page(flight_id):
    map = make_bokeh_map(300, 300, flight_id=flight_id, title="Flight Map", flight_lines=flight_lines)
    cbd_plot = make_cbd_plot(db.session, flight_id, 500, 300)
    return render_template("flight.html", flight=flight_id, map=map, cbd_plot=cbd_plot,
                           breadcrumbs=[('Explorer', '/'), (f'Flight {flight_id}', url_for('flight_page', flight_id=flight_id))])


@app.route('/update_form/<int:id>/')
def update_page(id):
    seg = FilmSegment.query.get(id)
    return render_template("update.html", segment=seg, breadcrumbs=[('Explorer', '/')])

def serve_pil_image(pil_img):
    img_io = BytesIO()
    pil_img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')

@app.route('/api/radargram/jpg/<int:id>')
@app.route('/api/radargram/jpg/<int:id>.jpg')
@app.route('/api/radargram/jpg/<int:id>/h/<int:max_height>')
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

@app.route('/api/radargram/tiff/<int:id>')
@app.route('/api/radargram/tiff/<int:id>.tiff')
def radargram_tiff(id):
    base_path = "/data3/schroeder/jemmons/35mm_output.2018-01-12"
    seg = FilmSegment.query.get(id)
    return send_from_directory(base_path, seg.path)

# if __name__ == '__main__':
#     #Thread(target=bk_worker).start()
#     app.run(debug=True, port=7879)
