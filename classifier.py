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
import time
import requests
from config import Config

PERSPECTIVE_URL = (
    "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
)
HUGGINGFACE_URL = f"https://api-inference.huggingface.co/models/{Config.HUGGINGFACE_MODEL}"

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


# --- Hugging Face Inference API (primary, recommended) --------------------
# Perspective API stopped accepting new access requests in Feb 2026, so this
# is the actual working "real classifier" path for new setups. unitary/
# toxic-bert is publicly hosted, needs only a free HF account + token --
# no approval process. Get a token at https://huggingface.co/settings/tokens

def _huggingface_classify(text):
    if not text or not text.strip():
        return {"flagged": False, "category": None, "confidence": 0, "reason": ""}

    headers = {"Authorization": f"Bearer {Config.HUGGINGFACE_API_TOKEN}"}
    payload = {"inputs": text[:2000]}

    resp = requests.post(HUGGINGFACE_URL, headers=headers, json=payload, timeout=20)

    if resp.status_code == 503:
        # Free-tier models cold-start on first call (or after idling) --
        # HF returns an estimated_time to wait, then it's warm.
        wait = resp.json().get("estimated_time", 10)
        time.sleep(min(wait, 20))
        resp = requests.post(HUGGINGFACE_URL, headers=headers, json=payload, timeout=20)

    if resp.status_code != 200:
        raise RuntimeError(f"Hugging Face API error ({resp.status_code}): {resp.text[:200]}")

    data = resp.json()
    scores = data[0] if data and isinstance(data, list) else []

    best_label, best_score = None, 0.0
    for item in scores:
        label = item.get("label")
        score = item.get("score", 0.0)
        if label in Config.HUGGINGFACE_LABEL_MAP and score > best_score:
            best_label, best_score = label, score

    if best_label and best_score >= Config.HUGGINGFACE_THRESHOLD:
        return {
            "flagged": True,
            "category": Config.HUGGINGFACE_LABEL_MAP[best_label],
            "confidence": round(best_score * 100),
            "reason": f"Hugging Face model ({Config.HUGGINGFACE_MODEL}) scored '{best_label}' at {best_score:.2f}.",
        }

    return {"flagged": False, "category": None, "confidence": 0, "reason": ""}


# --- Public entry point -----------------------------------------------------

def classify(text):
    """
    Classify a piece of text.
    Order: Hugging Face (real model, recommended) -> Perspective (legacy,
    only works if you already had access before Feb 2026) -> rule-based
    (always works, but coarse -- exists so the app never fully breaks).
    """
    if Config.HUGGINGFACE_API_TOKEN:
        try:
            return _huggingface_classify(text)
        except Exception:
            pass  # fall through rather than losing the whole request

    if Config.PERSPECTIVE_API_KEY:
        try:
            return _perspective_classify(text)
        except Exception:
            pass

    return _rule_based_classify(text)