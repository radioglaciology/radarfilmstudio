import pandas as pd

from app import db, app
from app import FilmSegment

raise(Exception("Don't run this file unless you're re-creating the database."))

with app.app_context():
    db.create_all()

    df = pd.read_csv('../fixed8.csv', low_memory=False)
    df = df[df.complete == True]

    for idx, r in df.iterrows():
        fseg = FilmSegment(path=r['relpath'], reel=r['reel'], first_frame=r['first_frame'], last_frame=r['last_frame'],
                           first_cbd=r['first_cdb'], last_cbd=r['last_cdb'], flight=r['first_flight'],
                           is_junk=False, is_verified=False, needs_review=False,
                           scope_type=r['type'], instrument_type=FilmSegment.UNKNOWN)

        db.session.add(fseg)

    db.session.commit()