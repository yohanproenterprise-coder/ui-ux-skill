"""Pipeline : URL YouTube -> moments clés -> clips verticaux 9:16."""
import array
import json
import os
import re
import subprocess
from pathlib import Path

WORK = Path(os.environ.get("SHORTS_WORKDIR", "work"))
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

HOOK_WORDS = re.compile(
    r"\b(secret|incroyable|jamais|toujours|erreur|astuce|attention|problème|"
    r"gratuit|argent|choc|vérité|impossible|meilleur|pire|comment|pourquoi|"
    r"never|always|mistake|secret|free|money|truth|best|worst|how|why|shocking)\b",
    re.I,
)


def video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})", url)
    if not m:
        raise ValueError("URL YouTube invalide")
    return m.group(1)


def download(url: str) -> tuple[Path, dict]:
    import yt_dlp

    vid = video_id(url)
    WORK.mkdir(exist_ok=True)
    opts = {
        "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "merge_output_format": "mp4",
        "outtmpl": str(WORK / f"{vid}.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return WORK / f"{vid}.mp4", {"title": info.get("title", vid), "duration": info.get("duration", 0)}


def get_transcript(url: str) -> list[dict]:
    """Liste de {start, end, text}. Vide si indisponible."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id(url), languages=["fr", "en"])
        return [
            {"start": s.start, "end": s.start + s.duration, "text": s.text.replace("\n", " ")}
            for s in fetched
        ]
    except Exception:
        return []


def audio_energy(video: Path) -> list[float]:
    """Énergie audio moyenne par seconde (PCM 8 kHz mono)."""
    out = subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", str(video), "-vn", "-ac", "1", "-ar", "8000",
         "-f", "s16le", "-"],
        capture_output=True, check=True,
    ).stdout
    samples = array.array("h")
    samples.frombytes(out[: len(out) // 2 * 2])
    sec = []
    for i in range(0, len(samples), 8000):
        chunk = samples[i : i + 8000]
        sec.append((sum(x * x for x in chunk) / max(len(chunk), 1)) ** 0.5)
    return sec


def heuristic_moments(video: Path, duration: float, transcript: list[dict],
                      n: int = 5, length: int = 35) -> list[dict]:
    energy = audio_energy(video)
    dur = int(min(duration or len(energy), len(energy)))
    length = min(length, max(dur, 1))
    mx = max(energy) or 1
    energy = [e / mx for e in energy]
    words = [0.0] * (dur + 1)
    hooks = [0.0] * (dur + 1)
    for seg in transcript:
        s = int(seg["start"])
        if s <= dur:
            words[s] += len(seg["text"].split())
            hooks[s] += len(HOOK_WORDS.findall(seg["text"]))
    wmax, hmax = (max(words) or 1), (max(hooks) or 1)
    per_sec = [0.5 * energy[i] + 0.3 * words[i] / wmax + 0.2 * hooks[i] / hmax for i in range(dur)]
    # fenêtre glissante, favorise les 15 premières secondes (accroche)
    scored = []
    for start in range(0, max(dur - length, 0) + 1, 3):
        win = per_sec[start : start + length]
        hook = sum(per_sec[start : start + 5]) / 5
        scored.append((sum(win) / len(win) + 0.5 * hook, start))
    scored.sort(reverse=True)
    picks = []
    for score, start in scored:
        if all(abs(start - p["start"]) >= length for p in picks):
            picks.append({"start": float(start), "end": float(start + length),
                          "score": round(score, 3), "reason": "pic d'énergie / densité de parole"})
        if len(picks) == n:
            break
    return sorted(picks, key=lambda p: p["start"])


def claude_moments(title: str, duration: float, transcript: list[dict],
                   n: int = 5, length: int = 35) -> list[dict]:
    """Choix éditorial par Claude (nécessite ANTHROPIC_API_KEY + transcript)."""
    import anthropic

    text = "\n".join(f"[{int(s['start'])}s] {s['text']}" for s in transcript)[:120_000]
    prompt = (
        f"Vidéo « {title} » ({int(duration)}s). Voici la transcription horodatée.\n"
        f"Choisis les {n} meilleurs moments pour des Shorts/TikTok viraux de ~{length}s "
        "(accroche forte dans les 3 premières secondes, idée complète, pas de coupure en plein mot). "
        'Réponds UNIQUEMENT en JSON : [{"start":sec,"end":sec,"reason":"...","title":"titre accrocheur"}]\n\n'
        + text
    )
    msg = anthropic.Anthropic().messages.create(
        model=CLAUDE_MODEL, max_tokens=2000, messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text
    data = json.loads(raw[raw.index("[") : raw.rindex("]") + 1])
    return [
        {"start": float(m["start"]), "end": min(float(m["end"]), duration),
         "reason": m.get("reason", ""), "title": m.get("title", ""), "score": 1.0}
        for m in data
    ]


def find_moments(video: Path, info: dict, transcript: list[dict], n=5, length=35) -> list[dict]:
    if transcript and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return claude_moments(info["title"], info["duration"], transcript, n, length)
        except Exception as e:  # repli sur l'heuristique
            print("Claude indisponible, repli heuristique :", e)
    return heuristic_moments(video, info["duration"], transcript, n, length)


def _srt_time(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int((s % 1) * 1000):03}"


def write_srt(transcript: list[dict], start: float, end: float, path: Path) -> bool:
    segs = [s for s in transcript if s["end"] > start and s["start"] < end]
    if not segs:
        return False
    lines = []
    for i, s in enumerate(segs, 1):
        a, b = max(s["start"] - start, 0), min(s["end"], end) - start
        lines.append(f"{i}\n{_srt_time(a)} --> {_srt_time(b)}\n{s['text']}\n")
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def render_clip(video: Path, moment: dict, out: Path, transcript: list[dict] | None = None,
                mode: str = "blur", captions: bool = True) -> Path:
    """mode 'crop' = recadrage centré ; 'blur' = vidéo entière sur fond flouté."""
    start, end = moment["start"], moment["end"]
    if mode == "crop":
        vf = "crop=ih*9/16:ih,scale=1080:1920"
    else:
        vf = ("split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,"
              "crop=1080:1920,boxblur=30:5[bg];[b]scale=1080:-2[fg];"
              "[bg][fg]overlay=(W-w)/2:(H-h)/2")
    srt = out.with_suffix(".srt")
    if captions and transcript and write_srt(transcript, start, end, srt):
        style = "FontSize=14,Bold=1,Outline=2,Alignment=2,MarginV=120"
        vf += f",subtitles={srt.name}:force_style='{style}'"
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-to", str(end), "-i", str(video.resolve()),
           "-filter_complex" if mode == "blur" else "-vf", vf,
           "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
           "-movflags", "+faststart", out.name]
    subprocess.run(cmd, check=True, cwd=out.parent)
    return out


def process(url: str, n=5, length=35, mode="blur", captions=True, log=print) -> list[dict]:
    log("Téléchargement…")
    video, info = download(url)
    log("Transcription…")
    transcript = get_transcript(url)
    log("Détection des moments clés…")
    moments = find_moments(video, info, transcript, n, length)
    outdir = WORK / "clips" / video_id(url)
    outdir.mkdir(parents=True, exist_ok=True)
    for i, m in enumerate(moments, 1):
        log(f"Rendu du clip {i}/{len(moments)}…")
        m["file"] = str(render_clip(video, m, outdir / f"short_{i}.mp4", transcript, mode, captions))
    (outdir / "moments.json").write_text(json.dumps(moments, ensure_ascii=False, indent=2))
    return moments
