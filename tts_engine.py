"""
Moteur TTS unifié pour JARVIS.
Backends : edge (cloud), pyttsx3 (Windows SAPI), xtts (Coqui local GPU), fish_speech (serveur local).
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
from typing import Any
from pathlib import Path

JARVIS_ROOT = os.path.dirname(os.path.abspath(__file__))
VOICES_DIR = os.path.join(JARVIS_ROOT, "voices")
CONFIG_PATH = os.path.join(JARVIS_ROOT, "jarvis_config.json")

ENGINES = ("edge", "pyttsx3", "xtts", "fish_speech")
DEFAULT_TTS = {
    "engine": "edge",
    "voice_id": "fr-FR-HenriNeural",
    "xtts_speaker_wav": "",
    "xtts_language": "fr",
    "fish_speech_url": "http://127.0.0.1:8080",
    "fish_speech_reference_id": "",
    "pyttsx3_rate": 150,
    "pyttsx3_volume": 0.9,
    "edge_tts_rate": "+0%",
    "edge_tts_volume": "+0%",
}

# Voix Edge TTS recommandées par langue
EDGE_VOICES_PRESETS = {
    "fr": [
        {"id": "fr-FR-HenriNeural", "label": "Henri (FR) - Homme", "gender": "Male"},
        {"id": "fr-FR-DeniseNeural", "label": "Denise (FR) - Femme", "gender": "Female"},
        {"id": "fr-CA-ThierryNeural", "label": "Thierry (CA) - Homme", "gender": "Male"},
        {"id": "fr-CA-AntoineNeural", "label": "Antoine (CA) - Homme", "gender": "Male"},
        {"id": "fr-CA-SylvieNeural", "label": "Sylvie (CA) - Femme", "gender": "Female"},
        {"id": "fr-BE-GerardNeural", "label": "Gérard (BE) - Homme", "gender": "Male"},
        {"id": "fr-BE-CharlineNeural", "label": "Charline (BE) - Femme", "gender": "Female"},
        {"id": "fr-CH-ArianeNeural", "label": "Ariane (CH) - Femme", "gender": "Female"},
        {"id": "fr-CH-FabriceNeural", "label": "Fabrice (CH) - Homme", "gender": "Male"},
    ],
}

_xtts_model = None


def _ensure_voices_dir() -> None:
    os.makedirs(VOICES_DIR, exist_ok=True)


def ensure_voices_dir() -> Path:
    """Crée le répertoire des voix s'il n'existe pas. (Alias pour compatibilité)"""
    _ensure_voices_dir()
    return Path(VOICES_DIR)


def charger_config_tts() -> dict:
    """Lit la section tts depuis jarvis_config.json."""
    cfg = dict(DEFAULT_TTS)
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            tts = data.get("tts") or {}
            if isinstance(tts, dict):
                cfg.update({k: v for k, v in tts.items() if v is not None})
    except Exception as e:
        print(f"[TTS] Erreur lecture config : {e}")
    if cfg.get("engine") not in ENGINES:
        cfg["engine"] = "edge"
    return cfg


def sauvegarder_config_tts(tts: dict) -> bool:
    """Fusionne la section tts dans jarvis_config.json."""
    try:
        data: dict = {}
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except Exception:
            pass
        current = data.get("tts") or {}
        if not isinstance(current, dict):
            current = {}
        current.update(tts)
        data["tts"] = current
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"[TTS] Configuration sauvegardée")
        return True
    except Exception as e:
        print(f"[TTS] Erreur sauvegarde config : {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# API SIMPLIFIÉE POUR GÉRER LES VOIX
# ─────────────────────────────────────────────────────────────────────────────

def get_engine() -> str:
    """Retourne le moteur TTS actuellement configuré."""
    return charger_config_tts().get("engine", "edge")


def get_voice_id() -> str:
    """Retourne l'ID de voix actuellement configurée."""
    return charger_config_tts().get("voice_id", "fr-FR-HenriNeural")


def set_engine(engine: str) -> bool:
    """Change le moteur TTS."""
    if engine not in ENGINES:
        print(f"[TTS] Engine invalide : {engine}. Engines disponibles: {', '.join(ENGINES)}")
        return False
    return sauvegarder_config_tts({"engine": engine})


