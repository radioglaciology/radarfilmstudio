import os
import pandas as pd
import numpy as np
from datetime import datetime

from explore_app import create_app

app = create_app()
app.app_context().push()

from explore_app import db, continuum
from explore_app.film_segment import FilmSegment
from explore_app.user import User


#raise(Exception("Be very careful about running this script"))

def update_from_df(df, dataset, updated_by_name, dry_run=True, allow_add=False, path_prefix=None, scope_type=None):
    update_count = 0

    if allow_add and ((scope_type is None) or (path_prefix is None)):
        raise ValueError("If adding segments is allowed, scope_type and path_prefix must be specified")

    for idx, r in df.iterrows():
        q = FilmSegment.query.filter(FilmSegment.path.contains(r['file']))

        if q.count() == 0: # This path doesn't exist in the db yet
            if allow_add:
                f_split = os.path.splitext(r['file'])[0]
                f_split = f_split.split('_')
                seg = FilmSegment(path=path_prefix+r['file'], dataset=dataset,
                                reel=f_split[0], first_frame=f_split[1], last_frame=f_split[2],
                                is_junk=False, is_verified=False, needs_review=False, scope_type=scope_type,
                                instrument_type=FilmSegment.UNKNOWN, notes="")
                print(f"Adding segment entry: {seg}")
                db.session.add(seg)
            else:
                raise(Exception(f"[MISSING] Could not find matching row for filename: {r['file']}"))
        else:
            seg = q.first()

        if seg.dataset != dataset:
            print(seg)
            raise(Exception(f"Matched with path from a different dataset (processing dataset {dataset})"))
        
        if q.count() > 1:
            print(q)
            print(q.count())
            print(q.first())
            raise(Exception(f"Multiple matches for file {r['file']}"))

        updated = False

        if seg.is_verified:
            print(f"Skipping already-verified segment: {seg}")
            continue

        for k in r.keys():
            if k in ['id', 'file', 'path']: # Allowed columns that should be ignored -- no update occurs
                continue # cannot be updated
            
            if np.isnan(r[k]):
                continue

            if hasattr(seg, k):
                if getattr(seg, k) != r[k]:
                    setattr(seg, k, r[k])
                    updated = True
            else:
                raise(Exception(f"[KEY ERROR] Could not find key {k} in database"))
        
        if updated:
            seg.updated_by = updated_by_name
            seg.last_changed = datetime.now()
            update_count = update_count + 1

    print(f"Updated {update_count} entries to dataset {dataset}")
    
    if dry_run:
        print(f"[DRY RUN] No changes actually made!")
        db.session.rollback()
    else:
        print(f"[COMMIT] Changes being committed...")
        db.session.commit()


allow_add = False
scope_type = None
path_prefix = None

#filename = "manual_import_data/20221205_nanna_fl10_1974.csv"
#filename = "manual_import_data/20221206_1974fl5_filled.csv"
#filename, allow_add, scope_type, path_prefix = "manual_import_data/20221206_1974fl6_filled.csv", True, "z", "DTU001/TIFF (2400x1800)/"
filename, allow_add, scope_type, path_prefix = "manual_import_data/20221207_1974fl11_filled.csv", True, "z", "DTU001/TIFF (2400x1800)/"


df = pd.read_csv(filename, na_values=["-9999"], header=0, sep=",", engine="python")
df = df.rename(columns={
    'year': 'raw_date',
    'flightline': 'flight',
    'cbd_start': 'first_cbd',
    'cbd_end': 'last_cbd',
    'Filenames': 'file'
    })

df = df.drop(columns=['contains_two_flights', 'flipped_vert'])

df['file'] = df['file'].apply((lambda x : x.replace("_lowqual.jpg", ".tiff")))
update_from_df(df, dataset='greenland', updated_by_name=filename, allow_add=allow_add, scope_type=scope_type, path_prefix=path_prefix, dry_run=False)

