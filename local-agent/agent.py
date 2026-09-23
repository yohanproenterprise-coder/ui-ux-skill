#!/usr/bin/env python3
"""
Jarvis — agent IA autonome qui tourne sur ton ordinateur.

  python agent.py              conversation dans le terminal
  python agent.py --web        interface dans le navigateur (http://localhost:7860)
  python agent.py "tâche"      exécute une tâche directement

Aucune dépendance obligatoire : uniquement Python 3.9+ (pypdf en option pour les PDF).
"""

import argparse
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jarvis import config, scheduler, system, updater  # noqa: E402
from jarvis.config import MEMORY_FILE  # noqa: E402
from jarvis.core import Agent, Brain  # noqa: E402
from jarvis.llm import OllamaLLM  # noqa: E402

if os.name == "nt":
    os.system("")  # active les couleurs ANSI dans la console Windows
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

C = {"dim": "\033[2m", "cyan": "\033[36m", "yellow": "\033[33m", "green": "\033[32m",
     "red": "\033[31m", "bold": "\033[1m", "reset": "\033[0m"}


def say(text, color="reset", end="\n"):
    print(f"{C[color]}{text}{C['reset']}", end=end, flush=True)


class TerminalUI:
    def __init__(self, cfg):
        self.cfg = cfg
        self.started = False

    def token(self, text):
        if not self.started:
            say("\n", end="")
            self.started = True
        say(text, end="")

    def tool_start(self, name, args):
        self.started = False
        preview = ", ".join(f"{k}={str(v)[:60]!r}" for k, v in args.items())
        say(f"\n  → {name}({preview[:160]})", "dim")

    def tool_end(self, name, result):
        short = result[:280].replace("\n", "\n    ")
        say(f"    {short}{'…' if len(result) > 280 else ''}", "red" if result.startswith("ERREUR") else "dim")

    def done(self, text):
        self.started = False
        say("")
        if text and self.cfg.get("speak"):
            threading.Thread(target=system.speak, args=(text,), daemon=True).start()

    def info(self, text, level="info"):
        say(f"\n  ({text})", "yellow" if level != "info" else "dim")

    def plan(self, steps):
        icons = {"fait": "✔", "en_cours": "▶"}
        say("\n  Plan :", "cyan")
        for s in steps:
            say(f"   {icons.get(s.get('statut'), '○')} {s.get('etape')}", "cyan")

    def confirm(self, action):
        say(f"\n  ⚠  {action}", "yellow")
        ans = input(f"{C['yellow']}  Autoriser ? [o]ui / [n]on / [t]oujours : {C['reset']}").strip().lower()
        if ans in ("t", "toujours", "a", "always"):
            return "always"
        return ans in ("o", "oui", "y", "yes", "")


HELP = """Commandes :
  /aide                 cette aide
  /voix                 parler au lieu d'écrire (Windows)
  /parole               lire les réponses à voix haute (oui/non)
  /auto                 exécuter sans demander de confirmation (oui/non)
  /cerveau NOM          changer de modèle : local, gemini, groq, openrouter
  /modele NOM           changer le modèle du cerveau actuel (ex: /modele qwen3:1.7b)
  /cle FOURNISSEUR CLÉ  enregistrer une clé API gratuite (ex: /cle gemini AIza...)
  /taches               rappels et tâches programmés
  /maj                  mettre Jarvis à jour
  /memoire              afficher la mémoire à long terme
  /reprendre            reprendre la dernière conversation
  /resume               résumer le contexte maintenant
  /nouveau              nouvelle conversation
  /quitter              quitter"""


def check_local(cfg):
    """Vérifie qu'Ollama tourne et que le modèle local est installé, avec des conseils sinon."""
    p = cfg["providers"]["local"]
    names = OllamaLLM(p).installed_models()
    if names is None:
        return ("Ollama ne répond pas. Lance l'application Ollama (icône lama près de l'horloge) "
                "ou installe-la : https://ollama.com/download")
    want = p["model"] if ":" in p["model"] else p["model"] + ":latest"
    if want not in names:
        return f"Le modèle local n'est pas installé. Tape dans un terminal :  ollama pull {p['model']}"
    return None