def set_voice_id(voice_id: str, engine: str | None = None) -> bool:
    """Change l'ID de voix."""
    updates = {"voice_id": voice_id}
    if engine:
        if not set_engine(engine):
            return False
    return sauvegarder_config_tts(updates)


def afficher_config() -> str:
    """Affiche la configuration actuelle sous forme lisible."""
    cfg = charger_config_tts()
    lines = [
        "═" * 60,
        "CONFIGURATION VOIX JARVIS",
        "═" * 60,
        f"Engine actuel  : {cfg.get('engine', 'edge')}",
        f"Voice ID       : {cfg.get('voice_id', 'fr-FR-HenriNeural')}",
    ]
    
    if cfg.get("engine") == "pyttsx3":
        lines.append(f"Rate (pyttsx3) : {cfg.get('pyttsx3_rate', 150)} wpm")
        lines.append(f"Volume         : {cfg.get('pyttsx3_volume', 0.9) * 100:.0f}%")
    
    elif cfg.get("engine") == "edge":
        lines.append(f"Rate (Edge)    : {cfg.get('edge_tts_rate', '+0%')}")
        lines.append(f"Volume (Edge)  : {cfg.get('edge_tts_volume', '+0%')}")
    
    elif cfg.get("engine") == "xtts":
        lines.append(f"XTTS Speaker   : {cfg.get('xtts_speaker_wav', '(aucun)')}")
        lines.append(f"XTTS Language  : {cfg.get('xtts_language', 'fr')}")
    
    elif cfg.get("engine") == "fish_speech":
        lines.append(f"Fish URL       : {cfg.get('fish_speech_url', 'http://127.0.0.1:8080')}")
    
    lines.append("═" * 60)
    return "\n".join(lines)


async def creer_demo_voix() -> str | None:
    """Crée un fichier audio de démonstration avec la voix actuelle. Retourne le chemin du fichier."""
    cfg = charger_config_tts()
    engine = cfg.get("engine", "edge")
    texte = "Bonjour, je suis JARVIS. Voici un exemple de ma voix."
    
    demo_path = os.path.join(JARVIS_ROOT, "voice_demo.mp3")
    
    try:
        if engine == "edge":
            voice_id = cfg.get("voice_id", "fr-FR-HenriNeural")
            await synthese_avec_fallback(texte, cfg)
            path = await synthese(texte, cfg)
            return path
        else:
            path = await synthese(texte, cfg)
            return path
    except Exception as e:
        print(f"[TTS] Erreur création démo : {e}")
        return None


# Alias pour compatibilité avec voice_config
charger_config = charger_config_tts
sauvegarder_config = sauvegarder_config_tts


def lister_voix_reference() -> list[dict]:
    """Fichiers .wav/.mp3 dans voices/ — utilisables pour XTTS / Fish Speech."""
    _ensure_voices_dir()
    out = []
    for name in sorted(os.listdir(VOICES_DIR)):
        low = name.lower()
        if low.endswith((".wav", ".mp3", ".flac", ".ogg")):
            path = os.path.join(VOICES_DIR, name)
            out.append({"id": path, "label": os.path.splitext(name)[0], "path": path})
    return out


async def lister_voix_edge() -> list[dict]:
    try:
        import edge_tts
        voices = await edge_tts.list_voices()
        fr = [v for v in voices if v.get("Locale", "").lower().startswith("fr")]
        rest = [v for v in voices if not v.get("Locale", "").lower().startswith("fr")]
        ordered = fr + rest
        return [
            {
                "id": v["ShortName"],
                "label": f"{v.get('FriendlyName', v['ShortName'])} ({v.get('Locale', '?')})",
                "gender": v.get("Gender", ""),
            }
            for v in ordered
        ]
    except Exception as e:
        print(f"[TTS] edge list_voices : {e}")
        return [{"id": "fr-FR-HenriNeural", "label": "Henri (fr-FR)"}]


def lister_voix_pyttsx3() -> list[dict]:
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty("voices") or []
        out = []
        for v in voices:
            langs = getattr(v, "languages", None) or []
            lang_hint = ""
            if langs:
                try:
                    lang_hint = langs[0].decode("utf-8", errors="ignore") if isinstance(langs[0], bytes) else str(langs[0])
                except Exception:
                    lang_hint = str(langs[0])
            label = v.name
            if lang_hint:
                label = f"{v.name} ({lang_hint})"
            out.append({"id": v.id, "label": label})
        try:
            engine.stop()
        except Exception:
            pass
        return out or [{"id": "", "label": "Voix système par défaut"}]
    except Exception as e:
        print(f"[TTS] pyttsx3 indisponible : {e}")
        return []


