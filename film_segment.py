from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

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
    needs_review = db.Column(db.Boolean)

    Z_SCOPE = 'z'
    A_SCOPE = 'a'
    scope_type = db.Column(db.CHAR)

    RADAR_60MHZ = 10
    RADAR_300MHZ = 20
    UNKNOWN = 0
    instrument_type = db.Column(db.Integer)

    def __repr__(self):
        return f'<FilmSegment {self.id}: Reel {self.reel} frames {self.first_frame} to {self.last_frame} [{self.path}]>'