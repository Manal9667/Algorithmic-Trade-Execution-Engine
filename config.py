"""
Central configuration. All secrets come from environment variables so
nothing sensitive is hard-coded or committed to source control.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
    PERSPECTIVE_API_KEY = os.environ.get("PERSPECTIVE_API_KEY", "")
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "policy_monitor.db")

    # How many videos to pull per keyword search (kept small for free-tier quota).
    MAX_VIDEOS_PER_SEARCH = 8
    # How many comments to pull per video.
    MAX_COMMENTS_PER_VIDEO = 15

    # Perspective API attributes we request, mapped to human-readable categories.
    PERSPECTIVE_ATTRIBUTES = {
        "SEVERE_TOXICITY": "Harassment",
        "IDENTITY_ATTACK": "Hate Speech",
        "THREAT": "Violence",
        "SEXUALLY_EXPLICIT": "Adult Content",
        "INSULT": "Harassment",
    }

    # Score (0-1) above which a Perspective attribute counts as flagged.
    PERSPECTIVE_THRESHOLD = 0.75
