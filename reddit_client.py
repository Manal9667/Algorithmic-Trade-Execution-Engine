"""
Reddit client -- collects public posts matching a keyword via Reddit's
official API (OAuth "script" app, no user login flow needed).
"""
import os
import time
from datetime import datetime, timezone
import requests

CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "policy-monitor/1.0")

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
SEARCH_URL = "https://oauth.reddit.com/search"

_token_cache = {"access_token": None, "expires_at": 0}

MAX_RESULTS = 50


def _get_access_token():
    """Client-credentials OAuth flow, cached until near expiry."""
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError(
            "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set. Create a "
            "'script' app at https://www.reddit.com/prefs/apps to get these."
        )

    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["access_token"]

    resp = requests.post(
        TOKEN_URL,
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()

    _token_cache["access_token"] = payload["access_token"]
    _token_cache["expires_at"] = time.time() + payload.get("expires_in", 3600)
    return _token_cache["access_token"]


def collect_content_for_keyword(keyword, max_results=MAX_RESULTS, sort="new"):
    """
    Search public posts across all of Reddit for `keyword`.
    Raises on auth/HTTP errors so app.py's per-platform try/except can log
    and surface them without killing the whole search.
    """
    token = _get_access_token()
    headers = {
        "Authorization": f"bearer {token}",
        "User-Agent": USER_AGENT,
    }
    params = {
        "q": keyword,
        "sort": sort,
        "limit": min(max_results, 100),
        "type": "link",
    }

    resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=15)

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 5))
        time.sleep(min(retry_after, 30))
        resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=15)

    resp.raise_for_status()
    posts = resp.json().get("data", {}).get("children", [])

    items = []
    for post in posts:
        d = post.get("data", {})
        author = d.get("author", "unknown")
        title = d.get("title", "") or ""
        selftext = d.get("selftext", "") or ""
        text = f"{title}\n\n{selftext}".strip()
        created = d.get("created_utc")
        timestamp = (
            datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
            if created else ""
        )

        items.append({
            "platform": "Reddit",
            "account": f"u/{author}",
            "profile_url": f"https://reddit.com/user/{author}",
            "post_url": f"https://reddit.com{d.get('permalink', '')}",
            "text": text,
            "timestamp": timestamp,
        })

    return items