def lister_voix_xtts() -> list[dict]:
    refs = lister_voix_reference()
    if refs:
        return refs
    return [{"id": "", "label": "— Placez un fichier .wav dans le dossier voices/ —"}]


def lister_voix_fish_speech(cfg: dict | None = None) -> list[dict]:
    refs = lister_voix_reference()
    base = [{"id": r["id"], "label": f"Clone : {r['label']}"} for r in refs]
    url = (cfg or charger_config_tts()).get("fish_speech_url", DEFAULT_TTS["fish_speech_url"])
    try:
        import requests
        resp = requests.get(f"{url.rstrip('/')}/v1/references", timeout=2)
        if resp.ok:
            data = resp.json()
            items = data if isinstance(data, list) else data.get("references", [])
            for item in items:
                rid = item.get("id") or item.get("reference_id") or item.get("name", "")
                if rid:
                    base.append({"id": str(rid), "label": f"Serveur : {item.get('name', rid)}"})
    except Exception:
        pass
    if not base:
        base.append({"id": "", "label": "— Lancez Fish Speech + ajoutez un .wav dans voices/ —"})
    return base


async def lister_voix(engine: str | None = None, cfg: dict | None = None) -> list[dict]:
    cfg = cfg or charger_config_tts()
    eng = engine or cfg.get("engine", "edge")
    if eng == "pyttsx3":
        return lister_voix_pyttsx3()
    if eng == "xtts":
        return lister_voix_xtts()
    if eng == "fish_speech":
        return lister_voix_fish_speech(cfg)
    return await lister_voix_edge()


def moteur_disponible(engine: str) -> bool:
    if engine == "edge":
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False
    if engine == "pyttsx3":
        try:
            import pyttsx3  # noqa: F401
            return True
        except ImportError:
            return False
    if engine == "xtts":
        try:
            import torch  # noqa: F401
            from TTS.api import TTS  # noqa: F401
            return True
        except ImportError:
            return False
    if engine == "fish_speech":
        try:
            import requests  # noqa: F401
            return True
        except ImportError:
            return False
    return False


def statut_moteurs() -> dict[str, dict]:
    return {
        eng: {
            "available": moteur_disponible(eng),
            "label": {
                "edge": "Edge TTS (cloud, rapide)",
                "pyttsx3": "Pyttsx3 (Windows, local)",
                "xtts": "Coqui XTTS v2 (GPU, clone vocal)",
                "fish_speech": "Fish Speech (serveur local)",
            }.get(eng, eng),
        }
        for eng in ENGINES
    }


def _get_xtts_model():
    global _xtts_model
    if _xtts_model is None:
        import torch
        from TTS.api import TTS
        use_gpu = torch.cuda.is_available()
        print(f"[TTS] Chargement XTTS v2 (GPU={'oui' if use_gpu else 'non'})…")
        _xtts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=use_gpu)
    return _xtts_model


def _synthese_edge_sync(texte: str, voice_id: str, out_path: str) -> None:
    import edge_tts

    async def _run():
        comm = edge_tts.Communicate(texte, voice=voice_id or "fr-FR-HenriNeural")
        await comm.save(out_path)

    asyncio.run(_run())


def _synthese_pyttsx3_sync(texte: str, voice_id: str, out_path: str) -> None:
    import pyttsx3
    engine = pyttsx3.init()
    if voice_id:
        engine.setProperty("voice", voice_id)
    engine.save_to_file(texte, out_path)
    engine.runAndWait()
    try:
        engine.stop()
    except Exception:
        pass


def _synthese_xtts_sync(texte: str, speaker_wav: str, language: str, out_path: str) -> None:
    if not speaker_wav or not os.path.isfile(speaker_wav):
        refs = lister_voix_reference()
        if not refs:
            raise FileNotFoundError(
                "XTTS nécessite un fichier de référence (.wav) dans le dossier voices/"
            )
        speaker_wav = refs[0]["path"]
    model = _get_xtts_model()
    model.tts_to_file(
        text=texte,
        file_path=out_path,
        speaker_wav=speaker_wav,
        language=language or "fr",
    )


