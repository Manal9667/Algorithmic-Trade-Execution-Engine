"""
YouTube client -- collects public videos matching a keyword via the
official YouTube Data API v3.
 
Env vars:
    YOUTUBE_API_KEY - API key from Google Cloud Console with "YouTube Data
                       API v3" enabled. Free tier: 10,000 quota units/day;
                       a search.list call costs 100 units.
"""
import os
import re
import requests
 
API_KEY = os.environ.get("YOUTUBE_API_KEY")
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
COMMENT_THREADS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
 
MAX_RESULTS = 25
MAX_COMMENTS = 50
 
_VIDEO_ID_PATTERN = re.compile(
    r"(?:v=|\/shorts\/|\/embed\/|\/v\/|youtu\.be\/)([a-zA-Z0-9_-]{11})"
)
 
 
def collect_content_for_keyword(keyword, max_results=MAX_RESULTS):
    """
    Search public videos for `keyword` and return normalized items.
    Raises on auth/HTTP errors so app.py's per-platform try/except can log
    and surface them without killing the whole search.
    """
    if not API_KEY:
        raise RuntimeError(
            "YOUTUBE_API_KEY is not set. Create one in Google Cloud Console "
            "with the YouTube Data API v3 enabled."
        )
 
    search_resp = requests.get(
        SEARCH_URL,
        params={
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "maxResults": min(max_results, 50),
            "order": "date",
            "key": API_KEY,
        },
        timeout=15,
    )
    search_resp.raise_for_status()
    search_items = search_resp.json().get("items", [])
 
    video_ids = [
        item["id"]["videoId"] for item in search_items
        if item.get("id", {}).get("videoId")
    ]
    if not video_ids:
        return []
 
    # search.list truncates descriptions -- batch-fetch full snippets.
    details_resp = requests.get(
        VIDEOS_URL,
        params={"part": "snippet", "id": ",".join(video_ids), "key": API_KEY},
        timeout=15,
    )
    details_resp.raise_for_status()
    details_items = {
        item["id"]: item["snippet"] for item in details_resp.json().get("items", [])
    }
 
    items = []
    for video_id, snippet in details_items.items():
        channel_title = snippet.get("channelTitle", "unknown")
        channel_id = snippet.get("channelId", "")
 
        items.append({
            "platform": "YouTube",
            "account": channel_title,
            "profile_url": f"https://youtube.com/channel/{channel_id}" if channel_id else "",
            "post_url": f"https://youtube.com/watch?v={video_id}",
            "text": f"{snippet.get('title', '')}\n\n{snippet.get('description', '')}",
            "timestamp": snippet.get("publishedAt", ""),
        })
 
    return items
 
 
def extract_video_id(url):
    """
    Pulls the 11-character video ID out of any common YouTube URL shape:
    watch?v=, youtu.be/, /shorts/, /embed/, /v/. Returns None if no match.
    """
    match = _VIDEO_ID_PATTERN.search(url or "")
    return match.group(1) if match else None
 
 
def get_video_comments(video_id, max_results=MAX_COMMENTS):
    """
    Fetch top-level comments for a single video via commentThreads.list.
    Each comment's author is treated as the "account" being evaluated --
    this is the actual person who wrote the text being classified, unlike
    keyword search where the flagged account was the video's channel owner.
 
    Raises on auth/HTTP errors so the caller's try/except can log and
    surface them. Comments-disabled videos raise a clearer message than
    the raw API error.
    """
    if not API_KEY:
        raise RuntimeError(
            "YOUTUBE_API_KEY is not set. Create one in Google Cloud Console "
            "with the YouTube Data API v3 enabled."
        )
 
    resp = requests.get(
        COMMENT_THREADS_URL,
        params={
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(max_results, 100),
            "order": "relevance",
            "textFormat": "plainText",
            "key": API_KEY,
        },
        timeout=15,
    )
 
    if resp.status_code == 403 and "commentsDisabled" in resp.text:
        raise RuntimeError("Comments are disabled on this video -- nothing to scan.")
    if resp.status_code == 404:
        raise RuntimeError("Video not found -- check the URL and that the video is public.")
    resp.raise_for_status()
 
    items = resp.json().get("items", [])
 
    comments = []
    for item in items:
        top = item["snippet"]["topLevelComment"]["snippet"]
        comment_id = item["snippet"]["topLevelComment"]["id"]
        author = top.get("authorDisplayName", "unknown")
        author_channel_id = top.get("authorChannelId", {}).get("value", "")
 
        comments.append({
            "platform": "YouTube",
            "account": author,
            "profile_url": f"https://youtube.com/channel/{author_channel_id}" if author_channel_id else "",
            "post_url": f"https://youtube.com/watch?v={video_id}&lc={comment_id}",
            "text": top.get("textDisplay", ""),
            "timestamp": top.get("publishedAt", ""),
        })
 
    return comments
 


