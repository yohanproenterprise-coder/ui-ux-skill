"""Pipeline : URL YouTube -> moments clés -> clips verticaux 9:16 optimisés."""
import array
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

WORK = Path(os.environ.get("SHORTS_WORKDIR", "work"))
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

HOOK_WORDS = re.compile(
    r"\b(secret|incroyable|jamais|toujours|erreur|astuce|attention|problème|"
    r"gratuit|argent|choc|vérité|impossible|meilleur|pire|comment|pourquoi|"
    r"never|always|mistake|free|money|truth|best|worst|how|why|shocking)\b",
    re.I,
)
NOISE = re.compile(r"^\s*[\[(♪].*[\])♪]\s*$")  # [Musique], (applaudissements), ♪


def video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})", url)
    if not m:
        raise ValueError("URL YouTube invalide")
    return m.group(1)


def download(url: str) -> tuple[Path, dict]:
    import yt_dlp

    vid = video_id(url)
    WORK.mkdir(exist_ok=True)
    mp4, meta = WORK / f"{vid}.mp4", WORK / f"{vid}.json"
    if mp4.exists() and meta.exists():  # déjà téléchargée
        return mp4, json.loads(meta.read_text(encoding="utf-8"))
    h = int(os.environ.get("MAX_HEIGHT", "720"))
    opts = {
        "format": f"bv*[height<={h}]+ba/b[height<={h}]/b",
        "merge_output_format": "mp4",
        "outtmpl": str(WORK / f"{vid}.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
        "no_color": True,
    }
    if os.environ.get("YT_COOKIES_BROWSER"):
        opts["cookiesfrombrowser"] = (os.environ["YT_COOKIES_BROWSER"],)
    local = Path(__file__).resolve().parent / "cookies.txt"  # peu importe d'où on lance l'outil
    # navigateur choisi => on l'utilise seul ; sinon fichier explicite, sinon cookies.txt local
    cookie_file = os.environ.get("YT_COOKIES_FILE") or (
        "" if os.environ.get("YT_COOKIES_BROWSER") else (str(local) if local.exists() else ""))
    if cookie_file:  # un cookies.txt posé dans ce dossier est utilisé automatiquement
        opts["cookiefile"] = cookie_file
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        if "Sign in to confirm" in str(e):
            used = f"fichier utilisé : {cookie_file}" if cookie_file else f"aucun cookies.txt trouvé (attendu : {local})"
            raise RuntimeError(f"YouTube demande une connexion — {used}. Exporte tes cookies YouTube (voir README).") from e
        raise
    data = {"title": info.get("title", vid), "duration": info.get("duration", 0)}
    meta.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return mp4, data


def clean_transcript(raw: list[dict]) -> list[dict]:
    """Retire le bruit ([Musique]…) et supprime les chevauchements des sous-titres auto."""
    segs = [s for s in raw if s["text"].strip() and not NOISE.match(s["text"])]
    segs.sort(key=lambda s: s["start"])
    for a, b in zip(segs, segs[1:]):
        a["end"] = max(min(a["end"], b["start"]), a["start"] + 0.2)
    return segs


def get_transcript(url: str) -> list[dict]:
    """Liste de {start, end, text}. Vide si indisponible."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        fetched = YouTubeTranscriptApi().fetch(video_id(url), languages=["fr", "en"])
        return clean_transcript([
            {"start": s.start, "end": s.start + s.duration, "text": s.text.replace("\n", " ")}
            for s in fetched
        ])
    except Exception:
        return []


def audio_energy(video: Path) -> list[float]:
    out = subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", str(video), "-vn", "-ac", "1", "-ar", "8000",
         "-f", "s16le", "-"], capture_output=True, check=True).stdout
    samples = array.array("h")
    samples.frombytes(out[: len(out) // 2 * 2])
    return [(sum(x * x for x in samples[i:i + 8000]) / max(len(samples[i:i + 8000]), 1)) ** 0.5
            for i in range(0, len(samples), 8000)]


def heuristic_moments(video: Path, duration: float, transcript: list[dict],
                      n: int = 5, length: int = 35) -> list[dict]:
    energy = audio_energy(video)
    dur = int(min(duration or len(energy), len(energy)))
    length = min(length, max(dur, 1))
    mx = max(energy) or 1
    energy = [e / mx for e in energy]
    words, hooks = [0.0] * (dur + 1), [0.0] * (dur + 1)
    for seg in transcript:
        s = int(seg["start"])
        if s <= dur:
            words[s] += len(seg["text"].split())
            hooks[s] += len(HOOK_WORDS.findall(seg["text"])) + ("?" in seg["text"])
    wmax, hmax = (max(words) or 1), (max(hooks) or 1)
    per_sec = [0.5 * energy[i] + 0.3 * words[i] / wmax + 0.2 * hooks[i] / hmax for i in range(dur)]
    scored = []
    for start in range(0, max(dur - length, 0) + 1, 3):
        win = per_sec[start:start + length]
        hook = sum(per_sec[start:start + 5]) / 5  # l'accroche pèse beaucoup
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
    import anthropic

    text = "\n".join(f"[{int(s['start'])}s] {s['text']}" for s in transcript)[:120_000]
    prompt = (
        f"Tu es expert en contenu court viral (YouTube Shorts, TikTok, Reels).\n"
        f"Vidéo « {title} » ({int(duration)}s). Transcription horodatée ci-dessous.\n\n"
        f"Choisis les {n} meilleurs extraits d'environ {length}s (entre {max(length - 10, 15)} et {length + 15}s).\n"
        "Critères : accroche forte dès les 3 premières secondes (question, affirmation choc, promesse), "
        "extrait compréhensible SANS le contexte de la vidéo, tension ou émotion, chute/payoff clair à la fin, "
        "début et fin sur des phrases complètes. Évite les intros, remerciements et passages creux.\n"
        "Pour chaque extrait fournis aussi : hook (texte affiché à l'écran 3s, max 8 mots, qui donne envie de rester), "
        "title (titre de publication, max 70 car.), description (1-2 phrases + question pour déclencher des commentaires), "
        "hashtags (5 à 7, mélange larges et de niche), score (1-10 potentiel viral), reason (pourquoi ça marche).\n"
        'Réponds UNIQUEMENT en JSON : [{"start":sec,"end":sec,"hook":"","title":"","description":"",'
        '"hashtags":["#.."],"score":0,"reason":""}]\n\n' + text
    )
    msg = anthropic.Anthropic().messages.create(
        model=CLAUDE_MODEL, max_tokens=4000, messages=[{"role": "user", "content": prompt}])
    raw = msg.content[0].text
    data = json.loads(raw[raw.index("["):raw.rindex("]") + 1])
    out = []
    for m in data:
        m["start"], m["end"] = float(m["start"]), min(float(m["end"]), duration or 1e9)
        out.append(m)
    return sorted(out, key=lambda m: m["start"])


def snap_to_speech(m: dict, transcript: list[dict]) -> dict:
    """Aligne début/fin sur des limites de phrases pour ne jamais couper un mot."""
    if not transcript:
        return m
    starts = [s for s in transcript if abs(s["start"] - m["start"]) <= 4]
    if starts:
        m["start"] = max(min(starts, key=lambda s: abs(s["start"] - m["start"]))["start"] - 0.15, 0)
    ends = [s for s in transcript if abs(s["end"] - m["end"]) <= 5 and s["end"] > m["start"] + 10]
    if ends:
        sentence = [s for s in ends if re.search(r"[.!?…]\s*$", s["text"])]
        best = min(sentence or ends, key=lambda s: abs(s["end"] - m["end"]))
        m["end"] = best["end"] + 0.3
    return m


def find_moments(video: Path, info: dict, transcript: list[dict], n=5, length=35) -> list[dict]:
    moments = None
    if transcript and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            moments = claude_moments(info["title"], info["duration"], transcript, n, length)
        except Exception as e:
            print("Claude indisponible, repli heuristique :", e)
    if moments is None:
        moments = heuristic_moments(video, info["duration"], transcript, n, length)
    for m in moments:
        snap_to_speech(m, transcript)
        m.setdefault("title", info["title"][:70])
        m.setdefault("hashtags", ["#shorts", "#fyp", "#viral"])
    return moments


# ---------- Sous-titres mot par mot (ASS) ----------

def _ass_time(t: float) -> str:
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02}:{t % 60:05.2f}"


def _esc(s: str) -> str:
    return s.replace("{", "(").replace("}", ")").replace("\\", "")


LEAD = 0.05  # secondes


def build_ass(transcript: list[dict], start: float, end: float, hook: str | None, path: Path) -> bool:
    """Sous-titres style TikTok : 3 mots max à l'écran, mot actuel en jaune, petite taille,
    placés dans la zone sûre (au-dessus de l'interface de l'appli)."""
    events = []
    for seg in transcript:
        if seg["end"] <= start or seg["start"] >= end:
            continue
        words = seg["text"].split()
        if not words:
            continue
        weights = [len(w) + 1.5 + (2 if re.search(r"[,.!?;:]$", w) else 0) for w in words]
        total, t = sum(weights), seg["start"]
        timed = []
        for w, wt in zip(words, weights):
            d = (seg["end"] - seg["start"]) * wt / total
            timed.append((w, t, t + d))
            t += d
        # groupes de 3 mots, coupés après la ponctuation
        chunks, cur = [], []
        for item in timed:
            cur.append(len(cur))
            if len(cur) == 3 or re.search(r"[.!?,;:]$", item[0]):
                chunks.append(cur)
                cur = []
        if cur:
            chunks.append(cur)
        # chaque mot dure jusqu'au début du suivant : jamais deux lignes en même temps
        ends = [timed[k + 1][1] if k + 1 < len(timed) else seg["end"] for k in range(len(timed))]
        k = 0
        for ch in chunks:
            idx = list(range(k, k + len(ch)))
            k += len(ch)
            for i in idx:
                a, b = timed[i][1] - start - LEAD, ends[i] - start - LEAD  # léger avance : on lit avant d'entendre
                if b <= 0 or a >= end - start:
                    continue
                line = " ".join(
                    ("{\\c&H00D7FF&}" + _esc(timed[x][0]) + "{\\c&HFFFFFF&}") if x == i else _esc(timed[x][0])
                    for x in idx)
                events.append(f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},Cap,,0,0,0,,{line}")
    if hook:
        h = _esc(hook.upper())
        events.append(f"Dialogue: 1,{_ass_time(0)},{_ass_time(3.5)},Hook,,0,0,0,,{{\\fad(200,250)}}{h}")
    if not events:
        return False
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n"
        "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
        "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,"
        "MarginL,MarginR,MarginV,Encoding\n"
        # sous-titres : petits (58 px), contour noir épais, zone sûre (MarginV 480)
        "Style: Cap,Arial,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,1,2,90,90,480,1\n"
        # accroche : haut de l'écran, fond semi-transparent
        "Style: Hook,Arial,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&HB4000000,-1,0,0,0,100,100,0,0,3,22,0,8,90,90,300,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
        + "\n".join(events) + "\n", encoding="utf-8")
    return True


def render_clip(video: Path, moment: dict, out: Path, transcript: list[dict] | None = None,
                mode: str = "blur", captions: bool = True, hook: bool = True) -> Path:
    """mode 'crop' = recadrage centré ; 'blur' = vidéo entière sur fond flouté."""
    start, end = moment["start"], moment["end"]
    dur = end - start
    if mode == "crop":
        vf = "crop=ih*9/16:ih,scale=1080:1920"
    else:
        vf = ("split[a][b];[a]scale=270:480:force_original_aspect_ratio=increase,"
              "crop=270:480,boxblur=6:2,scale=1080:1920[bg];[b]scale=1080:-2[fg];"
              "[bg][fg]overlay=(W-w)/2:(H-h)/2")
    ass = out.with_suffix(".ass")
    hook_text = (moment.get("hook") or "") if hook else None
    if (captions and transcript or hook_text) and build_ass(
            transcript if captions else [], start, end, hook_text or None, ass):
        vf += f",ass={ass.name}"
    af = f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:d=0.1,afade=t=out:st={max(dur - 0.25, 0):.2f}:d=0.25"
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(video.resolve()),
           "-filter_complex" if mode == "blur" else "-vf", vf, "-af", af,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-r", "30",
           "-profile:v", "high", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
           "-movflags", "+faststart", out.name]
    subprocess.run(cmd, check=True, cwd=out.parent)
    return out


def process(url: str, n=5, length=35, mode="blur", captions=True, hook=True, post_style="satisfying", log=print) -> list[dict]:
    log("Téléchargement…")
    video, info = download(url)
    log("Transcription…")
    transcript = get_transcript(url)
    log("Détection des moments clés…")
    moments = find_moments(video, info, transcript, n, length)
    from posts import make_post
    for i, m in enumerate(moments):  # textes de publication en anglais selon la niche
        p = make_post(post_style, i, seed=hash((video_id(url), i)) & 0xFFFF)
        if p:
            m["post"] = p
    outdir = WORK / "clips" / video_id(url)
    outdir.mkdir(parents=True, exist_ok=True)

    def job(i_m):
        i, m = i_m
        m["file"] = str(render_clip(video, m, outdir / f"short_{i}.mp4", transcript, mode, captions, hook))
        log(f"Clip {i}/{len(moments)} prêt")
        return m

    log(f"Rendu de {len(moments)} clips…")
    with ThreadPoolExecutor(max_workers=2) as ex:
        moments = list(ex.map(job, enumerate(moments, 1)))
    (outdir / "moments.json").write_text(
        json.dumps({"title": info["title"], "moments": moments}, ensure_ascii=False, indent=2), encoding="utf-8")
    return moments
