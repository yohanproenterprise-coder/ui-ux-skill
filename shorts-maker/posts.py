"""Textes de publication (titre / description / hashtags) par niche, en anglais."""
import random

SATISFYING = {
    "hooks": [
        "Wait for the end… your brain will thank you 😌",
        "The way this ends is SO satisfying 🤯",
        "Stressed? Press play. Instant calm ✨",
        "Watch till the end, you won't regret it 👀",
        "10 seconds of pure satisfaction 😍",
        "This sound is everything 🎧",
        "Don't skip this one, trust me 🫶",
    ],
    "questions": [
        "Would you watch this on repeat? 👇",
        "Comment 🔥 if you watched it twice!",
        "What should I make next? Tell me below 👇",
        "Rate this from 1 to 10 👇",
        "Who else can't stop watching? 🙋",
    ],
    "cta": [
        "Follow for daily satisfying videos 🫶",
        "New satisfying videos every day — don't miss one!",
        "More satisfying videos coming soon ✨",
    ],
    "titles": [
        "The Most Satisfying Video You'll Watch Today 😌",
        "Wait For It… So Satisfying 🤯",
        "10 Seconds of Pure Satisfaction ✨",
        "This Sound Is Everything 🎧",
        "Oddly Satisfying — Try Not To Stop Watching 😍",
    ],
    "tiktok_tags": [
        ["#satisfying", "#oddlysatisfying", "#asmr", "#satisfyingvideo", "#fyp"],
        ["#oddlysatisfying", "#satisfying", "#asmrsounds", "#relaxing", "#foryou"],
        ["#satisfying", "#stressrelief", "#calming", "#asmr", "#fyp"],
    ],
    "youtube_tags": ["#shorts", "#satisfying", "#oddlysatisfying", "#asmr", "#relaxing"],
}

NICHES = {"satisfying": SATISFYING}


def make_post(niche: str, index: int = 0, seed: int | None = None) -> dict | None:
    """Texte varié pour chaque clip (évite des descriptions toutes identiques = spam)."""
    n = NICHES.get(niche)
    if not n:
        return None
    r = random.Random(seed if seed is not None else index)
    hook, q, cta = r.choice(n["hooks"]), r.choice(n["questions"]), r.choice(n["cta"])
    tt_tags = " ".join(r.choice(n["tiktok_tags"]))
    yt_tags = " ".join(n["youtube_tags"])
    return {
        "tiktok": f"{hook}\n{q}\n\n{tt_tags}",
        "youtube_title": r.choice(n["titles"]),
        "youtube_desc": f"{hook}\n{cta}\n\n{q}\n\n{yt_tags}",
    }
