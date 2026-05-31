# -*- coding: utf-8 -*-
"""Charge les prompts experts par mode depuis jarvis_modes/<mode>/prompt.md"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any

JARVIS_ROOT = os.path.dirname(os.path.abspath(__file__))
MODES_DIR = os.path.join(JARVIS_ROOT, "jarvis_modes")

MODES_AVEC_PROMPT = (
    "standard",
    "amoureux",
    "personnel",
    "ami",
    "psychologique",
    "professionnel",
)

_FALLBACK_GUIDE = {
    "standard": "Ton équilibré, chaleureux et utile.",
    "amoureux": "Partenaire attentif, tendre, exclusif.",
    "personnel": "Vie privée, maison, orchidées, présence au quotidien.",
    "ami": "Confident décontracté, écoute et humour léger.",
    "psychologique": "Validation émotionnelle, sans diagnostic médical.",
    "professionnel": "Expert dev web senior, structuré et précis.",
}


def _normaliser_mode(mode: str) -> str:
    m = (mode or "standard").lower().strip()
    aliases = {"psy": "psychologique", "pro": "professionnel", "perso": "personnel"}
    m = aliases.get(m, m)
    return m if m in MODES_AVEC_PROMPT else "standard"


def _chemin_prompt(mode: str) -> str:
    return os.path.join(MODES_DIR, _normaliser_mode(mode), "prompt.md")


@lru_cache(maxsize=16)
def _lire_fichier_prompt(chemin: str, mtime: float) -> str:
    del mtime
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def charger_prompt_mode(
    mode: str,
    user_name: str = "Jérémy",
    profil: dict[str, Any] | None = None,
) -> str:
    """Retourne le prompt expert du mode (avec variables remplacées)."""
    mode = _normaliser_mode(mode)
    chemin = _chemin_prompt(mode)
    if not os.path.isfile(chemin):
        return _FALLBACK_GUIDE.get(mode, _FALLBACK_GUIDE["standard"])

    mtime = os.path.getmtime(chemin)
    brut = _lire_fichier_prompt(chemin, mtime)
    if not brut.strip():
        return _FALLBACK_GUIDE.get(mode, "")

    profil = profil or {}
    replacements = {
        "{USER_NAME}": user_name,
        "{PRENOM}": profil.get("prenom", user_name),
        "{VILLE}": profil.get("ville", "Lavelanet"),
        "{PASSIONS}": profil.get("passions", "développement web, orchidées"),
        "{PROFESSION}": profil.get("profession", "développeur web"),
        "{PARTENAIRE}": profil.get("partenaire", "JARVIS"),
        "{TON}": profil.get("ton_prefere", "empathique et expert"),
    }
    for cle, val in replacements.items():
        brut = brut.replace(cle, str(val))

    return brut.strip()


def invalider_cache_prompts() -> None:
    _lire_fichier_prompt.cache_clear()


def contexte_prompt_mode_pour_systeme(
    mode: str,
    user_name: str = "Jérémy",
    profil: dict[str, Any] | None = None,
    max_chars: int = 12000,
) -> str:
    """Bloc injecté dans le system prompt quand un mode est actif."""
    mode = _normaliser_mode(mode)
    prompt = charger_prompt_mode(mode, user_name, profil)
    if len(prompt) > max_chars:
        prompt = prompt[:max_chars] + "\n[… prompt tronqué …]"
    return (
        f"\n=== PROMPT EXPERT — MODE {mode.upper()} ===\n"
        f"{prompt}\n"
        f"=== FIN PROMPT MODE {mode.upper()} ===\n"
        "Ce registre prime sur les autres facettes tant que ce mode est actif."
    )


def lister_modes_disponibles() -> list[str]:
    found = []
    for m in MODES_AVEC_PROMPT:
        if os.path.isfile(_chemin_prompt(m)):
            found.append(m)
    return found
