import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'job_hunter.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

    # Model used for both agents. Override via env if you want a cheaper/faster model.
    HUNTER_MODEL = os.environ.get("HUNTER_MODEL", "claude-sonnet-5")
    APPLICATOR_MODEL = os.environ.get("APPLICATOR_MODEL", "claude-sonnet-5")

    # Business rules
    DAILY_JOB_CAP = int(os.environ.get("DAILY_JOB_CAP", "2"))
    # 24 = no cutoff (hour is always < 24, so the cutoff check never trips).
    # Set to e.g. 16 to restore a 4pm-local cutoff.
    SEARCH_CUTOFF_HOUR_LOCAL = int(os.environ.get("SEARCH_CUTOFF_HOUR_LOCAL", "24"))
    TIMEZONE = os.environ.get("APP_TIMEZONE", "Asia/Riyadh")

    # How often the background scheduler checks for new jobs, in minutes.
    SEARCH_INTERVAL_MINUTES = int(os.environ.get("SEARCH_INTERVAL_MINUTES", "60"))

    # Where generated PDFs are stored on disk.
    GENERATED_FILES_DIR = Path(
        os.environ.get("GENERATED_FILES_DIR", BASE_DIR / "instance" / "generated")
    )

    # Set to "1" to disable the background scheduler (useful for local dev / one-off runs).
    DISABLE_SCHEDULER = os.environ.get("DISABLE_SCHEDULER", "0") == "1"
