import os


class Config:
    """Application configuration. Reads values from environment with sensible defaults."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_VISION_API_KEY = os.environ.get('GOOGLE_VISION_API_KEY')
