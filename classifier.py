"""
Content classifier. Isolated from the rest of the app so it can be
swapped out or upgraded later without touching routes or scrapers.

Primary method: Google's Perspective API (https://perspectiveapi.com/),
a free, well-established toxicity-scoring model -- far more accurate
than keyword matching, and simple to call (one HTTP request).

Fallback: a basic rule-based keyword matcher, used automatically if
no PERSPECTIVE_API_KEY is configured, or if a Perspective call fails.
This keeps the app fully functional with zero paid/gated dependencies.

Both paths return the same shape:
{
    "flagged": bool,
    "category": str | None,
    "confidence": int (0-100),
    "reason": str
}
"""
import re
import requests
from config import Config

PERSPECTIVE_URL = (
    "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
)

# --- Rule-based fallback --------------------------------------------------

_KEYWORD_RULES = {
    "Hate Speech": [
        r"\b(racial slur|go back to your country|subhuman|ethnic cleansing)\b",
    ],
    "Harassment": [
        r"\b(kill yourself|you're worthless|nobody likes you|stalking you)\b",
    ],
    "Violence": [
        r"\b(i will kill|going to hurt you|bring a gun|shoot you)\b",
    ],
    "Extremism": [
        r"\b(join the cause|holy war|glorify.*attack|recruit.*jihad)\b",
    ],
    "Misinformation": [
        r"\b(vaccines cause autism|election was stolen|flat earth proof)\b",
    ],
    "Scam / Fraud": [
        r"\b(click here to claim|send bitcoin to|you.?ve won a prize|verify your account now)\b",
    ],
    "Adult Content": [
        r"\b(explicit content|nsfw link|onlyfans promo)\b",
    ],
    "Self-Harm": [
        r"\b(want to end my life|how to self.?harm|thinspo)\b",
    ],
    "Spam": [
        r"\b(follow for follow|buy followers|check my bio|dm me for)\b",
    ],
}


def _rule_based_classify(text):
    text_lower = text.lower()
    for category, patterns in _KEYWORD_RULES.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return {
                    "flagged": True,
                    "category": category,
                    "confidence": 60,  # deliberately modest -- keyword matching is coarse
                    "reason": "Matched a rule-based policy keyword pattern.",
                }
    return {"flagged": False, "category": None, "confidence": 0, "reason": ""}


# --- Perspective API (primary) --------------------------------------------

def _perspective_classify(text):
    if not text or not text.strip():
        return {"flagged": False, "category": None, "confidence": 0, "reason": ""}

    params = {"key": Config.PERSPECTIVE_API_KEY}
    body = {
        "comment": {"text": text[:3000]},  # Perspective has a size limit
        "languages": ["en"],
        "requestedAttributes": {attr: {} for attr in Config.PERSPECTIVE_ATTRIBUTES},
    }

    resp = requests.post(PERSPECTIVE_URL, params=params, json=body, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Perspective API error ({resp.status_code}): {resp.text[:200]}")

    data = resp.json()
    scores = data.get("attributeScores", {})

    best_attr, best_score = None, 0.0
    for attr in Config.PERSPECTIVE_ATTRIBUTES:
        val = scores.get(attr, {}).get("summaryScore", {}).get("value", 0.0)
        if val > best_score:
            best_attr, best_score = attr, val

    if best_attr and best_score >= Config.PERSPECTIVE_THRESHOLD:
        return {
            "flagged": True,
            "category": Config.PERSPECTIVE_ATTRIBUTES[best_attr],
            "confidence": round(best_score * 100),
            "reason": f"Perspective API scored '{best_attr}' at {best_score:.2f}.",
        }

    return {"flagged": False, "category": None, "confidence": 0, "reason": ""}


# --- Public entry point -----------------------------------------------------

def classify(text):
    """
    Classify a piece of text. Tries Perspective API first (if configured);
    falls back to rule-based matching on any failure or missing key.
    """
    if Config.PERSPECTIVE_API_KEY:
        try:
            return _perspective_classify(text)
        except Exception:
            # Fall through to rule-based rather than losing the whole request.
            pass

    return _rule_based_classify(text)
