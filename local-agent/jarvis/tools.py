"""Outils que le modèle peut appeler."""

import base64
import datetime
import fnmatch
import html
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from . import system
from .config import CAPTURES_DIR, HOME, MEMORY_FILE

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "$RECYCLE.BIN"}
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp"}


class Tools:
    def __init__(self, workdir, ui, brain, auto=False, spawn=None):
        self.workdir = Path(workdir).expanduser().resolve()
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.ui, self.brain, self.auto = ui, brain, auto
        self.spawn = spawn  # fabrique de sous-agent (None dans un sous-agent)

    def _path(self, p):
        p = Path(os.path.expanduser(str(p)))
        return p if p.is_absolute() else self.workdir / p

    def _confirm(self, action):
        if self.auto:
            return True
        answer = self.ui.confirm(action)
        if answer == "always":
            self.auto = True
        return bool(answer)

    # ------------------------------------------------------------ exécution --
    def run_command(self, command, timeout=300):
        if not self._confirm(f"Commande : {command}"):
            return "REFUSÉ par l'utilisateur."
        try:
            if system.WINDOWS:
                code, out = system.powershell("Set-Location -LiteralPath '" + str(self.workdir).replace("'", "''") + "';" + command,
                                              timeout=timeout)
            else:
                r = subprocess.run(command, shell=True, cwd=self.workdir, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=timeout)
                code, out = r.returncode, ((r.stdout or "") + ("\n[stderr]\n" + r.stderr if r.stderr else ""))
            return f"[code de sortie {code}]\n{out.strip()}"
        except subprocess.TimeoutExpired:
            return f"ERREUR : délai de {timeout}s dépassé."

    def run_python(self, code, timeout=300):
        if not self._confirm("Exécuter du Python :\n" + code[:800]):
            return "REFUSÉ par l'utilisateur."
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
        try:
            r = subprocess.run([sys.executable, f.name], cwd=self.workdir, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=timeout,
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            return f"[code de sortie {r.returncode}]\n{r.stdout}" + (f"\n[stderr]\n{r.stderr}" if r.stderr else "")
        except subprocess.TimeoutExpired:
            return f"ERREUR : délai de {timeout}s dépassé."
        finally:
            os.unlink(f.name)

    # ------------------------------------------------------------- fichiers --
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

    def list_dir(self, path=".", pattern="*", max_depth=6):
        root = self._path(path)
        out = []
        for dirpath, dirnames, filenames in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            dirnames[:] = [] if depth >= max_depth else [d for d in dirnames if d not in SKIP_DIRS]
            out += [str(Path(dirpath, f).relative_to(root)) for f in filenames if fnmatch.fnmatch(f, pattern)]
            if len(out) > 500:
                out.append("… (tronqué)")
                break
        return "\n".join(sorted(out)) or "(aucun fichier)"

    def search_files(self, regex, path=".", pattern="*"):
        rx = re.compile(regex, re.I)
        root = self._path(path)
        hits = []
        for rel in self.list_dir(path, pattern).splitlines():
            f = root / rel
            if not f.is_file() or f.stat().st_size > 2_000_000:
                continue
            try:
                with f.open("rb") as fh:
                    if b"\0" in fh.read(2048):
                        continue  # fichier binaire
                for n, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if rx.search(line):
                        hits.append(f"{rel}:{n}: {line.strip()[:200]}")
            except OSError:
                continue
            if len(hits) > 200:
                break
        return "\n".join(hits) or "(aucun résultat)"

    def read_document(self, path):
        p = self._path(path)
        ext = p.suffix.lower()
        if ext == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError:
                return "ERREUR : lecture PDF indisponible. Installe-la avec : python -m pip install pypdf"
            pages = PdfReader(str(p)).pages
            return "\n\n".join(f"--- page {i} ---\n{pg.extract_text() or ''}" for i, pg in enumerate(pages, 1))
        if ext in (".docx", ".pptx", ".xlsx", ".odt", ".ods", ".odp"):
            return _office_text(p)
        if ext in IMAGE_TYPES:
            return self.look_at_image(str(p), "Décris cette image en détail et retranscris tout texte visible.")
        return p.read_text(encoding="utf-8", errors="replace")

    # ------------------------------------------------------------------ web --
    @staticmethod
    def _get(url, raw=False):
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            return data if raw else data.decode(r.headers.get_content_charset() or "utf-8", errors="replace")

    def web_search(self, query):
        q = urllib.parse.quote(query)
        clean = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).strip()
        out = []
        try:
            page = self._get("https://html.duckduckgo.com/html/?q=" + q)
            for href, title, snippet in re.findall(
                    r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>',
                    page, re.S)[:8]:
                m = re.search(r"uddg=([^&]+)", href)
                out.append(f"- {clean(title)}\n  {urllib.parse.unquote(m.group(1)) if m else href}\n  {clean(snippet)}")
        except Exception:
            pass
        if not out:  # repli sur la version « lite »
            page = self._get("https://lite.duckduckgo.com/lite/?q=" + q)
            for href, title in re.findall(r"<a[^>]+href=\"([^\"]+)\"[^>]*class=['\"]result-link['\"][^>]*>(.*?)</a>",
                                          page, re.S)[:8]:
                m = re.search(r"uddg=([^&]+)", href)
                out.append(f"- {clean(title)}\n  {urllib.parse.unquote(m.group(1)) if m else href}")
        return "\n".join(out) or "(aucun résultat — reformule ou essaie fetch_url sur un site précis)"

    def fetch_url(self, url):
        page = self._get(url)
        page = re.sub(r"(?is)<(script|style|noscript|svg|head).*?</\1>", "", page)
        page = re.sub(r"(?i)<br\s*/?>|</(p|div|h\d|li|tr|section|article)>", "\n", page)
        text = html.unescape(re.sub(r"<[^>]+>", "", page))
        return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()

    def download_file(self, url, path):
        p = self._path(path)
        if not self._confirm(f"Télécharger {url} vers {p}"):
            return "REFUSÉ par l'utilisateur."
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(self._get(url, raw=True))
        return f"Téléchargé : {p} ({p.stat().st_size} octets)"

    # --------------------------------------------------------- vision & PC --
    def look_at_image(self, path, question="Décris cette image en détail."):
        p = self._path(path)
        mime = IMAGE_TYPES.get(p.suffix.lower())
        if not mime:
            return "ERREUR : format d'image non pris en charge."
        image = {"mime": mime, "data": base64.b64encode(p.read_bytes()).decode()}
        self.ui.info("analyse de l'image…")
        return self.brain.vision(question, image)

    def screenshot(self, question=None):
        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        path = CAPTURES_DIR / f"ecran-{datetime.datetime.now():%Y%m%d-%H%M%S}.png"
        err = system.screenshot(path)
        if err:
            return "ERREUR capture : " + err
        if question:
            return f"Capture : {path}\n" + self.look_at_image(str(path), question)
        return f"Capture enregistrée : {path} (utilise look_at_image pour l'analyser)"

    def open_item(self, target):
        system.open_item(target if re.match(r"^[a-z]+://|^www\.", target) or not self._path(target).exists()
                         else str(self._path(target)))
        return f"Ouvert : {target}"

    def clipboard(self, action="read", text=""):
        if action == "write":
            system.clipboard_set(text)
            return "Copié dans le presse-papiers."
        return system.clipboard_get() or "(presse-papiers vide)"

    def speak(self, text):
        return system.speak(text) or "Dit à voix haute."

    # ------------------------------------------------------ organisation --
    def remember(self, fact):
        HOME.mkdir(parents=True, exist_ok=True)
        with MEMORY_FILE.open("a", encoding="utf-8") as f:
            f.write(f"- {fact}\n")
        return "Mémorisé."

    def update_plan(self, steps):
        self.ui.plan(steps)
        return "Plan mis à jour."

    def delegate(self, task):
        if not self.spawn:
            return "ERREUR : un sous-agent ne peut pas déléguer."
        self.ui.info(f"sous-agent lancé : {task[:80]}")
        return self.spawn(task)

    # ----------------------------------------------------------- dispatch --
    def call(self, name, args, max_chars):
        fn = getattr(self, name, None)
        if name not in TOOL_NAMES or fn is None or (name == "delegate" and not self.spawn):
            return f"ERREUR : outil inconnu '{name}'. Outils disponibles : {', '.join(TOOL_NAMES)}"
        if "_raw" in args:
            return "ERREUR : arguments JSON invalides. Réessaie avec un JSON valide."
        try:
            result = str(fn(**args))
        except TypeError as e:
            result = f"ERREUR : mauvais arguments pour {name} : {e}"
        except Exception as e:  # l'erreur est renvoyée au modèle pour qu'il se corrige
            result = f"ERREUR : {type(e).__name__}: {e}"
        if len(result) > max_chars:
            half = max_chars // 2
            result = f"{result[:half]}\n… ({len(result) - max_chars} caractères coupés) …\n{result[-half:]}"
        return result


