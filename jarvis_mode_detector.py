# -*- coding: utf-8 -*-
"""
Détection automatique : intention, humeur, état d'esprit → mode JARVIS adapté.
Modes : amoureux | personnel | ami | psychologique | professionnel | standard | auto
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from jarvis_human import detecter_humeur, CONFIG_FILE, _lire_json

JARVIS_ROOT = os.path.dirname(os.path.abspath(__file__))
MODES_CONFIG_FILE = os.path.join(JARVIS_ROOT, "jarvis_modes", "config.json")

MODES_ACTIFS = (
    "auto",
    "standard",
    "amoureux",
    "personnel",
    "ami",
    "psychologique",
    "professionnel",
)

# Alias utilisateur / JARVIS
_MODE_ALIASES = {
    "psy": "psychologique",
    "psychologue": "psychologique",
    "psychologique": "psychologique",
    "amour": "amoureux",
    "romantique": "amoureux",
    "pro": "professionnel",
    "professionnel": "professionnel",
    "dev": "professionnel",
    "perso": "personnel",
    "personnel": "personnel",
    "confident": "ami",
    "friend": "ami",
    "normal": "standard",
    "defaut": "standard",
    "défaut": "standard",
    "default": "standard",
}

_CONFIG_DEFAUT: dict[str, Any] = {
    "mode_standard": "standard",
    "seuil_confiance_auto": 0.42,
    "seuil_confiance_haute": 0.62,
    "confirmation_si_ambigu": True,
    "messages_sticky": 2,
    "defaut_si_neutre": "amoureux",
    "mots_cles": {
        "amoureux": [
            "amour", "chéri", "cheri", "mon amour", "ma vie", "romantique",
            "je t'aime", "bisou", "câlin", "ensemble", "tu me manques", "complice",
        ],
        "personnel": [
            "personnel", "perso", "intime", "privé", "ma vie", "pour moi",
            "chez moi", "maison", "famille", "orchidée", "orchidee", "jardin",
            "routine", "bien-être quotidien",
        ],
        "ami": [
            "ami", "copain", "pote", "confident", "partager", "sortie", "apéro",
            "balade", "hobby", "discuter", "rigoler", "conseil entre amis",
        ],
        "psychologique": [
            "psy", "psychologue", "émotion", "emotion", "anxiété", "anxiete",
            "stress", "déprime", "deprime", "bien-être", "mental", "sentiment",
            "je me sens", "ça va pas", "ca va pas", "parler de moi", "thérapie",
        ],
        "professionnel": [
            "projet", "code", "api", "fastapi", "react", "bug", "deploy",
            "client", "deadline", "git", "npm", "webdev", "développement",
            "site web", "terminal", "sprint",
        ],
    },
    "intentions": {
        "reconfort": {
            "patterns": [
                r"\bbesoin\b.*\b(parler|écouter|aide)\b",
                r"\b(je )?me sens\b",
                r"\bça va pas\b",
                r"\bca va pas\b",
                r"\bdifficile\b",
                r"\bécoute[- ]?moi\b",
            ],
            "mode_boost": {"psychologique": 3, "amoureux": 2, "ami": 1},
        },
        "romantique": {
            "patterns": [
                r"\b(idée|moment)\b.*\b(deux|ensemble)\b",
                r"\bsoirée\b.*\b(nous|ensemble)\b",
            ],
            "mode_boost": {"amoureux": 4},
        },
        "technique": {
            "patterns": [
                r"\b(comment|pourquoi)\b.*\b(code|api|bug)\b",
                r"\b(résoudre|fixer|debugger)\b",
                r"\brefonte\b",
            ],
            "mode_boost": {"professionnel": 4},
        },
        "social": {
            "patterns": [
                r"\b(sortie|activité)\b",
                r"\bon pourrait\b",
                r"\bplanifier\b",
            ],
            "mode_boost": {"ami": 3, "personnel": 1},
        },
        "introspection": {
            "patterns": [
                r"\bqui suis[- ]?je\b",
                r"\bmon état\b",
                r"\bétat d'esprit\b",
                r"\bhumeur\b",
            ],
            "mode_boost": {"psychologique": 3, "personnel": 2},
        },
    },
    "humeur_vers_mode": {
        "triste": {"psychologique": 3, "amoureux": 1},
        "stresse": {"psychologique": 2, "professionnel": 1},
        "affectueux": {"amoureux": 4},
        "fatigue": {"personnel": 2, "psychologique": 1},
        "curieux": {"professionnel": 2, "ami": 1},
        "joyeux": {"ami": 2, "amoureux": 1},
        "neutre": {},
    },
    "commandes_explicites": [
        r"(?:passe|passer|active|activer|met|mets|basculer?)\s+(?:en\s+)?mode\s+(\w+)",
        r"mode\s+(\w+)\s*(?:s'il te pla[iî]t|stp)?",
        r"(?:je\s+veux\s+)(?:le\s+)?mode\s+(\w+)",
    ],
    "raccourcis_clavier": {
        "1": "amoureux",
        "2": "personnel",
        "3": "ami",
        "4": "psychologique",
        "5": "professionnel",
        "0": "standard",
    },
}

_GUIDES_MODE = {
    "standard": "Ton équilibré : chaleureux sans excès, utile et clair.",
    "amoureux": "Partenaire attentif, tendre, exclusif — complicité, petits mots, présence.",
    "personnel": "Vie privée et intimité du quotidien — orchidées, maison, routines, sans jargon pro.",
    "ami": "Confident décontracté — écoute, humour léger, sorties et hobbies.",
    "psychologique": "Bienveillant et centré sur les émotions — valider, écouter, pas de diagnostic médical.",
    "professionnel": "Double virtuel dev senior — précis, structuré, webdev et résolution de problèmes.",
    "auto": "Adapter le registre au message courant.",
}


def charger_config_modes() -> dict[str, Any]:
    cfg = _lire_json(MODES_CONFIG_FILE, {})
    if not isinstance(cfg, dict):
        cfg = {}
    merged = json.loads(json.dumps(_CONFIG_DEFAUT))
    for key in ("mots_cles", "intentions", "humeur_vers_mode", "raccourcis_clavier"):
        if key in cfg and isinstance(cfg[key], dict):
            if key == "mots_cles":
                for mode, mots in cfg[key].items():
                    merged.setdefault("mots_cles", {}).setdefault(mode, [])
                    if isinstance(mots, list):
                        merged["mots_cles"][mode] = list(
                            dict.fromkeys(merged["mots_cles"].get(mode, []) + mots)
                        )
            elif key == "intentions":
                merged["intentions"].update(cfg[key])
            elif key == "humeur_vers_mode":
                merged["humeur_vers_mode"].update(cfg[key])
            else:
                merged[key].update(cfg[key])
    for k, v in cfg.items():
        if k not in merged:
            merged[k] = v
    return merged


def _normaliser_mode(nom: str) -> str | None:
    m = (nom or "").lower().strip()
    m = _MODE_ALIASES.get(m, m)
    if m in MODES_ACTIFS:
        return m
    if m == "professionnel" or m == "pro":
        return "professionnel"
    return None


def detecter_commande_mode(texte: str) -> str | None:
    t = (texte or "").strip()
    if not t:
        return None
    tl = t.lower()
    if re.search(r"\b(mode\s+)?(standard|normal|défaut|defaut|auto)\b", tl):
        if "auto" in tl and "mode auto" in tl or tl.strip() in ("auto", "mode auto"):
            return "auto"
        if any(x in tl for x in ("standard", "normal", "défaut", "defaut")):
            return "standard"
    cfg = charger_config_modes()
    for pattern in cfg.get("commandes_explicites", _CONFIG_DEFAUT["commandes_explicites"]):
        m = re.search(pattern, tl, re.I)
        if m:
            mode = _normaliser_mode(m.group(1))
            if mode:
                return mode
    return None


def _score_mots_cles(texte: str, cfg: dict) -> dict[str, float]:
    t = (texte or "").lower()
    scores: dict[str, float] = {m: 0.0 for m in MODES_ACTIFS if m not in ("auto", "standard")}
    for mode, mots in (cfg.get("mots_cles") or {}).items():
        if mode not in scores:
            continue
        for mot in mots:
            if mot.lower() in t:
                scores[mode] += 2.0 + min(len(mot) / 20, 1.0)
    return scores


def _score_intentions(texte: str, cfg: dict) -> dict[str, float]:
    t = texte or ""
    scores: dict[str, float] = {m: 0.0 for m in MODES_ACTIFS if m not in ("auto", "standard")}
    for _nom, spec in (cfg.get("intentions") or {}).items():
        if not isinstance(spec, dict):
            continue
        for pat in spec.get("patterns", []):
            try:
                if re.search(pat, t, re.I):
                    for mode, pts in (spec.get("mode_boost") or {}).items():
                        if mode in scores:
                            scores[mode] += float(pts)
                    break
            except re.error:
                continue
    return scores


def _fusionner_scores(*dicts: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for d in dicts:
        for k, v in d.items():
            out[k] = out.get(k, 0.0) + v
    return out


def analyser_message(
    texte: str,
    mode_config_force: str | None = None,
    mode_precedent: str = "standard",
    compteur_sticky: int = 0,
) -> dict[str, Any]:
    """
    Analyse complète d'un message utilisateur.
    Retourne mode_suggere, confiance, intention, humeur, changement, confirmation, etc.
    """
    cfg = charger_config_modes()
    texte = (texte or "").strip()
    humeur = detecter_humeur(texte)

    cmd = detecter_commande_mode(texte)
    if cmd:
        return {
            "mode": cmd,
            "mode_suggere": cmd,
            "confiance": 1.0,
            "humeur": humeur,
            "intention": "commande_explicite",
            "changement": cmd != mode_precedent,
            "source": "commande",
            "confirmation_requise": False,
            "scores": {cmd: 100.0},
            "guide": _GUIDES_MODE.get(cmd, ""),
        }

    if mode_config_force and mode_config_force not in ("auto",):
        return {
            "mode": mode_config_force,
            "mode_suggere": mode_config_force,
            "confiance": 1.0,
            "humeur": humeur,
            "intention": "config_fixe",
            "changement": mode_config_force != mode_precedent,
            "source": "config",
            "confirmation_requise": False,
            "scores": {mode_config_force: 100.0},
            "guide": _GUIDES_MODE.get(mode_config_force, ""),
        }

    scores = _fusionner_scores(
        _score_mots_cles(texte, cfg),
        _score_intentions(texte, cfg),
    )
    hum_map = (cfg.get("humeur_vers_mode") or {}).get(humeur) or {}
    for mode, pts in hum_map.items():
        scores[mode] = scores.get(mode, 0.0) + float(pts)

    # Légère inertie : favoriser le mode actuel si scores proches
    sticky_n = int(cfg.get("messages_sticky", 2))
    if compteur_sticky < sticky_n and mode_precedent in scores:
        scores[mode_precedent] = scores.get(mode_precedent, 0.0) + 1.5

    if not scores or max(scores.values()) <= 0:
        defaut = cfg.get("defaut_si_neutre", "amoureux")
        if humeur in ("triste", "stresse"):
            defaut = "psychologique"
        elif humeur == "affectueux":
            defaut = "amoureux"
        elif humeur == "curieux" and "?" in texte:
            defaut = "professionnel"
        return {
            "mode": defaut,
            "mode_suggere": defaut,
            "confiance": 0.35,
            "humeur": humeur,
            "intention": "neutre",
            "changement": defaut != mode_precedent,
            "source": "defaut_humeur",
            "confirmation_requise": False,
            "scores": scores,
            "guide": _GUIDES_MODE.get(defaut, ""),
        }

    best = max(scores, key=scores.get)
    total = sum(scores.values()) or 1.0
    confiance = scores[best] / total

    # Intention dominante (label lisible)
    intention = "conversation"
    if scores.get("psychologique", 0) >= scores.get("amoureux", 0) and humeur in ("triste", "stresse"):
        intention = "soutien_emotionnel"
    elif best == "professionnel":
        intention = "travail_technique"
    elif best == "amoureux":
        intention = "complicite"
    elif best == "ami":
        intention = "social"
    elif best == "personnel":
        intention = "vie_personnelle"

    seuil_bas = float(cfg.get("seuil_confiance_auto", 0.42))
    seuil_haut = float(cfg.get("seuil_confiance_haute", 0.62))
    conf_requise = bool(cfg.get("confirmation_si_ambigu", True)) and seuil_bas <= confiance < seuil_haut

    # Second meilleur trop proche → ambiguïté
    sorted_modes = sorted(scores.items(), key=lambda x: -x[1])
    if len(sorted_modes) >= 2:
        s1, s2 = sorted_modes[0][1], sorted_modes[1][1]
        if s2 > 0 and s1 / (s1 + s2) < seuil_haut:
            conf_requise = conf_requise or (confiance < seuil_haut)

    mode_final = best
    if confiance < seuil_bas and mode_precedent not in ("auto", "standard"):
        mode_final = mode_precedent
        confiance = max(confiance, 0.4)

    return {
        "mode": mode_final,
        "mode_suggere": best,
        "confiance": round(confiance, 3),
        "humeur": humeur,
        "intention": intention,
        "changement": mode_final != mode_precedent,
        "source": "detection_auto",
        "confirmation_requise": conf_requise and mode_final != mode_precedent,
        "scores": {k: round(v, 2) for k, v in sorted(scores.items(), key=lambda x: -x[1])},
        "guide": _GUIDES_MODE.get(mode_final, ""),
    }


def libelle_mode(mode: str) -> str:
    labels = {
        "amoureux": "Amoureux",
        "personnel": "Personnel",
        "ami": "Ami",
        "psychologique": "Psychologique",
        "professionnel": "Professionnel",
        "standard": "Standard",
        "auto": "Auto",
    }
    return labels.get(mode, mode.capitalize())


def contexte_mode_pour_prompt(analyse: dict[str, Any], mode_actif: str) -> str:
    a = analyse or {}
    lignes = [
        f"MODE JARVIS ACTIF : {libelle_mode(mode_actif).upper()}",
        f"Guide de ton : {_GUIDES_MODE.get(mode_actif, '')}",
        f"Humeur détectée : {a.get('humeur', 'neutre')} | Intention : {a.get('intention', 'conversation')}",
        f"Confiance détection : {int((a.get('confiance') or 0) * 100)}%",
    ]
    if a.get("confirmation_requise"):
        lignes.append(
            "Le changement de mode est incertain — tu peux demander brièvement : "
            f"« Je bascule en mode {libelle_mode(a.get('mode_suggere', mode_actif))}, ça te convient ? »"
        )
    return "\n".join(lignes)
