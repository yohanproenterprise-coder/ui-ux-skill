"""Accès depuis le téléphone : code PIN, appareils autorisés, adresses du PC, icône d'application."""

import hashlib
import hmac
import json
import secrets
import socket
import struct
import time
import zlib

from .config import HOME

DEVICES_FILE = HOME / "appareils.json"
MAX_FAILS, LOCK_SECONDS = 5, 300
_fails = {"count": 0, "until": 0.0}


def enabled(cfg):
    r = cfg.get("remote") or {}
    return bool(r.get("enabled") and r.get("pin_hash"))


def _hash(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 200_000).hex()


def set_pin(cfg, pin):
    pin = (pin or "").strip()
    if not pin.isdigit() or len(pin) < 6:
        raise ValueError("Le code PIN doit contenir au moins 6 chiffres.")
    salt = secrets.token_hex(16)
    cfg.setdefault("remote", {}).update({"salt": salt, "pin_hash": _hash(pin, salt)})
    _save_devices({})  # nouveau code : tous les appareils doivent se reconnecter


def check_pin(cfg, pin):
    """Renvoie (ok, message). Bloque 5 minutes après 5 essais ratés."""
    now = time.time()
    if now < _fails["until"]:
        return False, f"Trop d'essais. Réessaie dans {int(_fails['until'] - now) // 60 + 1} min."
    r = cfg.get("remote") or {}
    if r.get("pin_hash") and hmac.compare_digest(_hash(str(pin or ""), r["salt"]), r["pin_hash"]):
        _fails["count"] = 0
        return True, ""
    _fails["count"] += 1
    if _fails["count"] >= MAX_FAILS:
        _fails.update(count=0, until=now + LOCK_SECONDS)
        return False, "Trop d'essais. Accès bloqué 5 minutes."
    return False, f"Code incorrect ({MAX_FAILS - _fails['count']} essais restants)."


def _load_devices():
    try:
        return json.loads(DEVICES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_devices(devices):
    HOME.mkdir(parents=True, exist_ok=True)
    DEVICES_FILE.write_text(json.dumps(devices, indent=1), encoding="utf-8")


def new_token(user_agent=""):
    token = secrets.token_hex(24)
    devices = _load_devices()
    devices[hashlib.sha256(token.encode()).hexdigest()] = {"since": time.strftime("%Y-%m-%d %H:%M"),
                                                          "device": user_agent[:120]}
    _save_devices(devices)
    return token


def token_ok(token):
    return bool(token) and hashlib.sha256(token.encode()).hexdigest() in _load_devices()


def addresses(port):
    """Adresses auxquelles le téléphone peut joindre le PC."""
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))  # aucun paquet n'est envoyé : sert à connaître l'IP locale
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    out = []
    for ip in sorted(ips):
        if ip.startswith("127.") or ip.startswith("169.254."):
            continue
        first, second = (int(x) for x in ip.split(".")[:2])
        kind = "partout, via Tailscale" if first == 100 and 64 <= second < 128 else "même Wi-Fi"
        out.append({"url": f"http://{ip}:{port}", "kind": kind})
    return out


def icon_png(size):
    """Icône de l'application (carré bleu arrondi avec un anneau blanc), en PNG, sans dépendance."""
    rows = []
    c, radius = size / 2, size * 0.22
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            dx, dy = max(abs(x - c + .5) - (c - radius), 0), max(abs(y - c + .5) - (c - radius), 0)
            inside = dx * dx + dy * dy <= radius * radius
            d = ((x - c + .5) ** 2 + (y - c + .5) ** 2) ** .5
            if not inside:
                row += bytes((0, 0, 0, 0))
            elif size * 0.24 <= d <= size * 0.31 or d <= size * 0.09:
                row += bytes((255, 255, 255, 255))
            else:
                t = y / size
                row += bytes((int(47 + 30 * t), int(111 - 40 * t), int(219 - 10 * t), 255))
        rows.append(bytes(row))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))
