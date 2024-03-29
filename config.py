"""Flask config class."""
import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

class Config:
    """
    Set Flask configuration vars and various other app-wide configuration.

    Note that some of these settings are deployment-location specific, so they're actually loaded from environment
    variables. The best place to configure these is in the .env file. The .env file should NOT be added to the git
    repo and should be independently maintained for each deployment.

    """

    # General Config
    TESTING = False
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    FLASK_APP = os.environ.get('FLASK_APP')
    SESSION_COOKIE_NAME = 'rg_explore_sess'
    INVITE_CODE = os.environ.get('INVITE_CODE')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://")

    CACHE_TYPE = 'null'
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
    COLOR_SKY = '#0098db'  # Sky (light blue)

    # Data locations
    ANTARCTICA_FLIGHT_POSITIONING_DIR = os.environ.get('ANTARCTICA_FLIGHT_POSITIONING_DIR')
    GREENLAND_FLIGHT_POSITIONING_DIR = os.environ.get('GREENLAND_FLIGHT_POSITIONING_DIR')
    ANTARCTICA_FILM_IMAGES_DIR = os.environ.get('ANTARCTICA_FILM_IMAGES_DIR')
    ANTARCTICA_FILM_IMAGES_TIFF_DIR = os.environ.get('ANTARCTICA_FILM_IMAGES_TIFF_DIR')
    GREENLAND_FILM_IMAGES_DIR = os.environ.get('GREENLAND_FILM_IMAGES_DIR')
    GREENLAND_FILM_IMAGES_TIFF_DIR = os.environ.get('GREENLAND_FILM_IMAGES_TIFF_DIR')
    TMP_OUTPUTS_DIR = os.environ.get('TMP_OUTPUTS_DIR')
    ENABLE_TIFF = os.environ.get('ENABLE_TIFF')

    # APScheduler
    SCHEDULER_API_ENABLED = True

    # Airbrake
    PYBRAKE = dict(
        project_id=os.environ.get('PYBRAKE_PROJECT_ID', None),
        project_key=os.environ.get('PYBRAKE_KEY', "")
    )

    # Talisman
    FORCE_HTTPS = (True if os.environ.get('FORCE_HTTPS', "1") == "1" else False)