def _office_text(p):
    """Extrait le texte d'un fichier Word, PowerPoint, Excel ou OpenDocument sans dépendance."""
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
        read = lambda n: z.read(n).decode("utf-8", "replace")
        text = lambda xml: html.unescape(re.sub(r"<[^>]+>", "", xml))
        ext = p.suffix.lower()
        if ext == ".docx":
            xml = re.sub(r"</w:p>", "\n", read("word/document.xml"))
            return text(re.sub(r"<w:tab/>", "\t", xml)).strip()
        if ext == ".pptx":
            slides = sorted((n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                            key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)))
            return "\n\n".join(f"--- diapo {i} ---\n" + text(re.sub(r"</a:p>", "\n", read(n))).strip()
                               for i, n in enumerate(slides, 1))
        if ext == ".xlsx":
            shared = []
            if "xl/sharedStrings.xml" in names:
                shared = [text(si) for si in re.findall(r"<si>(.*?)</si>", read("xl/sharedStrings.xml"), re.S)]
            out = []
            for n in sorted(x for x in names if re.match(r"xl/worksheets/sheet\d+\.xml$", x)):
                out.append(f"--- feuille {n.rsplit('/', 1)[1][:-4]} ---")
                for row in re.findall(r"<row[^>]*>(.*?)</row>", read(n), re.S):
                    cells = []
                    for attrs, body in re.findall(r"<c([^>]*)>(.*?)</c>", row, re.S):
                        v = re.search(r"<v>(.*?)</v>", body, re.S)
                        val = v.group(1) if v else text(body)
                        if 't="s"' in attrs and v:
                            val = shared[int(val)]
                        cells.append(val)
                    out.append("\t".join(cells))
            return "\n".join(out)
        return text(re.sub(r"</text:p>", "\n", read("content.xml"))).strip()


