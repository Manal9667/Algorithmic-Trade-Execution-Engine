"""
Instagram client.

Instagram's Graph API has no free-text keyword search. The closest thing
available to a normal app is hashtag search: max 30 unique hashtags per
7-day rolling window, and it only finds media tagged with "#word", not
captions that merely contain the word. No search by account name/bio.
For anything broader, Meta's Content Library API (research-partner
program) is the only real path.

Env vars:
    INSTAGRAM_ACCESS_TOKEN     - long-lived token for the IG Business account
    IG_BUSINESS_ACCOUNT_ID     - the querying account's IG user ID
"""
import os
import re
import requests

ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
IG_BUSINESS_ACCOUNT_ID = os.environ.get("IG_BUSINESS_ACCOUNT_ID")
GRAPH_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

MAX_MEDIA = 50


def _clean_hashtag(keyword):
    return re.sub(r"[^A-Za-z0-9_]", "", keyword)


def collect_content_for_keyword(keyword, max_media=MAX_MEDIA):
    """
    Look up recent public media tagged with `keyword` (as a hashtag).
    Raises on auth/HTTP errors so app.py's per-platform try/except can log
    and surface them without killing the whole search.
    """
    if not ACCESS_TOKEN or not IG_BUSINESS_ACCOUNT_ID:
        raise RuntimeError(
            "INSTAGRAM_ACCESS_TOKEN / IG_BUSINESS_ACCOUNT_ID not set. "
            "Requires an Instagram Business/Creator account linked to a "
            "Meta app with the instagram_basic and instagram_manage_insights "
            "permissions."
        )

    tag = _clean_hashtag(keyword)
    if not tag:
        return []

    lookup_resp = requests.get(
        f"{BASE_URL}/ig_hashtag_search",
        params={"user_id": IG_BUSINESS_ACCOUNT_ID, "q": tag, "access_token": ACCESS_TOKEN},
        timeout=15,
    )
    lookup_resp.raise_for_status()
    hashtag_data = lookup_resp.json().get("data", [])
    if not hashtag_data:
        return []
    hashtag_id = hashtag_data[0]["id"]

    media_resp = requests.get(
        f"{BASE_URL}/{hashtag_id}/recent_media",
        params={
            "user_id": IG_BUSINESS_ACCOUNT_ID,
            "fields": "id,caption,permalink,timestamp,username",
            "limit": min(max_media, 50),
            "access_token": ACCESS_TOKEN,
        },
        timeout=15,
    )
    media_resp.raise_for_status()
    media_items = media_resp.json().get("data", [])

    items = []
    for m in media_items:
        username = m.get("username", "unknown")
        items.append({
            "platform": "Instagram",
            "account": f"@{username}",
            "profile_url": f"https://instagram.com/{username}",
            "post_url": m.get("permalink", ""),
            "text": m.get("caption", "") or "",
            "timestamp": m.get("timestamp", ""),
        })

    return items