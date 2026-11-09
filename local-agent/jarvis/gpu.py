"""Accélération par la carte graphique (Windows, DirectML : marche avec les puces Intel, AMD et NVIDIA).

Le moteur d'IA « carte graphique » est installé à part (dossier gpu-runtime), sans toucher au moteur
habituel : il suffit de supprimer ce dossier (ou de désactiver l'option) pour revenir au processeur.
Au premier démarrage, Jarvis mesure les deux sur le PC et ne garde la carte graphique que si elle est
vraiment plus rapide. Au moindre problème avec un modèle, celui-ci repasse tout seul sur le processeur.
"""

import json
import subprocess
import sys
import threading
import time

from .config import HOME

DIR = HOME / "gpu-runtime"          # moteur d'IA DirectML (installé à côté du moteur habituel)
OFF = HOME / "gpu-off"              # présent : l'utilisateur a désactivé la carte graphique
TEST = HOME / "gpu-test.json"       # résultat de la mesure de vitesse sur ce PC
DML = "DmlExecutionProvider"
state = {"state": "", "step": "", "error": ""}


def supported():
    return sys.platform == "win32" and sys.maxsize > 2 ** 32


def activate_path():
    """À appeler au démarrage, AVANT tout import d'onnxruntime : utilise le moteur carte graphique s'il est là."""
    if not (supported() and DIR.exists() and not OFF.exists() and str(DIR) not in sys.path):
        return False
    sys.path.insert(0, str(DIR))
    try:
        import onnxruntime  # noqa: F401  (vérifie tout de suite que ce moteur démarre sur ce PC)
        return True
    except Exception as e:
        # il ne démarre pas : on revient au moteur habituel, et on le note pour ne pas réessayer en boucle
        sys.path.remove(str(DIR))
        for name in [m for m in sys.modules if m == "onnxruntime" or m.startswith("onnxruntime.")]:
            del sys.modules[name]
        try:
            OFF.write_text(f"le moteur carte graphique ne démarre pas : {e}"[:300], encoding="utf-8")
            TEST.write_text(json.dumps({"ok": False, "reason": f"le moteur ne démarre pas sur ce PC ({e})"[:200]}),
                            encoding="utf-8")
        except OSError:
            pass
        return False


