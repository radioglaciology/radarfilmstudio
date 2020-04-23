"""Flask config class."""
import os


class Config:
    """Set Flask configuration vars."""

    # General Config
    TESTING = True
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY')
    FLASK_APP = os.environ.get('FLASK_APP')
    SESSION_COOKIE_NAME = 'rg_explore_sess'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///explore.db'

    FLIGHT_POSITIONING_DIR = '../original_positioning/'

    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 30