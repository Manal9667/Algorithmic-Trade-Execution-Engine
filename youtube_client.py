
Claude finished the response

Architected comprehensive YouTube video analysis pipeline integrating Hugging Face models
Architected comprehensive YouTube video analysis pipeline integrating Hugging Face models
Good instinct — and this is a genuinely better design for what you're actually trying to build. A few reasons this is a real upgrade, not just a swap:

It fixes the Perspective dead-end — Hugging Face's Inference API is free, doesn't require the closed-off approval process Perspective needs now.
It changes what gets flagged, in a good way. Your original keyword-search design flagged based on video titles/descriptions — but those belong to the channel owner, who didn't necessarily write anything policy-violating themselves. Scanning comments on a video means the account you flag is the actual person who wrote the violating text. That's a more defensible mapping between "flagged account" and "thing they actually said."
Your pasted regex is solid — I'll use that idea (extract video ID from any YouTube URL format) as-is.
Here's the plan: add a new mode alongside your existing keyword search — paste a video URL, pull its comments via commentThreads.list, classify each comment, and flag whichever commenters cross the threshold. I'll wire it into your existing app.py/models.py/database.py without touching what already works.


Ran a command
Ran a command
First, the classifier — swapping Hugging Face in as the primary path, keeping your rule-based fallback:


Edited 3 files
Edited 3 files
Now youtube_client.py — adding video-ID extraction and comment fetching alongside the existing keyword search:


Edited 2 files, viewed a file
Edited 2 files, viewed a file
Now app.py — a new route for video-URL comment scanning, reusing your existing storage functions:


Editing file
Editing file
Now the template — adding a second card for video-URL scanning next to your existing keyword search:


Viewed a file, edited a file
Viewed a file, edited a file
Now let's actually test it end to end — mocking the YouTube API and Hugging Face responses, since I can't reach either from this sandbox:


Ran 2 commands
Ran 2 commands
That's just Jinja auto-escaping the apostrophe as &#39; — the message works correctly, my test assertion was too strict (didn't account for HTML escaping). Fixing the test and re-running:


Ran a command
Ran a command
Full pipeline verified: URL parsing across all common YouTube link formats, successful comment scan with correct flagging, invalid/empty URL handling, and comments-disabled videos — all fail gracefully with clear messages, no crashes.

Updated files — youtube_client.py:


Ran a command
Ran a command
Here's what changed across the four files (youtube_client.py, classifier.py, config.py, app.py, templates/index.html):

youtube_client.py — added extract_video_id(url) (your regex idea, generalized to catch shorts/embed/youtu.be too) and get_video_comments(video_id) (fetches top-level comments via commentThreads.list, with clean error messages for disabled comments / missing videos).

classifier.py — added _huggingface_classify() as the new primary path (calls unitary/toxic-bert, handles the free-tier cold-start delay), tried before Perspective (kept for anyone with legacy access) and the rule-based fallback.

config.py — added HUGGINGFACE_API_TOKEN, HUGGINGFACE_MODEL, HUGGINGFACE_THRESHOLD, and a label map from the model's raw output labels to your existing category names.

app.py — new /analyze-video route, reusing your existing upsert_account/add_violation/log_search unchanged.

templates/index.html — added a second card with the video URL input field.

To get this live, you'll need one more credential:

Add it to Render (and your local .env)
Add HUGGINGFACE_API_TOKEN as a new environment variable on Render, pasting the token directly into Render's field (not here in chat). Locally, add the same line to your .env.
1
2
3
Want the five updated/new files (app.py, classifier.py, config.py, youtube_client.py, templates/index.html) presented now so you can drop them into your local folder and push?

yes but don't make zip file


Presented 5 files
Presented 5 files
All five are individual files, no zip. One thing to watch: index.html needs to go back into your templates/ folder (not the project root) when you save it locally — same as the earlier flattening issue with the other HTML files.

Replace these in your local socialpolicy folder:

app.py
classifier.py
config.py
youtube_client.py
templates/index.html
Then:

powershell
git add app.py classifier.py config.py youtube_client.py templates/index.html
git commit -m "Add video-comment scanning with Hugging Face classifier"
git push
Once that's pushed and Render redeploys, add HUGGINGFACE_API_TOKEN as a new env var on Render so the new classifier path actually activates — otherwise it'll fall back to the rule-based matcher like before.


App
PY 

Classifier
PY 

Config
PY 

Youtube client
PY 

Index
Code · HTML 





Claude is AI and can make mistakes. Please double-check responses.
Youtube client · PY
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
 


