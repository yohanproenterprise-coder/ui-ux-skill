#!/usr/bin/env python3
"""
Jarvis local — agent IA autonome qui tourne 100 % en local via Ollama.

Aucune dépendance externe : uniquement la bibliothèque standard Python (3.9+).
Outils : shell, fichiers (lire / écrire / éditer / lister / chercher),
web (recherche + lecture de pages), mémoire persistante, plan de tâches.
La conversation est automatiquement résumée quand elle approche de la
limite de contexte du modèle : les sessions peuvent donc durer indéfiniment.
"""

import argparse
import datetime
import fnmatch
import html
import json
import os
import platform
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("JARVIS_HOME", Path.home() / ".jarvis"))
MEMORY_FILE = HOME / "memoire.md"
SESSIONS_DIR = HOME / "sessions"
MAX_TOOL_OUTPUT = 12000  # caractères renvoyés au modèle par appel d'outil

# ----------------------------------------------------------------- couleurs --
if os.name == "nt":
    os.system("")  # active les séquences ANSI dans la console Windows
C = {"dim": "\033[2m", "cyan": "\033[36m", "yellow": "\033[33m",
     "green": "\033[32m", "red": "\033[31m", "bold": "\033[1m", "reset": "\033[0m"}


def say(text, color="reset", end="\n"):
    print(f"{C[color]}{text}{C['reset']}", end=end, flush=True)


# --------------------------------------------------------------- ollama API --
class Ollama:
    def __init__(self, host, model, num_ctx):
        self.host = host.rstrip("/")
        self.model = model
        self.num_ctx = num_ctx

    def _post(self, path, payload):
        req = urllib.request.Request(
            self.host + path, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req, timeout=600)

    def chat(self, messages, tools=None, stream=True, on_token=None):
        payload = {"model": self.model, "messages": messages, "stream": stream,
                   "options": {"num_ctx": self.num_ctx}}
        if tools:
            payload["tools"] = tools
        content, thinking, tool_calls = "", "", []
        with self._post("/api/chat", payload) as resp:
            for line in resp:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if "error" in chunk:
                    raise RuntimeError(chunk["error"])
                msg = chunk.get("message", {})
                if msg.get("thinking"):
                    thinking += msg["thinking"]
                if msg.get("content"):
                    content += msg["content"]
                    if on_token:
                        on_token(msg["content"])
                tool_calls += msg.get("tool_calls") or []
                if chunk.get("done"):
                    break
        return {"role": "assistant", "content": content, "tool_calls": tool_calls}

    def check(self):
        try:
            with urllib.request.urlopen(self.host + "/api/tags", timeout=5) as r:
                names = [m["name"] for m in json.load(r).get("models", [])]
        except Exception:
            sys.exit(f"Impossible de joindre Ollama sur {self.host}. "
                     "Lance d'abord l'application Ollama (ou `ollama serve`).")
        base = self.model if ":" in self.model else self.model + ":latest"
        if base not in names and self.model not in names:
            sys.exit(f"Le modèle '{self.model}' n'est pas installé.\n"
                     f"Installe-le avec :  ollama pull {self.model}\n"
                     f"Modèles disponibles : {', '.join(names) or 'aucun'}")


