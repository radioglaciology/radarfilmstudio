import os

from flask import current_app as app

from flask_sqlalchemy import SQLAlchemy

from sqlalchemy_continuum.plugins import FlaskPlugin
from sqlalchemy_continuum import make_versioned

from . import db

from explore_app.user import User

make_versioned(plugins=[FlaskPlugin()])

class FilmSegment(db.Model):
    __versioned__ = {}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    dataset = db.Column(db.String(100))

    path = db.Column(db.String(300), unique=True)
    reel = db.Column(db.String(100))
    first_frame = db.Column(db.Integer)
    last_frame = db.Column(db.Integer)

    first_cbd = db.Column(db.Integer)
    last_cbd = db.Column(db.Integer)
    flight = db.Column(db.Integer)

    # Extra fields read in their raw number formats - possible to be processed into more useful versions later
    raw_date = db.Column(db.Integer, nullable=True)
    raw_time = db.Column(db.Integer, nullable=True)
    raw_mode = db.Column(db.Integer, nullable=True)

    is_junk = db.Column(db.Boolean)
    is_verified = db.Column(db.Boolean)
    needs_review = db.Column(db.Boolean)

    Z_SCOPE = 'z'
    A_SCOPE = 'a'
    ESM_SCOPE = 'esm'
    scope_type = db.Column(db.String(100))

    RADAR_60MHZ = 10
    RADAR_300MHZ = 20
    UNKNOWN = 0
    instrument_type = db.Column(db.Integer)

    notes = db.Column(db.String)

    updated_by = db.Column(db.String)
    last_changed = db.Column(db.DateTime)

    def get_year(self):
        if self.raw_date is None:
            return None
        else:
            return self.raw_date % 100 # last two digits _should be_ the year

    def query_visible_to_user(user, session=None):
        if session is not None:
            q = session.query(FilmSegment) # Allow a specific session to be provided
        else:
            q = FilmSegment.query
        
        return q

    def get_path(self, format='jpg'):
        """
        Mapping from "path" column of database to a URL where we can actually locate the data.
        """
        p = ''
        if self.dataset == 'greenland':
            if format == 'jpg':
                p = f"{app.config['GREENLAND_FILM_IMAGES_DIR']}{self.path}"
            elif format == 'tiff':
                p = f"{app.config['GREENLAND_FILM_IMAGES_TIFF_DIR']}{self.path}"
            else:
                return None
            print(p)
        else:
            if format == 'jpg':
                p = f"{app.config['ANTARCTICA_FILM_IMAGES_DIR']}{self.path}"
            elif format == 'tiff':
                p = f"{app.config['ANTARCTICA_FILM_IMAGES_TIFF_DIR']}{self.path}"
            else:
                return None

        if format == 'jpg':    
            pre, ext = os.path.splitext(p)
            return pre + "_lowqual.jpg"
        else:
            return p

    def to_dict(self):
        res = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        res['url_jpg'] = self.get_path(format='jpg')
        res['url_tiff'] = self.get_path(format='tiff')
        return res

    def __repr__(self):
        return f'<FilmSegment {self.id} [{self.dataset}]: Reel {self.reel} frames {self.first_frame} to {self.last_frame} [{self.path}]>'