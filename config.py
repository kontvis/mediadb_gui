import os


class Config:
    """Application configuration with environment-based defaults."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///db.sqlite3"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_VISION_API_KEY = os.environ.get("GOOGLE_VISION_API_KEY")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    # Haiku 4.5: vision-capable, lowest-cost model on current Anthropic API.
    ANTHROPIC_MODEL = os.environ.get(
        "ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"
    )
