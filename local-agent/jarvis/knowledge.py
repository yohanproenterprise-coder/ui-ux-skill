"""Base de connaissances : indexe des dossiers de documents et y cherche (algorithme BM25)."""

import json
import math
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path

from .config import HOME

FILE = HOME / "connaissances.json"
TEXT_EXT = {".txt", ".md", ".csv", ".json", ".html", ".htm", ".xml", ".py", ".js", ".css", ".log", ".ini", ".rtf"}
DOC_EXT = {".pdf", ".docx", ".pptx", ".xlsx", ".odt", ".ods", ".odp"}
STOP = set("""le la les un une des du de d l et ou a au aux en dans sur pour par avec sans ce ces cet cette
qui que quoi dont ou est sont etre avoir ai as a ont il elle ils elles je tu nous vous on ne pas plus
se sa son ses leur leurs mon ma mes ton ta tes the of and to in is for on with as by at an be this that""".split())
MAX_CHUNKS = 30000


def tokens(text):
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return [w for w in re.findall(r"[a-z0-9]{2,}", text) if w not in STOP]


def _load():
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"chunks": []}


def index_folder(root, extract, chunk_size=1200):
    """extract(path) -> texte. Remplace l'index existant de ce dossier."""
    root = Path(root).resolve()
    data = _load()
    data["chunks"] = [c for c in data["chunks"] if not c["src"].startswith(str(root))]
    files = errors = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
        for name in filenames:
            p = Path(dirpath, name)
            ext = p.suffix.lower()
            if ext not in TEXT_EXT | DOC_EXT or p.stat().st_size > 30_000_000:
                continue
            try:
                text = extract(p) if ext in DOC_EXT else p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                errors += 1
                continue
            if not text or text.startswith("ERREUR"):
                errors += 1
                continue
            files += 1
            for start in range(0, len(text), chunk_size - 200):
                piece = text[start:start + chunk_size].strip()
                if len(piece) > 40:
                    data["chunks"].append({"src": str(p), "text": piece, "tf": Counter(tokens(piece))})
            if len(data["chunks"]) > MAX_CHUNKS:
                break
    HOME.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return files, errors, len(data["chunks"])


def search(query, k=6):
    chunks = _load()["chunks"]
    if not chunks:
        return []
    q = set(tokens(query))
    n = len(chunks)
    avg = sum(sum(c["tf"].values()) for c in chunks) / n or 1
    df = Counter(t for c in chunks for t in q if t in c["tf"])
    scored = []
    for c in chunks:
        length = sum(c["tf"].values()) or 1
        score = 0.0
        for t in q:
            f = c["tf"].get(t, 0)
            if f:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                score += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * length / avg))
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:k]]


def sources():
    return sorted({c["src"] for c in _load()["chunks"]})
