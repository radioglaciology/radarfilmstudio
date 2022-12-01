import time

def worker_dummy_serve_metadata_dict(metadata_dict, qid):
    return {
        'job_type': 'metadata_to_dict',
        'metadata': metadata_dict,
        'timestamp': time.time()
    }