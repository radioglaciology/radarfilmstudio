export FLASK_APP=wsgi.py
export FLASK_DEBUG=1
export APP_CONFIG_FILE=config.py

#python wsgi.py

gunicorn wsgi:app