def terminal(cfg, args):
    ui = TerminalUI(cfg)
    try:
        brain = Brain(cfg, ui)
    except ValueError as e:
        sys.exit(str(e))
    if brain.name == "local" or cfg.get("fallback") == "local":
        problem = check_local(cfg)
        if problem:
            say(problem, "yellow" if brain.name != "local" else "red")
            if brain.name == "local":
                sys.exit(1)
    agent = Agent(brain, ui, cfg, cfg["workdir"], auto=cfg["auto"])

    def on_due(item):
        label = "Rappel" if item["kind"] == "rappel" else "Tâche prévue (lance l'interface web pour l'exécution auto)"
        system.notify(f"Jarvis — {label}", item["task"])
        say(f"\n  ⏰ {label} : {item['task']}", "yellow")
    scheduler.start(on_due)

    if args.tache:
        agent.run(" ".join(args.tache))
        return

    say(f"Jarvis — {brain.label} — dossier {agent.tools.workdir}", "bold")
    say("Écris ta demande. /aide pour les commandes. Ctrl+C interrompt une tâche.", "dim")
    while True:
        try:
            text = input(f"\n{C['green']}{C['bold']}toi › {C['reset']}").strip()
        except (EOFError, KeyboardInterrupt):
            say("\nÀ bientôt !")
            return
        if not text:
            continue
        cmd, _, arg = text.partition(" ")
        arg = arg.strip()
        try:
            if cmd in ("/quitter", "/exit", "/q"):
                return
            elif cmd == "/aide":
                say(HELP, "cyan")
            elif cmd == "/voix":
                say("  🎤 Je t'écoute…", "cyan")
                heard, err = system.listen()
                if err:
                    say("  " + err, "yellow")
                else:
                    say(f"  toi (voix) › {heard}", "green")
                    agent.run(heard)
            elif cmd == "/parole":
                cfg["speak"] = not cfg["speak"]
                config.save(cfg)
                say(f"Lecture à voix haute : {'activée' if cfg['speak'] else 'désactivée'}", "cyan")
            elif cmd == "/auto":
                agent.tools.auto = not agent.tools.auto
                say(f"Mode auto : {'ACTIVÉ — plus aucune confirmation' if agent.tools.auto else 'désactivé'}",
                    "yellow")
            elif cmd == "/cerveau" and arg:
                brain.use(arg)
                cfg["provider"] = arg
                config.save(cfg)
                say(f"Cerveau : {brain.label}", "cyan")
            elif cmd == "/modele" and arg:
                cfg["providers"][brain.name]["model"] = arg
                config.save(cfg)
                brain.use(brain.name)
                say(f"Cerveau : {brain.label}", "cyan")
            elif cmd == "/cle":
                name, _, key = arg.partition(" ")
                if name not in cfg["providers"] or not key.strip():
                    say("Usage : /cle gemini TA_CLE", "yellow")
                else:
                    cfg["api_keys"][name] = key.strip()
                    config.save(cfg)
                    say(f"Clé {name} enregistrée. Tape /cerveau {name} pour l'utiliser.", "cyan")
            elif cmd == "/taches":
                say(agent.tools.list_scheduled(), "cyan")
            elif cmd == "/maj":
                say("Téléchargement de la mise à jour…", "cyan")
                say(updater.update(), "cyan")
            elif cmd == "/memoire":
                say(MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else "(vide)", "cyan")
            elif cmd == "/reprendre":
                say("Conversation reprise." if agent.resume_last() else "Aucune conversation enregistrée.", "cyan")
            elif cmd == "/resume":
                agent.compact(force=True)
            elif cmd == "/nouveau":
                agent = Agent(brain, ui, cfg, agent.tools.workdir, auto=agent.tools.auto)
                say("Nouvelle conversation.", "cyan")
            elif cmd.startswith("/"):
                say("Commande inconnue. /aide pour la liste.", "yellow")
            else:
                agent.run(text)
        except KeyboardInterrupt:
            agent.stop = True
            say("\n  (interrompu)", "yellow")
        except Exception as e:
            say(f"\n  Erreur : {e}", "red")


def main():
    cfg = config.load()
    ap = argparse.ArgumentParser(description="Jarvis — agent IA local")
    ap.add_argument("tache", nargs="*", help="tâche à exécuter directement")
    ap.add_argument("--web", action="store_true", help="ouvrir l'interface web")
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("-c", "--cerveau", help="fournisseur : local, gemini, groq, openrouter")
    ap.add_argument("-m", "--model", help="modèle à utiliser pour ce fournisseur")
    ap.add_argument("--ctx", type=int, help="taille de contexte (tokens)")
    ap.add_argument("-d", "--dir", help="dossier de travail (par défaut ~/Jarvis)")
    ap.add_argument("--auto", action="store_true", help="aucune confirmation (prudence !)")
    ap.add_argument("--maj", action="store_true", help="mettre Jarvis à jour depuis GitHub")
    ap.add_argument("--set-key", nargs=2, metavar=("FOURNISSEUR", "CLE"), help="enregistrer une clé API")
    a = ap.parse_args()

    if a.maj:
        print(updater.update())
        return
    if a.set_key:
        cfg["api_keys"][a.set_key[0]] = a.set_key[1]
        if a.set_key[0] in cfg["providers"]:
            cfg["provider"] = a.set_key[0]
        config.save(cfg)
        print(f"Clé {a.set_key[0]} enregistrée ; c'est maintenant le cerveau principal.")
        return
    if a.cerveau:
        cfg["provider"] = a.cerveau
    if a.model:
        cfg["providers"][cfg["provider"]]["model"] = a.model
    if a.ctx:
        cfg["providers"][cfg["provider"]]["ctx"] = a.ctx
    if a.dir:
        cfg["workdir"] = a.dir
    cfg["auto"] = cfg["auto"] or a.auto
    if not config.CONFIG_FILE.exists():
        config.save(cfg)

    if a.web:
        from jarvis.web import serve
        if cfg["provider"] == "local" and check_local(cfg):
            print("Attention : " + check_local(cfg))
        try:
            serve(cfg, cfg["workdir"], a.port)
        except ValueError as e:
            sys.exit(str(e))
    else:
        terminal(cfg, a)


if __name__ == "__main__":
    main()
