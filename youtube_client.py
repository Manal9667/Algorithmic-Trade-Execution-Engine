"""
YouTube data fetcher, built entirely on the official YouTube Data API v3.
No scraping, no headless browsers -- just documented REST endpoints:
https://developers.google.com/youtube/v3

Returns a flat list of dicts, one per public comment, in a common
format so the classifier and rest of the app don't need to know or
care that the source was YouTube specifically:

{
    "platform": "YouTube",
    "account": "<channel title>",
    "channel_id": "<channel id>",
    "profile_url": "https://www.youtube.com/channel/<id>",
    "post_url": "<link to the specific video/comment>",
    "text": "<comment or video title+description text>",
    "timestamp": "<ISO8601>"
}
"""
import requests
from config import Config

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeClientError(Exception):
    pass


def _get(endpoint, params):
    params = {**params, "key": Config.YOUTUBE_API_KEY}
    resp = requests.get(f"{YOUTUBE_API_BASE}/{endpoint}", params=params, timeout=10)
    if resp.status_code != 200:
        raise YouTubeClientError(
            f"YouTube API error ({resp.status_code}): {resp.text[:200]}"
        )
    return resp.json()


def search_videos(keyword, max_results=None):
    """Search public videos matching a keyword. Returns basic video/channel info."""
    if not Config.YOUTUBE_API_KEY:
        raise YouTubeClientError(
            "YOUTUBE_API_KEY is not set. Add it to your .env file or Render environment."
        )

    max_results = max_results or Config.MAX_VIDEOS_PER_SEARCH
    data = _get(
        "search",
        {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "maxResults": max_results,
            "order": "relevance",
            "safeSearch": "none",
        },
    )

    videos = []
    for item in data.get("items", []):
        vid = item["id"]["videoId"]
        snip = item["snippet"]
        videos.append(
            {
                "video_id": vid,
                "channel_id": snip["channelId"],
                "channel_title": snip["channelTitle"],
                "title": snip["title"],
                "description": snip.get("description", ""),
                "published_at": snip.get("publishedAt", ""),
                "video_url": f"https://www.youtube.com/watch?v={vid}",
            }
        )
    return videos


def fetch_comments(video_id, max_results=None):
    """Fetch top-level public comments for a video. Some videos have
    comments disabled -- that's handled gracefully, not as an error."""
    max_results = max_results or Config.MAX_COMMENTS_PER_VIDEO
    try:
        data = _get(
            "commentThreads",
            {
                "part": "snippet",
                "videoId": video_id,
                "maxResults": max_results,
                "order": "relevance",
                "textFormat": "plainText",
            },
        )
    except YouTubeClientError as e:
        if "commentsDisabled" in str(e) or "403" in str(e):
            return []
        raise

    comments = []
    for item in data.get("items", []):
        top = item["snippet"]["topLevelComment"]["snippet"]
        comments.append(
            {
                "comment_id": item["id"],
                "author": top.get("authorDisplayName", "Unknown"),
                "author_channel_id": (top.get("authorChannelId") or {}).get("value", ""),
                "text": top.get("textDisplay", ""),
                "published_at": top.get("publishedAt", ""),
                "like_count": top.get("likeCount", 0),
            }
        )
    return comments


def collect_content_for_keyword(keyword):
    """
    Main entry point used by the app. Pulls a small set of videos for the
    keyword, then pulls a small set of comments per video, and returns
    everything (video text + comment text) in the common content format.

    This intentionally casts a wide net over PUBLIC COMMENTERS, not just
    the channel that posted the video -- policy-violating content on
    YouTube is very often found in the comment section.
    """
    items = []
    videos = search_videos(keyword)

    for v in videos:
        # The video itself, attributed to the uploading channel.
        items.append(
            {
                "platform": "YouTube",
                "account": v["channel_title"],
                "channel_id": v["channel_id"],
                "profile_url": f"https://www.youtube.com/channel/{v['channel_id']}",
                "post_url": v["video_url"],
                "text": f"{v['title']}\n{v['description']}",
                "timestamp": v["published_at"],
            }
        )

        # Public comments, attributed to the commenting account (not the
        # video owner) -- this is who the flag would actually apply to.
        try:
            comments = fetch_comments(v["video_id"])
        except YouTubeClientError:
            comments = []

        for c in comments:
            if not c["author_channel_id"]:
                continue
            items.append(
                {
                    "platform": "YouTube",
                    "account": c["author"],
                    "channel_id": c["author_channel_id"],
                    "profile_url": f"https://www.youtube.com/channel/{c['author_channel_id']}",
                    "post_url": f"{v['video_url']}&lc={c['comment_id']}",
                    "text": c["text"],
                    "timestamp": c["published_at"],
                }
            )

    return items
