"""Clients de modèles : Ollama (local) et toute API compatible OpenAI (Gemini, Groq, OpenRouter…).

Les messages internes ont un format neutre :
  {"role", "content", "images": [{"mime", "data"}], "tool_calls": [{"id", "name", "args"}],
   "tool_call_id", "name"}
et sont convertis pour chaque fournisseur.
"""

import json
import urllib.error
import urllib.request


class LLMError(Exception):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


class Stop(Exception):
    """Levée pour interrompre une génération en cours."""


def _open(url, payload, headers=None, timeout=900):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:800]
        if e.code in (401, 403):
            raise LLMError(f"Clé API refusée ({e.code}). Vérifie ta clé. {body}")
        raise LLMError(f"HTTP {e.code} : {body}", retryable=e.code in (408, 429) or e.code >= 500)
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise LLMError(f"Serveur injoignable ({url}) : {e}", retryable=True)


class OllamaLLM:
    def __init__(self, provider, think=False):
        self.base = provider["base_url"].rstrip("/")
        self.model = provider["model"]
        self.vision_model = provider.get("vision_model") or self.model
        self.ctx = provider["ctx"]
        self.think = think

    @staticmethod
    def _convert(m):
        out = {"role": m["role"], "content": m.get("content") or ""}
        if m.get("images"):
            out["images"] = [img["data"] for img in m["images"]]
        if m.get("tool_calls"):
            out["tool_calls"] = [{"function": {"name": c["name"], "arguments": c["args"]}}
                                 for c in m["tool_calls"]]
        if m["role"] == "tool":
            out["tool_name"] = m.get("name", "")
        return out

    def chat(self, messages, tools=None, on_token=None, model=None):
        payload = {"model": model or self.model, "stream": True, "keep_alive": "30m",
                   "messages": [self._convert(m) for m in messages],
                   "options": {"num_ctx": self.ctx}}
        if tools:
            payload["tools"] = tools
        if self.think is not None:
            payload["think"] = self.think
        try:
            return self._stream(payload, on_token)
        except LLMError as e:
            if "think" in str(e).lower() and "think" in payload:
                self.think = None  # ce modèle ne gère pas le paramètre : on le retire
                del payload["think"]
                return self._stream(payload, on_token)
            if "not found" in str(e).lower():
                raise LLMError(f"Modèle absent. Installe-le : ollama pull {payload['model']}")
            raise

    def _stream(self, payload, on_token):
        content, calls = "", []
        with _open(self.base + "/api/chat", payload) as resp:
            for line in resp:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if "error" in chunk:
                    raise LLMError(chunk["error"])
                msg = chunk.get("message", {})
                if msg.get("content"):
                    content += msg["content"]
                    if on_token:
                        on_token(msg["content"])
                for c in msg.get("tool_calls") or []:
                    fn = c.get("function", {})
                    args = fn.get("arguments") or {}
                    if isinstance(args, str):
                        args = _parse_args(args)
                    calls.append({"id": f"call_{len(calls)}", "name": fn.get("name", ""), "args": args})
                if chunk.get("done"):
                    break
        return {"role": "assistant", "content": content, "tool_calls": calls}

    def installed_models(self):
        try:
            with urllib.request.urlopen(self.base + "/api/tags", timeout=5) as r:
                return [m["name"] for m in json.load(r).get("models", [])]
        except Exception:
            return None


class OpenAILLM:
    def __init__(self, provider, api_key):
        self.base = provider["base_url"].rstrip("/")
        self.model = provider["model"]
        self.vision_model = provider.get("vision_model") or self.model
        self.ctx = provider["ctx"]
        self.key = api_key

    @staticmethod
    def _convert(m):
        if m["role"] == "tool":
            return {"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]}
        content = m.get("content") or ""
        if m.get("images"):
            content = [{"type": "text", "text": content}] + [
                {"type": "image_url", "image_url": {"url": f"data:{i['mime']};base64,{i['data']}"}}
                for i in m["images"]]
        out = {"role": m["role"], "content": content}
        if m.get("tool_calls"):
            out["content"] = content or None
            out["tool_calls"] = [{"id": c["id"], "type": "function", "function": {
                "name": c["name"], "arguments": json.dumps(c["args"], ensure_ascii=False)},
                # Gemini 3 exige qu'on lui renvoie la « signature de pensée » reçue avec l'appel
                **({"extra_content": c["extra"]} if c.get("extra") else {})}
                for c in m["tool_calls"]]
        return out

    def chat(self, messages, tools=None, on_token=None, model=None):
        payload = {"model": model or self.model, "stream": True,
                   "messages": [self._convert(m) for m in messages]}
        if tools:
            payload["tools"] = tools
        content, acc = "", {}
        with _open(self.base + "/chat/completions", payload,
                   {"Authorization": f"Bearer {self.key}"}) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                if chunk.get("error"):
                    raise LLMError(str(chunk["error"]), retryable=True)
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta") or {}
                    if delta.get("content"):
                        content += delta["content"]
                        if on_token:
                            on_token(delta["content"])
                    for pos, tc in enumerate(delta.get("tool_calls") or []):
                        slot = acc.setdefault(tc.get("index", pos), {"id": "", "name": "", "args": "", "extra": None})
                        if tc.get("extra_content"):
                            slot["extra"] = tc["extra_content"]
                        fn = tc.get("function") or {}
                        slot["id"] = tc.get("id") or slot["id"]
                        slot["name"] = fn.get("name") or slot["name"]
                        slot["args"] += fn.get("arguments") or ""
        calls = [{"id": s["id"] or f"call_{i}", "name": s["name"], "args": _parse_args(s["args"]),
                  **({"extra": s["extra"]} if s["extra"] else {})}
                 for i, s in sorted(acc.items())]
        return {"role": "assistant", "content": content, "tool_calls": calls}


def _parse_args(text):
    if not text.strip():
        return {}
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {"_raw": text}
    except json.JSONDecodeError:
        return {"_raw": text}


def make(cfg, name):
    p = cfg["providers"][name]
    if p["type"] == "ollama":
        return OllamaLLM(p, think=cfg.get("think", False))
    return OpenAILLM(p, cfg["api_keys"].get(name, ""))
