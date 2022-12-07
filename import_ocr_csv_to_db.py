import pandas as pd
import numpy as np
from datetime import datetime

from explore_app import create_app

app = create_app()
app.app_context().push()

from explore_app import db, continuum
from explore_app.film_segment import FilmSegment
from explore_app.user import User


raise(Exception("Don't run this file unless you're re-creating the database or adding a new set of data."))

def add_from_csv(input_file_path, updated_by_name, dataset, update_mode=True):

    add_count = 0
    update_count = 0

    df = pd.read_csv(input_file_path, low_memory=False)
    df = df[df.complete == True]

    for idx, r in df.iterrows():
        q = FilmSegment.query.filter(FilmSegment.path == r['relpath'])
        if q.count() == 0: # This path doesn't exist in the db yet
            add_count = add_count + 1
            seg = FilmSegment(path=r['relpath'], dataset=dataset,
                                is_junk=False, is_verified=False, needs_review=False,
                                instrument_type=FilmSegment.UNKNOWN, notes="")
            db.session.add(seg)
        else:
            seg = q.first()

            if seg.dataset != dataset:
                print(seg)
                raise(Exception(f"Matched with path from a different dataset (processing dataset {dataset})"))
            
            if q.count() > 1:
                print(q)
                print(q.count())
                print(q.first())
                raise(Exception(f"Multiple matches for path {r['relpath']}"))

        updated = False

        if seg.reel is None:
            seg.reel = r['reel']
            updated = True
        if seg.first_frame is None and (not np.isnan(r['first_frame'])):
            seg.first_frame = r['first_frame']
            updated = True
        if seg.last_frame is None and (not np.isnan(r['last_frame'])):
            seg.last_frame = r['last_frame']
            updated = True
        if seg.first_cbd is None and (not np.isnan(r['first_cdb'])):
            seg.first_cbd = r['first_cdb']
            updated = True
        if seg.last_cbd is None and (not np.isnan(r['last_cdb'])):
            seg.last_cbd = r['last_cdb']
            updated = True
        if seg.flight is None and (not np.isnan(r['first_flight'])):
            seg.flight = r['first_flight']
            updated = True
        if seg.raw_date is None and (not np.isnan(r['first_date'])):
            seg.raw_date = r['first_date']
            updated = True
        if seg.raw_time is None and (not np.isnan(r['first_time'])):
            seg.raw_time = r['first_time']
            updated = True
        if seg.raw_mode is None and (not np.isnan(r['first_mode'])):
            seg.raw_mode = r['first_mode']
            updated = True
        if seg.scope_type is None:
            seg.scope_type = r['type']
            updated = True
    
        if updated:
            seg.updated_by = updated_by_name
            seg.last_changed = datetime.now()
            update_count = update_count + 1

    db.session.commit()

    print(f"Added {add_count} and updated {update_count} to dataset {dataset} from {input_file_path}")

    return add_count, update_count


add_from_csv('../fixed8.csv', 'fixed8.csv', 'antarctica', update_mode=True)
add_from_csv('../greenland_csvs/dtu-part1-20201011.csv', 'dtu-part2-20201011.csv', 'greenland', update_mode=True)
add_from_csv('../greenland_csvs/dtu-part2-20201115.csv', 'dtu-part2-20201115.csv', 'greenland', update_mode=True)