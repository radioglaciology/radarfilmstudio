from flask import Flask

import pybrake.middleware.flask
import logging

from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_restful import Api
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
from flask_talisman import Talisman

from rq import Queue
from rq.job import Job
from worker import conn

import os

# Globally accessible plugins
db = SQLAlchemy()
migrate = Migrate(compare_type=True)
ma = Marshmallow()
seg_api = Api()
login_manager = LoginManager()
csrf = CSRFProtect()
scheduler = APScheduler()
queue = Queue(connection=conn)
talisman = Talisman()


def create_app():
    """ Initialize the explore application """
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.Config')
    app = pybrake.middleware.flask.init_app(app)

    if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
        print("Detected gunicorn. Setting up logging...")
        gunicorn_logger = logging.getLogger('gunicorn.error')
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)

    from .film_segment import FilmSegment
    from .user import User

    # Initialize plugins
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    scheduler.init_app(app)
    scheduler.start()

    talisman.init_app(app, content_security_policy=[], force_https=app.config['FORCE_HTTPS'])

    with app.app_context():
        from explore_app.main import main_routes
        from explore_app.auth import auth_routes
        from explore_app.api import api_routes
        from explore_app.api.api_routes import FilmSegmentResource

        app.register_blueprint(main_routes.main_bp)
        app.register_blueprint(auth_routes.auth_bp)
        app.register_blueprint(api_routes.api_bp)

        return app