# ------------------------------------------------------------------- outils --
class Tools:
    def __init__(self, auto, workdir):
        self.auto = auto
        self.workdir = Path(workdir).resolve()
        self.plan = []

    def _path(self, p):
        p = Path(os.path.expanduser(p))
        return p if p.is_absolute() else self.workdir / p

    def _confirm(self, action):
        if self.auto:
            return True
        say(f"\n  ⚠  {action}", "yellow")
        ans = input(f"{C['yellow']}  Autoriser ? [o]ui / [n]on / [t]oujours : {C['reset']}")
        ans = ans.strip().lower()
        if ans in ("t", "toujours", "a", "always"):
            self.auto = True
            return True
        return ans in ("o", "oui", "y", "yes", "")

    # --- shell
    def run_command(self, command, timeout=300):
        if not self._confirm(f"Commande : {command}"):
            return "REFUSÉ par l'utilisateur."
        try:
            r = subprocess.run(command, shell=True, cwd=self.workdir, capture_output=True,
                               text=True, timeout=timeout, encoding="utf-8", errors="replace")
            out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr else "")
            return f"[code de sortie {r.returncode}]\n{out.strip()}"
        except subprocess.TimeoutExpired:
            return f"ERREUR : délai de {timeout}s dépassé."

    # --- fichiers
    def read_file(self, path, start_line=1, end_line=None):
        lines = self._path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        end = end_line or len(lines)
        body = "\n".join(f"{i:>5}  {l}" for i, l in enumerate(lines[start_line - 1:end], start_line))
        return f"({len(lines)} lignes au total)\n{body}"

    def write_file(self, path, content):
        p = self._path(path)
        if not self._confirm(f"Écrire {p} ({len(content)} caractères)"):
            return "REFUSÉ par l'utilisateur."
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Fichier écrit : {p}"

    def edit_file(self, path, old_text, new_text):
        p = self._path(path)
        text = p.read_text(encoding="utf-8")
        count = text.count(old_text)
        if count == 0:
            return "ERREUR : old_text introuvable. Relis le fichier et copie le texte exact."
        if count > 1:
            return f"ERREUR : old_text apparaît {count} fois. Ajoute du contexte pour le rendre unique."
        if not self._confirm(f"Modifier {p}"):
            return "REFUSÉ par l'utilisateur."
        p.write_text(text.replace(old_text, new_text), encoding="utf-8")
        return f"Fichier modifié : {p}"

    def list_dir(self, path=".", pattern="*"):
        root = self._path(path)
        skip = {".git", "node_modules", "__pycache__", ".venv", "venv"}
        out = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            for f in filenames:
                if fnmatch.fnmatch(f, pattern):
                    out.append(str(Path(dirpath, f).relative_to(root)))
            if len(out) > 500:
                out.append("… (tronqué)")
                break
        return "\n".join(sorted(out)) or "(aucun fichier)"

    def search_files(self, regex, path=".", pattern="*"):
        rx = re.compile(regex)
        root = self._path(path)
        hits = []
        for rel in self.list_dir(path, pattern).splitlines():
            f = root / rel
            if not f.is_file() or f.stat().st_size > 2_000_000:
                continue
            try:
                for n, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if rx.search(line):
                        hits.append(f"{rel}:{n}: {line.strip()[:200]}")
            except OSError:
                continue
            if len(hits) > 200:
                break
        return "\n".join(hits) or "(aucun résultat)"

    # --- web
    @staticmethod
    def _get(url):
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Jarvis-local/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode(r.headers.get_content_charset() or "utf-8", errors="replace")

    def web_search(self, query):
        page = self._get("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query))
        results = re.findall(
            r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>',
            page, re.S)
        out = []
        for href, title, snippet in results[:8]:
            m = re.search(r"uddg=([^&]+)", href)
            url = urllib.parse.unquote(m.group(1)) if m else href
            clean = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).strip()
            out.append(f"- {clean(title)}\n  {url}\n  {clean(snippet)}")
        return "\n".join(out) or "(aucun résultat)"

    def fetch_url(self, url):
        page = self._get(url)
        page = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", "", page)
        page = re.sub(r"(?i)<br\s*/?>|</(p|div|h\d|li|tr)>", "\n", page)
        text = html.unescape(re.sub(r"<[^>]+>", "", page))
        return re.sub(r"\n\s*\n+", "\n\n", text).strip()

    # --- mémoire & plan
    def remember(self, fact):
        HOME.mkdir(parents=True, exist_ok=True)
        with MEMORY_FILE.open("a", encoding="utf-8") as f:
            f.write(f"- {fact}\n")
        return "Mémorisé."

    def update_plan(self, steps):
        self.plan = steps
        icons = {"fait": "✔", "en_cours": "▶", "a_faire": "○"}
        say("\n  Plan :", "cyan")
        for s in steps:
            say(f"   {icons.get(s.get('statut'), '○')} {s.get('etape')}", "cyan")
        return "Plan mis à jour."

    def call(self, name, args):
        fn = getattr(self, name, None)
        if fn is None or name.startswith("_") or name == "call":
            return f"ERREUR : outil inconnu '{name}'."
        try:
            result = str(fn(**args))
        except Exception as e:  # on renvoie l'erreur au modèle pour qu'il se corrige
            result = f"ERREUR : {type(e).__name__}: {e}"
        if len(result) > MAX_TOOL_OUTPUT:
            result = result[:MAX_TOOL_OUTPUT] + f"\n… (tronqué, {len(result)} caractères au total)"
        return result


def _tool(name, desc, props, required=()):
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props, "required": list(required)}}}


