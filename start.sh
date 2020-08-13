#!/bin/bash
conda init bash
conda activate film

export FLASK_APP=wsgi.py
export FLASK_DEBUG=1
export APP_CONFIG_FILE=config.py

#python wsgi.py

pwd
echo $CONDA_PREFIX
ls
echo "directory explore_app/"
ls explore_app

gunicorn --bind localhost:$PORT wsgi:app