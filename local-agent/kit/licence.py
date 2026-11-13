"""Licence de Photo Studio IA : essai gratuit, puis clé de licence vendue par Lemon Squeezy.

Réglages dans licence-config.json (à côté de ce fichier) :
  enabled     : false tant que la boutique n'est pas prête (l'application reste alors libre)
  store_id    : numéro de la boutique Lemon Squeezy (les clés d'une autre boutique sont refusées)
  product_id  : numéro du produit (facultatif, pour n'accepter que les clés de ce produit)
  buy_url     : lien d'achat affiché dans l'application
  trial_days  : jours d'essai gratuit
La clé est vérifiée en ligne à l'activation, puis de temps en temps ; sans internet, l'application continue de marcher.
"""

import json
import os
import platform
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = os.environ.get("LEMONSQUEEZY_API", "https://api.lemonsqueezy.com/v1/licenses")
RECHECK_DAYS = 7


def config():
    try:
        c = json.loads((HERE / "licence-config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        c = {}
    return {"enabled": bool(c.get("enabled")), "store_id": c.get("store_id"), "product_id": c.get("product_id"),
            "buy_url": c.get("buy_url") or "", "trial_days": int(c.get("trial_days") or 7)}


def _file():
    return Path(os.environ["JARVIS_HOME"]) / "licence.json"


def _load():
    try:
        return json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(d):
    _file().write_text(json.dumps(d), encoding="utf-8")


def _call(action, **params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"{API}/{action}", data=data, headers={
        "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "PhotoStudioIA"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:   # Lemon Squeezy répond 400/404 avec un message d'erreur en JSON
        try:
            return json.loads(e.read())
        except ValueError:
            raise RuntimeError(f"le serveur de licences a répondu {e.code}")


def _ours(meta, c):
    if c["store_id"] and str((meta or {}).get("store_id")) != str(c["store_id"]):
        return False
    if c["product_id"] and str((meta or {}).get("product_id")) != str(c["product_id"]):
        return False
    return True


def status():
    c = config()
    d = _load()
    if not d.get("first_run"):
        d["first_run"] = int(time.time())
        _save(d)
    left = max(0, c["trial_days"] - int((time.time() - d["first_run"]) / 86400))
    licensed = bool(d.get("key") and d.get("instance_id"))
    return {"enabled": c["enabled"], "licensed": licensed, "trial_left": left, "buy_url": c["buy_url"],
            "allowed": (not c["enabled"]) or licensed or left > 0,
            "key_hint": (d.get("key") or "")[-4:] if licensed else ""}


def activate(key):
    key = (key or "").strip()
    if len(key) < 8:
        raise ValueError("Colle la clé de licence reçue par e-mail après l'achat.")
    c = config()
    r = _call("activate", license_key=key, instance_name=f"{platform.node() or 'PC'} (Photo Studio IA)")
    if not r.get("activated"):
        raise ValueError("Clé refusée : " + (r.get("error") or "clé inconnue ou déjà utilisée sur le nombre maximal de PC."))
    if not _ours(r.get("meta"), c):
        raise ValueError("Cette clé ne correspond pas à Photo Studio IA.")
    d = _load()
    d.update(key=key, instance_id=(r.get("instance") or {}).get("id"), checked=int(time.time()))
    _save(d)
    return status()


def deactivate():
    d = _load()
    if d.get("key") and d.get("instance_id"):
        try:
            _call("deactivate", license_key=d["key"], instance_id=d["instance_id"])
        except Exception:
            pass   # hors ligne : on libère quand même ce PC
    for k in ("key", "instance_id", "checked"):
        d.pop(k, None)
    _save(d)
    return status()


def recheck():
    """Vérification périodique (remboursement, clé désactivée…). Sans internet : on ne bloque personne."""
    c, d = config(), _load()
    if not (c["enabled"] and d.get("key") and d.get("instance_id")):
        return
    if time.time() - d.get("checked", 0) < RECHECK_DAYS * 86400:
        return
    try:
        r = _call("validate", license_key=d["key"], instance_id=d["instance_id"])
    except Exception:
        return
    if r.get("valid") and _ours(r.get("meta"), c):
        d["checked"] = int(time.time())
        _save(d)
    elif r.get("error") or r.get("valid") is False:
        for k in ("key", "instance_id", "checked"):
            d.pop(k, None)
        _save(d)
