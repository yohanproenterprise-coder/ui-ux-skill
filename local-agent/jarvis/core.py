"""Le cœur de Jarvis : cerveau (modèle + bascule de secours) et boucle d'agent."""

import datetime
import json
import platform
import time

from . import config, llm
from .config import MEMORY_FILE, SESSIONS_DIR
from .tools import TOOL_SPECS, Tools

SPEC_TOKENS = len(json.dumps(TOOL_SPECS, ensure_ascii=False)) // 3


class Brain:
    """Modèle principal, avec bascule automatique sur le modèle de secours en cas d'échec."""

    def __init__(self, cfg, ui):
        self.cfg, self.ui = cfg, ui
        self.use(cfg["provider"])

    def use(self, name):
        if name not in self.cfg["providers"]:
            raise ValueError(f"Fournisseur inconnu : {name}. Choix : {', '.join(self.cfg['providers'])}")
        if not config.available(self.cfg, name):
            raise ValueError(f"Pas de clé API pour {name}. Obtiens-en une gratuitement sur "
                             f"{self.cfg['providers'][name].get('key_url')} puis tape : /cle {name} TA_CLE")
        self.name, self.llm = name, llm.make(self.cfg, name)
        self.backup, self.backup_until = None, 0

    @property
    def ctx(self):
        return self.llm.ctx

    @property
    def label(self):
        return f"{self.name} · {self.llm.model}"

    def chat(self, messages, tools=None, on_token=None, model=None):
        if self.backup and time.time() < self.backup_until:
            return self.backup.chat(messages, tools, on_token)
        try:
            return self.llm.chat(messages, tools, on_token, model)
        except llm.LLMError as e:
            fb = self.cfg.get("fallback")
            if not e.retryable or not fb or fb == self.name or not config.available(self.cfg, fb):
                raise
            self.ui.info(f"{self.name} indisponible ({str(e)[:120]}) → j'utilise {fb} pendant 10 min", "warn")
            self.backup, self.backup_until = llm.make(self.cfg, fb), time.time() + 600
            return self.backup.chat(messages, tools, on_token)

    def vision(self, question, image):
        msg = [{"role": "user", "content": question, "images": [image]}]
        try:
            return self.llm.chat(msg, model=self.llm.vision_model)["content"] or "(pas de réponse)"
        except llm.LLMError as e:
            fb = self.cfg.get("fallback")
            if fb and fb != self.name and config.available(self.cfg, fb):
                other = llm.make(self.cfg, fb)
                return other.chat(msg, model=other.vision_model)["content"]
            return f"ERREUR vision : {e}"


def system_prompt(workdir):
    memory = MEMORY_FILE.read_text(encoding="utf-8").strip() if MEMORY_FILE.exists() else "(vide)"
    shell = "PowerShell" if platform.system() == "Windows" else "sh"
    return f"""Tu es Jarvis, un assistant IA autonome qui tourne sur l'ordinateur de l'utilisateur et agit pour lui.
Réponds en français, de façon claire et concise.

Système : {platform.system()} {platform.release()} · shell de run_command : {shell}
Dossier de travail : {workdir}
Date et heure : {datetime.datetime.now():%A %d %B %Y, %H:%M}

Règles :
- AGIS avec tes outils au lieu d'expliquer à l'utilisateur ce qu'il devrait faire.
- Tâche en plusieurs étapes : update_plan d'abord, puis tiens-le à jour.
- Lis avant de modifier. Après une action, VÉRIFIE le résultat (relance, relis, teste).
- Si un outil renvoie une erreur, comprends-la et essaie autre chose. N'invente jamais un résultat.
- Information récente ou incertaine : web_search puis fetch_url sur les meilleures sources.
- Pour voir ce qu'il y a à l'écran : screenshot avec une question. Pour une image : look_at_image.
- Grosse recherche indépendante : delegate à un sous-agent.
- Quand tu apprends un fait durable sur l'utilisateur (prénom, projets, préférences) : remember.
- Termine par un résumé court et honnête : ce qui est fait, ce qui reste.

Mémoire à long terme :
{memory}"""