S, I = {"type": "string"}, {"type": "integer"}
TOOL_SPECS = [
    _tool("run_command", "Exécute une commande shell dans le dossier de travail et renvoie stdout/stderr. "
          "Sert à installer, compiler, tester, lancer des scripts, utiliser git, etc.",
          {"command": S, "timeout": I}, ["command"]),
    _tool("read_file", "Lit un fichier texte (avec numéros de ligne).",
          {"path": S, "start_line": I, "end_line": I}, ["path"]),
    _tool("write_file", "Crée ou remplace entièrement un fichier.", {"path": S, "content": S}, ["path", "content"]),
    _tool("edit_file", "Remplace un passage exact et unique d'un fichier par un nouveau texte.",
          {"path": S, "old_text": S, "new_text": S}, ["path", "old_text", "new_text"]),
    _tool("list_dir", "Liste récursivement les fichiers d'un dossier (motif glob optionnel, ex: *.py).",
          {"path": S, "pattern": S}),
    _tool("search_files", "Cherche une expression régulière dans les fichiers d'un dossier.",
          {"regex": S, "path": S, "pattern": S}, ["regex"]),
    _tool("web_search", "Recherche sur le web (DuckDuckGo). Renvoie titres, liens et extraits.",
          {"query": S}, ["query"]),
    _tool("fetch_url", "Télécharge une page web et renvoie son texte lisible.", {"url": S}, ["url"]),
    _tool("remember", "Enregistre un fait durable sur l'utilisateur ou ses projets (mémoire entre sessions).",
          {"fact": S}, ["fact"]),
    _tool("update_plan", "Définit ou met à jour le plan d'une tâche en plusieurs étapes.",
          {"steps": {"type": "array", "items": {"type": "object", "properties": {
              "etape": S, "statut": {"type": "string", "enum": ["a_faire", "en_cours", "fait"]}}}}},
          ["steps"]),
]


# -------------------------------------------------------------------- agent --
def system_prompt(workdir):
    memory = MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else "(vide)"
    return f"""Tu es Jarvis, un agent IA autonome qui tourne en local sur l'ordinateur de l'utilisateur.
Tu réponds en français sauf demande contraire.

Environnement : {platform.system()} {platform.release()} — Python {platform.python_version()}
Dossier de travail : {workdir}
Date : {datetime.date.today().isoformat()}

Méthode de travail :
1. Pour une tâche en plusieurs étapes, commence par update_plan, puis tiens le plan à jour.
2. Agis avec les outils au lieu de décrire ce que l'utilisateur devrait faire. Explore avant de modifier :
   lis les fichiers avant de les éditer, vérifie ce qui existe.
3. Après une modification, vérifie qu'elle fonctionne (lance le code, les tests, relis le résultat).
4. Si un outil renvoie une erreur, analyse-la et corrige ton approche. N'invente jamais un résultat.
5. Pour une information récente ou incertaine, utilise web_search puis fetch_url.
6. Quand tu apprends quelque chose de durable sur l'utilisateur, utilise remember.
7. Termine par un résumé court et honnête de ce qui a été fait et de ce qui reste.

Mémoire à long terme :
{memory}"""


