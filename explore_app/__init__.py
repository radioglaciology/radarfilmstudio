from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_restful import Api
from flask_images import Images
from flask_caching import Cache
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_continuum import Continuum
from flask_migrate import Migrate
from flask_apscheduler import APScheduler

import os

# Globally accessible plugins
db = SQLAlchemy()
migrate = Migrate()
continuum = Continuum(db=db, migrate=migrate)
ma = Marshmallow()
seg_api = Api()
images = Images()
cache = Cache()
login_manager = LoginManager()
csrf = CSRFProtect()
scheduler = APScheduler()


def create_app():
    """ Initialize the explore application """
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.Config')

    from .film_segment import FilmSegment
    from .user import User

    # Initialize plugins
    db.init_app(app)
    migrate.init_app(app, db)
    continuum.init_app(app)
    ma.init_app(app)
    images.init_app(app)
    cache.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    scheduler.init_app(app)
    scheduler.start()

    with app.app_context():
        from explore_app.main import main_routes
        from explore_app.auth import auth_routes
        from explore_app.api import api_routes
        from explore_app.api.api_routes import FilmSegmentResource

        app.register_blueprint(main_routes.main_bp)
        app.register_blueprint(auth_routes.auth_bp)
        app.register_blueprint(api_routes.api_bp)

        return app