class Agent:
    def __init__(self, brain, ui, cfg, workdir, auto=False, sub=False):
        self.brain, self.ui, self.cfg = brain, ui, cfg
        self.tools = Tools(workdir, ui, brain, auto=auto, spawn=None if sub else self._spawn)
        self.specs = [t for t in TOOL_SPECS if not (sub and t["function"]["name"] == "delegate")]
        self.messages = [{"role": "system", "content": system_prompt(self.tools.workdir)}]
        self.sub, self.stop = sub, False
        self.session_file = SESSIONS_DIR / f"{datetime.datetime.now():%Y%m%d-%H%M%S}.json"

    # ------------------------------------------------------------ contexte --
    def _tokens(self):
        return SPEC_TOKENS + sum(len(json.dumps(m, ensure_ascii=False)) for m in self.messages) // 3

    def _max_tool_chars(self):
        return int(min(20000, max(3000, self.brain.ctx * 0.6)))

    def compact(self, force=False):
        """Résume les anciens échanges pour ne jamais dépasser la fenêtre de contexte."""
        if not force and self._tokens() < self.brain.ctx * 0.75:
            return
        cut = max(1, len(self.messages) - 6)
        while cut > 1 and self.messages[cut]["role"] == "tool":
            cut -= 1  # ne pas séparer un résultat d'outil de son appel
        old, recent = self.messages[1:cut], self.messages[cut:]
        if not old:
            return
        self.ui.info("contexte long : je résume les anciens échanges…")
        transcript = "\n".join(
            f"[{m['role']}] {(m.get('content') or '')[:1500]}"
            + "".join(f" <{c['name']} {json.dumps(c['args'], ensure_ascii=False)[:200]}>"
                      for c in m.get("tool_calls") or [])
            for m in old)[-int(self.brain.ctx * 2):]
        summary = self.brain.chat([
            {"role": "system", "content": "Tu résumes des sessions de travail de façon dense et factuelle."},
            {"role": "user", "content": "Résume cet historique : objectifs de l'utilisateur, décisions, fichiers "
                                        "touchés, résultats obtenus, problèmes ouverts, prochaines étapes.\n\n"
                                        + transcript}])["content"]
        for m in recent:
            if m["role"] == "tool" and len(m["content"]) > 2000:
                m["content"] = m["content"][:2000] + "\n… (tronqué)"
        self.messages = [self.messages[0],
                         {"role": "user", "content": "[Résumé des échanges précédents]\n" + summary},
                         {"role": "assistant", "content": "Compris, je continue à partir de ce résumé."}] + recent

    # ------------------------------------------------------------ sessions --
    def save(self):
        if self.sub:
            return
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        data = [{k: v for k, v in m.items() if k != "images"} for m in self.messages]
        self.session_file.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def resume_last(self):
        files = sorted(SESSIONS_DIR.glob("*.json")) if SESSIONS_DIR.exists() else []
        if not files:
            return False
        msgs = json.loads(files[-1].read_text(encoding="utf-8"))
        self.messages = [self.messages[0]] + msgs[1:]
        self.session_file = files[-1]
        self.compact()
        return True

    # --------------------------------------------------------------- boucle --
    def _token(self, text):
        if self.stop:
            raise llm.Stop()
        self.ui.token(text)

    def run(self, user_input):
        self.stop = False
        self.messages.append({"role": "user", "content": user_input})
        try:
            for _ in range(self.cfg.get("max_steps", 60)):
                self.compact()
                reply = self.brain.chat(self.messages, self.specs, self._token)
                self.messages.append(reply)
                if not reply["tool_calls"]:
                    self.save()
                    self.ui.done(reply["content"])
                    return reply["content"]
                for call in reply["tool_calls"]:
                    if self.stop:
                        raise llm.Stop()
                    self.ui.tool_start(call["name"], call["args"])
                    result = self.tools.call(call["name"], call["args"], self._max_tool_chars())
                    self.ui.tool_end(call["name"], result)
                    self.messages.append({"role": "tool", "tool_call_id": call["id"],
                                          "name": call["name"], "content": result})
                self.save()
            msg = "Limite d'étapes atteinte. Dis « continue » pour poursuivre."
        except llm.Stop:
            msg = "Interrompu."
            self.messages.append({"role": "assistant", "content": "(interrompu par l'utilisateur)"})
        except llm.LLMError as e:
            msg = f"Erreur du modèle : {e}"
            if "404" in str(e) or "not found" in str(e).lower() or "no longer available" in str(e):
                msg += "\n→ Ce modèle n'existe plus : clique sur « Modèle » en haut pour en choisir un autre."
        self.save()
        self.ui.info(msg, "warn")
        self.ui.done("")
        return msg

    def _spawn(self, task):
        sub = Agent(self.brain, _SubUI(self.ui), self.cfg, self.tools.workdir, auto=self.tools.auto, sub=True)
        report = sub.run(task + "\n\nQuand tu as fini, rédige un rapport complet et précis de tes résultats.")
        self.tools.auto = sub.tools.auto
        return report or "(le sous-agent n'a rien renvoyé)"


class _SubUI:
    """Interface d'un sous-agent : silencieuse, mais les confirmations remontent à l'utilisateur."""

    def __init__(self, parent):
        self.parent = parent

    def token(self, text):
        pass

    def tool_start(self, name, args):
        self.parent.info(f"  sous-agent → {name}")

    def tool_end(self, name, result):
        pass

    def done(self, text):
        pass

    def info(self, text, level="info"):
        self.parent.info("  sous-agent : " + text, level)

    def plan(self, steps):
        pass

    def confirm(self, action):
        return self.parent.confirm("(sous-agent) " + action)
