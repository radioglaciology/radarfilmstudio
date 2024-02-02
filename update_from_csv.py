import os
import pandas as pd
import numpy as np
from datetime import datetime
import argparse

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
        row_path = r['path']
        # If path ends in _lowqual.jpg, replace with .tiff
        if row_path.endswith("_lowqual.jpg"):
            row_path = row_path.replace("_lowqual.jpg", ".tiff")
            print(f"Replacing path with {row_path}")

        q = FilmSegment.query.filter(FilmSegment.path.contains(row_path))

        if q.count() == 0: # This path doesn't exist in the db yet
            if allow_add:
                f_split = os.path.basename(row_path)
                f_split = f_split.split('.')[0].split('_')
                seg = FilmSegment(path=path_prefix+row_path, dataset=dataset,
                                reel=f_split[0], first_frame=f_split[1], last_frame=f_split[2],
                                is_junk=False, is_verified=False, needs_review=False, scope_type=scope_type,
                                instrument_type=FilmSegment.UNKNOWN, notes="")
                print(f"Adding segment entry: {seg}")
                db.session.add(seg)
            else:
                raise(Exception(f"[MISSING] Could not find matching row for filename: {row_path}"))
        else:
            seg = q.first()

        if seg.dataset != dataset:
            print(seg)
            raise(Exception(f"Matched with path from a different dataset (processing dataset {dataset})"))
        
        if q.count() > 1:
            print(q)
            print(q.count())
            print(q.first())
            raise(Exception(f"Multiple matches for file {row_path}"))

        updated = False

        if seg.is_verified:
            print(f"Skipping already-verified segment: {seg}")
            continue

        for k in r.keys():
            if k in ['id', 'file', 'path', 'Filename', 'filename', 'Filenames', 'filenames']: # Allowed columns that should be ignored -- no update occurs
                continue # cannot be updated
            
            if pd.isna(r[k]) or (r[k] == ""):
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


# allow_add = False
# scope_type = None
# path_prefix = None

# #filename = "manual_import_data/20221205_nanna_fl10_1974.csv"
# #filename = "manual_import_data/20221206_1974fl5_filled.csv"
# #filename, allow_add, scope_type, path_prefix = "manual_import_data/20221206_1974fl6_filled.csv", True, "z", "DTU001/TIFF (2400x1800)/"
# #filename, allow_add, scope_type, path_prefix = "manual_import_data/20221207_1974fl11_filled.csv", True, "z", "DTU001/TIFF (2400x1800)/"
# #filename, allow_add, scope_type, path_prefix = "manual_import_data/20221208_1974fl8_filled.csv", True, "z", "DTU001/TIFF (2400x1800)/"


# df = pd.read_csv(filename, na_values=["-9999"], header=0, sep=None, engine="python")
# df = df.rename(columns={
#     'year': 'raw_date',
#     'flightline': 'flight',
#     'cbd_start': 'first_cbd',
#     'cbd_end': 'last_cbd',
#     'Filenames': 'file'
#     })

# df = df.drop(columns=['contains_two_flights', 'flipped_vert'])

# df['file'] = df['file'].apply((lambda x : x.replace("_lowqual.jpg", ".tiff")))
# update_from_df(df, dataset='greenland', updated_by_name=filename, allow_add=allow_add, scope_type=scope_type, path_prefix=path_prefix, dry_run=False)

if __name__ == "__main__":
    # Command-line arguments:
    # - path to CSV file
    # - allow_add (True/False) (defaults to False)
    # - scope_type (optional)
    # - dataset (optional)

    parser = argparse.ArgumentParser(description="Update database from CSV file")
    parser.add_argument('csv_file', type=str, help="Path to CSV file")
    parser.add_argument('dataset', type=str, help="Dataset to update")
    parser.add_argument('--allow_add', action="store_true", default=False, help="Allow adding new segments to the database")
    parser.add_argument('--scope_type', type=str, default=None, help="Scope type for new segments")
    parser.add_argument('--path_prefix', type=str, default="", help="Path prefix for new segments")
    parser.add_argument('--dry_run', action="store_true", default=False, help="Dry run (no changes committed)")
    args = parser.parse_args()

    df = pd.read_csv(args.csv_file, engine="python")

    # Check for required columns
    required_columns = ['path']
    if args.allow_add:
        required_columns.append('raw_date')
        required_columns.append('flight')
        required_columns.append('first_cbd')
        required_columns.append('last_cbd')
    
    for c in required_columns:
        if c not in df.columns:
            raise ValueError(f"Missing required column {c} in CSV file. Note: All required columns are {required_columns}")
    
    # Interpolate CBD values
    if 'first_cbd' in df.columns:
        df['first_cbd'] = df['first_cbd'].interpolate(method='linear')
    if 'last_cbd' in df.columns:
        df['last_cbd'] = df['last_cbd'].interpolate(method='linear')
    
    update_from_df(df, dataset=args.dataset, updated_by_name=os.path.basename(args.csv_file), allow_add=args.allow_add, scope_type=args.scope_type, path_prefix=args.path_prefix, dry_run=args.dry_run)
    
    

        