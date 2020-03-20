import pandas as pd

from app import db
from app import FilmSegment

raise(Exception("Don't run this file unless you're re-creating the database."))

df = pd.read_csv('../fixed8.csv', low_memory=False)
df = df[df.complete == True]

for idx, r in df.iterrows():
    fseg = FilmSegment(path=r['relpath'], reel=r['reel'], first_frame=r['first_frame'], last_frame=r['last_frame'],
                       first_cbd=r['first_cdb'], last_cbd=r['last_cdb'], flight=r['first_flight'],
                       is_junk=False, is_verified=False)

    db.session.add(fseg)

db.session.commit()