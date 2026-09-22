"""Configuration de Jarvis : fournisseurs de modèles, clés, préférences."""

import copy
import json
import os
from pathlib import Path

HOME = Path(os.environ.get("JARVIS_HOME", Path.home() / ".jarvis"))
CONFIG_FILE = HOME / "config.json"
MEMORY_FILE = HOME / "memoire.md"
SESSIONS_DIR = HOME / "sessions"
CAPTURES_DIR = HOME / "captures"

# "ctx" = fenêtre de contexte en tokens. 8192 est un bon maximum pour 8 Go de RAM.
PROVIDERS = {
    "local": {
        "type": "ollama", "base_url": "http://localhost:11434",
        "model": "qwen3:4b", "vision_model": "qwen2.5vl:3b", "ctx": 8192,
    },
    "gemini": {
        "type": "openai", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.5-flash", "vision_model": None, "ctx": 200000,
        "key_url": "https://aistudio.google.com/apikey",
    },
    "groq": {
        "type": "openai", "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-120b", "vision_model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "ctx": 100000, "key_url": "https://console.groq.com/keys",
    },
    "openrouter": {
        "type": "openai", "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-oss-120b:free", "vision_model": None, "ctx": 100000,
        "key_url": "https://openrouter.ai/settings/keys",
    },
}

DEFAULTS = {
    "provider": "local",       # cerveau principal
    "fallback": "local",       # utilisé si le principal est indisponible (quota, réseau…)
    "providers": PROVIDERS,
    "api_keys": {},
    "workdir": str(Path.home() / "Jarvis"),
    "auto": False,             # exécuter sans demander de confirmation
    "speak": False,            # lire les réponses à voix haute
    "think": False,            # mode « réflexion » des modèles locaux (plus lent)
    "max_steps": 60,
}


def _merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def load():
    cfg = copy.deepcopy(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            _merge(cfg, json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as e:
            print(f"Attention : config.json illisible ({e}), valeurs par défaut utilisées.")
    for name in cfg["providers"]:
        env = os.environ.get(f"{name.upper()}_API_KEY")
        if env:
            cfg["api_keys"][name] = env
    return cfg


def save(cfg):
    HOME.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def available(cfg, name):
    """Un fournisseur cloud n'est utilisable que si sa clé est configurée."""
    p = cfg["providers"].get(name)
    return bool(p) and (p["type"] == "ollama" or bool(cfg["api_keys"].get(name)))
