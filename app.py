"""
Social Media Policy Monitor -- Flask app.

Platforms (v1): YouTube, Reddit, Instagram (hashtag search only -- see
instagram_client.py's docstring for the real constraints on that one).
Architecture is modular: each platform client exposes
collect_content_for_keyword(keyword) -> list[dict] with a shared item
shape, wired in via PLATFORM_CLIENTS below. Adding a platform later means
writing one new module and adding one line here.

This tool is a REVIEW QUEUE, not a public accusation system: it surfaces
possible policy-relevant content for a human moderator/researcher to
check themselves. Automated classifiers (including this one) produce
false positives, so nothing here should be treated as a final verdict.
"""
from flask import Flask, render_template, request, redirect, url_for, flash
from config import Config
from database import init_db
from models import upsert_account, add_violation, get_flagged_accounts, get_account, log_search
from classifier import classify
import youtube_client
import reddit_client
import instagram_client

app = Flask(__name__)
app.config.from_object(Config)

# Registry of available platform clients. Add new platforms here.
PLATFORM_CLIENTS = {
    "YouTube": youtube_client.collect_content_for_keyword,
    "Reddit": reddit_client.collect_content_for_keyword,
    "Instagram": instagram_client.collect_content_for_keyword,
}

init_db()


@app.route("/")
def index():
    return render_template("index.html", platforms=list(PLATFORM_CLIENTS.keys()))


@app.route("/analyze-video", methods=["POST"])
def analyze_video():
    """
    Scan a single YouTube video's comments for policy violations.
    Each flagged comment's author (the commenter, not the video's channel
    owner) becomes the account on the review queue -- they're the one who
    actually wrote the text being evaluated.
    """
    video_url = (request.form.get("video_url") or "").strip()

    if not video_url:
        flash("Please paste a YouTube video URL.", "warning")
        return redirect(url_for("index"))

    video_id = youtube_client.extract_video_id(video_url)
    if not video_id:
        flash("Couldn't find a video ID in that URL -- check it's a valid YouTube link.", "warning")
        return redirect(url_for("index"))

    try:
        comments = youtube_client.get_video_comments(video_id)
    except Exception as e:
        log_search(video_url, "YouTube (video comments)", "error", str(e))
        flash(f"Couldn't fetch comments: {e}", "danger")
        return redirect(url_for("index"))

    log_search(video_url, "YouTube (video comments)", "ok", f"{len(comments)} comments collected")

    total_flagged = 0
    for item in comments:
        result = classify(item["text"])
        if not result["flagged"]:
            continue

        account_id = upsert_account(
            platform=item["platform"],
            account_name=item["account"],
            profile_url=item["profile_url"],
            risk_category=result["category"],
            confidence=result["confidence"],
        )
        add_violation(
            account_id=account_id,
            post_url=item["post_url"],
            post_text=item["text"],
            reason=result["reason"],
            category=result["category"],
            confidence=result["confidence"],
            timestamp=item.get("timestamp", ""),
        )
        total_flagged += 1

    if total_flagged:
        flash(f"Flagged {total_flagged} commenter(s) for review.", "success")
    else:
        flash("Scan completed -- nothing crossed the review threshold.", "info")

    return redirect(url_for("results"))


@app.route("/search", methods=["POST"])
def search():
    keyword = (request.form.get("keyword") or "").strip()
    selected_platforms = request.form.getlist("platforms")

    if not keyword:
        flash("Please enter a keyword to search.", "warning")
        return redirect(url_for("index"))

    if not selected_platforms:
        flash("Please select at least one platform.", "warning")
        return redirect(url_for("index"))

    errors = []
    total_flagged = 0

    for platform in selected_platforms:
        client_fn = PLATFORM_CLIENTS.get(platform)
        if not client_fn:
            errors.append(f"{platform} is not yet supported.")
            continue

        try:
            items = client_fn(keyword)
        except Exception as e:
            # A failure on one platform should never take down the whole search.
            log_search(keyword, platform, "error", str(e))
            errors.append(f"{platform} search failed: {e}")
            continue

        log_search(keyword, platform, "ok", f"{len(items)} items collected")

        for item in items:
            result = classify(item["text"])
            if not result["flagged"]:
                continue

            account_id = upsert_account(
                platform=item["platform"],
                account_name=item["account"],
                profile_url=item["profile_url"],
                risk_category=result["category"],
                confidence=result["confidence"],
            )
            add_violation(
                account_id=account_id,
                post_url=item["post_url"],
                post_text=item["text"],
                reason=result["reason"],
                category=result["category"],
                confidence=result["confidence"],
                timestamp=item.get("timestamp", ""),
            )
            total_flagged += 1

    for e in errors:
        flash(e, "danger")

    if total_flagged:
        flash(f"Flagged {total_flagged} item(s) for review.", "success")
    elif not errors:
        flash("Search completed -- nothing crossed the review threshold.", "info")

    return redirect(url_for("results"))


@app.route("/results")
def results():
    accounts = get_flagged_accounts()
    return render_template("results.html", accounts=accounts)


@app.route("/account/<int:account_id>")
def account_detail(account_id):
    account, violations = get_account(account_id)
    if not account:
        flash("Account not found.", "warning")
        return redirect(url_for("results"))
    return render_template("account.html", account=account, violations=violations)


if __name__ == "__main__":
    app.run(debug=True, port=5000)