def _tool(name, desc, props, required=()):
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props, "required": list(required)}}}


S, I = {"type": "string"}, {"type": "integer"}
TOOL_SPECS = [
    _tool("run_command", "Exécute une commande shell (PowerShell sous Windows) dans le dossier de travail. "
          "Pour installer, lancer des programmes, git, gérer des fichiers, infos système…",
          {"command": S, "timeout": I}, ["command"]),
    _tool("run_python", "Exécute un script Python complet et renvoie sa sortie. Idéal pour calculs, "
          "traitement de données, automatisation.", {"code": S, "timeout": I}, ["code"]),
    _tool("read_file", "Lit un fichier texte avec numéros de ligne.",
          {"path": S, "start_line": I, "end_line": I}, ["path"]),
    _tool("write_file", "Crée ou remplace entièrement un fichier texte.", {"path": S, "content": S},
          ["path", "content"]),
    _tool("edit_file", "Remplace un passage exact et unique d'un fichier.",
          {"path": S, "old_text": S, "new_text": S}, ["path", "old_text", "new_text"]),
    _tool("list_dir", "Liste récursivement les fichiers d'un dossier (motif glob optionnel, ex: *.pdf).",
          {"path": S, "pattern": S, "max_depth": I}),
    _tool("search_files", "Cherche une expression régulière dans le contenu des fichiers.",
          {"regex": S, "path": S, "pattern": S}, ["regex"]),
    _tool("read_document", "Extrait le texte d'un PDF, Word, Excel, PowerPoint, OpenDocument ou d'une image.",
          {"path": S}, ["path"]),
    _tool("web_search", "Recherche sur le web. Renvoie titres, liens et extraits.", {"query": S}, ["query"]),
    _tool("fetch_url", "Télécharge une page web et renvoie son texte.", {"url": S}, ["url"]),
    _tool("download_file", "Télécharge un fichier depuis une URL.", {"url": S, "path": S}, ["url", "path"]),
    _tool("look_at_image", "Analyse une image avec le modèle de vision et répond à une question dessus.",
          {"path": S, "question": S}, ["path"]),
    _tool("screenshot", "Capture l'écran de l'utilisateur ; si une question est donnée, analyse la capture.",
          {"question": S}),
    _tool("open_item", "Ouvre une URL dans le navigateur, un fichier, un dossier, ou une application "
          "(ex: 'notepad', 'calc', 'excel', 'winword').", {"target": S}, ["target"]),
    _tool("clipboard", "Lit (action=read) ou écrit (action=write) le presse-papiers.",
          {"action": {"type": "string", "enum": ["read", "write"]}, "text": S}, ["action"]),
    _tool("speak", "Dit un texte à voix haute.", {"text": S}, ["text"]),
    _tool("remember", "Mémorise un fait durable sur l'utilisateur ou ses projets (garde entre sessions).",
          {"fact": S}, ["fact"]),
    _tool("update_plan", "Définit ou met à jour le plan d'une tâche en plusieurs étapes.",
          {"steps": {"type": "array", "items": {"type": "object", "properties": {
              "etape": S, "statut": {"type": "string", "enum": ["a_faire", "en_cours", "fait"]}}}}},
          ["steps"]),
    _tool("delegate", "Confie une sous-tâche autonome à un sous-agent qui a un contexte neuf ; "
          "renvoie son rapport. Utile pour les recherches longues.", {"task": S}, ["task"]),
]
TOOL_NAMES = [t["function"]["name"] for t in TOOL_SPECS]