def _synthese_fish_speech_sync(texte: str, cfg: dict, out_path: str) -> None:
    import requests
    url = cfg.get("fish_speech_url", DEFAULT_TTS["fish_speech_url"]).rstrip("/")
    ref = cfg.get("voice_id") or cfg.get("fish_speech_reference_id") or cfg.get("xtts_speaker_wav", "")
    payload: dict[str, Any] = {"text": texte, "format": "wav"}
    if ref and os.path.isfile(ref):
        with open(ref, "rb") as f:
            resp = requests.post(
                f"{url}/v1/tts",
                files={"reference_audio": (os.path.basename(ref), f, "audio/wav")},
                data={"text": texte},
                timeout=120,
            )
    elif ref:
        payload["reference_id"] = ref
        resp = requests.post(f"{url}/v1/tts", json=payload, timeout=120)
    else:
        refs = lister_voix_reference()
        if refs:
            with open(refs[0]["path"], "rb") as f:
                resp = requests.post(
                    f"{url}/v1/tts",
                    files={"reference_audio": (os.path.basename(refs[0]["path"]), f, "audio/wav")},
                    data={"text": texte},
                    timeout=120,
                )
        else:
            resp = requests.post(f"{url}/v1/tts", json=payload, timeout=120)
    resp.raise_for_status()
    ct = resp.headers.get("content-type", "")
    if "json" in ct:
        data = resp.json()
        import base64
        audio_b64 = data.get("audio") or data.get("audio_b64") or data.get("data")
        if audio_b64:
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(audio_b64))
            return
        raise RuntimeError(f"Réponse Fish Speech inattendue : {data}")
    with open(out_path, "wb") as f:
        f.write(resp.content)


def _synthese_sync(texte: str, cfg: dict | None = None) -> str:
    """Génère un fichier audio temporaire et retourne son chemin."""
    cfg = cfg or charger_config_tts()
    engine = cfg.get("engine", "edge")
    voice_id = cfg.get("voice_id", "")

    ext = ".wav" if engine in ("pyttsx3", "xtts", "fish_speech") else ".mp3"
    out_path = os.path.join(JARVIS_ROOT, f"jarvis_tts_{int(time.time() * 1000)}{ext}")

    if engine == "pyttsx3":
        if not moteur_disponible("pyttsx3"):
            raise RuntimeError("pyttsx3 non installé")
        _synthese_pyttsx3_sync(texte, voice_id, out_path)
    elif engine == "xtts":
        if not moteur_disponible("xtts"):
            raise RuntimeError("Coqui TTS non installé — pip install TTS torch")
        speaker = cfg.get("xtts_speaker_wav") or voice_id
        _synthese_xtts_sync(texte, speaker, cfg.get("xtts_language", "fr"), out_path)
    elif engine == "fish_speech":
        _synthese_fish_speech_sync(texte, cfg, out_path)
    else:
        if not moteur_disponible("edge"):
            raise RuntimeError("edge-tts non installé")
        _synthese_edge_sync(texte, voice_id or "fr-FR-HenriNeural", out_path)

    if not os.path.isfile(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError(f"Fichier audio vide ou absent : {out_path}")
    return out_path


async def synthese(texte: str, cfg: dict | None = None) -> str:
    """Synthèse async — délègue au thread pool pour les moteurs bloquants."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _synthese_sync, texte, cfg)


async def synthese_avec_fallback(texte: str, cfg: dict | None = None) -> tuple[str, dict]:
    """
    Tente le moteur configuré, puis edge en secours.
    Retourne (chemin_fichier, config_effective).
    """
    cfg = dict(cfg or charger_config_tts())
    primary = cfg.get("engine", "edge")
    try:
        path = await synthese(texte, cfg)
        return path, cfg
    except Exception as e:
        print(f"[TTS] Échec {primary} : {e}")
        if primary != "edge" and moteur_disponible("edge"):
            print("[TTS] Repli sur Edge TTS…")
            fallback = dict(cfg)
            fallback["engine"] = "edge"
            if not fallback.get("voice_id"):
                fallback["voice_id"] = "fr-FR-HenriNeural"
            path = await synthese(texte, fallback)
            return path, fallback
        raise