class Agent:
    def __init__(self, llm, tools, workdir, max_steps):
        self.llm, self.tools, self.max_steps = llm, tools, max_steps
        self.messages = [{"role": "system", "content": system_prompt(workdir)}]
        self.session_file = SESSIONS_DIR / f"{datetime.datetime.now():%Y%m%d-%H%M%S}.json"

    def _size(self):
        return sum(len(json.dumps(m, ensure_ascii=False)) for m in self.messages) // 3

    def compact(self, force=False):
        """Résume les anciens échanges pour ne jamais saturer le contexte."""
        if not force and self._size() < self.llm.num_ctx * 0.7:
            return
        keep = 6
        if len(self.messages) <= keep + 2:
            return
        cut = len(self.messages) - keep
        while cut > 1 and self.messages[cut]["role"] == "tool":
            cut -= 1  # ne pas séparer un résultat d'outil de son appel
        old, recent = self.messages[1:cut], self.messages[cut:]
        say("\n  (contexte long : résumé des anciens échanges…)", "dim")
        transcript = "\n".join(f"[{m['role']}] {str(m.get('content', ''))[:2000]}" for m in old)
        summary = self.llm.chat([
            {"role": "system", "content": "Tu résumes des conversations de travail de façon dense et factuelle."},
            {"role": "user", "content": "Résume cet historique : objectifs, décisions, fichiers touchés, "
                                        "résultats, problèmes ouverts et prochaines étapes.\n\n" + transcript}],
            stream=False)["content"]
        self.messages = [self.messages[0],
                         {"role": "user", "content": "[Résumé des échanges précédents]\n" + summary},
                         {"role": "assistant", "content": "Compris, je poursuis à partir de ce résumé."}] + recent

    def save(self):
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.session_file.write_text(json.dumps(self.messages, ensure_ascii=False, indent=1), encoding="utf-8")

    def run(self, user_input):
        self.messages.append({"role": "user", "content": user_input})
        for _ in range(self.max_steps):
            self.compact()
            say("\n", end="")
            reply = self.llm.chat(self.messages, tools=TOOL_SPECS,
                                  on_token=lambda t: say(t, "reset", end=""))
            self.messages.append(reply)
            if not reply["tool_calls"]:
                say("")
                self.save()
                return
            for call in reply["tool_calls"]:
                fn = call.get("function", {})
                name, args = fn.get("name", ""), fn.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                preview = json.dumps(args, ensure_ascii=False)
                say(f"\n  → {name}({preview[:150]}{'…' if len(preview) > 150 else ''})", "dim")
                result = self.tools.call(name, args)
                say("    " + result[:300].replace("\n", "\n    ") + ("…" if len(result) > 300 else ""), "dim")
                self.messages.append({"role": "tool", "tool_name": name, "content": result})
            self.save()
        say(f"\n  (limite de {self.max_steps} étapes atteinte — tape « continue » pour poursuivre)", "yellow")


HELP = """Commandes :
  /aide          cette aide
  /auto          active/désactive l'exécution sans confirmation
  /modele NOM    change de modèle (ex: /modele qwen3:32b)
  /memoire       affiche la mémoire à long terme
  /resume        force le résumé du contexte
  /nouveau       nouvelle conversation
  /quitter       quitter"""


def main():
    ap = argparse.ArgumentParser(description="Jarvis — agent IA local (Ollama)")
    ap.add_argument("tache", nargs="*", help="tâche à exécuter directement (sinon mode interactif)")
    ap.add_argument("-m", "--model", default=os.environ.get("JARVIS_MODEL", "qwen3:14b"))
    ap.add_argument("--host", default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    ap.add_argument("--ctx", type=int, default=int(os.environ.get("JARVIS_CTX", 32768)),
                    help="taille de contexte en tokens (dépend de ta RAM/VRAM)")
    ap.add_argument("-d", "--dir", default=os.getcwd(), help="dossier de travail")
    ap.add_argument("--auto", action="store_true", help="ne demande pas de confirmation (prudence !)")
    ap.add_argument("--max-steps", type=int, default=50)
    a = ap.parse_args()
    if not a.host.startswith("http"):
        a.host = "http://" + a.host

    llm = Ollama(a.host, a.model, a.ctx)
    llm.check()
    tools = Tools(a.auto, a.dir)
    agent = Agent(llm, tools, tools.workdir, a.max_steps)

    if a.tache:
        agent.run(" ".join(a.tache))
        return

    say(f"Jarvis local — modèle {a.model} — dossier {tools.workdir}", "bold")
    say("Tape ta demande. /aide pour les commandes.", "dim")
    while True:
        try:
            text = input(f"\n{C['green']}{C['bold']}toi › {C['reset']}").strip()
        except (EOFError, KeyboardInterrupt):
            say("\nÀ bientôt !")
            return
        if not text:
            continue
        cmd, _, arg = text.partition(" ")
        if cmd in ("/quitter", "/exit", "/q"):
            return
        elif cmd == "/aide":
            say(HELP, "cyan")
        elif cmd == "/auto":
            tools.auto = not tools.auto
            say(f"Mode auto : {'ACTIVÉ' if tools.auto else 'désactivé'}", "yellow")
        elif cmd == "/modele" and arg:
            llm.model = arg.strip()
            llm.check()
            say(f"Modèle : {llm.model}", "cyan")
        elif cmd == "/memoire":
            say(MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else "(vide)", "cyan")
        elif cmd == "/resume":
            agent.compact(force=True)
        elif cmd == "/nouveau":
            agent = Agent(llm, tools, tools.workdir, a.max_steps)
            say("Nouvelle conversation.", "cyan")
        else:
            try:
                agent.run(text)
            except KeyboardInterrupt:
                say("\n  (interrompu)", "yellow")
            except Exception as e:
                say(f"\n  Erreur : {e}", "red")


if __name__ == "__main__":
    main()
