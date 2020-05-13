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
    CACHE_DEFAULT_TIMEOUT = 300

    # Stanford brand identity colors
    COLOR_PRIMARY = '#8c1515'  # Cardinal red
    COLOR_ACCENT = '#b1040e'  # Bright red
    COLOR_BACKGROUND = '#ffffff'  # White
    COLOR_GREY = '#4d4f53'  # Cool grey
    COLOR_GRAY = COLOR_GREY  # I hate spelling
    COLOR_BLACK = '#2e2d29'  # Black (but not actually)
    COLOR_PALO_ALTO = '#175e54'  # I'm not making this up... https://identity.stanford.edu/color.html#digital-color
    COLOR_REDWOOD = '#8d3c1e'  # Redwood
    COLOR_PURPLE = '#53284f'  # Purple