def _test():
    try:
        return json.loads(TEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def available():
    """Le moteur chargé sait-il utiliser la carte graphique ?"""
    try:
        import onnxruntime as ort
        return DML in ort.get_available_providers()
    except Exception:
        return False


def enabled():
    t = _test()
    return available() and not OFF.exists() and bool(t and t.get("ok"))


def providers(testing=False):
    return [DML, "CPUExecutionProvider"] if (enabled() or (testing and available())) else ["CPUExecutionProvider"]


def info():
    t = _test() or {}
    installed = DIR.exists()
    if state["state"] in ("installing", "error"):
        st = state["state"]
    elif not supported():
        st = "unsupported"
    elif not installed:
        st = "absent"
    elif OFF.exists():
        st = "slower" if t and not t.get("ok") and "démarre pas" in t.get("reason", "") else "off"
    elif not available():
        st = "restart"            # installé mais pas encore chargé : il faut redémarrer Jarvis
    elif not t:
        st = "testing"
    else:
        st = "active" if t.get("ok") else "slower"
    cpu_models = {k: v.get("why", "") for k, v in _models().items() if v.get("use") == "cpu"}
    return {"state": st, "speedup": t.get("speedup"), "cpu_models": cpu_models, "reason": t.get("reason", ""), "step": state["step"],
            "error": state["error"], "device": t.get("device", "")}


def install(on_done=None):
    """Installe le moteur carte graphique en arrière-plan, puis on_done() (redémarrage de Jarvis)."""
    if not supported():
        raise RuntimeError("La carte graphique n'est utilisable par Jarvis que sous Windows.")
    if state["state"] == "installing":
        return info()

    def work():
        try:
            state.update(state="installing", error="", step="Téléchargement du moteur carte graphique (≈ 20 Mo)…")
            DIR.mkdir(parents=True, exist_ok=True)
            # --no-deps : le moteur habituel a déjà installé numpy & co ; on ne touche à rien d'autre
            r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                                "--upgrade", "--no-deps", "--target", str(DIR), "onnxruntime-directml"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError("installation impossible : " + (r.stderr or r.stdout)[-300:])
            OFF.unlink(missing_ok=True)
            TEST.unlink(missing_ok=True)       # nouvelle mesure de vitesse au prochain démarrage
            MODELS_FILE.unlink(missing_ok=True)
            state.update(state="", step="Installé : Jarvis redémarre pour l'utiliser…")
            if on_done:
                on_done()
        except Exception as e:
            state.update(state="error", error=str(e), step="")
    threading.Thread(target=work, daemon=True).start()
    time.sleep(0.2)
    return info()


def set_enabled(on):
    """Active (après une nouvelle mesure) ou désactive la carte graphique. Prend effet au redémarrage."""
    if on:
        OFF.unlink(missing_ok=True)
        TEST.unlink(missing_ok=True)
        MODELS_FILE.unlink(missing_ok=True)
    else:
        OFF.write_text("désactivée par l'utilisateur", encoding="utf-8")


MODELS_FILE = HOME / "gpu-modeles.json"   # pour chaque modèle d'IA : carte graphique ou processeur (mesuré)


def _models():
    try:
        return json.loads(MODELS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def model_choice(path):
    from pathlib import Path
    return (_models().get(Path(path).name) or {}).get("use")


def set_model_choice(path, use, reason=""):
    from pathlib import Path
    m = _models()
    m[Path(path).name] = {"use": use, "why": reason}
    try:
        MODELS_FILE.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def selftest(model_path):
    """Mesure processeur contre carte graphique sur ce PC (une fois après l'installation). Ne garde la carte
    graphique que si elle est au moins 15 % plus rapide et donne le même résultat."""
    if not (available() and not OFF.exists() and _test() is None):
        return _test()
    import numpy as np
    import onnxruntime as ort
    result = {"ok": False, "time": int(time.time())}
    try:
        shapes = [(1, 3, 192, 256), (1, 3, 256, 256), (1, 3, 240, 320)]   # tailles variées, comme les tuiles
        rng = np.random.default_rng(0)
        xs = [rng.random(s, dtype=np.float32) for s in shapes]

        def bench(prov):
            o = ort.SessionOptions()
            o.log_severity_level = 3
            if prov[0] == DML:
                o.enable_mem_pattern = False
                o.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            s = ort.InferenceSession(str(model_path), sess_options=o, providers=prov)
            if prov[0] == DML and DML not in s.get_providers():
                raise RuntimeError("la carte graphique a refusé le modèle")
            name = s.get_inputs()[0].name
            s.run(None, {name: xs[0]})
            t = time.time()
            outs = [s.run(None, {name: x})[0] for x in xs]
            return time.time() - t, outs

        cpu_t, cpu_out = bench(["CPUExecutionProvider"])
        gpu_t, gpu_out = bench([DML, "CPUExecutionProvider"])
        diff = max(float(np.abs(a - b).max()) for a, b in zip(cpu_out, gpu_out))
        speed = round(cpu_t / max(gpu_t, 1e-6), 1)
        result.update(speedup=speed, cpu_s=round(cpu_t, 2), gpu_s=round(gpu_t, 2))
        if diff > 0.05:
            result["reason"] = "résultat différent du processeur"
        elif speed < 1.15:
            result["reason"] = f"pas plus rapide que le processeur sur ce PC (×{speed})"
        else:
            result["ok"] = True
    except Exception as e:
        result["reason"] = f"erreur : {e}"[:200]
    try:
        TEST.write_text(json.dumps(result), encoding="utf-8")
    except OSError:
        pass
    return result
