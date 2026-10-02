"""Rappels et tâches planifiées (actifs tant que Jarvis est ouvert)."""

import datetime
import json
import re
import threading
import time
import uuid

from .config import HOME

FILE = HOME / "taches.json"
_lock = threading.Lock()
REPEATS = {"aucune": None, "horaire": datetime.timedelta(hours=1),
           "quotidienne": datetime.timedelta(days=1), "hebdomadaire": datetime.timedelta(weeks=1)}


def _load():
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _save(items):
    HOME.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def parse_when(text, now=None):
    """Accepte : +20m, +2h, +1j, 14:30, demain 8:00, 2026-10-01 09:00, 01/10/2026 09:00."""
    now = now or datetime.datetime.now()
    t = text.strip().lower()
    m = re.fullmatch(r"\+\s*(\d+)\s*(m|min|h|j|d)", t)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        return now + {"m": datetime.timedelta(minutes=n), "min": datetime.timedelta(minutes=n),
                      "h": datetime.timedelta(hours=n)}.get(unit, datetime.timedelta(days=n))
    tomorrow = t.startswith("demain")
    t = t.replace("demain", "").strip()
    m = re.fullmatch(r"(\d{1,2})[:h](\d{2})?", t)
    if m:
        when = now.replace(hour=int(m.group(1)), minute=int(m.group(2) or 0), second=0, microsecond=0)
        if tomorrow:
            when += datetime.timedelta(days=1)
        elif when <= now:
            when += datetime.timedelta(days=1)
        return when
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(t, fmt)
        except ValueError:
            pass
    raise ValueError("Format de date non reconnu. Exemples : +20m, +2h, 14:30, demain 8:00, 2026-10-01 09:00")


def add(task, when, repeat="aucune", kind="rappel"):
    if repeat not in REPEATS:
        raise ValueError(f"repeat doit être l'un de : {', '.join(REPEATS)}")
    if kind not in ("rappel", "tache"):
        raise ValueError("kind doit être 'rappel' ou 'tache'")
    at = parse_when(when)
    item = {"id": uuid.uuid4().hex[:6], "task": task, "at": at.isoformat(timespec="minutes"),
            "repeat": repeat, "kind": kind}
    with _lock:
        items = _load()
        items.append(item)
        _save(items)
    return item


def remove(item_id):
    with _lock:
        items = _load()
        kept = [i for i in items if i["id"] != item_id]
        _save(kept)
    return len(kept) != len(items)


def listing():
    return sorted(_load(), key=lambda i: i["at"])


def pop_due(now=None):
    """Renvoie les éléments arrivés à échéance et reprogramme ceux qui se répètent."""
    now = now or datetime.datetime.now()
    due = []
    with _lock:
        items = _load()
        keep = []
        for i in items:
            at = datetime.datetime.fromisoformat(i["at"])
            if at > now:
                keep.append(i)
                continue
            due.append(i)
            step = REPEATS.get(i["repeat"])
            if step:
                while at <= now:
                    at += step
                keep.append({**i, "at": at.isoformat(timespec="minutes")})
        if due:
            _save(keep)
    return due


def start(on_due, interval=20):
    """Lance la surveillance en arrière-plan. on_due(item) est appelé pour chaque échéance."""
    def loop():
        while True:
            for item in pop_due():
                try:
                    on_due(item)
                except Exception as e:  # une erreur ne doit jamais arrêter le planificateur
                    print("Erreur planificateur :", e)
            time.sleep(interval)
    threading.Thread(target=loop, daemon=True).start()
