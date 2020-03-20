from threading import Thread

from flask import Flask, render_template, url_for
from flask_sqlalchemy import SQLAlchemy

from tornado.ioloop import IOLoop

import bokeh
from bokeh.plotting import figure
from bokeh.server.server import Server
from bokeh.embed import server_document

from map import bokeh_map


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///explore.db'
db = SQLAlchemy(app)


class FilmSegment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    path = db.Column(db.String(300), unique=True)
    reel = db.Column(db.Integer)
    first_frame = db.Column(db.Integer)
    last_frame = db.Column(db.Integer)

    first_cbd = db.Column(db.Integer)
    last_cbd = db.Column(db.Integer)
    flight = db.Column(db.Integer)

    is_junk = db.Column(db.Boolean)
    is_verified = db.Column(db.Boolean)

    def __repr__(self):
        return f'<FilmSegment {self.id}: Reel {self.reel} frames {self.first_frame} to {self.last_frame} [{self.path}]>'


@app.route('/')
@app.route('/map/')
def map_page():
    script = server_document('http://localhost:5006/map')
    return render_template("map.html", script=script,
                           breadcrumbs=[('Explorer', '/'), ('Map', url_for('map_page'))])


@app.route('/flight/<int:flight_id>/')
def flight_page(flight_id):
    return render_template("flight.html", flight=flight_id,
                           breadcrumbs=[('Explorer', '/'), (f'Flight {flight_id}', url_for('flight_page', flight_id=flight_id))])



def bk_worker():
    # Can't pass num_procs > 1 in this configuration. If you need to run multiple
    # processes, see e.g. flask_gunicorn_embed.py
    server = Server({'/map': bokeh_map}, io_loop=IOLoop(), allow_websocket_origin=["*"]) # localhost:8000
    server.start()
    server.io_loop.start()


if __name__ == '__main__':
    Thread(target=bk_worker).start()
    app.run(debug=True)
